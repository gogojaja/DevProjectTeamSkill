# 代碼質量驗證：風格/複雜度/覆蓋/異味/最佳實踐

> 編排器：`../SKILL.md`

---

## 1. 驗證範疇

| 類別 | 檢查點 | 工具 | 閾值 |
|------|--------|------|------|
| 風格一致性 | 縮進/命名/格式/導入排序 | ruff/black/eslint/prettier | 0 error |
| 圈複雜度 | 函數/類/模塊複雜度 | radon/eslint/complexity | ≤15 (函數) / ≤50 (類) |
| 測試覆蓋 | 行/分支/條件覆蓋率 | coverage.py/nyc/jacoco | 行≥80% 分支≥70% |
| 代碼異味 | 長函數/大類/重複/神類/參數過多 | sonar/sonarqube/custom | 0 critical |
| 最佳實踐 | 錯誤處理/日誌/類型提示/文檔字符串 | 自定義規則 | 0 high |
| 安全編碼 | 輸入驗證/輸出編碼/密鑰管理 | bandit/semgrep/sast | 0 high/critical |

---

## 2. 核心檢查清單

### 2.1 風格與格式 (CR-001)
```python
def check_style(codebase: str, config: StyleConfig) -> CheckResult:
    """統一風格：縮進/引號/尾隨逗號/導入排序/類型提示"""
    # ruff (Python) / eslint + prettier (JS/TS) / gofmt (Go)
    result = run_linter(codebase, config.linter)
    
    errors = [e for e in result.issues if e.severity == "error"]
    warnings = [w for w in result.issues if w.severity == "warning"]
    
    return CheckResult(
        id="CR-001",
        status="PASS" if not errors else "FAIL",
        evidence=[f"{e.file}:{e.line}: {e.message}" for e in errors],
        severity="high" if errors else "low"
    )
```

### 2.2 圈複雜度 (CR-002)
```python
def check_complexity(codebase: str, thresholds: ComplexityThresholds) -> CheckResult:
    """函數/類/模塊複雜度"""
    violations = []
    
    for func in extract_functions(codebase):
        cc = cyclomatic_complexity(func)
        if cc > thresholds.function_max:
            violations.append(f"{func.name}: CC={cc} > {thresholds.function_max}")
    
    for cls in extract_classes(codebase):
        wmc = weighted_methods_per_class(cls)
        if wmc > thresholds.class_max:
            violations.append(f"{cls.name}: WMC={wmc} > {thresholds.class_max}")
    
    return CheckResult(
        id="CR-002",
        status="PASS" if not violations else "FAIL",
        evidence=violations,
        severity="high" if any("CC=" in v and int(v.split("CC=")[1].split(" ")[0]) > 25 for v in violations) else "medium"
    )
```

### 2.3 測試覆蓋率 (CR-003)
```python
def check_test_coverage(coverage_data: CoverageData, thresholds: CoverageThresholds) -> CheckResult:
    """行/分支/條件覆蓋率"""
    issues = []
    
    if coverage_data.line_rate < thresholds.line_min:
        issues.append(f"Line coverage: {coverage_data.line_rate:.1%} < {thresholds.line_min:.1%}")
    
    if coverage_data.branch_rate < thresholds.branch_min:
        issues.append(f"Branch coverage: {coverage_data.branch_rate:.1%} < {thresholds.branch_min:.1%}")
    
    # 關鍵路徑覆蓋
    for critical in identify_critical_paths():
        if critical.coverage < 0.9:
            issues.append(f"Critical path {critical.name}: {critical.coverage:.1%} < 90%")
    
    return CheckResult(
        id="CR-003",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high" if any("line" in i or "branch" in i for i in issues) else "medium"
    )
```

### 2.4 代碼異味 (CR-004)
```python
def check_code_smells(codebase: str) -> CheckResult:
    """長函數/大類/重複代碼/神類/長參數列表"""
    smells = []
    
    for func in extract_functions(codebase):
        if func.lines > 50:
            smells.append(f"Long function: {func.name} ({func.lines} lines)")
        if len(func.params) > 5:
            smells.append(f"Long parameter list: {func.name} ({len(func.params)} params)")
    
    for cls in extract_classes(codebase):
        if cls.methods_count > 20:
            smells.append(f"Large class: {cls.name} ({cls.methods_count} methods)")
        if cls.lines > 500:
            smells.append(f"Large class: {cls.name} ({cls.lines} lines)")
    
    # 重複代碼 (sonarqube/duplication detector)
    duplications = detect_duplication(codebase, min_lines=10, min_tokens=100)
    for dup in duplications:
        if dup.similarity > 0.8:
            smells.append(f"Duplication: {dup.locations} ({dup.similarity:.0%})")
    
    return CheckResult(
        id="CR-004",
        status="PASS" if not smells else "FAIL",
        evidence=smells,
        severity="medium"
    )
```

