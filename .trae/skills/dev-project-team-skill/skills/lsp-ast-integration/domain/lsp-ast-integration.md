# LSP+AST 联合：混合导航 / 语义感知重构 / 类型感知生成

> 编排器：`../SKILL.md`

---

## 1. LSP 与 AST 互补性

### 1.1 能力互补
| 维度 | LSP | AST | 联合优势 |
|------|-----|-----|----------|
| 精度 | 高（语言服务器） | 中（语法级） | LSP 定位置、AST 定结构 |
| 范围 | 当前项目+依赖 | 可解析范围 | LSP 跨依赖、AST 全量扫描 |
| 性能 | 按需计算 | 全量索引 | LSP 热点查询、AST 批量分析 |
| 动态 | 支持语言特性 | 静态结构 | LSP 补动态、AST 补批量 |
| 变更 | 实时增量 | 全量重解析 | LSP 驱动、AST 验证 |

### 1.2 联合架构
```python
class LSPASTIntegration:
    """LSP + AST 联合引擎"""
    
    def __init__(self, ast_engine: ASTEngine, lsp_factory: LSPClientFactory):
        self.ast_engine = ast_engine
        self.lsp_factory = lsp_factory
        self.lsp_clients: Dict[str, LSPClient] = {}
        self.index = ProjectIndex()
    
    def for_language(self, language: str) -> "LSPASTIntegration":
        """初始化语言客户端"""
        if language not in self.lsp_clients:
            self.lsp_clients[language] = self.lsp_factory.create(language)
        return self
    
    def index_project(self, project_root: str):
        """全量索引项目：AST 构建结构、LSP 补充语义"""
        for file in self._scan_files(project_root):
            language = self._detect_language(file)
            ast = self.ast_engine.parse_file(file)
            
            # 构建 AST 索引
            self.index.add_file(file, ast)
            
            # 构建符号表
            symbols = self._extract_symbols(ast)
            self.index.add_symbols(file, symbols)
        
        # 构建依赖图
        self.index.build_dependency_graph(self.ast_engine)
        
        # 检测循环
        self.index.cycles = self.index.dependency_graph.find_cycles()
```

---

## 2. 混合导航

### 2.1 导航策略
```python
class HybridNavigator:
    """混合导航：LSP 优先，AST 兜底"""
    
    def __init__(self, integration: LSPASTIntegration):
        self.integration = integration
    
    def goto_definition(self, file: str, line: int, col: int) -> Location:
        """跳转定义"""
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        
        # 1. 优先 LSP
        if lsp:
            result = lsp.goto_definition(file, line, col)
            if result:
                return result
        
        # 2. LSP 失败 → AST 兜底
        return self._ast_goto_definition(file, line, col)
    
    def _ast_goto_definition(self, file: str, line: int, col: int) -> Optional[Location]:
        """AST 级定义查找"""
        ast = self.integration.index.get_ast(file)
        node = ast.node_at(line, col)
        
        # 向上查找最近的有名字符号
        while node and not node.has_name:
            node = node.parent
        
        if not node or not node.name:
            return None
        
        # 查索引中的符号表
        definitions = self.integration.index.find_symbol(node.name)
        if definitions:
            # 返回最近的定义
            return self._nearest_definition(definitions, file)
        
        return None
    
    def find_references(self, file: str, line: int, col: int) -> List[Location]:
        """查找引用"""
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        
        # 1. 确定符号名
        ast = self.integration.index.get_ast(file)
        node = ast.node_at(line, col)
        symbol_name = self._resolve_symbol_name(node)
        
        # 2. 合并 LSP + AST 引用
        references = []
        
        if lsp:
            refs = lsp.find_references(file, line, col)
            references.extend(refs)
        
        # AST 兜底：全项目扫描
        ast_refs = self.integration.index.find_all_references(symbol_name)
        references.extend(ast_refs)
        
        # 去重
        return self._dedupe_locations(references)
    
    def hover(self, file: str, line: int, col: int) -> HoverInfo:
        """悬停信息"""
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        
        if lsp:
            hover = lsp.hover(file, line, col)
            if hover:
                return hover
        
        # AST 兜底：显示符号类型信息
        return self._ast_hover(file, line, col)
    
    def _ast_hover(self, file: str, line: int, col: int) -> HoverInfo:
        """AST 级悬停"""
        ast = self.integration.index.get_ast(file)
        node = ast.node_at(line, col)
        
        symbol = self.integration.index.get_symbol(node.name) if node and node.name else None
        if symbol:
            return HoverInfo(
                kind=symbol.kind,
                type=symbol.type,
                doc=symbol.docstring,
                location=symbol.definition
            )
        return HoverInfo(kind="unknown", type="any", doc="")
```

