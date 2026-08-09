# LSP+AST 聯合：混合導航 / 語義感知重構 / 類型感知生成

> 編排器：`../SKILL.md`

---

## 1. LSP 與 AST 互補性

### 1.1 能力互補
| 維度 | LSP | AST | 聯合優勢 |
|------|-----|-----|----------|
| 精度 | 高（語言服務器） | 中（語法級） | LSP 定位置、AST 定結構 |
| 範圍 | 當前項目+依賴 | 可解析範圍 | LSP 跨依賴、AST 全量掃描 |
| 性能 | 按需計算 | 全量索引 | LSP 熱點查詢、AST 批量分析 |
| 動態 | 支持語言特性 | 靜態結構 | LSP 補動態、AST 補批量 |
| 變更 | 實時增量 | 全量重解析 | LSP 驅動、AST 驗證 |

### 1.2 聯合架構
```python
class LSPASTIntegration:
    """LSP + AST 聯合引擎"""
    
    def __init__(self, ast_engine: ASTEngine, lsp_factory: LSPClientFactory):
        self.ast_engine = ast_engine
        self.lsp_factory = lsp_factory
        self.lsp_clients: Dict[str, LSPClient] = {}
        self.index = ProjectIndex()
    
    def for_language(self, language: str) -> "LSPASTIntegration":
        """初始化語言客戶端"""
        if language not in self.lsp_clients:
            self.lsp_clients[language] = self.lsp_factory.create(language)
        return self
    
    def index_project(self, project_root: str):
        """全量索引項目：AST 構建結構、LSP 補充語義"""
        for file in self._scan_files(project_root):
            language = self._detect_language(file)
            ast = self.ast_engine.parse_file(file)
            
            # 構建 AST 索引
            self.index.add_file(file, ast)
            
            # 構建符號表
            symbols = self._extract_symbols(ast)
            self.index.add_symbols(file, symbols)
        
        # 構建依賴圖
        self.index.build_dependency_graph(self.ast_engine)
        
        # 檢測循環
        self.index.cycles = self.index.dependency_graph.find_cycles()
```

---

## 2. 混合導航

### 2.1 導航策略
```python
class HybridNavigator:
    """混合導航：LSP 優先，AST 兜底"""
    
    def __init__(self, integration: LSPASTIntegration):
        self.integration = integration
    
    def goto_definition(self, file: str, line: int, col: int) -> Location:
        """跳轉定義"""
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        
        # 1. 優先 LSP
        if lsp:
            result = lsp.goto_definition(file, line, col)
            if result:
                return result
        
        # 2. LSP 失敗 → AST 兜底
        return self._ast_goto_definition(file, line, col)
    
    def _ast_goto_definition(self, file: str, line: int, col: int) -> Optional[Location]:
        """AST 級定義查找"""
        ast = self.integration.index.get_ast(file)
        node = ast.node_at(line, col)
        
        # 向上查找最近的有名字符號
        while node and not node.has_name:
            node = node.parent
        
        if not node or not node.name:
            return None
        
        # 查索引中的符號表
        definitions = self.integration.index.find_symbol(node.name)
        if definitions:
            # 返回最近的定義
            return self._nearest_definition(definitions, file)
        
        return None
    
    def find_references(self, file: str, line: int, col: int) -> List[Location]:
        """查找引用"""
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        
        # 1. 確定符號名
        ast = self.integration.index.get_ast(file)
        node = ast.node_at(line, col)
        symbol_name = self._resolve_symbol_name(node)
        
        # 2. 合併 LSP + AST 引用
        references = []
        
        if lsp:
            refs = lsp.find_references(file, line, col)
            references.extend(refs)
        
        # AST 兜底：全項目掃描
        ast_refs = self.integration.index.find_all_references(symbol_name)
        references.extend(ast_refs)
        
        # 去重
        return self._dedupe_locations(references)
    
    def hover(self, file: str, line: int, col: int) -> HoverInfo:
        """懸停信息"""
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        
        if lsp:
            hover = lsp.hover(file, line, col)
            if hover:
                return hover
        
        # AST 兜底：顯示符號類型信息
        return self._ast_hover(file, line, col)
    
    def _ast_hover(self, file: str, line: int, col: int) -> HoverInfo:
        """AST 級懸停"""
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

### 2.2 導航回退策略
```python
class NavigationFallback:
    """導航回退策略"""
    
    PRIORITY = [
        "lsp_definition",   # LSP 定義
        "lsp_implementation",  # LSP 實現
        "lsp_type_definition", # LSP 類型定義
        "ast_symbol_table", # AST 符號表
        "ast_index_search", # AST 索引搜索
        "text_search",      # 純文本搜索
    ]
    
    def navigate(self, query: NavigationQuery, integration) -> NavigationResult:
        """按優先級嘗試導航策略"""
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

