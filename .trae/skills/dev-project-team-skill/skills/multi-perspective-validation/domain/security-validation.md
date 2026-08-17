# 安全验证：威胁建模/扫描/认证授权/数据流/合规

> 编排器：`../SKILL.md`

---

## 1. 验证范畴

| 领域 | 检查点 | 工具 | 严重性 |
|------|--------|------|--------|
| 静态扫描 | SAST/语义分析/模式匹配 | semgrep/CodeQL/bandit | high/critical |
| 依赖漏洞 | CVE/供应链/许可证 | osv-scanner/dependabot/snyk | high/critical |
| 密钥管理 | 硬编码/泄漏/轮换/存储 | trufflehog/gitleaks | critical |
| 认证授权 | RBAC/ABAC/OAuth/JWT/会话 | 代码审查/自动化测试 | high |
| 输入验证 | 注入/XSS/路径遍历/反序列化 | semgrep/CodeQL/自定义规则 | high/critical |
| 数据流 | 敏感数据标记/加密/脱敏/最小权限 | 代码分析/数据血统 | high |
| 威胁建模 | STRIDE/攻击面/信任边界/缓解措施 | 威胁建模文档审查 | high |
| 合规 | GDPR/PCI-DSS/SOC2/行业标准 | 合规清单/自动化检查 | high |

---

## 2. 核心检查清单

### 2.1 静态应用安全测试 (SEC-001)
```python
def run_sast_scan(codebase: str, rulesets: List[str] = None) -> CheckResult:
    """SAST: semgrep + CodeQL + bandit"""
    all_findings = []
    
    # semgrep (快速、规则丰富)
    semgrep_result = run_semgrep(codebase, config="p/security-audit")
    all_findings.extend(normalize_findings(semgrep_result, "semgrep"))
    
    # CodeQL (深度、跨语言)
    codeql_result = run_codeql(codebase, queries="security-and-quality")
    all_findings.extend(normalize_findings(codeql_result, "codeql"))
    
    # bandit (Python 专用)
    if has_python_files(codebase):
        bandit_result = run_bandit(codebase)
        all_findings.extend(normalize_findings(bandit_result, "bandit"))
    
    # 按严重性分组
    critical = [f for f in all_findings if f.severity == "critical"]
    high = [f for f in all_findings if f.severity == "high"]
    
    return CheckResult(
        id="SEC-001",
        status="PASS" if not critical and not high else "FAIL",
        evidence=[f"{f.tool}:{f.rule_id} {f.file}:{f.line} {f.message}" for f in critical + high],
        severity="critical" if critical else ("high" if high else "low")
    )
```

### 2.2 依赖漏洞扫描 (SEC-002)
```python
def scan_dependencies(manifest_files: List[str]) -> CheckResult:
    """CVE/供应链/许可证"""
    # osv-scanner / dependabot / snyk / trivy
    result = run_osv_scanner(manifest_files)
    
    vulns = result.vulnerabilities
    critical = [v for v in vulns if v.severity == "CRITICAL"]
    high = [v for v in vulns if v.severity == "HIGH"]
    
    # 许可证风险
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

### 2.3 密钥泄漏检测 (SEC-003)
```python
def scan_secrets(codebase: str, history: bool = True) -> CheckResult:
    """硬编码密钥/API Key/Token/证书"""
    # trufflehog / gitleaks / detect-secrets
    findings = []
    
    # 扫描当前代码
    findings.extend(run_trufflehog(codebase, only_verified=True))
    
    # 扫描 Git 历史 (可选)
    if history:
        findings.extend(run_gitleaks(repo_path, max_depth=100))
    
    # 分类
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

### 2.4 认证授权验证 (SEC-004)
```python
def verify_authz(codebase: str, auth_config: AuthConfig) -> CheckResult:
    """RBAC/ABAC/OAuth/JWT/会话管理"""
    issues = []
    
    # 1. 所有端点有授权检查
    endpoints = extract_endpoints(codebase)
    for ep in endpoints:
        if not ep.has_auth_check and not ep.is_public:
            issues.append(f"Missing auth: {ep.method} {ep.path}")
    
    # 2. JWT 验证完整性
    jwt_usage = find_jwt_usage(codebase)
    for usage in jwt_usage:
        if not usage.validates_signature:
            issues.append(f"JWT missing signature validation: {usage.location}")
        if not usage.validates_expiry:
            issues.append(f"JWT missing expiry check: {usage.location}")
        if usage.algorithm in ["none", "HS256"] and usage.is_asymmetric_context:
            issues.append(f"Weak JWT algorithm: {usage.location}")
    
    # 3. 会话安全
    session_code = find_session_management(codebase)
    for sc in session_codes:
        if not sc.secure_flag: issues.append("Session cookie missing Secure flag")
        if not sc.httponly_flag: issues.append("Session cookie missing HttpOnly")
        if not sc.samesite: issues.append("Session cookie missing SameSite")
    
    # 4. 权限检查粒度
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

### 2.5 输入验证与注入防护 (SEC-005)
```python
def verify_input_validation(codebase: str) -> CheckResult:
    """SQL注入/XSS/命令注入/路径遍历/反序列化/XXE"""
    # semgrep 规则集: injection, xss, path-traversal, deserialization, xxe
    rulesets = ["injection", "xss", "path-traversal", "deserialization", "xxe"]
    findings = run_semgrep(codebase, config=rulesets)
    
    critical = [f for f in findings if f.severity == "critical"]
    high = [f for f in findings if f.severity == "high"]
    
    # 额外：输出编码检查 (XSS 防护)
    xss_findings = check_output_encoding(codebase)
    
    return CheckResult(
        id="SEC-005",
        status="PASS" if not critical and not high else "FAIL",
        evidence=[f"{f.rule_id} {f.file}:{f.line} {f.message}" for f in critical + high] +
                 [f"XSS: {x.file}:{x.line}" for x in xss_findings],
        severity="critical" if critical else ("high" if high else "low")
    )
