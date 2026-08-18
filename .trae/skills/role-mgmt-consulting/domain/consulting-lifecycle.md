---
name: "consulting-lifecycle-skill"
description: "用户开展项目管理咨询（商机评估/投标、现状诊断、成熟度评估、差距分析、方案设计、变革实施、成效评估）时加载本咨询生命周期明细：对齐 ICM 咨询管理 + CMMI/P3M3/OPM3 成熟度模型 + Kotter 8 步/ADKAR 变革管理，5 环节全流程。用户说咨询/诊断/成熟度/变革时加载。"
---

# ConsultingLifecycleSkill 项目管理咨询生命周期明细

> 版权：`../../shared/references/COPYRIGHT.md`　标准：`../../references/consulting_standards.md`　成熟度模型：`consulting-lifecycle__resources/maturity_model.md`

## 1. 基础元数据

- **技能唯一标识**：ConsultingLifecycleSkill
- **技能版本**：v1.0.0
- **定位**：项目管理咨询（PM Consulting）的二级方法工程/诊断能力——评估组织项目管理成熟度、诊断差距、定制方法论、推动变革、评估成效，独立于 SDLC 一级执行路由。解决核心痛点：**咨询业务全生命周期管理** + **成熟度评估有据可依** + **变革落地可持续**。
- **调用主体**：DevProjectTeamSkill（管理咨询模式）/ 用户直接指令
- **依赖工具**：role-governance（台账读写 `create_baseline`/`change_audit`）、`../../shared/governance.md`、铁律 `../../references/iron_rules.md` §3（客户数据 A/B 级）
- **核心约束**：
   1. 咨询侧只提供评估/诊断/方案/变革/成效建议，不代行客户方决策；
   2. 客户数据按 A/B 级脱敏处理，台账只存别名；
   3. 本包为二级能力，落地执行由客户组织或本库执行角色承接。

---

## 2. 成熟度评估模型（自建 5 维框架）

对齐 P3M3（Portfolio/Program/Project Maturity Model）与 CMMI 裁剪，用于 `assess_maturity`。评分细则、指标定义与证据要求见 `consulting-lifecycle__resources/maturity_model.md`。

| 维度 | 考察内容 | 参考模型 |
|------|---------|---------|
| 治理 Governance | 组合/项目群/项目三层治理、决策权责、门禁机制 | OPM3 / ISO 21500 |
| 流程 Processes | 生命周期定义、标准流程、裁剪规则、变更控制 | CMMI / P3M3 |
| 组织 People | 角色定义、能力模型、培训、教练、激励 | IPMA ICB4 |
| 度量 Metrics | EVM、KPI 体系、报告节奏、数据质量 | P3M3 / EVM |
| 工具 Tools | PMIS、CMDB、协作平台、自动化 | ISO 10007 / CMMI |

**评分等级**：0 未定义 → 1 初始 → 2 可重复 → 3 已定义 → 4 已管理 → 5 已优化（每维度证据必填，禁止无证据评分）。

---

## 3. 统一入参标准

统一入参：`action`（九指令之一）+ `content`（客户背景/现状/差距/方案/变革/成效信息）+ `stage`（当前环节）+ `user_confirm`（无/同意/拒绝/查错）。

#### action 指令清单

| action | 作用 | 前置条件 |
|--------|------|----------|
| `assess_opportunity` | 商机评估与投标策略（机会评估/赢率分析/竞标建议） | 客户需求已表达 |
| `draft_proposal` | 咨询建议书（SOW/交付物/里程碑/报价/风险） | assess_opportunity |
| `diagnose_as_is` | 现状诊断（组织访谈/流程采集/痛点识别） | draft_proposal 中标或用户委托 |
| `assess_maturity` | 成熟度评估（5 维模型评分 + 证据） | diagnose_as_is |
| `analyze_gap` | 差距分析（As-Is vs To-Be 矩阵/根因/优先级） | assess_maturity |
| `design_solution` | 方案设计（PMO 蓝图/治理模型/方法论定制/绩效体系） | analyze_gap |
| `drive_change` | 变革实施（Kotter 8 步/ADKAR/干系人/试点推广） | design_solution |
| `coach_org` | 能力建设（培训/教练辅导/认证路径） | drive_change |
| `measure_value` | 成效评估（价值实现测量/结项评估） | 变革实施完成 |
| `asset_knowledge` | 知识资产沉淀（案例库/模板/IP 复用登记） | measure_value |

---

## 4. 咨询生命周期流程

