---
name: "schedule-cost"
description: "用户提到进度基准/成本基准/里程碑更新/挣值分析/EVM/PV·EV·AC/CPI/SPI/CV·SV/进度绩效/成本绩效/进度滞后/成本超支/里程碑准点率/进度成本复盘/工期偏差/预算燃尽/S曲线/偏差纠偏时加载本进度成本管理技能：负责进度基准（阶段划分+里程碑+任务拆解）与成本基准（工时预估+成本阈值+超支标准）建立、里程碑与成本更新、EVM 挣值分析（PV/EV/AC/CPI/SPI/CV/SV+准点率）、进度滞后·成本超支预警、周期性进度成本复盘与偏差纠偏。内化 dev-project-mgmt EVM 能力为本地权威工具，可脱离编排器独立部署运行。不加载：风险登记与应对（→risk-mgmt）、资源容量规划（→resource-ops）、WBS 方案分解（→plan-creation）。"
---

# schedule-cost 进度成本管理技能

> 版权：`../shared/references/COPYRIGHT.md` Token：`../shared/references/token_standard.md`
> 标准：`references/evm_standard.md`（进度成本挣值管理标准）v1.0.0
> 权威工具：`tools/evm_ops.py` v1.0.0（内化自 dev-project-mgmt `evm_calculator.py`，数据源改台账 CSV）

## 1. 元数据

- **技能版本**：v1.0.0 **发布日期**：2026-09-08
- **变更记录**：
  - v1.0.0：首个**可独立部署**进度成本管理技能版本。按 D2 内化决策，将原委派 dev-project-mgmt `evm_calculator.py`（SQLite）的 EVM 能力吸收为本地权威工具 `evm_ops.py`（台账 CSV 数据源），并从 `role-governance/domain/progress-cost.md` 抽出升级为自包含技能；EVM 指标公式（PV/EV/AC/CPI/SPI/CV/SV/准点率）与 dev-project-mgmt 保持一致（里程碑 0/100 挣值规则）；对齐 `evm_standard.md` v1.0.0。
- **参考标准**：PMBOK 7th（进度/成本绩效域）· PMBOK 6（控制进度/控制成本过程）· EVM 挣值管理（ANSI/EIA-748）· ISO 21500 · PRINCE2（阶段边界评审）· 关键路径法 CPM
- **定位**：进度与成本受控绩效的**单一权威实现层**——把「计划投多少（进度/成本基准 PV）」与「实际挣了多少、花了多少（EV/AC + CPI/SPI）」固化为可自动执行、可预警、可独立部署的工具化能力。

## 2. 触发规则

用户表达「建进度基准 / 建成本基准 / 更新里程碑 / 记录工时成本 / 算挣值 EVM / 看 CPI SPI / 检测进度滞后成本超支 / 出进度成本复盘」时加载本技能。先 Read 本路由表，命中后只读对应 `domain/*.md`。

| 环节 | action | 明细 | 主命令 |
|------|--------|------|--------|
| 进度成本基准 | schedule_cost_baseline | `domain/baseline.md`（阶段划分 / 里程碑清单 / 任务拆解 / 工时预估 / 成本阈值 / 超支标准 / BAC） | `add-milestone` |
| 里程碑与挣值 | milestone_evm | `domain/milestone-evm.md`（里程碑状态·完成率更新 / 工时成本记录 / PV·EV·AC / CPI·SPI·CV·SV / 准点率 / 健康判定） | `calc` · `update-milestone` · `status` |
| 周期复盘纠偏 | schedule_cost_review | `domain/review.md`（阶段·里程碑复盘 / EVM 偏差分析 / 滞后超支预警 / 纠偏方案 / 连续延期人工决策） | `calc --json` · `status` |

## 3. 与现有角色/技能的边界（单一信源 + 瘦引用）

