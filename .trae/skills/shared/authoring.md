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

## 3. 禁止

跳过结构校验直接发布 / description 缺失触发词 / 正文一次塞入全部明细 / 产生 .xlsx。

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）