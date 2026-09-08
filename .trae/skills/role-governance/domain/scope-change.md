---
name: "project-scope-change-skill"
description: "Project scope & change management ROUTING sub-skill for role-governance. Delegates the implementation of scope baseline / scope gate / health score / change lifecycle (CCB) / baseline freeze & diff to the standalone deployable skill `scope-tracking` (single source of truth). This file retains only governance routing (change_audit / scope_gate) and scope policy boundaries. Invoke when checking scope compliance, auditing changes, or handling scope changes."
---

# ProjectScopeChangeSkill 项目范围与变更管理（治理路由 · 瘦引用）

> 版权声明详见 `../../shared/references/COPYRIGHT.md`
> **权威实现已迁出（单一信源）**：范围基准 / 门禁 / 健康分 / 变更生命周期 / 基线冻结比对的**实现逻辑**统一收敛到独立可部署技能 **`scope-tracking`**（工具 `tools/scope_tracker.py` v1.2.0，标准 `references/traceability_standard.md` v1.2.0）。本文件仅保留 role-governance 的**路由触发**与**范围治理边界策略**，不复制实现细节（DRY / 铁律 #1 单源）。

## 1. 触发规则（治理路由 → 委派 scope-tracking）

| action | 作用 | 委派明细（scope-tracking） | 主命令 |
|--------|------|---------------------------|--------|
| `scope_gate` | 范围门禁 + 覆盖度 + 蔓延/缩水 + 健康分 + 变更合规 | `scope-tracking/domain/scope-gate.md` | `scope_tracker.py gate` |
| `change_audit` | 范围/架构/核心文件变更审计（五维影响 + 生命周期） | `scope-tracking/domain/change-control.md` | `scope_tracker.py change` / `change-decide` |
| （基准/比对） | 范围基准冻结、真实蔓延/缩水比对、需求易变性 KPI | `scope-tracking/domain/baseline-diff.md` | `scope_tracker.py baseline` / `report` |
| （范围基准） | RTM schema / MoSCoW / SCOPE_STATUS / 范围外登记 | `scope-tracking/domain/scope-baseline.md` | `scope_tracker.py init` |

- **调用主体**：ProjectMonitorSkill（薄路由壳按 action 分发）；范围门禁校验、产出物条目化比对、范围跟踪检查为 `check_gate`/`stage_review` 协同子步骤。
- **参考标准**：`references/traceability_standard.md` v1.2.0（范围跟踪与追溯一致性标准）。
- **依赖工具**：`tools/scope_tracker.py` v1.2.0（内部复用 `tools/check_traceability.py` 三方一致性校验）。

## 2. 范围治理边界策略（保留 · 实现委派）

以下为 role-governance 的**范围治理策略**；判定与实现逻辑见 `scope-tracking`（不在此复制）：

1. **范围基准权威**：范围合规以固化需求基线（SRS+RTM）为唯一比对标准；已实现内容与基准不符一律以基准为准、偏差记缺陷返工；**禁止以已实现内容逆向修正范围基准**。→ `scope-tracking/domain/scope-baseline.md`
2. **超范围无审批禁止流转**：gold-plating / 孤儿新增能力未经审批由门禁拦截（严重→驳回）。→ `scope-tracking/domain/scope-gate.md`
3. **重大变更强制 `user_confirm=同意`**；核心架构文件变更自动转发安全审计。→ `scope-tracking/domain/change-control.md`
4. **同一需求连续 3 次无审批变更 → 触发范围冻结预警**（收敛到 `baseline freeze` + 强制审批）。→ `scope-tracking/domain/baseline-diff.md`
5. **范围外不删除**：被否决/延期/明确范围外需求以 `SCOPE_STATUS ∈ {Rejected, Deferred, Out-of-Scope}` 标记保留在 RTM。→ `scope-tracking/domain/scope-baseline.md`

## 3. 输出规范

- 门禁类：`scope_tracker.py gate` → 范围健康分卡 + 变更合规 + 门禁结论，写 `台账/07_范围跟踪台账.csv`。
- 变更类：`scope_tracker.py change` / `change-decide` → `台账/06_范围变更台账.csv`（《变更影响评估表》五维）；批准 `--writeback` 回写 RTM 基线版本 + CHANGE_REFS。
- 基线类：`scope_tracker.py baseline freeze/diff` → `台账/范围基准快照.csv` + 真实蔓延/缩水比对。
> 目录规范详见 `../../shared/references/directory_structure.md`，协作接口详见 `../../shared/references/api_contracts.md` §1.2。

---

**文档版本**：v21.2.0
**最后更新**：2026-09-08（瘦引用改造：范围基准/门禁/健康分/变更生命周期/基线比对的实现逻辑迁至独立可部署技能 `scope-tracking`（scope_tracker.py v1.2.0 / 标准 v1.2.0）；本文件仅保留 role-governance 路由触发与范围治理边界策略，消除实现重复。此前 v21.1.1：审计整改 gate 快照留痕门禁结论/健康分阈值/fail-closed/蔓延补 MOD·TC 孤儿）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
