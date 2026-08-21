# 夜间全项目质量门禁（评审 + 单元测试）设计方案

> **状态**：草案 v1（评审通过，暂不落地）　**生成日期**：2026-08-21
> **档位**：FULL（best-practice-solution，含行业最佳实践锚定 + 多视角评审）
> **范围**：本仓库（DevProjectTeamSkill 技能库）及用户管理的多项目，每晚定时执行质量评审与单元测试
> **铁律对齐**：A 级凭据（铁律 #3）/ B 级脱敏（铁律 #8）/ 源码单源（AGENTS.md 规则 #1-#2）

> ⚠️ **暂不落地声明**：本文档为设计方案，不含任何可调度的实现代码。附录中的 CI 配置 / 脚本片段仅作「未来落地参考」，本仓库当前不创建 `.github/workflows/*.yml`、`tools/nightly_quality_gate.py` 或任何 crontab 条目。落地须另起实施任务。

---

## 1. 背景与目标

用户希望「每天晚上对所有项目进行一次评审或单元测试」，结合行业最佳实践形成一套方案。

目标分解：
1. **评审**：对每个项目跑可自动化质量门禁（架构 / 代码 / 安全 / 测试 / 性能 多视角）。
2. **单元测试**：夜间跑全量测试套件，捕获 PR 阶段漏掉的跨模块回归。
3. **可运维**：日志、重试、告警、审计齐全；失败有人看、有人管。
4. **合规**：凭据不入库、报告脱敏，对齐本仓库铁律 #3 / #8。

---

## 2. 决策问题清单（Triage）

| 编号 | 决策问题 | 影响 |
|------|----------|------|
| DQ1 | 调度载体：裸 crontab / 平台 CI schedule / 自建 scheduler | 系统级、运维可见性 |
| DQ2 | 单项目评审引擎：复用 `quality_gate.py` / 新建 | 重复造轮子成本 |
| DQ3 | 夜间执行内容：自动门禁 / 单测全量 / AI 语义评审 | 可靠性 + 成本 |
| DQ4 | 多项目枚举与凭据（A 级）管理 | 安全合规 |
| DQ5 | 失败处置与告警闭环 | 运维有效性 |

---

## 3. 行业最佳实践依据（证据卡）

| ID | 结论 | 来源 | 等级 | 置信度 |
|----|------|------|------|--------|
| EV-001 | 用平台 CI schedule 替代裸 crontab，获得日志/重试/告警/审计，避免「服务器重启后无人知」 | GitLab Scheduled Pipelines（2026） | T2 | medium-high |
| EV-002 | 测试金字塔：大量快单测每次提交跑（<10min 反馈），重/慢的全量集成·E2E·性能放 nightly | DORA test-automation（dora.dev, 2025, T1）+ DEV Community CI/CD（2026, T2）+ Google SRE | T1 | high |
| EV-003 | 夜间定时跑全量大测试/长套件回归/安全扫描，捕获 PR 漏掉的回归 | GitHub Actions Nightly（2026, T2）+ GitLab（T2） | T2 | medium-high |
| EV-004 | 自动化评审 = 静态分析+lint+类型+安全扫描作必须状态检查；AI 评审做增量第一遍，但 AI 安全 TPR 仅 22%（IDOR），须与确定性校验并行 | Diffwise / Augment Code（2026, T3，含 Semgrep 数据） | T3 | medium（混合） |
| EV-005 | 持续测试文化；不容忍 flaky——Google ~16% 测试有 flakiness，浪费 2–16% 算力，需 quarantine | Google SRE/Testing（T1）+ JASST 学术（T2） | T1 | high |
| EV-006 | 失败必须告警（邮件/Slack/台账）；关键 schedule 用 service account 拥有，避免人员离职失效 | GitLab Scheduled Pipelines（T2） | T2 | medium-high |
| EV-L01 | `quality_gate.py` 已实现单项目五视角门禁（Architect/CodeReviewer 自动，其余待宿主 LLM），写 `台账/36_质量门记录.csv` | 本仓库源码（已读） | 内部 | high |
| EV-L02 | 现有 `check_traceability`/`check_version_consistency`/`check_skill_closure`/`check_deprecation_cleanup`/`lint_repo`/`desensitize`/`pre-commit-secret-scan` 组成可复用门禁集 | 本仓库源码 | 内部 | high |
| EV-L03 | 本仓库无 scheduler 工具，调度层需新建或借平台 CI | 本仓库源码（glob 验证） | 内部 | high |
| EV-007 | 无人值守审批必须异步+持久：推「待授权提案」入队列后退出，人日间处理；审批队列可从一张表起步，状态 pending/approved/executed/expired | metacto / AQ Score（2026, T3 实践指南） | T3 | medium |
| EV-008 | 定时任务不得指向需人工 reviewer 的 protected environment，否则夜间「Waiting」永久卡死；应指向无 required reviewers 的自动环境，人工审批留交互式 | GitHub Docs / tekton / Latchkey（2026, T1/T2 官方+实践） | T1 | high |
| EV-009 | 非工作时段低紧急告警入队延迟通知，工作时间 replay/page，不唤醒人（deferred paging） | Rootly / SolarWinds（2026, T2 实践） | T2 | medium-high |
| EV-010 | 应急旁路 break-glass 须 scoped/time-bound/audited，预授权 scope 仍需记录审查 | AWS Well-Architected / Safeguard（T1 官方） | T1 | high |
| EV-011 | 策略引擎风险分级路由：低风险自动、高风险入审批队列 | AQ Score（T3） | T3 | medium |

