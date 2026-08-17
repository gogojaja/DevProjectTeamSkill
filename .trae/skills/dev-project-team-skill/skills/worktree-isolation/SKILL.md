---
name: "worktree-isolation"
description: "用户提到 worktree 隔离、并行开发环境、多任务隔离、git worktree、PSM、Teleport时加载本 worktree 隔离层技能：基于 git worktree 的并行开发环境管理，支持 issue/PR/feature 多任务隔离，内置会话注册表、tmux 整合、项目别名、GitHub/Jira 提供商。用户说 worktree/并行环境隔离时加载。"
---

# Worktree Isolation 工作树隔离层

- **技能版本**：v1.1.0　**发布日期**：2026-08-18

> 版权声明：`../../../references/COPYRIGHT.md`　Token 标准：`../../../references/token_standard.md`　编排器：`../../SKILL.md`

---

## 1. 触发规则

### 1.1 触发场景
- 用户需要同时处理多个 issue/PR/feature，要求环境隔离互不干扰
- 需要在同一仓库中并行开发多个功能分支
- PR 审查时需要干净的 checkout 环境
- 热修复与功能开发并行，需独立 worktree

### 1.2 触发词
| 关键字 | 映射命令 | 说明 |
|--------|----------|------|
| `worktree` / `wt` | 通用入口 | 列出/创建/切换/清理 worktree |
| `psm` / `project-session-manager` | 完整会话管理 | worktree + tmux + 注册表 + 专案别名 |
| `teleport` | 轻量 worktree | 仅创建 worktree，不建立 tmux 会话 |
| `fix <ref>` | Issue 修复会话 | 基于 issue 创建隔离环境 |
| `review <ref>` | PR 审查会话 | 基于 PR 创建隔离环境 |
| `feature <name>` | 功能开发会话 | 创建功能分支 worktree |

### 1.3 触发词 → 行为映射
```yaml
worktree:
  list: "wt list"
  create: "wt create <branch> [path]"
  switch: "wt switch <session-id>"
  remove: "wt remove <session-id>"
  cleanup: "wt cleanup"

psm:
  fix: "psm fix <ref>"           # issue/PR/URL/别名
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

### 2.1 Worktree 生命周期
```mermaid
graph LR
  A[解析引用] --> B[获取远端信息]
  B --> C[确保本地仓库存在]
  C --> D[创建/获取分支]
  D --> E[git worktree add]
  E --> F[写入会话元数据]
  F --> G[可选：创建 tmux 会话]
  G --> H[可选：启动编辑器/CLI]
  H --> I[注册到会话表]
  I --> J[输出连接信息]
```

### 2.2 会话注册表
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

### 2.3 专案别名配置
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

## 3. 输出规范

### 3.1 会话元数据
每个 worktree 根目录包含 `.psm-session.json`：
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

### 3.2 清理报告
```text
Cleanup complete:
  Removed: omc:pr-123 (merged)
  Removed: omc:issue-42 (closed)
  Kept: omc:feat-auth (active)
