---
name: "test-strategy-skill"
description: "Test strategy analysis skill covering requirements testability analysis, risk-based testing (RBT), test method selection, test type definition (functional/SIT/API automation/non-functional/security), and test metrics. Invoke when entering testing phase to analyze testability, assess risk, select methods, and define test strategy before planning."
---

# TestStrategySkill 测试策略分析技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能版本**：v21.0.0
- **定位**：测试阶段前置策略分析中枢，负责需求可测性分析、风险评估与优先级分配、测试方法选型、测试类型定义，为测试方案编写提供策略输入。
- **调用主体**：DevProjectTeamSkill（测试工程师子角色）
- **触发时机**：需求基线固化后进入测试阶段、需求可测性评估、风险评估与优先级分配、测试方法选型、测试类型选择、测试度量指标体系定义。
- **依赖工具**：ProjectMonitorSkill（阶段评审、基线固化、变更审计）
- **参考标准**：ISTQB CTFL/CTAL（风险驱动测试 RBT）、ISO/IEC/IEEE 29119、ISO/IEC 25010、OWASP Testing Guide v4.2 / Top 10
- **核心约束**：仅测试工程师角色激活时加载；策略分析必须在测试方案编写前完成；禁止编写业务架构、开发代码、需求文档。

## 2. 统一入参标准

- `analyze_strategy`：策略分析（可测性/风险/方法选型），前置：需求基线已固化
- `create_rtm`：创建/更新测试追溯矩阵，前置：需求基线已固化
- `estimate_effort`：测试工时估算，前置：测试策略已确定
- `test_type`：functional / sit / api_automation / non_functional / security / all
- `user_confirm`：无/同意/拒绝/查错

## 3. 测试策略分析流程

> 详细内容（可测性等级表/风险矩阵/风险维度/方法选型矩阵）见 `.//test_strategy_details.md` §一~§三。

### 3.1 需求可测性分析
对每条需求做四级可测性评估（可直接测试/需澄清后测试/间接测试/暂不可测试），输出《需求可测性分析清单》；不可测需求须标注阻塞条件。

### 3.2 风险评估与测试优先级
**RBT 风险驱动测试**：风险值 = 影响程度 × 发生概率（1-16），按极高/高/中/低分配 P0/P1/P2/P3 用例优先级；风险等级须经项目经理/需求方确认后作为测试优先级依据。

### 3.3 测试方法选型
按需求特征与风险结果选择方法组合（等价类/边界值/决策表/场景法/契约测试/负载测试等），方法选型矩阵详见 `.//test_strategy_details.md` §三。

### 3.4 输出
《测试策略分析报告》：可测性分析清单、风险评估矩阵、测试优先级分配表、方法选型矩阵、测试类型选择建议、资源与工时初步估算、关键风险与应对预案。

### 3.5 规则
1. 在需求基线固化后、测试方案编写前进行；所有需求须完成可测性评估
2. 测试策略变更走 ProjectMonitorSkill `change_audit`

## 4. 五大测试类型定义

> 测试类型与测试级别（组件/集成/系统/验收）正交；完整定义见 `.//test_strategy_details.md` §四。

| 测试类型 | 定义 | 设计方法 | 准出条件 |
|---------|------|---------|---------|
| **功能测试** | 验证系统功能行为符合需求 | 等价类+边界值+场景法+决策表+错误推测 | 用例执行率100%，严重/主要缺陷100%闭环 |
| **系统联调（SIT）** | 验证跨系统接口、数据交换、端到端链路 | 接口契约+业务链路场景法+数据一致性校验 | 全部接口链路验证通过 |
| **接口自动化** | 对 API 自动化验证 | 数据驱动+参数化+契约测试 | 核心接口自动化覆盖率>=80% |
| **非功能测试** | 性能/兼容性/可靠性/可用性等 | 负载/压力/兼容性/无障碍等 | 满足需求阈值 |
| **安全测试** | 评估安全性能，发现漏洞风险 | STRIDE 威胁建模+OWASP Top 10 | 无高危/严重漏洞 |

## 5. 测试度量指标体系

> 三类指标完整定义见 `.//test_strategy_details.md` §五；每类选 2-3 个建基线，趋势比绝对值更重要。

- **产品质量**：缺陷密度、缺陷DI值、缺陷逃逸率(<=5%)、需求覆盖率(核心100%)、代码覆盖率
- **过程有效性**：缺陷移除效率(DRE)、重新打开率、平均修复时长(MTTR)、用例执行率、用例通过率
- **项目管理**：进度偏差(>20%预警)、工时偏差、环境可用率、缺陷修复速率、测试资产复用率

> 版本规则见 `../../shared/references/common_standards.md`；当前版本：v21.0.0。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）