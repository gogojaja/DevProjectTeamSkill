# program_management.md — 项目群/项目集管理标准

> 跨项目协同层标准（role-program-mgmt 依据）。来源：PMI《项目集管理标准》(SPM 5th, 2023)、MSP《成功管理项目群》(5th, 2020)、Integrated Master Schedule（IMS）、EVM 挣值管理（ANSI EIA-748）、SAFe、ISO 10007 配置管理 / ISO 15489 文档管理。

## 1. 术语与三层治理定位

- **项目（Project）**：为创造独特可交付成果而进行的临时性工作；
- **项目集/项目群（Program）**：经过**协调管理以获取单独管理无法取得之收益**的一组相互关联的项目、子项目集与项目集活动；"互相关联"+"多个项目"是属性，"协调管理收获收益"是管理特征；
- **项目组合（Portfolio）**：为战略目标而选择并优先级排序的全部项目/项目群集合，投资决策层；
- **本仓库三层治理**：项目治理（role-governance 单项目总控）< **项目群治理（role-program-mgmt，Program Board 决策）** < 组合治理（战略投资层，不实现）。
- **信息治理**：项目群所有工件纳入**文档与配置管理**（§9），单一信息源、受控版本、可追溯——这是 SPM/M并将其作为治理子域（Governance）的硬性要求。

## 2. PMI《项目集管理标准》(SPM 5th) 要点

### 2.1 八项原则（Principles）
1. 干系人（Stakeholder）；2. 收益（Benefits）；3. 管理职责（Stewardship）；4. 协同（Collaboration）；5. 团队（Team）；6. 领导力（Leadership）；7. 治理（Governance）；8. 生命周期（Life Cycle）。
> 注意：5th 版将"合作/协同"列为**原则**而非绩效域，绩效域收敛为 5 个。

### 2.2 五项绩效域（Performance Domains）
| 绩效域 | 核心产出 |
|--------|----------|
| 战略一致（Strategy Alignment） | 业务论证 / 项目集章程 / **项目集路线图** / 环境评估 / 风险策略；确保组件贡献战略成果 |
| 收益管理（Benefits Management） | 收益识别 → 分析与规划 → 交付 → 过渡 → 维持（Benefits Realization & Sustainment） |
| 干系人参与（Stakeholder Engagement） | 识别 → 分析 → 争取规划 → 争取 → 沟通；持续承诺管理 |
| 治理（Governance） | 决策权 / 治理主体 / 设计与实施；**含文档与配置管理**（§9）、门禁、审计 |
| 生命周期管理（Life Cycle Management） | 定义 → 交付 → 收尾；tranche 波次管理 |

### 2.3 生命周期
- **定义阶段**：构建活动 + 规划活动（业务论证/章程/路线图/tranche 计划/治理结构/收益档案）；
- **交付阶段**：管理交付、绩效、收益维持与过渡、变更、沟通、财务、信息、采购、质量、资源、风险、进度、范围；
- **收尾阶段**：收益确认、财务收尾、信息存档过渡、采购收尾、资源过渡、风险过渡。

## 3. MSP（Managing Successful Programmes 5th）要点

### 3.1 七项原则
与战略对齐（Aligned to the corporate strategy）、目标引领（Lead with purpose）、聚焦成果（Focus on outcomes）、增加价值（Add value）、设计交付连贯能力（Design and deliver coherent capability）、从经验中学习（Learn from experience）、保持透明（Be transparent）。

### 3.2 治理主题（Themes）
组织（角色/职责/决策权：SRO、Program Board、Program Manager、Business Change Managers）、领导力与干系人、收益管理、蓝图设计与交付、计划与控制、商业论证、风险与问题管理、质量与保证。

### 3.3 Transformational Flow（转型流）
识别项目群（Identify）→ 定义项目群（Define：蓝图/详细商业论证/治理/收益地图与档案/tranche 计划）→ **管理 tranche（Manage the Tranches，分批交付产生能力增量，tranche 之间复盘调整）** → 交付能力（Deliver the Capability）→ 收益实现（Realize the Benefits）→ 收尾（Close）。

### 3.4 关键：Program Board 决策
Program Board 在 **tranche 边界**决策：**继续 / 转向 / 终止**；边界之间月度轻量跟踪。Program Manager 管理不决策、PMO 提供机制不决策。

## 4. IMS 集成主进度（时间信息一致核心）

- **三层结构**：Program Master Schedule（概要时间线）→ Integrated Master Plan/IMP（里程碑级，含关键事件准则）→ 明细排期（滚动式规划 rolling wave：近端 2~6 周详细 + 远端里程碑概要）；
- **逻辑链接**：跨项目任务 cause-effect 链接，上游延期自动传导下游；
- **关键路径**：最长依赖序列决定最短工期，零浮动任务延误直接影响结束日期；
- **健康度**：SPI（=EV/PV）与总浮动每周监控，周更新 + 月评审；
- **EVM 合规**：EVMS 对齐 ANSI EIA-748（CPI/SPI/AC/EV/PV 口径统一），CPI 与 SPI 合看不单读；
- **基线**：IMS 基线化 + 定期 re-baseline（避免频繁或从不基线化两个极端），基线变更走 change_audit；
- **敏捷项目群（可选）**：SAFe PI Planning——8~12 周 Program Increment 详细规划 + 同步规划仪式（跨团队对齐）+ 增量评审；价值流（Value Stream）映射对齐。

