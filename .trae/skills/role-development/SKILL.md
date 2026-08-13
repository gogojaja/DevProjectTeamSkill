---
name: "role-development"
description: "开发管理角色包：开发策略与技术栈、分支编码规范、模块编码与安全编码、代码走查与 PR 评审、单元测试、联调与质量收口及基线固化。触发词：开发策略、技术栈、分支规范、编码、代码走查、PR评审、单元测试、联调、质量检查。Load when the user starts development strategy, codes modules, reviews code (PR), runs unit tests, integrates, or closes the quality baseline."
---

# role-development 开发管理角色包

> 版权：`../shared/references/COPYRIGHT.md`　Token：`../shared/references/token_standard.md`　总控：`../shared/governance.md`

## 1. 元数据

- **技能版本**：v21.5.0　**发布日期**：2026-08-13
- **变更记录**：
  - v21.5.0：新增多项目环境隔离最佳实践引用（2026-08-13）——`domain/strategy.md` 引用 `../references/multi_project_isolation.md`（Git/运行时/数据库/Docker 四层隔离）。
  - v21.0.0：由 development-management-skill + 5 子技能重组为角色包
- **参考标准**：ISO/IEC/IEEE 12207 · OWASP ASVS · Trunk-Based/Git Flow

## 2. 触发规则

用户表达「开发策略/技术栈/分支规范/编码/实现功能/走查/PR评审/单测/联调/质量检查/固化基线」时加载本包。先 Read 路由表，命中后只读对应 `domain/*.md`。

## 3. 流程（路由到 domain/）

| 环节 | action | 明细 |
|------|--------|------|
| 策略确认 | analyze_strategy | `domain/strategy.md`（技术栈/分支/WBS/环境） |
| 多项目隔离 | setup_isolation | `../references/multi_project_isolation.md`（Git/运行时/数据库/Docker 四层隔离） |
| 模块编码 | develop_code | `domain/coding.md`（编码规范/安全编码/API/DB/异常） |
| 代码走查 | walkthrough_code | `domain/review.md`（Fagan Inspection） |
| PR 评审 | review_pr | `domain/review.md`（12 项清单） |
| 单元测试 | run_unit_test | `domain/testing.md`（TDD/覆盖率/Mock） |
| 系统联调 | integrate_system | `domain/integration.md` |
| 质量收口 | check_quality | `domain/integration.md`（SAST/SCA/静态分析） |
| 基线固化 | solidify_baseline | `../shared/governance.md` |

## 4. 编码铁律

安全编码遵循 OWASP ASVS；禁止在代码/日志中泄露密钥；实现遵循单线串行；错误处理完整；DoD 输出按 token_standard §3 用 CSV。

## 5. 输出规范与边界

- 编码/质量报告 / 单测覆盖率按 token_standard §3 输出 CSV；
- 质量门禁 / 基线固化经 `../shared/governance.md`；
- 边界：仅开发域；测试主流程路由到 role-testing。

---

**文档版本**：v21.5.0　**最后更新**：2026-08-13
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）