# 依賴圖構建與關鍵路徑

> 編排器：`../SKILL.md`　上位：編排器 §5 調度規則

---

## 1. DAG 構建算法

### 1.1 任務節點定義
```python
@dataclass
class TaskNode:
    id: str                    # 唯一標識，如 T1, T2
    name: str                  # 可讀名稱
    role: str                  # architect/executor/test-engineer/...
    deps: List[str]            # 上游依賴 task_id 列表
    estimated_duration: int    # 預估分鐘數
    model_hint: str = "auto"   # haiku/sonnet/opus/auto
    priority: int = 0          # 數值越大越優先
    metadata: Dict = field(default_factory=dict)
```

### 1.2 從 PRD 自動構建 DAG
```python
def build_dag_from_prd(prd: PRDDocument) -> TaskGraph:
    """Architect 產出 PRD → Planner 解析為 DAG"""
    nodes = []
    edges = []
    
    # 1. 接口契約 → Architect 任務
    for contract in prd.contracts:
        nodes.append(TaskNode(
            id=f"ARCH_{contract.id}",
            name=f"設計 {contract.name}",
            role="architect",
            deps=[],
            estimated_duration=30
        ))
    
    # 2. 實現任務 → Executor
    for impl in prd.implementations:
        dep_ids = [f"ARCH_{c.id}" for c in impl.depends_on_contracts]
        nodes.append(TaskNode(
            id=f"IMPL_{impl.id}",
            name=f"實現 {impl.name}",
            role="executor",
            deps=dep_ids,
            estimated_duration=impl.estimate_minutes,
            model_hint=impl.complexity  # simple/standard/complex
        ))
    
    # 3. 測試任務 → TestEngineer
    for test in prd.tests:
        dep_ids = [f"IMPL_{i.id}" for i in test.covers]
        nodes.append(TaskNode(
            id=f"TEST_{test.id}",
            name=f"測試 {test.name}",
            role="test-engineer",
            deps=dep_ids,
            estimated_duration=15
        ))
    
    # 4. 文檔任務 → Writer
    for doc in prd.docs:
        dep_ids = [f"IMPL_{i.id}" for i in doc.describes]
        nodes.append(TaskNode(
            id=f"DOC_{doc.id}",
            name=f"文檔 {doc.name}",
            role="writer",
            deps=dep_ids,
            estimated_duration=10,
            model_hint="haiku"
        ))
    
    return TaskGraph(nodes=nodes)
```

### 1.3 合法性檢查
```python
def validate_dag(graph: TaskGraph) -> List[str]:
    errors = []
    # 1. 無環檢查
    if has_cycle(graph):
        errors.append("DAG 存在環，請檢查依賴關係")
    # 2. 孤立節點
    isolated = [n for n in graph.nodes if not n.deps and not n.children]
    if isolated:
        errors.append(f"孤立任務: {[n.id for n in isolated]}")
    # 3. 缺失依賴
    all_ids = {n.id for n in graph.nodes}
    for n in graph.nodes:
        for dep in n.deps:
            if dep not in all_ids:
                errors.append(f"任務 {n.id} 依賴不存在的 {dep}")
    return errors
```

---

## 2. 拓扑排序與關鍵路徑

### 2.1 Kahn 拓扑排序
```python
def topological_sort(graph: TaskGraph) -> List[TaskNode]:
    in_degree = {n.id: len(n.deps) for n in graph.nodes}
    queue = deque([n for n in graph.nodes if in_degree[n.id] == 0])
    result = []
    
    while queue:
        node = queue.popleft()
        result.append(node)
        for child in node.children:
            in_degree[child.id] -= 1
            if in_degree[child.id] == 0:
                queue.append(child)
    
    if len(result) != len(graph.nodes):
        raise ValueError("DAG 有環，無法拓扑排序")
    return result
```

### 2.2 關鍵路徑計算
```python
def critical_path(graph: TaskGraph) -> List[TaskNode]:
    """返回最長路徑上的任務序列（決定最短完工時間）"""
    # 前向遍歷：計算最早開始時間
    for node in topological_sort(graph):
        node.earliest_start = max(
            [graph.nodes[dep].earliest_finish for dep in node.deps],
            default=0
        )
        node.earliest_finish = node.earliest_start + node.estimated_duration
    
    # 反向遍歷：計算最晚開始時間
    project_duration = max(n.earliest_finish for n in graph.nodes)
    for node in reversed(topological_sort(graph)):
        node.latest_finish = min(
            [graph.nodes[child].latest_start for child in node.children],
            default=project_duration
        )
        node.latest_start = node.latest_finish - node.estimated_duration
    
    # 浮動時間 = 0 的節點在關鍵路徑上
    return [n for n in graph.nodes if n.latest_start == n.earliest_start]
```

