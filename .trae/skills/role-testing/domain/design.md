---
name: "test-design-skill"
description: "Test case design skill for creating standardized test cases with risk-based layering, IEEE 830 traceability (RTM), design methods per ISO/IEC/IEEE 29119-4 (equivalence partitioning, boundary value, decision table, state transition), and case review. Invoke after test plan approval to design test cases."
---

# TestDesignSkill 测试用例设计技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能版本**：v21.0.0
- **定位**：将测试方案转化为标准化测试用例集，维护测试追溯矩阵（RTM）。
- **调用主体**：DevProjectTeamSkill（测试工程师子角色）
- **触发时机**：测试方案评审通过后、环境准备前，设计测试用例。
- **依赖工具**：ProjectMonitorSkill（质量缺陷台账）、test-strategy-skill（风险/方法输入）、test-planning-skill（方案输入）
- **参考标准**：ISO/IEC/IEEE 29119-4（测试设计技术）、ISTQB CTFL（测试设计技术）
- **核心约束**：仅测试工程师角色激活时加载；用例设计必须在方案评审后完成；核心需求（P0/P1）必须 100% 覆盖；禁止编写业务架构、开发代码、需求文档。

## 2. 统一入参标准

- `design_cases`：设计测试用例，前置：方案已评审
- `test_type`：functional / sit / api_automation / non_functional / security / all；`user_confirm`：无/同意/拒绝/查错

## 3. 测试用例设计环节

**action = design_cases**

### 3.1 Definition of Ready
- 测试方案已评审通过
- 需求基线/架构设计文档（接口定义、数据模型）、RTM 已创建

### 3.2 输出
`测试资产/测试用例集.csv`（按 7 类拆分）与 RTM（`测试资产/需求追溯矩阵.csv`）更新。用例标准字段（13 项）、设计方法（8 种）、方法选择矩阵、风险驱动用例分层、用例评审检查清单详见 `test-design-skill__resources/test_design_details.md`。

### 3.3 Definition of Done
- 测试用例已编写完成（覆盖所有计划测试类型）；RTM 已更新（需求→用例映射完整）
- 用例评审已通过（组内+需求方）；核心需求（P0/P1）100% 覆盖
- 用例编号全局唯一，支持版本管理

### 3.4 规则
1. 用例设计后组织评审（组内+需求方），核心需求 100% 覆盖
2. 每个用例独立可执行，步骤清晰，预期结果可验证
3. 用例编号全局唯一；用例变更须记录并同步更新 RTM
4. 参照风险评估结果，高风险模块增加用例密度

## 4. 标准化输出结构

| 输出类型 | 文档名称 | 格式 | 所属环节 |
|---------|---------|:---:|---------|
| 用例类 | 测试资产/测试用例集.csv | CSV | 用例设计 |

> 目录规范见 `../../shared/references/directory_structure.md`
> 协作接口见 `../../shared/references/api_contracts.md`
> 版本规则见 `../../shared/references/common_standards.md`；当前版本：v21.0.0。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）