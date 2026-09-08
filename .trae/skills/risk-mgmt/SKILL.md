---
name: "risk-mgmt"
description: "用户提到风险登记册/风险巡检/风险扫描/RAID/风险等级/概率影响/风险应对/规避减轻转移接受/问题升级/P1P2P3P4/假设/依赖/风险协同/风险台账时加载本风险与 RAID 管理技能：负责风险登记册初始化（范围/进度/成本/技术/质量/安全/人员七类预设）、RAID 四维台账（风险/假设/问题/依赖）全生命周期管理、定期风险巡检与概率×影响分级扫描（P1~P4）、风险应对策略（规避/减轻/转移/接受/应急预案）、问题升级机制（P1~P4 分级+四级升级阶梯+单一 Owner）、风险与范围/架构变更协同。内化 dev-project-mgmt RAID 能力为本地权威工具，可脱离编排器独立部署运行。用户说风险登记/风险扫描/RAID/风险应对/问题升级/概率影响分级时加载。"
---

# risk-mgmt 风险与 RAID 管理技能

> 版权：`../shared/references/COPYRIGHT.md` Token：`../shared/references/token_standard.md`
> 标准：`references/raid_standard.md`（RAID 与风险管理标准）v1.0.0
> 权威工具：`tools/raid_ops.py` v1.0.0（内化自 dev-project-mgmt `raid_manager.py` + MCP `risk_scan`，数据源统一台账 CSV）

## 1. 元数据

- **技能版本**：v1.0.0 **发布日期**：2026-09-08
- **变更记录**：
  - v1.0.0：首个**可独立部署**风险与 RAID 管理技能版本。按 D2 内化决策，将原委派 dev-project-mgmt `raid_manager.py`（RAID 四维 CRUD + 状态流转）与本地 MCP `risk_scan`（概率×影响分级）吸收为本地权威工具 `raid_ops.py`（台账 CSV 数据源），并从 `role-governance/domain/risk.md` 抽出升级为自包含技能；RAID 四维（risk/assumption/issue/dependency）状态流转规则与 dev-project-mgmt 保持一致，风险分级（概率×影响→P1~P4）与 MCP `risk_scan` 一致；对齐 `raid_standard.md` v1.0.0。
- **参考标准**：PMBOK 7th（风险/问题绩效域）· PMBOK 6（规划/实施/监督风险）· RAID（Risks/Assumptions/Issues/Dependencies）· ISO 31000 风险管理 · PRINCE2 风险与问题管理 · 问题升级机制（P1~P4 分级 + 四级升级阶梯）
- **定位**：风险与 RAID 受控治理的**单一权威实现层**——把「有哪些风险/假设/问题/依赖（RAID 登记册）」与「风险多大、怎么应对、何时升级（概率×影响分级 + 应对策略 + 升级阶梯）」固化为可自动扫描、可分级预警、可独立部署的工具化能力。

## 2. 触发规则

用户表达「建风险登记册 / 登记风险假设问题依赖 / 跑风险巡检 / 扫描 P1 高风险 / 评估概率影响 / 定风险应对策略 / 关闭风险 / 升级重大问题 / 风险与变更协同」时加载本技能。先 Read 本路由表，命中后只读对应 `domain/*.md`。

| 环节 | action | 明细 | 主命令 |
|------|--------|------|--------|
| 风险登记册初始化 | risk_register_init | `domain/register-init.md`（七类风险预设 / RAID 四维定义 / 登记册 schema / add 落地） | `add` |
| 风险巡检与分级 | risk_scan | `domain/scan.md`（巡检流程 / 概率×影响分级 / P1~P4 阈值 / scan 扫描 / 排除已关闭） | `scan` · `list` |
| 风险应对 | risk_response | `domain/response.md`（规避/减轻/转移/接受/应急预案 / 状态流转 / update·close） | `update` · `close` |
| 风险协同与升级 | risk_coordination | `domain/coordination.md`（P1~P4 问题分级 / 四级升级阶梯 / 单一 Owner / 风险与范围·架构变更协同） | `scan --json` · `update` |

## 3. 与现有角色/技能的边界（单一信源 + 瘦引用）