### 2.3 關鍵路徑示例
```
DAG:
  ARCH_API(30) → IMPL_API(60) → TEST_API(15) → DOC_API(10)
                 ↘ IMPL_UI(45) → TEST_UI(15) → DOC_UI(10)

關鍵路徑: ARCH_API → IMPL_API → TEST_API → DOC_API
總時長: 115 分鐘
浮動: IMPL_UI/TEST_UI/DOC_UI 有 15 分鐘浮動
```

---

## 3. 並行度優化

### 3.1 層級劃分
```python
def compute_levels(graph: TaskGraph) -> Dict[str, int]:
    """將節點按層級分組，同層可並行"""
    levels = {}
    for node in topological_sort(graph):
        level = max([levels[dep] for dep in node.deps], default=-1) + 1
        levels[node.id] = level
    return levels

# 結果示例:
# Level 0: [ARCH_API]
# Level 1: [IMPL_API, IMPL_UI]
# Level 2: [TEST_API, TEST_UI]
# Level 3: [DOC_API, DOC_UI]
```

### 3.2 資源感知調度
```python
def schedule_with_resources(graph, max_parallel=6, model_quota={"haiku": 4, "sonnet": 2, "opus": 1}):
    levels = compute_levels(graph)
    running = []
    completed = set()
    time = 0
    
    while len(completed) < len(graph.nodes):
        # 釋放完成任務
        for task in list(running):
            if task.finish_time <= time:
                model_quota[task.model] += 1
                running.remove(task)
                completed.add(task.id)
        
        # 啟動就緒任務
        for node_id, level in levels.items():
            if node_id in completed or any(r.id == node_id for r in running):
                continue
            if all(dep in completed for dep in graph.nodes[node_id].deps):
                node = graph.nodes[node_id]
                if model_quota[node.model_hint] > 0 and len(running) < max_parallel:
                    start_task(node, time)
                    model_quota[node.model_hint] -= 1
                    running.append(TaskRun(node, time))
        
        time += 1
    
    return makespan
```

---

## 4. 增量更新

當 PRD 變更時，增量更新 DAG：

```python
def incremental_update(old_graph, new_prd):
    # 1. 識別變更的合約/實現
    changed = diff_contracts(old_graph, new_prd)
    
    # 2. 計算受影響的下游
    affected = set()
    for node_id in changed:
        affected.update(descendants(old_graph, node_id))
    
    # 3. 重新生成受影響子圖
    subgraph = old_graph.subgraph(affected)
    new_subgraph = build_dag_from_prd(new_prd).subgraph(affected)
    
    # 4. 合併保留未變更部分
    return old_graph.replace_subgraph(affected, new_subgraph)
```

---

## 5. 可視化輸出

### 5.1 Mermaid 圖表
```mermaid
graph TD
    ARCH_API[ARCH_API<br/>30min] --> IMPL_API[IMPL_API<br/>60min]
    ARCH_API --> IMPL_UI[IMPL_UI<br/>45min]
    IMPL_API --> TEST_API[TEST_API<br/>15min]
    IMPL_UI --> TEST_UI[TEST_UI<br/>15min]
    TEST_API --> DOC_API[DOC_API<br/>10min]
    TEST_UI --> DOC_UI[DOC_UI<br/>10min]
    
    classDef critical fill:#ffcccc;
    class ARCH_API,IMPL_API,TEST_API,DOC_API critical;
```

### 5.2 JSON 輸出 (給調度器)
```json
{
  "version": "1.0",
  "critical_path": ["ARCH_API", "IMPL_API", "TEST_API", "DOC_API"],
  "project_duration": 115,
  "levels": {
    "0": ["ARCH_API"],
    "1": ["IMPL_API", "IMPL_UI"],
    "2": ["TEST_API", "TEST_UI"],
    "3": ["DOC_API", "DOC_UI"]
  },
  "model_quota": {"haiku": 4, "sonnet": 2, "opus": 1}
}
```

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08