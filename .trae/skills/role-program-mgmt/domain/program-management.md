---
name: "program-management-skill"
description: "Program management skill aligned with PMI Standard for Program Management (SPM 5th), MSP, IMS and EVM. Covers program definition, benefits management, dependency matrix, integrated master schedule, standardized execution metrics, program board tranche decisions and program closure. Invoke when coordinating multiple related projects as a program/portfolio program office (PMO) layer."
---

# ProgramManagementSkill 项目群管理技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`；项目群管理标准详见 `../../references/program_management.md`

## 1. 基础元数据

- **技能唯一标识**：ProgramManagementSkill
- **技能版本**：v1.0.0
- **定位**：跨项目协同层（Program/项目群 PMO 决策层），管理一组相互关联的项目（项目群），对齐 PMI《项目集管理标准》第5版与 MSP。解决核心痛点：**各项目时间信息一致**（IMS 集成主进度 + 依赖传导）与**执行标准一致**（统一度量口径 + 报告节奏）。
- **调用主体**：DevProjectTeamSkill（项目群协同模式）/ 用户直接指令
- **依赖工具**：role-governance（台账读写 `create_baseline`/`change_audit`/`risk_scan`）、role-project-init（成员项目启动产物）
- **核心约束**：
  1. 项目群协同必须在成员项目启动/评审通过后叠加进行，Program Board 决策不替代项目级门禁；
  2. Program Manager 管理不决策、PMO 提供机制不决策、Program Board 做决策（继续/转向/终止）；
  3. 本包只做跨项目协同，单项目内部由对应角色包负责；组合治理（投资决策）不属于本包。

---

## 2. 统一入参标准

统一入参：`action`（七指令之一）+ `content`（项目群背景/收益/依赖/进度/标准/评审/收尾信息）+ `stage`（当前环节）+ `user_confirm`（无/同意/拒绝/查错）。

#### action 指令清单

| action | 作用 | 前置条件 |
|--------|------|----------|
| `define_program` | 项目群定义（业务论证/章程/路线图/治理四角色/tranche 划分） | 成员项目已启动 |
| `manage_benefits` | 收益管理（收益档案 owner/metric/基线/目标/兑现时间线 + 追踪） | define_program |
| `map_dependencies` | 跨项目依赖矩阵（FS/SS/FF/SF + 相互交付物 + 共享资源 + 传导分析） | manage_benefits |
| `align_schedule` | IMS 三层集成主进度（滚动式规划/关键路径/SAFe PI Planning 可选） | map_dependencies |
| `standardize_execution` | 统一执行标准与度量口径（CPI/SPI/缺陷密度/里程碑准点率/变更计费率） | align_schedule |
| `review_program` | Program Board tranche 边界决策（继续/转向/终止 + 三层门禁叠加） | standardize_execution |
| `close_program` | 项目群收尾（收益确认/移交/资源释放/复盘归档） | review_program=继续 或 终止 |

---

## 3. 项目群管理流程

流程主线：`define_program → manage_benefits → map_dependencies → align_schedule → standardize_execution → review_program → (继续) → 下一 tranche / (终止) → close_program`；评审 No-Go → 转向（re-plan）或终止，停止。

- **门禁**：每环节产出经用户确认后进入下一环节；Program Board 决策必须人工确认；
- **双层门禁**：项目级 check_ready/stage_review 通过 → 再执行项目群评审（时间对齐/依赖无冲突/标准一致）；
- **No-Go 后重启**：阻塞消除后从对应环节恢复，不需从头重跑。

### 环节 1：项目群定义（define_program）
处理：输出**业务论证**（战略价值/可行性/投资合理性）+ **项目集章程**（授权/目标/收益/约束）+ **项目集路线图**（里程碑与 tranche 概览）+ **治理结构四角色**（Sponsor 战略背书/Program Board 决策/Program Manager 协调/PMO 机制）+ **tranche 划分**（分批交付波次，每波次有明确收益增量）；治理结构经干系人确认；战略一致不清晰时输出「项目群定义缺陷清单」，不强行通过。
输出：《项目群注册》（写入「28_项目群注册.csv」：编号/名称/战略目标/收益目标/成员项目清单/治理四角色/tranche 划分/路线图/统一度量口径/执行标准基线/状态），经 Sponsor 与用户确认。

### 环节 2：收益管理（manage_benefits）
处理：建立**收益档案**（每项收益：owner/metric/基线值/目标值/兑现时间线/使能变更/威胁）与**收益地图**（能力→中间成果→最终收益的因果链）；贯穿项目群生命周期持续追踪，威胁收益提前升级；收益确认移交运营。
输出：《收益档案与追踪》（写入「28_项目群注册.csv」收益档案区：收益项/owner/指标/基线/目标/时间线/状态），经 Sponsor 确认。

