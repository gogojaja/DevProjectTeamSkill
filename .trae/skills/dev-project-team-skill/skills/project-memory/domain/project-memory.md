# ProjectMemory 存储引擎

> 编排器：`../SKILL.md`　上位：编排器 §5 调度规则

---

## 1. 存储架构

```
.senate/memory/
├── project-memory.jsonl      # 决策/约束 (JSONL, 追加写入)
├── project-memory.idx        # 向量索引 (FAISS/Annoy)
├── project-memory.meta       # 元数据 (统计/版本/校验和)
└── archive/                  # 归档 (按年月分区)
    ├── 2026-07/
    └── 2026-08/
```

---

## 2. 数据模型

### 2.1 记忆条目
```python
@dataclass
class MemoryEntry:
    id: str                     # mem-{timestamp}-{seq}
    type: str                   # decision | constraint | knowledge | observation
    title: str                  # 简短标题 (≤100字)
    content: str                # 完整内容 (Markdown)
    tags: List[str]             # 搜索标签
    confidence: str             # high | medium | low
    source: str                 # 来源角色: architect/planner/executor/user
    timestamp: str              # ISO 8601
    links: List[str]            # 关联记忆 ID
    embedding: Optional[List[float]]  # 向量嵌入 (768 维)
    metadata: Dict              # 扩展字段
```

### 2.2 文件格式 (JSONL)
```jsonl
{"id":"mem-20260808-001","type":"decision","title":"选择 PostgreSQL","content":"...","tags":["arch","db"],"confidence":"high","source":"architect","timestamp":"2026-08-08T10:00:00Z","links":[],"embedding":null}
{"id":"mem-20260808-002","type":"constraint","title":"单表行数限制","content":"单表不超过 100M 行...","tags":["db","performance"],"confidence":"high","source":"architect","timestamp":"2026-08-08T10:15:00Z","links":["mem-20260808-001"],"embedding":null}
```

---

## 3. 核心操作

### 3.1 写入 (Append-only)
```python
def write_memory(entry: MemoryEntry) -> str:
    # 1. 生成 ID
    entry.id = f"mem-{entry.timestamp[:10].replace('-','')}-{next_seq()}"
    
    # 2. 向量化 (可选，异步)
    if entry.content and not entry.embedding:
        entry.embedding = embed_async(entry.title + "\n" + entry.content)
    
    # 3. 追加写入 JSONL
    with open(PROJECT_MEMORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    
    # 4. 更新索引 (增量)
    if entry.embedding:
        index.add(entry.id, entry.embedding)
    
    # 5. 更新元数据
    update_meta(count=+1, last_id=entry.id)
    
    return entry.id
```

### 3.2 读取/查询
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
    
    # 1. 向量检索 (语义相似)
    if use_vector and query:
        vector = embed(query)
        vector_results = index.search(vector, k=limit*3)
        candidates.extend(load_entries(vector_results.ids))
    
    # 2. 关键词过滤 (标题/内容/标签)
    if tags or types:
        keyword_results = scan_jsonl(filter_fn=lambda e: 
            (not types or e.type in types) and 
            (not tags or any(t in e.tags for t in tags))
        )
        candidates.extend(keyword_results)
    
    # 3. 时间范围过滤
    if time_range:
        candidates = [e for e in candidates if time_range[0] <= e.timestamp <= time_range[1]]
    
    # 4. 去重 + 重排序
    unique = deduplicate(candidates)
    ranked = rerank(unique, query)  # 向量相似度 + 关键词匹配 + 时间衰减
    
    return ranked[:limit]
```

### 3.3 关联链接
```python
def link_memories(source_id: str, target_id: str, relation: str = "related"):
    """建立双向关联"""
    for eid in [source_id, target_id]:
        entry = load_entry(eid)
        if target_id not in entry.links:
            entry.links.append(target_id)
            update_entry(entry)
```

---

## 4. 向量索引

### 4.1 嵌入模型
- **模型**：`bge-small-zh` / `all-MiniLM-L6-v2` (768/384 维)
- **离线**：本地推理，无外部依赖
- **批量**：写入时异步批量嵌入

### 4.2 索引选型
| 数据量 | 索引类型 | 说明 |
|--------|----------|------|
| < 1k | 线性扫描 | 内存数组，无需索引 |
| 1k-10k | FAISS IndexFlatIP | 精确内积，内存 |
| 10k-100k | FAISS IVF+PQ | 量化压缩，亚线性 |
| > 100k | Annoy / HNSW | 磁盘友好，近似 |

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

## 5. 归档与压缩

### 5.1 归档策略
- **触发**：文件 > 100MB 或 > 10k 条目
- **分区**：按月 `.senate/memory/archive/YYYY-MM/`
- **压缩**：gzip + 移除 embedding (可从源文本重建)

### 5.2 归档流程
```python
def archive_old_entries(before_date: str):
    # 1. 读取并分割
    current, archived = split_by_date(PROJECT_MEMORY_PATH, before_date)
    
    # 2. 压缩归档
    archive_path = f"archive/{before_date[:7]}/project-memory.jsonl.gz"
    with gzip.open(archive_path, "wt") as f:
        for entry in archived:
            # 移除 embedding 减小体积
            entry.pop("embedding", None)
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # 3. 覆写当前文件
    write_jsonl(current, PROJECT_MEMORY_PATH)
    
    # 4. 重建索引
    rebuild_index(current)
```

---

## 6. 一致性与备份

### 6.1 写入一致性
- **单文件追加**：原子写入 (O_APPEND + fsync)
- **索引异步**：写入确认后异步更新索引
- **崩溃恢复**：启动时检查索引完整性，不一致则重建

### 6.2 备份策略
```yaml
backup:
  local: .senate/memory/backups/ (每日增量)
  git: 随技能库提交 (project-memory.jsonl 不入 git，索引入 git)
  remote: 可配置 S3/NAS (每周全量)
```

---

## 7. 性能基准

| 操作 | <1k | 1k-10k | 10k-100k |
|------|-----|--------|----------|
| 写入 | <1ms | <5ms | <20ms |
| 向量查询 | <5ms | <10ms | <50ms |
| 关键词查询 | <2ms | <10ms | <30ms |
| 索引重建 | <1s | <5s | <30s |

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08