**真实外部信号（FULL 必需）**：dora.dev 官方测试自动化能力页、sre.google SRE Book「Testing Reliability」官方文档，均已联网读取核验。

---

## 4. 方案 v1（评审通过）

### 4.1 总体架构

```
                 ┌─────────────────────────────────────────────┐
   平台 CI 定时   │  Nightly Quality Gate Orchestrator           │
   (GitHub/GitLab │  1. 读取 projects_registry（项目清单）        │
   schedule cron) │  2. for each project:                        │
        │         │     - checkout / 进入路径                     │
        │         │     - quality_gate.py run --target <proj>    │
        │         │     - 跑测试命令（pytest -n auto --junitxml） │
        │         │     - 脱敏扫描（desensitize）                │
        │         │  3. 聚合 36_质量门记录.csv + nightly 汇总      │
        │         │  4. 失败 → 告警（邮件/Slack/台账）            │
        └────────►└─────────────────────────────────────────────┘
```

### 4.2 调度载体（DQ1 → 选 B）

采用**平台 CI scheduled pipeline**，不新建裸 crontab、暂不自建 scheduler 服务（对齐 EV-001 / EV-006 / EV-L03）。
- GitHub Actions：`on.schedule.cron`（如 `"0 19 * * *"` 本地时区晚 19 点）+ `workflow_dispatch` 手动触发。
- 关键 schedule 用 **service account / bot** 拥有，避免个人离职失效（EV-006）。
- 注意时区：GitHub cron 为 UTC，需换算；GitLab schedule 可设时区。
- 失败通知接入仓库告警渠道，无人看的 schedule 比没有更糟（EV-006）。

### 4.3 单项目评审引擎（DQ2 → 复用）

直接复用本仓库 `tools/quality_gate.py`（EV-L01）：
- `Architect` 视角：`check_version_consistency.py` + `check_skill_closure.py`
- `CodeReviewer` 视角：`check_skill_release_gate.py`
- `Security`/`Test`/`Performance` 视角：标记「待宿主 LLM」（host seam，ARCH-002）

外层仅需把多项目清单逐个作为 `--target` 传入，无需重写评审逻辑。

### 4.4 夜间执行内容（DQ3 → 分层）

依据测试金字塔（EV-002 / EV-003）：
- **每次 PR/提交**（不在本方案范围，既有 CI 负责）：快单测 + lint + 类型 + 安全扫描，反馈 <10min。
- **夜间（本方案）**：
  1. 自动门禁：`quality_gate` 的 Architect/CodeReviewer 自动视角 + 现有 `check_*` 全量。
  2. **单测全量套件**：`pytest -n auto --junitxml=reports/junit.xml`（或项目各自测试命令），捕获跨模块回归。
  3. **脱敏扫描**：串联 `desensitize.py` 对新增产物扫描（铁律 #8）。
  4. **AI 语义评审（三视角）**：默认**仅记录、非阻断**（见 4.6 硬约束）。

### 4.5 多项目枚举与凭据（DQ4 → registry）

