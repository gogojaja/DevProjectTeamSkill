# Ultrawork 高吞吐并行实现

> 编排器：`../SKILL.md`　上位：编排器 §5 调度规则

---

## 1. 架构概览

```
Ultrawork 执行引擎
├── DAG 构建器 (Planner)          → 依赖图 JSON
├── 工作窃取调度器 (Chase-Lev)    → 就绪队列 + 偷取逻辑
├── 模型路由器                    → S0~S3 档位自动选择（免费→强模型）
├── MVCC 状态存储                 → 版本化任务状态、原子提交
├── 执行器池                      → 按档位配置的模型实例
└── 收敛监控器                    → 叶子任务完成 → 触发下游
```

---

## 2. 工作窃取队列

### 2.1 双端队列数据结构
```python
class WorkStealingDeque:
    def __init__(self):
        self._deque = collections.deque()
        self._lock = threading.Lock()
    
    def push_bottom(self, task):      # 生产者：本地任务入队
        with self._lock:
            self._deque.append(task)
    
    def pop_bottom(self):             # 消费者：取自己任务
        with self._lock:
            return self._deque.pop() if self._deque else None
    
    def steal_top(self):              # 偷取者：从别人队列头偷取
        with self._lock:
            return self._deque.popleft() if self._deque else None
```

### 2.2 调度循环
```python
def scheduler_loop(worker_id, local_deque, global_ready):
    while not shutdown:
        task = local_deque.pop_bottom()
        if task is None:
            # 偷取全局就绪任务
            task = global_ready.steal_top()
        if task is None:
            time.sleep(0.01)  # 避免空转
            continue
        execute_task(worker_id, task)
```

### 2.3 就绪判定
任务就绪条件：
1. 所有上游依赖完成（DAG 入度为 0）
2. 所需资源可用（模型配额、文件锁等）
3. 未被其他 Worker 领取

---

## 3. MVCC 状态同步

### 3.1 版本化任务状态
```json
{
  "task_id": "T3",
  "version": 5,
  "status": "running",
  "worker": "executor-2",
  "started_at": "2026-08-08T10:15:00Z",
  "checkpoint": {"files_modified": ["src/api.py"], "tests_passed": 12}
}
```

### 3.2 原子提交协议
1. Worker 读取任务当前版本 V
2. 执行过程中本地累积变更
3. 提交时 CAS 比较版本：`if current_version == V: write V+1`
4. 失败 → 重读最新版本 → 合并冲突 → 重试（最多 3 次）

### 3.3 状态持久化
- 存储：`.senate/state/ultrawork-state.json`
- 格式：`{task_id: {version, status, worker, checkpoints...}}`
- 定期快照：每 30 秒或每 10 任务完成

---

## 4. 模型路由表

> 档位定义见 `../../../../references/model_selection.md` §3-4：S0 简单 / S1 常规 / S2 复杂 / S3 高危；成本档：免费 / 低价 / 平衡 / 强模型。

| 任务特征 | 档位 | 成本档 | 理由 |
|----------|------|--------|------|
| 模板代码生成、简单重构、文档 | S0 | 免费/低价 | 机械操作，最低成本 |
| 标准业务逻辑、单测编写、API 实现 | S1 | 低价/平衡 | 平衡质量与速度 |
| 架构设计、复杂算法、安全审查、根因分析 | S2 | 强模型 | 深度推理、上下文大 |
| 需求澄清、契约评审 | S2/S3 | 强模型 | 需全局视角 |

### 4.1 自动路由算法
```python
def route_model(task):
    keywords = task.description.lower()
    if any(k in keywords for k in ["architect", "security", "root-cause", "design"]):
        return "S3"
    if any(k in keywords for k in ["template", "boilerplate", "doc", "simple"]):
        return "S0"
    return "S1"
```

### 4.2 成本控制
- 单流水线强模型（S2/S3）任务上限：30%
- 免费档（S0）优先填满，剩余分配低价/平衡档
- 超预算 → 自动降档：强模型→平衡→低价→免费（S3 高危任务禁止降档，见 model_selection §6.5）

---

## 5. 收敛监控

```python
def check_convergence(dag, completed_tasks):
    """所有叶子节点完成 → 触发收敛"""
    leaf_nodes = [n for n in dag.nodes if not n.children]
    return all(n.id in completed_tasks for n in leaf_nodes)
```

- 叶子任务全部完成 → 标记流水线收敛
- 产出收敛报告：耗时、并行度、模型分布、成功率

---

**文档版本**：v1.0.0　**最后更新**：2026-08-08