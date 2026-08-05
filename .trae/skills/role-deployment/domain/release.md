---
name: "deployment-release-skill"
description: "Release preparation, execution and monitoring sub-skill for the DeploymentManagementSkill routing shell. Covers six-item preparation and rehearsal, staged release execution (canary/blue-green/rolling) with real-time monitoring (three pillars/RED), and automatic or manual rollback with data reversion. Invoke when preparing the release, executing deployment, monitoring, or rolling back."
---

# DeploymentReleaseSkill 投产准备执行与回滚子技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **分发**：DeploymentManagementSkill `prepare_release`（方案审批后）/ `execute_release`（Go-Live 评审通过后）/ `rollback`（投产失败、监控告警）；仅分发时临时加载。
- **DoR**：prepare=方案已审批+变更审批通过+版本已构建；execute=Go-Live 准入放行+投产窗口到达+值班就位
- **依赖**：ProjectMonitorSkill（安全审计台账、变更审计、门禁）· ITIL v4 · 三支柱（Metrics/Logs/Traces）+RED · 供应链安全（SBOM/签名）

## 2. 流程

### 2.1 投产准备六项

| 准备项 | 内容 | 验收标准 |
|--------|------|---------|
| **生产环境** | 配置核对、资源确认、网络/防火墙开通 | 与方案一致 |
| **部署包** | 生产包、签名验证、SBOM 清单 | 来自 CI/CD，非开发机直推 |
| **数据迁移** | DDL/DML 脚本、数据校验脚本 | 预生产验证且可逆 |
| **回滚包** | 回滚脚本、数据回退脚本、配置回退文件 | 回滚 ≤5 分钟 |
| **监控配置** | 指标采集、告警阈值、仪表盘、值班通知 | 覆盖全部新端点 |
| **预演验证** | 预生产完整执行一次部署 | 预演通过、无阻断 |

部署包安全：中央安全仓库 · 含 SBOM · SAST/DAST/SCA 无高危 · 制品签名验证防篡改。

### 2.2 预演五步

环境就绪→数据迁移预执行→部署包上传部署→冒烟测试→回滚演练（验证 ≤5 分钟）。

**预演报告**记录：时间/环境/执行人、各步骤结果、问题及处理、回滚演练耗时。

### 2.3 执行流程（金丝雀示例）

```
全量前检查 → 10% → 监控30-60min → 通过? → 否→自动回滚
          → 是 → 25% → 监控 → 通过? → 否→自动回滚 → 是 → 50% → 监控 → 通过? → 否→自动回滚 → 是 → 100% → 投产后验证 → 稳定期2-4h
```

**灰度验证指标**：错误率 ≤ 基线+0.5% · P50/P95/P99 ≤ 基线×1.2 · 吞吐量 ≥ 基线×0.9 · 核心业务 ≥ 99.5% · 资源 ≤ 阈值。

### 2.4 监控三大支柱

| 支柱 | 监控内容 | 工具建议 |
|------|---------|---------|
| **指标 Metrics** | RED（请求/错误/延迟）、资源、业务指标 | Prometheus+Grafana |
| **日志 Logs** | 应用/访问/错误/审计日志 | ELK Stack |
| **链路 Traces** | 跨服务路径、慢调用定位 | OpenTelemetry/Jaeger |

**自动回滚触发**：错误率 > 阈值（如 1%）持续 5 分钟 / P99 > 基线 200% / 核心业务指标异常 / 健康检查连续失败。

### 2.5 执行记录

每步标记成功/失败/跳过；执行时间/执行人/环境版本；实际 vs 预估耗时；问题与处理。

## 3. 输出规范

| 产出物 | 格式 |
|--------|:---:|
| 《环境就绪检查清单》/《预演报告》 | Markdown |
| 《部署执行记录》/《灰度验证报告》 | CSV |
| 《监控告警记录》/《回滚记录》 | CSV |

## 4. 边界

- **DoD**：prepare=环境就绪·部署包已验证（签名+SBOM）·迁移可逆·回滚≤5 分钟·监控覆盖·预演无阻断；execute=按策略执行·灰度各阶段通过·全量完成·投产后验证·稳定期通过·记录完整
- Go-Live 准入放行前禁止执行；严格按审批方案执行，禁止临时变更；灰度未达指标必回滚；自动回滚 5 分钟内；投产新问题优先回滚；仅用户下达「查错」后才排查。

> 目录规范、api_contracts、版本管理规则见 `../../shared/references/{directory_structure,api_contracts,common_standards}.md`

**文档版本**：v21.0.0
**最后更新**：2026-08-03
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
