---
name: "project-init-skill"
description: "Project initiation skill covering startup foundations: charter & business case, stakeholder registration, scope preliminary definition, feasibility check, kickoff readiness, and baseline initialization (ProjectMonitorSkill create_baseline) before requirements phase. Aligned with PMBOK initiating process group. Invoke when starting a new project, creating project charter, registering stakeholders, or initializing project baseline."
---

# ProjectInitSkill 项目启动技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能唯一标识**：ProjectInitSkill
- **技能版本**：v21.2.1
- **定位**：项目启动前置哨兵（Front-Gate），是六阶段全生命周期的「第 0 阶段」，对齐 PMBOK 启动过程组。
- **调用主体**：DevProjectTeamSkill（标准模式入口）/ 用户直接指令
- **依赖工具**：ProjectMonitorSkill（`create_baseline` 台账初始化、`change_audit` 变更审计）
- **核心约束**：
  1. 启动完成后必须调用 ProjectMonitorSkill `create_baseline` 生成台账基线，未初始化禁止进入需求阶段；
  2. 项目章程未经干系人确认，禁止固化范围初定义；
  3. 本技能只做启动准备与决策，需求收集由需求分析师接续执行；
  4. 启动决策为「Go / No-Go / 暂缓」，未批准不消耗开发资源。

---

## 2. 统一入参标准

统一入参：`action`（七指令之一）+ `content`（背景/章程/干系人/范围/可行性/就绪/基线信息）+ `stage`（当前环节）+ `user_confirm`（无/同意/拒绝/查错）。

#### action 指令清单

| action | 作用 | 前置条件 |
|--------|------|----------|
| `init_kickoff` | 启动登记 | 无 |
| `create_charter` | 输出项目章程 | init_kickoff |
| `register_stakeholder` | 干系人登记册 | create_charter |
| `define_scope_prelim` | 范围初定义 | register_stakeholder |
| `init_tailor` | 阶段/活动裁剪决策 | define_scope_prelim |
| `register_env_asset` | 环境资产注册与冲突预检（25_环境资源清单.csv） | init_tailor |
| `assess_feasibility` | 五维可行性评估 | register_env_asset |
| `check_ready` | 就绪检查（Go 判定） | assess_feasibility |
| `init_baseline` | create_baseline 初始化台账 | check_ready=Go |

---

## 3. 项目启动流程

流程主线：`init_kickoff → create_charter → register_stakeholder → define_scope_prelim → init_tailor → register_env_asset → assess_feasibility → check_ready → (Go) → init_baseline → 需求阶段入场`；No-Go/暂缓 → 阻塞清单 + 建议行动，停止。

- **门禁**：每环节产出经用户确认后进入下一环节；
- **刹车**：章程确认连续 2 次未通过 → 停止并推送人工决策；
- **No-Go 后重启**：阻塞消除后从对应环节恢复，不需从头重跑。

### 环节 1：启动登记（init_kickoff）
处理：生成项目编号（PRJ-XXX）与名称；登记 SMART 目标、背景、预期收益；判定项目类型，联动 RequirementsAnalysisSkill dimensions。
输出：项目登记记录（写入台账「01_启动组.csv」候选行）。

### 环节 2：项目章程（create_charter）
处理：章程含立项授权、目标（业务+交付）、约束、预算上限、关键里程碑；须经干系人确认；目标不清晰时输出「章程缺陷清单」，不强行通过。
输出：《项目章程》（Markdown 或 CSV），经干系人确认。

### 环节 3：干系人登记（register_stakeholder）
处理：登记册字段（角色/组织/影响/参与度/沟通需求/频率/联系方式）；**权力-利益矩阵**四象限（高权高利→重点管理、高权低利→使其满意、低权高利→保持知会、低权低利→监督）；识别项目经理/需求方/测试方；变更增量更新不重写整册。
输出：《干系人登记册》（写入「01_启动组.csv」）。

### 环节 4：范围初定义（define_scope_prelim）
处理：输出交付边界（做什么）、排除项（不做什么）、假设与制约；范围为「初步」，细则由需求阶段细化；变更走 ProjectMonitorSkill `change_audit`。
输出：《范围初定义说明书》（范围/排除项/假设/制约），写入「02_范围基准.csv」。

