---
name: "development-review-skill"
description: "Code review skill covering code walkthrough (Fagan Inspection) and PR review with a 12-item checklist, review workflow, roles, and review reports. Invoke when walking through code, reviewing pull requests, or doing peer code review."
---

# DevelopmentReviewSkill 代码走查与评审技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **技能唯一标识**：DevelopmentReviewSkill
- **调用主体**：DevProjectTeamSkill（开发工程师子角色 + 审查者子角色）
- **触发时机**：代码开发完成后进行代码走查、提交 PR 后执行代码审查、代码合并前评审把关
- **依赖工具**：ProjectMonitorSkill（门禁校验）、development-coding-skill（上游编码环节）
- **参考标准**：ISO/IEC/IEEE 12207（验证过程）· Fagan Inspection · Google Code Review · Clean Code
- **核心约束**：仅在开发工程师/审查者角色激活时加载执行逻辑；PR 必须通过自动检查与至少 1 人审查才可合并；12 项审查清单逐项核对；走查会议只记录问题不现场改码。

### 走查与审查原则

| 原则 | 要求 |
|------|------|
| 强制走查 | 代码合并前必须走查，禁止跳过 |
| 清单审查 | PR 审查按 12 项清单逐项核对 |
| 最小审查人 | 至少 1 人审查通过才可合并 |
| 问题分级 | 阻断/严重/主要/次要分级管理 |
| 客观记录 | 走查会议只记录问题，不讨论方案 |
| 及时关闭 | 阻断级问题必须修复后才能合并 |
| **需求基线权威** | 实现与需求基线不符 → 以需求基线为准，记为缺陷返工实现；**禁止以已实现内容修正需求基线** |

## 2. 统一入参标准

```json
{
  "action": "操作指令，可选值：walkthrough_code / review_pr",
  "dev_phase": "当前开发阶段，可选：review",
  "content": "对应操作内容：走查代码/PR 审查对象",
  "module": "当前开发模块",
  "user_confirm": "用户指令：无/同意/拒绝/查错"
}
```

### action 指令清单

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `walkthrough_code` | 代码走查（Fagan Inspection 流程、问题分级） | 代码开发完成后 | 代码已开发 |
| `review_pr` | PR 审查（12 项清单、审查流程、评审报告） | PR 提交后 | CI 通过 |

## 3. 流程

### 环节 1：代码走查（action = walkthrough_code）

- **DoR**：代码开发完成 ✅ 编码规范已定稿 ✅ 走查范围与角色已确定 ✅
- **执行内容**：走查流程（计划→准备→会议→修复→复检）、走查检查维度（正确性/清晰度/可维护性/安全性/性能/健壮性/规范一致性）、问题分级处理，详见 `.//development_review_details.md` §4。
- **DoD**：走查问题预清单完成 ✅ 走查记录表完成 ✅ 问题全部修复或登记遗留 ✅ 走查结论通过 ✅
- **规则**：走查会议只记录问题不现场改码；阻断级问题立即修复禁止合并；严重级 24 小时内修复；问题处理状态全部闭环。

### 环节 2：代码审查（action = review_pr）

- **DoR**：PR 已提交 ✅ CI 自动检查通过 ✅ 质量门禁已执行 ✅
- **执行内容**：PR 审查流程（提交→自动检查→审查→修复→合并）、12 项审查清单逐项核对（正确性/安全性/架构/性能/可测试性/规范一致性等）、审查角色与门槛、评审报告生成，详见 `.//development_review_details.md` §5。
- **DoD**：12 项清单全部核对 ✅ 审查问题已记录并反馈 ✅ 修复状态确认 ✅ 评审报告生成 ✅ 审查结论（通过/有条件通过/驳回）✅
- **规则**：PR 未过 CI 或门禁禁止人工审查放行；12 项清单逐项核对不可跳过；至少 1 人审查通过才可合并；阻断/严重问题必须修复后重新审查。

## 4. 输出规范

1. **走查类**：走查计划、走查问题预清单、走查记录表、修复记录；
2. **评审类**：代码评审报告（PR 编号/审查者/问题数/修复状态/结论）；
> 目录规范详见 `../../shared/references/directory_structure.md`
> 协作接口详见 `../../shared/references/api_contracts.md`

## 5. 边界

- 仅开发工程师/审查者角色激活时执行；PR 未过 CI 或门禁禁止人工审查放行；12 项清单逐项核对不可跳过；至少 1 人审查通过才可合并；走查会议只记录问题不现场改码；阻断/严重问题必须修复后重新审查。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-02
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