新增 `projects_registry.csv`（UTF-8 BOM，入库）：
| 列 | 说明 | 是否脱敏 |
|----|------|----------|
| project_alias | 项目别名 | 否 |
| project_path | 本地绝对路径或仓库 URL | 路径用相对/`<project-path>` 占位；URL 脱敏为 `<repo-url>` |
| test_cmd | 测试命令（如 `pytest`） | 否 |
| secret_ref | 凭据别名（如 `GH_TOKEN_<alias>`） | 仅别名，真实值走 `.secrets/` |

- **A 级凭据**：真实 token 仅存 `.secrets/`，经 `tools/load_secret.py` 注入环境变量，registry 文件**不含明文**（铁律 #3）。
- 跨仓 URL 在文档/registry 中以 `<repo-url>` 别名呈现，不泄露内网主机（铁律 #8）。

### 4.6 夜间合并裁决（硬约束，吸收 CR-SEC-1）

> **门禁合并规则（写入未来门禁规范）**：
> - 合并决策仅取**自动视角（check_*）+ 单测结果**。
> - `Security`/`Test`/`Performance` 三视角（待宿主 LLM）**仅作为记录列，不参与阻断裁决**。
> - 理由：EV-004 显示 AI 安全 TPR 仅 22%，夜间无人值守时不宜作唯一/阻断裁决。
> - 单测失败或自动视角 FAIL → `CHANGES_REQUESTED`（或高严重度 `BLOCKED`）；全绿 → `SIGNED_OFF`。

### 4.7 失败处置与告警（DQ5，吸收 CR-SEC-3 / EV-006）

- 失败触发：生态告警（邮件 / Slack / Webhook）+ 落 `台账/36_质量门记录.csv`。
- **告警内容脱敏**（CR-SEC-3）：路径统一相对项目根，禁含主机名 / 绝对路径 / IP（B 级，铁律 #8）；报告按 MPV §6.2.4 路径相对根。
- flaky 治理（EV-005）：预留 quarantine 钩子，夜间全量失败时先自动重跑一次确认非 flaky，再告警；quarantine 清单入台账。

### 4.8 成本与可演进（吸收 CR-COST-1）

- 默认 `ENABLE_AI_REVIEW=false`：夜间不启用 opencode 强模型批量 AI 评审，控成本/时延。
- 启用需显式开关 `ENABLE_AI_REVIEW=true` + `AI_BUDGET`（如 token/时长上限），且仍**非阻断**。
- 大仓算力优化预留「受影响测试选择（RTS）」钩子（EV-002 Google），本仓库规模非瓶颈。
- 平台调度与 `quality_gate` 模块化，迁移 GitLab/GitHub 或扩展视角低成本。

---

## 4.9 夜间人工授权与跳过机制（Decision Backlog）

> 目标：夜间流程**绝不因等待人工授权而中断**；任何需裁决项「跳过并登记」入待决策队列，日间由人工 replay 决策，保证整体任务完成。

### 4.9.1 设计原则（行业依据）
- **异步 + 持久审批**：无人值守场景下，审批必须是异步、持久的——把「待授权提案」推入队列后退出，人在数小时后处理（EV-007）。同步审批在夜间会「Waiting」永久卡死（EV-008）。
- **不阻断整体**：需授权项不执行副作用，仅记录；编排器单项目故障/需授权不影响其余项目（EV-009 deferred paging 思路）。
- **脱敏登记**：队列与告警内容相对路径、禁主机名/IP（铁律 #8）。

### 4.9.2 需授权触发分类（precondition，代码级策略引擎）
| 类别 | 触发条件 | 夜间行为 |
|------|----------|----------|
| 凭据缺失/失效 | registry 中 `secret_ref` 无法经 `load_secret` 解析 | 跳过该项目，记 pending |
| 高严重度阻断发现 | 自动视角 FAIL 且严重度=high（如废弃资产残留、版本不一致） | 不阻断整体，记 pending + 告警 |
| AI 语义高置信阻断 | Security/Test/Performance 视角高置信建议（仅记录，本就不阻断，见 §4.6） | 记入待决策供日间研判 |
| 受保护环境变更 | 涉及生产/对外副作用（发通知、改数据、PR 合并） | 夜间禁止自动执行，仅提案入队 |
| 规则不确定 | 命中豁免边界模糊项 | 记 pending，默认保守跳过 |

