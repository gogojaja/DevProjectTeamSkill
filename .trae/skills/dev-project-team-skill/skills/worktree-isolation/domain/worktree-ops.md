# Git Worktree 底层操作

> 编排器：`../SKILL.md`　上位：PSM 协议、Teleport

---

## 1. 基础操作

### 1.1 创建 Worktree
```bash
# 语法
git worktree add [-f] [--detach] [-b <new-branch>] <path> [<commit-ish>]

# 示例
git worktree add ../feature-auth feature/auth          # 从现有分支
git worktree add ../pr-123 pr-123-review              # 从已获取的 PR ref
git worktree add -b hotfix/urgent ../hotfix main      # 新建分支并创建 worktree
git worktree add --detach ../detached HEAD            # 分离 HEAD 模式
```

### 1.2 列出 Worktree
```bash
git worktree list
# 输出格式:
# /path/to/main      abcd1234 [main]
# /path/to/feature   efgh5678 [feature/auth]
# /path/to/pr-123    ijkl9012 [pr-123-review]
```

### 1.3 移除 Worktree
```bash
# 正常移除 (要求 worktree 干净)
git worktree remove <path>

# 强制移除 (忽略未提交变更)
git worktree remove --force <path>

# 移除并清理管理文件
git worktree remove <path> && git worktree prune
```

### 1.4 修剪失效记录
```bash
git worktree prune [-v] [--expire <time>]
# 移除 .git/worktrees/ 下已删除目录的管理文件
```

---

## 2. PR/Workflow 专用操作

### 2.1 获取 PR Ref 并创建 Worktree
```bash
# 1. 获取 PR 信息
gh pr view 123 --repo owner/repo --json number,title,headRefName,baseRefName

# 2. Fetch PR ref (GitHub 专用)
git fetch origin "pull/123/head:pr-123-review"

# 3. 创建 worktree
git worktree add ~/.psm/worktrees/owner/repo/pr-123 pr-123-review

# 完整脚本
create_pr_worktree() {
    local pr_number="$1"
    local repo="$2"
    local worktree_root="${3:-$HOME/.psm/worktrees}"
    
    # 获取 PR 信息
    local pr_info=$(gh pr view "$pr_number" --repo "$repo" --json number,title,headRefName,baseRefName)
    local base_branch=$(echo "$pr_info" | jq -r '.baseRefName')
    
    # Fetch PR ref
    git -C "$local_repo" fetch origin "pull/$pr_number/head:pr-$pr_number-review"
    
    # 创建 worktree
    local worktree_path="$worktree_root/$(echo $repo | tr '/' '_')/pr-$pr_number"
    git -C "$local_repo" worktree add "$worktree_path" "pr-$pr_number-review"
    
    echo "$worktree_path"
}
```

### 2.2 Issue 修复 Worktree
```bash
create_issue_worktree() {
    local issue_number="$1"
    local repo="$2"
    local base_branch="${3:-main}"
    
    # 获取 issue 信息
    local issue_info=$(gh issue view "$issue_number" --repo "$repo" --json number,title)
    local title=$(echo "$issue_info" | jq -r '.title')
    local branch_name="fix/$issue_number-$(echo "$title" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | head -c 30)"
    
    # 确保 base 分支最新
    git -C "$local_repo" fetch origin "$base_branch"
    
    # 创建分支
    git -C "$local_repo" checkout -b "$branch_name" "origin/$base_branch"
    
    # 创建 worktree
    local worktree_path="$worktree_root/$(echo $repo | tr '/' '_')/issue-$issue_number"
    git -C "$local_repo" worktree add "$worktree_path" "$branch_name"
    
    echo "$worktree_path"
}
```

---

## 3. 迁移与修复

### 3.1 Worktree 迁移 (移动路径)
```bash
# Git 2.30+ 支援 --move
git worktree move <old-path> <new-path>

# 旧版本手动迁移
migrate_worktree() {
    local old_path="$1"
    local new_path="$2"
    
    # 1. 获取 worktree 关联的分支
    local branch=$(git -C "$old_path" branch --show-current)
    
    # 2. 移除旧 worktree (保留分支)
    git worktree remove "$old_path"
    
    # 3. 在新位置创建
    git worktree add "$new_path" "$branch"
}
```