### 环节 5：阶段/活动裁剪（init_tailor）
处理：依据项目特点（范围/类型/资源/团队分工/合规要求）裁剪本项目生命周期阶段与阶段内活动，输出裁剪配置并写入台账「00_阶段配置.csv」。

**裁剪规则**：
- **强制保留**：第 0 阶段（项目启动）与总控保障（role-governance）不可裁剪——裁剪决策在启动阶段作出，评审/门禁/台账/基线固化由总控贯穿全周期；
- **可裁剪阶段**（默认按全生命周期，依据项目特点逐项确认）：需求 / 架构 / 开发 / 测试 / 投产，任一阶段可整体裁剪（如「纯外包开发+内部测试」项目可裁掉开发阶段）；
- **活动级裁剪**：保留阶段内的活动可进一步裁剪（如裁剪架构阶段中的 ADR/ATAM、投产中的金丝雀发布/DORA 指标），裁剪项须记录原因与责任方；
- **裁剪确认**：裁剪配置须经用户逐项确认（保留/裁剪/理由），未确认不得生效；裁剪后项目仅执行保留阶段，编排器据此调度（见 dev-project-team-skill §5）。

输出：《阶段配置单》（00_阶段配置.csv：阶段/保留或裁剪/裁剪理由/责任方），由 role-governance 写入台账。

**敏捷迭代模式扩展（可选）**：若项目采用敏捷迭代/快速上线，`init_tailor` 额外产出 `18_迭代配置.csv`（由 role-governance 写入台账）：

| 列 | 说明 |
|----|------|
| 迭代编号 | IT-01、IT-02… |
| 周期（天） | 5~10（1~2 周） |
| 吸收容量 | 迭代承诺规模 = 上期 Velocity × 可用人日（容量规划，P0-1） |
| MVP 范围 | 本迭代吸收的 PBI 清单（MoSCoW 优先，S/M/L 规模估算） |
| 技术债登记 | 技术债登记 + 偿还迭代计划（每 N 迭代 ~20% 容量，P1-2） |
| DoR / DoD | 进入迭代前置条件 / 完成标准（缺陷关闭+文档+预生产/金丝雀+冒烟，P1-3） |
| 发布点 | Y/N，仅 Y 触发发布级强门禁 |
| 角色包范围 | 本迭代启用的角色包（通常需求+开发+测试，可选部署） |

迭代模式下保留阶段通常为需求+开发+测试（+备选投产），架构随迭代演进（P1-4：首迭代可选、每发布点 ADR 评审），测试左移（P1-6：开发内联单测+迭代级集成测试，发布点才全量回归）。

### 环节 6：环境资产注册（register_env_asset，多项目共享环境必做）

处理：**多项目共享一台服务器时**，在项目启动阶段即登记本项目所需独占资源（端口/容器/Docker 容器名前缀/数据库/大模型运行目标），写入跨项目共享的 `台账/25_环境资源清单.csv`，并做冲突预检（先注册先得 + 冲突人工升阶，详见 `../../references/multi_project_isolation.md` §10）：

- **登记范围**：本项目规划占用的端口、Docker compose 项目名/容器名（带项目前缀）、数据库实例名、大模型运行目标（本地轻量档或云端别名）；
- **冲突预检**：查询 `25_环境资源清单.csv`，资源标识命中「已占用」即冲突；独占资源（大模型容器/GPU/Docker 单一运行时/固定端口）冲突自动升阶 `change_audit` 留痕并交用户决策（等待释放/抢占授权/换资源）；
- **单机独占约束**：一台服务器同一时间仅一个生成模型驻留（`OLLAMA_MAX_LOADED_MODELS=1`）、仅一个 Docker daemon 单实例；本地工具/脚本缺省运行目标 = 本地轻量模型档（`model_selection.md` §7.1）；
- **未注册不放行**：资源未全部登记或存在未裁决冲突，不得进入后续可行性评估。

输出：`台账/25_环境资源清单.csv` 登记/仲裁结果 + 冲突预检清单。

