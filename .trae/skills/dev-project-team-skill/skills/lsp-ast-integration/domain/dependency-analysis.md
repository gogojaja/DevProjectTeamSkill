# 依赖分析：导入图 / 调用链 / 影响分析 / 循环检测

> 编排器：`../SKILL.md`

---

## 1. 依赖分析架构

### 1.1 分析层级
| 层级 | 粒度 | 产物 | 应用 |
|------|------|------|------|
| 模块级 | 文件/包 | 模块依赖图 | 构建顺序、循环检测、解耦 |
| 类型级 | 类/接口 | 类型依赖图 | 分层约束、架构检查 |
| 方法级 | 函数/方法 | 调用链 | 影响分析、性能热点、死代码 |
| 符号级 | 导入/引用 | 引用图 | 重构范围、变更影响 |

### 1.2 核心组件
```python
@dataclass
class DependencyGraph:
    nodes: List[DependencyNode]      # 节点
    edges: List[DependencyEdge]      # 边
    cycle_groups: List[List[str]]    # 循环依赖组
    
    def get_affected(self, changed_nodes: Set[str], depth: int = -1) -> Set[str]:
        """影响分析：从变更节点向后遍历"""
        affected = set()
        queue = list(changed_nodes)
        
        while queue and (depth < 0 or len(queue) <= depth):
            current = queue.pop()
            for edge in self.edges:
                if edge.source == current and edge.target not in affected:
                    affected.add(edge.target)
                    queue.append(edge.target)
        return affected
    
    def find_cycles(self) -> List[List[str]]:
        """检测循环依赖 (Tarjan SCC)"""
        index = 0
        stack = []
        indices = {}
        lowlinks = {}
        result = []
        
        def strongconnect(node):
            nonlocal index
            indices[node] = index
            lowlinks[node] = index
            index += 1
            stack.append(node)
            
            for edge in self.edges:
                if edge.source == node:
                    if edge.target not in indices:
                        strongconnect(edge.target)
                        lowlinks[node] = min(lowlinks[node], lowlinks[edge.target])
                    elif edge.target in stack:
                        lowlinks[node] = min(lowlinks[node], indices[edge.target])
            
            if lowlinks[node] == indices[node]:
                scc = []
                while True:
                    n = stack.pop()
                    scc.append(n)
                    if n == node:
                        break
                if len(scc) > 1:
                    result.append(scc)
        
        for node in self.nodes:
            if node.name not in indices:
                strongconnect(node.name)
        
        return result
```

---

## 2. 模块依赖图

### 2.1 构建模块依赖图
```python
class ModuleDependencyAnalyzer:
    def __init__(self, ast_engine: ASTEngine, project_root: str):
        self.ast_engine = ast_engine
        self.project_root = project_root
    
    def build(self) -> DependencyGraph:
        """构建整个项目的模块依赖图"""
        graph = DependencyGraph(nodes=[], edges=[], cycle_groups=[])
        
        # 1. 扫描所有模块
        modules = self._scan_modules(self.project_root)
        for module in modules:
            graph.nodes.append(DependencyNode(name=module.name, file=module.file))
        
        # 2. 解析导入
        for module in modules:
            imports = self._resolve_imports(module)
            for imported in imports:
                if imported in {m.name for m in modules}:
                    graph.edges.append(DependencyEdge(source=module.name, target=imported))
        
        # 3. 循环检测
        graph.cycle_groups = graph.find_cycles()
        
        return graph
    
    def _scan_modules(self, root: str) -> List[Module]:
        """扫描项目内所有源文件"""
        modules = []
        for path in Path(root).rglob("*.py"):
            module = Module(
                name=str(path.relative_to(root)).replace("/", ".").removesuffix(".py"),
                file=str(path),
                imports=[]
            )
            module.imports = self._parse_imports(path)
            modules.append(module)
        return modules
    
    def _parse_imports(self, file: Path) -> List[str]:
        """解析导入语句"""
        ast = self.ast_engine.parse_file(str(file))
        imports = []
        for node in ast.query("import_statement, import_from_statement"):
            imports.extend(node.imported_names)
        return imports
    
    def _resolve_imports(self, module: Module) -> List[str]:
        """将导入解析为项目内模块"""
        resolved = []
        for imp in module.imports:
            # 相对导入
            if imp.startswith("."):
                base = module.name.rsplit(".", 1)[0] if len(imp) > 1 else module.name.rsplit(".", 1)[0]
                depth = imp.count(".") - 1
                prefix = base.rsplit(".", depth) if depth > 0 else base
                resolved.append(f"{prefix}.{imp.lstrip('.')}" if isinstance(prefix, str) else ".".join(prefix) + "." + imp.lstrip("."))
            # 项目内绝对导入
            elif imp in self.project_modules:
                resolved.append(imp)
        return resolved
```