| 载体 | 关系 | 说明 |
|------|------|------|
| **risk-mgmt（本技能）** | **权威实现** | 风险登记册/RAID 四维/风险巡检分级/应对/升级协同的**唯一逻辑来源**，工具 `raid_ops.py` v1.0.0 |
| `role-governance/domain/risk.md` | 瘦引用 | 保留总控角色的路由与触发，RAID/风险扫描逻辑**委派**本技能，不复制实现细节（AC8 委派标记） |
| `role-project-mgmt`（项目经理执行层） | 协同 | 日常 RAID 台账维护调用本技能工具；进度成本风险联动走 `schedule-cost` 技能 |
| dev-project-mgmt `raid_manager.py` | 被内化（保留兼容） | RAID 四维 CRUD + 状态流转已吸收为本地 `raid_ops.py`（新权威）；dev-project-mgmt 保留供其他项目/CLI 兼容，不强制退役 |
| MCP `raid_mgmt` / `risk_scan` | 委派 | `tools/mcp_server/skills_mcp_server.py` 以 subprocess 调用本地 `raid_ops.py`（B-7 由 `_run_mgmt_cli` 委派/内联改本地），逻辑单一信源在本技能 |
| `role-project-init`（问题升级机制） | 协同 | 启动阶段 `define_issue_escalation` 确立 P1~P4 分级与升级阶梯，本技能承接巡检期升级执行 |

> **铁律**：RAID/风险逻辑只此一处实现（DRY）。角色包/MCP/文档一律**引用或委派**，禁止复制粘贴导致漂移。

## 4. 工具调用（CLI）

权威工具 `tools/raid_ops.py`（Python3，零第三方依赖）。工具经 `PROJECT_ROOT` 环境变量解析目标项目根，无论脚本副本位于何处，读写的都是目标项目的 `台账/12_风险问题台账.csv`（兼容旧名 `RAID台账.csv` 只读）。

```bash
python3 tools/raid_ops.py add --type risk --desc "核心人员流失" [--probability 高] [--impact 高] [--owner 张三] [--notes "..."]
python3 tools/raid_ops.py list [--type risk] [--status open]
python3 tools/raid_ops.py update --id RAID-001 [--status mitigating] [--owner 李四] [--probability 中] [--impact 高] [--notes "..."]
python3 tools/raid_ops.py close --id RAID-001
python3 tools/raid_ops.py scan [--severity P1] [--json]
```

**台账数据源**（读写目标项目 `台账/12_风险问题台账.csv`，防御式列名别名兼容各项目 schema 差异）：
- RAID 四维：`risk`（风险）/ `assumption`（假设）/ `issue`（问题）/ `dependency`（依赖）
- 规范列：RAID_ID / 类型 / 描述 / 概率 / 影响 / 优先级 / 状态 / 责任人 / 登记日期 / 关闭日期 / 备注

**风险分级**（概率×影响，详见 `references/raid_standard.md`）：概率·影响 高=4/中=3/低=2；风险分=概率×影响（最高 16）；P1≥12 / P2≥8 / P3≥4 / P4<4。`add` 未指定 `--priority` 时按风险分自动定级。

**状态流转**（与 dev-project-mgmt `raid_manager` 一致）：`open → {mitigating,investigating,closed}`；`mitigating → {closed,open}`；`investigating → {closed,open}`；`closed` 为终态不可再变更。类型默认状态：risk→mitigating / assumption→open / issue→investigating / dependency→open。

**退出码约定**：`0`=成功/无数据友好提示；`1`=参数非法（无效 RAID 类型 / 条目不存在 / 非法状态流转）。

## 5. 核心原则

1. **登记册全覆盖**：全部风险/假设/问题/依赖纳入 `12_风险问题台账.csv`，禁止台账外私下跟踪。
2. **等级量化**：风险按概率×影响量化分级（P1~P4），杜绝「感觉风险大」的主观判断。
3. **单一信源**：RAID 逻辑只此一处（`raid_ops.py`）；MCP/角色包委派，禁止复制状态机/分级公式导致漂移。
4. **高风险即上报**：P1 高风险（≥12）立即制定应对方案并升级；`add`/`scan` 自动 WARN。
5. **状态流转受控**：状态迁移须合法（`closed` 终态），非法流转拒绝（rc1），关闭自动填关闭日期留痕。
6. **单一 Owner**：每条 RAID 唯一责任人（对齐 RACI 唯一 A），Owner 缺失不得升级，升级路径清晰可追溯。