> 单项目独立开发机（无共享冲突风险）可跳过本环节，按需登记即可。

### 环节 7：可行性评估（assess_feasibility）
五维矩阵，任一项"不可行"则 No-Go：

| 维度 | 通过标准 |
|------|---------|
| 技术可行性 | 无不可逾越障碍 |
| 资源可行性 | 资源缺口可填补 |
| 进度可行性 | 排期无硬性冲突 |
| 成本可行性 | 成本 ≤ 预算上限 |
| 风险可行性 | 风险可控或可接受 |

输出：《可行性评估报告》（五维结论 + Go/No-Go 建议）。

### 环节 8：启动就绪检查（check_ready）
处理：Gate 清单——章程确认 / 干系人登记（含权力-利益分析）/ 范围初定义 / 裁剪配置确认 / **环境资产已注册且无未裁决冲突（`25_环境资源清单.csv`）** / 可行性通过 / 预算里程碑明确 / 需求入场条件识别。判定 **Go**（全过）/ **No-Go**（任一不满足且无法调整）/ **暂缓**（条件暂缺，补足重查）；No-Go/暂缓输出阻塞清单与建议行动。
输出：《启动就绪检查单》（Go/No-Go/暂缓 + 阻塞清单）。

### 环节 9：基线初始化（init_baseline）
处理：调用 ProjectMonitorSkill `create_baseline` 创建全套台账（20+ 个 CSV，含「00_阶段配置」「18_迭代配置」「19_迭代回顾」）；启动产物写入对应 CSV（「01_启动组」编号/目标/相关方/沟通、「02_范围基准」范围/边界/禁止项、「03_进度基准」初步里程碑、「04_成本基准」预算/阈值、「00_阶段配置」阶段/活动裁剪清单、「18_迭代配置」敏捷迭代配置、「12_风险问题台账」初始风险登记册、「25_环境资源清单」已登记资源快照）；依据裁剪配置确定后续保留阶段，固化后输出《项目启动完成报告》，移交首个保留阶段入场。
输出：`台账/`（20+ 个 CSV，已初始化）+《项目启动完成报告》。

---

## 4. 触发规则

- 用户启动新项目（"启动一个项目"、"开始一个新项目"）；需求分析前的初始化准备；项目基线创建/干系人变动；**裁剪生命周期阶段/活动**（"只要需求+测试阶段"、"裁掉开发阶段"）；**开启敏捷迭代/快速上线**（"用敏捷/迭代/快速上线"）。

---

## 5. 输出规范

- 每环节产出须经用户确认后方可进入下一环节；
- 启动就绪后必须初始化台账基线，未初始化禁止进入需求分析阶段；
- 台账（20+ 个 CSV）读写由 ProjectMonitorSkill `create_baseline` 执行，本技能只做启动准备与决策；范围/基线变更经 `change_audit` 审计。

---

## 6. 边界（安全铁律）

1. **基线铁律**：未经 `create_baseline` 初始化，禁止进入需求分析阶段；
2. **章程铁律**：章程未经干系人确认，禁止固化范围初定义；
3. **决策铁律**：No-Go/暂缓必须停止推进并输出阻塞清单，不得强行开工；
4. **边界铁律**：不做需求细化、架构设计、写代码——范围初定义不等于需求规格说明书；
5. **权限铁律**：范围/基线变更经 ProjectMonitorSkill 审计。

**禁用**：需求收集与规格编写（由 RequirementsAnalysisSkill 执行）；架构/开发/测试/部署等后续阶段；跳过就绪检查直接固化基线。

**技能关系**：DevProjectTeamSkill=第 0 阶段入口；ProjectMonitorSkill=台账读写与变更审计；RequirementsAnalysisSkill=启动→需求衔接；SkillAuthoringSkill=无业务依赖。

---

> 协作接口详见各宿主技能元数据及 `../../shared/references/api_contracts.md`；目录规范详见 `../../shared/references/directory_structure.md`

---

**文档版本**：v21.2.2（新增 register_env_asset 环境资产注册环节 + check_ready 冲突预检门禁 + 25_环境资源清单.csv，2026-08-14）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）