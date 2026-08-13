# authoring.md — SkillAuthoringSkill 技能维护（单源共享）

> 源：原 skill-authoring-skill。被 role-governance 引用。
> 仅用于新建/修改 SKILL.md 文件，与 skill-evolution（只读诊断）职责不重叠。

## 1. 轻量五步流程（~50 分钟）

| Step | 名称 | 要点 |
|------|------|------|
| 1 | 需求定义 | 明确触发场景与触发词（description 150~250 字模板） |
| 2 | SKILL.md 编写 | 四段式正文：触发规则 + 流程 + 输出规范 + 边界 |
| 3 | 结构校验 | 三查：frontmatter / description 模板 / 目录一致 |
| 4 | 功能验证 | 三触发词测试 |
| 5 | 打包发布 | `tools/package_skills.sh` / `deploy_skills.sh` |

## 2. 结构规范

- frontmatter `name` 与目录名一致；
- description 结构 `<做什么>。<触发词，前置>。Load when <user says>.`（150~250 字符）；
- 表格按 `../shared/references/token_standard.md` §3（CSV/Markdown 阈值）；
- 明细外置 `domain/*.md` 与 `shared/`，禁止正文堆砌。

## 3. 临时文件与产出物目录（强制）

- **最终产出物**：新写/修改的 SKILL.md、`domain/*.md`、`*__resources/` 一律落盘在 `.trae/skills/<包名>/` 源码（唯一事实来源）；打包产物由 `tools/package_skills.sh` 输出至项目根 `dist/`（`dist/<包名>_v<版本>.zip`），禁止手工复制 shared/references 进角色包；
- **过程临时文件**：编写中的草稿、中间版本、拆分数据源等一律禁止写入 `.trae/skills/`、系统 `/tmp`（易失目录）与项目外路径；统一放项目根 `backup/tmp_migrations/`（纳入 git），打包过程临时产物归 `_pkg_tmp/`（gitignore，不入库）；
- **清理**：产出物落盘后立即清理临时文件；需留痕的临时文件迁移入 `backup/tmp_migrations/` 后删除原临时位置副本；
- **外部文件铁律**：涉及写入仓库之外路径（如全局技能目录）时，必须先用户授权 + 备份入 `.backup/` + 留痕 `台账/13_安全审计台账.csv`。

## 4. 禁止

跳过结构校验直接发布 / description 缺失触发词 / 正文一次塞入全部明细 / 产生 .xlsx / 产出物落在 `.trae/skills/` 之外。

---

**文档版本**：v21.0.1　**最后更新**：2026-08-13
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）