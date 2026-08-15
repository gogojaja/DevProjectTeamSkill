---
name: "worktree-isolation"
description: "用户提到 worktree 隔离、并行开发环境、多任务隔离、git worktree、PSM、Teleport时加载本 worktree 隔离层技能：基于 git worktree 的并行开发环境管理，支持 issue/PR/feature 多任务隔离，内置会话注册表、tmux 整合、项目别名、GitHub/Jira 提供商。用户说 worktree/并行环境隔离时加载。"
---

# Worktree Isolation 工作樹隔離層

> 版權聲明：`../../references/COPYRIGHT.md`　Token 標準：`../../references/token_standard.md`　編排器：`../SKILL.md`

---

## 1. 觸發規則

### 1.1 觸發場景
- 用戶需要同時處理多個 issue/PR/feature，要求環境隔離互不干擾
- 需要在同一倉庫中並行開發多個功能分支
- PR 審查時需要乾淨的 checkout 環境
- 熱修復與功能開發並行，需獨立 worktree

### 1.2 觸發詞
| 關鍵字 | 映射命令 | 說明 |
|--------|----------|------|
| `worktree` / `wt` | 通用入口 | 列出/創建/切換/清理 worktree |
| `psm` / `project-session-manager` | 完整會話管理 | worktree + tmux + 註冊表 + 專案別名 |
| `teleport` | 輕量 worktree | 僅創建 worktree，不建立 tmux 會話 |
| `fix <ref>` | Issue 修復會話 | 基於 issue 創建隔離環境 |
| `review <ref>` | PR 審查會話 | 基於 PR 創建隔離環境 |
| `feature <name>` | 功能開發會話 | 創建功能分支 worktree |

### 1.3 觸發詞 → 行為映射
```yaml
worktree:
  list: "wt list"
  create: "wt create <branch> [path]"
  switch: "wt switch <session-id>"
  remove: "wt remove <session-id>"
  cleanup: "wt cleanup"

psm:
  fix: "psm fix <ref>"           # issue/PR/URL/別名
  review: "psm review <ref>"
  feature: "psm feature <proj> <name>"
  list: "psm list [project]"
  attach: "psm attach <session>"
  kill: "psm kill <session>"
  cleanup: "psm cleanup"
  status: "psm status"

teleport:
  create: "teleport <ref|name>"  # issue/PR/feature
  list: "teleport list"
  remove: "teleport remove <id>"
```

---

## 2. 流程

### 2.1 Worktree 生命週期
```mermaid
graph LR
  A[解析引用] --> B[獲取遠端信息]
  B --> C[確保本地倉庫存在]
  C --> D[創建/獲取分支]
  D --> E[git worktree add]
  E --> F[寫入會話元數據]
  F --> G[可選：創建 tmux 會話]
  G --> H[可選：啟動編輯器/CLI]
  H --> I[註冊到會話表]
  I --> J[輸出連接信息]
```

### 2.2 會話註冊表
存放位置：`~/.psm/sessions.json`
```json
{
  "version": 1,
  "sessions": {
    "omc:pr-123": {
      "id": "omc:pr-123",
      "type": "review",
      "project": "omc",
      "ref": "pr-123",
      "branch": "feature/webhooks",
      "base": "main",
      "created_at": "2026-08-08T10:00:00Z",
      "tmux_session": "psm:omc:pr-123",
      "worktree_path": "/home/user/.psm/worktrees/omc/pr-123",
      "source_repo": "/home/user/Workspace/opencode-senate",
      "github": {"pr_number": 123, "pr_title": "Add webhooks", "pr_author": "user", "pr_url": "https://github.com/..."},
      "state": "active"
    }
  },
  "stats": {"total_created": 42, "total_cleaned": 38}
}
```

### 2.3 專案別名配置
位置：`~/.psm/projects.json`
```json
{
  "aliases": {
    "omc": {
      "repo": "senate/opencode-senate",
      "local": "~/Workspace/opencode-senate",
      "default_base": "main",
      "provider": "github"
    },
    "mywork": {
      "jira_project": "MYPROJ",
      "repo": "mycompany/my-project",
      "local": "~/Workspace/my-project",
      "default_base": "develop",
      "provider": "jira"
    }
  },
  "defaults": {
    "worktree_root": "~/.psm/worktrees",
    "cleanup_after_days": 14,
    "auto_cleanup_merged": true
  }
}
```

### 2.4 提供商抽象
| 提供商 | CLI | 支援命令 | 引用格式 |
|--------|-----|----------|----------|
| GitHub | `gh` | fix, review, feature | `owner/repo#123`, `alias#123`, URL |
| Jira | `jira` | fix, feature | `PROJ-123`, `alias#123` |

---

## 3. 輸出規範

### 3.1 會話元數據
每個 worktree 根目錄包含 `.psm-session.json`：
```json
{
  "id": "omc:pr-123",
  "type": "review",
  "project": "omc",
  "ref": "pr-123",
  "branch": "feature/webhooks",
  "base": "main",
  "created_at": "2026-08-08T10:00:00Z",
  "tmux_session": "psm:omc:pr-123",
  "worktree_path": "/home/user/.psm/worktrees/omc/pr-123",
  "source_repo": "/home/user/Workspace/opencode-senate",
  "github": {"pr_number": 123, "pr_title": "Add webhooks", "pr_author": "user", "pr_url": "https://github.com/..."},
  "state": "active"
}
```

### 3.2 清理報告
```text
Cleanup complete:
  Removed: omc:pr-123 (merged)
  Removed: omc:issue-42 (closed)
  Kept: omc:feat-auth (active)
```

### 3.3 狀態輸出
```text
Current Session: omc:pr-123
Type: review
PR: #123 - Add webhook support
Branch: feature/webhooks
Created: 2 hours ago
Worktree: ~/.psm/worktrees/omc/pr-123
Tmux: psm:omc:pr-123
```

---

## 4. 邊界

### 4.1 適用邊界
- ✅ 同倉庫多任務並行開發
- ✅ PR 審查需要乾淨環境
- ✅ 熱修復與功能開發並行
- ✅ 多專案別名管理

### 4.2 不適用邊界
- ❌ 單任務開發（直接在主 worktree 工作即可）
- ❌ 無 git 倉庫的項目
- ❌ 不支援 tmux 的環境（可用 teleport 純 worktree 模式）

### 4.3 資源限制
- worktree 根目錄：`~/.psm/worktrees/`（可配置）
- 自動清理：默認 14 天未活躍或 PR merged/issue closed
- 最大並發會話：受限於磁盤空間與 tmux 會話數

---

## 5. 明細外置

| 明細文件 | 說明 |
|----------|------|
| `domain/psm-protocol.md` | PSM 完整協議：子命令解析、引用解析、會話創建/掛載/清理流程 |
| `domain/teleport.md` | Teleport 輕量命令：worktree 創建/列表/移除、與 PSM 差異對比 |
| `domain/providers.md` | GitHub/Jira 提供商實現：CLI 調用、引用解析、認證配置 |
| `domain/session-registry.md` | 會話註冊表結構、CRUD、狀態機、併發安全 |
| `domain/worktree-ops.md` | git worktree 底層操作：創建/切換/移除/遷移/清理、錯誤處理 |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08
**知識產權所有**: 段波（驗證郵箱: duanbo.douglas@163.com）