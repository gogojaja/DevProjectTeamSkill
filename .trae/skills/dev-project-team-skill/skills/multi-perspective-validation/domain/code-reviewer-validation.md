# 代码质量验证：风格/复杂度/覆盖/异味/最佳实践

> 编排器：`../SKILL.md`

---

## 1. 验证范畴

| 类别 | 检查点 | 工具 | 阈值 |
|------|--------|------|------|
| 风格一致性 | 缩进/命名/格式/导入排序 | ruff/black/eslint/prettier | 0 error |
| 圈复杂度 | 函数/类/模块复杂度 | radon/eslint/complexity | ≤15 (函数) / ≤50 (类) |
| 测试覆盖 | 行/分支/条件覆盖率 | coverage.py/nyc/jacoco | 行≥80% 分支≥70% |
| 代码异味 | 长函数/大类/重复/神类/参数过多 | sonar/sonarqube/custom | 0 critical |
| 最佳实践 | 错误处理/日志/类型提示/文档字符串 | 自定义规则 | 0 high |
| 安全编码 | 输入验证/输出编码/密钥管理 | bandit/semgrep/sast | 0 high/critical |

---

## 2. 核心检查清单

### 2.1 风格与格式 (CR-001)
```python
def check_style(codebase: str, config: StyleConfig) -> CheckResult:
    """统一风格：缩进/引号/尾随逗号/导入排序/类型提示"""
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

### 2.2 圈复杂度 (CR-002)
```python
def check_complexity(codebase: str, thresholds: ComplexityThresholds) -> CheckResult:
    """函数/类/模块复杂度"""
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

### 2.3 测试覆盖率 (CR-003)
```python
def check_test_coverage(coverage_data: CoverageData, thresholds: CoverageThresholds) -> CheckResult:
    """行/分支/条件覆盖率"""
    issues = []
    
    if coverage_data.line_rate < thresholds.line_min:
        issues.append(f"Line coverage: {coverage_data.line_rate:.1%} < {thresholds.line_min:.1%}")
    
    if coverage_data.branch_rate < thresholds.branch_min:
        issues.append(f"Branch coverage: {coverage_data.branch_rate:.1%} < {thresholds.branch_min:.1%}")
    
    # 关键路径覆盖
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

### 2.4 代码异味 (CR-004)
```python
def check_code_smells(codebase: str) -> CheckResult:
    """长函数/大类/重复代码/神类/长参数列表"""
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
    
    # 重复代码 (sonarqube/duplication detector)
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

### 2.5 最佳实践与错误处理 (CR-005)
```python
def check_best_practices(codebase: str) -> CheckResult:
    """错误处理/日志/类型提示/文档/资源管理"""
    issues = []
    
    for func in extract_functions(codebase):
        # 异常处理
        if func.raises_exceptions and not func.has_try_except:
            issues.append(f"{func.name}: raises but no try/except")
        
        # 类型提示
        if not func.has_type_hints:
            issues.append(f"Missing type hints: {func.name}")
        
        # 文档字符串
        if func.is_public and not func.has_docstring:
            issues.append(f"Missing docstring: {func.name}")
        
        # 资源泄漏 (文件/连接/锁)
        if func.acquires_resources and not func.releases_resources:
            issues.append(f"Resource leak risk: {func.name}")
    
    return CheckResult(id="CR-005", status="PASS" if not issues else "FAIL", evidence=issues, severity="medium")
```

### 2.6 安全编码 (CR-006)
```python
def check_secure_coding(codebase: str) -> CheckResult:
    """输入验证/输出编码/密钥/注入防护"""
    # bandit (Python) / semgrep (多语言) / CodeQL
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

## 3. 工具链与配置

| 语言 | 风格 | 复杂度 | 覆盖率 | 异味/重复 | 安全 |
|------|------|--------|--------|-----------|------|
| Python | ruff/black | radon | coverage.py | sonar-python/bandit | bandit/semgrep |
| TypeScript/JS | eslint/prettier | eslint-complexity | nyc/jest | eslint/sonarjs | semgrep/CodeQL |
| Go | gofmt/gofumpt | gocyclo | go test -cover | govet/gocritic | gosec |
| Java | google-java-format | checkstyle | jacoco | spotbugs/pmd | spotbugs/CodeQL |
| Rust | rustfmt | cargo-complexity | cargo-tarpaulin | clippy | cargo-audit |

---

## 4. 门禁阈值 (可配置)

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

## 5. 输出报告格式

```json
{
  "perspective": "code_reviewer",
  "checks": [
    {"id": "CR-001", "name": "风格一致性", "status": "PASS", "evidence": [], "severity": "high"},
    {"id": "CR-002", "name": "圈复杂度", "status": "FAIL", "evidence": ["UserService.getUser: CC=18 > 15"], "severity": "high"},
    {"id": "CR-003", "name": "测试覆盖率", "status": "PASS", "evidence": ["line=85% branch=72%"], "severity": "high"},
    {"id": "CR-004", "name": "代码异味", "status": "FAIL", "evidence": ["Long function: processOrder (68 lines)"], "severity": "medium"},
    {"id": "CR-005", "name": "最佳实践", "status": "PASS", "evidence": [], "severity": "medium"},
    {"id": "CR-006", "name": "安全编码", "status": "PASS", "evidence": [], "severity": "critical"}
  ],
  "summary": "2 项违规：圈复杂度超标 1 处、长函数 1 处，建议重构",
  "confidence": "high",
  "tokens_used": 1500
}
```

---

## 6. 门禁策略

| 严重性 | 门禁行为 | 可例外 |
|----------|----------|--------|
| critical | 直接阻断 | 否 |
| high | 阻断 (可配置例外) | 是 (legacy/third-party) |
| medium | 警告 (不阻断) | 是 |
| low | 仅报告 | 是 |

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08