### 4.9.3 跳过并登记（Skip-and-Flag）
编排器对每个项目 `try/except` 隔离：
- 单项目异常/缺凭据/需授权 → `catch` 后写一条 `pending` 待决策，继续下一项目；
- 整体运行「成功完成（含 N 项跳过）」，退出码 0（跳过项不计入失败）；
- 仅当「全部项目均因致命错误无法启动」（如调度器自身故障）才非零退出。

### 4.9.4 待决策事项队列（Decision Backlog）
新增 `台账/37_待决策事项.csv`（UTF-8 BOM）：
| 列 | 说明 |
|----|------|
| decision_id | DB-YYYYMMDD-NNN |
| time | 提出时间（夜间） |
| project_alias | 项目别名（脱敏） |
| category | 4.9.2 类别 |
| payload | 待授权内容摘要（相对路径/动作描述，禁绝对路径/IP） |
| rationale | 为何需授权 + 风险评级 |
| status | pending / approved / rejected / expired |
| expires_at | 过期时间（默认 +12h 隔夜晨会；长待办 +72h） |
| daytime_decision | 日间决策记录（approve/reject/edit+approve/escalate） |
| approver | 日间审批人 |
| rollback | 回滚/补救方法 |

状态机：`pending → approved → executed` / `pending → rejected` / `pending → expired`（过期等同 rejected，可重排队列，不静默丢弃，EV-007）。

### 4.9.5 日间 replay 与决策处理
- 日间工作流（或人工）读取 `status=pending` 项，按 `category` 路由审批人；
- 批准的副作用动作由**独立执行器**执行（审批 UI 不直接执行，EV-007 防陷阱），带幂等键；
- `expired` 项在窗口结束前若仍 active，工作时间自动 replay 提醒（EV-009）；
- 所有决策入审计（谁、何时、依据）。

### 4.9.6 优化建议闭环（减少未来人工干预）
每次日间处理同步产出**优化建议**，反哺夜间降人工：
- 重复出现的「凭据缺失」→ 补 `.secrets/` + registry 别名，夜间自愈；
- 重复「高严重度阻断」→ 评估加白名单/豁免规则或修复根因；
- 重复「AI 高置信误报」→ 调阈值/忽略路径；
- flaky 项 → quarantine（EV-005）。
优化建议登记入 `台账/37_待决策事项.csv` 的 `optimization` 列或独立 `台账/38_优化建议.csv`，周回顾。

### 4.9.7 应急旁路（break-glass，兜底）
- 夜间确需紧急越权：提供**预授权 scope**（read-only / 非生产，EV-010），仍需记录+审查；
- break-glass 触发告警通知责任人，时限到期自动失效（time-bound）；
- 严禁夜间默认指向需 reviewer 的 protected environment（EV-008 教训）。

### 4.9.8 与 CI 调度对接
- 定时 workflow 指向**无 required reviewers** 的自动环境（如 `nightly` environment），人工审批仅留给交互式 `workflow_dispatch`（EV-008）；
- 需审批的部署/副作用步骤从 nightly 剥离，改由日间人工触发。

---

## 5. 多视角评审报告（Review 阶段产物）

> 声明：本库语境下为多视角自评（非真实第三方）；FULL 已含真实外部信号（dora.dev / sre.google 官方）。

| 视角 | 状态 | 关键发现 |
|------|------|----------|
| 架构一致性（Architect） | ✅ PASS | 复用 `quality_gate --target` 契合；数据追加无冲突；调度解耦 |
| 安全合规（SecurityReviewer） | ✅ PASS（带硬约束） | A 级凭据走 `.secrets`；AI 不作阻断裁决；脱敏串联合规 |
| 成本+可演进（Cost/Evolution） | ✅ PASS | 平台免费额度覆盖；可演进；默认关闭 AI 评审控成本 |

**聚合决策**：CHANGES_REQUESTED（5 条 CR，无 ERROR / 无硬 FAIL）→ 吸收后 **SIGNED_OFF（条件）**。

### CR 处理状态（Converge）

