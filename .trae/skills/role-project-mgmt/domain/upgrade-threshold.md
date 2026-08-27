---
name: "pm-upgrade-threshold"
description: "Threshold defining when the lightweight 'project management mode' (reusing role-project-init + role-governance only) must be upgraded to deploying the dedicated role-project-mgmt execution layer. Invoke when deciding whether to build the PM role."
---

# 轻量模式 → 建角色 升级阈值（CR-EVO-001）

> 归属：role-project-mgmt　版本：v21.0.0
> 对齐 PRINCE2「tailor to suit」——管理深度浅时先用编排器「项目管理模式」复用 `role-project-init` + `role-governance`，深度上升再升级建本角色。

## 触发升级的任一条件（持续满足即升级）

| # | 条件 | 量化阈值 | 说明 |
|---|------|----------|------|
| 1 | RAID 需独立持续跟踪 | 在管 RAID 条目持续 > 30 且跨 ≥2 阶段 | 仅靠保障层主台账已不便 PM 日常视图 |
| 2 | 需周期独立进展报告 | 需向决策层/干系人周期产出 highlight report（≥1 次/双周） | 保障层只做评审不编报 |
| 3 | 变更协调成常态 | 变更请求频率 > 1 次/周 且需专职初评与闭环 | PM 执行层职责，保障层只复核 |
| 4 | 多项目统一管控 | 同时管控 ≥2 项目且需统一状态/依赖视图 | 此时叠加 `role-program-mgmt` 更合适 |
| 5 | 经验教训需系统化 | 需持续登记并资产化复用（非偶发） | 保障层归档但不主动经营 |

## 不升级（维持轻量模式）的情形

- 仅单次/偶发协调、状态跟踪，无独立 RAID/报告/变更体系；
- 项目已临近收尾，仅做收口交接；
- 工程交付由对应角色在「标准模式」执行、PM 只做轻量同步。

## 升级动作

满足任一条件 → 编排器「项目管理模式」正式加载 `role-project-mgmt`（接管确认 → 日常循环 → RAID/报告/变更/经验），与 `role-governance` 边界按 `../SKILL.md` §2 执行。
