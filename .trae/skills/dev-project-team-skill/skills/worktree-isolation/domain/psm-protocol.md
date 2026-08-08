# PSM 協議：完整會話管理流程

> 編排器：`../SKILL.md`

---

## 1. 參數解析

### 1.1 子命令識別
```bash
# 支援格式
psm <subcommand> <ref> [options]

subcommand ∈ {review, fix, feature, list, attach, kill, cleanup, status}
ref ∈ {alias#num, owner/repo#num, URL, #num, project:name}
options: --branch, --base, --no-claude, --no-tmux, --json
```

### 1.2 引用解析優先級
1. `alias#num` → 別名配置 → 解析 repo + provider
2. `owner/repo#num` → 直接使用
3. `https://github.com/owner/repo/(pull|issues)/num` → 解析 owner/repo/num
4. `#num` → 當前目錄 git remote 推斷 repo
5. `project:name` → feature 模式專用

---

## 2. 子命令流程

### 2.1 `psm review <ref>` — PR 審查會話

```bash
# 步驟 1: 解析引用
ref="omc#123" → project="omc", pr_number=123, provider="github"

# 步驟 2: 讀取專案配置
cat ~/.psm/projects.json | jq '.aliases["omc"]'
# {"repo":"senate/opencode-senate","local":"~/Workspace/opencode-senate","default_base":"main","provider":"github"}

# 步驟 3: 獲取 PR 信息
gh pr view 123 --repo senate/opencode-senate \
  --json number,title,author,headRefName,baseRefName,body,files,url

# 步驟 4: 確保本地倉庫存在
if [[ ! -d "$local_path" ]]; then
  git clone "https://github.com/senate/opencode-senate.git" "$local_path"
fi

# 步驟 5: 創建 worktree
cd "$local_path"
git fetch origin "pull/123/head:pr-123-review"
worktree_path="$HOME/.psm/worktrees/omc/pr-123"
git worktree add "$worktree_path" "pr-123-review"

# 步驟 6: 創建會話元數據
cat > "$worktree_path/.psm-session.json" << EOF
{
  "id": "omc:pr-123",
  "type": "review",
  "project": "omc",
  "ref": "pr-123",
  "branch": "feature/webhooks",
  "base": "main",
  "created_at": "$(date -Iseconds)",
  "tmux_session": "psm:omc:pr-123",
  "worktree_path": "$worktree_path",
  "source_repo": "$local_path",
  "github": {"pr_number": 123, "pr_title": "Add webhooks", "pr_author": "user", "pr_url": "https://github.com/..."},
  "state": "active"
}
EOF

# 步驟 7: 更新會話註冊表
# 讀取 ~/.psm/sessions.json → 新增/更新 → 寫回

# 步驟 8: 創建 tmux 會話
tmux new-session -d -s "psm:omc:pr-123" -c "$worktree_path"

# 步驟 9: 啟動編輯器 (除非 --no-claude)
tmux send-keys -t "psm:omc:pr-123" "claude" Enter

# 步驟 9: 輸出會話信息
echo "Session ready! ID: omc:pr-123, Worktree: $worktree_path, Tmux: psm:omc:pr-123"
```

### 2.2 `psm fix <ref>` — Issue 修復會話

```bash
# 1-3 步同 review，使用 gh issue view 獲取信息

# 步驟 4: 創建功能分支
cd "$local_path"
git fetch origin main
branch_name="fix/123-$(echo "$title" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | head -c 30)"
git checkout -b "$branch_name" origin/main

# 步驟 5: 創建 worktree
worktree_path="$HOME/.psm/worktrees/omc/issue-123"
git worktree add "$worktree_path" "$branch_name"

# 步驟 6-9: 創建元數據、註冊、tmux、啟動 (type="fix")
```

### 2.3 `psm feature <project> <name>` — 功能開發

```bash
# 1. 解析專案 (alias 或路徑)
# 2. 創建 feature 分支
branch_name="feature/$feature_name"
git checkout -b "$branch_name" origin/main

# 3. 創建 worktree
worktree_path="$HOME/.psm/worktrees/omc/feat-$feature_name"
git worktree add "$worktree_path" "$branch_name"

# 後續同 fix (type="feature")
```

### 2.4 `psm list [project]` — 列出會話

```bash
# 1. 讀取會話註冊表
cat ~/.psm/sessions.json

# 2. 檢查 tmux 會話狀態
tmux list-sessions -F "#{session_name}" 2>/dev/null | grep "^psm:"

# 3. 檢查 worktree 存在性
ls -la ~/.psm/worktrees/omc/

# 3. 格式化輸出
echo "Active PSM Sessions:"
printf "%-20s | %-8s | %-8s | %s\n" "ID" "Type" "Status" "Worktree"
for session in ...; do
  printf "%-20s | %-8s | %-8s | %s\n" "$id" "$type" "$status" "$worktree_path"
done
```

### 2.5 `psm attach <session>` — 掛載會話

```bash
# 1. 解析 session ID
# 2. 驗證 tmux 會話存在
tmux has-session -t "psm:$session_id" 2>/dev/null

# 3. 掛載
tmux attach -t "psm:$session_id"
```

### 2.6 `psm kill <session>` — 終止會話

```bash
# 1. 殺死 tmux 會話
tmux kill-session -t "psm:$session_id" 2>/dev/null

# 2. 移除 worktree
worktree_path=$(jq -r ".sessions[\"$session_id\"].worktree_path" ~/.psm/sessions.json)
source_repo=$(jq -r ".sessions[\"$session_id\"].source_repo" ~/.psm/sessions.json)
cd "$source_repo"
git worktree remove "$worktree_path" --force

# 3. 更新註冊表 (移除該 session)
```

### 2.7 `psm cleanup` — 清理已合併/關閉

```bash
# 1. 讀取所有 sessions
# 2. 對每個 PR session，檢查是否 merged
gh pr view <pr_number> --repo <repo> --json merged,state
# 3. 對每個 issue session，檢查是否 closed
gh issue view <issue_number> --repo <repo> --json closed,state
# 4. 清理 merged/closed sessions (kill + 更新註冊表)
# 5. 報告結果
```

### 2.8 `psm status` — 當前會話狀態

```bash
# 1. 檢測當前會話 (tmux session name 或 cwd 在 worktree 內)
# 2. 讀取 .psm-session.json
# 3. 顯示狀態信息
```

---

## 3. 錯誤處理

| 錯誤 | 解決策略 |
|------|----------|
| Worktree 已存在 | 提供：attach / 重建 / 中止 選項 |
| PR/issue 不存在 | 驗證 URL/編號，檢查權限 |
| 無 tmux | 警告並跳過會話創建 (可用 teleport) |
| 無 gh CLI | 報錯並給出安裝指引 |
| Worktree 被佔用 | `git worktree remove --force` 後重試 |

---

## 4. 併發安全

```bash
# 會話註冊表操作加鎖
SESSION_LOCK="$HOME/.psm/sessions.lock"
exec 200>"$SESSION_LOCK"
flock -x 200
# ... 讀取/寫入 sessions.json ...
flock -u 200
```

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08