# Teleport 輕量 worktree 命令

> 編排器：`../SKILL.md`　上位：PSM 協議簡化版

---

## 1. 設計目標

| 特性 | PSM | Teleport |
|------|-----|----------|
| Git worktree | ✅ | ✅ |
| Tmux 會話 | ✅ | ❌ |
| Claude Code 啟動 | ✅ | ❌ |
| 會話註冊表 | ✅ | ❌ |
| 專案別名 | ✅ | ❌ (使用當前 repo) |
| 自動清理 | ✅ | ❌ |
| 適用場景 | 完整受控會話 | 快速隔離開發 |

---

## 2. 命令規格

### 2.1 `teleport <ref>` — 創建 worktree

```bash
# 支援格式
teleport #123                    # 當前 repo 的 issue/PR
teleport owner/repo#123          # 指定 repo
teleport https://github.com/owner/repo/issues/42
teleport my-feature              # 功能分支

# 選項
--worktree      # 創建 worktree (默認 true)
--path <path>   # 自定義 worktree 根目錄 (默認 ~/Workspace/omc-worktrees/)
--base <branch> # 基礎分支 (默認 main)
--json          # JSON 輸出
```

### 2.2 實現流程

```bash
# 1. 解析引用
if [[ "$1" =~ ^#([0-9]+)$ ]]; then
  # #123 → 當前 repo
  repo=$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')
  ref_type="issue"
  ref_num="${BASH_REMATCH[1]}"
elif [[ "$1" =~ ^([^/]+)/([^#]+)#([0-9]+)$ ]]; then
  owner="${BASH_REMATCH[1]}"
  repo="${BASH_REMATCH[2]}"
  ref_num="${BASH_REMATCH[3]}"
  ref_type="issue"
elif [[ "$1" =~ ^https://github.com/([^/]+)/([^/]+)/(issues|pull)/([0-9]+) ]]; then
  owner="${BASH_REMATCH[1]}"
  repo="${BASH_REMATCH[2]}"
  ref_type="${BASH_REMATCH[3]}"
  ref_num="${BASH_REMATCH[4]}"
else
  # 功能分支名
  feature_name="$1"
  ref_type="feature"
fi

# 2. 確定 worktree 路徑
worktree_root="${WORKTREE_ROOT:-$HOME/Workspace/omc-worktrees}"
case "$ref_type" in
  issue)  worktree_path="$worktree_root/issue/$repo-$ref_num" ;;
  pull)   worktree_path="$worktree_root/pr/$repo-$ref_num" ;;
  feature) worktree_path="$worktree_root/feat/$repo-$feature_name" ;;
esac

# 3. 確保本地 repo 存在
if [[ ! -d "$local_repo_path" ]]; then
  git clone "https://github.com/$repo.git" "$local_repo_path"
fi

# 4. 創建 worktree
cd "$local_repo_path"
case "$ref_type" in
  issue)
    gh issue view "$ref_num" --repo "$repo" --json number,title,body,labels,url
    git fetch origin "refs/heads/*:refs/remotes/origin/*"
    branch_name="issue/$ref_num-$(echo "$title" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | head -c 30)"
    git checkout -b "$branch_name" origin/main
    ;;
  pull)
    gh pr view "$ref_num" --repo "$repo" --json number,title,headRefName,baseRefName
    git fetch origin "pull/$ref_num/head:pr-$ref_num-teleport"
    branch_name="pr-$ref_num-teleport"
    ;;
  feature)
    branch_name="feature/$feature_name"
    git checkout -b "$branch_name" origin/main
    ;;
esac

git worktree add "$worktree_path" "$branch_name"

# 5. 輸出結果
if [[ "$JSON_OUTPUT" == "true" ]]; then
  jq -n --arg id "$repo-$ref_type-$ref_num" --arg path "$worktree_path" --arg branch "$branch_name" \
    '{id: $id, path: $path, branch: $branch, type: $ref_type}'
else
  echo "Worktree created:"
  echo "  ID: $repo-$ref_type-$ref_num"
  echo "  Path: $worktree_path"
  echo "  Branch: $branch_name"
  echo "  Type: $ref_type"
  echo ""
  echo "To start working:"
  echo "  cd \"$worktree_path\""
fi
```

### 2.3 `teleport list` — 列出 worktree

```bash
worktree_root="${WORKTREE_ROOT:-$HOME/Workspace/omc-worktrees}"
echo "Teleport Worktrees:"
echo "ID                    | Type  | Branch              | Path"
echo "----------------------|-------|---------------------|---------------------------"
for dir in "$worktree_root"/*/*/; do
  [[ -d "$dir" ]] || continue
  id=$(basename "$dir")
  type=$(basename "$(dirname "$dir")")
  branch=$(cd "$dir" && git branch --show-current 2>/dev/null || echo "detached")
  printf "%-22s | %-5s | %-19s | %s\n" "$id" "$type" "$branch" "$dir"
done
```

### 2.4 `teleport remove <id>` — 移除 worktree

```bash
worktree_root="${WORKTREE_ROOT:-$HOME/Workspace/omc-worktrees}"
worktree_path="$worktree_root/$1"

if [[ ! -d "$worktree_path" ]]; then
  echo "Worktree not found: $1"
  exit 1
fi

# 找到 source repo
source_repo=$(cd "$worktree_path" && git rev-parse --git-common-dir | sed 's|/\.git/worktrees/.*||')

# 移除 worktree
cd "$source_repo"
git worktree remove "$worktree_path" --force

echo "Removed: $1"
```

### 2.5 佈局結構

```
~/Workspace/omc-worktrees/
├── issue/
│   └── my-repo-123/        # Issue worktrees
├── pr/
│   └── my-repo-456/        # PR review worktrees
└── feat/
    └── my-repo-my-feature/ # Feature worktrees
```

---

## 3. PSM vs Teleport 選擇指南

| 需求 | 推薦 |
|------|------|
| 完整受控會話、tmux、自動清理、專案別名 | PSM |
| 快速創建隔離環境、手動管理、無 tmux 依賴 | Teleport |
| CI/CD 集成、腳本化批量創建 | Teleport |
| 團隊協作、會話共享、狀態持久化 | PSM |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08