### 2.2 导航回退策略
```python
class NavigationFallback:
    """导航回退策略"""
    
    PRIORITY = [
        "lsp_definition",   # LSP 定义
        "lsp_implementation",  # LSP 实现
        "lsp_type_definition", # LSP 类型定义
        "ast_symbol_table", # AST 符号表
        "ast_index_search", # AST 索引搜索
        "text_search",      # 纯文本搜索
    ]
    
    def navigate(self, query: NavigationQuery, integration) -> NavigationResult:
        """按优先级尝试导航策略"""
        for strategy in self.PRIORITY:
            result = self._try_strategy(strategy, query, integration)
            if result.found:
                return result
        return NavigationResult(found=False)
    
    def _try_strategy(self, strategy: str, query, integration) -> NavigationResult:
        try:
            if strategy == "lsp_definition":
                lsp = integration.lsp_clients.get(query.language)
                return NavigationResult(found=True, location=lsp.goto_definition(query.file, query.line, query.col))
            elif strategy == "lsp_implementation":
                lsp = integration.lsp_clients.get(query.language)
                return NavigationResult(found=True, location=lsp.goto_implementation(query.file, query.line, query.col))
            elif strategy == "lsp_type_definition":
                lsp = integration.lsp_clients.get(query.language)
                return NavigationResult(found=True, location=lsp.goto_type_definition(query.file, query.line, query.col))
            elif strategy == "ast_symbol_table":
                return NavigationResult(found=True, location=integration.index.find_symbol(query.symbol_name))
            elif strategy == "ast_index_search":
                return NavigationResult(found=True, location=integration.index.search(query.symbol_name))
            elif strategy == "text_search":
                return NavigationResult(found=True, location=integration.index.text_search(query.symbol_name))
        except Exception:
            pass
        return NavigationResult(found=False)
```

---

## 3. 语义感知重构

### 3.1 LSP 驱动 + AST 验证
```python
class SemanticRefactoring:
    """语义感知重构"""
    
    def __init__(self, integration: LSPASTIntegration):
        self.integration = integration
    
    def safe_rename(self, file: str, line: int, col: int, new_name: str) -> RefactorResult:
        """安全重命名：LSP 算范围，AST 验证"""
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        
        # 1. LSP 获取重命名编辑
        if lsp:
            edit = lsp.rename(file, line, col, new_name)
            changes = self._edit_to_changes(edit)
        else:
            # AST 兜底：手动重构
            changes = self._ast_rename(file, line, col, new_name)
        
        # 2. AST 验证
        for change in changes:
            errors = self._validate_change(change, language)
            if errors:
                return RefactorResult(success=False, changes=changes, errors=errors)
        
        return RefactorResult(success=True, changes=changes, preview=generate_diff(changes))
    
    def extract_method(self, file: str, range: Range, method_name: str) -> RefactorResult:
        """提取方法：AST 分析数据流，LSP 验证"""
        # 1. AST 分析目标区域
        ast = self.integration.index.get_ast(file)
        target = ast.node_at_range(range)
        
        if not target:
            return RefactorResult(success=False, errors=["Invalid extraction range"])
        
        # 2. 数据流分析
        data_flow = self._analyze_data_flow(ast, target)
        
        # 3. 生成新方法
        new_method = self._generate_method(method_name, data_flow)
        call_site = self._generate_call(method_name, data_flow.inputs)
        
        # 4. 构建变更
        changes = [
            FileChange(file=file, range=range, new_text=call_site),
            FileChange(file=file, range=self._next_position(ast, range), new_text=f"\n{new_method}\n")
        ]
        
        # 5. LSP 诊断验证
        return self._validate_changes(changes, language)
    
    def _analyze_data_flow(self, ast, target) -> DataFlow:
        """数据流分析"""
        inputs = set()
        outputs = set()
        returned = None
        
        def walk(node):
            nonlocal returned
            if node.type in {"identifier", "name"}:
                # 判断读写
                parent = node.parent
                if parent and parent.type == "assignment_expression" and parent.left == node:
                    outputs.add(node.name)
                else:
                    inputs.add(node.name)
            elif node.type in {"return_statement", "return"}:
                returned = node.child_by_field("value")
            for child in node.children:
                walk(child)
        
        walk(target)
        
        # 过滤局部变量
        local_vars = self._find_local_variables(target)
        return DataFlow(
            inputs=inputs - local_vars,
            outputs=outputs - local_vars,
            returned=returned
        )
```

