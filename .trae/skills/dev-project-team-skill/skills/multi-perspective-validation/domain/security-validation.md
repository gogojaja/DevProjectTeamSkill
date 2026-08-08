# 安全驗證：威脅建模/掃描/認證授權/數據流/合規

> 編排器：`../SKILL.md`

---

## 1. 驗證範疇

| 領域 | 檢查點 | 工具 | 嚴重性 |
|------|--------|------|--------|
| 靜態掃描 | SAST/語義分析/模式匹配 | semgrep/CodeQL/bandit | high/critical |
| 依賴漏洞 | CVE/供應鏈/許可證 | osv-scanner/dependabot/snyk | high/critical |
| 密鑰管理 | 硬編碼/洩漏/輪換/存儲 | trufflehog/gitleaks | critical |
| 認證授權 | RBAC/ABAC/OAuth/JWT/會話 | 代碼審查/自動化測試 | high |
| 輸入驗證 | 注入/XSS/路徑遍歷/反序列化 | semgrep/CodeQL/自定義規則 | high/critical |
| 數據流 | 敏感數據標記/加密/脫敏/最小權限 | 代碼分析/數據血統 | high |
| 威脅建模 | STRIDE/攻擊面/信任邊界/緩解措施 | 威脅建模文檔審查 | high |
| 合規 | GDPR/PCI-DSS/SOC2/行業標準 | 合規清單/自動化檢查 | high |

---

## 2. 核心檢查清單

### 2.1 靜態應用安全測試 (SEC-001)
```python
def run_sast_scan(codebase: str, rulesets: List[str] = None) -> CheckResult:
    """SAST: semgrep + CodeQL + bandit"""
    all_findings = []
    
    # semgrep (快速、規則豐富)
    semgrep_result = run_semgrep(codebase, config="p/security-audit")
    all_findings.extend(normalize_findings(semgrep_result, "semgrep"))
    
    # CodeQL (深度、跨語言)
    codeql_result = run_codeql(codebase, queries="security-and-quality")
    all_findings.extend(normalize_findings(codeql_result, "codeql"))
    
    # bandit (Python 專用)
    if has_python_files(codebase):
        bandit_result = run_bandit(codebase)
        all_findings.extend(normalize_findings(bandit_result, "bandit"))
    
    # 按嚴重性分組
    critical = [f for f in all_findings if f.severity == "critical"]
    high = [f for f in all_findings if f.severity == "high"]
    
    return CheckResult(
        id="SEC-001",
        status="PASS" if not critical and not high else "FAIL",
        evidence=[f"{f.tool}:{f.rule_id} {f.file}:{f.line} {f.message}" for f in critical + high],
        severity="critical" if critical else ("high" if high else "low")
    )
```

### 2.2 依賴漏洞掃描 (SEC-002)
```python
def scan_dependencies(manifest_files: List[str]) -> CheckResult:
    """CVE/供應鏈/許可證"""
    # osv-scanner / dependabot / snyk / trivy
    result = run_osv_scanner(manifest_files)
    
    vulns = result.vulnerabilities
    critical = [v for v in vulns if v.severity == "CRITICAL"]
    high = [v for v in vulns if v.severity == "HIGH"]
    
    # 許可證風險
    licenses = check_licenses(manifest_files)
    risky_licenses = [l for l in licenses if l in RISKY_LICENSES]
    
    return CheckResult(
        id="SEC-002",
        status="PASS" if not critical and not high and not risky_licenses else "FAIL",
        evidence=[f"{v.id} {v.package}@{v.version} {v.severity}" for v in critical + high] +
                 [f"License: {l}" for l in risky_licenses],
        severity="critical" if critical else ("high" if high else "medium")
    )
```

