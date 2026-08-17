---
name: "role-program-mgmt"
description: "用户提到项目群、项目集、多项目协同、PMO 决策层、跨项目依赖、里程碑对齐、统一执行标准时加载本项目群管理角色包：负责项目群定义（业务论证/章程/路线图/治理四角色/tranche 划分）、收益管理（收益档案与追踪）、跨项目依赖矩阵、IMS 三层集成主进度（滚动式规划/关键路径/SAFe PI Planning）、统一执行标准与度量口径（CPI/SPI/里程碑准点率）、Program Board tranche 边界决策与收尾。用户说项目群/多项目协同/PMO 时加载。Load when the user manages a program/portfolio, multi-project coordination, PMO decisions, cross-project dependencies, or milestone alignment."
---

# role-program-mgmt 项目群管理角色包

> 版权：`../shared/references/COPYRIGHT.md`　Token：`../shared/references/token_standard.md`　总控：`../shared/governance.md`　标准：`../references/program_management.md`

## 1. 元数据

- **技能版本**：v1.0.0　**发布日期**：2026-08-16
- **变更记录**：v1.0.0 新增项目群/项目集协同管理层（role-program-mgmt）——对齐 PMI《项目集管理标准》第5版（6 绩效域：战略一致/收益管理/干系人参与/治理框架/合作/生命周期管理）+ MSP（tranche 分批交付 + Program Board 决策）+ IMS/EVM（三层集成主进度 + 统一度量口径）；7 个 action：define_program / manage_benefits / map_dependencies / align_schedule / standardize_execution / review_program / close_program；新增 28_项目群注册 / 29_项目依赖矩阵 / 30_项目群主进度 台账；三层治理模型（项目治理 < 项目群治理 < 组合治理）。
- **参考标准**：PMI《项目集管理标准》(SPM 5th)、MSP（Managing Successful Programmes）、Integrated Master Schedule（IMS）、EVM 挣值管理

## 2. 触发规则

用户表达「项目群/项目集/多项目协同/PMO 决策层/跨项目依赖/里程碑对齐/统一执行标准/收益管理」时加载本包。单角色场景直接 Read 本文件；需要台账时调用 `../shared/governance.md`；明细按需 Read `domain/program-management.md` 与 `program-management__resources/program_details.md`。

## 3. 流程（路由到 domain/）

| 环节 | 动作 | 明细 |
|------|------|------|
| 项目群定义 | define_program（业务论证/章程/路线图/治理四角色/tranche 划分） | `domain/program-management.md` |
| 收益管理 | manage_benefits（收益档案 owner/metric/基线/目标/兑现时间线 + 追踪） | `domain/program-management.md` |
| 依赖管理 | map_dependencies（FS/SS/FF/SF 依赖矩阵 + 相互交付物 + 共享资源 + 传导分析） | `domain/program-management.md` |
| 进度对齐 | align_schedule（IMS 三层主进度 + 滚动式规划 + 关键路径 + SAFe PI Planning 可选） | `domain/program-management.md` |
| 标准一致 | standardize_execution（统一执行标准 + 统一度量口径 CPI/SPI/缺陷密度/里程碑准点率/变更计费率 + 报告 cadence） | `domain/program-management.md` |
| 项目群评审 | review_program（Program Board tranche 边界决策：继续/转向/终止 + 三层门禁叠加） | `domain/program-management.md` |
| 项目群收尾 | close_program（收益确认/移交/资源释放/复盘归档） | `domain/program-management.md` |

> **治理铁律**：项目群协同必须在单项目启动/评审通过之后进行——Program Board 决策（继续/转向/终止）不得替代项目级 check_ready/stage_review，二者为叠加双层门禁；Program Manager 管理不决策、PMO 提供机制不决策、Program Board 做决策（详见 `../references/program_management.md` §3）。
> **时间一致**：`align_schedule` 产出 IMS 三层集成主进度（`台账/30_项目群主进度.csv`），依赖驱动的排期同步（上游延期自动传导下游，`台账/29_项目依赖矩阵.csv`）；敏捷项目群采用 SAFe PI Planning 增量对齐（可选）。
> **标准一致**：`standardize_execution` 统一各项目执行标准与度量口径（CPI/SPI/缺陷密度/里程碑准点率/变更计费率/资源负载），单一真实数据源，统一报告节奏（cadence）。

