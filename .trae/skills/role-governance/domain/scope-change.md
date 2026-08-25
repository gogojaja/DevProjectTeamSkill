---
name: "project-scope-change-skill"
description: "Project scope and change management skill covering scope baseline (SRS+RTM+WBS), scope gate validation, deliverable itemized comparison, scope tracking, coverage metrics & scope creep/shrink detection, change audit with five-dimensional impact assessment, and change registration. Invoke when checking scope compliance, auditing changes, or handling scope changes."
---

# ProjectScopeChangeSkill 项目范围与变更管理技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `change_audit` | 范围/架构/核心文件变更审计（五维影响评估） | 变更、范围调整 | 变更已提出 |
| `scope_gate` | 范围门禁 + 覆盖度 + 蔓延/缩水检测 | 阶段流转前 | 追溯矩阵已建 |

- **调用主体**：ProjectMonitorSkill（薄路由壳按 action 分发）；范围门禁校验、产出物条目化比对、范围跟踪检查为 `check_gate`/`stage_review` 协同子步骤，由 project-quality-gate-skill 门禁流程触发本技能。
- **参考标准**：PMBOK 7th（范围管理）· ITIL v4（变更使能）· ISO 21500 · IEEE 29148
- **依赖工具**：`tools/scope_tracker.py`（范围跟踪主工具，内含 `check_traceability.py` 一致性校验）· `tools/check_traceability.py`（三方一致性）
- **标准文档**：`references/traceability_standard.md` v1.1.1（范围跟踪与追溯一致性标准）

## 2. 流程

### 环节 0：范围基准权威（强制）
- **范围基准 = 固化版需求基线**（SRS + 追溯矩阵 RTM）派生；「范围合规」以需求基线为唯一比对标准；
- **WBS 分解**：`REQ-<nnn>` → `AE-<nnn>`（架构组件）→ `MOD-<nnn>`（代码模块）即可执行 WBS 映射（RTM 的 `REQ→AE→MOD`）；大型项目可另附 WBS 词典；
- **范围外登记**：被否决/延期/明确范围外的需求**保留在 RTM 中以 `SCOPE_STATUS` ∈ {Rejected, Deferred, Out-of-Scope} 标记**，不物理删除（防范围蔓延靠重新争论）；
- 已实现内容与范围基准不符（该做未做/多做超范围/行为不符）→ 一律以范围基准（需求基线）为准，偏差记为缺陷返工，**禁止以已实现内容逆向修正范围基准/需求基线**；
- 范围基准调整仅允许经合法变更审批（来源限范围调整/接口变化/合规新规/新诉求/缺陷澄清），来源为「已实现内容」驳回。

### 环节 1：范围门禁校验（Scope Gate）— 自动化
**执行**：`python3 tools/scope_tracker.py gate`（内部调用 `check_traceability.py` 做三方一致性，再做覆盖度/蔓延/缩水检测，写 `台账/07_范围跟踪台账.csv` 快照）。
**产出**：范围健康分卡（覆盖度 %、状态分布、优先级分布、孤儿率）+ 范围跟踪比对表（缩水/蔓延/内容变更判定）+ 门禁结论（通过/警告/驳回）。
**DoD**：`scope_tracker.py gate` 通过 · 一致性违规 ≤ 容忍度 · 无严重缩水 · 结果写入 `07_范围跟踪台账.csv`。
**规则**：流转前必须范围核查；超范围内容（gold-plating / 孤儿新增能力）无审批拦截；严重（缩水）/主要（蔓延）缺陷记录并限期整改。

### 环节 2：变更审计（change_audit）— 自动化登记
**DoR**：变更已提出 · 影响范围可评估。
**执行**：`python3 tools/scope_tracker.py change --req <REQ> --title <标题> --type <类型> --impact-* <五维> --severity <严重度> --approver <审批人> --baseline-from <v> --baseline-to <v>`，记录追加 `台账/06_范围变更台账.csv`（CR-<nnn>）。
**基线版本化**：审批通过的变更**升级范围基准版本**（`BASELINE_VER` 从 v1.0.0 → v1.0.1…），同步更新受影响 REQ 行的 `BASELINE_VER` 与 `CHANGE_REFS`，保持 RTM 连续追溯（禁止事后突击补表）。
**DoD**：评估表完成 · 五维风险已评估 · 重大变更已审批 · 变更台账已追加 · 基准版本已升级。
**规则**：重大变更强制 `user_confirm=同意`；核心架构文件变更自动转发安全审计；同一需求连续 3 次无审批变更触发范围冻结预警。

## 3. 输出规范

1. **门禁类**：`scope_tracker.py gate` 范围健康分卡 + 范围跟踪比对表 → `台账/07_范围跟踪台账.csv`；
2. **变更类**：`scope_tracker.py change` 登记 → `台账/06_范围变更台账.csv`（《变更影响评估表》五维）。
> 目录规范详见 `../../shared/references/directory_structure.md`，协作接口详见 `../../shared/references/api_contracts.md`

## 4. 边界

- 仅由 ProjectMonitorSkill 路由分发加载；
- 超范围内容无审批禁止流转；
- 重大变更强制 `user_confirm=同意`；
- 同一需求连续 3 次无审批变更 → 冻结范围；
- 范围跟踪主工具为 `tools/scope_tracker.py`，三方一致性由其内部复用 `check_traceability.py`。

---

**文档版本**：v21.1.1
**最后更新**：2026-08-25（审计整改：gate 快照留痕门禁结论/健康分阈值/fail-closed/蔓延补 MOD·TC 孤儿，见 scope_tracker.py v1.1.1；标准引用升 v1.1.1）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
