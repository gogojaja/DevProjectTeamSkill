# program_details — 项目群管理明细

> 角色包明细资源，配合 `../domain/program-management.md` 使用。来源：PMI《项目集管理标准》第5版（SPM 5th）、MSP（Managing Successful Programmes）、Integrated Master Schedule（IMS）、EVM 挣值管理。

## 1. 治理模型（三层）

| 层 | 范围 | 核心问题 | 决策主体 |
|----|------|----------|----------|
| 项目治理 | 单项目 | 是否按时间/成本/质量交付？ | 项目指导委员会 / Steering Committee |
| **项目群治理** | 一组相关项目及其组合成果 | 是否兑现收益？当前工作包是否仍正确？继续/转向/终止？ | **Program Board**（由 Senior Responsible Owner/Sponsor 主持） |
| 组合治理 | 全部项目/项目群竞争资金 | 应存在哪些项目/项目群？ | Portfolio / Investment Board |

- Program Board 在 **tranche 边界**做正式决策（继续/转向/终止），边界之间月度轻量跟踪；
- Program Board 与项目指导委员会的区别：前者治理整个项目群及其收益，后者只治理单项目交付；
- Program Manager 管理日常不决策；PMO 提供治理流程/报告/标准不决策。

## 2. 治理角色（四角色）

| 角色 | 职责 | 决策权 |
|------|------|--------|
| Sponsor / SRO（高级负责人） | 战略背书、资金、收益拥有者、主持 Program Board | 终止项目群、批准战略变更 |
| Program Board | 授权每个 tranche 与预算、批准范围/收益/目标变更、裁决组件冲突、continuation 决策 | 继续/转向/终止 |
| Program Manager | 协调多项目、监控风险、向 Board 报告 | 不决策（建议权） |
| PMO | 标准化工具/流程/报告、强制一致性、绩效跟踪 | 不决策（机制与数据） |

## 3. 项目群生命周期（对齐 SPM 5th + MSP）

| 阶段 | 关键活动 | 产物 |
|------|----------|------|
| 定义（Identify/Define） | 业务论证、章程、路线图、收益档案、tranche 计划、治理结构 | 28_项目群注册.csv |
| 交付（Manage Tranches / Deliver Capability） | 按 tranche 交付、依赖协调、IMS 更新、标准执行 | 29/30 CSV + 进度 |
| 收益实现（Realize Benefits） | 对照收益档案核实兑现、嵌入运营 | 收益追踪 |
| 收尾（Close） | 收益确认、移交、资源释放、复盘归档 | 收尾报告 |

## 4. 收益管理（BRM）

- **收益地图**：能力 → 中间成果 → 最终收益（因果链），对齐战略目标；
- **收益档案**（每项）：owner / metric / baseline / target / realization timeline / enabling changes / risks；owner 与业务线负责人签订；
- **追踪**：按 KPI 与档案对照，威胁收益提前升级（衔接 12_风险问题台账 P1~P4 升级阶梯）；
- **商业论证保持"活文档"**：证据积累后持续更新，含敏感性分析。

## 5. 依赖管理

- 四类依赖：**FS**（Finish-to-Start 完成到开始）、**SS**（Start-to-Start 开始到开始）、**FF**（Finish-to-Finish 完成到完成）、**SF**（Start-to-Finish 开始到完成）；
- 依赖对象：相互交付物、共享资源、顺序约束；
- 传导分析：上游延期 → 下游风险自动识别；关键路径依赖（零浮动，延误直接拖期）与浮动依赖（可缓冲）区分；
- 共享资源冲突衔接 `25_环境资源清单.csv` 与 multi_project_isolation §10 仲裁。

## 6. IMS 三层集成主进度

| 层 | 内容 | 粒度 | 更新 |
|----|------|------|------|
| Program Master Schedule | 项目群概要时间线、波次、关键节点 | 概要 | 月评审 |
| Integrated Master Plan（IMP） | 里程碑级，含关键事件准则 | 里程碑 | 周 |
| 明细排期（rolling wave） | 近端 2~6 周详细 + 远端里程碑概要 | 任务/工作包 | 周 |

- 逻辑链接：任务间 cause-effect 链接，一处延期自动传导下游风险；
- 关键路径：最长依赖序列决定最短工期，零浮动任务延误直接影响结束日期；
- 健康度：SPI（=EV/PV，<1 落后）与总浮动每周监控；
- 基线：IMS 基线化 + 定期 re-baseline（避免频繁或从不基线化两个极端）；
- 敏捷项目群（可选）：SAFe PI Planning——8~12 周 Program Increment 详细规划 + 同步规划仪式（跨团队对齐）+ 增量评审。

## 7. 统一度量口径（执行标准一致）

| 度量 | 公式/口径 | 阈值 | 作用 |
|------|-----------|------|------|
| CPI | EV/AC | ≥1 优于预算 | 成本效率 |
| SPI | EV/PV | ≥1 提前于计划 | 进度效率 |
| 缺陷密度 | 缺陷数/千行或功能点 | 按质量基准 | 质量 |
| 里程碑准点率 | 按期里程碑/总里程碑 | ≥目标 | 计划可靠性 |
| 变更计费率 | 已计费变更/总变更 | ≥目标 | 变更控制 |
| 资源负载 | 已分配工时/可用工时 | ≤80% | 资源健康 |

- 统一数据采集程序与报告模板，避免各项目口径不一导致度量失真；
- CPI 与 SPI 必须合看（单独指标会掩盖风险）；
- 报告节奏：周报 RAID+EVM、里程碑评审、月报趋势（红黄绿分级 + 高层介入机制）。

## 8. Program Board 评审

- **tranche 边界决策**：继续（proceed）/ 转向（re-plan）/ 终止（close）；
- 决策依据：收益是否兑现、当前工作包是否仍正确、业务论证是否仍成立；
- **三层门禁叠加**：项目级 stage_review 通过 → 项目群评审三 Gate（时间对齐 / 依赖无冲突 / 标准一致）；
- 评审节奏：tranche 边界正式决策 + 月度轻量跟踪（过长漂移、过频变交付团队）；
- 决策留痕：评审纪要 + 决策记录，禁止无记录口头决策；
- 仲裁衔接：跨项目资源/时间/依赖冲突超出 Program Board 决策权限 → 升阶组合治理或用户/Sponsor 决策（衔接 priority-arbitration P0~P6 与 change_audit）。

## 9. 收尾

- 收益确认：对照收益档案逐项核实兑现并移交运营；
- 资源释放：CMDB release + `25_环境资源清单` 释放登记；
- 复盘归档：提炼可固化流程/复用工具/降 Token（衔接 `retrospect_harvest`）；
- 结束临时治理结构（Program Board 解散）。

---

**文档版本**：v1.0.0　**最后更新**：2026-08-16
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
