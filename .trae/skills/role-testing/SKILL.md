---
name: "role-testing"
description: "测试管理角色包：可测性分析与风险测试策略、测试计划、用例设计（等价类/边界/决策表/状态迁移）、环境数据准备、执行与缺陷管理、总结与门禁退出。触发词：测试策略、测试计划、用例设计、测试环境、测试数据、执行测试、缺陷、测试总结。Load when the user plans test strategy, writes the test plan, designs cases, prepares env/data, executes tests, or writes the summary."
---

# role-testing 测试管理角色包

> 版权：`../shared/references/COPYRIGHT.md`　Token：`../shared/references/token_standard.md`　总控：`../shared/governance.md`

## 1. 元数据

- **技能版本**：v21.0.0　**发布日期**：2026-08-04
- **变更记录**：v21.0.0 由 test-management-skill + 6 子技能重组为角色包
- **参考标准**：ISTQB · ISO/IEC/IEEE 29119 · ISO/IEC/IEEE 29119-4 用例设计

## 2. 触发规则

用户表达「测试策略/测试计划/用例设计/环境准备/执行测试/缺陷/测试总结/测试报告」时加载本包。先 Read 路由表，命中后只读对应 `domain/*.md`。

## 3. 流程（路由到 domain/）

| 环节 | action | 明细 |
|------|--------|------|
| 策略分析 | analyze_testability / risk | `domain/strategy.md`（RBT/方法/指标） |
| 计划编写 | write_plan | `domain/planning.md`（入口/出口/资源/环境/CI） |
| 用例设计 | design_cases | `domain/design.md`（等价类/边界/决策表/状态迁移/RTM） |
| 环境数据 | prepare_env | `domain/preparation.md`（环境/数据/Mock/配置/冒烟） |
| 执行缺陷 | execute_test / manage_defect | `domain/execution.md`（风险序/探索性/缺陷生命周期） |
| 总结门禁 | write_report / stage_review | `domain/summary.md`（对接总控） |

## 4. 测试铁律

风险驱动执行排序；缺陷管理 New→Closed 生命周期；用例须 IEEE 830 RTM 追溯；DoD 与报告按 token_standard §3 输出 CSV。

## 5. 输出规范与边界

- 用例 / 缺陷 / 报告按 token_standard §3 输出 CSV；
- 阶段评审退出门禁经 `../shared/governance.md`；
- 边界：仅测试域；需求链路回溯到 role-requirements-analysis。

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）