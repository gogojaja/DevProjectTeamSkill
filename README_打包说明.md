# DevProjectTeamSkill v20.2.0 发布包

**版本**：v20.2.0 ｜ **打包日期**：见压缩包文件名 ｜ **技能总数**：39

## 内容结构
- `skills_源码/`：全部 39 技能 + references 的源库（唯一事实来源）
- `dist/`：每个技能独立的自包含 zip（可单独解压使用）
- `tools/`：package_skills.sh / deploy_skills.sh / solidify.sh
- 顶层 *.md：跨会话交接文档 / TRAE部署与启用指南 / 项目归档报告

## 结构变更（CHG-19，最新）
运维部署工程师角色四分路由重构：deployment-management-skill 由单体六环节
重写为薄路由壳 v2.0.0，按 ITIL v4 发布部署子流程分发至
strategy / planning / release / handover 四子技能 v1.0.0。

## 使用
技能源库安装：将 `skills_源码/references/` 与各技能目录拷贝至工具技能目录。
详见 `TRAE部署与启用指南.md`。
