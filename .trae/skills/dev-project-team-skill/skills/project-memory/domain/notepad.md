# Notepad 轻量工作记忆

> 编排器：`../SKILL.md`　上位：编排器 §5 调度规则

---

## 1. 设计目标

| 特性 | ProjectMemory | Notepad |
|------|---------------|---------|
| 持久化 | 永久 (JSONL + 向量) | 会话/短期 (内存 + 可选落盘) |
| 向量化 | 是 (语义检索) | 否 (关键词/标签) |
| 结构 | 丰富 (类型/标签/关联/嵌入) | 极简 (类型/内容/TTL) |
| 读写延迟 | ~ms (含向量) | <1ms (纯内存) |
| 适用场景 | 决策/约束/长期知识 | 会话临时笔记/观察/待办 |

---

## 1. 数据模型

### 1.1 笔记类型
```python
NOTE_TYPES = {
    "working": {"ttl": "session", "desc": "正在进行的工作内容、代码片段、调试信息"},
    "observation": {"ttl": "7d", "desc": "运行时观察、性能数据、异常现象"},
    "todo": {"ttl": "30d", "desc": "待办事项、后续跟进行动"},
    "scratch": {"ttl": "1h", "desc": "极短期草稿、计算过程、临时记录"},
}
```

### 1.2 笔记结构
```python
@dataclass
class Note:
    id: str                     # note-{timestamp}-{seq}
    type: str                   # working | observation | todo | scratch
    title: str                  # 可选，自动从内容首行生成
    content: str                # 纯文本/Markdown
    tags: List[str]             # 可选标签
    session_id: str             # 归属会话
    created_at: str             # ISO 8601
    expires_at: Optional[str]   # TTL 到期时间
    metadata: Dict              # 任意扩展
```

---

## 2. 存储引擎

### 2.1 内存优先 + 可选持久化
```python
class Notepad:
    def __init__(self, session_id: str, persist_path: str = None):
        self.session_id = session_id
        self.persist_path = persist_path or f".senate/memory/notepad-{session_id}.json"
        self.notes: Dict[str, Note] = {}
        self._load()
    
    def _load(self):
        if os.path.exists(self.persist_path):
            with open(self.persist_path, "r") as f:
                data = json.load(f)
                self.notes = {k: Note(**v) for k, v in data.items()}
                # 清理过期
                self._cleanup_expired()
    
    def _save(self):
        # 原子写入
        data = {k: asdict(v) for k, v in self.notes.items()}
        atomic_write(self.persist_path, json.dumps(data, ensure_ascii=False, indent=2))
```

### 2.2 核心操作 (<1ms)
```python
def write(self, type: str, content: str, title: str = "", tags: List[str] = None, ttl: str = None) -> str:
    note = Note(
        id=f"note-{time.time_ns()}",
        type=type,
        title=title or content[:50],
        content=content,
        tags=tags or [],
        session_id=self.session_id,
        created_at=datetime.now().isoformat(),
        expires_at=calculate_ttl(type, ttl),
    )
    self.notes[note.id] = note
    self._save_async()  # 非阻塞
    return note.id

def read(self, note_id: str) -> Optional[Note]:
    note = self.notes.get(note_id)
    if note and note.expires_at and note.expires_at < now():
        self.delete(note_id)
        return None
    return note

def search(self, query: str = "", type: str = None, tags: List[str] = None, limit: int = 20) -> List[Note]:
    results = []
    for note in self.notes.values():
        if note.expires_at and note.expires_at < now():
            continue
        if type and note.type != type:
            continue
        if tags and not all(t in note.tags for t in tags):
            continue
        if query and query.lower() not in (note.title + note.content).lower():
            continue
        results.append(note)
    return sorted(results, key=lambda n: n.created_at, reverse=True)[:limit]

def delete(self, note_id: str) -> bool:
    if note_id in self.notes:
        del self.notes[note_id]
        self._save_async()
        return True
    return False

def cleanup_expired(self):
    now = datetime.now().isoformat()
    expired = [k for k, v in self.notes.items() if v.expires_at and v.expires_at < now]
    for k in expired:
        del self.notes[k]
    if expired:
        self._save()
```

---

## 3. TTL 管理

### 3.1 TTL 计算
```python
def calculate_ttl(note_type: str, custom_ttl: str = None) -> Optional[str]:
    if custom_ttl:
        return parse_ttl(custom_ttl)
    
    defaults = {
        "working": "session",     # 会话结束清理
        "observation": "7d",      # 7 天
        "todo": "30d",            # 30 天
        "scratch": "1h",          # 1 小时
    }
    ttl_str = defaults.get(note_type, "session")
    
    if ttl_str == "session":
        return None  # 不设过期，会话结束由外部清理
    
    return (datetime.now() + parse_duration(ttl_str)).isoformat()
```

### 3.2 自动清理
```python
# 会话结束时调用
def on_session_end(session_id: str):
    path = f".senate/memory/notepad-{session_id}.json"
    if os.path.exists(path):
        os.remove(path)  # working/scratch 直接删除

# 定时任务 (每小时)
def periodic_cleanup():
    for path in glob(".senate/memory/notepad-*.json"):
        notepad = Notepad("", path)
        notepad.cleanup_expired()
        if not notepad.notes:
            os.remove(path)
```

---

## 4. 会话隔离

### 4.1 会话级命名空间
```
.senate/memory/
├── notepad-sess-abc123.json    # 会话 abc123 的笔记
├── notepad-sess-def456.json    # 会话 def456 的笔记
└── notepad-global.json         # 跨会话共享 (可选)
```

### 4.2 跨会话共享 (可选)
```python
def share_note(note_id: str, target_session: str = "global"):
    """将笔记复制到另一会话或全局"""
    source = Notepad(current_session)
    note = source.read(note_id)
    if note:
        target = Notepad(target_session)
        new_id = target.write(note.type, note.content, note.title, note.tags)
        return new_id
```

---

## 4. CLI 介面

```bash
# 写入
note "working" "正在修复 UserService N+1 查询" --tags debug,performance
note "observation" "API 响应 P99 从 200ms 降到 50ms" --tags api,optimization
note "todo" "补全 ADR-012 选型文档" --ttl 30d

# 读取/搜索
note list --type working
note search "N+1" --tags debug
note read <note-id>

# 删除/清理
note delete <note-id>
note cleanup --session current
```

---

## 5. 与 ProjectMemory 协作

### 5.1 升级机制
```python
def promote_to_memory(note_id: str, memory_type: str = "observation"):
    """将成熟的笔记升级为长期记忆"""
    notepad = Notepad(current_session)
    note = notepad.read(note_id)
    if note:
        memory_id = write_memory(
            type=memory_type,
            title=note.title,
            content=note.content,
            tags=note.tags + ["promoted-from-notepad"],
            source=f"notepad:{current_session}"
        )
        # 标记已升级
        note.metadata["promoted_to"] = memory_id
        notepad._save()
        return memory_id
```

### 5.2 降级/引用
```python
def reference_memory(memory_id: str) -> str:
    """在 notepad 中引用长期记忆"""
    mem = read_memory(memory_id)
    if mem:
        return notepad.write("working", f"[Ref: {memory_id}] {mem.title}\n{mem.content}", tags=["ref"])
```

---

## 6. 性能指标

| 操作 | 耗时 | 说明 |
|------|------|------|
| 写入 | <0.5ms | 内存字典 + 异步落盘 |
| 读取 | <0.1ms | 字典查找 |
| 搜索 | <1ms | 线性扫描 (通常 <100 条) |
| TTL 清理 | <5ms | 批量删除 |

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08