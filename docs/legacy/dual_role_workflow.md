## 8. 双角色裁剪流程（业务人员模式）

> **适用场景**：使用者是项目业务人员，只负责需求编写和测试用例编写与执行，架构设计/开发编码/投产部署/文档归档由其他团队完成。

### 8.1 裁剪方案

| 角色 | 状态 | 依赖技能 | 说明 |
|------|------|---------|------|
| 需求分析师 | 保留 | requirements-analysis-skill（路由壳 → requirements-elicitation-skill / requirements-dimension-analysis-skill / requirements-specification-skill / requirements-lifecycle-skill） | 完整保留四环节流程 |
| 架构设计师 | 裁剪 | architecture-management-skill（路由壳 → architecture-strategy-skill / architecture-design-skill / architecture-data-security-skill / architecture-review-skill） | 由其他团队负责，不加载 |
| 开发工程师 | 裁剪 | development-strategy-skill / development-coding-skill / development-review-skill / development-testing-skill / development-integration-skill | 由其他团队负责，不加载 |
| 测试工程师 | 保留 | TestManagementSkill（路由壳 → test-strategy-skill / test-planning-skill / test-design-skill / test-preparation-skill / test-execution-skill / test-summary-skill） | 完整保留策略+执行流程 |
| 运维部署工程师 | 裁剪 | DeploymentManagementSkill | 由其他团队负责，不加载 |
| 文档管理员 | 裁剪 | （整合职责） | 归档交接由其他团队负责 |
| ProjectMonitorSkill | 公共底座保留 | 路由壳（governance/scope-change/progress-cost/quality-gate/risk/security-audit 6 子技能） | 保留但简化使用（仅需求+测试相关台账） |

**启动话术**：`DevProjectTeamSkill，仅加载【需求分析师】和【测试工程师】`

### 8.2 双阶段流程

两个角色分属项目生命周期的不同阶段，中间通过跨团队交接点衔接，非串行流转关系：

```
阶段A（需求分析师）           跨团队交接点            阶段B（测试工程师）
1.需求收集                  ──→ 交付需求基线 →      5.策略分析
2.需求分析                  ←─ 接收待测版本 ←       6.方案编写
3.需求编写                                         7.用例设计
4.需求评审                                         8.环境准备
  → 需求基线固化                                    9.执行与缺陷
                                                   10.总结评审
                                                     → 测试基线固化
```

**阶段A：需求分析（需求分析师，4 环节）**

| 环节 | action | 输出物 |
|------|--------|--------|
| 需求收集 | `gather_requirements` | 需求收集清单.xlsx |
| 需求分析 | `analyze_requirements` | 需求分析报告.xlsx、冲突消解记录.xlsx |
| 需求编写 | `document_requirements` | SRS_v1.0.xlsx（10 Sheet）、SRS质量校验报告.xlsx |
| 需求评审 | `stage_review` | 评审报告 Excel（5 Sheet）、需求基线 v1.0 固化 |

**跨团队交接点（需求 → 其他团队 → 测试）**

- 需求阶段交付物：SRS_v1.0.xlsx、需求分析报告.xlsx、需求追溯矩阵、需求基线固化确认书
- 其他团队执行：架构设计 → 开发编码 → 单元测试 → 交付待测版本
- 测试阶段接收物：待测版本（部署包/制品）、开发完成报告（含已知问题清单）、接口文档/API文档、测试环境访问权限

**阶段B：测试管理（测试工程师，6 环节）**

| 环节 | action | 输出物 |
|------|--------|--------|
| 策略分析 | `analyze_strategy`/`create_rtm` | 策略报告、RTM Excel、工时估算 |
| 方案编写 | `write_plan` | 测试方案（14章） |
| 用例设计 | `design_cases` | 测试用例 Excel |
| 环境准备 | `prepare_env` | 环境就绪清单、冒烟结果 |
| 执行与缺陷 | `execute_test`/`manage_defect` | 执行记录、缺陷清单 |
| 总结与评审 | `write_report`/`stage_review` | 测试总结报告、评审 Excel、测试基线固化 |

### 8.3 门禁校验（简化版）

**需求阶段门禁**：SRS质量校验通过、七维度无遗漏、缺陷闭环、追溯无断链、范围一致、变更经审批。门禁通过后交付给其他团队（非流转架构阶段）。

**测试阶段门禁**：用例覆盖率无断链、缺陷闭环率 100%、用例通过率 ≥95%、测试报告评审通过。门禁通过后交付测试报告给其他团队（非流转投产阶段）。

### 8.4 台账简化

16 Sheet 台账中 10 个使用（其中 3 个简化使用）、6 个不使用。台账文件保持完整结构（不删除 Sheet），仅标记不使用的不写入数据，确保其他团队接手时可无缝恢复完整台账。

| 使用状态 | Sheet |
|---------|-------|
| 使用 | 启动组、范围基准、质量基准、范围变更台账、范围跟踪台账、需求追溯矩阵、质量缺陷台账、风险&问题台账、门禁验收记录 |
| 使用（简化） | 进度基准（仅需求+测试里程碑）、进度跟踪台账（仅需求+测试进度）、执行记录（仅需求+测试记录） |
| 不使用 | 成本基准、成本消耗台账、安全审计台账、收尾归档 |

### 8.5 阶段切换话术

| 场景 | 话术 | 效果 |
|------|------|------|
| 启动需求阶段 | `开始需求分析` | 激活需求分析师，从需求收集开始 |
| 需求完成交付 | `需求基线已固化，交付给其他团队` | 记录交接，需求分析师待命 |
| 接收待测版本 | `已接收待测版本，开始测试` | 激活测试工程师，从策略分析开始 |
| 测试完成交付 | `测试基线已固化，交付测试报告` | 记录交接，测试工程师待命 |
| 需求变更 | `需求变更，需要分析影响` | 切回需求分析师执行 `change_analysis` |

### 8.6 与完整六角色对比

| 维度 | 完整六角色 | 双角色裁剪 |
|------|-----------|-----------|
| 启用角色 | 6 个 | 2 个（需求/测试） |
| 加载技能 | 7 个 | 3 个（需求+测试+总控） |
| 执行环节 | 36+ | 10（4 需求 + 6 测试） |
| 台账 Sheet | 16 个全部使用 | 10 个使用（3 个简化） |
| 阶段流转 | 串行六阶段 | 双段+跨团队交接 |
| 预估耗时 | ~8h | ~3h（需求 ~1h + 测试 ~2h） |
| 适用人员 | 全栈开发者/技术负责人 | 业务人员/测试人员/QA |

> 详细文档：`dual-role-workflow/dual-role-workflow.html`

---

**文档版本**：v8.2.0
**最后更新**：2026-08-02
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
