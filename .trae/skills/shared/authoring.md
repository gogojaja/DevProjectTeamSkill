# authoring.md — SkillAuthoringSkill 技能维护（单源共享）

> 源：原 skill-authoring-skill。被 role-governance 引用。
> 仅用于新建/修改 SKILL.md 文件，与 skill-evolution（只读诊断）职责不重叠。

## 1. 维护目标：生成“闭环执行型技能”而非说明型流程

所有经 skill-authoring 维护产出的技能，都必须具备标准的闭环执行能力，不允许只停留在角色职责说明、经验总结、或流程建议。

### 1.1 硬门禁

每个维护产出的技能必须满足：
- 具备明确任务入口（触发词 + 场景 + 前置条件）；
- 具备执行动作层（步骤/工具/输入输出）；
- 具备状态机（待启动→执行→校验→完成/回退）；
- 具备验收门禁（完成标准/必须产出/失败条件）；
- 具备失败恢复机制（重试/回滚/恢复点）；
- 具备交接与审计记录（产出物/保存路径/下一步动作/证据）。
- 具备 `闭环执行系统` 标题，且必须包含 `任务入口 / 执行状态 / 验收门禁 / 失败处理 / 产出与交接 / 审计记录` 六个核心章节。

> 若技能仅有流程描述、最佳实践、角色职责说明而无闭环执行系统，则不视为合格产出。维护产出必须通过 `tools/check_skill_closure.py` 与 `tools/check_version_consistency.py` 的硬门禁后才允许打包、部署和固化。

## 2. 维护范围硬门禁（默认仅维护当前工作目录/当前项目）

维护模式启动时，必须先声明 `maintenance_scope`。默认行为为：仅维护当前工作目录或当前项目中的技能，不维护 `DevProjectTeamSkill` 本体；只有在用户明确要求时，才允许维护 `DevProjectTeamSkill` 自身。

### 2.1 自动检查
在维护开始前，必须执行：

```bash
python3 tools/check_maintenance_scope.py --scope current_project
```

如果用户明确要求维护本体，则使用：

```bash
python3 tools/check_maintenance_scope.py --scope dev-project-team-skill --allow-dev-project-team-skill
```

### 2.2 默认规则
- 默认 `maintenance_scope`：`current_project` 或 `current_directory`；
- 默认禁止范围：`DevProjectTeamSkill`、全库根目录、其他无关项目；
- 允许扩展范围：仅在用户明确要求“维护 DevProjectTeamSkill”或“维护整套技能库”时才可扩大范围；
- 若未声明 `maintenance_scope`，视为“只维护当前工作目录/当前项目”，并触发人工确认。

### 2.2 维护范围判定模板
```text
maintenance_scope = current_project
# or: current_directory
# or: dev-project-team-skill
# or: role-project-init
# or: role-development
```

> 若范围命中 `dev-project-team-skill`，必须要求用户显式确认；默认不得直接维护本体技能库。

## 3. 轻量六步流程（~60 分钟）

| Step | 名称 | 要点 |
|------|------|------|
| 1 | 需求定义 | 明确触发场景、触发词、前置条件、输出目标，并先确认 `maintenance_scope` |
| 2 | 能力建模 | 确定任务入口、状态机、动作层、验收门禁 |
| 3 | SKILL.md 编写 | 结构化正文：触发规则 + 流程 + 输出规范 + 边界 + 闭环执行系统 |
| 4 | 结构校验 | 校验 frontmatter / description / 目录一致 / 闭环执行系统完整性 |
| 5 | 功能验证 | 三触发词测试 + 验收门禁验证 + 失败回退验证 |
| 6 | 打包发布 | `tools/package_skills.sh` / `deploy_skills.sh` / `solidify.sh` |

## 3. 统一结构规范

- frontmatter `name` 与目录名一致；
- description 结构 `<做什么>。<触发词，前置>。用户说…时加载。`（150~250 字符）；
- 表格按 `../shared/references/token_standard.md` §3（CSV/Markdown 阈值）；
- 明细外置 `domain/*.md` 与 `shared/`，禁止正文堆砌；
- 每个技能正文必须包含 `闭环执行系统` 强制章节。

## 4. 闭环执行系统模板（强制）

统一引用 `../shared/closure_execution_template.md` 作为标准模板；新维护产出必须与该模板保持一致，不得自行裁剪关键章节。

