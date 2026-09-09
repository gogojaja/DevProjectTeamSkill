---
name: "scope-tracking"
description: "用户提到范围基准/范围门禁/范围健康分/范围蔓延/范围缩水/覆盖度指标/变更控制/变更审计/变更生命周期/基线冻结/基线比对/需求易变性/范围跟踪台账/范围管理/RTM/WBS 时加载本范围跟踪技能：负责范围基准（SRS+RTM+WBS）与单一事实来源追溯矩阵维护、范围门禁（覆盖度+一致性+蔓延/缩水+健康分）、变更生命周期状态机（提出→分析→批准/驳回→实施→关闭，五维影响评估+审批回写基线）、基线冻结与真实蔓延/缩水差异比对、需求易变性 KPI 与范围状态报告。可脱离编排器独立部署运行。不加载：需求收集（→role-requirements-analysis）、进度管理（→schedule-cost）。"
---

# scope-tracking 范围跟踪技能

> 版权：`../shared/references/COPYRIGHT.md` Token：`../shared/references/token_standard.md`
> 标准：`references/traceability_standard.md`（范围跟踪与追溯一致性标准）v1.2.0
> 权威工具：`tools/scope_tracker.py` v1.2.0（内含 `tools/check_traceability.py` 三方一致性校验）

## 1. 元数据

- **技能版本**：v1.2.0 **发布日期**：2026-09-08
- **变更记录**：
  - v1.2.0：首个**可独立部署**范围跟踪技能版本，从 `role-governance/domain/scope-change.md` 抽出并升级为自包含技能；一体内含 `scope_tracker.py` v1.2.0 全部最佳实践能力（F1 UTF-8 输出防护 / F2 变更生命周期状态机 + 审批回写基线 / F3 门禁集成变更台账合规 / F4 基线冻结与真实蔓延·缩水比对 / F6 需求易变性 KPI + `report --json`）；对齐 `traceability_standard.md` v1.2.0（§8 健康分模型 + §9 变更生命周期/基线比对）。
- **参考标准**：PMBOK 7th（范围管理 / 实施整体变更控制 CCB）· IEEE 29148 · ISO 21500 · ITIL v4（变更使能）· MoSCoW 优先级 · NASA SWE-059 / EN 62304 / ASPICE（追溯健康）· ArchUnit FreezingArchRule（基线冻结思路）
- **定位**：范围受控基线的**单一权威实现层**——把「范围是什么（基准+RTM）」与「范围变了没有、变了多少（覆盖度+蔓延/缩水+基线漂移+易变性）」固化为可自动执行、可门禁、可独立部署的工具化能力。

## 2. 触发规则

用户表达「建范围基准 / 跑范围门禁 / 算范围健康分 / 检测范围蔓延缩水 / 登记变更 / 审批变更 / 变更回写基线 / 冻结基线 / 比对基线差异 / 看需求易变性 / 出范围状态报告」时加载本技能。先 Read 本路由表，命中后只读对应 `domain/*.md`。

| 环节 | action | 明细 | 主命令 |
|------|--------|------|--------|
| 范围基准与 RTM | scope_baseline | `domain/scope-baseline.md`（RTM schema / MoSCoW / SCOPE_STATUS / WBS 映射 / 范围外登记 / 单一事实来源） | `init` |
| 范围门禁与健康分 | scope_gate | `domain/scope-gate.md`（覆盖度 / 一致性 / 蔓延·缩水 / 健康分模型 / fail-closed / 门禁结论） | `metrics` · `gate` |
| 变更生命周期 | change_control | `domain/change-control.md`（五维影响 / CCB 状态机 / 审批回写 RTM 基线 / 变更台账合规） | `change` · `change-decide` |
| 基线冻结与比对 | baseline_diff | `domain/baseline-diff.md`（freeze/diff/list / 真实蔓延·缩水 / 易变性 KPI / 综合报告） | `baseline` · `report` |

## 3. 与现有角色/技能的边界（单一信源 + 瘦引用）