## 5. 统一执行标准与度量（执行标准一致核心）

- **统一范围**：流程 / 模板 / 门禁 / 质量标准 / 度量口径 / 报告节奏（cadence）；
- **度量口径**：CPI（EV/AC ≥1 优）、SPI（EV/PV ≥1 优）、缺陷密度、里程碑准点率、变更计费率、资源负载（≤80%）；CPI 与 SPI 合看不单读；
- **单一真实数据源**：消除多版本真相，统一数据采集程序与报告模板；
- **报告节奏**：周报 RAID+EVM、里程碑评审、月报趋势（红黄绿分级 + 高层介入）。

## 6. 依赖管理

- 四类依赖：FS / SS / FF / SF；
- 依赖对象：相互交付物、共享资源、顺序约束；
- 依赖强度：**硬依赖（Hard，不可缓冲）** vs **软依赖（Soft，可缓冲）**——关键路径依赖为硬；
- 传导分析：上游延期 → 下游风险；关键路径依赖（零浮动）与浮动依赖（可缓冲）区分；
- 共享资源冲突衔接 `multi_project_isolation.md` §10 与 `25_环境资源清单.csv` / CMDB 仲裁；
- **CMDB 关联**：共享资源依赖（端口/GPU/模型服务）须在 `29_项目依赖矩阵.csv` 的「关联CMDB资产ID」列登记对应 CMDB 资产，使依赖可追溯、可仲裁（详见 §9.8）。

## 7. 收益管理（Benefits Realization Management）

- **收益地图**：能力 → 中间成果 → 最终收益（因果链），对齐战略目标；
- **收益档案（Benefits Register）**：每项收益含 owner / metric / baseline / target / realization timeline / enabling changes / threats / sustainment plan；
- **收益维持（Sustainment）**：移交运营后持续兑现，避免"交付即弃"；
- **追踪**：按 KPI 与档案对照，威胁收益提前升级（衔接 `12_风险问题台账` P1~P4 升级阶梯）；
- **商业论证"活文档"**：证据积累后持续更新，含敏感性分析（见 §9 文档生命周期）。

## 8. 项目群评审（Program Board）

- **tranche 边界决策**：继续（proceed）/ 转向（re-plan）/ 终止（close）；
- 决策依据：收益是否兑现、当前工作包是否仍正确、业务论证是否仍成立；
- **三层门禁叠加**：项目级 stage_review 通过 → 项目群评审四 Gate（时间对齐 / 依赖无冲突 / 标准一致 / **环境就绪**）；
- **环境就绪 Gate（Environment Readiness）**：tranche 边界决策前先查 CMDB 关键资产状态（端口已注册 / 模型服务在线 / GPU 可用）；环境未就绪 → 阻塞评审或降优先级，不进入下一 tranche（详见 §9.8）；
- 评审节奏：tranche 边界正式决策 + 月度轻量跟踪（过长漂移、过频变交付团队）；
- 决策留痕：评审纪要 + 决策记录，禁止无记录口头决策；
- 仲裁衔接：跨项目冲突超出 Program Board 权限 → 升阶组合治理或 Sponsor 决策（衔接 `priority-arbitration` P0~P6 与 `change_audit`）。

## 9. 文档与配置管理（Document & Configuration Management，行业最佳实践）

> 作用：保障项目群**单一信息源、受控版本、可追溯、可审计**。对齐 ISO 15489（文档管理）、ISO 10007（配置管理）、PMI 治理子域。