### 2.2 架构约束检查
```python
class ArchitectureChecker:
    def __init__(self, rules: ArchitectureRules):
        self.rules = rules
    
    def check(self, graph: DependencyGraph) -> List[Violation]:
        """检查分层依赖约束"""
        violations = []
        
        # 如: 禁止 infra → domain 反向依赖
        for edge in graph.edges:
            source_layer = self.rules.layer_of(edge.source)
            target_layer = self.rules.layer_of(edge.target)
            
            if source_layer and target_layer:
                if not self.rules.allowed(source_layer, target_layer):
                    violations.append(Violation(
                        type="layer_violation",
                        source=edge.source,
                        target=edge.target,
                        message=f"{source_layer} should not depend on {target_layer}"
                    ))
        
        # 禁止循环
        for cycle in graph.cycle_groups:
            violations.append(Violation(
                type="circular_dependency",
                source=cycle[0],
                target=cycle[-1],
                message=f"Circular dependency: {' -> '.join(cycle + [cycle[0]])}"
            ))
        
        return violations
```

---

## 3. 调用链分析

### 3.1 调用图构建
```python
class CallGraphBuilder:
    def __init__(self, ast_engine: ASTEngine):
        self.ast_engine = ast_engine
    
    def build(self, project_root: str) -> CallGraph:
        """构建方法级调用图"""
        graph = CallGraph(nodes=[], calls=[])
        
        # 1. 收集所有函数/方法
        for file in self._scan_files(project_root):
            ast = self.ast_engine.parse_file(file)
            for func in ast.query("function_definition, method_definition"):
                graph.nodes.append(CallNode(
                    name=func.qualified_name,
                    file=file,
                    line=func.start_line,
                    calls=[]
                ))
        
        # 2. 解析函数体内的调用
        for node in graph.nodes:
            ast = self.ast_engine.parse_file(node.file)
            func = self._find_function(ast, node.name)
            if func:
                for call in self._extract_calls(func):
                    if call.target in {n.name for n in graph.nodes}:
                        node.calls.append(call.target)
                        graph.calls.append(CallEdge(source=node.name, target=call.target, line=call.line))
        
        return graph
    
    def _extract_calls(self, func) -> List[CallSite]:
        """提取函数体内的所有调用点"""
        calls = []
        for node in func.body.walk():
            if node.type == "call_expression":
                target = node.function_name
                if self._is_project_function(target):
                    calls.append(CallSite(target=target, line=node.start_line))
        return calls
    
    def call_chain(self, graph: CallGraph, target: str, depth: int = 5) -> List[List[str]]:
        """逆向调用链：谁调用了 target"""
        chains = []
        
        def dfs(current, path, remaining):
            if remaining == 0:
                return
            for edge in graph.calls:
                if edge.target == current:
                    if edge.source not in path:
                        new_path = path + [edge.source]
                        chains.append(new_path)
                        dfs(edge.source, new_path, remaining - 1)
        
        dfs(target, [target], depth)
        return chains
```

### 3.2 死代码检测
```python
class DeadCodeDetector:
    def detect(self, graph: CallGraph) -> List[DeadCode]:
        """检测死代码：无被调用的项目内函数"""
        called = set()
        for edge in graph.calls:
            called.add(edge.target)
        
        dead = []
        for node in graph.nodes:
            # 排除入口点 (main, 装饰器注册, 导出)
            if node.name not in called and not self._is_entry_point(node):
                dead.append(DeadCode(node=node.name, file=node.file, line=node.line))
        
        return dead
    
    def _is_entry_point(self, node: CallNode) -> bool:
        """识别入口点"""
        return (node.name in {"main", "__init__", "__call__"} 
                or "if __name__ == '__main__'" in node.containing_code
                or node.is_exported)
```

---

## 4. 影响分析