### 环节 3：跨项目依赖管理（map_dependencies）
处理：输出**依赖矩阵**——四类依赖关系（FS 完成到开始/SS 开始到开始/FF 完成到完成/SF 开始到完成）+ 相互交付物 + 共享资源（衔接 `25_环境资源清单.csv` 冲突仲裁）；**传导分析**：上游延期自动传导下游，识别关键路径依赖（不可延误）与浮动依赖（可缓冲）；依赖冲突升阶 `change_audit` 留痕。
输出：《项目依赖矩阵》（写入「29_项目依赖矩阵.csv」：依赖编号/源项目/目标项目/依赖类型/依赖对象/方向/状态/责任方/传导风险），经相关项目经理确认。

### 环节 4：进度对齐（align_schedule）
处理：建立 **IMS 三层集成主进度**——第 1 层 Program Master Schedule（项目群概要时间线）、第 2 层 Integrated Master Plan（里程碑级，含关键事件准则）、第 3 层明细排期（滚动式规划：近端 2~6 周详细 + 远端里程碑概要，每波次推进细化）；**关键路径**标注（SPI/总浮动监控）；**敏捷项目群可选**：SAFe PI Planning（8~12 周 PI 增量详细规划 + 同步规划仪式 + 增量对齐）；周更新 + 月评审节奏。
输出：《项目群主进度》（写入「30_项目群主进度.csv」：项目/里程碑/计划日期/实际日期/偏差/SPI/关键路径标记/状态/责任方/更新记录），经 Program Board 确认。

### 环节 5：统一执行标准（standardize_execution）
处理：统一各项目**执行标准**（流程/模板/门禁/质量标准）与**度量口径**——CPI（成本绩效指数=EV/AC）、SPI（进度绩效指数=EV/PV）、缺陷密度、里程碑准点率、变更计费率、资源负载（≤80%）；统一**报告节奏**（周报 RAID/EVM、里程碑评审、月报趋势）；单一真实数据源，消除多版本真相。
输出：《标准一致性检查清单》（统一标准项/度量口径/报告节奏/各项目达标状态），经 PMO 确认。

### 环节 6：项目群评审（review_program）
处理：**Program Board 在 tranche 边界决策**——继续（proceed）/ 转向（re-plan）/ 终止（close），决策依据：收益是否兑现、当前工作包是否仍为正确选择、业务论证是否仍成立；**三层门禁叠加**：项目级 stage_review 通过 → 项目群评审（时间对齐 Gate / 依赖无冲突 Gate / 标准一致 Gate）；评审节奏：tranche 边界正式决策 + 月度轻量跟踪；决策留痕，禁止无记录口头决策。
输出：《项目群评审决策》（继续/转向/终止 + 理由 + 门禁检查项 + 纪要入库），经 Program Board 与用户确认。

### 环节 7：项目群收尾（close_program）
处理：收益确认（对照收益档案逐项核实兑现）+ 移交运营 + 资源释放（衔接 CMDB 释放与 `25_环境资源清单`）+ 复盘归档（提炼可固化流程/复用工具/降 Token）；结束项目群临时治理结构。
输出：《项目群收尾报告》（收益兑现清单/移交清单/资源释放/复盘结论），经 Sponsor 确认后归档。

---

## 4. 触发规则

- 用户提出「项目群/项目集/多项目协同/PMO 决策层」；多项目需统一时间与标准；跨项目依赖管理；里程碑对齐；统一度量口径；项目群评审。

## 5. 输出规范

- 台账（28/29/30 CSV）经 role-governance 路由写入，禁止 .xlsx；输出表格按 token_standard §3 阈值；
- 每环节产出须经用户确认后方可进入下一环节；
- 与成员项目衔接：读取各项目「01_启动组」「03_进度基准」「09_进度跟踪」「12_风险问题台账」「27_组织架构」数据，不重复建立单项目台账。

## 6. 边界（安全铁律）

1. **叠加门禁铁律**：项目群评审不替代项目级 check_ready/stage_review，双层叠加执行；
2. **决策主体铁律**：Program Manager/PMO 不得代行 Program Board 决策，继续/转向/终止须人工确认并留痕；
3. **收益锚定铁律**：业务论证不成立或收益无法兑现时，Program Board 应终止项目群而非坚持推进；
4. **数据边界铁律**：访问成员项目 `台账/` 遵循项目访问边界（`26_访问边界.csv`），跨项目访问经 `register_auth` 授权；
5. **标准统一铁律**：统一度量口径后不得各项目各自口径（CPI/SPI/里程碑准点率/变更计费率），单一真实数据源。

**禁用**：替代项目级评审/门禁；替代组合治理投资决策；未经 Program Board 决策继续推进已终止项目群。

**技能关系**：DevProjectTeamSkill=项目群协同模式入口；role-governance=台账读写与变更审计；role-project-init=成员项目启动；multi_project_isolation=环境资源仲裁衔接。

---

> 协作接口详见各宿主技能元数据及 `../../shared/references/api_contracts.md`；目录规范详见 `../../shared/references/directory_structure.md`；项目群管理标准详见 `../../references/program_management.md`

---

**文档版本**：v1.0.0（新增项目群/项目集协同管理层：define_program/manage_benefits/map_dependencies/align_schedule/standardize_execution/review_program/close_program，2026-08-16）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