### 3.2 修复损坏的 Worktree
```bash
repair_worktree() {
    local path="$1"
    
    # 1. 检查 .git 文件
    if [[ ! -f "$path/.git" ]]; then
        echo "Not a worktree: $path"
        return 1
    fi
    
    # 2. 读取 .git 内容
    local git_dir=$(cat "$path/.git" | sed 's/gitdir: //')
    
    # 3. 检查 .git/worktrees/ 管理目录
    local wt_name=$(basename "$path")
    local admin_dir="$(dirname "$git_dir")/worktrees/$wt_name"
    
    if [[ ! -d "$admin_dir" ]]; then
        echo "Worktree admin dir missing, re-registering..."
        # 重新注册
        local branch=$(git -C "$path" branch --show-current)
        git worktree remove "$path" 2>/dev/null || true
        git worktree add "$path" "$branch"
    fi
}
```

---

## 4. 错误处理与常见问题

### 4.1 常见错误代码

| 错误 | 原因 | 解决 |
|------|------|------|
| `fatal: 'path' already exists` | 目标路径已存在 | 使用其他路径或先移除 |
| `fatal: 'branch' is already checked out at 'path'` | 分支已在别处 checkout | 先移除旧 worktree 或用其他分支 |
| `fatal: not a valid worktree` | 管理文件损坏 | `git worktree prune` 后重试 |
| `fatal: cannot lock ref` | 并发操作冲突 | 重试或检查锁文件 |
| `not a valid worktree: path` | worktree 目录被手动删除 | `git worktree prune` 清理 |

### 4.2 并发安全
```bash
# worktree 操作加锁
WT_LOCK_DIR="$HOME/.psm/wt-locks"
mkdir -p "$WT_LOCK_DIR"

with_wt_lock() {
    local repo="$1"
    local cmd="$2"
    local lock_file="$WT_LOCK_DIR/$(echo "$repo" | tr '/' '_').lock"
    mkdir -p "$(dirname "$lock_file")"
    
    exec 200>"$lock_file"
    flock -x -w 30 200 || { echo "Lock timeout"; return 1; }
    eval "$cmd"
    flock -u 200
}

# 使用示例
with_wt_lock "$repo" "git worktree add '$path' '$branch'"
```

---

## 5. 性能优化

### 5.1 共享 Object Database
```bash
# 所有 worktree 共享 .git/objects，节省空间
# 检查共享情况
du -sh .git/objects
du -sh .git/worktrees/*/
```

### 5.2 批量操作
```bash
# 批量创建 worktree (避免重复 fetch)
batch_create_worktrees() {
    local repo="$1"
    shift
    local branches=("$@")
    
    # 一次性 fetch 所有需要的 refs
    git -C "$repo" fetch origin "${branches[@]}"
    
    # 并行创建 worktree (背景任务)
    for branch in "${branches[@]}"; do
        git -C "$repo" worktree add "$worktree_root/$(echo $branch | tr '/' '_')" "$branch" &
    done
    wait
}
```

### 5.3 清理策略
```bash
# 定期清理失效 worktree 记录
git worktree prune --expire 30.days.ago

# 清理已合并分支的 worktree
cleanup_merged_worktrees() {
    local repo="$1"
    local main_branch="${2:-main}"
    
    # 找出已合并的分支
    git -C "$repo" branch --merged "$main_branch" | grep -v "^\*\|$main_branch" | while read branch; do
        # 找到使用该分支的 worktree
        local wt_path=$(git -C "$repo" worktree list --porcelain | awk -v b="$branch" '$1=="worktree"{w=$2} $1=="branch" && $2==b{print w}')
        if [[ -n "$wt_path" ]]; then
            echo "Removing merged worktree: $wt_path ($branch)"
            git -C "$repo" worktree remove "$wt_path" --force
        fi
    done
}
```

---

## 6. 跨平台注意事项

| 平台 | 注意事项 |
|------|----------|
| Linux/macOS | 完整支援，符号链接正常 |
| Windows (Git Bash/WSL) | 支援，需启用 `core.symlinks=true` |
| Windows (CMD/PowerShell) | 部分命令需调整路径分隔符 |
| 无符号链接权限 | 设置 `git config core.symlinks false` 使用副本模式 |

---

## 7. 诊断命令

```bash
# 完整诊断
diagnose_worktrees() {
    local repo="${1:-.}"
    echo "=== Git Worktree List ==="
    git -C "$repo" worktree list --porcelain
    echo ""
    echo "=== Admin Directories ==="
    ls -la "$(git -C "$repo" rev-parse --git-dir)/worktrees/" 2>/dev/null || echo "None"
    echo ""
    echo "=== Disk Usage ==="
    du -sh "$(git -C "$repo" rev-parse --git-dir)/worktrees/" 2>/dev/null
    echo ""
    echo "=== Lock Files ==="
    find "$(git -C "$repo" rev-parse --git-dir)/worktrees/" -name "*.lock" 2>/dev/null
}
```

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08