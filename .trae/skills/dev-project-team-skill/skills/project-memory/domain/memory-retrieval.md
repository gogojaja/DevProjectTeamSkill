# 記憶檢索：混合檢索(向量+關鍵詞+圖)/重排序/上下文注入

> 編排器：`../SKILL.md`　上位：編排器 §5 調度規則

---

## 1. 檢索架構

```
用戶查詢
    │
    ├─→ 意圖識別 (Intent Classifier)
    │       ├─ fact: 事實查詢 → 向量 + 關鍵詞
    │       ├─ decision: 決策查詢 → ProjectMemory + 標籤
    │       ├─ impact: 影響分析 → KnowledgeGraph
    │       ├─ context: 上下文恢復 → ContextSnapshot
    │       └─ todo: 待辦查詢 → Notepad
    │
    ├─→ 並行檢索
    │       ├─ Vector Search (語義相似)
    │       ├─ Keyword Search (BM25/關鍵詞)
    │       ├─ Graph Traversal (圖鄰域)
    │       └─ Structured Filter (類型/標籤/時間)
    │
    ├─→ 候選融合 (Reciprocal Rank Fusion)
    │
    ├─→ 重排序
    │       ├─ Cross-Encoder 精排
    │       ├─ 業務權重 (決策>約束>觀察)
    │       ├─ 時間衰減 (近期優先)
    │       └─ 來源可信度 (architect > user)
    │
    └─→ 上下文注入
            ├─ 截斷適配 Token 預算
            ├─ 格式化注入模板
            └─ 附帶引用來源
```

---

## 2. 多路檢索器

### 2.1 向量檢索
```python
class VectorRetriever:
    def __init__(self, index_path: str, embed_model: str = "bge-small-zh"):
        self.index = faiss.read_index(index_path)
        self.embedder = Embedder(embed_model)
        self.id_map = load_id_map()  # faiss_id -> memory_id
    
    def search(self, query: str, k: int = 20, filter_fn=None) -> List[RetrievalResult]:
        vec = self.embedder.encode(query)
        scores, ids = self.index.search(vec, k)
        results = []
        for score, faiss_id in zip(scores[0], ids[0]):
            if faiss_id == -1: continue
            mem_id = self.id_map[faiss_id]
            if filter_fn and not filter_fn(mem_id):
                continue
            results.append(RetrievalResult(
                id=mem_id, score=float(score), source="vector"
            ))
        return results
```

### 2.2 關鍵詞檢索 (BM25)
```python
class KeywordRetriever:
    def __init__(self, corpus_path: str):
        self.bm25 = BM25Okapi(build_corpus(corpus_path))
        self.id_map = load_corpus_id_map()
    
    def search(self, query: str, k: int = 20, filter_fn=None) -> List[RetrievalResult]:
        tokens = tokenize(query)
        scores = self.bm25.get_scores(tokens)
        top_k = np.argsort(scores)[-k:][::-1]
        results = []
        for idx in top_k:
            mem_id = self.id_map[idx]
            if filter_fn and not filter_fn(mem_id):
                continue
            results.append(RetrievalResult(
                id=mem_id, score=scores[idx], source="keyword"
            ))
        return results
```

### 2.3 圖鄰域檢索
```python
class GraphRetriever:
    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
    
    def search(self, query: str, seed_entities: List[str], k: int = 10, max_hops: int = 2) -> List[RetrievalResult]:
        # 1. 實體鏈接
        entities = link_entities(query, self.graph.nodes)
        seeds = entities + seed_entities
        
        # 2. 圖擴散
        visited = set()
        results = []
        for seed in seeds:
            for node_id, path in bfs(self.graph, seed, max_hops):
                if node_id in visited: continue
                visited.add(node_id)
                relevance = calculate_relevance(query, self.graph.nodes[node_id], path)
                results.append(RetrievalResult(
                    id=node_id, score=relevance, source="graph", path=path
                ))
        
        return sorted(results, key=lambda r: r.score, reverse=True)[:k]
```

