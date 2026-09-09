# 配置管理计划（CMP）— DevProjectTeamSkill 技能库

> 编制角色：role-governance（配置管理域 `config_mgmt`）
> 依据：`domain/configuration-management.md` §3 CMP 模板 · ISO 10007 · PMBOK 7（整合管理/变更控制系统）· CMMI CM PA
> 版本：v1.0　编制日期：2026-09-09　密级：C 级（正常入库）
> 适用范围：DevProjectTeamSkill 技能库自身（13 角色包 + 子技能 + tools + references + docs）

---

## 1. CI 范围（配置项清单及单一信息源）

| CI 类别 | 纳入的配置项 | 单一信息源（数据归属，禁止复制） |
|---------|-------------|--------------------------------|
| 技能包 CI | 13 个角色包 + dev-project-team-skill 编排器 + 独立子技能 | `.trae/skills/`（authoring 源）；快照 `skills_backup_v<版本>/`；`dist/*.zip` |
| 代码/工具 CI | `tools/*.py`、`tools/*.sh`、`tools/cmdb/`、`tools/mcp_server/` | 项目 `tools/` 目录 + git |
| 文档 CI | `docs/*.md`、`references/`、`shared/references/`、评审报告 | `docs/` + `31_doc_config_mgmt.csv` |
| 环境 CI | 部署目标机、全局技能库端点、端口/凭据别名 | CMDB `tools/cmdb/cmdb-cli.py` + `20_环境配置.csv` / `25_环境资源清单.csv` |
| 台账 CI | `台账/*.csv`（00~54 编号台账） | `台账/` 目录（UTF-8 with BOM，禁 .xlsx） |

**部署消费端（derived，非源）**：`.claude/` `.agents/` `.github/` 三目录 + 全局 5 端（opencode/trae-cn/workbuddy/claude/copilot）——均由 `deploy_skills.py` / `publish_production.py` 从 `.trae/skills/` 派生，不作为编辑源。

## 2. 命名与标识

| 项 | 规则 | 唯一标识来源 |
|----|------|-------------|
| 角色包 | `role-<域名>` | SKILL.md frontmatter `name` |
| 能力域 | `domain/<能力>.md` | 文件路径 + SKILL.md §3 路由行 |
| 版本 | 语义化 `vMAJOR.MINOR.PATCH` | SKILL.md 元数据版本 == 页脚版本（`check_version_consistency.py` 强制） |
| 基线快照 | `skills_backup_v<编排器版本>/` | 编排器 SKILL.md 版本 |
| 环境 CI | CMDB 资源 ID | `cmdb-cli.py register` 返回 |
| 台账 | `<编号>_<名称>.csv` | 编号唯一（当前 00~55） |

## 3. 基线策略

| 时机 | 动作 | 基线载体 |
|------|------|---------|
| 每次能力变更固化 | `solidify.py` 生成/更新快照 + 部署三目录 | `skills_backup_v<版本>/` + git commit |
| 生产发布 | `publish_production.py` 构建版本目录 + 全局 5 端同步 | `~/dev-project-team-skill/v<版本>/`（SHA256 校验）+ `current` 指针 |
| 阶段门禁通过 | 打 git 基线（commit）+ 交接文档断点区刷新 | git `main` + `交接文档.md` |
| 回滚点 | `.backup/last_production_version.txt` 记录上一生产版本 | 版本目录 + 回滚指针 |

> **已知机制约束**：快照以**编排器版本号**命名且"已存在不覆盖"。子角色包（如 role-governance）单独升版而编排器版本未升时，新内容不会立即进入快照，形成**基线漂移窗口**，须由 `config_audit` 捕获并在编排器下次升版时闭合。

## 4. 变更控制

| 变更级别 | 判据 | 审批与门禁 |
|---------|------|-----------|
| Tier1 只读 | 检索/查看，无副作用 | 自由执行 |
| Tier2 范围写 | 新增/编辑 domain、SKILL.md、台账（范围内） | 清单 + 确认词 |
| Tier3 高辐射 | `solidify` / `publish_production` / `mirror_push` / git push / 全局目录写 / 删除 | **六件套**：清单 + 参数哈希 + 备份 + 授权 + 确认词 + 审计台账 |

- 所有 CI 变更经 `change_audit` 留痕；重大变更走变更分级审批。
- 单一分支策略：所有工作在 `main`，`pre-push` hook 拦截非 main 推送（`branch_governance.sh`）。
- 提交后 post-commit agent-loop 钩子自动跑门禁（版本/闭环/发布/双推）。

## 5. 职责（RACI）

| CM 活动 | R 执行 | A 负责 | C 咨询 | I 知会 |
|---------|--------|--------|--------|--------|
| 配置标识 | 各角色包维护者 | role-governance | role-development | 全体角色 |
| 配置控制（基线/变更） | role-governance | role-governance | 变更发起角色 | Program Board |
| 配置状态记实 | role-governance + role-program-mgmt | role-governance | — | 项目负责人 |
| 配置审计 `config_audit` | role-governance | role-governance | role-security（高危项） | 用户 |
| 环境 CI 管理 | CMDB owner（role-project-init `register_env_asset`） | role-program-mgmt §9.8 | role-operations | role-governance |
| 发布/部署 CI | role-deployment | role-deployment | role-governance（门禁） | 运维 |

## 6. 配置审计周期

| 触发 | 时机 | 审计项 |
|------|------|--------|
| 发布/固化前 | `solidify` / `publish_production` 前置 | 五项全跑（基线/版本/分支/文档/环境CI） |
| 阶段门禁 | 阶段流转前，与 `check_gate` 叠加 | 五项全跑 |
| 周期审计 | 每周，与 `cmdb_audit` / `branch_governance` 同窗口 | 五项全跑 |
| 手动 | 用户要求 | 按需裁剪 |

审计产出：`台账/55_配置审计报告.csv`（UTF-8 with BOM）；偏差/阻断项一律 `change_audit` 留痕并给整改建议。

---

**文档版本**：v1.0　**最后更新**：2026-09-09
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