## 6. 输出规范

- 登记类：`add` → 追加 `12_风险问题台账.csv`（RAID-<nnn>，四维类型 + 默认状态 + 自动定级）。
- 查询类：`list` → 按类型/状态过滤的 RAID 清单（含风险分与等级）。
- 更新类：`update`/`close` → 整表重写 `12`（状态流转校验，closed 自动填关闭日期）。
- 扫描类：`scan` → 概率×影响分级扫描（排除已关闭，风险分降序，P1 铁律提示）；`scan --json` 供 MCP `risk_scan`/PMO 消费。
- 边界：仅风险与 RAID 域；不产出进度成本 EVM（归 schedule-cost）、不产出范围基准/变更（归 scope-tracking）、不产出质量缺陷（归 role-testing）。

## 7. 独立部署与镜像同步

本技能为**自包含可独立部署技能**：权威工具/测试保留在仓库根 `tools/`·`tests/`（单一信源），`skill.manifest.json` 声明打包/部署期需注入的副本（`raid_ops.py`/`test_raid_ops.py`）。`package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 按 manifest 注入后，产物（zip / 部署目录）内含 `SKILL.md + domain/ + skill.manifest.json + tools/ + tests/ + references/`，脱离编排器即可 `python3 tools/raid_ops.py ...` 直接运行。

**分发清单（STANDALONE_SKILLS）**：本技能已登记为 `package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 的 `STANDALONE_SKILLS`（独立于 11 个 `ALL_ROLES` 角色包），因此：
- **全量同步（无参）自动纳入**：`package_skills.py`（无 `--role`）产出自包含 zip；`deploy_skills.py` / `deploy_skills.sh`（无 `--roles`）全量部署到 4 个镜像目标时一并同步本技能（角色专用门禁校验器 `check_*` 仍只遍历 `ALL_ROLES`，语义不污染）。
- **按需单独分发**：`package_skills.py --role risk-mgmt` → `dist/risk-mgmt_v1.0.0.zip`；`deploy_skills.py --roles risk-mgmt`。

**镜像目标**（单一信源 `.trae/skills/risk-mgmt/` → 只读镜像，永不反写源）：`.github/skills/` · `.claude/skills/` · `.agents/skills/` · 全局 opencode 库。每个镜像内 `risk-mgmt/` 均自包含（含注入的 `tools/`+`tests/`），可整目录拷走独立运行。

**脱离本库运行**：解压 zip 或拷走镜像内 `risk-mgmt/` 目录，`cd` 到目标项目根（含 `台账/`），`python3 <目录>/tools/raid_ops.py scan`；自包含验证：`python3 <目录>/tests/test_raid_ops.py`（测试用 `ROOT=dirname(dirname(__file__))` 解析包内 `tools/`）。

> **同步命令**：改动本技能或权威工具后，运行 `python3 tools/package_skills.py`（重建 dist zip）+ `python3 tools/deploy_skills.py`（刷新 4 镜像）即可；二者对本技能均按 manifest 注入自包含副本，无需手工拷贝。

---

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求建风险登记册、登记 RAID 四维、跑风险巡检、扫描 P1 高风险、评估概率影响、定应对策略、关闭风险、升级重大问题、风险与变更协同；
- 前置：目标项目已初始化（或先 `add` 建 RAID 骨架）；`台账/12_风险问题台账.csv` 为单一事实来源；
- 不适用：进度成本 EVM（归 schedule-cost）、范围基准/变更（归 scope-tracking）、质量缺陷（归 role-testing）、安全漏洞扫描（归 role-governance security-audit）。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | 风险登记册目标已明确 | RAID 台账已初始化 | `add` 建 12 台账 + 七类风险预设 |
| 执行中 | 开始登记/巡检/应对 | 风险已分级并处置 | 按 domain 明细调用 add/list/update/close/scan |
| 校验中 | 巡检已扫描 | 分级与升级裁决完成 | 概率×影响分级 + P1 上报 + 状态流转校验 |
| 阻塞 | 12 台账缺失或条目不存在 | 补齐台账输入 | 暂停并列出缺失清单，scan 友好提示（rc0） |
| 完成 | 风险已缓解/关闭或已升级 | 交付风险巡检报告 | `scan --json` 出结构化风险，结论留痕 |
| 回退 | 检出 P1 高风险或非法状态流转 | 回到受控状态或升级人工决策 | 记风险/预警，连续 2 次延期推送人工决策 |

