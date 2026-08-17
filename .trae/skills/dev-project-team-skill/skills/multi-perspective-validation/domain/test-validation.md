# 测试验证：覆盖/策略/断言/契约/E2E/测试金字塔

> 编排器：`../SKILL.md`

---

## 1. 验证范畴

| 维度 | 检查点 | 阈值 | 工具 |
|------|--------|------|------|
| 覆盖率 | 行/分支/条件/函数 | 行≥80% 分支≥70% | coverage/nyc/jacoco |
| 测试金字塔 | 单元/集成/契约/E2E 比例 | 70/20/10 | 统计分析 |
| 断言质量 | 断言数/类型/具体性/负面测试 | ≥2 断言/测试 | 静态分析 |
| 契约测试 | Provider/Consumer 一致性 | 100% 契约覆盖 | pact/spring-cloud-contract |
| E2E 覆盖 | 关键业务流程/用户旅程 | 核心流程 100% | cypress/playwright |
| 测试策略 | 分层/隔离/数据管理/并行/稳定性 | 文档化 + 自动化 | 文档审查 |
| 断言质量 | 具体/可读/单一职责/边界/异常 | ≥80% 符合规范 | 静态分析 |
| 测试数据 | 隔离/工厂/构建器/匿名化 | 无硬编码/可复用 | 代码审查 |

---

## 2. 核心检查清单

### 2.1 覆盖率达标 (TE-001)
```python
def check_coverage(coverage_data: CoverageData, thresholds: CoverageThresholds) -> CheckResult:
    """行/分支/条件/函数覆盖率"""
    issues = []
    
    if coverage_data.line_rate < thresholds.line_min:
        issues.append(f"Line coverage: {coverage_data.line_rate:.1%} < {thresholds.line_min:.1%}")
    
    if coverage_data.branch_rate < thresholds.branch_min:
        issues.append(f"Branch coverage: {coverage_data.branch_rate:.1%} < {thresholds.branch_min:.1%}")
    
    if coverage_data.function_rate < thresholds.function_min:
        issues.append(f"Function coverage: {coverage_data.function_rate:.1%} < {thresholds.function_min:.1%}")
    
    # 关键模块专项检查
    critical_modules = identify_critical_modules()
    for mod in critical_modules:
        mod_cov = coverage_data.get_module_coverage(mod)
        if mod_cov.line_rate < 0.9:
            issues.append(f"Critical module {mod}: line {mod_cov.line_rate:.1%} < 90%")
    
    # 未测试代码热点
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

### 2.2 测试金字塔比例 (TE-002)
```python
def check_test_pyramid(test_suite: TestSuite) -> CheckResult:
    """单元/集成/契约/E2E 比例"""
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

### 2.3 断言质量 (TE-003)
```python
def check_assertion_quality(tests: List[TestCase]) -> CheckResult:
    """断言数量/具体性/负面测试/边界/异常"""
    issues = []
    
    for test in tests:
        assertions = extract_assertions(test)
        
        # 断言数量
        if len(assertions) == 0:
            issues.append(f"No assertions: {test.name}")
        elif len(assertions) == 1 and test.complexity > "low":
            issues.append(f"Single assertion for complex test: {test.name}")
        
        # 具体性 (避免 assertTrue/assertFalse 等模糊断言)
        vague_assertions = [a for a in assertions if a.type in ["assertTrue", "assertFalse", "assertNotNull"]]
        if len(vague_assertions) > len(assertions) * 0.5:
            issues.append(f"Vague assertions >50%: {test.name}")
        
        # 负面测试
        if not test.has_negative_case and test.complexity != "trivial":
            issues.append(f"Missing negative case: {test.name}")
        
        # 边界值测试
        if test.involves_boundaries and not test.has_boundary_assertions:
            issues.append(f"Missing boundary assertions: {test.name}")
        
        # 异常路径
        if test.invokes_external and not test.has_exception_assertions:
            issues.append(f"Missing exception assertions: {test.name}")
    
    return CheckResult(
        id="TE-003",
        status="PASS" if not issues else "FAIL",
        evidence=issues[:20],  # 限制输出
        severity="medium"
    )
```

