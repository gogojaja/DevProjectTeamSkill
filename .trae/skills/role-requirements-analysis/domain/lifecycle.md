---
name: "requirements-lifecycle-skill"
description: "Requirements lifecycle management sub-skill covering requirement review with five review dimensions, change analysis with mandatory-dimension forced full-scan impact evaluation, and bidirectional traceability matrix maintenance. Handles quality gate gatekeeping before review, review defect closure within two rounds, change registration and impact assessment, and traceability updates into the project ledger. Invoke when reviewing SRS, performing requirement changes, or updating the traceability matrix."
---

# RequirementsLifecycleSkill 需求生命周期管理技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **定位/调用**：需求工程「验证与生命周期管理」阶段技能；由 requirements-analysis-skill 路由分发，DevProjectTeamSkill 需求分析师子角色主动调用（仅调用时临时加载，不常驻上下文）
- **触发时机**：需求评审环节、需求变更分析、需求追溯矩阵更新
- **存储介质**：`需求变更影响评估表_<变更编号>.csv` + 追溯矩阵写入 `台账/08_需求追溯矩阵.csv`
- **参考标准**：BABOK v3、ISO/IEC/IEEE 29148:2018
- **入参**：`{"action": "review_requirements / change_analysis / update_traceability", "stage": "需求收集/需求分析/需求编写/需求评审", "content": "评审对象/变更描述/追溯信息", "project_context": "项目名称/范围边界/相关方/约束条件", "dimensions": "已选维度代码，变更分析按维度评估", "user_confirm": "无/同意/拒绝"}`

| action | 作用 | 触发场景 |
|--------|------|----------|
| `review_requirements` | 需求评审准备，对接 ProjectMonitorSkill stage_review | 需求评审环节 |
| `change_analysis` | 需求变更已选维度影响分析 | 需求变更 |
| `update_traceability` | 更新需求双向追溯矩阵 | 需求变更/新增/删除 |

## 2. 流程

**环节 1 评审**（`review_requirements`）：评审五维度（范围合规/功能逻辑质量/工程规范-结构与编号/风险安全-威胁建模与合规/范围跟踪-无缩水蔓延，详 §一 `.//requirements_lifecycle_details.md`）。前置门禁：追溯覆盖率 100% / 冲突消解记录为空或全部关闭 / 每条需求含量化验收标准 / 无合规违规。流程：自检门禁全通过 → 调 `stage_review` 传入 SRS 与校验报告 → 缺陷分级录入「质量缺陷台账」逐条整改 → 最多 2 轮整改复核 → 严重/主要缺陷闭环 + `check_gate` 通过后 `stage_close` 固化需求基线。

**环节 2 变更分析**（`change_analysis`）：基线固化后任何新增/修改/删除/范围调整触发。变更登记至 `需求变更记录.csv` → 按已选维度逐项评估（触及必选维度 func/sec/data/env 时强制全维度扫描）→ 追溯矩阵影响评估 → 生成《需求变更影响评估表》转 `change_audit` 等用户「同意」→ 审批后 `update_traceability` 更新追溯矩阵。

**环节 3 追溯矩阵**（`update_traceability`）：结构（需求编号|描述|来源|优先级|关联功能模块|关联接口|关联数据实体|关联测试用例|关联设计文档|变更记录）写入 `台账/08_需求追溯矩阵.csv`。方向：正向 需求→功能模块→设计文档→代码→测试用例；反向 逆序。维护：每条需求增删改后自动更新；阶段评审强制校验完整性，断链判定为缺陷；追溯矩阵作为 SRS 第 10 个 Sheet 同步输出。

## 3. 输出规范

- 评审报告（5 Sheet）+ 缺陷清单写入「质量缺陷台账」
- `需求变更影响评估表_<变更编号>.csv`（「已选维度影响评估」「追溯矩阵影响」「变更审批记录」三区）
- `台账/08_需求追溯矩阵.csv`（更新）

**质量门禁（向架构设计阶段流转前）**：① 评审全部严重/主要缺陷已闭环；② 追溯矩阵无断链（断链率≤20%）；③ 需求范围与项目范围基准一致；④ 需求变更全部经审批落地。

## 4. 边界（刹车规则）

- 评审：第 2 轮整改仍存严重/主要缺陷 → 停止自动修复，人工介入；门禁未达标 → 禁止评审通过，转整改
- 变更：同一需求连续 3 次无审批变更 → 冻结基准预警；未审批先实施 → 暂停，补审批
- **需求基线权威**：需求基线是设计与开发的唯一权威基准；设计/开发阶段评审发现已实现功能 ≠ 需求基线 → 一律以需求基线为准，偏差即缺陷、返工实现；**禁止以已实现内容逆向修正需求基线**；需求基线调整仅允许经合法 `change_analysis`+`change_audit` 审批触发（来源限范围调整/接口变化/合规新规/新诉求/缺陷澄清，来源为「已实现内容」驳回）
- 追溯：断链率超过 20% → 暂停流转，要求补全追溯关系

---

> 目录规范详见 `../../shared/references/directory_structure.md`
> 协作接口详见 `../../shared/references/api_contracts.md`

**文档版本**：v21.0.1 | **最后更新**：2026-08-15（需求基线权威铁律） | **知识产权所有**：段波（duanbo.douglas@163.com）