### 4.1 变更影响分析
```python
class ImpactAnalyzer:
    def __init__(self, graph: DependencyGraph, call_graph: CallGraph):
        self.graph = graph
        self.call_graph = call_graph
    
    def analyze(self, changes: List[FileChange]) -> ImpactReport:
        """分析变更的影响范围"""
        # 1. 确定直接受影响的模块
        changed_modules = set()
        for change in changes:
            module = self._module_of(change.file)
            changed_modules.add(module)
        
        # 2. 传递影响
        affected_modules = self.graph.get_affected(changed_modules, depth=3)
        
        # 3. 受影响函数
        affected_functions = set()
        for module in changed_modules | affected_modules:
            for node in self.call_graph.nodes:
                if node.file.startswith(module):
                    for chain in self.call_graph.call_chain(node.name, depth=3):
                        affected_functions.update(chain)
        
        # 4. 受影响测试
        affected_tests = self._find_affected_tests(affected_modules)
        
        return ImpactReport(
            changed=changed_modules,
            affected_modules=affected_modules,
            affected_functions=affected_functions,
            affected_tests=affected_tests,
            risk_level=self._assess_risk(affected_modules, affected_functions)
        )
    
    def _assess_risk(self, modules, functions) -> str:
        """风险评估"""
        if len(functions) > 20 or len(modules) > 5:
            return "high"
        elif len(functions) > 5:
            return "medium"
        return "low"
    
    def _find_affected_tests(self, modules) -> List[str]:
        """查找需要运行的测试"""
        tests = []
        for module in modules:
            test_path = self._test_for_module(module)
            if test_path:
                tests.append(test_path)
        return tests
```

### 4.2 影响报告
```python
@dataclass
class ImpactReport:
    changed: Set[str]           # 直接变更模块
    affected_modules: Set[str]  # 间接受影响模块
    affected_functions: Set[str]  # 受影响函数
    affected_tests: List[str]   # 需运行的测试
    risk_level: str             # high / medium / low
    
    def render(self) -> str:
        """渲染影响报告"""
        lines = [
            "## 影响分析报告",
            "",
            f"**风险等级**: {self.risk_level.upper()}",
            "",
            "### 直接变更",
            *[f"- `{m}`" for m in sorted(self.changed)],
            "",
            "### 间接受影响",
            *[f"- `{m}`" for m in sorted(self.affected_modules)],
            "",
            "### 受影响函数",
            *[f"- `{f}`" for f in sorted(self.affected_functions)],
            "",
            "### 需运行测试",
            *[f"- `{t}`" for t in self.affected_tests],
        ]
        return "\n".join(lines)
```

---

## 5. 循环依赖检测与解决

### 5.1 循环检测
```python
class CycleDetector:
    def __init__(self, graph: DependencyGraph):
        self.graph = graph
        self.cycles = []
        self.current_path = []
        self.visited = set()
    
    def detect_all(self) -> List[Cycle]:
        """检测所有循环依赖"""
        self.cycles = []
        for node in self.graph.nodes:
            self._dfs(node.name, [])
        return self._dedupe(self.cycles)
    
    def _dfs(self, current, path):
        """DFS 查找环"""
        if current in path:
            # 找到环
            cycle_start = path.index(current)
            cycle = path[cycle_start:] + [current]
            self.cycles.append(cycle)
            return
        
        for edge in self.graph.edges:
            if edge.source == current:
                self._dfs(edge.target, path + [current])
    
    def _dedupe(self, cycles) -> List[Cycle]:
        """去除旋转等价的循环"""
        seen = set()
        unique = []
        for cycle in cycles:
            # 规范化: 以最小元素为起点
            min_idx = cycle.index(min(cycle))
            normalized = tuple(cycle[min_idx:] + cycle[:min_idx])
            if normalized not in seen:
                seen.add(normalized)
                unique.append(cycle)
        return unique
```

### 5.2 解决建议
```python
class CycleResolver:
    def suggest(self, cycle: List[str]) -> List[Resolution]:
        """为循环依赖提供解决建议"""
        suggestions = []
        
        # 1. 提取公共依赖
        common = self._find_common_dependency(cycle)
        if common:
            suggestions.append(Resolution(
                type="extract_common",
                description=f"提取公共模块 `{common}` 为独立依赖",
                steps=[
                    f"创建 `{common}` 模块存放共享代码",
                    f"更新 {cycle} 的导入指向 `{common}`",
                ]
            ))
        
        # 2. 接口隔离
        suggestions.append(Resolution(
            type="interface_separation",
            description="引入接口隔离循环",
            steps=[
                f"为 {cycle[0]} 定义接口",
                f"让 {cycle[1]} 依赖接口而非实现",
            ]
        ))
        
        # 3. 依赖注入
        suggestions.append(Resolution(
            type="dependency_injection",
            description="使用依赖注入打破循环",
            steps=[
                f"将 {cycle[1]} 对 {cycle[0]} 的依赖改为构造函数注入",
            ]
        ))
        
        return suggestions
```

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08