### 3.2 重构安全检查
```python
class RefactoringSafetyChecker:
    """重构安全检查器"""
    
    def __init__(self, integration: LSPASTIntegration):
        self.integration = integration
    
    def check(self, operation: RefactorOperation) -> List[SafetyIssue]:
        """执行重构前安全检查"""
        issues = []
        
        # 1. 边界检查
        issues.extend(self._check_boundaries(operation))
        
        # 2. 符号冲突
        issues.extend(self._check_symbol_conflicts(operation))
        
        # 3. 公开 API 影响
        issues.extend(self._check_public_api(operation))
        
        # 4. 测试影响
        issues.extend(self._check_tests(operation))
        
        return issues
    
    def _check_boundaries(self, operation) -> List[SafetyIssue]:
        """检查操作是否超出安全边界"""
        issues = []
        target = operation.target
        
        # 目标是否在生成代码中
        if self.integration.index.is_generated(target.file):
            issues.append(SafetyIssue(
                severity="warning",
                message=f"Target is in generated code: {target.file}",
                recommendation="Regenerate instead of manually editing"
            ))
        
        # 目标是否在第三方依赖中
        if self.integration.index.is_vendored(target.file):
            issues.append(SafetyIssue(
                severity="error",
                message=f"Target is in vendored dependency: {target.file}",
                recommendation="Do not modify dependencies"
            ))
        
        return issues
    
    def _check_symbol_conflicts(self, operation) -> List[SafetyIssue]:
        """检查重命名后的符号冲突"""
        if operation.type != "rename":
            return []
        
        new_name = operation.params["new_name"]
        scope = operation.target.scope
        
        existing = self.integration.index.find_symbols_in_scope(scope)
        if new_name in existing:
            return [SafetyIssue(
                severity="error",
                message=f"Symbol `{new_name}` already exists in scope",
                recommendation="Choose a different name"
            )]
        return []
```

---

## 4. 类型感知生成

### 4.1 LSP 类型 → 代码生成
```python
class TypeAwareGeneration:
    """类型感知代码生成"""
    
    def __init__(self, integration: LSPASTIntegration):
        self.integration = integration
    
    def implement_interface(self, file: str, interface_name: str, target_file: str = None) -> str:
        """基于 LSP 类型信息实现接口"""
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        
        # 1. 从 LSP 获取接口定义
        interface_def = self._get_symbol_definition(lsp, file, interface_name)
        
        # 2. 提取接口成员
        members = self._extract_interface_members(interface_def)
        
        # 3. AST 分析当前文件的符号
        ast = self.integration.index.get_ast(target_file or file)
        existing = self._collect_existing_members(ast)
        
        # 4. 生成缺失的实现
        to_implement = [m for m in members if m.name not in existing]
        
        generated = []
        for member in to_implement:
            code = self._generate_member(member)
            generated.append(code)
        
        return "\n\n".join(generated)
    
    def _get_symbol_definition(self, lsp, file, symbol_name) -> Optional[SymbolDefinition]:
        """获取符号定义"""
        ast = self.integration.index.get_ast(file)
        node = ast.find_symbol(symbol_name)
        if not node:
            return None
        
        # 用 LSP 获取完整类型信息
        if lsp:
            hover = lsp.hover(node.file, node.start_line, node.start_col)
            if hover:
                return SymbolDefinition(name=symbol_name, type=hover.type, members=hover.members)
        
        # AST 兜底
        return SymbolDefinition(name=symbol_name, type="object", members=node.children)
    
    def generate_dto_from_type(self, file: str, type_name: str) -> str:
        """从类型生成 DTO"""
        ast = self.integration.index.get_ast(file)
        node = ast.find_symbol(type_name)
        if not node:
            return ""
        
        # 提取字段
        fields = []
        for child in node.children:
            if child.type == "field_declaration":
                fields.append({
                    "name": child.name,
                    "type": child.type_annotation,
                    "optional": child.is_optional,
                    "default": child.default_value
                })
        
        # 生成
        return self._render_dto(type_name, fields)
```

