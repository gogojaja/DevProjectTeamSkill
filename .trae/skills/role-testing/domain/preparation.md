---
name: "test-preparation-skill"
description: "Test environment preparation skill for deploying environments, preparing test data, configuring third-party mocks, CI pipelines, environment configuration management, and smoke validation. Aligned with ISTQB test implementation process. Invoke after test case review to prepare test environments and data before execution."
---

# TestPreparationSkill 测试环境准备技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能版本**：v21.0.0
- **定位**：测试域环境准备角色，部署测试环境、准备数据、配置依赖与工具，确保执行前环境就绪。
- **调用主体**：DevProjectTeamSkill（测试工程师子角色）
- **触发时机**：用例设计完成后、测试执行前，准备测试环境与数据。
- **依赖工具**：ProjectMonitorSkill（质量缺陷台账）、test-design-skill（用例输入）
- **参考标准**：ISTQB CTFL（测试实现过程）、ISO/IEC/IEEE 29119-2（测试环境设计）
- **核心约束**：仅测试工程师角色激活时加载；冒烟测试不通过不得进入正式执行；测试环境须与生产隔离；禁止编写业务架构、开发代码、需求文档。

## 2. 统一入参标准

- `prepare_env`：准备测试环境与数据，前置：用例已评审
- `test_type`：functional / sit / api_automation / non_functional / security / all；`user_confirm`：无/同意/拒绝/查错

## 3. 测试依赖准备环节

**action = prepare_env**

### 3.1 Definition of Ready
- 测试用例已评审通过
- 架构设计文档（环境拓扑、部署方案）
- 待测版本交付物

### 3.2 准备内容
七项准备（测试环境/测试数据/第三方依赖/工具部署/CI流水线/环境配置管理/冒烟验证）+ 环境管理规范（隔离/版本/配置/快照/监控），详见 `.//test_preparation_details.md`。

### 3.3 Definition of Done
- 测试环境已部署并验证可用；测试数据覆盖正常/边界/异常三类
- 第三方依赖/Mock、测试工具已配置验证；CI 流水线已配置（如有接口自动化）
- 冒烟测试已通过

### 3.4 规则
1. 测试环境尽量接近生产配置，须与生产隔离
2. 数据涉及敏感信息按脱敏规则处理
3. 环境就绪后执行冒烟测试；冒烟不通过则退回开发，不进入正式执行

## 4. 标准化输出结构

| 输出类型 | 文档名称 | 格式 | 所属环节 |
|---------|---------|:---:|---------|
| 环境准备类 | 《环境就绪检查清单》 + 《冒烟测试结果》 | Markdown | 环境准备 |

> 目录规范见 `../../shared/references/directory_structure.md`
> 协作接口见 `../../shared/references/api_contracts.md`
> 版本规则见 `../../shared/references/common_standards.md`；当前版本：v21.0.0。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）