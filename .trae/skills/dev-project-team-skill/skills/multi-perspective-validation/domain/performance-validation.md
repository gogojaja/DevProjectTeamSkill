# 性能驗證：基準/負載/壓力/併發/資源/回歸

> 編排器：`../SKILL.md`

---

## 1. 驗證範疇

| 類別 | 指標 | 閾值示例 | 工具 |
|------|------|----------|------|
| 基準測試 | 單接口延遲/吞吐 | P99<200ms QPS>1000 | k6/locust/wrk/benchstat |
| 負載測試 | 持續負載下表現 | 目標 QPS 穩定運行 10min | k6/locust |
| 壓力測試 | 破壞點/優雅降級 | 2x 目標負載不崩潰 | k6/locust |
| 併發測試 | 並發用戶/連接/鎖爭用 | 無死鎖/超時<5% | k6/自定義 |
| 資源利用 | CPU/內存/磁盤/網絡/GC | CPU<70% 內存<80% 無洩漏 | prometheus/grafana/pprof |
| 數據庫性能 | 查詢延遲/連接池/鎖等待 | P99<50ms 無慢查詢 | EXPLAIN/pg_stat/pt-query-digest |
| 緩存命中 | 命中率/淘汰/一致性 | 命中率>95% | redis-cli/memcached-stats |
| 回歸檢測 | 版本間性能對比 | 無顯著退化 (>10%) | benchstat/自定義對比 |

---

## 2. 核心檢查清單

### 2.1 基準測試 (PERF-001)
```python
def run_benchmark(target: BenchmarkTarget, config: BenchmarkConfig) -> CheckResult:
    """單接口基準：延遲分位/吞吐/錯誤率"""
    # k6 腳本生成
    script = generate_k6_script(target, config)
    result = run_k6(script)
    
    issues = []
    
    # 延遲檢查
    for endpoint, metrics in result.endpoints.items():
        if metrics.p99 > config.thresholds.p99_max:
            issues.append(f"{endpoint}: P99={metrics.p99:.0f}ms > {config.thresholds.p99_max}ms")
        if metrics.p95 > config.thresholds.p95_max:
            issues.append(f"{endpoint}: P95={metrics.p95:.0f}ms > {config.thresholds.p95_max}ms")
        if metrics.error_rate > config.thresholds.error_rate_max:
            issues.append(f"{endpoint}: Error rate={metrics.error_rate:.2%} > {config.thresholds.error_rate_max:.2%}")
    
    # 吞吐檢查
    if result.overall_throughput < config.thresholds.min_throughput:
        issues.append(f"Throughput: {result.overall_throughput:.0f} req/s < {config.thresholds.min_throughput}")
    
    return CheckResult(
        id="PERF-001",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high"
    )
```

### 2.2 負載測試 (PERF-002)
```python
def run_load_test(scenario: LoadScenario) -> CheckResult:
    """持續負載：穩定性/資源/降級"""
    result = run_k6(scenario.script, duration=scenario.duration)
    
    issues = []
    
    # 穩定性：錯誤率不應隨時間增長
    if result.error_rate_trend > 0.01:  # 每分鐘錯誤率增長 >1%
        issues.append(f"Error rate growing: {result.error_rate_trend:.2%}/min")
    
    # 響應時間不應顯著漂移
    if result.latency_drift > 0.2:  # P99 漂移 >20%
        issues.append(f"Latency drift: {result.latency_drift:.1%}")
    
    # 資源穩定
    if result.memory_growth > 100_000_000:  # 100MB/小時
        issues.append(f"Memory leak suspected: {result.memory_growth/1e6:.0f}MB/h")
    
    # CPU 利用率合理
    if result.cpu_avg > 85:
        issues.append(f"CPU saturation: {result.cpu_avg:.0f}%")
    
    return CheckResult(
        id="PERF-002",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high"
    )
```

### 2.3 壓力測試 (PERF-003)
```python
def run_stress_test(target: StressTarget) -> CheckResult:
    """破壞點/優雅降級/恢復能力"""
    # 階梯式加壓
    result = run_step_stress(target)
    
    issues = []
    
    # 破壞點識別
    breaking_point = find_breaking_point(result)
    if breaking_point.load_factor < target.min_load_factor:
        issues.append(f"Breaking point too low: {breaking_point.load_factor:.1f}x < {target.min_load_factor}x")
    
    # 優雅降級
    if not result.has_graceful_degradation:
        issues.append("No graceful degradation (circuit breaker/fallback/queue)")
    
    # 恢復能力
    recovery_time = measure_recovery(result)
    if recovery_time > target.max_recovery_time:
        issues.append(f"Recovery too slow: {recovery_time:.0f}s > {target.max_recovery_time}s")
    
    # 無數據丟失/損壞
    if result.data_integrity_issues:
        issues.append(f"Data integrity issues under stress: {result.data_integrity_issues}")
    
    return CheckResult(
        id="PERF-003",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high"
    )
```

