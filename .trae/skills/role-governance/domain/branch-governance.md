# 分支统一治理规范

> **铁律**：所有项目在所有机器上只使用 `main` 分支，禁止创建/推送其他分支。

## 1. 策略概述

### 1.1 单一分支原则
- 所有开发、修复、文档变更均在 `main` 分支进行
- 不使用 feature 分支、develop 分支、release 分支
- 不使用 `master`（历史遗留已统一迁移到 `main`）

### 1.2 适用范围
- **项目**：TwinForge 及所有子项目（dev-* 系列）
- **机器**：Mac mini / Dell / Huawei / 任意新增节点
- **副本**：主工作区 + 运行时副本

## 2. 治理工具

### 2.1 审计脚本
**位置**：`TwinForge/scripts/branch_governance.sh`

```bash
# 审计模式（只检查不修改）
./scripts/branch_governance.sh

# 强制修复模式（自动删除非 main 分支、清理残留引用）
./scripts/branch_governance.sh --enforce

# 安静模式（只输出异常项）
./scripts/branch_governance.sh --quiet

# 指定项目
./scripts/branch_governance.sh --project TwinForge
```

**检查项**：
1. 当前分支是否为 `main`
2. 是否存在本地非 main 分支
3. 是否存在远端残留引用（如 `origin/master`）
4. 远端是否存在非 main 分支

### 2.2 Pre-push Hook
**位置**：`TwinForge/scripts/hooks/pre-push`

**安装**：
```bash
./scripts/install_branch_hooks.sh           # 安装到所有项目
./scripts/install_branch_hooks.sh --uninstall  # 卸载
```

**效果**：在非 main 分支执行 `git push` 时被拦截：
```
❌ 分支治理拦截：当前分支=feature-xxx

本项目执行单一分支策略，所有工作必须在 main 分支进行。

修复方法：
  git checkout main
  git merge feature-xxx
  git branch -d feature-xxx
  git push origin main
```

## 3. 日常工作流

### 3.1 标准流程
```bash
# 1. 开始工作前，确保在 main 分支
git checkout main
git pull --rebase origin main

# 2. 工作（直接在 main 上提交）
git add -A
git commit -m "说明"

# 3. 三推同步
git push origin main
git push gitee main
git push mac main

# 4. 同步运行时副本
cd ~/projects/<repo>
git fetch origin && git reset --hard origin/main
```

### 3.2 多机器协作
1. **机器 A 提交** → 三推到远端
2. **机器 B 拉取** → `git pull --rebase origin main`
3. **永远不要**在本地创建新分支

### 3.3 冲突处理
```bash
# 如果 pull --rebase 失败
git rebase --abort
git stash                    # 暂存本地改动
git pull --rebase origin main
git stash pop                # 恢复本地改动

# 如果仍有冲突，手动解决后
git add .
git rebase --continue
```

## 4. 新节点接入

在新机器上初始化工作区时：

```bash
# 1. 克隆代码（自动使用 main 分支）
git clone <url>
cd <repo>

# 2. 安装分支治理 hook
<path-to-TwinForge>/scripts/install_branch_hooks.sh

# 3. 验证
<path-to-TwinForge>/scripts/branch_governance.sh --project <repo>
```

## 5. 违规处理

| 场景 | 处理 |
|------|------|
| 本地意外创建分支 | `git checkout main && git branch -D <branch>` |
| 推送到非 main 远端分支 | `git push origin --delete <branch>` |
| Hook 被绕过 | 下次运行 `branch_governance.sh --enforce` 自动修复 |

## 6. 审计频率

| 触发 | 方式 |
|------|------|
| 每日 09:00 | nightly_verify.sh 自动运行 |
| 每周日 04:45 | cmdb_audit 检查分支一致性 |
| 手动 | 随时运行 `branch_governance.sh` |

---

**文档版本**：v1.0.0
**创建日期**：2026-09-06
**维护人**：AI Agent
