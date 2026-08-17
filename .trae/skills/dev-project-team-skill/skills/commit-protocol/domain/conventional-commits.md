# Conventional Commits 完整规范

> 编排器：`../SKILL.md`

---

## 1. 核心格式

```
<type>(<scope>): <subject>

<body>

<trailer1>: <value1>
<trailer2>: <value2>
...

Signed-off-by: <name> <email>
```

---

## 2. Type 类型完整定义

| Type | 语义 | 触发场景 | 版本影响 |
|------|------|----------|----------|
| `feat` | 新功能 | 用户可见的新能力 | Minor |
| `fix` | Bug 修复 | 修复不正确行为 | Patch |
| `refactor` | 重构 | 代码结构优化，行为不变 | 无 |
| `perf` | 性能优化 | 提升速度/资源效率 | Patch |
| `docs` | 文档 | README/注释/架构文档 | 无 |
| `style` | 风格 | 格式/缩进/引号/空格 | 无 |
| `test` | 测试 | 新增/修改测试 | 无 |
| `chore` | 杂项 | 依赖/构建/配置/脚本 | 无/Patch |
| `revert` | 回滚 | 撤销前次提交 | 视情况 |
| `security` | 安全 | 漏洞修复/加固 | Patch |
| `ci` | CI/CD | 流水线/脚本/环境 | 无 |
| `build` | 构建 | 包管理/编译/打包 | Patch |
| `config` | 配置 | 环境/参数/特性开关 | 无/Patch |

### 2.1 Type 选择决策树
```
是否修复 Bug? → 是 → fix
否 → 是否新增用户可见功能? → 是 → feat
否 → 是否改善性能? → 是 → perf
否 → 是否仅文档? → 是 → docs
否 → 是否仅格式/风格? → 是 → style
否 → 是否仅测试? → 是 → test
否 → 是否重构(行为不变)? → 是 → refactor
否 → 是否安全相关? → 是 → security
否 → 是否 CI/CD/构建/配置? → 是 → ci/build/config
否 → 是否依赖更新/杂项? → 是 → chore
否 → 是否回滚? → 是 → revert
```

---

## 3. Scope 范围规范

### 3.1 标准 Scope 列表
| Scope | 含义 | 示例 |
|-------|------|------|
| `auth` | 认证授权 | `feat(auth): add SSO` |
| `api` | API 接口 | `fix(api): handle 429` |
| `db` | 数据库 | `perf(db): add index` |
| `ui` | 用户界面 | `style(ui): fix alignment` |
| `core` | 核心业务逻辑 | `refactor(core): simplify` |
| `cache` | 缓存 | `perf(cache): add Redis` |
| `queue` | 消息队列 | `feat(queue): add dead-letter` |
| `storage` | 存储/文件 | `fix(storage): handle large files` |
| `config` | 配置管理 | `config: add feature flags` |
| `deps` | 依赖管理 | `chore(deps): upgrade lodash` |
| `build` | 构建系统 | `build: add Docker multi-stage` |
| `ci` | CI/CD | `ci: add security scan` |
| `release` | 发布流程 | `release: v2.1.0` |
| `security` | 安全加固 | `security: rotate keys` |
| `test` | 测试基础设施 | `test: add contract tests` |
| `docs` | 文档 | `docs: update API guide` |
| `infra` | 基础设施 | `infra: add k8s manifests` |

### 3.2 Scope 选择原则
- **单一职责**：一个提交只影响一个主要 scope
- **粒度适中**：不宜过细（如 `auth-login`）或过粗（如 `backend`）
- **团队约定**：项目启动时定义 scope 白名单，CI 校验

---

## 4. Subject 主题行规范

### 4.1 格式要求
- **长度**：≤ 72 字符（含 `type(scope): `）
- **大小写**：动词小写开头
- **语气**：祈使语气
- **标点**：不以句号结尾
- **语言**：项目统一语言（中文/英文）

### 4.2 动词规范
| 操作 | 推荐动词 | 反例 |
|------|----------|------|
| 新增 | `add` `introduce` `implement` | `create` `make` `build` |
| 移除 | `remove` `drop` `delete` | `del` `rm` |
| 修改 | `update` `modify` `change` `adjust` | `fix` `modify` (用于 feat) |
| 替换 | `replace` `migrate` `switch` | `change` `update` |
| 优化 | `optimize` `improve` `speed up` | `perf` `enhance` |
| 重构 | `refactor` `restructure` `simplify` | `cleanup` `reorganize` |
| 修复 | `fix` `resolve` `correct` | `patch` `handle` |
| 回滚 | `revert` `rollback` | `undo` |
| 文档 | `document` `add docs` `update docs` | `write` |
| 测试 | `add test` `cover` `extend coverage` | `test` |

