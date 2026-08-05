---
name: "deployment-handover-skill"
description: "Release review, summary and operations handover sub-skill for the DeploymentManagementSkill routing shell. Covers Go-Live review (six-dimension check with gate admission), release summary report writing (ten chapters), operations handover (Runbook/monitoring/on-call/SLA), and release stage review with gate closure. Invoke when performing Go-Live review, writing release summary, doing operations handover, or reviewing the release stage."
---

# DeploymentHandoverSkill 投产评审总结与运维交接子技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **分发**：DeploymentManagementSkill `go_live_review`（投产前 24-48h）/ `write_report`（监控稳定期过后）/ `handover_ops`（总结报告完成后）/ `stage_review`（总结报告定稿后）；仅分发时临时加载。
- **依赖**：ProjectMonitorSkill（check_gate 门禁、stage_review 阶段评审、stage_close 基线固化、project_archive 归档）· Go-Live Review / ITIL v4 发布评估与服务移交 · DORA

## 2. 流程

### 2.1 Go-Live 六维检查总表

| 维度 | 检查项 | 红线（No-Go） |
|------|--------|---------------|
| **代码就绪** | 合并/PR 审批/测试通过/依赖锁定 | 失败测试、未审批代码 |
| **测试就绪** | 验收/回归/性能安全/缺陷闭环 | 开放 Critical 缺陷 |
| **基础设施** | 配置/DB 迁移可逆/SSL/监控/回滚已测 | 无回滚计划或未测试 |
| **文档就绪** | 用户/API/运维手册/变更说明/已知问题 | 破坏性 API 变更无文档 |
| **沟通就绪** | 干系人签署/简报/客户沟通/升级路径 | 关键干系人未批准 |
| **团队就绪** | 值班/开发可升级/决策人 | 无 24h 值班覆盖 |

**决策**：Go=全绿或黄色有可接受缓解；Conditional Go=发布窗口前解决指定项；No-Go=红项未解或黄色项累积不可接受。

### 2.2 门禁准入（check_gate）六项

测试基线固化 · 六维全部通过（或黄色缓解）· 变更审批通过 · 回滚已测 ≤5 分钟 · 监控已配且覆盖新端点 · 投产方案已评审通过。

### 2.3 投产总结报告（10 章）

| 章 | 内容 |
|----|------|
| 1 投产概况 | 范围/策略/窗口/人员 |
| 2 执行统计 | 步骤/成败/耗时/灰度 |
| 3 问题记录 | 问题/处理/遗留 |
| 4 DORA 采集 | 部署频率/交付时间/失败率/恢复时间 |
| 5 监控分析 | 趋势/异常/性能基线 |
| 6 业务验证 | 验证清单/结果 |
| 7 风险评估 | 残留风险/已知影响 |
| 8 投产结论 | 成功与否/跟进修复 |
| 9 经验教训 | 成功/改进/优化方向 |
| 10 交接清单 | 产出物清单/支持安排 |

### 2.4 运维交接标准产出物

| 产出物 | 负责人 | 验收标准 |
|--------|--------|---------|
| 运维手册 Runbook | 运维部署工程师 | 覆盖新功能操作/故障排除 |
| 监控仪表盘 | 运维部署工程师 | 覆盖全部新端点、告警合理 |
| 已知问题清单 | 测试工程师 | 每项含 workaround |
| 值班与升级路径 | 工程经理 | 24×7 覆盖、升级链路清晰 |
| SLA 定义 | 项目经理 | 支持时段、响应时间明确 |

### 2.5 阶段评审四维 + 门禁准出

范围合规（覆盖全部变更项、与方案一致）· 功能逻辑（业务正常、DORA 达标）· 工程规范（文档/报告/交接完整）· 风险安全（残留充分、已知问题有 workaround）。

**门禁准出**：投产执行率 100% · 灰度通过率 100% · 监控稳定期通过 · 业务验证通过 · 交接 100% · 报告评审通过 → `stage_close` 固化基线 + `project_archive` 归档。

## 3. 输出规范

| 产出物 | 格式 |
|--------|:---:|
| 《Go-Live 评审报告》 | CSV |
| 《投产总结报告》/《运维手册 Runbook》 | Markdown |
| 《已知问题清单》/《运维交接签收单》 | CSV |
| 《门禁校验结果》/《基线固化记录》 | CSV |

## 4. 边界

- **前置**：go_live=准备完成+预演通过+变更审批通过；write_report/handover=投产完成+监控稳定期通过
- 评审须在投产前 24-48h；红项触发 No-Go；Conditional Go 指定负责人+截止时间；No-Go 覆盖仅限极端场景；交接不完整不得归档。

> 目录规范、api_contracts、版本管理规则见 `../../shared/references/{directory_structure,api_contracts,common_standards}.md`

**文档版本**：v21.0.0
**最后更新**：2026-08-03
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
