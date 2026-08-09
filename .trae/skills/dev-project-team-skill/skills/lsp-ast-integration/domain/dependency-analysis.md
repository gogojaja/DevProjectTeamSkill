# 依賴分析：導入圖 / 調用鏈 / 影響分析 / 循環檢測

> 編排器：`../SKILL.md`

---

## 1. 依賴分析架構

### 1.1 分析層級
| 層級 | 粒度 | 產物 | 應用 |
|------|------|------|------|
| 模塊級 | 文件/包 | 模塊依賴圖 | 構建順序、循環檢測、解耦 |
| 類型級 | 類/接口 | 類型依賴圖 | 分層約束、架構檢查 |
| 方法級 | 函數/方法 | 調用鏈 | 影響分析、性能熱點、死代碼 |
| 符號級 | 導入/引用 | 引用圖 | 重構範圍、變更影響 |

### 1.2 核心組件
```python
@dataclass
class DependencyGraph:
    nodes: List[DependencyNode]      # 節點
    edges: List[DependencyEdge]      # 邊
    cycle_groups: List[List[str]]    # 循環依賴組
    
    def get_affected(self, changed_nodes: Set[str], depth: int = -1) -> Set[str]:
        """影響分析：從變更節點向後遍歷"""
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
        """檢測循環依賴 (Tarjan SCC)"""
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

## 2. 模塊依賴圖

### 2.1 構建模塊依賴圖
```python
class ModuleDependencyAnalyzer:
    def __init__(self, ast_engine: ASTEngine, project_root: str):
        self.ast_engine = ast_engine
        self.project_root = project_root
    
    def build(self) -> DependencyGraph:
        """構建整個項目的模塊依賴圖"""
        graph = DependencyGraph(nodes=[], edges=[], cycle_groups=[])
        
        # 1. 掃描所有模塊
        modules = self._scan_modules(self.project_root)
        for module in modules:
            graph.nodes.append(DependencyNode(name=module.name, file=module.file))
        
        # 2. 解析導入
        for module in modules:
            imports = self._resolve_imports(module)
            for imported in imports:
                if imported in {m.name for m in modules}:
                    graph.edges.append(DependencyEdge(source=module.name, target=imported))
        
        # 3. 循環檢測
        graph.cycle_groups = graph.find_cycles()
        
        return graph
    
    def _scan_modules(self, root: str) -> List[Module]:
        """掃描項目內所有源文件"""
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
        """解析導入語句"""
        ast = self.ast_engine.parse_file(str(file))
        imports = []
        for node in ast.query("import_statement, import_from_statement"):
            imports.extend(node.imported_names)
        return imports
    
    def _resolve_imports(self, module: Module) -> List[str]:
        """將導入解析為項目內模塊"""
        resolved = []
        for imp in module.imports:
            # 相對導入
            if imp.startswith("."):
                base = module.name.rsplit(".", 1)[0] if len(imp) > 1 else module.name.rsplit(".", 1)[0]
                depth = imp.count(".") - 1
                prefix = base.rsplit(".", depth) if depth > 0 else base
                resolved.append(f"{prefix}.{imp.lstrip('.')}" if isinstance(prefix, str) else ".".join(prefix) + "." + imp.lstrip("."))
            # 項目內絕對導入
            elif imp in self.project_modules:
                resolved.append(imp)
        return resolved
```

### 2.2 架構約束檢查
```python
class ArchitectureChecker:
    def __init__(self, rules: ArchitectureRules):
        self.rules = rules
    
    def check(self, graph: DependencyGraph) -> List[Violation]:
        """檢查分層依賴約束"""
        violations = []
        
        # 如: 禁止 infra → domain 反向依賴
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
        
        # 禁止循環
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

## 3. 調用鏈分析

### 3.1 調用圖構建
```python
class CallGraphBuilder:
    def __init__(self, ast_engine: ASTEngine):
        self.ast_engine = ast_engine
    
    def build(self, project_root: str) -> CallGraph:
        """構建方法級調用圖"""
        graph = CallGraph(nodes=[], calls=[])
        
        # 1. 收集所有函數/方法
        for file in self._scan_files(project_root):
            ast = self.ast_engine.parse_file(file)
            for func in ast.query("function_definition, method_definition"):
                graph.nodes.append(CallNode(
                    name=func.qualified_name,
                    file=file,
                    line=func.start_line,
                    calls=[]
                ))
        
        # 2. 解析函數體內的調用
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
        """提取函數體內的所有調用點"""
        calls = []
        for node in func.body.walk():
            if node.type == "call_expression":
                target = node.function_name
                if self._is_project_function(target):
                    calls.append(CallSite(target=target, line=node.start_line))
        return calls
    
    def call_chain(self, graph: CallGraph, target: str, depth: int = 5) -> List[List[str]]:
        """逆向調用鏈：誰調用了 target"""
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

### 3.2 死代碼檢測
```python
class DeadCodeDetector:
    def detect(self, graph: CallGraph) -> List[DeadCode]:
        """檢測死代碼：無被調用的項目內函數"""
        called = set()
        for edge in graph.calls:
            called.add(edge.target)
        
        dead = []
        for node in graph.nodes:
            # 排除入口點 (main, 裝飾器註冊, 導出)
            if node.name not in called and not self._is_entry_point(node):
                dead.append(DeadCode(node=node.name, file=node.file, line=node.line))
        
        return dead
    
    def _is_entry_point(self, node: CallNode) -> bool:
        """識別入口點"""
        return (node.name in {"main", "__init__", "__call__"} 
                or "if __name__ == '__main__'" in node.containing_code
                or node.is_exported)
