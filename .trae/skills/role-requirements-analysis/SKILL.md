---
name: "role-requirements-analysis"
description: "需求分析角色包：需求收集、七维度分析、IEEE 830 SRS 编写、需求评审、变更影响分析与双向追溯。触发词：收集需求、分析需求、编写 SRS、需求规格、需求评审、需求变更、需求追溯、需求基线。Load when the user asks to gather, analyze, specify (SRS), review, change, or trace requirements."
---

# role-requirements-analysis 需求分析角色包

> 版权：`../shared/references/COPYRIGHT.md`　Token：`../shared/references/token_standard.md`　总控：`../shared/governance.md`

## 1. 元数据

- **技能版本**：v21.0.0　**发布日期**：2026-08-04
- **变更记录**：v21.0.0 由 requirements-analysis-skill + 4 子技能重组为角色包
- **参考标准**：BABOK v3 · IEEE 830 · MoSCoW

## 2. 触发规则

用户表达「收集需求/分析需求/写 SRS/需求评审/需求变更/需求追溯/初始化需求基线」时加载本包。先 Read 路由表（下方 §3），命中后只读对应 `domain/*.md`。

## 3. 流程（路由到 domain/）

| 环节 | action | 明细 |
|------|--------|------|
| 需求基线 | create_requirements_baseline | `domain/elicitation.md` |
| 需求收集 | gather_requirements | `domain/elicitation.md` |
| 需求分析 | analyze_requirements | `domain/dimension-analysis.md` |
| SRS 编写 | document_requirements | `domain/specification.md` |
| 需求评审 | review_requirements | `domain/lifecycle.md`（对接总控 stage_review） |
| 需求变更 | change_analysis | `domain/lifecycle.md` |
| 追溯更新 | update_traceability | `domain/lifecycle.md` |

## 4. 全局强制刹车规则

1. 收集：同源 3 次矛盾 → 暂停，干系人仲裁；
2. 分析：同需求 2 次矛盾结论 → 高优冲突，干系人确认；
3. 编写：质量校验 ≥3 项 ❌ → 返回分析环节；
4. 评审：第 2 轮仍存严重/主要缺陷 → 停止自动修复，人工介入；
5. 变更：同需求连续 3 次无审批变更 → 冻结基准预警；
6. 追溯：断链率 >20% → 暂停流转，补全追溯。

## 5. 输出规范与边界

- 分析报告 / SRS / 追溯矩阵按 token_standard §3 输出 CSV（禁止 .xlsx）；
- 评审经 `../shared/governance.md`；台账读写经总控；
- 边界：仅需求域；架构/测试等路由到对应角色包。

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）