```

### 2.6 敏感数据保护 (SEC-006)
```python
def verify_data_protection(codebase: str) -> CheckResult:
    """PII/敏感数据标记/加密/脱敏/日志泄漏/最小权限"""
    issues = []
    
    # 1. 硬编码敏感数据
    pii_patterns = find_pii_in_code(codebase)
    for p in pii_patterns:
        issues.append(f"PII in code: {p.file}:{p.line} ({p.type})")
    
    # 2. 日志敏感数据泄漏
    log_calls = find_logging_calls(codebase)
    for log in log_calls:
        if contains_sensitive(log.arguments):
            issues.append(f"Sensitive data in log: {log.file}:{log.line}")
    
    # 3. 加密存储/传输
    crypto_usage = find_crypto_usage(codebase)
    for cu in crypto_usage:
        if cu.algorithm in WEAK_ALGORITHMS:
            issues.append(f"Weak crypto: {cu.algorithm} at {cu.location}")
        if not cu.uses_tls and cu.is_network:
            issues.append(f"Missing TLS: {cu.location}")
    
    # 4. 数据保留/删除策略
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

## 3. 威胁建模审查 (SEC-007)

### 3.1 STRIDE 分析
```markdown
# 威胁建模审查清单

## S - Spoofing (身份冒充)
- [ ] 所有 API 端点强制认证
- [ ] JWT 签名验证不可绕过
- [ ] 会话 ID 不可预测/可枚举

## T - Tampering (篡改)
- [ ] 关键数据签名/哈希验证
- [ ] 参数完整性校验
- [ ] 文件上传类型/内容验证

## R - Repudiation (抵赖)
- [ ] 关键操作审计日志
- [ ] 日志不可篡改 (签名/写一次)
- [ ] 关键操作不可否认性

## I - Information Disclosure (信息泄漏)
- [ ] 错误信息不泄漏堆栈/内部结构
- [ ] 敏感数据加密存储/传输
- [ ] API 响应最小化原则

## D - Denial of Service (拒绝服务)
- [ ] 速率限制/配额
- [ ] 输入大小限制
- [ ] 并发连接限制

## E - Elevation of Privilege (权限提升)
- [ ] 最小权限原则
- [ ] 管理接口隔离/强认证
- [ ] 容器/进程最小权限运行
```

---

## 4. 合规检查清单

| 标准 | 关键要求 | 自动化程度 |
|------|----------|------------|
| GDPR | 数据最小化/同意/删除权/ DPIA | 半自动 |
| PCI-DSS | 卡数据加密/网络隔离/访问控制/日志 | 半自动 |
| SOC2 | 安全性/可用性/处理完整性/保密性/隐私 | 人工 |
| ISO 27001 | 风险评估/控制目标/持续改进 | 人工 |

---

## 5. 输出报告格式

```json
{
  "perspective": "security",
  "checks": [
    {"id": "SEC-001", "name": "静态扫描 (SAST)", "status": "PASS", "evidence": [], "severity": "critical"},
    {"id": "SEC-002", "name": "依赖漏洞", "status": "FAIL", "evidence": ["CVE-2024-1234 lodash@4.17.20 HIGH"], "severity": "high"},
    {"id": "SEC-003", "name": "密钥泄漏", "status": "PASS", "evidence": [], "severity": "critical"},
    {"id": "SEC-004", "name": "认证授权", "status": "PASS", "evidence": [], "severity": "high"},
    {"id": "SEC-005", "name": "输入验证/注入", "status": "PASS", "evidence": [], "severity": "critical"},
    {"id": "SEC-006", "name": "敏感数据保护", "status": "FAIL", "evidence": ["PII in log: user-service.log:42"], "severity": "high"},
    {"id": "SEC-007", "name": "威胁建模", "status": "PASS", "evidence": ["STRIDE 完整"], "severity": "high"}
  ],
  "summary": "发现 1 个依赖漏洞 (lodash) + 1 个日志泄漏 PII，建议升级依赖并清理日志",
  "confidence": "high",
  "tokens_used": 1200
}
```

---

## 6. 门禁阈值

| 严重性 | 门禁 | 例外处理 |
|----------|------|----------|
| critical (SAST/密钥/注入) | 0 容忍，直接阻断 | 仅允许已审计的第三方库 |
| high (依赖/认证/数据保护) | 阻断 | legacy 代码可申请豁免 (需风险接受单) |
| medium (合规/许可证) | 警告 | 可配置 |

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08