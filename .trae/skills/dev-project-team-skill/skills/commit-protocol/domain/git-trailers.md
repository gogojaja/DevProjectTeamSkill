# Git Trailers 完整規範

> 編排器：`../SKILL.md`

---

## 1. Trailer 格式規範

### 1.1 基本語法
```
<Token>: <Value>
```
- Token 首字母大寫，單詞連接用連字符：`Signed-off-by` `Risk-Accepted`
- Value 不包含換行，長度建議 ≤ 100 字符
- 多個 Trailer 逐行排列，順序不敏感但建議按重要性排序

### 1.2 標準 Trailer 註冊表
| Token | 必填 | 可重複 | 語義 | 解析器支持 |
|-------|------|--------|------|------------|
| `Signed-off-by` | 是 | 是 | 開發者簽署 | Git 內建 |
| `Co-authored-by` | 否 | 是 | 協作作者 | GitHub/GitLab |
| `Constraint` | 否 | 是 | 活躍約束 | 自定義 |
| `Rejected` | 否 | 是 | 被拒替代方案 | 自定義 |
| `Directive` | 否 | 是 | 前瞻指令 | 自定義 |
| `Confidence` | 否 | 否 | 決策信心度 | 自定義 |
| `Scope-risk` | 否 | 否 | 風險範圍 | 自定義 |
| `Not-tested` | 否 | 是 | 未測試項 | 自定義 |
| `Risk-Accepted` | 否 | 是 | 風險接受單 ID | 自定義 |
| `ADR` | 否 | 是 | 架構決策引用 | 自定義 |
| `Fixes` | 否 | 是 | 修復 Issue | GitHub/GitLab |
| `Related` | 否 | 是 | 關聯 PR/提交 | 自定義 |
| `Breaking` | 否 | 是 | 破壞性變更標記 | 自定義 |
| `Depends-on` | 否 | 是 | 依賴其他提交 | 自定義 |

---

## 2. 標準 Trailer 詳細定義

### 2.1 Signed-off-by (強制)
```
Signed-off-by: Alice Chen <alice@example.com>
```
- **語義**：開發者確認有權提交、遵守 DCO/許可證
- **生成**：`git commit -s` 自動添加
- **驗證**：CI 強制檢查存在

### 2.2 Co-authored-by (協作)
```
Co-authored-by: Bob Wang <bob@example.com>
Co-authored-by: Carol Lee <carol@example.com>
```
- **語義**：標記協作貢獻者，顯示在 GitHub 提交頁
- **格式**：`Name <email>`

### 2.3 Constraint (約束)
```
Constraint: Single-table rows < 100M
Constraint: API response P99 < 200ms
Constraint: Must support PKCE for public clients
```
- **語義**：塑造決策的硬性約束（技術/業務/合規）
- **可重複**：是，每行一個約束
- **解析**：CI 可提取用於架構驗證

### 2.4 Rejected (被拒替代方案)
```
Rejected: MongoDB | ACID transactions not supported
Rejected: Custom JWT implementation | Maintenance burden
Rejected: SAML integration | Complexity exceeds value
```
- **格式**：`<alternative> | <reason>`
- **語義**：記錄決策過程中被拒絕的方案及理由
- **可重複**：是

### 2.5 Directive (前瞻指令)
```
Directive: Migrate to async IO in Q3
Directive: Add OIDC discovery endpoint in v2.2
Directive: Deprecate legacy API by 2026-Q4
```
- **語義**：給未來開發者的指令/警告/計劃
- **時效性**：建議包含時間範圍

### 2.6 Confidence (信心度)
```
Confidence: high
Confidence: medium
Confidence: low
```
- **取值**：`high` `medium` `low`
- **語義**：決策者對方案正確性的信心程度

### 2.7 Scope-risk (風險範圍)
```
Scope-risk: narrow
Scope-risk: moderate
Scope-risk: broad
```
- **取值**：`narrow` (單模塊) `moderate` (少數服務) `broad` (跨系統)
- **用途**：自動化風險評估、部署策略決策

### 2.8 Not-tested (未測試項)
```
Not-tested: E2E checkout flow with real payment gateway
Not-tested: Multi-region failover scenario
Not-tested: Load test > 10k concurrent users
```
- **語義**：已知的驗證缺口，風險透明化
- **可重複**：是

