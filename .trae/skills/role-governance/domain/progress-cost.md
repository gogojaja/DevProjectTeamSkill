---
name: "project-progress-cost-skill"
description: "Project schedule and cost management skill covering baseline setup, milestone updates, EVM earned value analysis, schedule/cost risk warnings, and periodic reviews. Invoke when updating milestones, tracking progress, analyzing EVM indicators, or reviewing schedule/cost."
---

# ProjectProgressCostSkill 项目进度与成本管理技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `update_milestone` | 更新里程碑、工时、成本（含 EVM 分析） | 阶段验收通过后 | 阶段验收通过 |

- **调用主体**：ProjectMonitorSkill（薄路由壳按 action 分发）；前置里程碑门禁校验为 `check_gate` 协同子步骤。
- **参考标准**：PMBOK 7th（进度/成本管理）· 挣值管理（EVM）· ISO 21500
- **依赖工具**：project-governance-skill（基线固化协同）、project-risk-skill（风险预警协同）

## 2. 流程

### 环节 1：基准建立（Baseline Setup）
进度基准（阶段划分/里程碑/任务拆解/工期）、成本基准（工时预估/成本阈值/超支标准）写入 `台账/03_进度基准.csv`、`台账/04_成本基准.csv`。
**DoD**：进度基准写入完成 · 成本基准写入完成。
**规则**：基准在项目初始化时建立；任务分解至可跟踪粒度。

### 环节 2：里程碑与成本更新（update_milestone）
**DoR**：阶段验收通过 · 工时/成本数据可记录。
**执行内容**：里程碑状态/完成率更新（`台账/09_进度跟踪台账.csv`）、实际工时/成本/资源投入记录（`台账/10_成本消耗台账.csv`）、EVM 指标计算（PV/EV/AC/SPI/CPI/SV/CV）。
**DoD**：里程碑状态已更新 · 工时/成本已记录 · EVM 指标已计算 · 异常已触发预警。
**规则**：验收通过后立即更新；任务滞后/成本超阈值自动生成预警报告与调整方案。

### 环节 3：门禁校验协同（check_gate 进度协同）
前置里程碑校验（未完成禁止跳转）、进度/成本风险预警。
**DoD**：前置里程碑校验完成 · 风险预警已触发。
**规则**：前置里程碑未完成禁止跳转下一阶段。

### 环节 4：周期复盘（Periodic Review）
阶段/25-100 轮/项目三级复盘，读取全量台账输出进度/成本复盘报告，EVM 偏差分析与调整方案。
**DoD**：复盘报告完成 · 偏差分析与调整方案输出。
**规则**：连续 2 次延期/超支 → 停止 AI 自动调整计划，推送人工决策。

## 3. 输出规范

1. **台账类**：「进度跟踪台账」「成本消耗台账」更新；
2. **预警类**：进度滞后/成本超支预警报告、调整方案；
3. **复盘类**：进度/成本复盘报告（含 EVM 指标）。
> 目录规范详见 `../../shared/references/directory_structure.md`，协作接口详见 `../../shared/references/api_contracts.md`

## 4. 边界

- 仅由 ProjectMonitorSkill 路由分发加载；
- 前置里程碑未完成禁止跳转；
- 连续 2 次延期/超支停止 AI 自动调整，推送人工决策。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）