| 载体 | 关系 | 说明 |
|------|------|------|
| **scope-tracking（本技能）** | **权威实现** | 范围基准/门禁/变更生命周期/基线比对的**唯一逻辑来源**，工具 `scope_tracker.py` v1.2.0 |
| `role-governance/domain/scope-change.md` | 瘦引用 | 保留总控角色的路由与触发，范围逻辑**委派**本技能，不复制实现细节 |
| `role-requirements-analysis/domain/lifecycle.md` | 瘦引用 | 需求变更/冻结预警的**范围裁决**委派本技能；需求级 `08_需求追溯矩阵.csv` 仍归需求角色维护 |
| `check_traceability.py`（三方一致性） | 被复用 | 共享独立工具（铁律 #10 / CI / nightly gate 引用），本技能**内部复用**其 `load_matrix`/`analyze`，不吞并、不改其权威路径 |
| MCP `scope_metrics` | 委派 | `tools/mcp_server/skills_mcp_server.py` 以 subprocess 调用 `scope_tracker.py`，逻辑单一信源在本技能 |

> **铁律**：范围逻辑只此一处实现（DRY）。角色包/MCP/文档一律**引用或委派**，禁止复制粘贴导致漂移。

## 4. 工具调用（CLI）

权威工具 `tools/scope_tracker.py`（Python3，零第三方依赖）。工具经 `find_project_root()` 自动解析真实项目根（`--root` 可显式覆盖 / `PROJECT_ROOT`·`DPB_ROOT` 环境变量），无论脚本副本位于何处，读写的都是目标项目的 `台账/`。

```bash
python3 tools/scope_tracker.py init [--reset-ledgers]
python3 tools/scope_tracker.py metrics [--write]
python3 tools/scope_tracker.py gate [--max-violations 0] [--min-health 90] [--against-baseline vX.Y.Z] [--allow-open-changes]
python3 tools/scope_tracker.py change --req REQ-001 --title "..." [--type 范围调整] \
       [--impact-scope 高 --impact-schedule 中 --impact-cost 低 --impact-quality 中 --impact-security 低] \
       [--severity 主要] [--approver 用户] [--baseline-from v1.0.0 --baseline-to v1.0.1]
python3 tools/scope_tracker.py change-decide --id CR-001 --status 已批准 [--approver 用户] [--baseline-to v1.0.1] [--writeback] [--note "..."]
python3 tools/scope_tracker.py baseline freeze [--ver v1.0.0] [--force]
python3 tools/scope_tracker.py baseline diff [--against v1.0.0] [--strict]
python3 tools/scope_tracker.py baseline list
python3 tools/scope_tracker.py report [--json] [--against-baseline vX.Y.Z]
```

**台账产物**（写入目标项目 `台账/`）：`需求-架构-代码追溯矩阵.csv`（RTM，单一事实来源）· `06_范围变更台账.csv`（CR）· `07_范围跟踪台账.csv`（快照/门禁结论）· `范围基准快照.csv`（冻结基线，F4）。

**退出码约定**：`0`=通过/成功；`1`=驳回（gate 判定驳回 / diff `--strict` 检出未审批漂移）；`2`=fail-closed（一致性校验模块异常，防门禁假绿）。

## 5. 核心原则

1. **范围基准权威**：范围合规以固化的需求基线（SRS+RTM）为唯一比对标准；禁止以「已实现内容」逆向修正范围基准。
2. **单一事实来源**：RTM 连续维护，禁止事后突击补表；标识符 `REQ-/AE-/MOD-/TC-` 不复用。
3. **变更必经审批**：触及 Must/基线需求的变更未经审批禁止流转；批准后才回写基线版本与 `CHANGE_REFS`。
4. **门禁 fail-closed**：一致性校验异常时驳回（exit 2），绝不假绿放行。
5. **范围外不删除**：被否决/延期/范围外需求以 `SCOPE_STATUS` 标记保留在 RTM，防范围蔓延靠重新争论。
6. **健康分驱动**：范围健康分 <90 触发门禁驳回，量化范围失控风险（模型见标准 §8）。

## 6. 输出规范

