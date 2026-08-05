---
name: "skill-evolution"
description: "技能演进诊断元技能（只读诊断侧）：五步闭环诊断、五层根因分析、上下文健康监控、SHA256 哈希链审计、经验教训六分类库、定期效果评估。触发词：evolve_start、ctx_health_check、技能自省、诊断技能、演进。Load when the user starts skill evolution diagnosis, context health checks, or hash-chain audit."
---

# SkillEvolutionSkill 技能自省优化元技能（shared/evolution.md）

> 版权声明详见 `./references/COPYRIGHT.md`　接口契约详见 `./references/api_contracts.md`

## 1. 基础元数据

- **技能唯一标识**：SkillEvolutionSkill
- **技能版本**：v2.2.0（源版本，随宿主 v21.0.0 内嵌 shared/）
- **定位**：通用技能自省优化元技能（Meta-Skill），支持独立（standalone）与嵌入（embedded）两种部署模式。
- **调用主体**：用户手动指令触发（`evolve_start`）；可选自动触发（6 条条件，默认关闭）。
- **触发时机**：手动（evolve_start）/ 自动（默认关闭）/ 定期评估（evolve_review，月度/季度）/ 上下文健康监控（ctx_health_check，每轮对话后自包含执行）。
- **参考标准**（行业最佳实践）：PDCA 循环（Plan-Do-Check-Act，持续改进）· 根本原因分析 RCA（5-Why/鱼骨图）· 混沌工程原则 · SHA-256 哈希链防篡改（区块链式记账）· context window 管理最佳实践（Lost in the Middle）· ITIL 持续改进（CSI）
- **部署模式**：standalone（无外部依赖，审计写本地 Markdown/CSV，用户人工审批）/ embedded（通过四适配器调用宿主技能审计/交接/存储/版本能力）。
- **核心约束**：
  1. 本技能为**只读诊断**元技能，无任何文件写入/修改/删除权限；
  2. 所有优化提案须经审计适配器审批 + 用户人工确认后方可落地；
  3. 单次会话最多执行一轮诊断；诊断期间禁止触发业务技能操作；
  4. 诊断数据按 scope 按需读取，不全量加载；
  5. 每次诊断记录 SHA256 哈希链，防篡改可追溯。

## 2. 统一入参标准

```json
{
  "action": "操作指令，可选值：evolve_start / evolve_check_log / evolve_review / ctx_health_check",
  "deploy_mode": "部署模式，可选：standalone / embedded（默认 standalone）",
  "scope": "诊断范围，可选：single_skill / cross_skill / full_system",
  "target_skill": "目标技能名称（任意字符串，如 MyCustomSkill / DevProjectTeamSkill / 无则诊断全部已加载技能）",
  "content": "对应操作内容：诊断范围说明/校验起始记录/评估周期/上下文状态数据",
  "user_confirm": "用户指令：无/同意/拒绝/查错"
}
```

### action 指令清单

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `evolve_start` | 执行五步闭环诊断（PDCA） | 手动或自动条件满足 | 单次会话未执行过诊断 |
| `evolve_check_log` | 执行 SHA256 哈希链校验 | 怀疑台账被篡改、定期校验 | 审计台账已存在 |
| `evolve_review` | 定期效果评估（月度/季度） | 周期结束、手动触发 | 至少完成 1 次 evolve_start |
| `ctx_health_check` | 上下文健康检查（五项指标） | 每轮对话后自动执行（自包含） | 无 |

## 3. 适配器接口规范

| 适配器 | embedded 实现 | standalone 实现 | 接口契约 |
|--------|--------------|----------------|---------|
| audit | 宿主 `change_audit` | 输出《变更审批单》Markdown，用户人工确认 | 输入=变更描述/影响/提案编号；输出=审批结果+编号 |
| handover | 宿主 `handover_export` | 生成 `Skill_Evolution_Handover_<时间戳>.md` | 输入=触发原因；输出=快照路径+摘要 |
| storage | 宿主共享台账 | `Skill_Evolution_Log`(CSV 2) + `Skill_Lessons_Learned`(CSV 6) | 输入=记录类型+数据；输出=状态+记录编号 |
| version | 宿主版本管理（评审见 `./references/common_standards.md`） | 输出《技能升级建议书》Markdown | 输入=提案编号+变更+影响；输出=版本建议+评审角色 |

**适配器自动检测**：启动时扫描 `.trae/skills/` 目录，存在含 `change_audit`/`handover_export` action 的技能 → embedded 并自动绑定；否则 standalone 加载内置降级实现。

