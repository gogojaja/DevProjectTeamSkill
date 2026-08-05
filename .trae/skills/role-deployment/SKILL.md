---
name: "role-deployment"
description: "投产发布角色包：部署策略与风险分析、发布计划、准备与演练、分阶段发布执行与监控、回滚、Go-Live 评审与运维交接。触发词：投产策略、发布计划、发布准备、部署执行、发布监控、回滚、Go-Live、运维交接。Load when the user analyzes deployment strategy, writes the release plan, prepares/executes a release, rolls back, or hands over operations."
---

# role-deployment 投产发布角色包

> 版权：`../shared/references/COPYRIGHT.md`　Token：`../shared/references/token_standard.md`　总控：`../shared/governance.md`

## 1. 元数据

- **技能版本**：v21.0.0　**发布日期**：2026-08-04
- **变更记录**：v21.0.0 由 deployment-management-skill + 4 子技能重组为角色包
- **参考标准**：ITIL v4 发布管理 · DORA · SRE 三支柱

## 2. 触发规则

用户表达「投产策略/发布计划/发布准备/部署/发布监控/回滚/Go-Live/运维交接/DORA」时加载本包。先 Read 路由表，命中后只读对应 `domain/*.md`。

## 3. 流程（路由到 domain/）

| 环节 | action | 明细 |
|------|--------|------|
| 策略分析 | analyze_strategy | `domain/strategy.md`（决策树/风险矩阵/DORA/容灾） |
| 计划编写 | write_plan | `domain/planning.md`（12 章 + 变更分级审批） |
| 发布准备 | prepare_release | `domain/release.md`（六项准备 + 演练） |
| 发布执行 | execute_release | `domain/release.md`（金丝雀/蓝绿/滚动 + 三支柱监控） |
| 监控回滚 | monitor / rollback | `domain/release.md`（自动/手动回滚 + 数据还原） |
| Go-Live | go_live_review | `domain/handover.md`（六维门禁） |
| 交接 | handover_ops | `domain/handover.md`（Runbook/监控/on-call/SLA/发布总结） |

## 4. 发布铁律

任何发布前完成策略评审 + 变更分级审批；回滚预案必须随发布计划编写；实施按阶段灰度受控推进；DORA 指标基线评估。

## 5. 输出规范与边界

- 发布计划/总结/Go-Live 评审按 token_standard §3 输出 CSV；
- Go-Live 门禁经 `../shared/governance.md`；
- 边界：仅投产域；回滚数据还原遵循总控安全审计。

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）