# 任务契约模板（Task Contract Template）

为避免触发词歧义并提升可执行性，新增 `任务契约模板` 要求：所有 `SKILL.md` 的 `description` 与正文应具备下列段落（可简称为 5 段式契约）：

- 目标：一句话说明本技能的目标（做什么）。
- 触发条件：列出明确的触发输入/场景（包括必须存在的前置产物或状态）。
- 不适用条件：列出不应触发本技能的场景或限制（避免误触发）。
- 输入/输出契约：结构化定义主要输入与输出（字段/文件名/格式/CSV/JSON），输出格式需指定 `CSV`/`JSON`/`Markdown` 等。
- 失败与回退策略：列出在执行中发生错误时的自动回退或人工介入点（checkpoint/rollback 指令/审计记录）。

示例（放在 `SKILL.md` 描述头部，可为 YAML frontmatter 之后的首段）：

目标：生成项目需求清单 CSV（IEEE 830 结构）以供下一阶段评审。

触发条件：用户明确请求“收集需求”且项目根存在 `00_阶段配置.csv`，或在 `init_tailor` 阶段后自动触发。

不适用条件：当项目处于 `已归档` 状态或 `00_阶段配置.csv` 标记本阶段为“裁剪（exclude）”时，不触发。

输入/输出契约：输入-原始访谈记录（`source_interviews/*.md`），输出-`需求规格_SRS.csv`（UTF-8 BOM，表头遵循 REQ-<dimension>-<module>-<sequence> 规则）。

失败与回退策略：若输出 CSV 缺失必需列（功能点/优先级/来源），则标记 task=blocked 并记录 `台账/13_安全审计台账.csv`；自动回退到上一个快照并发送 `notify:role-requirements-analysis`。

文档维护：所有新增/修改的 `SKILL.md` 必须遵守此模板，`tools/check_version_consistency.py` 后续将新增结构校验（另议）。