### 3. 执行动作层
- 执行步骤 1：`add` 登记 RAID 四维条目（类型/描述/概率/影响/责任人/备注），自动定级 + 默认状态；
- 执行步骤 2：`scan` 概率×影响分级扫描（排除已关闭，风险分降序），P1 高风险自动 WARN + 铁律提示；
- 执行步骤 3：`update` 推进状态流转（mitigating/investigating/closed）+ 应对策略落地，非法流转拒绝（rc1）；
- 执行步骤 4：`close` 关闭风险（终态校验，自动填关闭日期）；`scan --json` 供 MCP `risk_scan`/PMO 仪表盘消费；
- 所需输入：RAID 条目参数（类型/描述/概率/影响/责任人）/ 状态更新 / 升级阈值；
- 输入输出约束：RAID_ID 不复用；状态流转须合法（closed 终态）；P1 高风险必须升级留痕；单一 Owner。

### 4. 验收门禁
- 必须产出物：RAID 风险登记册（12 台账）、风险分级（P1~P4）、风险扫描报告、应对方案、升级记录；
- 通过条件：全部风险已登记且分级明确、P1 高风险已有应对方案并升级、状态流转合法、每条 RAID 有唯一 Owner；
- 失败条件：12 台账缺失致无法扫描、P1 高风险无应对方案/未升级、非法状态流转、Owner 缺失；
- 审核对象：总控保障角色（role-governance）+ 项目经理（role-project-mgmt）。

### 5. 失败处理
- 失败类型：RAID 台账缺失/为空、无效 RAID 类型、条目不存在、非法状态流转、P1 高风险未处置；
- 恢复策略：补台账/纠正类型后重扫；非法流转回退到合法前置状态；P1 高风险立即升级 L2/L3；
- 是否需要人工确认：P1 阻断问题（≤4h 响应）强制升级；连续 2 次延期/风险失控停止 AI 自动调整，推送人工决策；超本级权限（预算/范围/人员）升级 L3 指导委员会仲裁。

### 6. 产出与交接
- 产出物列表：`12_风险问题台账.csv`、风险扫描报告（`scan`/`scan --json`）、风险等级评估、应对方案、升级记录；
- 交接对象：role-governance（阶段评审门禁风险口径）、role-project-mgmt（日常 RAID 管控）、MCP `raid_mgmt`/`risk_scan`（PMO 仪表盘）、schedule-cost（进度成本风险联动）、scope-tracking（范围变更风险协同）、role-program-mgmt（跨项目风险升级）；
- 下一步动作：风险已缓解/关闭 → 允许阶段流转；P1 未决 → 升级人工决策并限期复核。

### 7. 审计记录
- 执行时间：add/update/close/scan 的时间点（12 台账 `登记日期`/`关闭日期`）；
- 关键参数：RAID 类型、概率·影响、风险分与等级（P1~P4）、状态流转、责任人；
- 关键决策：风险分级、应对策略（规避/减轻/转移/接受/应急预案）、升级路径（L1~L4）、关闭裁决；
- 结果证据：12 风险问题台账、`scan --json` 风险扫描输出、升级记录。

---

**文档版本**：v1.0.0 **最后更新**：2026-09-08（首个独立可部署风险与 RAID 管理技能；内化 dev-project-mgmt raid_manager + MCP risk_scan 为本地权威工具 raid_ops.py v1.0.0，数据源统一台账 12_风险问题台账.csv，RAID 四维状态流转与风险分级与 dev-project-mgmt/MCP 一致；对齐 raid_standard.md v1.0.0；已登记 SKILL_INDEX 条目30 + package/deploy 的 STANDALONE_SKILLS 全量同步清单，§7 补镜像同步说明）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