## 3. 語義感知重構

### 3.1 LSP 驅動 + AST 驗證
```python
class SemanticRefactoring:
    """語義感知重構"""
    
    def __init__(self, integration: LSPASTIntegration):
        self.integration = integration
    
    def safe_rename(self, file: str, line: int, col: int, new_name: str) -> RefactorResult:
        """安全重命名：LSP 算範圍，AST 驗證"""
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        
        # 1. LSP 獲取重命名編輯
        if lsp:
            edit = lsp.rename(file, line, col, new_name)
            changes = self._edit_to_changes(edit)
        else:
            # AST 兜底：手動重構
            changes = self._ast_rename(file, line, col, new_name)
        
        # 2. AST 驗證
        for change in changes:
            errors = self._validate_change(change, language)
            if errors:
                return RefactorResult(success=False, changes=changes, errors=errors)
        
        return RefactorResult(success=True, changes=changes, preview=generate_diff(changes))
    
    def extract_method(self, file: str, range: Range, method_name: str) -> RefactorResult:
        """提取方法：AST 分析數據流，LSP 驗證"""
        # 1. AST 分析目標區域
        ast = self.integration.index.get_ast(file)
        target = ast.node_at_range(range)
        
        if not target:
            return RefactorResult(success=False, errors=["Invalid extraction range"])
        
        # 2. 數據流分析
        data_flow = self._analyze_data_flow(ast, target)
        
        # 3. 生成新方法
        new_method = self._generate_method(method_name, data_flow)
        call_site = self._generate_call(method_name, data_flow.inputs)
        
        # 4. 構建變更
        changes = [
            FileChange(file=file, range=range, new_text=call_site),
            FileChange(file=file, range=self._next_position(ast, range), new_text=f"\n{new_method}\n")
        ]
        
        # 5. LSP 診斷驗證
        return self._validate_changes(changes, language)
    
    def _analyze_data_flow(self, ast, target) -> DataFlow:
        """數據流分析"""
        inputs = set()
        outputs = set()
        returned = None
        
        def walk(node):
            nonlocal returned
            if node.type in {"identifier", "name"}:
                # 判斷讀寫
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
        
        # 過濾局部變量
        local_vars = self._find_local_variables(target)
        return DataFlow(
            inputs=inputs - local_vars,
            outputs=outputs - local_vars,
            returned=returned
        )
```

### 3.2 重構安全檢查
```python
class RefactoringSafetyChecker:
    """重構安全檢查器"""
    
    def __init__(self, integration: LSPASTIntegration):
        self.integration = integration
    
    def check(self, operation: RefactorOperation) -> List[SafetyIssue]:
        """執行重構前安全檢查"""
        issues = []
        
        # 1. 邊界檢查
        issues.extend(self._check_boundaries(operation))
        
        # 2. 符號衝突
        issues.extend(self._check_symbol_conflicts(operation))
        
        # 3. 公開 API 影響
        issues.extend(self._check_public_api(operation))
        
        # 4. 測試影響
        issues.extend(self._check_tests(operation))
        
        return issues
    
    def _check_boundaries(self, operation) -> List[SafetyIssue]:
        """檢查操作是否超出安全邊界"""
        issues = []
        target = operation.target
        
        # 目標是否在生成代碼中
        if self.integration.index.is_generated(target.file):
            issues.append(SafetyIssue(
                severity="warning",
                message=f"Target is in generated code: {target.file}",
                recommendation="Regenerate instead of manually editing"
            ))
        
        # 目標是否在第三方依賴中
        if self.integration.index.is_vendored(target.file):
            issues.append(SafetyIssue(
                severity="error",
                message=f"Target is in vendored dependency: {target.file}",
                recommendation="Do not modify dependencies"
            ))
        
        return issues
    
    def _check_symbol_conflicts(self, operation) -> List[SafetyIssue]:
        """檢查重命名後的符號衝突"""
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

## 4. 類型感知生成

### 4.1 LSP 類型 → 代碼生成
```python
class TypeAwareGeneration:
    """類型感知代碼生成"""
    
    def __init__(self, integration: LSPASTIntegration):
        self.integration = integration
    
    def implement_interface(self, file: str, interface_name: str, target_file: str = None) -> str:
        """基於 LSP 類型信息實現接口"""
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        
        # 1. 從 LSP 獲取接口定義
        interface_def = self._get_symbol_definition(lsp, file, interface_name)
        
        # 2. 提取接口成員
        members = self._extract_interface_members(interface_def)
        
        # 3. AST 分析當前文件的符號
        ast = self.integration.index.get_ast(target_file or file)
        existing = self._collect_existing_members(ast)
        
        # 4. 生成缺失的實現
        to_implement = [m for m in members if m.name not in existing]
        
        generated = []
        for member in to_implement:
            code = self._generate_member(member)
            generated.append(code)
        
        return "\n\n".join(generated)
    
    def _get_symbol_definition(self, lsp, file, symbol_name) -> Optional[SymbolDefinition]:
        """獲取符號定義"""
        ast = self.integration.index.get_ast(file)
        node = ast.find_symbol(symbol_name)
        if not node:
            return None
        
        # 用 LSP 獲取完整類型信息
        if lsp:
            hover = lsp.hover(node.file, node.start_line, node.start_col)
            if hover:
                return SymbolDefinition(name=symbol_name, type=hover.type, members=hover.members)
        
        # AST 兜底
        return SymbolDefinition(name=symbol_name, type="object", members=node.children)
    
    def generate_dto_from_type(self, file: str, type_name: str) -> str:
        """從類型生成 DTO"""
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