### 2.9 Risk-Accepted (風險接受)
```
Risk-Accepted: RA-20260808-001
Risk-Accepted: RA-20260805-003
```
- **格式**：`RA-YYYYMMDD-NNN`
- **語義**：引用風險接受單，表明風險已審批接受

### 2.10 ADR (架構決策記錄)
```
ADR: ADR-003
ADR: ADR-012
```
- **格式**：`ADR-<NNN>`
- **語義**：關聯架構決策記錄，便於追溯

### 2.11 Fixes / Related
```
Fixes: #1234
Related: #5678
Related: !456
```
- **Fixes**：GitHub/GitLab 自動關閉 Issue
- **Related**：關聯但不自動關閉

### 2.12 Breaking (破壞性變更)
```
Breaking: API v1 removed, migrate to v2
Breaking: Database schema changed, migration required
```
- **語義**：標記破壞性變更，觸發 Major 版本升級

---

## 3. Trailers 解析與驗證

### 3.1 解析器實現
```python
import re

TRAILER_PATTERN = re.compile(
    r'^(?P<token>[A-Za-z][A-Za-z0-9-]*):\s*(?P<value>.+)$'
)

def parse_trailers(commit_msg: str) -> Dict[str, List[str]]:
    """解析提交訊息中的 Trailers"""
    trailers = defaultdict(list)
    in_trailer_section = False
    
    for line in commit_msg.split('\n'):
        if not in_trailer_section:
            if line.strip() == '' or TRAILER_PATTERN.match(line):
                in_trailer_section = True
            else:
                continue
        
        m = TRAILER_PATTERN.match(line)
        if m:
            token = m.group('token')
            value = m.group('value').strip()
            trailers[token].append(value)
    
    return dict(trailers)

def validate_trailers(trailers: Dict[str, List[str]]) -> List[str]:
    """驗證 Trailers 完整性"""
    errors = []
    
    # 強制簽署
    if 'Signed-off-by' not in trailers:
        errors.append("Missing required trailer: Signed-off-by")
    
    # Confidence 值域
    if 'Confidence' in trailers:
        for v in trailers['Confidence']:
            if v not in ('high', 'medium', 'low'):
                errors.append(f"Invalid Confidence value: {v}")
    
    # Scope-risk 值域
    if 'Scope-risk' in trailers:
        for v in trailers['Scope-risk']:
            if v not in ('narrow', 'moderate', 'broad'):
                errors.append(f"Invalid Scope-risk value: {v}")
    
    # Risk-Accepted 格式
    if 'Risk-Accepted' in trailers:
        for v in trailers['Risk-Accepted']:
            if not re.match(r'^RA-\d{8}-\d{3}$', v):
                errors.append(f"Invalid Risk-Accepted format: {v}")
    
    # ADR 格式
    if 'ADR' in trailers:
        for v in trailers['ADR']:
            if not re.match(r'^ADR-\d{3,}$', v):
                errors.append(f"Invalid ADR format: {v}")
    
    return errors
```

---

## 4. 自動化生成與提取

### 4.1 上下文感知生成
```python
def generate_trailers_from_context(ctx: CommitContext) -> List[str]:
    trailers = []
    
    # 約束
    for c in ctx.constraints:
        trailers.append(f"Constraint: {c}")
    
    # 被拒方案
    for alt, reason in ctx.rejected_alternatives:
        trailers.append(f"Rejected: {alt} | {reason}")
    
    # 指令
    for d in ctx.directives:
        trailers.append(f"Directive: {d}")
    
    # 信心度/風險
    if ctx.confidence:
        trailers.append(f"Confidence: {ctx.confidence}")
    if ctx.scope_risk:
        trailers.append(f"Scope-risk: {ctx.scope_risk}")
    
    # 未測試
    for nt in ctx.not_tested:
        trailers.append(f"Not-tested: {nt}")
    
    # 風險接受
    for ra in ctx.risk_acceptances:
        trailers.append(f"Risk-Accepted: {ra}")
    
    # ADR
    for adr in ctx.adrs:
        trailers.append(f"ADR: {adr}")
    
    # Issue 關聯
    for issue in ctx.fixes:
        trailers.append(f"Fixes: #{issue}")
    for rel in ctx.related:
        trailers.append(f"Related: #{rel}")
    
    # 破壞性變更
    if ctx.breaking:
        trailers.append(f"Breaking: {ctx.breaking}")
    
    return trailers
```