```

---

## 4. 影響分析

### 4.1 變更影響分析
```python
class ImpactAnalyzer:
    def __init__(self, graph: DependencyGraph, call_graph: CallGraph):
        self.graph = graph
        self.call_graph = call_graph
    
    def analyze(self, changes: List[FileChange]) -> ImpactReport:
        """分析變更的影響範圍"""
        # 1. 確定直接受影響的模塊
        changed_modules = set()
        for change in changes:
            module = self._module_of(change.file)
            changed_modules.add(module)
        
        # 2. 傳遞影響
        affected_modules = self.graph.get_affected(changed_modules, depth=3)
        
        # 3. 受影響函數
        affected_functions = set()
        for module in changed_modules | affected_modules:
            for node in self.call_graph.nodes:
                if node.file.startswith(module):
                    for chain in self.call_graph.call_chain(node.name, depth=3):
                        affected_functions.update(chain)
        
        # 4. 受影響測試
        affected_tests = self._find_affected_tests(affected_modules)
        
        return ImpactReport(
            changed=changed_modules,
            affected_modules=affected_modules,
            affected_functions=affected_functions,
            affected_tests=affected_tests,
            risk_level=self._assess_risk(affected_modules, affected_functions)
        )
    
    def _assess_risk(self, modules, functions) -> str:
        """風險評估"""
        if len(functions) > 20 or len(modules) > 5:
            return "high"
        elif len(functions) > 5:
            return "medium"
        return "low"
    
    def _find_affected_tests(self, modules) -> List[str]:
        """查找需要運行的測試"""
        tests = []
        for module in modules:
            test_path = self._test_for_module(module)
            if test_path:
                tests.append(test_path)
        return tests
```

### 4.2 影響報告
```python
@dataclass
class ImpactReport:
    changed: Set[str]           # 直接變更模塊
    affected_modules: Set[str]  # 間接受影響模塊
    affected_functions: Set[str]  # 受影響函數
    affected_tests: List[str]   # 需運行的測試
    risk_level: str             # high / medium / low
    
    def render(self) -> str:
        """渲染影響報告"""
        lines = [
            "## 影響分析報告",
            "",
            f"**風險等級**: {self.risk_level.upper()}",
            "",
            "### 直接變更",
            *[f"- `{m}`" for m in sorted(self.changed)],
            "",
            "### 間接受影響",
            *[f"- `{m}`" for m in sorted(self.affected_modules)],
            "",
            "### 受影響函數",
            *[f"- `{f}`" for f in sorted(self.affected_functions)],
            "",
            "### 需運行測試",
            *[f"- `{t}`" for t in self.affected_tests],
        ]
        return "\n".join(lines)
```

---

## 5. 循環依賴檢測與解決

### 5.1 循環檢測
```python
class CycleDetector:
    def __init__(self, graph: DependencyGraph):
        self.graph = graph
        self.cycles = []
        self.current_path = []
        self.visited = set()
    
    def detect_all(self) -> List[Cycle]:
        """檢測所有循環依賴"""
        self.cycles = []
        for node in self.graph.nodes:
            self._dfs(node.name, [])
        return self._dedupe(self.cycles)
    
    def _dfs(self, current, path):
        """DFS 查找環"""
        if current in path:
            # 找到環
            cycle_start = path.index(current)
            cycle = path[cycle_start:] + [current]
            self.cycles.append(cycle)
            return
        
        for edge in self.graph.edges:
            if edge.source == current:
                self._dfs(edge.target, path + [current])
    
    def _dedupe(self, cycles) -> List[Cycle]:
        """去除旋轉等價的循環"""
        seen = set()
        unique = []
        for cycle in cycles:
            # 規範化: 以最小元素為起點
            min_idx = cycle.index(min(cycle))
            normalized = tuple(cycle[min_idx:] + cycle[:min_idx])
            if normalized not in seen:
                seen.add(normalized)
                unique.append(cycle)
        return unique
```

### 5.2 解決建議
```python
class CycleResolver:
    def suggest(self, cycle: List[str]) -> List[Resolution]:
        """為循環依賴提供解決建議"""
        suggestions = []
        
        # 1. 提取公共依賴
        common = self._find_common_dependency(cycle)
        if common:
            suggestions.append(Resolution(
                type="extract_common",
                description=f"提取公共模塊 `{common}` 為獨立依賴",
                steps=[
                    f"創建 `{common}` 模塊存放共享代碼",
                    f"更新 {cycle} 的導入指向 `{common}`",
                ]
            ))
        
        # 2. 接口隔離
        suggestions.append(Resolution(
            type="interface_separation",
            description="引入接口隔離循環",
            steps=[
                f"為 {cycle[0]} 定義接口",
                f"讓 {cycle[1]} 依賴接口而非實現",
            ]
        ))
        
        # 3. 依賴注入
        suggestions.append(Resolution(
            type="dependency_injection",
            description="使用依賴注入打破循環",
            steps=[
                f"將 {cycle[1]} 對 {cycle[0]} 的依賴改為構造函數注入",
            ]
        ))
        
        return suggestions
```

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08