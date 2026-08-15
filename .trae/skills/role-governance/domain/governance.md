---
name: "project-governance-skill"
description: "Project governance skill covering baseline initialization (17-sheet CSV ledger), stage close (baseline finalization with backup), project archive, and cross-session handover. Invoke when creating project baselines, finalizing stage baselines, archiving projects, or exporting handover."
---

# ProjectGovernanceSkill 项目治理技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能唯一标识**：ProjectGovernanceSkill
- **技能版本**：v21.2.1
- **版本发布日期**：2026-08-02
- **版本变更记录**：v1.0.0 由 project-monitor-skill v2.7.0 拆分而来（PMBOK 7th 整合管理 · ISO 21500 · ITIL v4 配置管理）
- **定位**：项目治理中枢子技能，负责台账与项目基准初始化（create_baseline）、阶段基线固化（stage_close）、全项目归档（project_archive）、跨会话交接（handover_export）。
- **调用主体**：ProjectMonitorSkill（薄路由壳按 action 分发）
- **触发时机**：项目初始化、阶段评审门禁通过后、全项目完工、跨会话交接、25/100 轮强制归档。
- **依赖工具**：project-quality-gate-skill · project-scope-change-skill
- **核心约束**：仅由 ProjectMonitorSkill 路由分发；固化前评审/门禁必须通过；未完成归档总结不得开始新会话；台账版本号独立管理。

---

## 2. 统一入参标准

```json
{
  "action": "create_baseline / stage_close / project_archive / handover_export",
  "current_stage": "需求分析/架构设计/开发编码/测试验收/部署运维/文档归档",
  "content": "对应操作内容",
  "user_confirm": "无/同意/拒绝/查错"
}
```

### action 指令清单

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `create_baseline` | 创建全套台账 CSV 与项目基准（27 个 NN_ 前缀 CSV） | 项目初始化 | 启动就绪=Go |
| `stage_close` | 阶段固化基线（备份+更新版本+产出物清单） | 评审通过、门禁放行 | 评审/门禁通过 |
| `project_archive` | 全项目归档（台账+交付物+审计日志） | 所有阶段完工 | 全部阶段固化 |
| `handover_export` | 跨会话交接打包（话术+台账快照+交接文档） | 周期复盘、新建对话 | 台账可读 |

---

## 3. 治理原则

| 原则 | 要求 |
|------|------|
| 基线独立 | 台账基线版本号独立于技能/项目版本 |
| 固化前置 | 评审与门禁通过后方可固化基线 |
| 备份铁律 | 每次 stage_close 自动备份台账（CSV） |
| 交接完整 | 新对话可完整读取历史数据，无信息遗漏 |
| 归档必检 | 未完成归档总结不得开始新会话 |

---

## 4. 治理流程

> 各环节详细执行内容详见 `.//project_governance_details.md` 对应章节。

### 环节 1：台账与项目基准初始化（create_baseline）

**DoR**：项目启动就绪=Go ✅ · 启动产物已具备（章程/干系人/范围初定/可行性）✅

**执行内容**：创建 `台账/`（27 个 NN_ 前缀 CSV：00_阶段配置.csv … 02_迭代回顾.csv 等全量初始化）、录入项目基准（目标/边界/干系人/质量验收标准/初始风险 + 问题升级机制 + 组织架构 RACI）、基线版本 v0.1，详见 `.//project_governance_details.md` §1。

**DoD**：台账 27 个 CSV 全部创建 ✅ · 项目基准写入「范围基准」CSV ✅ · 初始风险写入「风险&问题台账」CSV ✅ · 问题升级机制写入「风险&问题台账」升级字段 ✅ · 组织架构/RACI 写入「组织架构」CSV ✅ · 基线 v0.1 记录 ✅

**规则**：台账存放于 `.trae/` 目录；未初始化禁止进入需求阶段。

### 环节 2：阶段基线固化（stage_close）

**DoR**：本阶段评审通过 ✅ · 门禁校验通过 ✅ · 阻断级缺陷 0 遗留 ✅

**执行内容**：备份核心文件、更新台账基线版本号、记录验收结论、生成产出物基准清单追加「范围跟踪台账」CSV、自动备份台账，详见 `.//project_governance_details.md` §2。

**DoD**：核心文件已备份 ✅ · 基线版本号已递增 ✅ · 产出物基准清单已追加 ✅ · `台账/` 备份 CSV 已生成 ✅

**规则**：固化前置检查（评审/门禁/缺陷）不通过禁止固化；产出物清单作为下阶段比对基准。

### 环节 3：全项目归档（project_archive）

**DoR**：全部阶段已固化 ✅ · 台账数据完整 ✅

**执行内容**：整合台账 CSV、交付物、评审记录、变更审计日志，生成归档文档包与归档清单，详见 `.//project_governance_details.md` §3。

**DoD**：归档文档包（zip）完成 ✅ · 归档清单完成 ✅ · 收尾归档 CSV 已写入 ✅

**规则**：归档含全部审计日志；归档后标记项目收尾。

### 环节 4：跨会话交接（handover_export）

**DoR**：台账可读 ✅ · 当前阶段与待办可梳理 ✅

**执行内容**：拉取全套台账、生成交接话术、打包台账快照、更新 `跨会话交接文档.md`（25/100 轮强制归档），详见 `.//project_governance_details.md` §4。

**DoD**：交接话术生成 ✅ · 台账快照打包 ✅ · 跨会话交接文档已更新 ✅ · 归档总结确认 ✅

**规则**：25 轮对话强制归档动作；100 轮输出全量复盘与交接话术；未完成归档不得开始新会话。

---

## 5. 标准化输出结构

1. **基线类**：`台账/`（27 个 NN_ 前缀 CSV，含 12_风险问题台账升级字段 / 27_组织架构）、基线版本号、产出物基准清单；
2. **固化类**：备份文件、`台账/` 备份 CSV、验收结论；
3. **归档类**：归档文档包、归档清单；
4. **交接类**：交接话术、台账快照、跨会话交接文档；
> 目录规范详见 `../../shared/references/directory_structure.md`

> 协作接口详见 `../../shared/references/api_contracts.md`

## 6. 技能版本管理规范

> 版本号规则、升级触发条件、升级评审机制统一见 `../../shared/references/common_standards.md`。
> 当前版本：v21.0.0。

---

**文档版本**：v21.2.1
**最后更新**：2026-08-02
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）