| ID | 严重度 | 内容 | 状态 |
|----|--------|------|------|
| CR-SEC-1 | 高 | 夜间合并裁决仅取自动视角+单测；AI 语义三视角仅记录非阻断 | **closed**（已写入 §4.6 硬约束） |
| CR-SEC-2 | 中 | registry 仅存路径/别名，token 经 `load_secret` 注入禁入库 | **closed**（已写入 §4.5） |
| CR-SEC-3 | 中 | 告警/报告脱敏（相对路径，禁主机名/IP） | **closed**（已写入 §4.7） |
| CR-ARC-1 | 中 | 定义外层编排器接口（循环 registry→quality_gate+pytest→聚合） | **closed**（已写入 §4.1/§4.3） |
| CR-COST-1 | 中 | 默认关闭强模型批量 AI 评审，启用需开关+预算上限 | **closed**（已写入 §4.8） |

---

## 6. ADR 草案

- **标识**：ADR-xxx（交 role-architecture 正式编号）
- **决策**：采用「平台 CI 定时流水线 + 复用 `quality_gate` + 单测全量 + 失败告警」，不新建裸 crontab 调度、暂不自建 scheduler
- **决策点 B（本补充）**：引入夜间「Decision Backlog 待决策队列 + Skip-and-Flag 跳过机制 + 日间 replay」，确保需授权项不阻断夜间整体；审批必须异步持久，定时任务避开 reviewer-gated environment
- **选项**：A 裸 crontab / B 平台 CI schedule（选） / C 自建 scheduler 服务（均含「维持现状」基线）
- **理由**：B 具备日志·重试·审计·告警，运维可见性最优（EV-001/006）；复用 `quality_gate` 免重复（EV-L01）
- **已验证**：DORA（dora.dev）、Google SRE（sre.google）、GitLab/GitHub Actions 官方实践（联网已读）
- **不确定**：夜间 AI 语义评审最终形态、多项目 registry 物理结构
- **未关闭风险**：AI 视角夜间裁决可靠性（已用 §4.6 硬约束降为仅记录，非阻断）；跨仓凭据安全（已用 §4.5 别名+`.secrets` 降风险）
- **反信号**：若项目无 CI 平台托管，则回退到 B 的 self-hosted runner + 受管 service account

---

## 7. 暂不落地 — 未来实施检查清单

> 以下条件达成后可另起实施任务，逐项落地（每项独立提交 + 门禁）：

1. [ ] 新建 `projects_registry.csv`（仅别名/路径占位/测试命令/凭据别名），并验证 `.secrets/` 注入链路。
2. [ ] 新建 `tools/nightly_quality_gate.py`：循环 registry → `quality_gate run --target` + 测试命令 → 聚合 `36_质量门记录.csv` → 告警；实现 §4.6 合并裁决与 §4.7 脱敏。
3. [ ] 新增 `.github/workflows/nightly-quality-gate.yml`：`schedule.cron` + `workflow_dispatch`，用 service account / bot 拥有。
4. [ ] 接入失败告警渠道（邮件/Slack/Webhook），验证通知内容脱敏。
5. [ ] flaky quarantine 钩子与重跑确认逻辑。
6. [ ] 新增 `台账/37_待决策事项.csv` + 编排器 Skip-and-Flag（单项目 try/except、pending 登记、整体不阻断）。
7. [ ] 日间 replay 工作流：读取 pending → 路由审批 → 独立执行器执行（幂等）→ 审计；优化建议登记 `台账/38_优化建议.csv`。
8. [ ] （可选）`ENABLE_AI_REVIEW=true` + `AI_BUDGET` 开关与监控。
9. [ ] 落 `role-architecture` 正式 ADR 编号与追溯矩阵登记。

---

## 8. 风险与未关闭项

- **高**：AI 语义三视角夜间可靠性 —— 已用「仅记录、非阻断」硬约束化解，非阻塞。
- **中**：跨仓凭据安全 —— 已用 registry 别名 + `.secrets/` + `load_secret` 化解。
- **中**：大仓算力成本 —— 本仓库规模非瓶颈，RTS 钩子预留。
- **中**：待决策事项积压 —— 若日间未及时处理，pending 累积；缓解：expires_at + 晨会 replay + 周回顾优化建议闭环（§4.9）。
- **INSUFFICIENT 占比**：0%（关键结论均有 T1/T2 来源或本仓库源码验证），不触发阻塞。

---

*文档版本 v1.0 · 由 best-practice-solution（FULL）+ multi-perspective-validation 协作产出 · 知识产权所有：段波（duanbo.douglas@163.com）*