### 2.4 結構化過濾
```python
class StructuredFilter:
    def filter(self, candidates: List[RetrievalResult], 
               types: List[str]=None, tags: List[str]=None,
               time_range: Tuple[str,str]=None, source: str=None) -> List[RetrievalResult]:
        filtered = []
        for c in candidates:
            mem = load_memory(c.id)
            if not mem: continue
            if types and mem.type not in types: continue
            if tags and not all(t in mem.tags for t in tags): continue
            if time_range and not (time_range[0] <= mem.timestamp <= time_range[1]): continue
            filtered.append(c)
        return filtered
```

---

## 3. 候選融合 (RRF)

### 3.1 Reciprocal Rank Fusion
```python
def rrf_fusion(result_lists: List[List[RetrievalResult]], k: int = 60) -> List[RetrievalResult]:
    """
    RRF: score = Σ 1 / (k + rank_i)
    """
    scores = defaultdict(float)
    sources = defaultdict(list)
    
    for results in result_lists:
        for rank, r in enumerate(results):
            scores[r.id] += 1.0 / (k + rank + 1)
            sources[r.id].append(r.source)
    
    fused = []
    for mem_id, score in sorted(scores.items(), key=lambda x: -x[1]):
        fused.append(RetrievalResult(
            id=mem_id, score=score, source="+".join(set(sources[mem_id]))
        ))
    
    return fused
```

### 3.2 加權融合 (可選)
```python
WEIGHTS = {"vector": 0.4, "keyword": 0.3, "graph": 0.2, "filter": 0.1}

def weighted_fusion(result_lists: Dict[str, List[RetrievalResult]]) -> List[RetrievalResult]:
    scores = defaultdict(float)
    for source, results in result_lists.items():
        w = WEIGHTS.get(source, 0.1)
        for rank, r in enumerate(results):
            scores[r.id] += w * (1.0 / (rank + 1))
    # ... 同 RRF 排序
```

---

## 4. 重排序

### 4.1 Cross-Encoder 精排
```python
class CrossEncoderReranker:
    def __init__(self, model: str = "bge-reranker-base"):
        self.model = CrossEncoder(model)
    
    def rerank(self, query: str, candidates: List[RetrievalResult], top_k: int = 10) -> List[RetrievalResult]:
        if len(candidates) <= top_k:
            return candidates
        
        pairs = [(query, load_memory(c.id).content) for c in candidates]
        scores = self.model.predict(pairs)
        
        for c, score in zip(candidates, scores):
            c.rerank_score = float(score)
        
        return sorted(candidates, key=lambda x: x.rerank_score, reverse=True)[:top_k]
```

### 4.2 業務感知重排序
```python
def business_rerank(results: List[RetrievalResult], query_intent: str) -> List[RetrievalResult]:
    for r in results:
        mem = load_memory(r.id)
        base = r.rerank_score or r.score
        
        # 1. 類型權重
        type_weight = {
            "decision": 1.3, "constraint": 1.2, 
            "knowledge": 1.1, "observation": 1.0
        }.get(mem.type, 1.0)
        
        # 2. 置信度
        conf_weight = {"high": 1.2, "medium": 1.0, "low": 0.8}.get(mem.confidence, 1.0)
        
        # 3. 來源可信度
        source_weight = {
            "architect": 1.3, "planner": 1.1, "executor": 1.0, "user": 0.9
        }.get(mem.source, 1.0)
        
        # 4. 時間衰減 (半衰期 90 天)
        days_old = (now() - parse(mem.timestamp)).days
        time_decay = 0.5 ** (days_old / 90)
        
        # 5. 意圖匹配加成
        intent_bonus = 1.2 if matches_intent(mem, query_intent) else 1.0
        
        r.final_score = base * type_weight * conf_weight * source_weight * time_decay * intent_bonus
    
    return sorted(results, key=lambda x: x.final_score, reverse=True)
```

---

## 5. 上下文注入

### 5.1 Token 預算管理
```python
def inject_context(
    query: str,
    results: List[RetrievalResult],
    token_budget: int = 4000,  # 預留給用戶查詢+回複
    template: str = "default"
) -> InjectedContext:
    """將檢索結果注入上下文，控制 Token 消耗"""
    
    # 1. 估算各結果 Token
    for r in results:
        mem = load_memory(r.id)
        r.tokens = estimate_tokens(format_memory(mem, template))
    
    # 2. 貪心選擇 (按 final_score 降序，直到填滿預算)
    selected = []
    used = 0
    for r in results:
        if used + r.tokens > token_budget:
            break
        selected.append(r)
        used += r.tokens
    
    # 3. 格式化注入
    context_blocks = []
    for r in selected:
        mem = load_memory(r.id)
        block = format_memory(mem, template)
        block += f"\n[來源: {mem.id} | 類型: {mem.type} | 置信度: {mem.confidence} | 分數: {r.final_score:.3f}]"
        context_blocks.append(block)
    
    return InjectedContext(
        query=query,
        blocks=context_blocks,
        total_tokens=used,
        count=len(selected),
        template=template
    )
```