| 载体 | 关系 | 说明 |
|------|------|------|
| **schedule-cost（本技能）** | **权威实现** | 进度成本基准/里程碑更新/EVM 挣值分析的**唯一逻辑来源**，工具 `evm_ops.py` v1.0.0 |
| `role-governance/domain/progress-cost.md` | 瘦引用 | 保留总控角色的路由与触发，EVM/进度成本逻辑**委派**本技能，不复制实现细节（AC8 委派标记） |
| `role-project-mgmt`（项目经理执行层） | 协同 | 日常进度/成本管控调用本技能工具；RAID 风险联动走 `risk-mgmt` 技能 |
| dev-project-mgmt `evm_calculator.py` | 被内化（保留兼容） | EVM 公式已吸收为本地 `evm_ops.py`（新权威）；dev-project-mgmt 保留供其他项目/CLI 兼容，不强制退役 |
| MCP `evm_analyze` | 委派 | `tools/mcp_server/skills_mcp_server.py` 以 subprocess 调用本地 `evm_ops.py`（B-7 由 `_run_mgmt_cli` 委派改本地），逻辑单一信源在本技能 |

> **铁律**：进度成本/EVM 逻辑只此一处实现（DRY）。角色包/MCP/文档一律**引用或委派**，禁止复制粘贴导致漂移。

## 4. 工具调用（CLI）

权威工具 `tools/evm_ops.py`（Python3，零第三方依赖）。工具经 `PROJECT_ROOT` 环境变量解析目标项目根，无论脚本副本位于何处，读写的都是目标项目的 `台账/`（03/04/09/10）。

```bash
python3 tools/evm_ops.py add-milestone --id M1 --name "需求基线" [--start 2026-09-01] [--end 2026-09-30] [--value 1000]
python3 tools/evm_ops.py update-milestone --id M1 [--status 已完成] [--actual-end 2026-09-28] [--completion 100]
python3 tools/evm_ops.py calc [--milestone M1] [--json]
python3 tools/evm_ops.py status
```

**台账数据源**（读写目标项目 `台账/`，防御式列名别名兼容各项目 schema 差异）：
- `03_进度基准.csv`（阶段/里程碑/计划日期）· `04_成本基准.csv`（成本阈值=BAC/预估工时）
- `09_进度跟踪台账.csv`（里程碑状态/完成率/计划·实际日期，EV/PV 主源）· `10_成本消耗台账.csv`（累计消耗/资源成本，AC 主源）

**EVM 指标**（公式与 dev-project-mgmt 一致，详见 `references/evm_standard.md`）：PV=Σ里程碑计划值；EV=Σ已完成里程碑计划值（0/100 规则）；AC=台账实际成本（缺失回退时间进度比估算）；CPI=EV/AC；SPI=EV/PV；CV=EV−AC；SV=EV−PV；准点率=准点完成数/总数。

**退出码约定**：`0`=成功/无数据友好提示；`1`=参数非法（重复里程碑 ID / 里程碑不存在）。

## 5. 核心原则

1. **基准权威**：进度/成本绩效以固化的基准（03/04）为唯一比对标准；禁止以「实际发生」逆向修正基准。
2. **挣值驱动**：以 CPI/SPI 量化绩效，CPI<1 成本超支、SPI<1 进度滞后，双维健康判定。
3. **单一信源**：EVM 逻辑只此一处（`evm_ops.py`）；MCP/角色包委派，禁止复制公式导致漂移。
4. **里程碑 0/100**：EV 采里程碑完成即计全额计划值、未完成计 0（与 dev-project-mgmt 一致），避免主观百分比挣值。
5. **预警前置**：任务滞后/成本超阈值自动生成预警；连续 2 次延期/超支停止 AI 自动调整计划，推送人工决策。
6. **准点率留痕**：里程碑准点判定（实际完成日 ≤ 计划完成日）纳入绩效，责任到人。

## 6. 输出规范