- 门禁类：`gate` → 范围健康分卡 + 变更合规 + 门禁结论，写 `07_范围跟踪台账.csv`。
- 变更类：`change`/`change-decide` → 追加/更新 `06_范围变更台账.csv`（CR-<nnn>），批准回写 RTM。
- 基线类：`baseline freeze/diff` → `范围基准快照.csv` + 真实蔓延/缩水比对表。
- 报告类：`report --json` → 结构化范围状态（覆盖度/一致性/稳定性/变更合规/基线漂移/健康分），供 MCP/PMO 消费。
- 边界：仅范围跟踪域；不产出需求 SRS（归 role-requirements-analysis）、不产出架构设计（归 role-architecture）。

## 7. 独立部署与镜像同步

本技能为**自包含可独立部署技能**：权威工具/测试保留在仓库根 `tools/`·`tests/`（单一信源），`skill.manifest.json` 声明打包/部署期需注入的副本（`scope_tracker.py`/`check_traceability.py`/`test_scope_tracker.py`）。`package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 按 manifest 注入后，产物（zip / 部署目录）内含 `SKILL.md + domain/ + skill.manifest.json + tools/ + tests/ + references/`，脱离编排器即可 `python3 tools/scope_tracker.py ...` 直接运行。

**分发清单（STANDALONE_SKILLS）**：本技能已登记为 `package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 的 `STANDALONE_SKILLS`（独立于 11 个 `ALL_ROLES` 角色包），因此：
- **全量同步（无参）自动纳入**：`package_skills.py`（无 `--role`）产出自包含 zip；`deploy_skills.py` / `deploy_skills.sh`（无 `--roles`）全量部署到 4 个镜像目标时一并同步本技能（角色专用门禁校验器 `check_*` 仍只遍历 `ALL_ROLES`，语义不污染）。
- **按需单独分发**：`package_skills.py --role scope-tracking` → `dist/scope-tracking_v1.2.0.zip`；`deploy_skills.py --roles scope-tracking`（或与角色包组合 `--roles role-governance,scope-tracking`）。

