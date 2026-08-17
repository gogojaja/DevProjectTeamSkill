---
name: "program-management-skill"
description: "Program management skill aligned with PMI Standard for Program Management (SPM 5th), MSP, IMS and EVM. Covers program definition, benefits management, dependency matrix, integrated master schedule, standardized execution metrics, document & configuration management, program board tranche decisions and program closure. Invoke when coordinating multiple related projects as a program/portfolio program office (PMO) layer."
---

# ProgramManagementSkill 项目群管理技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`；项目群管理标准详见 `../../references/program_management.md`

## 1. 基础元数据

- **技能唯一标识**：ProgramManagementSkill
- **技能版本**：v1.1.0（v1.1.0 新增 manage_documents 文档与配置管理 action + 31_文档配置管理.csv；对齐 PMI SPM 5th / MSP 5th）
- **定位**：跨项目协同层（Program/项目群 PMO 决策层），管理一组相互关联的项目（项目群），对齐 PMI《项目集管理标准》第5版与 MSP。解决核心痛点：**各项目时间信息一致**（IMS 集成主进度 + 依赖传导）与**执行标准一致**（统一度量口径 + 报告节奏），并以**文档与配置管理**保障单一信息源与可追溯。
- **调用主体**：DevProjectTeamSkill（项目群协同模式）/ 用户直接指令
- **依赖工具**：role-governance（台账读写 `create_baseline`/`change_audit`/`risk_scan`）、role-project-init（成员项目启动产物）、tools/cmdb（环境资产配置）
- **核心约束**：
   1. 项目群协同必须在成员项目启动/评审通过后叠加进行，Program Board 决策不替代项目级门禁；
   2. Program Manager 管理不决策、PMO 提供机制不决策、Program Board 做决策（继续/转向/终止）；
   3. 本包只做跨项目协同，单项目内部由对应角色包负责；组合治理（投资决策）不属于本包。

---

## 2. 统一入参标准

统一入参：`action`（八指令之一）+ `content`（项目群背景/收益/依赖/进度/标准/文档/评审/收尾信息）+ `stage`（当前环节）+ `user_confirm`（无/同意/拒绝/查错）。

#### action 指令清单

| action | 作用 | 前置条件 |
|--------|------|----------|
| `define_program` | 项目群定义（业务论证/章程/路线图/治理四角色/tranche 划分） | 成员项目已启动 |
| `manage_benefits` | 收益管理（收益档案 owner/metric/基线/目标/兑现时间线/维持 + 追踪） | define_program |
| `map_dependencies` | 跨项目依赖矩阵（FS/SS/FF/SF + 强度 + 相互交付物 + 共享资源 + 传导分析） | manage_benefits |
| `align_schedule` | IMS 三层集成主进度（滚动式规划/关键路径/SAFe PI Planning 可选） | map_dependencies |
| `standardize_execution` | 统一执行标准与度量口径（CPI/SPI/缺陷密度/里程碑准点率/变更计费率） | align_schedule |
| `manage_documents` | 文档与配置管理（单一信息源/命名/版本/基线/CI/留存/密级，登记 31_文档配置管理.csv） | define_program（贯穿全程） |
| `review_program` | Program Board tranche 边界决策（继续/转向/终止 + 三层门禁叠加） | standardize_execution |
| `close_program` | 项目群收尾（收益确认/移交/资源释放/复盘归档） | review_program=继续 或 终止 |

---

## 3. 项目群管理流程

流程主线：`define_program → manage_benefits → map_dependencies → align_schedule → standardize_execution → manage_documents(贯穿) → review_program → (继续) → 下一 tranche / (终止) → close_program`；评审 No-Go → 转向（re-plan）或终止，停止。

- **门禁**：每环节产出经用户确认后进入下一环节；Program Board 决策必须人工确认；**文档与配置管理贯穿全程**（每次工件生成/变更均登记 31）；
- **双层门禁**：项目级 check_ready/stage_review 通过 → 再执行项目群评审（时间对齐/依赖无冲突/标准一致）；
- **No-Go 后重启**：阻塞消除后从对应环节恢复，不需从头重跑。

### 环节 1：项目群定义（define_program）
输出**业务论证** + **项目集章程** + **项目集路线图** + **治理结构四角色** + **tranche 划分**；治理结构经干系人确认；战略一致不清晰时输出「项目群定义缺陷清单」，不强行通过。
输出：《项目群注册》写入 `28_项目群注册.csv`（编号/名称/战略目标/收益目标/成员项目清单/治理四角色/tranche 划分/路线图/统一度量口径/执行标准基线/文档库路径/创建时间/版本/状态/收益档案），经 Sponsor 与用户确认；同时于 `31_文档配置管理.csv` 登记章程/路线图 CI 基线。

### 环节 2：收益管理（manage_benefits）
建立**收益档案（Benefits Register）**与**收益地图**；含 owner/metric/基线/目标/兑现时间线/使能变更/威胁/维持计划；贯穿生命周期持续追踪。
输出：《收益档案与追踪》写入 `28_项目群注册.csv` 收益档案区（或独立收益台账），经 Sponsor 确认；重大收益变更走 `change_audit` 并刷新 31 版本。