- 基准类：`add-milestone` → 追加 `09_进度跟踪台账.csv`（里程碑编号/计划值/计划日期/状态）。
- 更新类：`update-milestone` → 整表重写 `09`（状态/实际完成日/完成率），已完成自动补实际完成日。
- 绩效类：`calc` → PV/EV/AC/CPI/SPI/CV/SV/准点率 + 健康判定 + 滞后超支预警；`calc --json` 供 MCP/PMO 消费。
- 状态类：`status` → 全里程碑状态清单 + EVM 概览。
- 边界：仅进度成本绩效域；不产出范围基准（归 scope-tracking）、不产出风险 RAID（归 risk-mgmt）、不产出资源平衡（归 resource-ops）。

## 7. 独立部署与镜像同步

本技能为**自包含可独立部署技能**：权威工具/测试保留在仓库根 `tools/`·`tests/`（单一信源），`skill.manifest.json` 声明打包/部署期需注入的副本（`evm_ops.py`/`test_evm_ops.py`）。`package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 按 manifest 注入后，产物（zip / 部署目录）内含 `SKILL.md + domain/ + skill.manifest.json + tools/ + tests/ + references/`，脱离编排器即可 `python3 tools/evm_ops.py ...` 直接运行。

**分发清单（STANDALONE_SKILLS）**：本技能已登记为 `package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 的 `STANDALONE_SKILLS`（独立于 11 个 `ALL_ROLES` 角色包），因此：
- **全量同步（无参）自动纳入**：`package_skills.py`（无 `--role`）产出自包含 zip；`deploy_skills.py` / `deploy_skills.sh`（无 `--roles`）全量部署到 4 个镜像目标时一并同步本技能（角色专用门禁校验器 `check_*` 仍只遍历 `ALL_ROLES`，语义不污染）。
- **按需单独分发**：`package_skills.py --role schedule-cost` → `dist/schedule-cost_v1.0.0.zip`；`deploy_skills.py --roles schedule-cost`。

**镜像目标**（单一信源 `.trae/skills/schedule-cost/` → 只读镜像，永不反写源）：`.github/skills/` · `.claude/skills/` · `.agents/skills/` · 全局 opencode 库。每个镜像内 `schedule-cost/` 均自包含（含注入的 `tools/`+`tests/`），可整目录拷走独立运行。

**脱离本库运行**：解压 zip 或拷走镜像内 `schedule-cost/` 目录，`cd` 到目标项目根（含 `台账/`），`python3 <目录>/tools/evm_ops.py calc`；自包含验证：`python3 <目录>/tests/test_evm_ops.py`（测试用 `ROOT=dirname(dirname(__file__))` 解析包内 `tools/`）。

> **同步命令**：改动本技能或权威工具后，运行 `python3 tools/package_skills.py`（重建 dist zip）+ `python3 tools/deploy_skills.py`（刷新 4 镜像）即可；二者对本技能均按 manifest 注入自包含副本，无需手工拷贝。

---

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求建进度/成本基准、更新里程碑、记录工时成本、算 EVM 挣值、看 CPI/SPI、检测滞后超支、出进度成本复盘；
- 前置：目标项目已有阶段/里程碑规划（或先 `add-milestone` 建骨架）；`台账/09_进度跟踪台账.csv` 为 EV/PV 主源、`10_成本消耗台账.csv` 为 AC 主源；
- 不适用：范围基准与变更（归 scope-tracking）、风险 RAID（归 risk-mgmt）、资源容量平衡（归 resource-ops）、质量缺陷（归 role-testing）。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | 进度/成本基准目标已明确 | 里程碑已登记 | `add-milestone` 建 09 台账骨架 + 计划值 |
| 执行中 | 开始更新里程碑/记录成本 | 绩效指标已产出 | 按 domain 明细调用 update-milestone/calc/status |
| 校验中 | EVM 已计算 | 健康判定完成 | CPI/SPI 双维健康判定 + 滞后超支预警裁决 |
| 阻塞 | 09/10 台账缺失或里程碑不存在 | 补齐台账输入 | 暂停并列出缺失清单，calc 友好提示（rc0） |
| 完成 | 绩效健康或偏差已纠偏 | 交付进度成本复盘 | `calc --json` 出结构化绩效，结论留痕 |
| 回退 | 检出严重偏差（CPI/SPI<0.9） | 回到合规基准或重规划 | 记偏差/预警，连续 2 次延期推送人工决策 |

