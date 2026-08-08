# Git Worktree 底層操作

> 編排器：`../SKILL.md`　上位：PSM 協議、Teleport

---

## 1. 基礎操作

### 1.1 創建 Worktree
```bash
# 語法
git worktree add [-f] [--detach] [-b <new-branch>] <path> [<commit-ish>]

# 示例
git worktree add ../feature-auth feature/auth          # 從現有分支
git worktree add ../pr-123 pr-123-review              # 從已獲取的 PR ref
git worktree add -b hotfix/urgent ../hotfix main      # 新建分支並創建 worktree
git worktree add --detach ../detached HEAD            # 分離 HEAD 模式
```

### 1.2 列出 Worktree
```bash
git worktree list
# 輸出格式:
# /path/to/main      abcd1234 [main]
# /path/to/feature   efgh5678 [feature/auth]
# /path/to/pr-123    ijkl9012 [pr-123-review]
```

### 1.3 移除 Worktree
```bash
# 正常移除 (要求 worktree 乾淨)
git worktree remove <path>

# 強制移除 (忽略未提交變更)
git worktree remove --force <path>

# 移除並清理管理文件
git worktree remove <path> && git worktree prune
```

### 1.4 修剪失效記錄
```bash
git worktree prune [-v] [--expire <time>]
# 移除 .git/worktrees/ 下已刪除目錄的管理文件
```

---

## 2. PR/Workflow 專用操作

### 2.1 獲取 PR Ref 並創建 Worktree
```bash
# 1. 獲取 PR 信息
gh pr view 123 --repo owner/repo --json number,title,headRefName,baseRefName

# 2. Fetch PR ref (GitHub 專用)
git fetch origin "pull/123/head:pr-123-review"

# 3. 創建 worktree
git worktree add ~/.psm/worktrees/owner/repo/pr-123 pr-123-review

# 完整腳本
create_pr_worktree() {
    local pr_number="$1"
    local repo="$2"
    local worktree_root="${3:-$HOME/.psm/worktrees}"
    
    # 獲取 PR 信息
    local pr_info=$(gh pr view "$pr_number" --repo "$repo" --json number,title,headRefName,baseRefName)
    local base_branch=$(echo "$pr_info" | jq -r '.baseRefName')
    
    # Fetch PR ref
    git -C "$local_repo" fetch origin "pull/$pr_number/head:pr-$pr_number-review"
    
    # 創建 worktree
    local worktree_path="$worktree_root/$(echo $repo | tr '/' '_')/pr-$pr_number"
    git -C "$local_repo" worktree add "$worktree_path" "pr-$pr_number-review"
    
    echo "$worktree_path"
}
```

### 2.2 Issue 修復 Worktree
```bash
create_issue_worktree() {
    local issue_number="$1"
    local repo="$2"
    local base_branch="${3:-main}"
    
    # 獲取 issue 信息
    local issue_info=$(gh issue view "$issue_number" --repo "$repo" --json number,title)
    local title=$(echo "$issue_info" | jq -r '.title')
    local branch_name="fix/$issue_number-$(echo "$title" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | head -c 30)"
    
    # 確保 base 分支最新
    git -C "$local_repo" fetch origin "$base_branch"
    
    # 創建分支
    git -C "$local_repo" checkout -b "$branch_name" "origin/$base_branch"
    
    # 創建 worktree
    local worktree_path="$worktree_root/$(echo $repo | tr '/' '_')/issue-$issue_number"
    git -C "$local_repo" worktree add "$worktree_path" "$branch_name"
    
    echo "$worktree_path"
}
```

---

## 3. 遷移與修復

### 3.1 Worktree 遷移 (移動路徑)
```bash
# Git 2.30+ 支援 --move
git worktree move <old-path> <new-path>

# 舊版本手動遷移
migrate_worktree() {
    local old_path="$1"
    local new_path="$2"
    
    # 1. 獲取 worktree 關聯的分支
    local branch=$(git -C "$old_path" branch --show-current)
    
    # 2. 移除舊 worktree (保留分支)
    git worktree remove "$old_path"
    
    # 3. 在新位置創建
    git worktree add "$new_path" "$branch"
}
```