### 环节 3：跨项目依赖管理（map_dependencies）
**依赖矩阵**——四类依赖（FS/SS/FF/SF）+ 强度（硬/软）+ 相互交付物 + 共享资源；**传导分析**：上游延期自动传导下游，关键路径依赖（硬/零浮动）与浮动依赖（软/可缓冲）区分；冲突升阶 `change_audit`。
输出：《项目依赖矩阵》写入 `29_项目依赖矩阵.csv`（依赖编号/源项目/目标项目/依赖类型/依赖强度/依赖对象/方向/关键路径标记/状态/责任方/传导风险/缓解措施），经相关项目经理确认。

### 环节 4：进度对齐（align_schedule）
**IMS 三层集成主进度**——第 1 层 Program Master Schedule、第 2 层 Integrated Master Plan（里程碑级，含关键事件准则）、第 3 层明细排期（滚动式规划）；**关键路径**标注（SPI/总浮动监控）；敏捷项目群可选 SAFe PI Planning；周更新 + 月评审；基线变更走 `change_audit`。
输出：《项目群主进度》写入 `30_项目群主进度.csv`（项目/里程碑/计划日期/实际日期/偏差(天)/SPI/关键路径标记/健康度(红黄绿)/状态/责任方/更新记录/更新日期），经 Program Board 确认。

### 环节 5：统一执行标准（standardize_execution）
统一各项目**执行标准**与**度量口径**——CPI/SPI/缺陷密度/里程碑准点率/变更计费率/资源负载（≤80%）；统一**报告节奏**（周报 RAID/EVM、里程碑评审、月报趋势）；单一真实数据源。
输出：《标准一致性检查清单》（统一标准项/度量口径/报告节奏/各项目达标状态），经 PMO 确认。

### 环节 6：文档与配置管理（manage_documents，贯穿）
落实 `program_management.md` §9：单一信息源、受控库、命名规范、版本/状态生命周期（Draft→Review→Baseline→Obsolete）、CI 基线、留存与密级、变更控制。
输出：《文档配置管理登记》写入 `31_文档配置管理.csv`（文档ID/项目群编号/文档类别/文档名称/版本/状态/密级/责任人/存放路径/基线日期/变更记录/留存期限/关联配置项），每次工件生成或变更时增量登记；受控库纳入 git 版本化与 solidify 快照。

### 环节 7：项目群评审（review_program）
**Program Board 在 tranche 边界决策**——继续/转向/终止；**三层门禁叠加**：项目级 stage_review 通过 → 项目群评审（时间对齐 Gate / 依赖无冲突 Gate / 标准一致 Gate）；评审节奏：tranche 边界正式决策 + 月度轻量跟踪；决策留痕，禁止无记录口头决策。
输出：《项目群评审决策》（继续/转向/终止 + 理由 + 门禁检查项 + 纪要入库），经 Program Board 与用户确认。

### 环节 8：项目群收尾（close_program）
收益确认（对照收益档案逐项核实兑现）+ 移交运营 + 资源释放（衔接 CMDB 释放与 `25_环境资源清单`）+ 复盘归档（提炼可固化流程/复用工具/降 Token）+ 文档进入**只读归档库**（按 §9 留存期限）。
输出：《项目群收尾报告》（收益兑现清单/移交清单/资源释放/复盘结论/归档清单），经 Sponsor 确认后归档。

---

## 4. 触发规则
- 用户提出「项目群/项目集/多项目协同/PMO 决策层/文档与配置管理/跨项目依赖/里程碑对齐/统一度量口径/项目群评审」。

## 5. 输出规范
- 台账（28/29/30/31 CSV）经 role-governance 路由写入，禁止 .xlsx；输出表格按 token_standard §3 阈值；
- 每环节产出须经用户确认后方可进入下一环节；
- 与成员项目衔接：读取各项目 `台账/` 数据，不重复建立单项目台账。

## 6. 边界（安全铁律）
1. **叠加门禁铁律**：项目群评审不替代项目级 check_ready/stage_review，双层叠加执行；
2. **决策主体铁律**：Program Manager/PMO 不得代行 Program Board 决策，继续/转向/终止须人工确认并留痕；
3. **收益锚定铁律**：业务论证不成立或收益无法兑现时，Program Board 应终止项目群而非坚持推进；
4. **数据边界铁律**：访问成员项目 `台账/` 遵循项目访问边界（`26_访问边界.csv`），跨项目访问经 `register_auth` 授权；
5. **标准统一铁律**：统一度量口径后不得各项目各自口径，单一真实数据源；
6. **文档受控铁律**：所有项目群工件须登记 `31_文档配置管理.csv`，禁止分散多版本真相、禁止无 change_audit 基线变更、禁止删除历史基线（仅标记 Obsolete）。

**禁用**：替代项目级评审/门禁；替代组合治理投资决策；未经 Program Board 决策继续推进已终止项目群；绕过文档与配置管理。

**技能关系**：DevProjectTeamSkill=项目群协同模式入口；role-governance=台账读写与变更审计；role-project-init=成员项目启动；multi_project_isolation=环境资源仲裁衔接。

---

> 协作接口详见各宿主技能元数据及 `../../shared/references/api_contracts.md`；目录规范详见 `../../shared/references/directory_structure.md`；项目群管理标准详见 `../../references/program_management.md`

---

**文档版本**：v1.1.0（v1.1.0：新增 manage_documents 文档与配置管理 action、31_文档配置管理.csv、§9 文档与配置管理；对齐 PMI SPM 5th / MSP 5th，2026-08-17）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
