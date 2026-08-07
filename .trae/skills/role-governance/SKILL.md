---
name: "role-governance"
description: "总控保障角色包：台账与基线初始化、五维评审与门禁、变更审计、进度成本(EVM)、风险扫描、安全审计、基线固化/归档/交接。触发词：台账、阶段评审、门禁、变更审计、EVM、进度、风险、安全审计、基线固化、归档、交接文档。Load when the user manages the ledger, runs reviews/gates, audits changes, updates progress, scans risks, or solidifies/archives/hands over."
---

# role-governance 总控保障角色包（文档管理员）

> 版权：`../shared/references/COPYRIGHT.md`　Token：`../shared/references/token_standard.md`　总控能力：`../shared/governance.md`

## 1. 元数据

- **技能版本**：v21.3.2　**发布日期**：2026-08-07
- **变更记录**：v21.3.2 新增 register_auth 授权登记 + 阶段末授权时效检查（14_授权登记/13 留痕入 git）；v21.3.0 新增 record_env_config/retrospect_harvest/select_model 三 action（环境配置抽取/阶段复盘收割/模型选型）；v21.2.1 新增发布级门禁（release_gate 自动化质量阈值）+ 迭代评审/回顾（iteration_review），门禁分级/防绕过见 `../shared/governance.md`；v21.0.0 由 project-monitor-skill + 6 子技能 + project-governance-skill 重组为角色包；SkillEvolution/SkillAuthoring 迁至 `shared/`
- **参考标准**：PMBOK（十大过程组/领域管控）· ISO 31000 风险

## 2. 触发规则

用户表达「台账/评审/门禁/变更审计/进度成本/EVM/风险/安全审计/基线固化/归档/交接」时加载本包。核心能力直接引用 `../shared/governance.md`；自省/技能维护引用 `../shared/evolution.md`、`../shared/authoring.md`。

## 3. 能力路由（总控核心见 shared/governance.md）

| 能力 | action | 明细 |
|------|--------|------|
| 基线初始化 | create_baseline | `../shared/governance.md` |
| 阶段评审 | stage_review | `../shared/governance.md`（输出 CSV） |
| 门禁校验 | check_gate | `../shared/governance.md` |
| 变更审计 | change_audit / register_change | `domain/scope-change.md` |
| 进度成本 | progress_update | `domain/progress-cost.md`（里程碑/EVM） |
| 质量门禁 | check_gate / 缺陷 | `domain/quality-gate.md` |
| 风险扫描 | risk_scan | `domain/risk.md` |
| 安全审计 | security_audit | `domain/security-audit.md`（高危操作/审计链/回滚） |
| 基线固化 | solidify_baseline | `domain/governance.md`（固化/快照/归档） |
| 发布级门禁 | release_gate | `../shared/governance.md`（含自动化质量阈值，敏捷 发布点=Y） |
| 迭代评审/回顾 | iteration_review | `../shared/governance.md`（迭代末轻量评审+回顾） |
| 环境配置抽取 | record_env_config | `../shared/governance.md`（20_环境配置.csv，密钥别名） |
| 阶段末复盘收割 | retrospect_harvest | `../shared/governance.md`（22_阶段复盘 + 23_复用资产） |
| 模型选型 | select_model | `../shared/governance.md`（21_模型选型，四级规则） |
| 授权登记/时效 | register_auth / 授权检查 | `../shared/governance.md`（14_授权登记 + 13 留痕 + 阶段末时效检查） |
| 交接归档 | handover_export | `domain/governance.md`（交接文档优先） |
| 技能自省 | evolve_start / ctx_health_check | `../shared/evolution.md` |
| 技能维护 | skill-authoring | `../shared/authoring.md` |

## 4. 铁律

评审/变更/门禁/固化/归档禁止其他角色包自主处理，一律经本包；高危文件操作先 `security_audit`；审计链非删除；固化后交接文档断点区必须反映磁盘最新状态（solidify.sh）；跨模型交接优先读 `交接文档.md`。

## 5. 输出规范与边界

- 台账 / 评审 / 变更 / 风险 / 缺陷全部 CSV（UTF-8 with BOM，token_standard §3）；
- 禁止 .xlsx；导出仅回显首 5 行 + 行数；
- 边界：总控域，不直接执行需求/架构/开发/测试/投产业务动作。

---

**文档版本**：v21.3.2　**最后更新**：2026-08-07（register_auth 授权登记 + 阶段末时效检查）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）