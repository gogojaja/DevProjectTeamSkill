# ProjectMemory 存儲引擎

> 編排器：`../SKILL.md`　上位：編排器 §5 調度規則

---

## 1. 存儲架構

```
.senate/memory/
├── project-memory.jsonl      # 決策/約束 (JSONL, 追加寫入)
├── project-memory.idx        # 向量索引 (FAISS/Annoy)
├── project-memory.meta       # 元數據 (統計/版本/校驗和)
└── archive/                  # 歸檔 (按年月分區)
    ├── 2026-07/
    └── 2026-08/
```

---

## 2. 數據模型

### 2.1 記憶條目
```python
@dataclass
class MemoryEntry:
    id: str                     # mem-{timestamp}-{seq}
    type: str                   # decision | constraint | knowledge | observation
    title: str                  # 簡短標題 (≤100字)
    content: str                # 完整內容 (Markdown)
    tags: List[str]             # 搜索標籤
    confidence: str             # high | medium | low
    source: str                 # 來源角色: architect/planner/executor/user
    timestamp: str              # ISO 8601
    links: List[str]            # 關聯記憶 ID
    embedding: Optional[List[float]]  # 向量嵌入 (768 維)
    metadata: Dict              # 擴展字段
```

### 2.2 文件格式 (JSONL)
```jsonl
{"id":"mem-20260808-001","type":"decision","title":"選擇 PostgreSQL","content":"...","tags":["arch","db"],"confidence":"high","source":"architect","timestamp":"2026-08-08T10:00:00Z","links":[],"embedding":null}
{"id":"mem-20260808-002","type":"constraint","title":"單表行數限制","content":"單表不超過 100M 行...","tags":["db","performance"],"confidence":"high","source":"architect","timestamp":"2026-08-08T10:15:00Z","links":["mem-20260808-001"],"embedding":null}
```

---

## 3. 核心操作

### 3.1 寫入 (Append-only)
```python
def write_memory(entry: MemoryEntry) -> str:
    # 1. 生成 ID
    entry.id = f"mem-{entry.timestamp[:10].replace('-','')}-{next_seq()}"
    
    # 2. 向量化 (可選，異步)
    if entry.content and not entry.embedding:
        entry.embedding = embed_async(entry.title + "\n" + entry.content)
    
    # 3. 追加寫入 JSONL
    with open(PROJECT_MEMORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    
    # 4. 更新索引 (增量)
    if entry.embedding:
        index.add(entry.id, entry.embedding)
    
    # 5. 更新元數據
    update_meta(count=+1, last_id=entry.id)
    
    return entry.id
```

### 3.2 讀取/查詢
```python
def query_memory(
    query: str = "",
    types: List[str] = None,
    tags: List[str] = None,
    time_range: Tuple[str, str] = None,
    limit: int = 10,
    use_vector: bool = True
) -> List[MemoryEntry]:
    
    candidates = []
    
    # 1. 向量檢索 (語義相似)
    if use_vector and query:
        vector = embed(query)
        vector_results = index.search(vector, k=limit*3)
        candidates.extend(load_entries(vector_results.ids))
    
    # 2. 關鍵詞過濾 (標題/內容/標籤)
    if tags or types:
        keyword_results = scan_jsonl(filter_fn=lambda e: 
            (not types or e.type in types) and 
            (not tags or any(t in e.tags for t in tags))
        )
        candidates.extend(keyword_results)
    
    # 3. 時間範圍過濾
    if time_range:
        candidates = [e for e in candidates if time_range[0] <= e.timestamp <= time_range[1]]
    
    # 4. 去重 + 重排序
    unique = deduplicate(candidates)
    ranked = rerank(unique, query)  # 向量相似度 + 關鍵詞匹配 + 時間衰減
    
    return ranked[:limit]
```

### 3.3 關聯鏈接
```python
def link_memories(source_id: str, target_id: str, relation: str = "related"):
    """建立雙向關聯"""
    for eid in [source_id, target_id]:
        entry = load_entry(eid)
        if target_id not in entry.links:
            entry.links.append(target_id)
            update_entry(entry)
```

---

## 4. 向量索引

### 4.1 嵌入模型
- **模型**：`bge-small-zh` / `all-MiniLM-L6-v2` (768/384 維)
- **離線**：本地推理，無外部依賴
- **批量**：寫入時異步批量嵌入

### 4.2 索引選型
| 數據量 | 索引類型 | 說明 |
|--------|----------|------|
| < 1k | 線性掃描 | 內存數組，無需索引 |
| 1k-10k | FAISS IndexFlatIP | 精確內積，內存 |
| 10k-100k | FAISS IVF+PQ | 量化壓縮，亞線性 |
| > 100k | Annoy / HNSW | 磁盤友好，近似 |

### 4.3 增量更新
```python
def incremental_index_update(new_entries: List[MemoryEntry]):
    vectors = [e.embedding for e in new_entries if e.embedding]
    ids = [e.id for e in new_entries if e.embedding]
    if vectors:
        index.add(np.array(vectors), ids)
        index.save(INDEX_PATH)
```

---

## 5. 歸檔與壓縮

### 5.1 歸檔策略
- **觸發**：文件 > 100MB 或 > 10k 條目
- **分區**：按月 `.senate/memory/archive/YYYY-MM/`
- **壓縮**：gzip + 移除 embedding (可從源文本重建)

### 5.2 歸檔流程
```python
def archive_old_entries(before_date: str):
    # 1. 讀取並分割
    current, archived = split_by_date(PROJECT_MEMORY_PATH, before_date)
    
    # 2. 壓縮歸檔
    archive_path = f"archive/{before_date[:7]}/project-memory.jsonl.gz"
    with gzip.open(archive_path, "wt") as f:
        for entry in archived:
            # 移除 embedding 減小體積
            entry.pop("embedding", None)
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # 3. 覆寫當前文件
    write_jsonl(current, PROJECT_MEMORY_PATH)
    
    # 4. 重建索引
    rebuild_index(current)
```

---

## 6. 一致性與備份

### 6.1 寫入一致性
- **單文件追加**：原子寫入 (O_APPEND + fsync)
- **索引異步**：寫入確認後異步更新索引
- **崩潰恢復**：啟動時檢查索引完整性，不一致則重建

### 6.2 備份策略
```yaml
backup:
  local: .senate/memory/backups/ (每日增量)
  git: 隨技能庫提交 (project-memory.jsonl 不入 git，索引入 git)
  remote: 可配置 S3/NAS (每週全量)
```

---

## 7. 性能基準

| 操作 | <1k | 1k-10k | 10k-100k |
|------|-----|--------|----------|
| 寫入 | <1ms | <5ms | <20ms |
| 向量查詢 | <5ms | <10ms | <50ms |
| 關鍵詞查詢 | <2ms | <10ms | <30ms |
| 索引重建 | <1s | <5s | <30s |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08