### 2.4 契约测试 (TE-004)
```python
def check_contract_tests(pacts: List[PactFile], provider_code: str) -> CheckResult:
    """Provider/Consumer 契约一致性"""
    issues = []
    
    for pact in pacts:
        # 1. 消费端期望
        consumer_expectations = extract_consumer_expectations(pact)
        
        # 2. 提供端实现
        provider_implementation = extract_provider_implementation(pact.provider, provider_code)
        
        # 3. 匹配验证
        for interaction in consumer_expectations:
            match = verify_interaction(interaction, provider_implementation)
            if not match.matched:
                issues.append(f"Contract mismatch: {interaction.description} -> {match.mismatches}")
        
        # 状态处理
        if pact.requires_state_setup and not has_state_handlers(provider_code, pact):
            issues.append(f"Missing state handlers for: {pact.consumer}")
    
    return CheckResult(
        id="TE-004",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high"
    )
```

### 2.5 E2E 覆盖 (TE-005)
```python
def check_e2e_coverage(e2e_tests: List[E2ETest], user_journeys: List[UserJourney]) -> CheckResult:
    """关键业务流程/用户旅程覆盖"""
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
    
    # 稳定性检查
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

### 2.6 测试策略文档 (TE-006)
```python
def check_test_strategy_docs(project_root: str) -> CheckResult:
    """测试策略文档：分层/隔离/数据/并行/稳定性"""
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

## 3. 测试数据管理检查 (TE-007)

```python
def check_test_data_management(codebase: str) -> CheckResult:
    """隔离/工厂/构建器/匿名化/无硬编码"""
    issues = []
    
    # 1. 硬编码测试数据
    hardcoded = find_hardcoded_test_data(codebase)
    for h in hardcoded:
        issues.append(f"Hardcoded test data: {h.file}:{h.line}")
    
    # 2. 测试数据工厂/构建器使用
    if not uses_test_factories(codebase):
        issues.append("No test factory/builder pattern detected")
    
    # 3. 数据隔离 (并行安全)
    if not has_test_isolation(codebase):
        issues.append("Missing test isolation (parallel unsafe)")
    
    # 4. 敏感数据匿名化
    pii_in_tests = find_pii_in_test_data(codebase)
    for p in pii_in_tests:
        issues.append(f"PII in test data: {p.file}:{p.line}")
    
    # 5. 测试数据清理
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

## 3. 门禁阈值

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

## 4. 输出报告格式

```json
{
  "perspective": "test_engineer",
  "checks": [
    {"id": "TE-001", "name": "覆盖率达标", "status": "PASS", "evidence": ["line=85% branch=72%"], "severity": "high"},
    {"id": "TE-002", "name": "测试金字塔", "status": "FAIL", "evidence": ["unit=55% < 60%"], "severity": "medium"},
    {"id": "TE-003", "name": "断言质量", "status": "FAIL", "evidence": ["Single assertion: testComplexFlow"], "severity": "medium"},
    {"id": "TE-004", "name": "契约测试", "status": "PASS", "evidence": [], "severity": "high"},
    {"id": "TE-005", "name": "E2E 覆盖", "status": "FAIL", "evidence": ["Missing E2E: checkout flow"], "severity": "high"},
    {"id": "TE-006", "name": "测试策略文档", "status": "PASS", "evidence": [], "severity": "low"},
    {"id": "TE-007", "name": "测试数据管理", "status": "PASS", "evidence": [], "severity": "medium"}
  ],
  "summary": "覆盖率达标，但金字塔比例失衡(单元过少)、缺少关键 E2E、部分测试断言过于简单",
  "confidence": "high",
  "tokens_used": 1800
}
```

---

## 5. 门禁策略

| 检查项 | 严重性 | 门禁 | 可例外 |
|----------|--------|------|--------|
| 行覆盖 < 80% | high | 阻断 | legacy 模块可豁免 |
| 分支覆盖 < 70% | high | 阻断 |  |
| 关键模块 < 90% | high | 阻断 |  |
| 无契约测试 | high | 阻断 | 新 API 必须有 |
| 关键旅程无 E2E | high | 阻断 | 已知风险可记录 |
| 金字塔失衡 | medium | 警告 | 可配置 |
| 断言质量 | medium | 警告 |  |

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08