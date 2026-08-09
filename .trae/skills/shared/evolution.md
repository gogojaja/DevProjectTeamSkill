# evolution.md — 技能自省路由桥（单源共享）

> 源：原 skill-evolution-skill。被 role-governance 引用（`../shared/evolution.md`）。
> **已合并**：2026-08-09，SkillEvolutionSkill 只读诊断能力并入 `self-improve` 子技能 `domain/self-diagnosis.md`。
> 本文件保留为兼容路由桥，不承载功能明细。

## 1. 路由

| 原能力 | 现位置 |
|--------|--------|
| `evolve_start` 五步闭环诊断（PDCA） | `../dev-project-team-skill/skills/self-improve/domain/self-diagnosis.md` §2 |
| `evolve_check_log` SHA256 哈希链校验 | 同上 §4 |
| `evolve_review` 定期效果评估（五维指标） | `../dev-project-team-skill/skills/self-improve/domain/experiment-evaluation.md` |
| `ctx_health_check` 上下文健康监控 | `../dev-project-team-skill/skills/self-improve/domain/self-diagnosis.md` §5 |
| 五层根因框架 | `../dev-project-team-skill/skills/self-improve/domain/self-diagnosis.md` §3 + `root-cause-analysis.md` |

## 2. 原则（保持不变）

1. 诊断模式只读，变更须经审批；
2. 每条缺陷附证据编号；
3. 单次会话最多一轮诊断（禁止递归）；
4. 提案 P0-P2 分级；
5. 诊断中禁止触发业务技能。

## 3. 加载指引

需要技能库自省/诊断/防篡改/健康监控时，加载 `self-improve` 技能包（`../dev-project-team-skill/skills/self-improve/SKILL.md`），其 `domain/self-diagnosis.md` 为合并后的完整实现。

---

**文档版本**：v21.4.0　**最后更新**：2026-08-09（合并入 self-improve，保留桥接）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）