### 2.5 最佳實踐與錯誤處理 (CR-005)
```python
def check_best_practices(codebase: str) -> CheckResult:
    """錯誤處理/日誌/類型提示/文檔/資源管理"""
    issues = []
    
    for func in extract_functions(codebase):
        # 異常處理
        if func.raises_exceptions and not func.has_try_except:
            issues.append(f"{func.name}: raises but no try/except")
        
        # 類型提示
        if not func.has_type_hints:
            issues.append(f"Missing type hints: {func.name}")
        
        # 文檔字符串
        if func.is_public and not func.has_docstring:
            issues.append(f"Missing docstring: {func.name}")
        
        # 資源洩漏 (文件/連接/鎖)
        if func.acquires_resources and not func.releases_resources:
            issues.append(f"Resource leak risk: {func.name}")
    
    return CheckResult(id="CR-005", status="PASS" if not issues else "FAIL", evidence=issues, severity="medium")
```

### 2.6 安全編碼 (CR-006)
```python
def check_secure_coding(codebase: str) -> CheckResult:
    """輸入驗證/輸出編碼/密鑰/注入防護"""
    # bandit (Python) / semgrep (多語言) / CodeQL
    result = run_security_linter(codebase)
    
    critical = [i for i in result.issues if i.severity == "critical"]
    high = [i for i in result.issues if i.severity == "high"]
    
    return CheckResult(
        id="CR-006",
        status="PASS" if not critical and not high else "FAIL",
        evidence=[f"{i.file}:{i.line} {i.message}" for i in critical + high],
        severity="critical" if critical else ("high" if high else "low")
    )
```

---

## 3. 工具鏈與配置

| 語言 | 風格 | 複雜度 | 覆蓋率 | 異味/重複 | 安全 |
|------|------|--------|--------|-----------|------|
| Python | ruff/black | radon | coverage.py | sonar-python/bandit | bandit/semgrep |
| TypeScript/JS | eslint/prettier | eslint-complexity | nyc/jest | eslint/sonarjs | semgrep/CodeQL |
| Go | gofmt/gofumpt | gocyclo | go test -cover | govet/gocritic | gosec |
| Java | google-java-format | checkstyle | jacoco | spotbugs/pmd | spotbugs/CodeQL |
| Rust | rustfmt | cargo-complexity | cargo-tarpaulin | clippy | cargo-audit |

---

## 4. 門禁閾值 (可配置)

```yaml
# .code-quality.yml
thresholds:
  complexity:
    function_max: 15
    class_max: 50
    module_max: 200
  coverage:
    line_min: 0.80
    branch_min: 0.70
    critical_path_min: 0.90
  style:
    max_line_length: 100
    error_tolerance: 0
  smells:
    max_function_lines: 50
    max_class_methods: 20
    max_class_lines: 500
    max_params: 5
    duplication_threshold: 0.8
```

---

## 5. 輸出報告格式

```json
{
  "perspective": "code_reviewer",
  "checks": [
    {"id": "CR-001", "name": "風格一致性", "status": "PASS", "evidence": [], "severity": "high"},
    {"id": "CR-002", "name": "圈複雜度", "status": "FAIL", "evidence": ["UserService.getUser: CC=18 > 15"], "severity": "high"},
    {"id": "CR-003", "name": "測試覆蓋率", "status": "PASS", "evidence": ["line=85% branch=72%"], "severity": "high"},
    {"id": "CR-004", "name": "代碼異味", "status": "FAIL", "evidence": ["Long function: processOrder (68 lines)"], "severity": "medium"},
    {"id": "CR-005", "name": "最佳實踐", "status": "PASS", "evidence": [], "severity": "medium"},
    {"id": "CR-006", "name": "安全編碼", "status": "PASS", "evidence": [], "severity": "critical"}
  ],
  "summary": "2 項違規：圈複雜度超標 1 處、長函數 1 處，建議重構",
  "confidence": "high",
  "tokens_used": 1500
}
```

---

## 6. 門禁策略

| 嚴重性 | 門禁行為 | 可例外 |
|----------|----------|--------|
| critical | 直接阻斷 | 否 |
| high | 阻斷 (可配置例外) | 是 (legacy/third-party) |
| medium | 警告 (不阻斷) | 是 |
| low | 僅報告 | 是 |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08