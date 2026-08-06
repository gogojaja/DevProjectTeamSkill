# evolution.md — SkillEvolutionSkill 技能自省（单源共享）

> 源：原 skill-evolution-skill。被 role-governance 引用（`../shared/evolution.md`）。
> 工具只读诊断元技能，无写入/删除权限；变更须经审计适配器 + 用户审批。
> 配套脚本：`../skill-evolution-skill/evolve_check_log.py`（genesis/append/check/lessons，CSV 读写）。

## 1. action 指令

| action | 作用 | 触发 |
|--------|------|------|
| `evolve_start` | 五步闭环诊断（PDCA） | 手动/自动条件（默认关闭） |
| `evolve_check_log` | SHA256 哈希链校验 | 怀疑篡改/定期 |
| `evolve_review` | 定期效果评估（五维指标） | 月度/季度 |
| `ctx_health_check` | 上下文健康监控（绿/黄/橙/红，60/75/85%） | 每轮对话后自包含 |

## 2. 五层根因框架（前四层必选，第五层可选）

角色层 / 流程层 / 规则层 / 上下文层 / 追溯性层。

## 3. 哈希链防篡改

`stored_hash` = SHA256(记录内容 + prev_hash)；首条=创世基线（`genesis` 建立）；篡改→链断裂→`check` 定位首条。存储 CSV：`Skill_Evolution_Log.csv` + `Skill_Lessons_Learned.csv`。

## 4. 安全铁律

只读 / 证据每条缺陷须附证据编号 / 单次会话最多一轮诊断（禁止递归）/ scope=full_system 预算 >15K 拆或确认 / 提案 P0-P2 分级。禁止行为：改 SKILL.md、删移文件、绕过审计、无证据推测、诊断中触发业务技能。

## 5. ContextHealthMonitor（跨角色共享）

五项指标（Token 占用率/轮次/工具输出累积/技能负载/关键信息位置）；四级预警绿 0-60 / 黄 60-75 / 橙 75-85 / 红 85+；引发压缩瘦身（MicroCompact）与阶段门禁强制压缩。

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）