### 3.2 修復損壞的 Worktree
```bash
repair_worktree() {
    local path="$1"
    
    # 1. 檢查 .git 文件
    if [[ ! -f "$path/.git" ]]; then
        echo "Not a worktree: $path"
        return 1
    fi
    
    # 2. 讀取 .git 內容
    local git_dir=$(cat "$path/.git" | sed 's/gitdir: //')
    
    # 3. 檢查 .git/worktrees/ 管理目錄
    local wt_name=$(basename "$path")
    local admin_dir="$(dirname "$git_dir")/worktrees/$wt_name"
    
    if [[ ! -d "$admin_dir" ]]; then
        echo "Worktree admin dir missing, re-registering..."
        # 重新註冊
        local branch=$(git -C "$path" branch --show-current)
        git worktree remove "$path" 2>/dev/null || true
        git worktree add "$path" "$branch"
    fi
}
```

---

## 4. 錯誤處理與常見問題

### 4.1 常見錯誤代碼

| 錯誤 | 原因 | 解決 |
|------|------|------|
| `fatal: 'path' already exists` | 目標路徑已存在 | 使用其他路徑或先移除 |
| `fatal: 'branch' is already checked out at 'path'` | 分支已在別處 checkout | 先移除舊 worktree 或用其他分支 |
| `fatal: not a valid worktree` | 管理文件損壞 | `git worktree prune` 後重試 |
| `fatal: cannot lock ref` | 併發操作衝突 | 重試或檢查鎖文件 |
| `not a valid worktree: path` | worktree 目錄被手動刪除 | `git worktree prune` 清理 |

### 4.2 併發安全
```bash
# worktree 操作加鎖
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

## 5. 性能優化

### 5.1 共享 Object Database
```bash
# 所有 worktree 共享 .git/objects，節省空間
# 檢查共享情況
du -sh .git/objects
du -sh .git/worktrees/*/
```

### 5.2 批量操作
```bash
# 批量創建 worktree (避免重複 fetch)
batch_create_worktrees() {
    local repo="$1"
    shift
    local branches=("$@")
    
    # 一次性 fetch 所有需要的 refs
    git -C "$repo" fetch origin "${branches[@]}"
    
    # 並行創建 worktree (背景任務)
    for branch in "${branches[@]}"; do
        git -C "$repo" worktree add "$worktree_root/$(echo $branch | tr '/' '_')" "$branch" &
    done
    wait
}
```

### 5.3 清理策略
```bash
# 定期清理失效 worktree 記錄
git worktree prune --expire 30.days.ago

# 清理已合併分支的 worktree
cleanup_merged_worktrees() {
    local repo="$1"
    local main_branch="${2:-main}"
    
    # 找出已合併的分支
    git -C "$repo" branch --merged "$main_branch" | grep -v "^\*\|$main_branch" | while read branch; do
        # 找到使用該分支的 worktree
        local wt_path=$(git -C "$repo" worktree list --porcelain | awk -v b="$branch" '$1=="worktree"{w=$2} $1=="branch" && $2==b{print w}')
        if [[ -n "$wt_path" ]]; then
            echo "Removing merged worktree: $wt_path ($branch)"
            git -C "$repo" worktree remove "$wt_path" --force
        fi
    done
}
```

---

## 6. 跨平台注意事項

| 平台 | 注意事項 |
|------|----------|
| Linux/macOS | 完整支援，符號鏈接正常 |
| Windows (Git Bash/WSL) | 支援，需啟用 `core.symlinks=true` |
| Windows (CMD/PowerShell) | 部分命令需調整路徑分隔符 |
| 無符號鏈接權限 | 設置 `git config core.symlinks false` 使用副本模式 |

---

## 7. 診斷命令

```bash
# 完整診斷
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

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08