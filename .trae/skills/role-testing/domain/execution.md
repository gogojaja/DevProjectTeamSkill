---
name: "test-execution-skill"
description: "Test execution and defect management skill covering risk-driven execution ordering, exploratory testing, and defect lifecycle management (New to Closed). Invoke after environment preparation to execute tests, run exploratory testing, manage defects, and track defect metrics."
---

# TestExecutionSkill 测试执行与缺陷管理技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能版本**：v21.0.0
- **定位**：测试域执行角色，负责风险驱动测试执行、探索性测试与缺陷全生命周期管理。
- **调用主体**：DevProjectTeamSkill（测试工程师子角色）
- **触发时机**：测试环境就绪、待测版本交付后执行测试，测试中发现缺陷时管理缺陷。
- **依赖工具**：ProjectMonitorSkill（质量缺陷台账）、test-preparation-skill（环境输入）、test-summary-skill（下游协作）
- **参考标准**：ISTQB CTFL（测试执行与缺陷管理）、ISO/IEC/IEEE 29119-2（测试执行过程）
- **核心约束**：仅测试工程师角色激活时加载；所有缺陷必须录入台账；严重/主要缺陷修复后必须回归验证；禁止编写业务架构、开发代码、需求文档。

## 2. 统一入参标准

- `execute_test`：执行测试并记录结果，前置：环境就绪+冒烟通过
- `explore_test`：探索性测试（补充脚本测试），前置：待测版本可用
- `manage_defect`：缺陷全生命周期管理，前置：测试执行中
- `test_type`：functional / sit / api_automation / non_functional / security / all
- `user_confirm`：无/同意/拒绝/查错

## 3. 测试执行与缺陷管理环节

**action = execute_test / explore_test / manage_defect**

### 3.1 Definition of Ready
- 测试环境就绪、冒烟测试通过；待测版本已交付
- 测试用例已评审通过；测试数据已准备

### 3.2 执行内容
风险驱动执行顺序（冒烟→功能→SIT→接口自动化→非功能→安全→探索→回归）+ 执行记录规范见 `test-execution-skill__resources/test_execution_details.md` §一；探索性测试原则/章程/适用场景见 §二；缺陷生命周期/报告字段/严重程度 vs 优先级/度量指标见 §三。

### 3.3 Definition of Done
- 所有计划用例已执行（含跳过/不适用，执行率100%）；执行记录完整可追溯
- 所有缺陷已录入 ProjectMonitorSkill 质量缺陷台账；严重/主要缺陷已修复并回归验证
- 探索性测试已完成（如有计划）

### 3.4 规则
1. 所有缺陷必须录入 ProjectMonitorSkill 质量缺陷台账
2. 严重/主要缺陷修复后必须回归验证；同一缺陷重开 2 次升级人工介入（刹车机制）
3. 执行进度每日更新，偏差超过 20% 触发预警
4. 回归范围 = 缺陷影响的用例 + 核心功能 P0/P1 用例；探索性测试问题补充为正式用例入回归库

## 4. 标准化输出结构

| 输出类型 | 文档名称 | 格式 | 所属环节 |
|---------|---------|:---:|---------|
| 执行记录类 | 测试资产/测试执行结果.csv + 测试资产/缺陷清单.csv | CSV | 执行与缺陷 |
| 执行记录类 | 《探索性测试记录》 | Markdown | 执行与缺陷 |

> 目录规范见 `../../shared/references/directory_structure.md`
> 协作接口见 `../../shared/references/api_contracts.md`
> 版本规则见 `../../shared/references/common_standards.md`；当前版本：v21.0.0。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）