### 4.2 类型安全保证
```python
class TypeSafetyGuarantor:
    """类型安全保证"""
    
    def __init__(self, integration: LSPASTIntegration):
        self.integration = integration
    
    def verify(self, file: str, generated: str) -> List[TypeError_]:
        """验证生成代码的类型正确性"""
        # 1. 插入临时代码
        temp_file = self._stage_code(file, generated)
        
        # 2. LSP 诊断
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        diagnostics = lsp.get_diagnostics(temp_file)
        
        # 3. 过滤类型错误
        type_errors = [d for d in diagnostics if d.severity == 1]
        
        # 4. 清理
        self._cleanup(temp_file)
        
        return type_errors
```

---

## 5. 索引一致性

### 5.1 增量更新
```python
class IncrementalIndexing:
    """增量索引更新"""
    
    def __init__(self, index: ProjectIndex, integration: LSPASTIntegration):
        self.index = index
        self.integration = integration
        self.watchers = []
    
    def on_file_changed(self, file: str, change_type: str):
        """文件变更处理"""
        if change_type == "created":
            self._add_file(file)
        elif change_type == "deleted":
            self._remove_file(file)
        elif change_type == "modified":
            self._update_file(file)
    
    def _update_file(self, file: str):
        """增量更新单个文件"""
        # 1. 记录旧索引
        old_symbols = self.index.get_symbols(file)
        old_edges = self.index.get_edges_from(file)
        
        # 2. 重解析
        ast = self.integration.ast_engine.parse_file(file)
        new_symbols = self._extract_symbols(ast)
        
        # 3. 对比变更
        added = new_symbols - old_symbols
        removed = old_symbols - new_symbols
        
        # 4. 更新索引
        self.index.update_file(file, ast, new_symbols)
        
        # 5. 影响范围分析
        affected = self.index.dependency_graph.get_affected({file})
        
        # 6. 通知依赖方
        for watcher in self.watchers:
            watcher.on_index_update(file, added, removed, affected)
    
    def schedule_rebuild(self):
        """调度全量重建"""
        self.index.mark_dirty()
```

### 5.2 一致性检查
```python
class IndexConsistencyChecker:
    """索引一致性检查"""
    
    def check(self, index: ProjectIndex) -> List[Inconsistency]:
        """检查索引与实际代码的一致性"""
        inconsistencies = []
        
        # 1. 文件存在性
        for symbol in index.all_symbols():
            if not os.path.exists(symbol.file):
                inconsistencies.append(Inconsistency(
                    type="stale_symbol",
                    message=f"Symbol {symbol.name} references missing file {symbol.file}"
                ))
        
        # 2. 符号位置校验
        for symbol in index.all_symbols():
            source = read_file(symbol.file)
            line = source.splitlines()[symbol.line - 1] if symbol.line - 1 < len(source.splitlines()) else ""
            if symbol.name not in line:
                inconsistencies.append(Inconsistency(
                    type="position_mismatch",
                    message=f"Symbol {symbol.name} position mismatch in {symbol.file}"
                ))
        
        # 3. 依赖边有效性
        for edge in index.dependency_graph.edges:
            if edge.source not in index.module_names or edge.target not in index.module_names:
                inconsistencies.append(Inconsistency(
                    type="dangling_edge",
                    message=f"Dependency edge {edge.source} -> {edge.target} is stale"
                ))
        
        return inconsistencies
```

---

## 6. 最佳实践

### 6.1 使用策略
1. **导航**：优先 LSP（精确），失败后 AST 兜底，再退化文本搜索
2. **重构**：LSP 提供精确范围，AST 进行结构验证，双重确认
3. **生成**：AST 提供结构上下文，LSP 提供类型信息，组合生成
4. **分析**：AST 全量扫描，LSP 按需精查，避免过度查询
5. **变更**：LSP 实时诊断，AST 批量验证，确保一致性

### 6.2 性能优化
- LSP 请求按需发出，带 200ms 防抖
- AST 索引增量更新，避免全量重解析
- 大型项目分区索引，延迟加载
- 查询结果缓存，失效标记

### 6.3 错误处理
- LSP 未启动/崩溃 → 静默回退 AST
- AST 解析失败 → 文本搜索
- 索引不一致 → 标记并触发重建

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08