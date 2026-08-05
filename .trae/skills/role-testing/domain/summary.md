---
name: "test-summary-skill"
description: "Test summary and review skill for writing test summary reports (10 chapters), performing test phase review via ProjectMonitorSkill stage_review, checking gate exit criteria, and reviewing reports. Aligned with ISTQB test closure and ISO/IEC/IEEE 29119-3. Invoke after test execution to summarize results, review, and finalize test baseline."
---

# TestSummarySkill 测试总结与评审技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能版本**：v21.0.0
- **定位**：测试域总结评审角色，编写测试总结报告、执行阶段评审与门禁校验、固化测试基线。
- **调用主体**：DevProjectTeamSkill（测试工程师子角色）
- **触发时机**：全部测试执行完成后，编写总结报告、阶段评审、基线固化。
- **依赖工具**：ProjectMonitorSkill（门禁校验、阶段评审、基线固化）
- **参考标准**：ISTQB CTFL（测试结束过程）、ISO/IEC/IEEE 29119-3（测试文档模板）
- **核心约束**：仅测试工程师角色激活时加载；门禁未通过禁止流转部署阶段；基线固化后方可归档；禁止编写业务架构、开发代码、需求文档。

## 2. 统一入参标准

- `write_report`：编写测试总结报告，前置：全部测试执行完毕
- `stage_review`：测试阶段评审与门禁校验，前置：报告已定稿
- `test_type`：functional / sit / api_automation / non_functional / security / all；`user_confirm`：无/同意/拒绝/查错

## 3. 测试总结与评审环节

**action = write_report / stage_review**

### 3.1 Definition of Ready
- 全部测试执行完成；所有缺陷已处理（关闭/延期/拒绝）
- 测试度量数据已采集

### 3.2 执行内容
`测试总结报告.csv`：10 章结构见 `.//test_summary_details.md` §一；stage_review 四大维度见 §二；测试门禁准出标准（10 项）见 §三；报告评审检查清单见 §四。

### 3.3 Definition of Done
- `测试总结报告.csv` 已输出（含 10 章节）；度量数据已采集分析
- 门禁校验全部通过；已经项目经理/架构师/需求方评审通过
- 测试基线已固化（ProjectMonitorSkill `stage_close`）；测试资产已归档

### 3.4 规则
1. 报告经项目经理/架构师/需求方评审通过
2. 门禁全部通过后调用 ProjectMonitorSkill `stage_close` 固化测试基线，方可流转部署
3. 测试资产（用例/报告/缺陷/脚本/环境配置）归档保存
4. 遗留缺陷须有明确风险评估与后续处理计划

## 4. 标准化输出结构

| 输出类型 | 文档名称 | 格式 | 所属环节 |
|---------|---------|:---:|---------|
| 总结报告类 | 测试总结报告.csv | CSV | 总结评审 |
| 阶段固化类 | 《门禁校验结果》 + 《基线固化记录》 | Markdown | 总结评审 |

> 目录规范见 `../../shared/references/directory_structure.md`
> 协作接口见 `../../shared/references/api_contracts.md`
> 版本规则见 `../../shared/references/common_standards.md`；当前版本：v21.0.0。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）