### 4.3 Subject 模板
| Type | 模板 | 示例 |
|------|------|------|
| feat | `add <what> [for <context>]` | `add OAuth2 login for enterprise` |
| fix | `fix <what> [when <condition>]` | `fix null pointer when user inactive` |
| refactor | `refactor <what> to <how>` | `refactor UserService to use repository` |
| perf | `optimize <what> by <how>` | `optimize query by adding index` |
| docs | `document <what> [for <audience>]` | `document API rate limits for clients` |
| test | `add test for <what> [scenario]` | `add test for OAuth2 token refresh` |
| chore | `<action> <what>` | `upgrade dependencies` |

---

## 5. Body 正文规范

### 5.1 结构
```
动机/背景：为什么做这个变更
决策理由：为什么选这个方案（拒绝了什么替代方案）
影响分析：影响范围/风险/迁移需求
测试证据：如何验证
```

### 5.2 写作模板
```
## Motivation
<问题描述 / 业务需求 / 技术债>

## Decision
<选择方案> 而非 <替代方案1/2>
理由：<核心理由>

## Impact
影响范围：<模块/服务/用户>
风险：<高/中/低> - <具体风险>
迁移：<无/需迁移脚本/需配置变更>

## Testing
- <测试类型>: <覆盖范围>
- <关键测试场景>
```

---

## 6. 完整示例

```bash
feat(auth): add OAuth2 login for enterprise customers

## Motivation
Enterprise customers require SSO integration with their identity providers.
Current username/password auth doesn't meet compliance requirements.

## Decision
Implement OAuth2 Authorization Code flow with PKCE, supporting Google/Microsoft/Okta.
Rejected SAML (complexity) and custom JWT (maintenance burden).
Reason: OAuth2 is industry standard, wide IdP support, mature libraries.

## Impact
Affected: auth-service, api-gateway, frontend-login
Risk: medium - new external dependencies, token validation complexity
Migration: Feature flag `oauth2.enabled`, default off. No DB migration.

## Testing
- Unit: OAuth2 flow, token validation, error cases (95% coverage)
- Integration: Mock IdP flows, token exchange, user provisioning
- E2E: Happy path login/logout (manual, automated in next sprint)

Constraint: Must support PKCE for public clients
Rejected: SAML | complexity; Custom JWT | maintenance
Directive: Add OIDC discovery endpoint in v2.2
Confidence: high
Scope-risk: moderate
Not-tested: E2E with real Okta tenant
ADR: ADR-012
Fixes: #1234

Signed-off-by: Alice Chen <alice@example.com>
Co-authored-by: Bob Wang <bob@example.com>
```

---

## 7. CI 校验规则

### 7.1 Header 校验
```yaml
# .github/lint-commit.yml
header:
  pattern: "^(feat|fix|refactor|perf|docs|style|test|chore|revert|security|ci|build|config)(\([a-z-]+\))?: .{1,72}$"
  max_length: 100  # 含 type(scope):
  
body:
  max_line_length: 72
  required_sections: ["Motivation", "Decision", "Impact", "Testing"]  # feat/fix 强制
  
trailers:
  required: ["Signed-off-by"]
  allowed_keys: 
    - Constraint
    - Rejected
    - Directive
    - Confidence
    - Scope-risk
    - Not-tested
    - Risk-Accepted
    - ADR
    - Fixes
    - Related
    - Breaking
```

---

## 8. 常见错误与修正

| 错误 | 修正 |
|------|------|
| `feat: Add new feature` | `feat: add new feature` (动词小写) |
| `fix(auth): Fixed bug.` | `fix(auth): fix null pointer when token expired` (祈使语气、具体) |
| `refactor: code cleanup` | `refactor(core): simplify order processing logic` (具体) |
| `feat: add feature.` | `feat: add feature` (无句号) |
| `type(scope): subject` 行超 72 字符 | 缩短 subject 或移除次要信息到 body |

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08