流程主线：`assess_opportunity → draft_proposal → diagnose_as_is → assess_maturity → analyze_gap → design_solution → drive_change (+coach_org) → measure_value → asset_knowledge`。

- **门禁**：每环节产出经用户确认后进入下一环节；涉及客户数据使用/变革决策必须人工确认；
- **定位铁律**：咨询只出建议，不代客户决策；落地执行交接 role-project-init/role-governance；
- **No-Go 后重启**：阻塞消除后从对应环节恢复，不需从头重跑。

### 环节 1：商机评估与投标（assess_opportunity + draft_proposal）
机会评估（客户需求清晰度/预算/时间窗口/赢率）+ 竞标策略；中标或委托后起草建议书。
输出：《商机评估》写 `33_商机管道.csv`（商机编号/客户/需求/预算/时间窗口/赢率/阶段）；《咨询建议书》写 `35_建议书版本.csv`（版本/SOW/交付物/里程碑/报价/风险/有效期），客户名仅存脱敏别名。

### 环节 2：现状诊断与成熟度评估（diagnose_as_is + assess_maturity + analyze_gap）
组织访谈、流程采集、痛点识别；按 5 维模型评分（证据必填）；差距矩阵与根因、优先级排序。
输出：《成熟度评估报告》写 `36_成熟度基线.csv`（维度/评分/等级/证据/差距项）+ 文档版落 `咨询资产/`；《差距矩阵》（As-Is 现状 / To-Be 目标 / 差距 / 根因 / 优先级 / 建议）。

### 环节 3：方案设计（design_solution）
To-Be 蓝图：PMO 类型与职责、治理模型设计、方法论定制（裁剪指南）、绩效体系（度量口径/KPI）、工具选型建议。
输出：《PMO 蓝图》《方法论定制手册》《绩效体系设计》落 `咨询资产/`，经客户方负责人确认。

### 环节 4：实施与变革（drive_change + coach_org）
Kotter 8 步（营造紧迫感→组建联盟→愿景→沟通→授权→速赢→巩固→文化固化）或 ADKAR（Awareness→Desire→Knowledge→Ability→Reinforcement）；干系人权力-利益管理；试点→推广；教练辅导与能力建设。
输出：《变革计划》写 `37_变革计划.csv`（阶段/动作/Kotter 或 ADKAR 映射/责任人/时间/状态）+ 培训与教练记录落 `咨询资产/`。

### 环节 5：成效评估与资产化（measure_value + asset_knowledge）
对照价值实现目标逐项测量（效率提升/周期缩短/缺陷下降等量化指标）+ 结项评估；知识资产沉淀（可复用模板/方法论/IP）。
输出：《成效评估报告》落 `咨询资产/`；《知识资产记录》（资产编号/类型/用途/来源咨询/复用率）登记并更新 33~37 台账。

---

## 5. 触发规则
- 用户提出「项目管理咨询/PMO 咨询/成熟度评估/差距分析/方法论定制/变革管理/咨询建议书/PMO 蓝图/教练辅导/成效评估」。

## 6. 输出规范
- 台账（33~37 CSV）经 role-governance 路由写入，禁止 .xlsx；输出表格按 token_standard §3 阈值；
- 每环节产出须经用户确认后方可进入下一环节；
- 文档类交付物（评估报告/建议书/蓝图/变革计划）落 `咨询资产/` 目录。

## 7. 边界（安全铁律）
1. **决策主体铁律**：咨询师只提供建议，不代行客户方决策；变革范围调整须客户方负责人确认；
2. **保密铁律**：客户组织信息按 `../../references/iron_rules.md` §3 A/B 级处理，台账只存脱敏别名，真实信息走 `.secrets/`，禁止入库；
3. **证据铁律**：成熟度评分必须有证据支撑，禁止无证据评分；
4. **落地承接铁律**：咨询方案落地执行交接本库 role-project-init/role-governance（如客户委托），咨询包不重复执行落地；
5. **授权铁律**：访问客户方信息/外部系统经 `register_auth` 登记（`14_授权登记.csv`），未授权禁止访问。

**禁用**：代行客户决策；无证据成熟度评分；客户真实信息入库；跳过授权访问客户系统。

**技能关系**：DevProjectTeamSkill=管理咨询模式入口；role-governance=台账读写与审计；role-project-init/role-governance=落地承接；iron_rules=客户数据分级。

---

> 协作接口详见各宿主技能元数据及 `../../shared/references/api_contracts.md`；目录规范详见 `../../shared/references/directory_structure.md`；咨询标准详见 `../../references/consulting_standards.md`

---

**文档版本**：v1.0.0　**最后更新**：2026-08-18
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
