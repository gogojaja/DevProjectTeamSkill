# Teleport 轻量 worktree 命令

> 编排器：`../SKILL.md`　上位：PSM 协议简化版

---

## 1. 设计目标

| 特性 | PSM | Teleport |
|------|-----|----------|
| Git worktree | ✅ | ✅ |
| Tmux 会话 | ✅ | ❌ |
| Claude Code 启动 | ✅ | ❌ |
| 会话注册表 | ✅ | ❌ |
| 专案别名 | ✅ | ❌ (使用当前 repo) |
| 自动清理 | ✅ | ❌ |
| 适用场景 | 完整受控会话 | 快速隔离开发 |

---

## 2. 命令规格

### 2.1 `teleport <ref>` — 创建 worktree

```bash
# 支援格式
teleport #123                    # 当前 repo 的 issue/PR
teleport owner/repo#123          # 指定 repo
teleport https://github.com/owner/repo/issues/42
teleport my-feature              # 功能分支

# 选项
--worktree      # 创建 worktree (默认 true)
--path <path>   # 自定义 worktree 根目录 (默认 ~/Workspace/omc-worktrees/)
--base <branch> # 基础分支 (默认 main)
--json          # JSON 输出
```

### 2.2 实现流程

```bash
# 1. 解析引用
if [[ "$1" =~ ^#([0-9]+)$ ]]; then
  # #123 → 当前 repo
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

# 2. 确定 worktree 路径
worktree_root="${WORKTREE_ROOT:-$HOME/Workspace/omc-worktrees}"
case "$ref_type" in
  issue)  worktree_path="$worktree_root/issue/$repo-$ref_num" ;;
  pull)   worktree_path="$worktree_root/pr/$repo-$ref_num" ;;
  feature) worktree_path="$worktree_root/feat/$repo-$feature_name" ;;
esac

# 3. 确保本地 repo 存在
if [[ ! -d "$local_repo_path" ]]; then
  git clone "https://github.com/$repo.git" "$local_repo_path"
fi

# 4. 创建 worktree
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

# 5. 输出结果
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

### 2.5 布局结构

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

## 3. PSM vs Teleport 选择指南

| 需求 | 推荐 |
|------|------|
| 完整受控会话、tmux、自动清理、专案别名 | PSM |
| 快速创建隔离环境、手动管理、无 tmux 依赖 | Teleport |
| CI/CD 集成、脚本化批量创建 | Teleport |
| 团队协作、会话共享、状态持久化 | PSM |

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08