### 4.2 從代碼變更推斷
```python
def infer_trailers_from_changes(changes: List[Change]) -> List[str]:
    trailers = []
    
    # 檢測破壞性變更
    if any(is_breaking_change(c) for c in changes):
        trailers.append("Breaking: API/Schema changed, migration required")
    
    # 檢測安全相關
    if any(is_security_related(c) for c in changes):
        trailers.append("Directive: Review security implications")
    
    # 檢測性能敏感
    if any(is_performance_sensitive(c) for c in changes):
        trailers.append("Directive: Benchmark before merge")
    
    return trailers
```

---

## 5. 工具集成

### 5.1 Git 配置
```bash
# 全局模板
git config commit.template ~/.gitmessage

# ~/.gitmessage 內容
# <type>(<scope>): <subject>
#
# ## Motivation
#
# ## Decision
#
# ## Impact
#
# ## Testing
#
# Constraint: 
# Rejected: 
# Directive: 
# Confidence: 
# Scope-risk: 
# Not-tested: 
# Risk-Accepted: 
# ADR: 
# Fixes: 
# Related: 
# Breaking: 
#
# Signed-off-by: 
```

### 5.2 Git Hooks 驗證
```bash
#!/bin/bash
# .git/hooks/commit-msg
# 驗證 Trailers 完整性

COMMIT_MSG_FILE=$1
ERRORS=$(python3 -c "
import sys, re
msg = open(sys.argv[1]).read()
trailers = {}
in_trailer = False
for line in msg.split('\n'):
    if not in_trailer and (not line.strip() or re.match(r'^[A-Z][A-Za-z0-9-]*:', line)):
        in_trailer = True
    if in_trailer:
        m = re.match(r'^([A-Z][A-Za-z0-9-]*):\s*(.+)$', line)
        if m: trailers[m.group(1)] = trailers.get(m.group(1), []) + [m.group(2)]
if 'Signed-off-by' not in trailers:
    print('ERROR: Missing Signed-off-by trailer')
    sys.exit(1)
for token, vals in trailers.items():
    if token == 'Confidence':
        for v in vals:
            if v not in ('high','medium','low'): print(f'ERROR: Invalid Confidence: {v}'); sys.exit(1)
    if token == 'Scope-risk':
        for v in vals:
            if v not in ('narrow','moderate','broad'): print(f'ERROR: Invalid Scope-risk: {v}'); sys.exit(1)
    if token == 'Risk-Accepted':
        for v in vals:
            if not re.match(r'^RA-\d{8}-\d{3}$', v): print(f'ERROR: Invalid Risk-Accepted: {v}'); sys.exit(1)
    if token == 'ADR':
        for v in vals:
            if not re.match(r'^ADR-\d{3,}$', v): print(f'ERROR: Invalid ADR: {v}'); sys.exit(1)
" "$1")
echo "$ERRORS"
exit 0
```

---

## 6. 完整示例

```bash
feat(auth): add OAuth2 login for enterprise

## Motivation
Enterprise customers require SSO integration.

## Decision
Implement OAuth2 Authorization Code flow with PKCE.

## Impact
Affected: auth-service, api-gateway
Risk: medium - new external dependencies
Migration: Feature flag oauth2.enabled

## Testing
- Unit: 95% coverage
- Integration: Mock IdP flows

Constraint: Must support PKCE for public clients
Rejected: SAML | complexity
Rejected: Custom JWT | maintenance
Directive: Add OIDC discovery endpoint in v2.2
Confidence: high
Scope-risk: moderate
Not-tested: E2E with real Okta tenant
Risk-Accepted: RA-20260808-001
ADR: ADR-012
Fixes: #1234

Signed-off-by: Alice Chen <alice@example.com>
Co-authored-by: Bob Wang <bob@example.com>
```

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08