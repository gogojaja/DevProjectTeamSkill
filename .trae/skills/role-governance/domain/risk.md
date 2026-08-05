---
name: "project-risk-skill"
description: "Project risk management skill covering risk register initialization, periodic risk scanning (risk_scan), risk level assessment, and risk response strategies. Invoke when scanning risks, updating the risk register, or assessing risk impact."
---

# ProjectRiskSkill 项目风险管理技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能唯一标识**：ProjectRiskSkill
- **技能版本**：v21.0.0
- **版本发布日期**：2026-08-02
- **版本变更记录**：v1.0.0 由 project-monitor-skill v2.7.0 拆分而来（PMBOK 7th 风险管理 · ISO 31000）
- **定位**：项目管控子技能，负责风险登记册初始化、定期风险巡检（risk_scan）、风险等级评估与风险应对策略。
- **调用主体**：ProjectMonitorSkill（薄路由壳按 action 分发）
- **触发时机**：项目初始化、定期巡检、阶段切换、项目重大变更后。
- **依赖工具**：project-progress-cost-skill · project-scope-change-skill
- **核心约束**：仅由 ProjectMonitorSkill 路由分发加载；高风险必须立即制定应对方案并上报决策；风险等级按概率×影响评估。

---

## 2. 统一入参标准

```json
{
  "action": "risk_scan",
  "current_stage": "需求分析/架构设计/开发编码/测试验收/部署运维/文档归档",
  "content": "对应操作内容",
  "user_confirm": "无/同意/拒绝/查错"
}
```

### action 指令清单

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `risk_scan` | 风险巡检（登记册更新/新风险识别/等级评估） | 定期、阶段切换、重大变更 | 风险台账可读 |

---

## 3. 风险管理原则

| 原则 | 要求 |
|------|------|
| 登记册管理 | 全部风险纳入「风险&问题台账」CSV |
| 定期巡检 | 阶段切换与周期复盘时执行 |
| 等级量化 | 概率×影响评估等级 |
| 高风险上报 | 高风险立即制定应对方案并上报 |
| 变更联动 | 重大变更后重新识别风险 |

---

## 4. 风险管理流程

> 各环节详细执行内容详见 `.//project_risk_details.md` 对应章节。

### 环节 1：风险登记册初始化（Risk Register Init）

**执行内容**：预设常见风险（范围/进度/成本/技术/质量/安全/人员七类）+ 应对策略，写入「风险&问题台账」CSV，详见 `.//project_risk_details.md` §1。

**DoD**：初始风险登记册完成 ✅ · 七类风险已预设 ✅

**规则**：项目初始化时建立初始风险登记册。

### 环节 2：风险巡检（risk_scan）

**DoR**：风险台账可读 ✅ · 巡检范围明确 ✅

**执行内容**：读取台账→状态复核→新风险识别（结合进度/成本/质量/安全数据）→等级评估→登记册更新，详见 `.//project_risk_details.md` §2。

**DoD**：风险状态全部复核 ✅ · 新风险已识别 ✅ · 等级已评估 ✅ · 登记册已更新 ✅

**规则**：高风险（高概率×高影响）立即制定应对方案并上报决策；中风险制定预案持续监控。

### 环节 3：风险应对（Risk Response）

**执行内容**：风险应对策略选择（规避/减轻/转移/接受/应急预案）、高风险预案预设，详见 `.//project_risk_details.md` §3。

**DoD**：应对策略已确定 ✅ · 高风险预案已预设 ✅

**规则**：高风险不可控时预设应急预案触发条件。

### 环节 4：风险协同（Risk Coordination）

**执行内容**：需求/架构变更同步风险影响、风险升级重大问题推送人工决策，详见 `.//project_risk_details.md` §4。

**DoD**：变更风险已评估 ✅ · 升级问题已推送 ✅

**规则**：重大变更后必须重新识别风险。

---

## 5. 标准化输出结构

1. **台账类**：「风险&问题台账」CSV 更新（风险登记册）；
2. **报告类**：风险巡检报告、风险等级评估、应对方案；
> 目录规范详见 `../../shared/references/directory_structure.md`

> 协作接口详见 `../../shared/references/api_contracts.md`

## 6. 技能版本管理规范

> 版本号规则、升级触发条件、升级评审机制统一见 `../../shared/references/common_standards.md`。
> 当前版本：v21.0.0。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-02
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）