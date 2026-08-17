# 分支命名规范

> 编排器：`../SKILL.md`

---

## 1. 分支命名格式

### 1.1 统一格式
```
<type>/<task-id>-<short-description>
```

### 1.2 Type 类型
| Type | 用途 | 命名前缀 | 示例 |
|------|------|----------|------|
| `feature` | 新功能开发 | `feat/` | `feat/AUTH-123-add-oauth2` |
| `bugfix` | Bug 修复 | `fix/` | `fix/API-456-handle-null` |
| `hotfix` | 紧急线上修复 | `hotfix/` | `hotfix/SEC-789-jwt-validation` |
| `refactor` | 代码重构 | `refactor/` | `refactor/core-simplify-service` |
| `perf` | 性能优化 | `perf/` | `perf/db-add-index` |
| `docs` | 文档更新 | `docs/` | `docs/update-api-guide` |
| `test` | 测试相关 | `test/` | `test/add-oauth2-tests` |
| `chore` | 杂项/依赖/配置 | `chore/` | `chore/deps-upgrade-lodash` |
| `release` | 发布准备 | `release/` | `release/v2.1.0` |
| `experiment` | 实验/探索 | `exp/` | `exp/new-cache-strategy` |

### 1.3 Task ID 规范
| 来源 | 格式 | 示例 |
|------|------|------|
| Jira | `<PROJECT>-<NUM>` | `AUTH-123` |
| GitHub Issues | `#<NUM>` | `#123` (分支名用 `issue-123`) |
| GitLab Issues | `#<NUM>` | `#456` (分支名用 `issue-456`) |
| 内部任务 | `TASK-<NUM>` | `TASK-789` |
| 无追踪系统 | `local-<描述>` | `local-add-health-check` |

---

## 2. 完整示例

| 类型 | 分支名 |
|------|--------|
| 新功能 | `feat/AUTH-123-add-oauth2-login` |
| Bug 修复 | `fix/API-456-handle-null-response` |
| 紧急修复 | `hotfix/SEC-789-jwt-validation-bypass` |
| 重构 | `refactor/core-extract-repository-pattern` |
| 性能 | `perf/db-add-composite-index-orders` |
| 文档 | `docs/update-api-docs-v2` |
| 测试 | `test/integration-add-oauth2-flows` |
| 依赖升级 | `chore/deps-upgrade-spring-boot-3.2` |
| 发布 | `release/v2.1.0` |
| 实验 | `exp/redis-cluster-mode` |

---

## 3. 命名规则

### 3.1 基本规则
1. **小写**：全部小写字母
2. **连字符**：单词间用 `-` 连接
2. **无特殊字符**：仅允许 `a-z` `0-9` `-` `/`
3. **长度**：≤ 60 字符（含 type/ 前缀）
4. **描述性**：短语动词开头，清晰表达目的

### 3.2 禁止模式
| 禁止 | 原因 | 修正 |
|------|------|------|
| `feature/new-feature` | 无 Task ID | `feat/AUTH-123-new-feature` |
| `fix/bug` | 描述过于简略 | `fix/API-456-null-pointer` |
| `temp/debug` | 临时分支应有追踪 | `fix/LOCAL-debug-null-pointer` |
| `wip/refactor` | WIP 应在 commit message | `refactor/core-extract-service` |
| `dev/alice/new-ui` | 无需开发者名 | `feat/UI-789-new-dashboard` |

### 3.3 长度控制
- `type/` 前缀：4-7 字符
- `task-id`：6-12 字符
- `description`：20-40 字符
- **总计**：≤ 60 字符

---

## 4. 分支生命周期

### 4.1 创建
```bash
# 从主分支创建
git checkout main
git pull origin main
git checkout -b feat/AUTH-123-add-oauth2-login

# 或从开发分支
git checkout develop
git pull origin develop
git checkout -b fix/API-456-handle-null
```

### 4.2 同步更新
```bash
# 定期从主分支 rebase
git fetch origin
git rebase origin/main

# 或 merge (团队约定)
git merge origin/main
```

### 4.3 推送与 PR
```bash
# 推送并建立 PR
git push -u origin feat/AUTH-123-add-oauth2-login
# 在 GitHub/GitLab 建立 PR，目标分支: main 或 develop
```

### 4.4 合并后清理
```bash
# 合并后删除远端分支
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
# 创建发布分支
git checkout -b release/v2.1.0 main
# 仅允许: 版本号更新、变更日志、关键修复
# 禁止: 新功能、大重构

# 发布后合并回主分支并打标签
git checkout main
git merge release/v2.1.0
git tag -a v2.1.0 -m "Release v2.1.0"
git push origin main --tags
```

### 5.2 Hotfix 分支
```bash
# 从生产标签创建
git checkout -b hotfix/SEC-789-jwt-fix v2.0.0

# 修复并测试
# ...

# 合并回 main 和 develop
git checkout main
git merge hotfix/SEC-789-jwt-fix
git tag -a v2.0.1 -m "Hotfix v2.0.1"

git checkout develop
git merge hotfix/SEC-789-jwt-fix
```

### 5.3 实验分支
```bash
# 短期探索，不合并回主线
git checkout -b exp/new-cache-strategy
# 实验结束后：要么转为 feat/ 分支，要么删除
```

---

## 6. CI/CD 集成

### 6.1 分支名校验
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

### 6.2 自动清理
```yaml
# 合并后自动删除分支
# GitHub: Settings > Pull Requests > "Automatically delete head branches"
# GitLab: Settings > Repository > "Delete source branch when merge request is accepted"
```

---

## 6. 常见问题

| 问题 | 解决 |
|------|------|
| 忘记 Task ID | 推送前 `git branch -m <new-name>` 重命名 |
| 描述过长 | 缩短至关键动词+名词，移至 commit message |
| 分支名冲突 | 加后缀 `-v2` 或重新创建 |
| 推送前发现命名错误 | `git branch -m <old> <new>` 重命名本地，`git push origin :<old> <new>` 更新远端 |
| 已合并但未删除 | 定期 `git branch -r --merged | grep -v main | xargs -n 1 git push origin --delete` |

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08