### 2.3 密鑰洩漏檢測 (SEC-003)
```python
def scan_secrets(codebase: str, history: bool = True) -> CheckResult:
    """硬編碼密鑰/API Key/Token/證書"""
    # trufflehog / gitleaks / detect-secrets
    findings = []
    
    # 掃描當前代碼
    findings.extend(run_trufflehog(codebase, only_verified=True))
    
    # 掃描 Git 歷史 (可選)
    if history:
        findings.extend(run_gitleaks(repo_path, max_depth=100))
    
    # 分類
    verified = [f for f in findings if f.verified]
    unverified = [f for f in findings if not f.verified]
    
    return CheckResult(
        id="SEC-003",
        status="PASS" if not verified else "FAIL",
        evidence=[f"{f.type} in {f.file}:{f.line}" for f in verified] +
                 [f"UNVERIFIED: {f.type} in {f.file}:{f.line}" for f in unverified[:5]],
        severity="critical" if verified else ("high" if unverified else "low")
    )
```

### 2.4 認證授權驗證 (SEC-004)
```python
def verify_authz(codebase: str, auth_config: AuthConfig) -> CheckResult:
    """RBAC/ABAC/OAuth/JWT/會話管理"""
    issues = []
    
    # 1. 所有端點有授權檢查
    endpoints = extract_endpoints(codebase)
    for ep in endpoints:
        if not ep.has_auth_check and not ep.is_public:
            issues.append(f"Missing auth: {ep.method} {ep.path}")
    
    # 2. JWT 驗證完整性
    jwt_usage = find_jwt_usage(codebase)
    for usage in jwt_usage:
        if not usage.validates_signature:
            issues.append(f"JWT missing signature validation: {usage.location}")
        if not usage.validates_expiry:
            issues.append(f"JWT missing expiry check: {usage.location}")
        if usage.algorithm in ["none", "HS256"] and usage.is_asymmetric_context:
            issues.append(f"Weak JWT algorithm: {usage.location}")
    
    # 3. 會話安全
    session_code = find_session_management(codebase)
    for sc in session_codes:
        if not sc.secure_flag: issues.append("Session cookie missing Secure flag")
        if not sc.httponly_flag: issues.append("Session cookie missing HttpOnly")
        if not sc.samesite: issues.append("Session cookie missing SameSite")
    
    # 4. 權限檢查粒度
    authz_checks = find_authorization_checks(codebase)
    for check in authz_checks:
        if check.is_coarse_grained:
            issues.append(f"Coarse-grained authz: {check.location}")
    
    return CheckResult(
        id="SEC-004",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high"
    )
```

### 2.5 輸入驗證與注入防護 (SEC-005)
```python
def verify_input_validation(codebase: str) -> CheckResult:
    """SQL注入/XSS/命令注入/路徑遍歷/反序列化/XXE"""
    # semgrep 規則集: injection, xss, path-traversal, deserialization, xxe
    rulesets = ["injection", "xss", "path-traversal", "deserialization", "xxe"]
    findings = run_semgrep(codebase, config=rulesets)
    
    critical = [f for f in findings if f.severity == "critical"]
    high = [f for f in findings if f.severity == "high"]
    
    # 額外：輸出編碼檢查 (XSS 防護)
    xss_findings = check_output_encoding(codebase)
    
    return CheckResult(
        id="SEC-005",
        status="PASS" if not critical and not high else "FAIL",
        evidence=[f"{f.rule_id} {f.file}:{f.line} {f.message}" for f in critical + high] +
                 [f"XSS: {x.file}:{x.line}" for x in xss_findings],
        severity="critical" if critical else ("high" if high else "low")
    )
```

### 2.6 敏感數據保護 (SEC-006)
```python
def verify_data_protection(codebase: str) -> CheckResult:
    """PII/敏感數據標記/加密/脫敏/日誌洩漏/最小權限"""
    issues = []
    
    # 1. 硬編碼敏感數據
    pii_patterns = find_pii_in_code(codebase)
    for p in pii_patterns:
        issues.append(f"PII in code: {p.file}:{p.line} ({p.type})")
    
    # 2. 日誌敏感數據洩漏
    log_calls = find_logging_calls(codebase)
    for log in log_calls:
        if contains_sensitive(log.arguments):
            issues.append(f"Sensitive data in log: {log.file}:{log.line}")
    
    # 3. 加密存儲/傳輸
    crypto_usage = find_crypto_usage(codebase)
    for cu in crypto_usage:
        if cu.algorithm in WEAK_ALGORITHMS:
            issues.append(f"Weak crypto: {cu.algorithm} at {cu.location}")
        if not cu.uses_tls and cu.is_network:
            issues.append(f"Missing TLS: {cu.location}")
    
    # 4. 數據保留/刪除策略
    retention = find_data_retention(codebase)
    for r in retention:
        if not r.has_policy:
            issues.append(f"Missing retention policy: {r.entity}")
    
    return CheckResult(
        id="SEC-006",
        status="PASS" if not issues else "FAIL",
        evidence=issues,
        severity="high"
    )
```