### 3. 执行动作层
- 执行步骤 1：`add-milestone` 登记里程碑（编号/名称/计划开始·完成日/计划值 PV）到 09 台账；
- 执行步骤 2：`update-milestone` 更新里程碑状态/实际完成日/完成率（已完成自动补实际完成日）；
- 执行步骤 3：`calc` 计算 PV/EV/AC/CPI/SPI/CV/SV/准点率 + 健康判定（AC 优先取 10 台账累计消耗，缺失回退时间进度比估算）；
- 执行步骤 4：`status` 查看全部里程碑状态 + EVM 概览；`calc --json` 供 MCP `evm_analyze`/PMO 仪表盘消费；
- 所需输入：里程碑参数（编号/计划值/计划日期）/ 状态更新 / 成本消耗台账；
- 输入输出约束：里程碑 ID 不重复；EV 采 0/100 规则；CPI/SPI 公式与 dev-project-mgmt 一致；预警必须留痕。

### 4. 验收门禁
- 必须产出物：进度/成本基准（03/04）、里程碑台账（09）、成本消耗台账（10）、EVM 绩效卡（PV/EV/AC/CPI/SPI/CV/SV/准点率）；
- 通过条件：里程碑已登记且计划值明确、EVM 指标可计算、健康判定为「健康」或偏差已有纠偏方案；
- 失败条件：09/10 台账缺失致指标不可算、CPI/SPI 严重偏差（<0.9）无纠偏、连续 2 次延期/超支未推送人工决策；
- 审核对象：总控保障角色（role-governance）+ 项目经理（role-project-mgmt）。

### 5. 失败处理
- 失败类型：里程碑台账缺失/为空、里程碑 ID 重复或不存在、成本台账缺失致 AC 回退估算、CPI/SPI 严重偏差；
- 恢复策略：补里程碑/补成本台账后重算；AC 台账缺失时以时间进度比估算并标注 `ac_source`；严重偏差转纠偏方案；
- 是否需要人工确认：连续 2 次延期/超支停止 AI 自动调整计划，强制推送人工决策；基准调整须走变更审批（委派 scope-tracking 变更生命周期）。

### 6. 产出与交接
- 产出物列表：`09_进度跟踪台账.csv`、`10_成本消耗台账.csv`、EVM 绩效卡（`calc`/`calc --json`）、进度成本复盘报告；
- 交接对象：role-governance（阶段评审门禁 EVM 口径）、role-project-mgmt（日常进度成本管控）、MCP `evm_analyze`（PMO 仪表盘）、role-program-mgmt（跨项目 CPI/SPI/准点率统一度量口径）；
- 下一步动作：绩效健康 → 允许阶段流转；偏差 → 转纠偏并限期复核。

### 7. 审计记录
- 执行时间：add-milestone/update-milestone/calc 的时间点（09 台账 `更新日期`）；
- 关键参数：里程碑计划值 PV、计划·实际完成日、完成率、BAC（成本阈值）、AC 来源（台账/时间估算）；
- 关键决策：健康判定（健康/轻度偏差/严重偏差）、滞后超支预警、连续延期人工决策推送；
- 结果证据：09 进度跟踪台账、10 成本消耗台账、`calc --json` EVM 绩效输出。

---

**文档版本**：v1.0.0 **最后更新**：2026-09-08（首个独立可部署进度成本管理技能；内化 dev-project-mgmt evm_calculator 为本地权威工具 evm_ops.py v1.0.0，数据源改台账 CSV，EVM 公式与 dev-project-mgmt 一致；对齐 evm_standard.md v1.0.0；已登记 SKILL_INDEX 条目29 + package/deploy 的 STANDALONE_SKILLS 全量同步清单，§7 补镜像同步说明）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
