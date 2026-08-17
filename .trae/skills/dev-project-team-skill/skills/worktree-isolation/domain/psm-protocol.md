# PSM 协议：完整会话管理流程

> 编排器：`../SKILL.md`

---

## 1. 参数解析

### 1.1 子命令识别
```bash
# 支援格式
psm <subcommand> <ref> [options]

subcommand ∈ {review, fix, feature, list, attach, kill, cleanup, status}
ref ∈ {alias#num, owner/repo#num, URL, #num, project:name}
options: --branch, --base, --no-claude, --no-tmux, --json
```

### 1.2 引用解析优先级
1. `alias#num` → 别名配置 → 解析 repo + provider
2. `owner/repo#num` → 直接使用
3. `https://github.com/owner/repo/(pull|issues)/num` → 解析 owner/repo/num
4. `#num` → 当前目录 git remote 推断 repo
5. `project:name` → feature 模式专用

---

## 2. 子命令流程

### 2.1 `psm review <ref>` — PR 审查会话

```bash
# 步骤 1: 解析引用
ref="omc#123" → project="omc", pr_number=123, provider="github"

# 步骤 2: 读取专案配置
cat ~/.psm/projects.json | jq '.aliases["omc"]'
# {"repo":"senate/opencode-senate","local":"~/Workspace/opencode-senate","default_base":"main","provider":"github"}

# 步骤 3: 获取 PR 信息
gh pr view 123 --repo senate/opencode-senate \
  --json number,title,author,headRefName,baseRefName,body,files,url

# 步骤 4: 确保本地仓库存在
if [[ ! -d "$local_path" ]]; then
  git clone "https://github.com/senate/opencode-senate.git" "$local_path"
fi

# 步骤 5: 创建 worktree
cd "$local_path"
git fetch origin "pull/123/head:pr-123-review"
worktree_path="$HOME/.psm/worktrees/omc/pr-123"
git worktree add "$worktree_path" "pr-123-review"

# 步骤 6: 创建会话元数据
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

# 步骤 7: 更新会话注册表
# 读取 ~/.psm/sessions.json → 新增/更新 → 写回

# 步骤 8: 创建 tmux 会话
tmux new-session -d -s "psm:omc:pr-123" -c "$worktree_path"

# 步骤 9: 启动编辑器 (除非 --no-claude)
tmux send-keys -t "psm:omc:pr-123" "claude" Enter

# 步骤 9: 输出会话信息
echo "Session ready! ID: omc:pr-123, Worktree: $worktree_path, Tmux: psm:omc:pr-123"
```

### 2.2 `psm fix <ref>` — Issue 修复会话

```bash
# 1-3 步同 review，使用 gh issue view 获取信息

# 步骤 4: 创建功能分支
cd "$local_path"
git fetch origin main
branch_name="fix/123-$(echo "$title" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | head -c 30)"
git checkout -b "$branch_name" origin/main

# 步骤 5: 创建 worktree
worktree_path="$HOME/.psm/worktrees/omc/issue-123"
git worktree add "$worktree_path" "$branch_name"

# 步骤 6-9: 创建元数据、注册、tmux、启动 (type="fix")
```

### 2.3 `psm feature <project> <name>` — 功能开发

```bash
# 1. 解析专案 (alias 或路径)
# 2. 创建 feature 分支
branch_name="feature/$feature_name"
git checkout -b "$branch_name" origin/main

# 3. 创建 worktree
worktree_path="$HOME/.psm/worktrees/omc/feat-$feature_name"
git worktree add "$worktree_path" "$branch_name"

# 后续同 fix (type="feature")
```

### 2.4 `psm list [project]` — 列出会话

```bash
# 1. 读取会话注册表
cat ~/.psm/sessions.json

# 2. 检查 tmux 会话状态
tmux list-sessions -F "#{session_name}" 2>/dev/null | grep "^psm:"

# 3. 检查 worktree 存在性
ls -la ~/.psm/worktrees/omc/

# 3. 格式化输出
echo "Active PSM Sessions:"
printf "%-20s | %-8s | %-8s | %s\n" "ID" "Type" "Status" "Worktree"
for session in ...; do
  printf "%-20s | %-8s | %-8s | %s\n" "$id" "$type" "$status" "$worktree_path"
done
```

### 2.5 `psm attach <session>` — 挂载会话

```bash
# 1. 解析 session ID
# 2. 验证 tmux 会话存在
tmux has-session -t "psm:$session_id" 2>/dev/null

# 3. 挂载
tmux attach -t "psm:$session_id"
```

### 2.6 `psm kill <session>` — 终止会话

```bash
# 1. 杀死 tmux 会话
tmux kill-session -t "psm:$session_id" 2>/dev/null

# 2. 移除 worktree
worktree_path=$(jq -r ".sessions[\"$session_id\"].worktree_path" ~/.psm/sessions.json)
source_repo=$(jq -r ".sessions[\"$session_id\"].source_repo" ~/.psm/sessions.json)
cd "$source_repo"
git worktree remove "$worktree_path" --force

# 3. 更新注册表 (移除该 session)
```

### 2.7 `psm cleanup` — 清理已合并/关闭

```bash
# 1. 读取所有 sessions
# 2. 对每个 PR session，检查是否 merged
gh pr view <pr_number> --repo <repo> --json merged,state
# 3. 对每个 issue session，检查是否 closed
gh issue view <issue_number> --repo <repo> --json closed,state
# 4. 清理 merged/closed sessions (kill + 更新注册表)
# 5. 报告结果
```

### 2.8 `psm status` — 当前会话状态

```bash
# 1. 检测当前会话 (tmux session name 或 cwd 在 worktree 内)
# 2. 读取 .psm-session.json
# 3. 显示状态信息
```

---

## 3. 错误处理

| 错误 | 解决策略 |
|------|----------|
| Worktree 已存在 | 提供：attach / 重建 / 中止 选项 |
| PR/issue 不存在 | 验证 URL/编号，检查权限 |
| 无 tmux | 警告并跳过会话创建 (可用 teleport) |
| 无 gh CLI | 报错并给出安装指引 |
| Worktree 被占用 | `git worktree remove --force` 后重试 |

---

## 4. 并发安全

```bash
# 会话注册表操作加锁
SESSION_LOCK="$HOME/.psm/sessions.lock"
exec 200>"$SESSION_LOCK"
flock -x 200
# ... 读取/写入 sessions.json ...
flock -u 200
```

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08