# 上下文快照：捕获/恢复/归档/版本管理

> 编排器：`../SKILL.md`　上位：编排器 §5 调度规则

---

## 1. 快照定义

### 1.1 触发时机
| 触发器 | 说明 | 优先级 |
|--------|------|--------|
| 会话结束 | 用户退出 / 会话超时 | 高 |
| 阶段切换 | 编排器阶段转换 (plan→prd→exec...) | 高 |
| 手动触发 | 用户执行 `/snapshot` | 中 |
| 关键决策后 | 记录 ADR/关键约束后 | 中 |
| 错误/异常 | 捕获错误上下文用于事后分析 | 低 |

### 1.2 快照内容
```python
@dataclass
class ContextSnapshot:
    id: str                         # snap-{timestamp}-{seq}
    session_id: str                 # 归属会话
    trigger: str                    # manual | phase_change | session_end | decision | error
    timestamp: str                  # ISO 8601
    
    # 任务上下文
    current_task: Optional[str]     # 当前任务描述
    task_progress: Dict             # {task_id: status}
    active_files: List[str]         # 当前打开/编辑的文件
    cursor_positions: Dict[str, int] # 文件光标位置
    
    # 决策/记忆上下文
    recent_decisions: List[str]     # 近期决策 ID
    active_constraints: List[str]   # 生效约束 ID
    working_hypothesis: str         # 当前工作假设/调试方向
    
    # 环境状态
    git_status: Dict                # {branch, commit, dirty_files}
    env_vars: Dict[str, str]        # 关键环境变量
    running_services: List[str]     # 本地运行的服务
    
    # 元数据
    tags: List[str]                 # checkpoint | milestone | debugging | handoff
    metadata: Dict                  # 扩展字段
```

---

## 2. 捕获流程

### 2.1 自动捕获 (会话结束/阶段切换)
```python
def capture_snapshot(trigger: str, session_id: str, extra: Dict = None) -> ContextSnapshot:
    snap = ContextSnapshot(
        id=f"snap-{time.time_ns()}",
        session_id=session_id,
        trigger=trigger,
        timestamp=datetime.now().isoformat(),
        current_task=get_current_task(),
        task_progress=get_task_progress(),
        active_files=get_open_files(),
        cursor_positions=get_cursor_positions(),
        recent_decisions=get_recent_decision_ids(limit=10),
        active_constraints=get_active_constraint_ids(),
        working_hypothesis=get_working_hypothesis(),
        git_status=get_git_status(),
        env_vars=get_key_env_vars(),
        running_services=get_running_services(),
        tags=determine_tags(trigger),
        metadata=extra or {}
    )
    
    # 1. 保存快照文件
    path = f".senate/memory/snapshots/{snap.id}.json"
    atomic_write(path, json.dumps(asdict(snap), ensure_ascii=False, indent=2))
    
    # 2. 更新索引
    update_snapshot_index(snap)
    
    # 3. 关联决策/约束
    for dec_id in snap.recent_decisions:
        link_snapshot_decision(snap.id, dec_id)
    
    return snap
```

### 2.2 手动快照
```bash
# 用户命令
/snapshot "完成 API 设计，准备进入实现阶段"
# 或
/snapshot --tag milestone "Phase 1 完成"
```

---

## 3. 恢复流程

### 3.1 会话启动自动恢复
```python
def restore_on_session_start(session_id: str) -> RestoreReport:
    # 1. 找到最近的有效快照
    snapshots = list_snapshots(session_id=session_id, limit=5)
    if not snapshots:
        return RestoreReport(restored=False, reason="no_snapshots")
    
    latest = snapshots[0]
    
    # 2. 恢复环境
    restore_git_status(latest.git_status)
    restore_env_vars(latest.env_vars)
    start_services(latest.running_services)
    
    # 3. 恢复编辑器状态 (需编辑器协作)
    restore_editor_state(latest.active_files, latest.cursor_positions)
    
    # 4. 注入决策/约束上下文
    inject_decisions(latest.recent_decisions)
    inject_constraints(latest.active_constraints)
    
    # 5. 设置工作假设
    set_working_hypothesis(latest.working_hypothesis)
    
    return RestoreReport(
        restored=True,
        snapshot_id=latest.id,
        restored_items=["git", "env", "services", "editor", "decisions", "constraints", "hypothesis"]
    )
```

### 3.2 手动恢复 (切换快照)
```bash
# 列出可用快照
snapshot list --session current

# 恢复指定快照
snapshot restore snap-20260808-003

# 查看快照差异
snapshot diff snap-20260808-001 snap-20260808-003
```

---

## 4. 版本管理与归档

### 4.1 快照索引
```json
{
  "version": "1.0",
  "snapshots": [
    {"id": "snap-20260808-001", "session": "sess-abc", "trigger": "phase_change", "time": "2026-08-08T10:00:00Z", "tags": ["plan->prd"]},
    {"id": "snap-20260808-002", "session": "sess-abc", "trigger": "decision", "time": "2026-08-08T10:30:00Z", "tags": ["decision", "adr-003"]}
  ],
  "by_session": {"sess-abc": ["snap-001", "snap-002"]},
  "by_tag": {"milestone": ["snap-003"], "decision": ["snap-002", "snap-005"]}
}
```

### 4.2 归档策略
| 策略 | 触发 | 动作 |
|------|------|------|
| 会话级保留 | 会话活跃 | 保留所有 |
| 最近 N 个 | 会话结束 | 保留最近 10 个 |
| 标签保留 | 标签 milestone/decision | 永久保留 |
| 时间归档 | > 30 天 | 移至 `.senate/memory/snapshots/archive/YYYY-MM/` |
| 压缩 | 归档时 | gzip + 移除大字段 (cursor_positions 等) |

### 4.3 版本对比
```python
def diff_snapshots(snap1: ContextSnapshot, snap2: ContextSnapshot) -> DiffReport:
    return DiffReport(
        git_diff=diff_dict(snap1.git_status, snap2.git_status),
        task_diff=diff_dict(snap1.task_progress, snap2.task_progress),
        decisions_added=set(snap2.recent_decisions) - set(snap1.recent_decisions),
        decisions_removed=set(snap1.recent_decisions) - set(snap2.recent_decisions),
        constraints_changed=diff_list(snap1.active_constraints, snap2.active_constraints),
        files_changed=diff_list(snap1.active_files, snap2.active_files)
    )
```

---

## 5. 交接/协作场景

### 5.1 会话交接
```bash
# 生成交接包
snapshot handoff --output handoff-20260808.json

# 包含:
# - 最新快照
# - 关键决策/约束摘要
# - 待办事项
# - 环境启动脚本
```

### 5.2 团队协作
```bash
# 导出共享快照 (去除敏感信息)
snapshot export --sanitize --output team-checkpoint.json

# 团队成员导入
snapshot import team-checkpoint.json --merge
```

---

## 5. 存储结构

```
.senate/memory/snapshots/
├── index.json                    # 总索引
├── snap-20260808-001.json        # 快照文件
├── snap-20260808-002.json
└── archive/
    ├── 2026-07/
    │   ├── snap-20260715-001.json.gz
    │   └── index.json
    └── 2026-08/
        └── ...
```

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08