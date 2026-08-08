# 上下文快照：捕獲/恢復/歸檔/版本管理

> 編排器：`../SKILL.md`　上位：編排器 §5 調度規則

---

## 1. 快照定義

### 1.1 觸發時機
| 觸發器 | 說明 | 優先級 |
|--------|------|--------|
| 會話結束 | 用戶退出 / 會話超時 | 高 |
| 階段切換 | 編排器階段轉換 (plan→prd→exec...) | 高 |
| 手動觸發 | 用戶執行 `/snapshot` | 中 |
| 關鍵決策後 | 記錄 ADR/關鍵約束後 | 中 |
| 錯誤/異常 | 捕獲錯誤上下文用於事後分析 | 低 |

### 1.2 快照內容
```python
@dataclass
class ContextSnapshot:
    id: str                         # snap-{timestamp}-{seq}
    session_id: str                 # 歸屬會話
    trigger: str                    # manual | phase_change | session_end | decision | error
    timestamp: str                  # ISO 8601
    
    # 任務上下文
    current_task: Optional[str]     # 當前任務描述
    task_progress: Dict             # {task_id: status}
    active_files: List[str]         # 當前打開/編輯的文件
    cursor_positions: Dict[str, int] # 文件光標位置
    
    # 決策/記憶上下文
    recent_decisions: List[str]     # 近期決策 ID
    active_constraints: List[str]   # 生效約束 ID
    working_hypothesis: str         # 當前工作假設/調試方向
    
    # 環境狀態
    git_status: Dict                # {branch, commit, dirty_files}
    env_vars: Dict[str, str]        # 關鍵環境變量
    running_services: List[str]     # 本地運行的服務
    
    # 元數據
    tags: List[str]                 # checkpoint | milestone | debugging | handoff
    metadata: Dict                  # 擴展字段
```

---

## 2. 捕獲流程

### 2.1 自動捕獲 (會話結束/階段切換)
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
    
    # 3. 關聯決策/約束
    for dec_id in snap.recent_decisions:
        link_snapshot_decision(snap.id, dec_id)
    
    return snap
```

### 2.2 手動快照
```bash
# 用戶命令
/snapshot "完成 API 設計，準備進入實現階段"
# 或
/snapshot --tag milestone "Phase 1 完成"
```

---

## 3. 恢復流程

### 3.1 會話啟動自動恢復
```python
def restore_on_session_start(session_id: str) -> RestoreReport:
    # 1. 找到最近的有效快照
    snapshots = list_snapshots(session_id=session_id, limit=5)
    if not snapshots:
        return RestoreReport(restored=False, reason="no_snapshots")
    
    latest = snapshots[0]
    
    # 2. 恢復環境
    restore_git_status(latest.git_status)
    restore_env_vars(latest.env_vars)
    start_services(latest.running_services)
    
    # 3. 恢復編輯器狀態 (需編輯器協作)
    restore_editor_state(latest.active_files, latest.cursor_positions)
    
    # 4. 注入決策/約束上下文
    inject_decisions(latest.recent_decisions)
    inject_constraints(latest.active_constraints)
    
    # 5. 設置工作假設
    set_working_hypothesis(latest.working_hypothesis)
    
    return RestoreReport(
        restored=True,
        snapshot_id=latest.id,
        restored_items=["git", "env", "services", "editor", "decisions", "constraints", "hypothesis"]
    )
```

### 3.2 手動恢復 (切換快照)
```bash
# 列出可用快照
snapshot list --session current

# 恢復指定快照
snapshot restore snap-20260808-003

# 查看快照差異
snapshot diff snap-20260808-001 snap-20260808-003
```

---

## 4. 版本管理與歸檔

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

### 4.2 歸檔策略
| 策略 | 觸發 | 動作 |
|------|------|------|
| 會話級保留 | 會話活躍 | 保留所有 |
| 最近 N 個 | 會話結束 | 保留最近 10 個 |
| 標簽保留 | 標簽 milestone/decision | 永久保留 |
| 時間歸檔 | > 30 天 | 移至 `.senate/memory/snapshots/archive/YYYY-MM/` |
| 壓縮 | 歸檔時 | gzip + 移除大字段 (cursor_positions 等) |

### 4.3 版本對比
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

## 5. 交接/協作場景

### 5.1 會話交接
```bash
# 生成交接包
snapshot handoff --output handoff-20260808.json

# 包含:
# - 最新快照
# - 關鍵決策/約束摘要
# - 待辦事項
# - 環境啟動腳本
```

### 5.2 團隊協作
```bash
# 導出共享快照 (去除敏感信息)
snapshot export --sanitize --output team-checkpoint.json

# 團隊成員導入
snapshot import team-checkpoint.json --merge
```

---

## 5. 存儲結構

```
.senate/memory/snapshots/
├── index.json                    # 總索引
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

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08