## 4. 输出规范与边界

- 台账经 `../shared/governance.md` 路由写入（主台账 CSV 读写，禁止 .xlsx）；
- 输出表格按 token_standard §3 阈值（Markdown/CSV）；
- 边界：仅负责跨项目协同层（项目群/项目集）；单项目内部由各角色包负责；组合治理（投资决策/项目立项选择）不属于本包。

---

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求建立项目群、登记多项目协同、管理跨项目依赖、对齐里程碑、统一执行标准、召开项目群评审；
- 前置：需确认项目群成员项目清单、各项目启动/评审状态、台账模板；
- 不适用：单项目独立推进（无跨项目协同需求）时不加载本包。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待定义 | 项目群需求已明确 | 项目群注册完成或中止 | 读取成员项目台账与背景 |
| 定义中 | 章程/路线图/治理结构已形成 | 关键产出形成 | 按流程推进项目群定义 |
| 交付中 | 依赖/进度/标准已对齐 | 收益实现或调整 | 按 tranche 推进交付 |
| 校验中 | 评审门禁已生成 | 评审通过或退回 | 检查时间/依赖/标准一致 |
| 阻塞 | 依赖冲突、资源冲突、标准不齐 | 补充信息/人工确认 | 暂停并记录阻塞原因 |
| 完成 | 收益确认且收尾归档 | 移交运营或组合层 | 归档证据并交接 |
| 回退 | 评审失败/依赖未决 | 回到最近稳定状态 | 撤销无效决策，保留审计 |

### 3. 执行动作层
- 执行步骤 1：定义项目群（业务论证/章程/路线图/治理结构/tranche）；
- 执行步骤 2：建立收益档案与依赖矩阵，对齐 IMS 三层主进度；
- 执行步骤 3：统一执行标准与度量口径，执行 Program Board 评审（继续/转向/终止）；
- 所需工具/脚本：总控台账、`../references/program_management.md` 标准、成员项目 `台账/` 数据；
- 输入输出约束：输出必须落盘到 `台账/`（28/29/30 CSV），不能跳过依赖校验与评审门禁。

### 4. 验收门禁
- 必须产出物：项目群注册、收益档案、依赖矩阵、IMS 主进度、标准一致检查、评审决策、收尾记录；
- 通过条件：时间对齐（无未决依赖冲突）、标准一致（度量口径统一）、Program Board 决策完成；
- 失败条件：依赖未决、标准不齐、收益口径不清、评审未通过；
- 审核对象：Program Board（决策主体）+ Sponsor（背书）+ 用户确认。

### 5. 失败处理
- 失败类型：依赖冲突未决、进度对齐失败、标准不统一、收益无法兑现；
- 恢复策略：回到依赖/进度/标准校验，补充信息后重审；
- 回滚方案：撤销受影响草稿，保留上一可用项目群状态；
- 重试策略：在依赖与标准解决后再重试；
- 是否需要人工确认：Program Board 决策（继续/转向/终止）必须人工确认。

### 6. 产出与交接
- 产出物列表：项目群注册、收益档案、依赖矩阵、IMS 主进度、评审决策、收尾记录；
- 保存路径：`台账/28_项目群注册.csv`、`29_项目依赖矩阵.csv`、`30_项目群主进度.csv`；
- 交接对象：成员项目各角色包 + role-governance 总控 + 组合治理层（如有）；
- 下一步动作：根据评审决策继续下一 tranche 或进入收尾；
- 归档条件：收益确认且收尾门禁通过。

### 7. 审计记录
- 执行时间：项目群动作开始/结束时间；
- 关键参数：项目群编号、成员项目、依赖、里程碑、评审决策、版本标识；
- 关键决策：Program Board 继续/转向/终止决策及理由；
- 结果证据：28/29/30 CSV、评审记录、收尾归档；
- 失败原因：记录在总控审计台账与交接文档。

---

**文档版本**：v1.0.0　**最后更新**：2026-08-16
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