### 2.3 併發與鎖分析 (PERF-004)
```python
def analyze_concurrency(target: ConcurrencyTarget) -> CheckResult:
    """併發用戶/連接池/鎖爭用/死鎖"""
    issues = []
    
    # 連接池
    pool_metrics = measure_connection_pool(target.db_pool)
    if pool_metrics.wait_time_p99 > 100:  # ms
        issues.append(f"DB pool wait P99: {pool_metrics.wait_time_p99}ms")
    if pool_metrics.usage_avg > 0.9:
        issues.append(f"Pool saturation: {pool_metrics.usage_avg:.0%}")
    
    # 鎖爭用
    lock_stats = analyze_locks(target.codebase)
    if lock_stats.contention_rate > 0.05:
        issues.append(f"Lock contention: {lock_stats.contention_rate:.1%}")
    if lock_stats.deadlocks > 0:
        issues.append(f"Deadlocks detected: {lock_stats.deadlocks}")
    
    # 併發用戶
    if target.max_concurrent_users < target.required_concurrent:
        issues.append(f"Max concurrent users: {target.max_concurrent_users} < {target.required_concurrent}")
    
    return CheckResult(
        id="PERF-004",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high"
    )
```

### 2.4 資源利用與洩漏 (PERF-005)
```python
def check_resource_usage(target: ResourceTarget) -> CheckResult:
    """CPU/內存/磁盤/網絡/GC/文件描述符"""
    issues = []
    
    # 內存
    if target.memory_rss > target.memory_limit * 0.85:
        issues.append(f"Memory usage: {target.memory_rss/1e9:.1f}GB > 85% limit")
    
    # GC 壓力
    gc_stats = analyze_gc(target.runtime)
    if gc_stats.pause_p99 > 100:  # ms
        issues.append(f"GC pause P99: {gc_stats.pause_p99}ms")
    if gc_stats.frequency > 1000:  # per minute
        issues.append(f"GC frequency: {gc_stats.frequency}/min")
    
    # 文件描述符
    if target.fd_usage > target.fd_limit * 0.8:
        issues.append(f"FD usage: {target.fd_usage}/{target.fd_limit}")
    
    # 磁盤 I/O
    if target.disk_latency_p99 > 10:  # ms
        issues.append(f"Disk latency P99: {target.disk_latency_p99}ms")
    
    return CheckResult(
        id="PERF-005",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high"
    )
```

### 2.5 數據庫性能 (PERF-006)
```python
def check_database_performance(db: DatabaseTarget) -> CheckResult:
    """查詢延遲/連接池/鎖等待/慢查詢/索引"""
    issues = []
    
    # 慢查詢
    slow_queries = find_slow_queries(db, threshold_ms=100)
    for sq in slow_queries[:10]:
        issues.append(f"Slow query: {sq.query[:100]}... ({sq.avg_time:.0f}ms, {sq.calls} calls)")
    
    # 連接池
    if db.pool_wait_p99 > 50:
        issues.append(f"Pool wait P99: {db.pool_wait_p99}ms")
    
    # 鎖等待
    if db.lock_wait_p99 > 10:
        issues.append(f"Lock wait P99: {db.lock_wait_p99}ms")
    
    # 缺失索引
    missing_indexes = find_missing_indexes(db)
    for idx in missing_indexes[:5]:
        issues.append(f"Missing index: {idx.table}.{idx.columns} (seq_scan={idx.seq_scans})")
    
    # 表膨脹
    bloat = find_table_bloat(db)
    for t in bloat[:3]:
        issues.append(f"Table bloat: {t.name} {t.bloat_ratio:.1%} waste")
    
    return CheckResult(
        id="PERF-006",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high"
    )
```