## 4. 核心能力模块

### 模块一：evolve_start — 五步闭环诊断

| Step | 名称 | 输出 |
|------|------|------|
| 1 | Plan 规划诊断范围 | 《诊断范围确认单》 |
| 2 | Do 缺陷采集与分层 | 《缺陷清单》（证据编号/分层/系统性标记） |
| 3 | Check 效果评估与基线对比 | 《效果评估摘要》 |
| 4 | Act 输出优化提案 | 《优化提案报告》（P0/P1/P2 分级） |
| 5 | Archive 归档与经验沉淀 | 诊断完成确认 + 台账/经验库更新 |

### 模块二：evolve_check_log — 哈希链校验

读取创世基线 → 逐条重算 SHA256(内容+prev_hash) → 比对（全匹配=通过；不匹配=断裂告警+定位首条）→ 失败用备份恢复或重建基线。存储：`Skill_Evolution_Log/01_诊断记录.csv` + `02_哈希基线.csv`。输出：《哈希链校验报告》。

### 模块三：evolve_review — 定期效果评估

五维指标：诊断覆盖率≥80%、缺陷检出率≥70%、提案采纳率≥60%、系统性缺陷复发率≤20%、经验教训复用率≥50%。

### 模块四：ctx_health_check — 上下文健康监控

自包含运行，每轮对话后自动执行。五项监控指标、四级预警（绿 0-60%/黄 60-75%/橙 75-85%/红 85%+）、MicroCompact 适配、关键信息位置保护。输出：预警事件写入审计台账。

## 5. 五层根因诊断框架

| 层 | 名称 | 类型 | 诊断范围 |
|----|------|------|---------|
| 1 | 角色层 Role Layer | 必选 | 角色定义、边界、协作、权限 |
| 2 | 流程层 Process Layer | 必选 | 阶段流转、门禁、串行约束 |
| 3 | 规则层 Rule Layer | 必选 | 规则矛盾、宽松、严格、缺失 |
| 4 | 上下文层 Context Layer | 必选 | 上下文长度、信息遗忘、幻觉 |
| 5 | 追溯性层 Traceability Layer | 可选 | 追溯矩阵完整性（无追溯矩阵时跳过并提示） |

## 6. SHA256 哈希链防篡改机制

**结构**：`stored_hash` = SHA256(记录内容 + prev_hash)；`prev_hash` = 上条 stored_hash（首条=创世哈希）。
**创世基线**：首次使用执行 `evolve_check_log genesis` 生成；后续记录全部追溯创世基线。
**篡改检测**：历史记录修改 → 该记录 stored_hash 不匹配 → 后续链断裂 → check 输出断裂位置。
**存储**：standalone → `Skill_Evolution_Log/` CSV + `Skill_Lessons_Learned/` CSV；embedded → storage_adapter 决定。

## 7. 触发规则与安全铁律

### 7.1 自动触发条件（默认关闭）

累计缺陷≥10（严重+主要）/ 连续 3 次同类缺陷 / 变更≥3 次 / 评审失败 / 同一缺陷复发≥2 次 / 升级评审未通过。启用：输入「启用 SkillEvolutionSkill 自动触发」。

### 7.2 安全铁律

1. **只读铁律**：无任何写入/修改/删除权限，变更须经审计适配器 + 用户审批；
2. **证据铁律**：每条缺陷判定须附证据编号（来源+位置+时间戳），无证据自动剔除；
3. **诊断刹车**：单次会话最多一轮诊断；期间屏蔽业务技能触发；禁止递归调用自身；
4. **范围约束**：scope=full_system 预估 Token >15K 必须拆分或用户确认；
5. **提案分级**：必须标注 P0/P1/P2；P0 须附安全风险说明；禁止 P2 包装为 P0。

### 7.3 禁止行为清单

直接修改任何 SKILL.md/台账/数据文件 · 删除或移动项目文件 · 绕过审计适配器执行变更 · 无证据生成推测性缺陷判定 · 诊断中触发业务技能 · 递归调用 evolve_start。

## 8. 与相关技能的关系

| 技能 | 关系 | 边界 |
|------|------|------|
| DevProjectTeamSkill | 宿主技能，embedded 通过四适配器协作 | 本技能只读诊断，不执行业务角色任务 |
| shared/authoring.md | 诊断→产出协作 | 本技能只读诊断已有技能；authoring 负责新建/修改 SKILL.md，两者不重叠 |
| role-governance | 审计/交接/存储适配器实现方 | 本技能无直接写权限，变更落地经总控审计 |

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
