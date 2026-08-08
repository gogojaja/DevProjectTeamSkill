# 分支命名規範

> 編排器：`../SKILL.md`

---

## 1. 分支命名格式

### 1.1 統一格式
```
<type>/<task-id>-<short-description>
```

### 1.2 Type 類型
| Type | 用途 | 命名前綴 | 示例 |
|------|------|----------|------|
| `feature` | 新功能開發 | `feat/` | `feat/AUTH-123-add-oauth2` |
| `bugfix` | Bug 修復 | `fix/` | `fix/API-456-handle-null` |
| `hotfix` | 緊急線上修復 | `hotfix/` | `hotfix/SEC-789-jwt-validation` |
| `refactor` | 代碼重構 | `refactor/` | `refactor/core-simplify-service` |
| `perf` | 性能優化 | `perf/` | `perf/db-add-index` |
| `docs` | 文檔更新 | `docs/` | `docs/update-api-guide` |
| `test` | 測試相關 | `test/` | `test/add-oauth2-tests` |
| `chore` | 雜項/依賴/配置 | `chore/` | `chore/deps-upgrade-lodash` |
| `release` | 發布準備 | `release/` | `release/v2.1.0` |
| `experiment` | 實驗/探索 | `exp/` | `exp/new-cache-strategy` |

### 1.3 Task ID 規範
| 來源 | 格式 | 示例 |
|------|------|------|
| Jira | `<PROJECT>-<NUM>` | `AUTH-123` |
| GitHub Issues | `#<NUM>` | `#123` (分支名用 `issue-123`) |
| GitLab Issues | `#<NUM>` | `#456` (分支名用 `issue-456`) |
| 內部任務 | `TASK-<NUM>` | `TASK-789` |
| 無追蹤系統 | `local-<描述>` | `local-add-health-check` |

---

## 2. 完整示例

| 類型 | 分支名 |
|------|--------|
| 新功能 | `feat/AUTH-123-add-oauth2-login` |
| Bug 修復 | `fix/API-456-handle-null-response` |
| 緊急修復 | `hotfix/SEC-789-jwt-validation-bypass` |
| 重構 | `refactor/core-extract-repository-pattern` |
| 性能 | `perf/db-add-composite-index-orders` |
| 文檔 | `docs/update-api-docs-v2` |
| 測試 | `test/integration-add-oauth2-flows` |
| 依賴升級 | `chore/deps-upgrade-spring-boot-3.2` |
| 發布 | `release/v2.1.0` |
| 實驗 | `exp/redis-cluster-mode` |

---

## 3. 命名規則

### 3.1 基本規則
1. **小寫**：全部小寫字母
2. **連字符**：單詞間用 `-` 連接
2. **無特殊字符**：僅允許 `a-z` `0-9` `-` `/`
3. **長度**：≤ 60 字符（含 type/ 前綴）
4. **描述性**：短語動詞開頭，清晰表達目的

### 3.2 禁止模式
| 禁止 | 原因 | 修正 |
|------|------|------|
| `feature/new-feature` | 無 Task ID | `feat/AUTH-123-new-feature` |
| `fix/bug` | 描述過於簡略 | `fix/API-456-null-pointer` |
| `temp/debug` | 臨時分支應有追蹤 | `fix/LOCAL-debug-null-pointer` |
| `wip/refactor` | WIP 應在 commit message | `refactor/core-extract-service` |
| `dev/alice/new-ui` | 無需開發者名 | `feat/UI-789-new-dashboard` |

### 3.3 長度控制
- `type/` 前綴：4-7 字符
- `task-id`：6-12 字符
- `description`：20-40 字符
- **總計**：≤ 60 字符

---

## 4. 分支生命週期

### 4.1 創建
```bash
# 從主分支創建
git checkout main
git pull origin main
git checkout -b feat/AUTH-123-add-oauth2-login

# 或從開發分支
git checkout develop
git pull origin develop
git checkout -b fix/API-456-handle-null
```

### 4.2 同步更新
```bash
# 定期從主分支 rebase
git fetch origin
git rebase origin/main

# 或 merge (團隊約定)
git merge origin/main
```

### 4.3 推送與 PR
```bash
# 推送並建立 PR
git push -u origin feat/AUTH-123-add-oauth2-login
# 在 GitHub/GitLab 建立 PR，目標分支: main 或 develop
```

### 4.4 合併後清理
```bash
# 合併後刪除遠端分支
git push origin --delete feat/AUTH-123-add-oauth2-login

# 本地清理
git checkout main
git branch -d feat/AUTH-123-add-oauth2-login
git fetch --prune
```

---

## 5. 特殊分支

### 5.1 Release 分支
```bash
# 創建發布分支
git checkout -b release/v2.1.0 main
# 僅允許: 版本號更新、變更日誌、關鍵修復
# 禁止: 新功能、大重構

# 發布後合併回主分支並打標籤
git checkout main
git merge release/v2.1.0
git tag -a v2.1.0 -m "Release v2.1.0"
git push origin main --tags
```

### 5.2 Hotfix 分支
```bash
# 從生產標籤創建
git checkout -b hotfix/SEC-789-jwt-fix v2.0.0

# 修復並測試
# ...

# 合併回 main 和 develop
git checkout main
git merge hotfix/SEC-789-jwt-fix
git tag -a v2.0.1 -m "Hotfix v2.0.1"

git checkout develop
git merge hotfix/SEC-789-jwt-fix
```

### 5.3 實驗分支
```bash
# 短期探索，不合併回主線
git checkout -b exp/new-cache-strategy
# 實驗結束後：要么轉為 feat/ 分支，要么刪除
```

---

## 6. CI/CD 集成

### 6.1 分支名校驗
```yaml
# .github/workflows/branch-name-check.yml
name: Branch Name Check
on: [pull_request, push]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Check branch name
        run: |
          BRANCH="${GITHUB_HEAD_REF:-${GITHUB_REF#refs/heads/}}"
          PATTERN='^(feat|fix|hotfix|refactor|perf|docs|test|chore|release|exp)/[A-Z]+-\d+-[a-z0-9-]+$|^release/v\d+\.\d+\.\d+$'
          if [[ ! $BRANCH =~ $PATTERN ]]; then
            echo "❌ Invalid branch name: $BRANCH"
            echo "Expected: <type>/<TASK-ID>-<description>"
            echo "Example: feat/AUTH-123-add-oauth2"
            exit 1
          fi
          echo "✅ Branch name valid: $BRANCH"
```

### 6.2 自動清理
```yaml
# 合併後自動刪除分支
# GitHub: Settings > Pull Requests > "Automatically delete head branches"
# GitLab: Settings > Repository > "Delete source branch when merge request is accepted"
```

---

## 6. 常見問題

| 問題 | 解決 |
|------|------|
| 忘記 Task ID | 推送前 `git branch -m <new-name>` 重命名 |
| 描述過長 | 縮短至關鍵動詞+名詞，移至 commit message |
| 分支名衝突 | 加後綴 `-v2` 或重新創建 |
| 推送前發現命名錯誤 | `git branch -m <old> <new>` 重命名本地，`git push origin :<old> <new>` 更新遠端 |
| 已合併但未刪除 | 定期 `git branch -r --merged | grep -v main | xargs -n 1 git push origin --delete` |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08