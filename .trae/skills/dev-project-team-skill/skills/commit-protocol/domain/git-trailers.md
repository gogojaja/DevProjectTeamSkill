# Git Trailers 完整规范

> 编排器：`../SKILL.md`

---

## 1. Trailer 格式规范

### 1.1 基本语法
```
<Token>: <Value>
```
- Token 首字母大写，单词连接用连字符：`Signed-off-by` `Risk-Accepted`
- Value 不包含换行，长度建议 ≤ 100 字符
- 多个 Trailer 逐行排列，顺序不敏感但建议按重要性排序

### 1.2 标准 Trailer 注册表
| Token | 必填 | 可重复 | 语义 | 解析器支持 |
|-------|------|--------|------|------------|
| `Signed-off-by` | 是 | 是 | 开发者签署 | Git 内建 |
| `Co-authored-by` | 否 | 是 | 协作作者 | GitHub/GitLab |
| `Constraint` | 否 | 是 | 活跃约束 | 自定义 |
| `Rejected` | 否 | 是 | 被拒替代方案 | 自定义 |
| `Directive` | 否 | 是 | 前瞻指令 | 自定义 |
| `Confidence` | 否 | 否 | 决策信心度 | 自定义 |
| `Scope-risk` | 否 | 否 | 风险范围 | 自定义 |
| `Not-tested` | 否 | 是 | 未测试项 | 自定义 |
| `Risk-Accepted` | 否 | 是 | 风险接受单 ID | 自定义 |
| `ADR` | 否 | 是 | 架构决策引用 | 自定义 |
| `Fixes` | 否 | 是 | 修复 Issue | GitHub/GitLab |
| `Related` | 否 | 是 | 关联 PR/提交 | 自定义 |
| `Breaking` | 否 | 是 | 破坏性变更标记 | 自定义 |
| `Depends-on` | 否 | 是 | 依赖其他提交 | 自定义 |

---

## 2. 标准 Trailer 详细定义

### 2.1 Signed-off-by (强制)
```
Signed-off-by: Alice Chen <alice@example.com>
```
- **语义**：开发者确认有权提交、遵守 DCO/许可证
- **生成**：`git commit -s` 自动添加
- **验证**：CI 强制检查存在

### 2.2 Co-authored-by (协作)
```
Co-authored-by: Bob Wang <bob@example.com>
Co-authored-by: Carol Lee <carol@example.com>
```
- **语义**：标记协作贡献者，显示在 GitHub 提交页
- **格式**：`Name <email>`

### 2.3 Constraint (约束)
```
Constraint: Single-table rows < 100M
Constraint: API response P99 < 200ms
Constraint: Must support PKCE for public clients
```
- **语义**：塑造决策的硬性约束（技术/业务/合规）
- **可重复**：是，每行一个约束
- **解析**：CI 可提取用于架构验证

### 2.4 Rejected (被拒替代方案)
```
Rejected: MongoDB | ACID transactions not supported
Rejected: Custom JWT implementation | Maintenance burden
Rejected: SAML integration | Complexity exceeds value
```
- **格式**：`<alternative> | <reason>`
- **语义**：记录决策过程中被拒绝的方案及理由
- **可重复**：是

### 2.5 Directive (前瞻指令)
```
Directive: Migrate to async IO in Q3
Directive: Add OIDC discovery endpoint in v2.2
Directive: Deprecate legacy API by 2026-Q4
```
- **语义**：给未来开发者的指令/警告/计划
- **时效性**：建议包含时间范围

### 2.6 Confidence (信心度)
```
Confidence: high
Confidence: medium
Confidence: low
```
- **取值**：`high` `medium` `low`
- **语义**：决策者对方案正确性的信心程度

### 2.7 Scope-risk (风险范围)
```
Scope-risk: narrow
Scope-risk: moderate
Scope-risk: broad
```
- **取值**：`narrow` (单模块) `moderate` (少数服务) `broad` (跨系统)
- **用途**：自动化风险评估、部署策略决策

