---
name: "project-risk-skill"
description: "Project risk management ROUTING sub-skill for role-governance. Delegates the implementation of risk register initialization, RAID four-dimension ledger (risk/assumption/issue/dependency), periodic risk scanning (probability×impact grading P1~P4), risk response strategies, and issue escalation to the standalone deployable skill `risk-mgmt` (single source of truth). This file retains only governance routing (risk_scan / stage_review risk口径) and risk policy boundaries. Invoke when scanning risks, updating the risk register, or assessing risk impact."
---

# ProjectRiskSkill 项目风险管理（治理路由 · 瘦引用）

> 版权声明详见 `../../shared/references/COPYRIGHT.md`
> **权威实现已迁出（单一信源）**：风险登记册初始化 / RAID 四维台账（risk·assumption·issue·dependency）/ 风险巡检与概率×影响分级（P1~P4）/ 风险应对策略 / 问题升级机制的**实现逻辑**统一收敛到独立可部署技能 **`risk-mgmt`**（工具 `tools/raid_ops.py` v1.0.0，标准 `references/raid_standard.md` v1.0.0，内化自 dev-project-mgmt `raid_manager.py` + MCP `risk_scan`）。本文件仅保留 role-governance 的**路由触发**与**风险治理边界策略**，不复制实现细节（DRY / 铁律 #1 单源）。

## 1. 触发规则（治理路由 → 委派 risk-mgmt）

| action | 作用 | 委派明细（risk-mgmt） | 主命令 |
|--------|------|----------------------|--------|
| `risk_scan` | 风险巡检（登记册更新/新风险识别/概率×影响分级扫描） | `risk-mgmt/domain/scan.md` | `raid_ops.py scan` / `list` |
| （登记册初始化） | 七类风险预设 + RAID 四维登记册建立 | `risk-mgmt/domain/register-init.md` | `raid_ops.py add` |
| （风险应对） | 规避/减轻/转移/接受/应急预案 + 状态流转 | `risk-mgmt/domain/response.md` | `raid_ops.py update` / `close` |
| `stage_review`（风险协同） | 问题分级 P1~P4 + 四级升级阶梯 + 变更协同 | `risk-mgmt/domain/coordination.md` | `raid_ops.py scan --json` |

- **调用主体**：ProjectMonitorSkill（薄路由壳按 action 分发）；风险巡检、P1 高风险裁决为 `check_gate`/`stage_review` 协同子步骤。
- **参考标准**：`references/raid_standard.md` v1.0.0（RAID 与风险管理标准）。
- **依赖工具**：`tools/raid_ops.py` v1.0.0（RAID 逻辑单一信源；MCP `raid_mgmt`/`risk_scan` 以 subprocess 委派）。

## 2. 风险治理边界策略（保留 · 实现委派）

以下为 role-governance 的**风险治理策略**；判定与实现逻辑见 `risk-mgmt`（不在此复制）：

1. **登记册全覆盖**：全部风险/假设/问题/依赖纳入 `台账/12_风险问题台账.csv`，禁止台账外私下跟踪。→ `risk-mgmt/domain/register-init.md`
2. **等级量化**：风险按概率×影响量化分级（P1~P4），杜绝主观判断；P1 高风险（≥12）立即制定应对方案并升级。→ `risk-mgmt/domain/scan.md`
3. **状态流转受控**：RAID 状态迁移须合法（`closed` 终态），非法流转拒绝，关闭自动填关闭日期留痕。→ `references/raid_standard.md` §5
4. **单一 Owner**：每条 RAID 唯一责任人（对齐 RACI 唯一 A），Owner 缺失不得升级。→ `risk-mgmt/domain/coordination.md`
5. **重大变更后必须重新识别风险**；连续 2 次延期/风险失控停止 AI 自动调整，推送人工决策。→ `risk-mgmt/domain/coordination.md`

## 3. 标准化输出结构

- 台账类：`raid_ops.py add`/`update`/`close` → `台账/12_风险问题台账.csv`（RAID 四维登记册 + 状态流转 + 关闭日期）。
- 扫描类：`raid_ops.py scan`/`scan --json` → 风险分级扫描报告（概率×影响 → P1~P4，排除已关闭，风险分降序）。
- 升级类：P1~P4 问题分级 + 四级升级阶梯（L1~L4）记录，衔接 `change_audit` 变更审计。
> 目录规范详见 `../../shared/references/directory_structure.md`，协作接口详见 `../../shared/references/api_contracts.md`。

## 4. 边界

- 仅由 ProjectMonitorSkill 路由分发加载；实现逻辑一律委派 `risk-mgmt`，本文件不复制 RAID 状态机/概率×影响分级公式；
- P1 高风险必须立即制定应对方案并上报决策；单一 Owner；重大变更后重新识别风险；
- 进度成本风险联动委派 `schedule-cost`（EVM 预警），范围变更风险协同委派 `scope-tracking`（变更生命周期）。

---

**文档版本**：v21.2.0
**最后更新**：2026-09-08（瘦引用改造：风险登记册初始化/RAID 四维/风险巡检分级/应对策略/问题升级的实现逻辑迁至独立可部署技能 `risk-mgmt`（raid_ops.py v1.0.0 / 标准 raid_standard.md v1.0.0，内化自 dev-project-mgmt raid_manager.py + MCP risk_scan）；本文件仅保留 role-governance 路由触发与风险治理边界策略，消除实现重复。此前 v21.0.0：由 project-monitor-skill v2.7.0 拆分）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
