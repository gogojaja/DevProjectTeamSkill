# Notepad 輕量工作記憶

> 編排器：`../SKILL.md`　上位：編排器 §5 調度規則

---

## 1. 設計目標

| 特性 | ProjectMemory | Notepad |
|------|---------------|---------|
| 持久化 | 永久 (JSONL + 向量) | 會話/短期 (內存 + 可選落盤) |
| 向量化 | 是 (語義檢索) | 否 (關鍵詞/標籤) |
| 結構 | 豐富 (類型/標籤/關聯/嵌入) | 極簡 (類型/內容/TTL) |
| 讀寫延遲 | ~ms (含向量) | <1ms (純內存) |
| 適用場景 | 決策/約束/長期知識 | 會話臨時筆記/觀察/待辦 |

---

## 1. 數據模型

### 1.1 筆記類型
```python
NOTE_TYPES = {
    "working": {"ttl": "session", "desc": "正在進行的工作內容、代碼片段、調試信息"},
    "observation": {"ttl": "7d", "desc": "運行時觀察、性能數據、異常現象"},
    "todo": {"ttl": "30d", "desc": "待辦事項、後續跟進行動"},
    "scratch": {"ttl": "1h", "desc": "極短期草稿、計算過程、臨時記錄"},
}
```

### 1.2 筆記結構
```python
@dataclass
class Note:
    id: str                     # note-{timestamp}-{seq}
    type: str                   # working | observation | todo | scratch
    title: str                  # 可選，自動從內容首行生成
    content: str                # 純文本/Markdown
    tags: List[str]             # 可選標籤
    session_id: str             # 歸屬會話
    created_at: str             # ISO 8601
    expires_at: Optional[str]   # TTL 到期時間
    metadata: Dict              # 任意擴展
```

---

## 2. 存儲引擎

### 2.1 內存優先 + 可選持久化
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
                # 清理過期
                self._cleanup_expired()
    
    def _save(self):
        # 原子寫入
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

### 3.1 TTL 計算
```python
def calculate_ttl(note_type: str, custom_ttl: str = None) -> Optional[str]:
    if custom_ttl:
        return parse_ttl(custom_ttl)
    
    defaults = {
        "working": "session",     # 會話結束清理
        "observation": "7d",      # 7 天
        "todo": "30d",            # 30 天
        "scratch": "1h",          # 1 小時
    }
    ttl_str = defaults.get(note_type, "session")
    
    if ttl_str == "session":
        return None  # 不設過期，會話結束由外部清理
    
    return (datetime.now() + parse_duration(ttl_str)).isoformat()
```

### 3.2 自動清理
```python
# 會話結束時調用
def on_session_end(session_id: str):
    path = f".senate/memory/notepad-{session_id}.json"
    if os.path.exists(path):
        os.remove(path)  # working/scratch 直接刪除

# 定時任務 (每小時)
def periodic_cleanup():
    for path in glob(".senate/memory/notepad-*.json"):
        notepad = Notepad("", path)
        notepad.cleanup_expired()
        if not notepad.notes:
            os.remove(path)
```

---

## 4. 會話隔離

### 4.1 會話級命名空間
```
.senate/memory/
├── notepad-sess-abc123.json    # 會話 abc123 的筆記
├── notepad-sess-def456.json    # 會話 def456 的筆記
└── notepad-global.json         # 跨會話共享 (可選)
```

### 4.2 跨會話共享 (可選)
```python
def share_note(note_id: str, target_session: str = "global"):
    """將筆記複製到另一會話或全局"""
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
# 寫入
note "working" "正在修復 UserService N+1 查詢" --tags debug,performance
note "observation" "API 響應 P99 從 200ms 降到 50ms" --tags api,optimization
note "todo" "補全 ADR-012 選型文檔" --ttl 30d

# 讀取/搜索
note list --type working
note search "N+1" --tags debug
note read <note-id>

# 刪除/清理
note delete <note-id>
note cleanup --session current
```

---

## 5. 與 ProjectMemory 協作

### 5.1 升級機制
```python
def promote_to_memory(note_id: str, memory_type: str = "observation"):
    """將成熟的筆記升級為長期記憶"""
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
        # 標記已升級
        note.metadata["promoted_to"] = memory_id
        notepad._save()
        return memory_id
```

### 5.2 降級/引用
```python
def reference_memory(memory_id: str) -> str:
    """在 notepad 中引用長期記憶"""
    mem = read_memory(memory_id)
    if mem:
        return notepad.write("working", f"[Ref: {memory_id}] {mem.title}\n{mem.content}", tags=["ref"])
```

---

## 6. 性能指標

| 操作 | 耗時 | 說明 |
|------|------|------|
| 寫入 | <0.5ms | 內存字典 + 異步落盤 |
| 讀取 | <0.1ms | 字典查找 |
| 搜索 | <1ms | 線性掃描 (通常 <100 條) |
| TTL 清理 | <5ms | 批量刪除 |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08