---
name: "deployment-planning-skill"
description: "Release plan writing sub-skill for the DeploymentManagementSkill routing shell. Covers writing the twelve-chapter release plan and change classification approval (standard/normal/emergency with CAB/ECAB path). Invoke when writing the release plan or preparing the change request after deployment strategy is approved."
---

# DeploymentPlanningSkill 投产方案编写技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **分发**：DeploymentManagementSkill `write_plan` 分发（策略分析评审通过后）；仅分发时临时加载。
- **DoR**：策略分析已评审 ✅ · 测试基线文档 ✅ · 架构设计文档 ✅ · 进度基准与投产窗口 ✅
- **依赖**：ProjectMonitorSkill（变更审计、门禁校验）· DeploymentStrategySkill（策略输入）· ITIL v4 变更管理（CAB/ECAB）

## 2. 流程

### 2.1 《投产方案》12 章结构

| 章 | 内容 |
|----|------|
| 1 投产目标 | 业务/技术目标、预期收益 |
| 2 投产范围 | 变更清单（模块/接口/配置/数据/脚本）、排除项及理由 |
| 3 部署策略 | 选定策略及理由、流量切换、灰度阶段划分 |
| 4 变更分类 | 标准/普通/紧急变更、CAB 审批路径 |
| 5 部署步骤 | 前置检查→执行→验证→后置确认 |
| 6 回滚方案 | 触发条件、步骤、数据回退、决策人 |
| 7 环境要求 | 生产配置、资源清单、网络/防火墙变更；配置项经 `台账/20_环境配置.csv`（`../../shared/references/environment_standard.md`）核对，密钥以别名引用 |
| 8 数据迁移 | DB 变更脚本、迁移计划、数据回退方案 |
| 9 监控告警 | RED 指标+业务指标、阈值、值班、升级路径 |
| 10 风险与预案 | 环境/依赖/数据/性能/安全风险及应对 |
| 11 人员与排期 | RACI 矩阵、时间窗口、变更冻结期 |
| 12 验证计划 | 投产后验证清单、顺序、业务验证脚本 |

### 2.2 变更审批流程（ITIL v4）

```
定稿 → 分类判定：标准→预授权直接准备；普通→CAB（提前 3 工作日）→通过后准备；紧急→ECAB（15 分钟决策）→简化文档+后补评审
```

| 变更类型 | 特征 | 审批路径 | 文档要求 |
|---------|------|---------|---------|
| **标准变更** | 低风险、既定流程、频繁执行 | 预授权，无需 CAB | 标准化模板 |
| **普通变更** | 需评估风险与影响 | CAB 审批 | 完整投产方案 |
| **紧急变更** | 紧急修复、时间敏感 | ECAB 快速审批 | 简化文档+后补 |

## 3. 输出规范

| 产出物 | 格式 |
|--------|:---:|
| 《投产方案》（12 章） | Markdown |
| 《变更申请单》（分类+审批） | CSV |

## 4. 边界

- **DoD**：《投产方案》含 12 章 · 变更分类与审批路径明确 · 回滚方案含数据回退且已测 · 监控告警方案已制定 · 经项目经理/架构师评审
- 方案基于已评审策略报告；须 CAB/ECAB 审批后执行；变更分类错误视为高风险；方案变更需 `change_audit`。

> 目录规范、api_contracts、版本管理规则见 `../../shared/references/{directory_structure,api_contracts,common_standards}.md`

**文档版本**：v21.0.0
**最后更新**：2026-08-03
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