### 2.8 Not-tested (未测试项)
```
Not-tested: E2E checkout flow with real payment gateway
Not-tested: Multi-region failover scenario
Not-tested: Load test > 10k concurrent users
```
- **语义**：已知的验证缺口，风险透明化
- **可重复**：是

### 2.9 Risk-Accepted (风险接受)
```
Risk-Accepted: RA-20260808-001
Risk-Accepted: RA-20260805-003
```
- **格式**：`RA-YYYYMMDD-NNN`
- **语义**：引用风险接受单，表明风险已审批接受

### 2.10 ADR (架构决策记录)
```
ADR: ADR-003
ADR: ADR-012
```
- **格式**：`ADR-<NNN>`
- **语义**：关联架构决策记录，便于追溯

### 2.11 Fixes / Related
```
Fixes: #1234
Related: #5678
Related: !456
```
- **Fixes**：GitHub/GitLab 自动关闭 Issue
- **Related**：关联但不自动关闭

### 2.12 Breaking (破坏性变更)
```
Breaking: API v1 removed, migrate to v2
Breaking: Database schema changed, migration required
```
- **语义**：标记破坏性变更，触发 Major 版本升级

---

## 3. Trailers 解析与验证

### 3.1 解析器实现
```python
import re

TRAILER_PATTERN = re.compile(
    r'^(?P<token>[A-Za-z][A-Za-z0-9-]*):\s*(?P<value>.+)$'
)

def parse_trailers(commit_msg: str) -> Dict[str, List[str]]:
    """解析提交讯息中的 Trailers"""
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
    """验证 Trailers 完整性"""
    errors = []
    
    # 强制签署
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

## 4. 自动化生成与提取

### 4.1 上下文感知生成
```python
def generate_trailers_from_context(ctx: CommitContext) -> List[str]:
    trailers = []
    
    # 约束
    for c in ctx.constraints:
        trailers.append(f"Constraint: {c}")
    
    # 被拒方案
    for alt, reason in ctx.rejected_alternatives:
        trailers.append(f"Rejected: {alt} | {reason}")
    
    # 指令
    for d in ctx.directives:
        trailers.append(f"Directive: {d}")
    
    # 信心度/风险
    if ctx.confidence:
        trailers.append(f"Confidence: {ctx.confidence}")
    if ctx.scope_risk:
        trailers.append(f"Scope-risk: {ctx.scope_risk}")
    
    # 未测试
    for nt in ctx.not_tested:
        trailers.append(f"Not-tested: {nt}")
    
    # 风险接受
    for ra in ctx.risk_acceptances:
        trailers.append(f"Risk-Accepted: {ra}")
    
    # ADR
    for adr in ctx.adrs:
        trailers.append(f"ADR: {adr}")
    
    # Issue 关联
    for issue in ctx.fixes:
        trailers.append(f"Fixes: #{issue}")
    for rel in ctx.related:
        trailers.append(f"Related: #{rel}")
    
    # 破坏性变更
    if ctx.breaking:
        trailers.append(f"Breaking: {ctx.breaking}")
    
    return trailers
```

### 4.2 从代码变更推断
```python
def infer_trailers_from_changes(changes: List[Change]) -> List[str]:
    trailers = []
    
    # 检测破坏性变更
    if any(is_breaking_change(c) for c in changes):
        trailers.append("Breaking: API/Schema changed, migration required")
    
    # 检测安全相关
    if any(is_security_related(c) for c in changes):
        trailers.append("Directive: Review security implications")
    
    # 检测性能敏感
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

# ~/.gitmessage 内容
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

### 5.2 Git Hooks 验证
```bash
#!/bin/bash
# .git/hooks/commit-msg
# 验证 Trailers 完整性

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

**文档版本**: v1.0.0  **最后更新**: 2026-08-08