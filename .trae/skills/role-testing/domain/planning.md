---
name: "test-planning-skill"
description: "Test planning skill for writing test plans based on approved test strategy, defining test scope, entry/exit criteria, resource allocation, environment and data requirements, CI/CD integration, schedule, risks, metrics, and deliverables. Aligned with ISTQB and ISO/IEC/IEEE 29119. Invoke after test strategy is approved to write the test plan."
---

# TestPlanningSkill 测试方案编写技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能版本**：v21.0.0
- **定位**：将已评审测试策略转化为可执行《测试方案》，明确范围、标准、资源、排期与交付物。
- **调用主体**：DevProjectTeamSkill（测试工程师子角色）
- **触发时机**：测试策略分析完成后、用例设计前，编写测试方案。
- **依赖工具**：ProjectMonitorSkill（阶段评审、变更审计）、test-strategy-skill（策略输入）、test-design-skill（下游协作）
- **参考标准**：ISTQB CTFL/CTAL（测试计划过程）、ISO/IEC/IEEE 29119-2（测试过程模型）
- **核心约束**：仅测试工程师角色激活时加载；方案必须基于已评审策略编写；方案评审通过前禁止进入用例设计；禁止编写业务架构、开发代码、需求文档。

## 2. 统一入参标准

- `write_plan`：编写测试方案，前置：策略分析已评审
- `test_type`：functional / sit / api_automation / non_functional / security / all；`user_confirm`：无/同意/拒绝/查错

## 3. 测试方案编写环节

**action = write_plan**

### 3.1 Definition of Ready
- 测试策略分析已完成并评审通过
- 需求基线/架构设计文档（已固化）、项目进度基准与里程碑

### 3.2 输出
《测试方案》（14 章 + 测试数据管理策略），章节明细见 `test-planning-skill__resources/test_planning_details.md` §一，数据管理策略见 §二。

### 3.3 Definition of Done
- 《测试方案》已输出（含 14 章节），进入/退出标准已明确
- 测试数据管理策略、CI/CD 集成方案（如有接口自动化）已制定
- 已经项目经理/架构师评审通过

### 3.4 规则
1. 方案基于已评审策略编写，经项目经理/架构师评审通过后方可执行
2. 测试范围变更走 ProjectMonitorSkill `change_audit`
3. 方案必须明确进入/退出标准，作为后续门禁校验依据

## 4. 标准化输出结构

| 输出类型 | 文档名称 | 格式 | 所属环节 |
|---------|---------|:---:|---------|
| 方案类 | 《测试方案》 | Markdown/Word | 方案编写 |

> 目录规范见 `../../shared/references/directory_structure.md`
> 协作接口见 `../../shared/references/api_contracts.md`
> 版本规则见 `../../shared/references/common_standards.md`；当前版本：v21.0.0。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）