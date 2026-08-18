# DevProjectTeamSkill v21.7.0 技能库

**版本**：v21.7.0 ｜ **发布日期**：2026-08-18 ｜ **结构**：9 角色包 + 1 编排器

## 内容结构

- `.trae/skills/`：技能源码（**唯一事实来源**）
  - `SKILL_INDEX.md`：9 包路由索引
  - `dev-project-team-skill/`：编排器（薄壳，含路由表 + 调度/压缩规则）
  - `role-*/`：9 角色包（启动 / 需求 / 架构 / 开发 / 测试 / 投产 / 总控 / 项目群 / 管理咨询），各含 SKILL.md + domain/ 流程 + *__resources/ 明细
  - `references/`：公共标准（token / csv / api 契约 / 环境标准 / 模型选型 / 铁律卡等）
  - `shared/`：单源共享库（governance / evolution / authoring + references 副本）
- `tools/`：package_skills.sh / deploy_skills.sh / solidify.sh（另有 .py 双实现）及 excel_to_csv.py / check_version_consistency.py
- 顶层 *.md：交接文档 / 技能库增强改造方案 / 敏捷迭代模式方案 / opencode 启用指南（docs/）

## 打包与部署

```sh
bash tools/package_skills.sh               # 打包全部 9 角色包到 dist/
bash tools/package_skills.sh --role role-testing
bash tools/deploy_skills.sh --roles role-a,role-b   # 部署到 .github/.claude/.agents/ 及全局库
bash tools/solidify.sh "说明"               # 快照→刷新交接断点→打包→部署
```

部署目标：`.github/skills/`、`.claude/skills/`、`.agents/skills/` 及全局库
（Windows：`C:\Users\gogoj\.config\opencode\skills`；macOS：`~/.config/opencode/skills`）。
**永不覆盖 `.trae/skills/` 源**；共享内容经打包自动内嵌，禁止手工复制。

## 启用方式

- **TRAE**：详见 `docs/legacy/TRAE部署与启用指南.md`（v8.0.0 历史版，仅作留档）
- **opencode**：详见 `docs/opencode启用指南.md`（当前推荐）

## 关键规则（详见 AGENTS.md）

- 源码单源：只在 `.trae/skills/` 改技能，改完即跑 `solidify`
- 修改技能须同步 `SKILL_INDEX.md` + `references/api_contracts.md`；description 150~250 字符
- ≥4K token 或 >20 列 → CSV（UTF-8 with BOM），禁止 .xlsx
- 系统/项目外文件操作：先授权 → 备份到 `.backup/` → 留痕 `台账/13_安全审计台账.csv`