### 9.1 单一信息源与受控库
- 所有项目群工件集中受控库（本仓库 `台账/` 或指定 PMO 库，本机为 `D:\trae\台账\`），**禁止分散多版本真相**；
- 受控库纳入版本化（git）与定期快照（solidify），保障可回溯。

### 9.2 文档分类与密级
| 类别 | 工件示例 | 密级（对齐 iron_rules §3） |
|------|----------|----------------------------|
| 战略类 | 业务论证 / 章程 / 路线图 | B 脱敏入库（含环境/路径） |
| 收益类 | 收益档案 / 收益追踪 | C 正常 |
| 治理类 | 决策纪要 / 门禁记录 | C 正常 |
| 计划类 | IMS / 依赖矩阵 | C 正常 |
| 标准类 | 执行标准基线 | C 正常 |
| 文档类 | 本文档 / 模板 | C 正常 |
| 资产类 | 凭据/密钥别名 | A 禁止入库（仅别名） |

### 9.3 命名规范
`[项目群编号]_[类]_[工件]_v[主.次]_[状态].csv`
- 状态 ∈ {Draft 草稿, Review 评审, Baseline 基线, Obsolete 作废}；
- 例：`PG-LOCAL-001_计划_IMS_v1.0_Baseline.csv`。

### 9.4 版本与状态生命周期
`Draft → Review → Baseline（Program Board 批准）→ Obsolete（被新基线取代，保留归档）`；
- 基线化需 Program Board 批准并记录；基线变更走 `change_audit`；
- 历史基线**不得删除**，仅标记 Obsolete，满足审计与留存。

### 9.5 配置管理（Configuration Management）
- 识别**配置项 CI**：章程 / 路线图 / 收益档案 / IMS / 依赖矩阵 / 标准基线 / 环境资产；
- 建立 CI 基线 + 版本历史；环境资产（端口/GPU/模型容器）经 CMDB 配置管理（`register_env_asset`）；
- 配置项变更触发依赖/进度重算（传导分析）。

### 9.6 变更控制与留存
- 文档变更走 role-governance `change_audit`；重大工件（章程/路线图/收益档案）变更须经 Program Board 决策，禁止无记录口头修改；
- 留存与归档：收尾时按 retention 归档（收益确认/移交/复盘），临时治理结构解散后文档进入**只读归档库**；保留期建议 ≥ 项目结束后 3 年或合规要求；
- 访问与权限：按四角色 + 密级授权（`register_auth`），外部访问经 `26_访问边界.csv`。

### 9.7 工具链
台账 CSV（UTF-8 BOM，禁 .xlsx）+ git 版本化 + CMDB 资产登记 + solidify 快照。

### 9.8 环境与资产配置（CMDB 集成）
> 程序完整配置管理 = §9 文档/工件 CI（`31_文档配置管理.csv`）+ 本节制环境/基础设施 CI（CMDB）。二者合为程序级配置管理（**环境 + 文档**）。

- **职责边界（避免重复）**：CMDB（工具层 `tools/cmdb`，对齐 ITIL 配置管理）是环境 CI 的**单一信息源**（主机/端口/GPU/模型容器/共享服务）；程序台账不存环境明细，仅存「引用 + 状态快照」，真相源仍在 CMDB；
- **登记与仲裁**：程序通过 `register_env_asset` 登记共享环境资产，冲突（独占资源先注册先得）升阶 `change_audit` 留痕（衔接 `multi_project_isolation.md` §10 与 `25_环境资源清单.csv`）；
- **与依赖矩阵（29）关联**：29 增「关联CMDB资产ID」列，使共享资源依赖（端口/GPU/模型服务）可追溯、可仲裁；此类依赖属硬依赖（§6），可用性直接影响关键路径；
- **资源负载度量**：统一度量「资源负载≤80%」以 CMDB 实时占用为准，而非各项目自报；
- **环境就绪门禁**：Program Board 在 tranche 边界决策前，先查 CMDB 关键资产状态（端口已注册 / 模型服务在线 / GPU 可用）；环境未就绪 → 阻塞评审或降优先级，不进入下一 tranche（见 §8 第四 Gate）；
- **收尾释放**：资源释放经 CMDB release（见 §9.6 / §10）。

## 10. 本仓库落点

| 环节 | action | 台账 |
|------|--------|------|
| 项目群定义 | define_program | 28_项目群注册.csv |
| 收益管理 | manage_benefits | 28 收益档案区 |
| 依赖管理 | map_dependencies | 29_项目依赖矩阵.csv |
| 进度对齐 | align_schedule | 30_项目群主进度.csv |
| 标准一致 | standardize_execution | 标准一致性检查清单 |
| 文档与配置管理 | manage_documents | 31_文档配置管理.csv |
| 项目群评审 | review_program | 评审记录 CSV |
| 项目群收尾 | close_program | 收尾归档 |

- 明细执行见 `role-program-mgmt/domain/program-management.md` 与 `program-management__resources/program_details.md`。
- 环境/基础设施 CI 由 CMDB（`tools/cmdb`）统一管理，程序库通过「关联CMDB资产ID」引用，不重复登记。

## 11. 与现有机制衔接
- **优先级仲裁**：跨项目资源/时间/依赖冲突超出 Program Board 权限 → 升阶组合治理或 Sponsor 决策（衔接 `priority-arbitration` P0~P6 与 `change_audit`）；
- **问题升级**：项目群级问题走 `12_风险问题台账` P1~P4 升级阶梯；
- **环境资源**：跨项目共享资源冲突走 `25_环境资源清单` + CMDB 仲裁；
- **文档与配置**：工件命名/版本/留存/密级统一走 §9，登记 `31_文档配置管理.csv`；
- **访问边界**：跨项目访问成员项目台账遵循 `26_访问边界` + `register_auth` 授权。

---

**文档版本**：v1.1.1　**最后更新**：2026-08-17（CMDB 纳入程序管理范畴：新增 §9.8 环境与资产配置（CMDB 集成）；依赖矩阵 29 增「关联CMDB资产ID」；评审增「环境就绪」第四 Gate）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
