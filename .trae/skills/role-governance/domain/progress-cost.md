---
name: "project-progress-cost-skill"
description: "Project schedule and cost management ROUTING sub-skill for role-governance. Delegates the implementation of schedule/cost baseline setup, milestone updates, EVM earned value analysis (PV/EV/AC/CPI/SPI/CV/SV/on-time rate), schedule/cost risk warnings, and periodic reviews to the standalone deployable skill `schedule-cost` (single source of truth). This file retains only governance routing (update_milestone / check_gate progress协同) and schedule/cost policy boundaries. Invoke when updating milestones, tracking progress, analyzing EVM indicators, or reviewing schedule/cost."
---

# ProjectProgressCostSkill 项目进度与成本管理（治理路由 · 瘦引用）

> 版权声明详见 `../../shared/references/COPYRIGHT.md`
> **权威实现已迁出（单一信源）**：进度/成本基准建立 / 里程碑更新 / EVM 挣值分析（PV·EV·AC·CPI·SPI·CV·SV·准点率）/ 滞后超支预警 / 周期复盘的**实现逻辑**统一收敛到独立可部署技能 **`schedule-cost`**（工具 `tools/evm_ops.py` v1.0.0，标准 `references/evm_standard.md` v1.0.0，内化自 dev-project-mgmt `evm_calculator.py`）。本文件仅保留 role-governance 的**路由触发**与**进度成本治理边界策略**，不复制实现细节（DRY / 铁律 #1 单源）。

## 1. 触发规则（治理路由 → 委派 schedule-cost）

| action | 作用 | 委派明细（schedule-cost） | 主命令 |
|--------|------|---------------------------|--------|
| `update_milestone` | 里程碑/工时/成本更新 + EVM 挣值分析 | `schedule-cost/domain/milestone-evm.md` | `evm_ops.py update-milestone` / `calc` |
| （进度成本基准） | 进度基准（阶段/里程碑/工期）+ 成本基准（工时/BAC/超支标准） | `schedule-cost/domain/baseline.md` | `evm_ops.py add-milestone` |
| `check_gate`（进度协同） | 前置里程碑校验 + EVM 健康判定作为阶段流转门禁 | `schedule-cost/domain/milestone-evm.md` | `evm_ops.py calc` |
| （周期复盘） | 阶段/轮次/项目三级复盘 + EVM 偏差分析 + 纠偏方案 | `schedule-cost/domain/review.md` | `evm_ops.py calc --json` / `status` |

- **调用主体**：ProjectMonitorSkill（薄路由壳按 action 分发）；前置里程碑门禁校验、EVM 健康判定为 `check_gate`/`stage_review` 协同子步骤。
- **参考标准**：`references/evm_standard.md` v1.0.0（进度成本挣值管理标准）。
- **依赖工具**：`tools/evm_ops.py` v1.0.0（EVM 逻辑单一信源；MCP `evm_analyze` 以 subprocess 委派）。

## 2. 进度成本治理边界策略（保留 · 实现委派）

以下为 role-governance 的**进度成本治理策略**；判定与实现逻辑见 `schedule-cost`（不在此复制）：

1. **基准权威**：进度/成本绩效以固化基准（03/04）为唯一比对标准；**禁止以「实际发生」逆向修正基准**，基准调整须走变更审批（委派 `scope-tracking`）。→ `schedule-cost/domain/baseline.md`
2. **挣值驱动门禁**：阶段流转以 CPI/SPI 双维健康判定为据，严重偏差（<0.9）无纠偏方案不得流转。→ `schedule-cost/domain/milestone-evm.md`
3. **前置里程碑未完成禁止跳转**：`check_gate` 前置里程碑校验拦截越阶流转。→ `schedule-cost/domain/milestone-evm.md`
4. **里程碑 0/100 挣值**：EV 采里程碑完成即计全额计划值、未完成计 0，避免主观百分比挣值。→ `references/evm_standard.md` §5
5. **连续 2 次延期/超支 → 停止 AI 自动调整计划，推送人工决策**（升级至项目经理/PMO）。→ `schedule-cost/domain/review.md`

## 3. 输出规范

- 更新类：`evm_ops.py update-milestone` → `台账/09_进度跟踪台账.csv`（里程碑状态/实际完成日/完成率）。
- 绩效类：`evm_ops.py calc` / `calc --json` → EVM 绩效卡（PV/EV/AC/CPI/SPI/CV/SV/准点率 + 健康判定 + 滞后超支预警）。
- 复盘类：`evm_ops.py status` → 全里程碑状态 + EVM 概览，供阶段/周期复盘。
> 目录规范详见 `../../shared/references/directory_structure.md`，协作接口详见 `../../shared/references/api_contracts.md`。

## 4. 边界

- 仅由 ProjectMonitorSkill 路由分发加载；实现逻辑一律委派 `schedule-cost`，本文件不复制 EVM 公式/健康阈值；
- 前置里程碑未完成禁止跳转；连续 2 次延期/超支停止 AI 自动调整，推送人工决策；
- 进度成本风险联动登记委派 `risk-mgmt`（RAID），范围基准调整委派 `scope-tracking`（变更生命周期）。

---

**文档版本**：v21.2.0
**最后更新**：2026-09-08（瘦引用改造：进度/成本基准/里程碑更新/EVM 挣值分析/滞后超支预警/周期复盘的实现逻辑迁至独立可部署技能 `schedule-cost`（evm_ops.py v1.0.0 / 标准 evm_standard.md v1.0.0，内化自 dev-project-mgmt evm_calculator.py）；本文件仅保留 role-governance 路由触发与进度成本治理边界策略，消除实现重复。此前 v21.0.0：由 project-monitor-skill 拆分）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
