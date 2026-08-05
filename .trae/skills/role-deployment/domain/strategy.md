---
name: "deployment-strategy-skill"
description: "Release and deployment strategy analysis sub-skill for the DeploymentManagementSkill routing shell. Covers deployment strategy selection (decision tree), release risk assessment matrix, rollback plan design, DORA baseline evaluation, and disaster recovery validation plan (RTO/RPO/chaos). Invoke when analyzing deployment strategy or assessing release risk."
---

# DeploymentStrategySkill 投产策略分析技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **分发**：DeploymentManagementSkill `analyze_strategy` 分发（测试基线固化后、投产第一步）；仅分发时临时加载。
- **DoR**：测试基线固化 ✅ · 总结报告评审通过 ✅ · 进度基准与投产窗口明确 ✅ · 投产资源初步分配 ✅
- **依赖**：ProjectMonitorSkill（可追溯矩阵、变更审计、基线固化）· ITIL v4 变更评估 · DORA + EU DORA · ISO 22301（RTO/RPO）

## 2. 流程

### 2.1 部署策略选型（决策树）

| 策略 | 适用场景 | 风险 | 回滚速度 | 资源要求 |
|------|---------|:---:|:---:|------|
| 蓝绿部署 | 核心系统、秒级回滚 | 中 | 秒级 | 2 套环境 |
| 金丝雀发布 | 中高风险、渐进验证 | 低 | 分钟级 | 流量控制 |
| 滚动更新 | 无状态服务、集群 | 中 | 分钟级 | 滚动策略 |
| 特性开关 | 控制开放节奏、A/B | 低 | 秒级关闭 | 开关平台 |
| 大爆炸 | 小型/非核心变更 | 高 | 需完整回滚 | 低 |

```
核心系统 → 可停机→蓝绿；不可停机→金丝雀
非核心 → 大规模→金丝雀/滚动；中等→滚动/特性开关；小→大爆炸
```

### 2.2 投产风险评估矩阵

| 影响\概率 | 极低(1) | 低(2) | 中(3) | 高(4) |
|-----------|---------|-------|-------|-------|
| **致命(4)** | 中(4) | 高(8) | 极高(12) | 极高(16) |
| **严重(3)** | 低(3) | 中(6) | 高(9) | 极高(12) |
| **一般(2)** | 低(2) | 中(4) | 中(6) | 高(8) |
| **微小(1)** | 极低(1) | 低(2) | 低(3) | 中(4) |

六维识别风险信号：业务影响/技术复杂度/数据敏感性/回滚难度/监控覆盖/合规要求；数据迁移深层、无回滚能力、无监控覆盖、监管合规均视为高风险。

### 2.3 回滚预案设计

- 回滚目标 ≤5 分钟（金融级）；触发：错误率 >1%×5min / P99 > 基线 200% / 核心业务指标异常
- 步骤：停止流量→切换版本→数据回退→验证恢复；DDL/DML 回退脚本、数据快照恢复；决策人明确（工程经理或值班负责人）

### 2.4 DORA 基线评估

| 指标 | 定义 | 目标 |
|------|------|------|
| 部署频率 | 成功发布到生产频率 | 按需/每日/每周 |
| 变更交付时间 | 代码提交→部署生产 | <1h/天 |
| 变更失败率 | 导致生产故障部署占比 | <5% |
| 服务恢复时间 | 故障到恢复 | <1h |

### 2.5 灾备验证计划（ISO 22301）

RTO ≤15 分钟（核心）· RPO ≤5 分钟（核心）· 灾备切换自动化演练 ≥1 次投产前 · 混沌工程依赖故障注入验证优雅降级。

## 3. 输出规范

| 产出物 | 格式 |
|--------|:---:|
| 《投产策略分析报告》 | Markdown |
| 《投产风险评估矩阵》 | CSV |
| 《DORA 基线表》 / 《灾备验证计划》 | CSV/Markdown |

## 4. 边界

- **DoD**：策略选定并记录理由 · 风险评估矩阵完成 · 回滚预案含数据回退 · DORA 基线已评估 · 灾备验证计划已制定
- 策略未评审通过不得进入投产方案编写；风险评估须项目经理/架构师确认；核心系统必须秒级回滚策略；策略变更需 `change_audit`。

> 目录规范、api_contracts、版本管理规则见 `../../shared/references/{directory_structure,api_contracts,common_standards}.md`

**文档版本**：v21.0.0
**最后更新**：2026-08-03
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