---

## 3. 威脅建模審查 (SEC-007)

### 3.1 STRIDE 分析
```markdown
# 威脅建模審查清單

## S - Spoofing (身份冒充)
- [ ] 所有 API 端點強制認證
- [ ] JWT 簽名驗證不可繞過
- [ ] 會話 ID 不可預測/可枚舉

## T - Tampering (篡改)
- [ ] 關鍵數據簽名/哈希驗證
- [ ] 參數完整性校驗
- [ ] 文件上傳類型/內容驗證

## R - Repudiation (抵賴)
- [ ] 關鍵操作審計日誌
- [ ] 日誌不可篡改 (簽名/寫一次)
- [ ] 關鍵操作不可否認性

## I - Information Disclosure (信息洩漏)
- [ ] 錯誤信息不洩漏堆棧/內部結構
- [ ] 敏感數據加密存儲/傳輸
- [ ] API 響應最小化原則

## D - Denial of Service (拒絕服務)
- [ ] 速率限制/配額
- [ ] 輸入大小限制
- [ ] 併發連接限制

## E - Elevation of Privilege (權限提升)
- [ ] 最小權限原則
- [ ] 管理接口隔離/強認證
- [ ] 容器/進程最小權限運行
```

---

## 4. 合規檢查清單

| 標準 | 關鍵要求 | 自動化程度 |
|------|----------|------------|
| GDPR | 數據最小化/同意/刪除權/ DPIA | 半自動 |
| PCI-DSS | 卡數據加密/網絡隔離/訪問控制/日誌 | 半自動 |
| SOC2 | 安全性/可用性/處理完整性/保密性/隱私 | 人工 |
| ISO 27001 | 風險評估/控制目標/持續改進 | 人工 |

---

## 5. 輸出報告格式

```json
{
  "perspective": "security",
  "checks": [
    {"id": "SEC-001", "name": "靜態掃描 (SAST)", "status": "PASS", "evidence": [], "severity": "critical"},
    {"id": "SEC-002", "name": "依賴漏洞", "status": "FAIL", "evidence": ["CVE-2024-1234 lodash@4.17.20 HIGH"], "severity": "high"},
    {"id": "SEC-003", "name": "密鑰洩漏", "status": "PASS", "evidence": [], "severity": "critical"},
    {"id": "SEC-004", "name": "認證授權", "status": "PASS", "evidence": [], "severity": "high"},
    {"id": "SEC-005", "name": "輸入驗證/注入", "status": "PASS", "evidence": [], "severity": "critical"},
    {"id": "SEC-006", "name": "敏感數據保護", "status": "FAIL", "evidence": ["PII in log: user-service.log:42"], "severity": "high"},
    {"id": "SEC-007", "name": "威脅建模", "status": "PASS", "evidence": ["STRIDE 完整"], "severity": "high"}
  ],
  "summary": "發現 1 個依賴漏洞 (lodash) + 1 個日誌洩漏 PII，建議升級依賴並清理日誌",
  "confidence": "high",
  "tokens_used": 1200
}
```

---

## 6. 門禁閾值

| 嚴重性 | 門禁 | 例外處理 |
|----------|------|----------|
| critical (SAST/密鑰/注入) | 0 容忍，直接阻斷 | 僅允許已審計的第三方庫 |
| high (依賴/認證/數據保護) | 阻斷 | legacy 代碼可申請豁免 (需風險接受單) |
| medium (合規/許可證) | 警告 | 可配置 |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08