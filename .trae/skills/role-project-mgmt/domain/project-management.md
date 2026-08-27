---
name: "project-management-skill"
description: "Project manager execution-layer skill: daily control loop across PMBOK 10 knowledge areas, RAID log, stage plan/milestones, highlight report, change coordination, and lessons learned. Invoke when managing a project day-to-day without performing engineering delivery (requirements/design/dev/test/deploy)."
---

# 项目经理执行层 · 日常管控

> 归属：role-project-mgmt　版本：v21.0.0
> 对齐：PMBOK 7（8 绩效域）· PRINCE2 2023（管理产品）· 与 `role-governance`（保障/审计层）职责分离

## 1. 接管确认（启动即做）

读取项目根 `交接文档.md` 断点区 + 启动期产物：
- `项目章程`（成功标准、PM 职权、签字批准）——来自 `role-project-init`
- 范围初定 + `00_阶段配置.csv`（阶段裁剪）——来自 `role-project-init`
- `27_组织架构.csv`（RACI）+ `12_风险问题台账.csv`（升级机制）——来自 `role-project-init`

若缺失章程/范围/RACI 任一项 → 阻塞，先回 `role-project-init` 补齐（硬前置）。

## 2. 日常管控循环（十大知识领域日/周态）

| 知识领域 | PM 执行动作（做） | 交给保障层（审） |
|----------|------------------|------------------|
| 整合 | 维护项目全景、串接各角色状态、发周会 | 阶段评审/门禁 |
| 范围 | 跟踪范围基准偏差、收集变更 | 范围变更审计（`role-governance` scope-change） |
| 进度 | 维护里程碑/关键路径、红黄绿预警 | EVM/进度度量 |
| 成本 | 跟踪预算消耗、预警超支 | 成本度量/门禁 |
| 质量 | 推动质量门禁结果闭环 | 质量门禁（`role-governance` quality-gate） |
| 资源 | 协调人力/环境资产（CMDB）占用 | 环境就绪核对 |
| 沟通 | 编发进展报告、干系人沟通 | — |
| 风险 | RAID 风险登记与应对跟踪 | 风险扫描复核 |
| 采购 | 跟踪外部依赖/合同节点 | 合规审计 |
| 干系人 | 维护权力-利益视图、期望管理 | — |

> 工程角色（需求/架构/开发/测试/投产）在「项目管理模式」下为**协调只读**：仅读其状态/依赖/风险，不触发其交付 action。

## 3. RAID 台账（PM 自有轻量视图）

- 风险 Risks / 假设 Assumptions / 问题 Issues / 依赖 Dependencies 统一记入 `台账/12_风险问题台账.csv`（复用保障层主台账，不另建库）；
- 每条含：ID、类型、归属阶段、责任人、严重度、状态、到期、应对；
- 周巡检：更新状态、升级临近到期的 P1~P4（升级机制见 `role-project-init`）。

## 4. 阶段计划与进展报告

- **阶段计划**：依据 `00_阶段配置.csv` 细化里程碑 + 容差（管理 by exception，超容差才升级决策层）；
- **进展报告（highlight report）**：周期产出，含 进度/成本/质量/风险/依赖/下一步/需决策项，输出 CSV（`评审报告_<项目>_<期>_进展.csv`）或 Markdown 摘要；仅回显首 5 行 + 行数（token_standard §3）。

## 5. 变更协调

1. 接收变更请求（来源：干系人/工程角色/RAID）；
2. PM 做**影响初评**（范围/进度/成本/风险），不自行裁定放行；
3. 提交 `role-governance` 的 `scope-change` 复核 + 门禁留痕（`13_安全审计台账.csv`）；
4. 闭环跟踪至关闭，结果回写 RAID 与进展报告。

## 6. 经验教训

- 阶段末/问题关闭后登记经验教训（`23_复用资产.csv` 同源，或独立 `经验教训_<项目>.csv`）；
- 复盘要点：何因、何果、可复用流程/工具/降 Token 措施；
- 资产化交接保障层归档，供后续项目检索复用。

> 全部台账读写经 `../../shared/governance.md`，禁止 .xlsx；外部文件/系统文件操作须 `register_auth` 授权（铁律 #7/#7a）。
