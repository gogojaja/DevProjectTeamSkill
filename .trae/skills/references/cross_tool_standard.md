# 跨工具技能库目录规范（Cross-Tool Skill Library Standard）

> 全技能体系跨工具（TRAE / opencode / VSCode Copilot / Claude Code / 其他 Agent Skills 兼容工具）的目录与部署统一规范。
> 本文件为**唯一事实来源**，各技能与部署脚本均遵循本规范。

---

## 1. 技能库单一事实来源（Source of Truth）

- **源库目录**：`.opencode/skills/`（含全部技能目录与共享 `references/`）；
- **部署原则**：任何工具使用时，均从源库**单向同步**（同步/复制），禁止在目标目录直接编辑修改；
- **工具目录映射**（项目级技能）：

| 工具 | 项目技能目录 | 全局技能目录 | 说明 |
|------|--------------|--------------|------|
| opencode | `.opencode/skills/` | `~/.config/opencode/skills/` | 源库所在，TRAE 与 VS Code 从源库同步 |
| TRAE | `.trae/skills/` | `~/.trae/skills/`（Windows CN 版 `~/.trae-cn/skills/`） | 项目级自动扫描 |
| VSCode / GitHub Copilot | `.github/skills/` `.claude/skills/` `.agents/skills/` | `~/.copilot/skills/` `~/.claude/skills/` `~/.agents/skills/` | 三者任选，推荐 `.github/skills/` |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | 与 VSCode 共用 `.claude/skills/` |

---

## 2. 目录结构规范

### 2.1 源库结构（`.opencode/skills/`）

```
.opencode/skills/
├── <skill-name>/                # 技能目录：kebab-case，与 frontmatter name 完全一致
│   ├── SKILL.md                 # 必须：YAML frontmatter（name + description）+ Markdown 正文
│   └── （可选）辅助文件           # 脚本/模板/示例，随技能目录整体同步
├── <skill-name>/...
└── references/                  # 共享引用目录（多技能共用，Token 优化方案 B）
    ├── COPYRIGHT.md
    ├── api_contracts.md
    ├── common_standards.md
    ├── directory_structure.md
    ├── dual_role_workflow.md
    ├── simplified_workflow.md
    └── cross_tool_standard.md   # 本文件
```

### 2.2 目标工具目录结构

- **整库同步**：将源库全部技能目录 + `references/` 同步到目标 `skills/` 目录；
- **目录层级**：目标目录下每个技能为一级子目录（`<skill-name>/SKILL.md`），`references/` 与技能目录平级；
- **相对引用**：技能内引用 `../references/` 的路径在同步后保持不变（references 与技能目录始终平级）。

### 2.3 SKILL.md frontmatter 规范（跨工具兼容）

```yaml
---
name: <skill-name>              # 必须：仅小写字母、数字、连字符，≤64 字符，须与父目录名一致
description: "<description>"    # 必须：功能 + 使用时机，≤1024 字符（本项目约定精简 ~250 字符）
---
```

- 各工具要求的 name/description 均兼容：TRAE、opencode、VSCode Copilot、Claude Code 均读取 `name` + `description`；
- **禁止**在 frontmatter 增加工具私有字段（如 `allowed-tools` 等）以保持跨工具纯净；确需能力声明时写入正文。

---

## 3. 部署规范

### 3.1 一键部署脚本

- **脚本位置**：项目根 `tools/deploy_skills.sh`；
- **部署目标**：`.trae/skills/`、`.github/skills/`、`.claude/skills/`、`.agents/skills/`（目标目录自动创建）；
- **部署方式**：全量 rsync 同步（含删除目标端已废弃技能），始终以源库为准；
- **执行**：`bash tools/deploy_skills.sh [--target .trae/skills]`；不带参数时部署全部默认目标。

### 3.2 部署后验证

1. 每个技能目录存在且 `SKILL.md` 可读；
2. frontmatter `name` 与父目录名一致（`tools/check_skill_names.py` 校验）；
3. `references/` 已在目标目录平级存在；
4. 随机抽查技能引用的 `../references/*.md` 在目标目录可解析。

### 3.3 技能变更流程

1. 修改源库 `.opencode/skills/` 中的 SKILL.md / references；
2. 按 `common_standards.md` §1.3 评审、按 §3 创建快照；
3. 重新执行 `tools/deploy_skills.sh` 同步各工具目录；
4. 重新打包 `dist/`（zip 内含 SKILL.md + references，见 §4）。

### 3.4 任务级断点固化（跨模型/跨会话防丢，强制）

> 解决跨模型/跨会话切换时工作成果只存在于上下文、落盘失败导致丢失的问题。

1. 任何涉及技能升级/拆分/批量修改、台账/契约/文档更新的**原子任务**，在**任务完成、切换模型或切换任务前**，必须先执行一键固化：
   `bash tools/solidify.sh "<改动说明>"`
   该脚本自动完成：列技能清单 → 生成 `skills_backup_<版本>/` 快照 → 校验一致性 → 更新 `跨会话交接文档.md` 断点区 → 打包 `dist/` → 部署 4 目录；
2. 固化后执行 `git add -A && git commit -m "<说明>"` 提交成果；
3. **跨模型接手**：新模型/新会话启动先读 `跨会话交接文档.md` 文末「工作断点」区，定位上一模型已完成/待办，**不要重复已固化工作**；若磁盘已变更而快照/断点区未更新，说明旧模型切换前未固化，先跑 `solidify.sh` 固化再续作；
4. 本机制与 `common_standards.md` §3 快照、`dist` 打包互补，`solidify.sh` 为三者的一键封装。

---

## 4. dist 发布包规范

- **命名**：`dist/<skill-name>_v<版本号>.zip`；
- **内容**：技能目录完整打包——`<skill-name>/SKILL.md` + 该技能引用的 `references/`（`../references/` 转为 `references/` 与技能目录平级），确保 zip 独立解压后可放入任意工具 `skills/` 目录直接使用；
- **zip 内结构**：

```
<skill-name>_v<版本号>.zip
├── <skill-name>/
│   └── SKILL.md
└── references/                  # 该技能实际引用的共享文档（不含全量）
```

---

## 5. 命名与兼容性约定

| 约束项 | 规范 | 依据 |
|--------|------|------|
| 技能目录名 | kebab-case（`xxx-skill`），≤64 字符 | VSCode/opencode 强校验 |
| frontmatter name | 与目录名逐字一致 | 各工具加载失败即静默 |
| references 相对路径 | 一律 `../references/`（源库） | 跨工具路径稳定 |
| 工具私有字段 | 禁止加入 frontmatter | 保持跨工具纯净 |
| 全局 vs 项目 | 项目技能放项目内，全局技能放用户目录 | 各工具规范一致 |

---

**文档版本**：v1.0.0
**最后更新**：2026-08-02
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