### 4.2 類型安全保證
```python
class TypeSafetyGuarantor:
    """類型安全保證"""
    
    def __init__(self, integration: LSPASTIntegration):
        self.integration = integration
    
    def verify(self, file: str, generated: str) -> List[TypeError_]:
        """驗證生成代碼的類型正確性"""
        # 1. 插入臨時代碼
        temp_file = self._stage_code(file, generated)
        
        # 2. LSP 診斷
        language = self._detect_language(file)
        lsp = self.integration.lsp_clients.get(language)
        diagnostics = lsp.get_diagnostics(temp_file)
        
        # 3. 過濾類型錯誤
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
        """文件變更處理"""
        if change_type == "created":
            self._add_file(file)
        elif change_type == "deleted":
            self._remove_file(file)
        elif change_type == "modified":
            self._update_file(file)
    
    def _update_file(self, file: str):
        """增量更新單個文件"""
        # 1. 記錄舊索引
        old_symbols = self.index.get_symbols(file)
        old_edges = self.index.get_edges_from(file)
        
        # 2. 重解析
        ast = self.integration.ast_engine.parse_file(file)
        new_symbols = self._extract_symbols(ast)
        
        # 3. 對比變更
        added = new_symbols - old_symbols
        removed = old_symbols - new_symbols
        
        # 4. 更新索引
        self.index.update_file(file, ast, new_symbols)
        
        # 5. 影響範圍分析
        affected = self.index.dependency_graph.get_affected({file})
        
        # 6. 通知依賴方
        for watcher in self.watchers:
            watcher.on_index_update(file, added, removed, affected)
    
    def schedule_rebuild(self):
        """調度全量重建"""
        self.index.mark_dirty()
```

### 5.2 一致性檢查
```python
class IndexConsistencyChecker:
    """索引一致性檢查"""
    
    def check(self, index: ProjectIndex) -> List[Inconsistency]:
        """檢查索引與實際代碼的一致性"""
        inconsistencies = []
        
        # 1. 文件存在性
        for symbol in index.all_symbols():
            if not os.path.exists(symbol.file):
                inconsistencies.append(Inconsistency(
                    type="stale_symbol",
                    message=f"Symbol {symbol.name} references missing file {symbol.file}"
                ))
        
        # 2. 符號位置校驗
        for symbol in index.all_symbols():
            source = read_file(symbol.file)
            line = source.splitlines()[symbol.line - 1] if symbol.line - 1 < len(source.splitlines()) else ""
            if symbol.name not in line:
                inconsistencies.append(Inconsistency(
                    type="position_mismatch",
                    message=f"Symbol {symbol.name} position mismatch in {symbol.file}"
                ))
        
        # 3. 依賴邊有效性
        for edge in index.dependency_graph.edges:
            if edge.source not in index.module_names or edge.target not in index.module_names:
                inconsistencies.append(Inconsistency(
                    type="dangling_edge",
                    message=f"Dependency edge {edge.source} -> {edge.target} is stale"
                ))
        
        return inconsistencies
```

---

## 6. 最佳實踐

### 6.1 使用策略
1. **導航**：優先 LSP（精確），失敗後 AST 兜底，再退化文本搜索
2. **重構**：LSP 提供精確範圍，AST 進行結構驗證，雙重確認
3. **生成**：AST 提供結構上下文，LSP 提供類型信息，組合生成
4. **分析**：AST 全量掃描，LSP 按需精查，避免過度查詢
5. **變更**：LSP 實時診斷，AST 批量驗證，確保一致性

### 6.2 性能優化
- LSP 請求按需發出，帶 200ms 防抖
- AST 索引增量更新，避免全量重解析
- 大型項目分區索引，延遲加載
- 查詢結果緩存，失效標記

### 6.3 錯誤處理
- LSP 未啟動/崩潰 → 靜默回退 AST
- AST 解析失敗 → 文本搜索
- 索引不一致 → 標記並觸發重建

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08