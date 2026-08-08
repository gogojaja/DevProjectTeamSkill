# 測試驗證：覆蓋/策略/斷言/契約/E2E/測試金字塔

> 編排器：`../SKILL.md`

---

## 1. 驗證範疇

| 維度 | 檢查點 | 閾值 | 工具 |
|------|--------|------|------|
| 覆蓋率 | 行/分支/條件/函數 | 行≥80% 分支≥70% | coverage/nyc/jacoco |
| 測試金字塔 | 單元/集成/契約/E2E 比例 | 70/20/10 | 統計分析 |
| 斷言質量 | 斷言數/類型/具體性/負面測試 | ≥2 斷言/測試 | 靜態分析 |
| 契約測試 | Provider/Consumer 一致性 | 100% 契約覆蓋 | pact/spring-cloud-contract |
| E2E 覆蓋 | 關鍵業務流程/用戶旅程 | 核心流程 100% | cypress/playwright |
| 測試策略 | 分層/隔離/數據管理/並行/穩定性 | 文檔化 + 自動化 | 文檔審查 |
| 斷言質量 | 具體/可讀/單一職責/邊界/異常 | ≥80% 符合規範 | 靜態分析 |
| 测試數據 | 隔離/工廠/構建器/匿名化 | 無硬編碼/可復用 | 代碼審查 |

---

## 2. 核心檢查清單

### 2.1 覆蓋率達標 (TE-001)
```python
def check_coverage(coverage_data: CoverageData, thresholds: CoverageThresholds) -> CheckResult:
    """行/分支/條件/函數覆蓋率"""
    issues = []
    
    if coverage_data.line_rate < thresholds.line_min:
        issues.append(f"Line coverage: {coverage_data.line_rate:.1%} < {thresholds.line_min:.1%}")
    
    if coverage_data.branch_rate < thresholds.branch_min:
        issues.append(f"Branch coverage: {coverage_data.branch_rate:.1%} < {thresholds.branch_min:.1%}")
    
    if coverage_data.function_rate < thresholds.function_min:
        issues.append(f"Function coverage: {coverage_data.function_rate:.1%} < {thresholds.function_min:.1%}")
    
    # 關鍵模塊專項檢查
    critical_modules = identify_critical_modules()
    for mod in critical_modules:
        mod_cov = coverage_data.get_module_coverage(mod)
        if mod_cov.line_rate < 0.9:
            issues.append(f"Critical module {mod}: line {mod_cov.line_rate:.1%} < 90%")
    
    # 未測試代碼熱點
    untested_hotspots = find_untested_hotspots(coverage_data, top_n=10)
    for hs in untested_hotspots:
        issues.append(f"Untested hotspot: {hs.file} (complexity={hs.complexity}, changes={hs.churn})")
    
    return CheckResult(
        id="TE-001",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high" if any("line" in i or "branch" in i for i in issues) else "medium"
    )
```

### 2.2 測試金字塔比例 (TE-002)
```python
def check_test_pyramid(test_suite: TestSuite) -> CheckResult:
    """單元/集成/契約/E2E 比例"""
    total = len(test_suite.tests)
    if total == 0:
        return CheckResult(id="TE-002", status="FAIL", evidence=["No tests found"], severity="high")
    
    unit = sum(1 for t in test_suite.tests if t.type == "unit")
    integration = sum(1 for t in test_suite.tests if t.type == "integration")
    contract = sum(1 for t in test_suite.tests if t.type == "contract")
    e2e = sum(1 for t in test_suite.tests if t.type == "e2e")
    
    ratios = {
        "unit": unit / total,
        "integration": integration / total,
        "contract": contract / total,
        "e2e": e2e / total
    }
    
    issues = []
    # 理想：70/20/5/5 或 70/20/10/0
    if ratios["unit"] < 0.6:
        issues.append(f"Unit tests too low: {ratios['unit']:.1%} < 60%")
    if ratios["e2e"] > 0.15:
        issues.append(f"E2E tests too high: {ratios['e2e']:.1%} > 15% (slow/flaky)")
    if ratios["integration"] + ratios["contract"] < 0.15:
        issues.append(f"Integration+Contract too low: {(ratios['integration']+ratios['contract']):.1%}")
    
    return CheckResult(
        id="TE-002",
        status="PASS" if not issues else "FAIL",
        evidence=[f"Ratios: {ratios}"] + issues,
        severity="medium"
    )
```