**镜像目标**（单一信源 `.trae/skills/scope-tracking/` → 只读镜像，永不反写源）：`.github/skills/` · `.claude/skills/` · `.agents/skills/` · 全局 opencode 库 `~/.config/opencode/skills/`（Windows：`%USERPROFILE%\.config\opencode\skills\`）。每个镜像内 `scope-tracking/` 均自包含（含注入的 `tools/`+`tests/`），可整目录拷走独立运行。

**脱离本库运行**：解压 zip 或拷走镜像内 `scope-tracking/` 目录，`cd` 到目标项目根（含 `台账/`），`python3 <目录>/tools/scope_tracker.py --root <项目根> gate`；自包含验证：`python3 <目录>/tests/test_scope_tracker.py`（无需仓库根 `tools/`，测试用 `ROOT=dirname(dirname(__file__))` 解析包内 `tools/`）。

> **同步命令**：改动本技能或权威工具后，运行 `python3 tools/package_skills.py`（重建 dist zip）+ `python3 tools/deploy_skills.py`（刷新 4 镜像）即可；二者对本技能均按 manifest 注入自包含副本，无需手工拷贝。

---

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求建范围基准、跑范围门禁、检测蔓延/缩水、登记或审批变更、冻结/比对基线、出范围状态报告；
- 前置：目标项目已有 SRS/需求基线（或先 `init` 建 RTM 骨架）；`台账/需求-架构-代码追溯矩阵.csv` 为单一事实来源；
- 不适用：需求文档撰写（归 role-requirements-analysis）、架构设计（归 role-architecture）、纯代码实现（归 role-development）。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | 范围基准/RTM 目标已明确 | RTM 已初始化 | `init` 建 RTM + 06/07 台账表头 |
| 执行中 | 开始度量/门禁/变更登记 | 指标与结论已产出 | 按 domain 明细调用 metrics/gate/change/baseline |
| 校验中 | 门禁或比对已运行 | 门禁结论/漂移判定完成 | 一致性 fail-closed + 健康分 + 变更合规裁决 |
| 阻塞 | RTM 缺失/一致性模块异常/未审批触及 Must | 补齐输入或补审批 | 暂停并列出缺失清单，gate 驳回（exit 1/2） |
| 完成 | 门禁通过且基线冻结/变更闭环 | 交付范围状态报告 | `report` 出报告，结论留痕 07 台账 |
| 回退 | 检出真实蔓延/缩水或基线漂移 | 回到最近合规基线 | 记缺陷/变更，经审批回写或撤销漂移 |

### 3. 执行动作层
- 执行步骤 1：`init` 初始化 RTM（扩展列 PRIORITY/SCOPE_STATUS/BASELINE_VER/SOURCE/VERIFY_METHOD/CHANGE_REFS）与 06/07 台账；
- 执行步骤 2：`metrics` 计算覆盖度（REQ→AE、REQ→TC）+ 一致性违规 + 蔓延/缩水 + 健康分 + 易变性 KPI；
- 执行步骤 3：`gate` 范围门禁（一致性 fail-closed + 蔓延/缩水 + 变更台账合规 + 健康分 ≥ 阈值），结论写 07 台账并 exit；
- 执行步骤 4：`change`/`change-decide` 登记并推进变更生命周期（五维影响 → CCB 状态机 → 批准回写 RTM 基线版本 + CHANGE_REFS）；
- 执行步骤 5：`baseline freeze/diff` 冻结基线并比对真实蔓延/缩水（区分已审批/未审批漂移）；`report --json` 供 MCP/PMO 消费；
- 所需输入：RTM CSV / 变更请求参数 / 基线版本号；
- 输入输出约束：标识符不复用；变更触及 Must/基线必经审批；门禁结论必须留痕；一致性异常必须 fail-closed。

### 4. 验收门禁
- 必须产出物：RTM（单一事实来源）、范围健康分卡、门禁结论（07 台账）、变更台账（06）、基线快照（冻结时）；
- 通过条件：一致性违规 ≤ 容忍度、无严重缩水、健康分 ≥ `--min-health`（默认 90）、无未审批变更触及 Must/基线、基线漂移已审批；
- 失败条件：一致性模块异常（fail-closed，exit 2）、健康分 < 阈值、存在未审批的 Must/基线变更、检出未审批真实蔓延/缩水；
- 审核对象：总控保障角色（role-governance）+ 项目经理（role-project-mgmt）。

### 5. 失败处理
- 失败类型：RTM 缺失/为空、一致性校验模块不可用、未审批变更触及 Must、基线漂移未审批、健康分不达标；
- 恢复策略：补 RTM/补审批/撤销漂移/整改缺陷后重跑门禁；迁移期可 `gate --allow-open-changes` 临时降级为警告（留痕）；
- 是否需要人工确认：重大变更强制 `user_confirm=同意`；范围基准调整仅经合法变更审批；同一需求连续 3 次无审批变更触发范围冻结预警。

### 6. 产出与交接
- 产出物列表：`需求-架构-代码追溯矩阵.csv`、`06_范围变更台账.csv`、`07_范围跟踪台账.csv`、`范围基准快照.csv`、范围状态报告（`report --json`）；
- 交接对象：role-governance（阶段评审门禁）、role-requirements-analysis（需求基线一致性）、MCP `scope_metrics`（PMO 仪表盘）、role-program-mgmt（跨项目范围口径）；
- 下一步动作：门禁通过 → 允许阶段流转；驳回 → 转整改并限期复核。

### 7. 审计记录
- 执行时间：init/metrics/gate/change/decide/freeze/diff/report 的时间点（台账 `SNAPSHOT_AT`/`PROPOSED_AT`/`DECIDED_AT`/`FROZEN_AT`）；
- 关键参数：基线版本、健康分阈值、容忍度、变更五维影响、严重度、审批人；
- 关键决策：门禁结论（通过/警告/驳回）、变更审批（批准/驳回）、基线漂移判定（真实蔓延/缩水/降级）；
- 结果证据：07 范围跟踪台账快照、06 变更台账、基线快照 CSV、`report --json` 输出。

---

**文档版本**：v1.2.0 **最后更新**：2026-09-08（首个独立可部署范围跟踪技能；一体内含 scope_tracker.py v1.2.0 F1-F6 能力；对齐 traceability_standard.md v1.2.0；已登记 SKILL_INDEX 条目23 + package/deploy 的 STANDALONE_SKILLS 全量同步清单，§7 补镜像同步说明）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
