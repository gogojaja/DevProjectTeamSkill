# AGENTS.md

## 项目定位

DevProjectTeamSkill：软件研发全生命周期多角色编排技能库（8 个角色包 + 1 个编排器）。本体即技能源码，不是业务应用。AI Agent 在本仓库的职责是**维护技能库本身**（skill 编写/结构/打包/部署），不是执行软件项目业务。

## 仓库结构

```
.trae/skills/         技能源码（唯一事实来源）
  SKILL_INDEX.md      8 包路由索引
  references/         公共标准（token/csv/api 契约等）
  shared/             单源共享库：governance/evolution/authoring + references 副本
  dev-project-team-skill/   编排器（薄壳）
  role-*/             SKILL.md(根) + domain/ 流程 + *__resources/ 明细
tools/                打包/部署/固化脚本（.sh + .py 双实现）
交接文档.md            跨会话断点，改动后必须刷新
opencode.json         opencode 技能注册
```

## 核心规则（违反即返工）

1. **源码单源**：共享内容只存 `shared/`，角色包用 `../shared/...` 相对引用；**禁止手工复制** shared/references 进角色包（打包时自动内嵌）。
2. **新增/修改技能**：必须同步 `SKILL_INDEX.md` + `references/api_contracts.md`；description 150~250 字符（`做什么。<触发词>。Load when...`）。
3. **输出格式**：>4K token 或 >20 列 → CSV（UTF-8 with BOM）；仅回显首 5 行 + 行数。禁止 .xlsx。
4. **改动后固化**：任务完成执行 `tools/solidify.sh "<说明>"` 并刷新 `交接文档.md` 断点区，然后 git commit。
5. **文件保护**：无明确指令禁止删除/移动/重命名文件。

## 命令

```sh
bash tools/package_skills.sh            # 打包全部 8 角色包到 dist/
bash tools/package_skills.sh --role role-testing
bash tools/deploy_skills.sh --roles role-a,role-b
bash tools/solidify.sh "说明"
python tools/excel_to_csv.py            # 迁移存量 xlsx→csv
git commit                              # 每原子改动一次提交
```

## 效率约定

- 先读根 `SKILL.md` 路由表 → 命中后只读目标文件，**禁止**一次性 Read 全部文件。
- 目录内先 `ls` / 文件列表，小文件直接 Read，大文件 grep 定位后读片段。
- 日志与命令输出仅回显变更/错误，不 cat 大文件全文。
- 引用路径保持相对，避免改动后全文失效。