### 2.3 斷言質量 (TE-003)
```python
def check_assertion_quality(tests: List[TestCase]) -> CheckResult:
    """斷言數量/具體性/負面測試/邊界/異常"""
    issues = []
    
    for test in tests:
        assertions = extract_assertions(test)
        
        # 斷言數量
        if len(assertions) == 0:
            issues.append(f"No assertions: {test.name}")
        elif len(assertions) == 1 and test.complexity > "low":
            issues.append(f"Single assertion for complex test: {test.name}")
        
        # 具體性 (避免 assertTrue/assertFalse 等模糊斷言)
        vague_assertions = [a for a in assertions if a.type in ["assertTrue", "assertFalse", "assertNotNull"]]
        if len(vague_assertions) > len(assertions) * 0.5:
            issues.append(f"Vague assertions >50%: {test.name}")
        
        # 負面測試
        if not test.has_negative_case and test.complexity != "trivial":
            issues.append(f"Missing negative case: {test.name}")
        
        # 邊界值測試
        if test.involves_boundaries and not test.has_boundary_assertions:
            issues.append(f"Missing boundary assertions: {test.name}")
        
        # 異常路徑
        if test.invokes_external and not test.has_exception_assertions:
            issues.append(f"Missing exception assertions: {test.name}")
    
    return CheckResult(
        id="TE-003",
        status="PASS" if not issues else "FAIL",
        evidence=issues[:20],  # 限制輸出
        severity="medium"
    )
```

### 2.4 契約測試 (TE-004)
```python
def check_contract_tests(pacts: List[PactFile], provider_code: str) -> CheckResult:
    """Provider/Consumer 契約一致性"""
    issues = []
    
    for pact in pacts:
        # 1. 消費端期望
        consumer_expectations = extract_consumer_expectations(pact)
        
        # 2. 提供端實現
        provider_implementation = extract_provider_implementation(pact.provider, provider_code)
        
        # 3. 匹配驗證
        for interaction in consumer_expectations:
            match = verify_interaction(interaction, provider_implementation)
            if not match.matched:
                issues.append(f"Contract mismatch: {interaction.description} -> {match.mismatches}")
        
        # 狀態處理
        if pact.requires_state_setup and not has_state_handlers(provider_code, pact):
            issues.append(f"Missing state handlers for: {pact.consumer}")
    
    return CheckResult(
        id="TE-004",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high"
    )
```

### 2.5 E2E 覆蓋 (TE-005)
```python
def check_e2e_coverage(e2e_tests: List[E2ETest], user_journeys: List[UserJourney]) -> CheckResult:
    """關鍵業務流程/用戶旅程覆蓋"""
    issues = []
    
    covered_journeys = set()
    for test in e2e_tests:
        for journey in test.covers_journeys:
            covered_journeys.add(journey.id)
    
    for journey in user_journeys:
        if journey.criticality == "critical" and journey.id not in covered_journeys:
            issues.append(f"Missing E2E for critical journey: {journey.name}")
        elif journey.criticality == "high" and journey.id not in covered_journeys:
            issues.append(f"Missing E2E for high-priority journey: {journey.name}")
    
    # 穩定性檢查
    flaky_tests = identify_flaky_e2e_tests()
    if flaky_tests:
        issues.append(f"Flaky E2E tests: {', '.join(flaky_tests[:5])}")
    
    return CheckResult(
        id="TE-005",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high" if any("critical" in i for i in issues) else "medium"
    )
```

### 2.6 測試策略文檔 (TE-006)
```python
def check_test_strategy_docs(project_root: str) -> CheckResult:
    """測試策略文檔：分層/隔離/數據/並行/穩定性"""
    required_sections = [
        "test_pyramid", "test_types", "data_management",
        "parallel_execution", "flaky_handling", "ci_integration",
        "coverage_targets", "test_environments"
    ]
    
    doc_path = find_test_strategy_doc(project_root)
    if not doc_path:
        return CheckResult(id="TE-006", status="FAIL", evidence=["Missing test strategy document"], severity="medium")
    
    content = read_doc(doc_path)
    missing = [s for s in required_sections if s.lower() not in content.lower()]
    
    return CheckResult(
        id="TE-006",
        status="PASS" if not missing else "FAIL",
        evidence=[f"Missing section: {s}" for s in missing],
        severity="low"
    )
```

