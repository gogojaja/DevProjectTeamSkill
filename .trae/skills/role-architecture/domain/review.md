---
name: "architecture-review-skill"
description: "Architecture decision and validation skill covering ADR decision records, prototype validation (POC, cross-platform, performance baseline), ATAM architecture review with anti-pattern checks, and baseline finalization. Invoke after architecture design to record decisions, validate prototypes, review, and finalize baseline."
---

# ArchitectureReviewSkill 架构决策评审技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能版本**：v21.0.0　**发布**：2026-08-04
- **定位**：架构决策与质量验证中枢：ADR 决策记录、POC 原型验证、ATAM 评审、反模式检查、七原则终审、架构基线固化、变更分析
- **调用主体**：架构设计师子角色 + architecture-management-skill（薄路由壳）；依赖 ProjectMonitorSkill（阶段评审/门禁/基线/变更审计/质量缺陷台账）
- **参考标准**：ATAM（SEI）· ADR / MADR · 架构反模式目录（ArchMan）

## 2. 触发规则

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `record_decisions` | ADR 编写 + ATAM 权衡分析 | 设计过程中关键技术决策点 | 设计进行中/初稿 |
| `validate_prototype` | POC + 跨平台 + 性能基准 | 设计初稿完成后 | 初稿完成 + ADR 已记 |
| `review_architecture` | ATAM 评估 + 反模式检查 + 七原则终审 | 设计定稿后 | 定稿 + 原型通过 |
| `finalize_baseline` | 架构基线固化（文档+指南+归档） | 评审通过后 | 评审通过 + 门禁放行 |
| `change_analysis` | 架构变更七维度影响评估 | 基线固化后需变更时 | 基线已固化 |

**入参**：`action`（上表）+ `design_phase` + `content`（ADR/评审材料/POC计划/架构方案）+ `user_confirm`（无/同意/拒绝/查错）。

## 3. 流程

> 各环节详细执行内容（MADR 模板/ADR 类型/ATAM 步骤/技术选型矩阵/POC 计划/检查清单/反模式目录/质量属性场景/说明书 12 章/追溯矩阵）详见 `.//architecture_review_details.md`。

### 环节 1：决策记录（record_decisions）
- **内容**：ADR 编写（MADR 格式+编号+类型）；ATAM 权衡分析（六步骤+典型权衡场景）；技术选型决策矩阵（九维加权）；决策评审。
- **DoD**：所有决策均有独立 ADR；权衡报告完成；选型矩阵完成；关键决策已评审。
- **规则**：每决策独立 ADR 不可合并；ADR 状态变更（Superseded）须记录原因与替代方案；ATAM 须覆盖七原则间权衡；ADR 归档后不可删除。

### 环节 2：原型验证（validate_prototype）
- **内容**：POC 方案；关键技术验证（Spike）；跨平台兼容；性能基准；安全验证；七原则验证。
- **DoD**：POC 执行完成；关键风险点已验证；跨平台/性能/安全报告输出；七原则全通过。
- **规则**：POC 不过须调整后重验；性能基准覆盖关键路径；跨平台覆盖全部目标平台；高危漏洞须评审前修复；七原则任一不过不得进入评审。

### 环节 3：架构评审（review_architecture）
- **内容**：ATAM 评估（六步骤）；评审检查清单（15 类）；反模式检查（8 种）；质量属性场景验证；七原则终审；对接 `stage_review`。
- **DoD**：ATAM 报告完成；15 类全检；反模式无未修复严重项；场景验证完成；七原则终审通过；`stage_review` 已执行；缺陷全部闭环（严重/主要 100%）。
- **规则**：15 类不可省略；反模式须记录评估、严重必整改；七原则任一不过评审不通过；评审最多 2 轮整改复核仍存严重/主要缺陷 → 人工介入；缺陷写入质量缺陷台账。

### 环节 4：基线固化（finalize_baseline）
- **内容**：说明书定稿（12 章）；ADR 归档；开发指南；架构资产清单；追溯矩阵；对接 `check_gate` + `stage_close`。
- **DoD**：说明书 12 章完整；ADR 全归档；开发指南输出；资产清单生成；追溯矩阵断链率 ≤20%；门禁通过；基线固化完成。
- **规则**：12 章不可省略；ADR 归档后不可删；断链率 >20% → 门禁驳回；基线后变更必须走 `change_analysis`；开发指南为开发输入。

### 变更分析（change_analysis）
- **触发**：基线固化后架构模式/技术栈/组件/接口契约/数据架构变更。
- **内容**：七维度影响评估（架构模式/组件/接口/数据/安全/性能/七原则）+ 变更流程。
- **规则**：先七维度评估；重大变更经架构委员会评审；更新受影响 ADR（新增或标记 Superseded）；更新追溯矩阵；变更记录写入范围变更台账。

## 4. 输出规范（CSV）

- 决策类：ADR 文档集（MADR）、ATAM 权衡报告、技术选型决策矩阵 CSV
- 原型类：POC 报告、跨平台报告、性能基准报告、安全验证报告、七原则验证结果
- 评审类：ATAM 评估报告、架构评审报告 CSV（15 类检查 + 反模式 + 七原则终审）、`stage_review` 评审报告 `评审报告_<对象>_<版本>_{摘要|缺陷清单|逐原则|范围跟踪|角色权限}.csv`
- 基线类：架构设计说明书（12 章）、开发指南、架构资产清单 CSV、架构追溯矩阵、ADR 归档清单
- 备份：`台账/项目总台账_v<版本号>_backup.csv`

> 目录规范见 `../../shared/references/directory_structure.md`；协作接口见 `../../shared/references/api_contracts.md`。

## 5. 边界

- 仅架构设计师角色激活时执行；禁止编写业务代码、测试用例、需求文档
- 评审不通过、七原则不达标、缺陷未闭环 → 禁止固化基线或流转开发阶段

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）