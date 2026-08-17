---
name: "role-development"
description: "用户提到开发策略、技术栈、分支规范、编码、代码走查、PR评审、单元测试、联调、质量检查时加载本开发管理角色包：负责开发策略与技术栈选型、分支编码规范、模块编码与安全编码、代码走查与 PR 评审、单元测试、联调与质量收口及基线固化，输出开发总结报告、技术债务登记与质量报告。用户说开发/编码/代码评审时加载。Load when the user starts development strategy, codes modules, reviews code (PR), runs unit tests, integrates, or closes quality baseline."
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

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求开发功能、走查代码、做 PR 评审、补充单测、检查质量或固化基线；
- 前置：需有需求与设计约束、分支状态、环境和安全要求；
- 不适用：任务无明确代码目标、未定义验收标准、或已完成开发动作时不应重复执行。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | 任务和目标已明确 | 代码/测试任务已启动 | 读取需求、设计和环境 |
| 执行中 | 编码或走查开始 | 关键修改或评审完成 | 按开发/审查流程推进 |
| 校验中 | 代码和测试已形成 | 质量门禁通过/失败 | 检查安全、覆盖率和集成风险 |
| 阻塞 | 依赖缺失、环境异常、缺陷未修复 |  补充信息/人工处理 | 暂停并记录阻塞原因 |
| 完成 | 质量通过并完成基线确认 | 进入测试或投产 | 留痕证据并交接 |
| 回退 | 质量门禁失败/缺陷严重 | 回到最近稳定提交 | 回滚问题提交并保留审计 |

### 3. 执行动作层
- 执行步骤 1：确认策略、环境与开发边界；
- 执行步骤 2：模块编码、代码走查和 PR 评审；
- 执行步骤 3：执行单测、联调和质量收口，并完成基线固化；
- 所需工具/脚本：代码审查清单、静态分析工具、测试命令、总控门禁；
- 输入输出约束：代码产出必须具备验收证据，不能仅停留在未验证实现。

### 4. 验收门禁
- 必须产出物：代码变更、测试结果、质量检查记录、PR 评审结论；
- 通过条件：缺陷完成、覆盖率达标、静态分析通过并完成基线确认；
- 失败条件：关键缺陷未修复、代码违反安全要求或质量门禁未过；
- 审核对象：开发负责人 + role-governance 总控。

### 5. 失败处理
- 失败类型：构建失败、测试失败、代码审查问题、安全扫描问题；
- 恢复策略：定位失败原因并回到最小修复范围；
- 回滚方案：回退到最后稳定提交，并在审计中说明影响；
- 重试策略：修复完成后重新运行受影响检验；
- 是否需要人工确认：高危漏洞、生产级变更、签入权限控制需人工确认。

### 6. 产出与交接
- 产出物列表：代码提交、测试报告、质量记录、基线确认；
- 保存路径：代码仓库、测试报告目录、台账/审计记录；
- 交接对象：测试、部署、总控和项目负责人；
- 下一步动作：进入测试或投产审批；
- 归档条件：门禁通过、缺陷清单关闭并完成基线移交。

### 7. 审计记录
- 执行时间：代码提交、评审、测试、基线确认的时间点；
- 关键参数：版本号、分支、缺陷状态、质量指标；
- 关键决策：是否修复、是否回滚、是否进入下阶段；
- 结果证据：PR 记录、测试日志、SAST/SCA 结果、CSV 审计；
- 失败原因：记录在总控审计链及交接文档。

---

**文档版本**：v21.5.0　**最后更新**：2026-08-13
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）