```

### 3.3 状态输出
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

## 4. 边界

### 4.1 适用边界
- ✅ 同仓库多任务并行开发
- ✅ PR 审查需要干净环境
- ✅ 热修复与功能开发并行
- ✅ 多专案别名管理

### 4.2 不适用边界
- ❌ 单任务开发（直接在主 worktree 工作即可）
- ❌ 无 git 仓库的项目
- ❌ 不支援 tmux 的环境（可用 teleport 纯 worktree 模式）

### 4.3 资源限制
- worktree 根目录：`~/.psm/worktrees/`（可配置）
- 自动清理：默认 14 天未活跃或 PR merged/issue closed
- 最大并发会话：受限于磁盘空间与 tmux 会话数

---

## 5. 明细外置

| 明细文件 | 说明 |
|----------|------|
| `domain/psm-protocol.md` | PSM 完整协议：子命令解析、引用解析、会话创建/挂载/清理流程 |
| `domain/teleport.md` | Teleport 轻量命令：worktree 创建/列表/移除、与 PSM 差异对比 |
| `domain/providers.md` | GitHub/Jira 提供商实现：CLI 调用、引用解析、认证配置 |
| `domain/session-registry.md` | 会话注册表结构、CRUD、状态机、并发安全 |
| `domain/worktree-ops.md` | git worktree 底层操作：创建/切换/移除/迁移/清理、错误处理 |

---

---

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求 worktree 并行开发环境隔离/创建/清理、多任务隔离、会话注册（`worktree`/`并行环境隔离`/`PSM`/`Teleport`）；
- 前置：已登记项目别名与 base 分支；明确任务/issue/PR 归属与并行边界；
- 不适用：单仓库单任务开发、无需环境隔离的小改动、用户未要求多任务隔离时不强制创建。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | 用户触发 worktree 操作 | 用户确认/系统启动 | 解析任务（issue/PR/feature）与目标别名 |
| 执行中 | worktree 创建/切换中 | 环境就绪/失败 | 按 `domain/worktree-ops.md` 创建、注册会话元数据 |
| 校验中 | 环境就绪 | 验证通过/失败 | 校验 worktree 与 session 注册一致性、tmux 附件 |
| 阻塞 | 端口/分支/仓库冲突 | 冲突解决/人工介入 | 暂停并记录冲突原因 |
| 完成 | 环境验证通过 | 进入开发/交接 | 更新 session 注册表与断点 |
| 回退 | 创建失败/冲突 | 回到稳定环境 | 移除失败 worktree，保留审计 |

### 3. 执行动作层
- 执行步骤 1：登记任务 → 解析别名/base 分支（`domain/psm-protocol.md`）；
- 执行步骤 2：`git worktree add` 创建隔离环境，写 `.psm-session.json`；
- 执行步骤 3：可选 attach tmux 会话；任务完成/PR 合并后清理；
- 所需工具/脚本：`domain/worktree-ops.md`、`domain/session-registry.md`、`domain/psm-protocol.md`、`domain/teleport.md`；
- 输入输出约束：worktree 路径 `.psm/worktrees/<project>/<task>`；会话元数据 JSON 存 `.psm-session.json`；清除后必须从注册表移除。

### 4. 验收门禁
- 必须产出物：worktree 工作区 + 会话元数据（id/type/branch/base/github）+ 注册表条目；
- 通过条件：worktree 干净创建 + 分支正确 + session 注册一致 + 无资源泄漏；
- 失败条件：分支冲突、base 漂移、session 元数据缺失、worktree 残留、tmux 挂死；
- 审核对象：项目负责人/工具维护者。

### 5. 失败处理
- 失败类型：分支已存在、端口被占、worktree 路径冲突、teleport 超时；
- 恢复策略：改名/换路径/清理冲突 worktree（`domain/worktree-ops.md` 错误处理）；
- 回滚方案：`worktree remove` 移除失败环境，恢复注册表；
- 重试策略：解除冲突后重试，禁止强制覆盖在用 worktree；
- 是否需要人工确认：删除他人 worktree、跨项目 create、生产分支操作需人工确认。

### 6. 产出与交接
- 产出物列表：隔离 worktree、会话元数据、清理报告、session 注册表更新；
- 保存路径：`.psm/` 注册表、各 worktree `.psm-session.json`、交接断点；
- 交接对象：任务开发角色、PR 评审者、工具维护者；
- 下一步动作：环境就绪 → 开发；任务完成 → 提交+PR；合并 → 清理；
- 归档条件：worktree 已清理、注册表一致、无孤儿会话。

### 7. 审计记录
- 执行时间：worktree 生命周期（创建→清理）；
- 关键参数：session id、project、branch、worktree path（脱敏）、PR number；
- 关键决策：别名解析、base 分支选择、冲突处理方式；
- 结果证据：`.psm-session.json`、清理报告、注册表快照；
- 失败原因：创建失败/冲突在台账或断点区留痕。

---

**文档版本**：v1.1.0　**最后更新**：2026-08-18（繁体转简体 + 新增闭环执行系统章节，技能库本体评审修复）

**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）