---
name: "role-governance"
description: "用户提到台账、阶段评审、门禁、变更审计、EVM、进度、风险、安全审计、基线固化、归档、交接文档、文档管理时加载本总控保障角色包：负责台账与基线初始化、五维评审与门禁、变更审计、进度成本(EVM)、风险扫描、安全审计、文档管理、基线固化/归档/交接，输出评审报告、门禁记录、审计台账与基线。用户说管控/评审/门禁/审计时加载。"
---

# role-governance 总控保障角色包（文档管理员）

> 版权：`../shared/references/COPYRIGHT.md`　Token：`../shared/references/token_standard.md`　总控能力：`../shared/governance.md`

## 1. 元数据

- **技能版本**：v21.4.0　**发布日期**：2026-09-01
- **变更记录**：v21.4.0 新增文档管理能力（2026-09-01）——`domain/doc-management.md` 文档生命周期/命名规范/密级处理/归档策略/文档审计（dev-doc-manager 项目技能化，项目群规划 v3.0 评分 74/100）；与 role-program-mgmt 31_文档配置管理互补（本域治理审计，项目群域配置分发）；v21.3.4 授权默认仅本次对话有效（2026-08-15）——register_auth 未填有效期默认会话级，跨会话须显式指定到期时间；目录访问边界铁律（本项目目录外一律经授权）；同步 `shared/governance.md` R6、`references/iron_rules.md` §1、`26_访问边界.csv`；v21.3.3 补充技能维护闭环执行能力门禁（2026-08-15）——维护产出的每个技能必须具备 `闭环执行系统` 标题与标准模板，包含任务入口、状态机、验收门禁、失败恢复、交接审计，不得仅停留在描述型流程；v21.3.2 新增 register_auth 授权登记 + 阶段末授权时效检查（14_授权登记/13 留痕入 git）；v21.3.0 新增 record_env_config/retrospect_harvest/select_model 三 action（环境配置抽取/阶段复盘收割/模型选型）；v21.2.1 新增发布级门禁（release_gate 自动化质量阈值）+ 迭代评审/回顾（iteration_review），门禁分级/防绕过见 `../shared/governance.md`；v21.0.0 由 project-monitor-skill + 6 子技能 + project-governance-skill 重组为角色包；SkillEvolution/SkillAuthoring 迁至 `shared/`
- **参考标准**：PMBOK（十大过程组/领域管控）· ISO 31000 风险

## 2. 触发规则

用户表达「台账/评审/门禁/变更审计/进度成本/EVM/风险/安全审计/基线固化/归档/交接」时加载本包。核心能力直接引用 `../shared/governance.md`；技能自省/改进引用 `../dev-project-team-skill/skills/self-improve/SKILL.md`（含原 evolution 只读诊断能力）；技能维护引用 `../shared/authoring.md`。

## 3. 能力路由（总控核心见 shared/governance.md）

| 能力 | action | 明细 |
|------|--------|------|
| 基线初始化 | create_baseline | `../shared/governance.md` |
| 阶段评审 | stage_review | `../shared/governance.md`（输出 CSV） |
| 门禁校验 | check_gate | `../shared/governance.md` |
| 变更审计 | change_audit / register_change | `domain/scope-change.md` |
| 范围门禁/跟踪 | scope_gate | `domain/scope-change.md`（工具 `tools/scope_tracker.py`，标准 `references/traceability_standard.md` v1.1.1） |
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
| 文档管理 | doc_manage | `domain/doc-management.md`（文档生命周期/命名规范/密级/归档审计；dev-doc-manager 技能化，项目群级配置管理见 role-program-mgmt 31 台账） |
| 技能自省 | evolve_start / ctx_health_check | `../dev-project-team-skill/skills/self-improve/SKILL.md`（PDCA/哈希链/健康监控） |
| 技能维护 | skill-authoring | `../shared/authoring.md`（强制闭环执行系统门禁） |

## 4. 铁律

