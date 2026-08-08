# Conventional Commits 完整規範

> 編排器：`../SKILL.md`

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

## 2. Type 類型完整定義

| Type | 語義 | 觸發場景 | 版本影響 |
|------|------|----------|----------|
| `feat` | 新功能 | 用戶可見的新能力 | Minor |
| `fix` | Bug 修復 | 修復不正確行為 | Patch |
| `refactor` | 重構 | 代碼結構優化，行為不變 | 無 |
| `perf` | 性能優化 | 提升速度/資源效率 | Patch |
| `docs` | 文檔 | README/註釋/架構文檔 | 無 |
| `style` | 風格 | 格式/縮進/引號/空格 | 無 |
| `test` | 測試 | 新增/修改測試 | 無 |
| `chore` | 雜項 | 依賴/構建/配置/腳本 | 無/Patch |
| `revert` | 回滾 | 撤銷前次提交 | 視情況 |
| `security` | 安全 | 漏洞修復/加固 | Patch |
| `ci` | CI/CD | 流水線/腳本/環境 | 無 |
| `build` | 構建 | 包管理/編譯/打包 | Patch |
| `config` | 配置 | 環境/參數/特性開關 | 無/Patch |

### 2.1 Type 選擇決策樹
```
是否修復 Bug? → 是 → fix
否 → 是否新增用戶可見功能? → 是 → feat
否 → 是否改善性能? → 是 → perf
否 → 是否僅文檔? → 是 → docs
否 → 是否僅格式/風格? → 是 → style
否 → 是否僅測試? → 是 → test
否 → 是否重構(行為不變)? → 是 → refactor
否 → 是否安全相關? → 是 → security
否 → 是否 CI/CD/構建/配置? → 是 → ci/build/config
否 → 是否依賴更新/雜項? → 是 → chore
否 → 是否回滾? → 是 → revert
```

---

## 3. Scope 範圍規範

### 3.1 標準 Scope 列表
| Scope | 含義 | 示例 |
|-------|------|------|
| `auth` | 認證授權 | `feat(auth): add SSO` |
| `api` | API 接口 | `fix(api): handle 429` |
| `db` | 數據庫 | `perf(db): add index` |
| `ui` | 用戶界面 | `style(ui): fix alignment` |
| `core` | 核心業務邏輯 | `refactor(core): simplify` |
| `cache` | 緩存 | `perf(cache): add Redis` |
| `queue` | 消息隊列 | `feat(queue): add dead-letter` |
| `storage` | 存儲/文件 | `fix(storage): handle large files` |
| `config` | 配置管理 | `config: add feature flags` |
| `deps` | 依賴管理 | `chore(deps): upgrade lodash` |
| `build` | 構建系統 | `build: add Docker multi-stage` |
| `ci` | CI/CD | `ci: add security scan` |
| `release` | 發布流程 | `release: v2.1.0` |
| `security` | 安全加固 | `security: rotate keys` |
| `test` | 測試基礎設施 | `test: add contract tests` |
| `docs` | 文檔 | `docs: update API guide` |
| `infra` | 基礎設施 | `infra: add k8s manifests` |

### 3.2 Scope 選擇原則
- **單一職責**：一個提交只影響一個主要 scope
- **粒度適中**：不宜過細（如 `auth-login`）或過粗（如 `backend`）
- **團隊約定**：項目啟動時定義 scope 白名單，CI 校驗

---

## 4. Subject 主題行規範

### 4.1 格式要求
- **長度**：≤ 72 字符（含 `type(scope): `）
- **大小寫**：動詞小寫開頭
- **語氣**：祈使語氣
- **標點**：不以句號結尾
- **語言**：項目統一語言（中文/英文）

### 4.2 動詞規範
| 操作 | 推薦動詞 | 反例 |
|------|----------|------|
| 新增 | `add` `introduce` `implement` | `create` `make` `build` |
| 移除 | `remove` `drop` `delete` | `del` `rm` |
| 修改 | `update` `modify` `change` `adjust` | `fix` `modify` (用於 feat) |
| 替換 | `replace` `migrate` `switch` | `change` `update` |
| 優化 | `optimize` `improve` `speed up` | `perf` `enhance` |
| 重構 | `refactor` `restructure` `simplify` | `cleanup` `reorganize` |
| 修復 | `fix` `resolve` `correct` | `patch` `handle` |
| 回滾 | `revert` `rollback` | `undo` |
| 文檔 | `document` `add docs` `update docs` | `write` |
| 測試 | `add test` `cover` `extend coverage` | `test` |

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

## 5. Body 正文規範

### 5.1 結構
```
動機/背景：為什麼做這個變更
決策理由：為什麼選這個方案（拒絕了什麼替代方案）
影響分析：影響範圍/風險/遷移需求
測試證據：如何驗證
```

### 5.2 寫作模板
```
## Motivation
<問題描述 / 業務需求 / 技術債>

## Decision
<選擇方案> 而非 <替代方案1/2>
理由：<核心理由>

## Impact
影響範圍：<模塊/服務/用戶>
風險：<高/中/低> - <具體風險>
遷移：<無/需遷移腳本/需配置變更>

## Testing
- <測試類型>: <覆蓋範圍>
- <關鍵測試場景>
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

## 7. CI 校驗規則

### 7.1 Header 校驗
```yaml
# .github/lint-commit.yml
header:
  pattern: "^(feat|fix|refactor|perf|docs|style|test|chore|revert|security|ci|build|config)(\([a-z-]+\))?: .{1,72}$"
  max_length: 100  # 含 type(scope):
  
body:
  max_line_length: 72
  required_sections: ["Motivation", "Decision", "Impact", "Testing"]  # feat/fix 強制
  
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

## 8. 常見錯誤與修正

| 錯誤 | 修正 |
|------|------|
| `feat: Add new feature` | `feat: add new feature` (動詞小寫) |
| `fix(auth): Fixed bug.` | `fix(auth): fix null pointer when token expired` (祈使語氣、具體) |
| `refactor: code cleanup` | `refactor(core): simplify order processing logic` (具體) |
| `feat: add feature.` | `feat: add feature` (無句號) |
| `type(scope): subject` 行超 72 字符 | 縮短 subject 或移除次要信息到 body |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08