> 通用模板内容包括：任务入口、执行状态、执行动作层、验收门禁、失败处理、产出与交接、审计记录、质量门禁。

```md
闭环执行系统

### 1. 任务入口
- 输入：说明什么情况下触发
- 前置：说明必要上下文、输入、角色状态
- 不适用：说明何时不该执行

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | 条件满足 | 用户确认/启动 | 准备上下文 |
| 执行中 | 任务已启动 | 关键动作完成/失败 | 执行动作 |
| 校验中 | 关键动作完成 | 通过/失败 | 检查门禁 |
| 阻塞 | 依赖缺失 | 补充信息/人工处理 | 暂停推进 |
| 完成 | 验收通过 | 进入交接 | 记录证据 |
| 回退 | 执行失败/门禁未过 | 回到稳定状态 | 启动回滚 |

### 3. 执行动作层
- 执行步骤 1
- 执行步骤 2
- 执行步骤 3
- 所需工具/脚本
- 输入输出约束

### 4. 验收门禁
- 必须产出物
- 通过条件
- 失败条件
- 审核对象

### 5. 失败处理
- 失败类型
- 恢复策略
- 回滚方案
- 重试策略
- 是否需要人工确认

### 6. 产出与交接
- 产出物列表
- 保存路径
- 交接对象
- 下一步动作
- 归档条件

### 7. 审计记录
- 执行时间
- 关键参数
- 关键决策
- 结果证据
- 失败原因
```

## 5. 质量门禁（维护模式专用）

- 必须存在 `闭环执行系统` 标题；
- 必须包含状态机；
- 必须包含验收门禁；
- 必须包含失败恢复；
- 必须包含产出物和交接说明；
- 必须能证明该技能可被执行、验证、恢复与交接；
- 必须通过 `tools/check_skill_closure.py` 与 `tools/check_skill_release_gate.py` 的发布级门禁；
- 若只有流程建议、角色职责或经验总结，则判定为不合格维护产出。

## 8. 发布级门禁（强制）

每个维护产出的 SKILL.md 在进入打包/部署前，必须满足以下条件：
1. frontmatter 包含 `name` 与合法 `description`（包含中文触发声明「用户说…时加载」，单语言原则，禁英文 Load when 尾巴）；
2. 正文包含 `技能版本` 和 `**文档版本**` 以及 `**最后更新**`；
3. 正文包含 `闭环执行系统` 章节及其六大核心部分；
4. 通过 `tools/check_skill_closure.py` 与 `tools/check_skill_release_gate.py`；
5. 仅在全部通过后，才允许执行 `package_skills.sh`、`deploy_skills.sh` 或 `solidify.sh`。

> 详细执行流程和统一标准，见 `../shared/skill_maintenance_sop.md` 与 `../shared/skill_maintenance_charter.md`。

## 6. 临时文件与产出物目录（强制）

- **最终产出物**：新写/修改的 SKILL.md、`domain/*.md`、`*__resources/` 一律落盘在 `.trae/skills/<包名>/` 源码（唯一事实来源）；打包产物由 `tools/package_skills.sh` 输出至项目根 `dist/`（`dist/<包名>_v<版本>.zip`），禁止手工复制 shared/references 进角色包；
- **过程临时文件**：编写中的草稿、中间版本、拆分数据源等一律禁止写入 `.trae/skills/`、系统 `/tmp`（易失目录）与项目外路径；统一放项目根 `backup/tmp_migrations/`（纳入 git），打包过程临时产物归 `_pkg_tmp/`（gitignore，不入库）；
- **清理**：产出物落盘后立即清理临时文件；需留痕的临时文件迁移入 `backup/tmp_migrations/` 后删除原临时位置副本；
- **外部文件铁律**：涉及写入仓库之外路径（如全局技能目录）时，必须先用户授权 + 备份入 `.backup/` + 留痕 `台账/13_安全审计台账.csv`。

## 7. 禁止

跳过结构校验直接发布 / description 缺失触发词 / 正文一次塞入全部明细 / 产生 .xlsx / 产出物落在 `.trae/skills/` 之外 / 维护产出缺少闭环执行系统 / 维护终审校验不通过。

---

**文档版本**：v21.5.7　**最后更新**：2026-08-18（description 模板统一中文触发声明并对齐 release_gate 触发检查）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）