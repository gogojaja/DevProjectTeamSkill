# 簽署協議：Signed-off-by / Co-authored-by / 審查簽署

> 編排器：`../SKILL.md`

---

## 1. Signed-off-by (DCO 簽署)

### 1.1 定義
`Signed-off-by` 是開發者對提交內容的法律聲明，遵循 **Developer Certificate of Origin (DCO) v1.1**：

```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.
660 York Street, Suite 102, San Francisco, CA 94110 USA

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.

Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including
    all personal information I submit with it, including my
    sign-off) is maintained indefinitely and may be redistributed
    consistent with this project or the open source license(s)
    involved.
```

### 1.2 格式
```
Signed-off-by: Full Name <email@example.com>
```
- **姓名**：法定全名或慣用名
- **郵箱**：有效聯繫郵箱（建議使用項目認可的郵箱）
- **生成**：`git commit -s` 自動添加（需配置 `user.name`/`user.email`）

### 1.3 強制要求
| 場景 | 強制 |
|------|------|
| 所有正式提交 | ✅ 是 |
| PR/MR 合併提交 | ✅ 是 |
| 發布提交 | ✅ 是 |
| Revert 提交 | ✅ 是 |
| 僅格式化/重排 (style) | 建議 |
| 僅文檔/註釋 (docs) | 建議 |

---

## 2. Co-authored-by (協作作者)

### 2.1 定義
標記對提交有實質貢獻但非主要作者的協作者，GitHub/GitLab 會在提交頁面顯示其頭像。

### 2.2 格式
```
Co-authored-by: Full Name <email@example.com>
```
- 可多行，每行一位協作者
- 郵箱需與 GitHub/GitLab 賬號關聯才能正確顯示頭像

### 2.3 適用場景
| 場景 | 是否添加 |
|------|----------|
| 兩人以上共同編程 | ✅ 是 |
| 代碼審查者提出關鍵修改並由作者提交 | ✅ 是 |
| 設計/架構師提供核心方案 | ✅ 是 |
| 僅提出建議/意見 | ❌ 否 |
| 僅測試/驗證 | 視貢獻程度 |

---

## 3. 審查簽署

### 3.1 代碼審查簽署
在 PR/MR 審查通過時，審查者在評論中簽署：

```markdown
## Review Sign-off

✅ **Approved** by @reviewer-name

**Review Scope**: Full codebase / auth-module / api-contracts
**Confidence**: High
**Conditions**: None / Fix flaky test before merge

**Signed-off-by**: Reviewer Name <reviewer@example.com>
```

### 3.2 架構審查簽署
```markdown
## Architecture Review Sign-off

✅ **Architecture Approved** by @architect-name

**ADR References**: ADR-012 (OAuth2), ADR-015 (Async Migration)
**Compliance**: PASS - All constraints satisfied
**Risk Acceptance**: RA-20260808-001 (E2E gap)

**Signed-off-by**: Architect Name <architect@example.com>
```

### 3.3 安全審查簽署
```markdown
## Security Review Sign-off

✅ **Security Approved** by @security-engineer

**Threat Model**: STRIDE completed, no critical gaps
**SAST/DAST**: PASS (0 critical, 0 high)
**Secrets Scan**: PASS
**Compliance**: GDPR/PCI-DSS alignment verified

**Signed-off-by**: Security Engineer <security@example.com>
```

---

## 4. 簽署驗證自動化

### 4.1 Git Hook 驗證
```bash
#!/bin/bash
# .git/hooks/commit-msg
# 驗證 Signed-off-by 存在

MSG_FILE=$1
if ! grep -q "^Signed-off-by:" "$1"; then
    echo "ERROR: Missing Signed-off-by trailer"
    echo "Run 'git commit -s' to add automatically"
    exit 1
fi
exit 0
```

### 4.2 CI 驗證
```yaml
# .github/workflows/dco-check.yml
name: DCO Check
on: [pull_request]
jobs:
  dco:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Check DCO
        run: |
          commits=$(git log --format="%H" ${{ github.event.pull_request.base.sha }}..HEAD)
          for sha in $commits; do
            if ! git log -1 --format="%B" $sha | grep -q "^Signed-off-by:"; then
              echo "❌ Commit $sha missing Signed-off-by"
              exit 1
            fi
          done
          echo "✅ All commits have DCO sign-off"
```

### 4.3 GitHub DCO App
```yaml
# 使用 GitHub DCO App 自動檢查
# 安裝: https://github.com/apps/dco
# 配置: .github/dco.yml
repos:
  - your-org/your-repo
require_signoff: true
allow_rebase: false
```

---

## 5. 簽署最佳實踐

### 5.1 配置全局簽署
```bash
# 設置用戶信息
git config --global user.name "Your Full Name"
git config --global user.email "your.email@example.com"

# 啟用自動簽署
git config --global commit.gpgsign true  # 可選：GPG 簽名
git config --global commit.signoff true  # 自動添加 Signed-off-by
```

### 5.2 GPG 簽名 (可選增強)
```bash
# 生成 GPG 密鑰
gpg --full-generate-key

# 配置 Git 使用 GPG
git config --global user.signingkey <KEY_ID>
git config --global commit.gpgsign true
git config --global tag.gpgsign true

# 導出公鑰到 GitHub/GitLab
gpg --armor --export <KEY_ID>
```

### 5.3 團隊簽署規範
| 角色 | 簽署要求 |
|------|----------|
| 開發者 | 每次提交 `Signed-off-by` |
| 審查者 | PR 批准時 `Co-authored-by` 或審查簽署 |
| 架構師 | 架構決策提交 `Signed-off-by` + ADR 引用 |
| 安全工程師 | 安全修復提交 `Signed-off-by` + 威脅模型引用 |
| 發布工程師 | 發布提交 `Signed-off-by` + 版本/變更日誌 |
| 專案負責人 | 關鍵發布/風險接受 `Signed-off-by` |

---

## 6. 簽署異常處理

| 異常 | 處理 |
|------|------|
| 缺少 Signed-off-by | CI 阻斷，要求補充 `git commit --amend -s` |
| 郵箱不匹配 GitHub | 提示更新 `user.email` 或在 GitHub 添加郵箱 |
| 多人共用一提交 | 主作者 `Signed-off-by`，協作者 `Co-authored-by` |
| 批量提交缺少簽署 | `git rebase -i` 逐個 `amend -s` 或腳本批量添加 |
| GPG 密鑰過期 | 更新密鑰或暫時關閉 `commit.gpgsign` |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08