评审/变更/门禁/固化/归档禁止其他角色包自主处理，一律经本包；高危文件操作先 `security_audit`；审计链非删除；固化后交接文档断点区必须反映磁盘最新状态（solidify.sh）；跨模型交接优先读 `交接文档.md`；**维护产出的技能必须具备 `闭环执行系统` 标题与终审门禁，不得以纯描述型流程发版。**

## 5. 输出规范与边界

- 台账 / 评审 / 变更 / 风险 / 缺陷全部 CSV（UTF-8 with BOM，token_standard §3）；
- 禁止 .xlsx；导出仅回显首 5 行 + 行数；
- 边界：总控域，不直接执行需求/架构/开发/测试/投产业务动作。

---

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求评审、门禁、审计、固化、归档、交接或维护技能库中的角色/流程；
- 前置：需确认项目阶段、台账状态、已发生变更与待审计证据；
- 不适用：不涉及项目状态、没有审计对象、或缺少门禁信息时不应直接发放放行结论。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | 任务和评审对象已明确 | 审计/评审已启动 | 读取台账与上下文 |
| 执行中 | 评审或审计已开始 | 结论/缺陷形成 | 检查门禁、冲突和风险 |
| 校验中 | 关键结论已形成 | 放行、阻断或回退确认 | 比对文档、版本、基线 |
| 阻塞 | 缺失证据、资源冲突、授权缺失 | 补充信息/人工处理 | 暂停并记录阻塞 |
| 完成 | 审计与门禁完成 | 进入归档或交接 | 归档证据并生成交接文档 |
| 回退 | 门禁未过或高风险事件 | 回到最近稳定状态 | 修正、回滚并保留审计链 |

### 3. 执行动作层
- 执行步骤 1：核对台账状态、阶段记录与版本一致性；
- 执行步骤 2：执行风险扫描、门禁校验、审计和基线固化；
- 执行步骤 3：生成 CSV 报告并完成归档、交接或回退；
- 所需工具/脚本：`tools/check_version_consistency.py`、`tools/solidify.sh`、总控台账与审计链；
- 输入输出约束：总控结论必须落盘到 CSV、审计记录和交接文档，不能仅停留在口头建议。

### 4. 验收门禁
- 必须产出物：评审报告、门禁结果、变更审计、固化/归档记录；
- 通过条件：无重大缺陷、门禁合格、交接文档完整且最新；
- 失败条件：关键门禁未过、审计证据缺失、版本/基线不一致；
- 审核对象：总控角色、项目负责人和必要的业务审批方。

### 5. 失败处理
- 失败类型：门禁未过、缺陷严重、版本不一致、授权缺失、审计证据不全；
- 恢复策略：回到最小可验证状态，补足缺失证据和修正记录；
- 回滚方案：恢复到最近稳定基线并保留问题链路；
- 重试策略：修复后重跑门禁和审计检查；
- 是否需要人工确认：高危文件操作、基线固化、发布级门禁必须人工确认。

### 6. 产出与交接
- 产出物列表：评审 CSV、审计台账、归档记录、交接文档断点区；
- 保存路径：项目根 `台账/`、`交接文档.md` 与 `dist/` 产物；
- 交接对象：下一阶段角色、项目负责人和运维/交付方；
- 下一步动作：根据门禁结论进入下一阶段、回退或归档；
- 归档条件：审计完整、版本一致、交接文档已更新。

### 7. 审计记录
- 执行时间：评审、门禁、固化和交接的时间点；
- 关键参数：版本号、阶段、缺陷等级、风险级别、授权状态；
- 关键决策：放行、阻断、回退、归档与交接；
- 结果证据：CSV、记录、快照、交接文档；
- 失败原因：在 `台账/13_安全审计台账.csv` 和 `交接文档.md` 留痕。

---

**文档版本**：v21.4.0　**最后更新**：2026-09-01（新增文档管理能力，dev-doc-manager 技能化）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
