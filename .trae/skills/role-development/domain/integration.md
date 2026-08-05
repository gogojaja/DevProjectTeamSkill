---
name: "development-integration-skill"
description: "System integration and quality closure skill covering integration strategy, integration testing, code quality checks (static analysis/SAST/SCA), quality gates, baseline solidification, and change analysis. Invoke when integrating modules, running system integration tests, checking code quality, or closing development baselines."
---

# DevelopmentIntegrationSkill 系统联调与质量收口

> 版权：`../../shared/references/COPYRIGHT.md`

## 1. 元数据

- **技能版本**：v21.0.0　**发布日期**：2026-08-04（由 development-integration-skill v1.0.0 重组瘦身）
- **参考标准**：ISO/IEC/IEEE 12207 集成与验证 · ISTQB 集成测试 · SonarQube Quality Gates · OWASP ASVS
- **核心约束**：联调用例先行；阻断级缺陷 0 遗留才可固化基线；质量门禁不通过禁止固化基线；变更必须走影响评估与 `change_audit`。

## 2. action

| action | 作用 | 前置 |
|--------|------|------|
| `integrate_system` | 系统联调（策略/用例/缺陷） | 单测通过 |
| `check_quality` | 质量检查（静态分析/SAST/SCA/门禁） | 联调通过 |
| `solidify_baseline` | 开发基线固化 | 门禁通过 |
| `analyze_change` | 开发变更分析 | 变更已提出 |

## 3. 原则

联调用例先行 · 自底向上（单模块→跨服务→端到端）· 阻断清零 · 门禁把关 · 追溯完整 · 变更受控（`change_audit`）。

## 4. 流程（明细：`./development-integration-skill__resources/development_integration_details.md`）

### 环节 1：系统联调（integrate_system）
- **DoR**：单测通过 · 环境就绪 · 接口清单与数据已备
- **执行**：联调策略（L1-L5 自底向上）→ 准备（环境/接口/数据/桩/计划）→ 用例（契约/链路/异常/并发/一致性）→ 执行与缺陷管理
- **DoD**：用例全执行 · 阻断 0 · 契约一致性确认 · 关键链路 100% 通过 · 联调报告生成
- **规则**：自底向上不可跳过；缺陷定界→责任方修复→更新单测→回归受影响链路。

### 环节 2：代码质量检查（check_quality）
- **DoR**：联调通过 · 质量工具已配置 · 基线代码可用
- **执行**：静态分析 · SAST · SCA · 复杂度 · 技术债务 · 门禁校验
- **DoD**：阻断/严重 0 · SAST 高危 0 · SCA 高危 0 · 覆盖率 ≥80% · 门禁通过
- **规则**：门禁不通过禁止固化基线；阻断/严重修复后复检；指标入追溯矩阵。

### 环节 3：开发基线固化（solidify_baseline）
- **DoR**：门禁通过 · 联调报告完成 · 追溯矩阵可建
- **执行**：开发总结报告（8 章）· 追溯矩阵 · 对接 `stage_review`/`check_gate`/`stage_close`
- **DoD**：总结报告完成 · 追溯矩阵写入台账 · 基线固化（备份+版本+清单）
- **规则**：固化前门禁必须通过；追溯与需求/代码/测试一一对应。

### 环节 4：开发变更分析（analyze_change）
- **执行**：影响评估（需求/架构/模块/接口/测试/安全/质量）→ `change_audit`→审批→改码→改测→重检质量→更新追溯→重新固化
- **规则**：所有变更走影响评估与 `change_audit`；变更后重跑质量与门禁；变更记录同步总结报告。

## 5. 输出物

联调计划/用例/报告/缺陷清单 · 静态分析/SAST/SCA/门禁报告 · 开发总结报告（8 章）/追溯矩阵（`台账/16_开发追溯.csv`）/基线清单 · 影响评估报告/变更记录。目录规范见 `../../shared/references/directory_structure.md`。

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）