---

## 3. 測試數據管理檢查 (TE-007)

```python
def check_test_data_management(codebase: str) -> CheckResult:
    """隔離/工廠/構建器/匿名化/無硬編碼"""
    issues = []
    
    # 1. 硬編碼測試數據
    hardcoded = find_hardcoded_test_data(codebase)
    for h in hardcoded:
        issues.append(f"Hardcoded test data: {h.file}:{h.line}")
    
    # 2. 測試數據工廠/構建器使用
    if not uses_test_factories(codebase):
        issues.append("No test factory/builder pattern detected")
    
    # 3. 數據隔離 (並行安全)
    if not has_test_isolation(codebase):
        issues.append("Missing test isolation (parallel unsafe)")
    
    # 4. 敏感數據匿名化
    pii_in_tests = find_pii_in_test_data(codebase)
    for p in pii_in_tests:
        issues.append(f"PII in test data: {p.file}:{p.line}")
    
    # 5. 測試數據清理
    if not has_cleanup_hooks(codebase):
        issues.append("Missing test data cleanup (afterEach/tearDown)")
    
    return CheckResult(
        id="TE-007",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="medium"
    )
```

---

## 3. 門禁閾值

```yaml
# .test-quality.yml
thresholds:
  coverage:
    line_min: 0.80
    branch_min: 0.70
    function_min: 0.75
    critical_module_min: 0.90
  
  pyramid:
    unit_min: 0.60
    integration_min: 0.15
    contract_min: 0.05
    e2e_max: 0.15
  
  assertions:
    min_per_test: 1
    vague_ratio_max: 0.5
    require_negative: true
    require_boundary: true
  
  contract:
    coverage_min: 1.0
  
  e2e:
    critical_journey_coverage: 1.0
    high_journey_coverage: 0.80
    flaky_rate_max: 0.05
```

---

## 4. 輸出報告格式

```json
{
  "perspective": "test_engineer",
  "checks": [
    {"id": "TE-001", "name": "覆蓋率達標", "status": "PASS", "evidence": ["line=85% branch=72%"], "severity": "high"},
    {"id": "TE-002", "name": "測試金字塔", "status": "FAIL", "evidence": ["unit=55% < 60%"], "severity": "medium"},
    {"id": "TE-003", "name": "斷言質量", "status": "FAIL", "evidence": ["Single assertion: testComplexFlow"], "severity": "medium"},
    {"id": "TE-004", "name": "契約測試", "status": "PASS", "evidence": [], "severity": "high"},
    {"id": "TE-005", "name": "E2E 覆蓋", "status": "FAIL", "evidence": ["Missing E2E: checkout flow"], "severity": "high"},
    {"id": "TE-006", "name": "測試策略文檔", "status": "PASS", "evidence": [], "severity": "low"},
    {"id": "TE-007", "name": "測試數據管理", "status": "PASS", "evidence": [], "severity": "medium"}
  ],
  "summary": "覆蓋率達標，但金字塔比例失衡(單元過少)、缺少關鍵 E2E、部分測試斷言過於簡單",
  "confidence": "high",
  "tokens_used": 1800
}
```

---

## 5. 門禁策略

| 檢查項 | 嚴重性 | 門禁 | 可例外 |
|----------|--------|------|--------|
| 行覆蓋 < 80% | high | 阻斷 | legacy 模塊可豁免 |
| 分支覆蓋 < 70% | high | 阻斷 |  |
| 關鍵模塊 < 90% | high | 阻斷 |  |
| 無契約測試 | high | 阻斷 | 新 API 必須有 |
| 關鍵旅程無 E2E | high | 阻斷 | 已知風險可記錄 |
| 金字塔失衡 | medium | 警告 | 可配置 |
| 斷言質量 | medium | 警告 |  |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08