### 5.2 注入模板
```python
TEMPLATES = {
    "default": """## {title}
{content}
標籤: {tags}
類型: {type} | 置信度: {confidence} | 來源: {source} | 時間: {timestamp}""",
    
    "compact": "[{type}] {title}: {content[:200]}... ({tags})",
    
    "decision": """### 決策: {title}
**內容**: {content}
**依據**: {metadata.get('rationale', 'N/A')}
**狀態**: {metadata.get('status', 'active')} | 置信度: {confidence}""",
    
    "graph": """實體: {title} (類型: {props.type})
關係: {edges_summary}
屬性: {props}""",
}
```

---

## 6. 評估指標

### 6.1 離線評估
```python
def evaluate_retrieval(test_set: List[TestCase]) -> EvalMetrics:
    """TestCase: {query, relevant_ids[], intent}"""
    mrr = 0
    hit_at_k = {1: 0, 3: 0, 5: 0, 10: 0}
    
    for tc in test_set:
        results = retrieve(tc.query, intent=tc.intent)
        ranked_ids = [r.id for r in results]
        
        # MRR
        for i, rid in enumerate(ranked_ids):
            if rid in tc.relevant_ids:
                mrr += 1.0 / (i + 1)
                break
        
        # Hit@K
        for k in hit_at_k:
            if any(rid in tc.relevant_ids for rid in ranked_ids[:k]):
                hit_at_k[k] += 1
    
    n = len(test_set)
    return EvalMetrics(
        mrr=mrr/n,
        hit_at_1=hit_at_k[1]/n,
        hit_at_3=hit_at_k[3]/n,
        hit_at_5=hit_at_k[5]/n,
        hit_at_10=hit_at_k[10]/n
    )
```

### 6.2 線上指標
| 指標 | 目標 | 說明 |
|------|------|------|
| 檢索延遲 P99 | < 200ms | 端到端 |
| 重排序延遲 P99 | < 100ms | Cross-Encoder 批量 |
| 上下文注入 Token 利用率 | > 80% | 預算使用率 |
| 用戶滿意度 | > 4.0/5.0 | 顯式反饋 |

---

## 7. API 介面

```python
class MemoryRetrievalAPI:
    def __init__(self):
        self.vector = VectorRetriever(...)
        self.keyword = KeywordRetriever(...)
        self.graph = GraphRetriever(...)
        self.filter = StructuredFilter()
        self.reranker = CrossEncoderReranker()
        self.injector = ContextInjector()
    
    def retrieve(
        self,
        query: str,
        intent: str = "auto",
        types: List[str] = None,
        tags: List[str] = None,
        time_range: Tuple[str,str] = None,
        top_k: int = 10,
        token_budget: int = 4000,
        template: str = "default"
    ) -> RetrievalResponse:
        # 1. 意圖識別
        if intent == "auto":
            intent = classify_intent(query)
        
        # 2. 並行檢索
        vector_r = self.vector.search(query, k=50)
        keyword_r = self.keyword.search(query, k=50)
        graph_r = self.graph.search(query, [], k=20)
        
        # 3. 融合
        fused = rrf_fusion([vector_r, keyword_r, graph_r])
        
        # 4. 過濾
        filtered = self.filter.filter(fused, types=types, tags=tags)
        
        # 5. 重排序
        reranked = self.reranker.rerank(query, filtered, top_k=top_k*2)
        final = business_rerank(reranked, intent)
        
        # 6. 截斷 + 注入
        injected = self.injector.inject_context(query, final[:top_k], token_budget)
        
        return RetrievalResponse(
            query=query,
            intent=intent,
            results=injected.blocks,
            total_candidates=len(fused),
            returned=len(selected),
            tokens_used=injected.total_tokens,
            metadata={"sources": [r.source for r in selected]}
        )
```

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08