### 2.6 緩存效能 (PERF-007)
```python
def check_cache_performance(cache: CacheTarget) -> CheckResult:
    """命中率/淘汰/一致性/熱點"""
    issues = []
    
    if cache.hit_rate < 0.95:
        issues.append(f"Cache hit rate: {cache.hit_rate:.1%} < 95%")
    
    if cache.eviction_rate > cache.ops_per_sec * 0.1:
        issues.append(f"High eviction rate: {cache.eviction_rate}/s")
    
    if cache.memory_usage > cache.max_memory * 0.9:
        issues.append(f"Cache memory: {cache.memory_usage:.1%} of max")
    
    # 熱點 Key
    hot_keys = find_hot_keys(cache, top=5)
    for hk in hot_keys:
        if hk.ops_per_sec > cache.ops_per_sec * 0.3:
            issues.append(f"Hot key: {hk.key} ({hk.ops_per_sec:.0f} ops/s)")
    
    return CheckResult(
        id="PERF-007",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="medium"
    )
```

### 2.7 性能回歸檢測 (PERF-008)
```python
def detect_performance_regression(current: BenchmarkResult, baseline: BenchmarkResult, threshold: float = 0.10) -> CheckResult:
    """版本間性能對比：>10% 退化報警"""
    issues = []
    
    for endpoint in current.endpoints:
        if endpoint not in baseline.endpoints:
            continue
        
        cur = current.endpoints[endpoint]
        base = baseline.endpoints[endpoint]
        
        # P99 退化
        if cur.p99 > base.p99 * (1 + threshold):
            pct = (cur.p99 - base.p99) / base.p99 * 100
            issues.append(f"{endpoint}: P99 regressed {pct:.1f}% ({base.p99:.0f} -> {cur.p99:.0f}ms)")
        
        # 吞吐退化
        if cur.throughput < base.throughput * (1 - threshold):
            pct = (base.throughput - cur.throughput) / base.throughput * 100
            issues.append(f"{endpoint}: Throughput regressed {pct:.1f}%")
        
        # 錯誤率上升
        if cur.error_rate > base.error_rate + 0.01:
            issues.append(f"{endpoint}: Error rate increased {base.error_rate:.2%} -> {cur.error_rate:.2%}")
    
    return CheckResult(
        id="PERF-008",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high"
    )
```

---

## 4. 基準配置模板

```yaml
# .performance.yml
targets:
  api_gateway:
    p99_max: 200      # ms
    p95_max: 100
    min_throughput: 1000  # req/s
    error_rate_max: 0.001
  
  database:
    query_p99_max: 50
    pool_wait_max: 50
    lock_wait_max: 10
  
  cache:
    hit_rate_min: 0.95
    memory_max_pct: 0.90
  
  stress:
    min_load_factor: 2.0
    max_recovery_time: 30
    min_graceful_degradation: true

regression:
  threshold: 0.10  # 10%
  baseline_ref: "main"  # git ref
```

---

## 5. 輸出報告格式

```json
{
  "perspective": "performance",
  "checks": [
    {"id": "PERF-001", "name": "基準測試", "status": "PASS", "evidence": ["P99=45ms QPS=1200"], "severity": "high"},
    {"id": "PERF-002", "name": "負載測試", "status": "FAIL", "evidence": ["Memory growth: 150MB/h"], "severity": "high"},
    {"id": "PERF-003", "name": "壓力測試", "status": "PASS", "evidence": ["Breaking point: 3.2x"], "severity": "high"},
    {"id": "PERF-004", "name": "併發分析", "status": "PASS", "evidence": [], "severity": "high"},
    {"id": "PERF-005", "name": "資源利用", "status": "FAIL", "evidence": ["GC pause P99=150ms"], "severity": "high"},
    {"id": "PERF-006", "name": "數據庫性能", "status": "PASS", "evidence": [], "severity": "high"},
    {"id": "PERF-007", "name": "緩存效能", "status": "PASS", "evidence": [], "severity": "medium"},
    {"id": "PERF-008", "name": "回歸檢測", "status": "FAIL", "evidence": ["/api/users: P99 regressed 15%"], "severity": "high"}
  ],
  "summary": "發現內存增長疑似洩漏、GC 停頓超標、/api/orders 接口性能回歸 15%",
  "confidence": "high",
  "tokens_used": 2000
}
```

---

## 6. 門禁閾值

| 指標 | 閾值 | 嚴重性 | 門禁 |
|------|------|--------|------|
| P99 延遲 | <200ms (API) / <50ms (DB) | high | 阻斷 |
| 錯誤率 | <0.1% | high | 阻斷 |
| 內存增長 | <50MB/h | high | 阻斷 |
| GC 停頓 P99 | <100ms | high | 阻斷 |
| 緩存命中率 | >95% | medium | 警告 |
| 回歸閾值 | >10% 退化 | high | 阻斷 |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08