# 范围跟踪与追溯一致性标准（Scope Tracking & Traceability）

> 版权声明：`../COPYRIGHT.md`
> 适用：所有启用本技能库的软件项目（对齐 PMBOK 6/7 范围管理 · 实施整体变更控制 · IEEE 830 / ISO/IEC/IEEE 29148 · ISO 21500 · ITIL v4 变更使能 · MoSCoW · NASA SWE-059 / EN 62304 / ASPICE · ArchUnit FreezingArchRule）
> 调用：阶段流转门禁 `stage_review` / `check_gate` 调用 `tools/scope_tracker.py`（内含 `tools/check_traceability.py` 一致性校验）自动校验
> 权威实现：可独立部署技能 `scope-tracking`（`tools/scope_tracker.py` v1.2.0）——范围逻辑单一信源，角色包/MCP 一律引用或委派

---

## 1. 问题定义

软件项目反复出现两类失控：

- **范围漂移（drift）**：架构/代码未覆盖需求（范围缩水），或实现了需求未要求的能力（gold-plating / 范围蔓延）。
- **追溯断裂**：缺乏单一事实来源的**双向追溯**，且追溯未随变更持续维护（只在审计前突击补矩阵）。

根因：**范围未作为受控基线持续跟踪**——既缺「范围是什么」（范围基准 + RTM），也缺「范围变了没有、变了多少」（覆盖度指标 + 蔓延/缩水检测）。

本标准在原有「需求-架构-代码-测试 三方一致性」基础上，补齐全生命周期**范围跟踪**能力：范围基准、RTM 扩展维度、覆盖度指标、范围蔓延/缩水检测、变更与基线版本化。

---

## 2. 行业最佳实践（依据）

| 来源 | 核心主张 | 本标准落点 |
|------|----------|-----------|
| PMBOK 6/7 范围管理 | 规划范围→收集需求→定义范围→创建 WBS→确认范围→控制范围；**范围基准 = 范围说明书 + WBS + WBS 词典** | §4 范围基准；§6 控制范围 |
| IEEE 830 / ISO 29148 | 需求工程须可验证、可追溯；需求状态机（提议/批准/基线/实现/验证/关闭） | §3 扩展 RTM；§5 状态机 |
| MoSCoW（优先级） | Must/Should/Could/Won't 优先级驱动范围取舍 | §3 `PRIORITY` 列 |
| NASA SWE-059 / ISO 24765 | 需求↔架构↔设计↔代码↔测试 **双向可追溯**，唯一标识，禁止「孤儿」 | §3 标识符；§7 一致性门禁 |
| EN 62304 | **4-way traceability** + 孤儿即审计发现项 | §7 |
| ASPICE | 每个需求分配到具体组件；定期「追溯健康自检」 | §8 健康自检 |
| 变更控制（CCB）/ PMBOK 实施整体变更控制 | 变更须评估影响、审批、记录，并触发基线版本化 | §6 变更与基线；§9 变更生命周期 |
| ITIL v4 变更使能 | 变更分类 + 授权 + 记录，最大化变更成功率同时控风险 | §9.1 变更状态机 |
| ArchUnit `FreezingArchRule` | 冻结既有基线，只阻止未经批准的劣化，允许经审批演进 | §9.3 基线冻结/比对 |
| IEEE 需求易变性度量 | 以易变性/变更密度/未决龄量化范围稳定性 | §9.4 易变性 KPI |

结论：**范围必须作为受控基线 + 连续维护的 RTM + 自动化门禁强制 + 变更生命周期可审计**，而非人工临时补表。

---

## 3. 标识符与 RTM 维度规范

### 3.1 唯一标识符（ID Scheme）

所有生命周期产物使用**唯一、稳定、不复用**的前缀标识：

| 产物 | 前缀 | 示例 | 生成阶段 |
|------|------|------|----------|
| 需求 | `REQ-<nnn>` | REQ-001 | 需求分析 |
| 架构决策 | `ADR-<nnn>` | ADR-001 | 架构设计 |
| 架构元素/组件 | `AE-<nnn>` | AE-001 | 架构设计 |
| 代码模块 | `MOD-<nnn>` | MOD-001 | 开发 |
| 测试用例 | `TC-<nnn>` | TC-001 | 测试 |
| 变更请求 | `CR-<nnn>` | CR-001 | 总控/变更 |

**存量 ID 兼容规则**：既有存量 `REQ-0x`（两位）与 `REQ-ITx-0x`（带迭代前缀）为历史合法变体（本库存量 11 条），工具不校验位数、兼容读取；新增条目一律采用上表三位规范（`REQ-<nnn>` / `REQ-ITx-<nnn>`），避免新老格式混用（2026-08-25 审计整改 DEV-10 明确）。

- 每个需求至少映射 1 个 AE；每个 AE 至少回溯 1 个 REQ（双向）。
- 每个代码模块声明所属 AE；每个 AE 至少 1 个 MOD 实现。
- 每个需求至少 1 个 TC 验证；每个 TC 回溯到至少 1 个 REQ。

### 3.2 扩展 RTM 维度（新增）

在原有 `REQ_ID/REQ_TITLE/AE_ID/MOD_ID/TC_ID` 基础上，RTM 追加以下维度，使矩阵同时承载**范围跟踪**语义：

| 列 | 含义 | 取值 / 分隔 |
|----|------|------------|
| `PRIORITY` | 优先级（MoSCoW） | `Must` / `Should` / `Could` / `Won't`（本轮/本基线） |
| `SCOPE_STATUS` | 范围生命周期状态 | 见 §5 状态机 |
| `BASELINE_VER` | 所属范围基准版本 | 如 `v1.0.0`；变更后随基线升级 |
| `SOURCE` | 需求来源 | 干系人/章程/合规/缺陷单号等 |
| `VERIFY_METHOD` | 验证方式 | `TC-xxx` / 评审 / 演示 /  Inspection |
| `CHANGE_REFS` | 关联变更请求 | `CR-<nnn>`，多值 `,` 分隔 |

> 向后兼容：`tools/check_traceability.py` 仅要求原 5 列存在，扩展列被 `tools/scope_tracker.py` 读取，不影响既有门禁。

### 3.3 拒绝/延期需求不删除，改为状态标记

被否决（Rejected）、延期（Deferred）、明确范围外（Out-of-Scope）的需求**保留在 RTM 中并以 `SCOPE_STATUS` 标记**，不物理删除——这是防止「范围蔓延靠重新争论」的最佳实践（out-of-scope register）。

---

## 4. 范围基准（Scope Baseline）

PMBOK 范围基准 = 范围说明书 + WBS + WBS 词典。本库以**需求基线（SRS）+ 追溯矩阵（RTM）**作为范围基准载体，并补充：

1. **范围说明书（SRS 兼）**：`role-requirements-analysis` 产出，定义「做什么、不做什么」。
2. **WBS 分解**：将 `REQ-<nnn>` 逐级分解为 `AE-<nnn>`（架构组件）→ `MOD-<nnn>`（代码模块），RTM 的 `REQ→AE→MOD` 即为可执行的 WBS 映射；大型项目可另附 WBS 词典。
3. **范围外登记**：通过 `SCOPE_STATUS ∈ {Rejected, Deferred, Out-of-Scope}` 在 RTM 内实现，无需独立文件。
4. **基准版本化**：范围基准一经固化即打 `BASELINE_VER`（如 `v1.0.0`）；任何经审批的变更**升级基准版本**（`v1.0.1`…），RTM 的 `BASELINE_VER` 列随行更新，`06_范围变更台账.csv` 记录版本跃迁。

**范围基准权威铁律**（沿用 `role-requirements-analysis` / `scope-change.md`）：「范围合规」以固化需求基线为唯一比对标准；已实现内容与基准不符一律以基准为准、偏差记缺陷返工；基准调整仅经合法变更审批，来源为「已实现内容」驳回。

---

## 5. 范围生命周期状态机（SCOPE_STATUS）

```
Proposed → Approved → Baselined → InProgress → Implemented → Verified → Closed
                                  │
                                  ├─→ Deferred（延期，留 RTM 标记）
                                  ├─→ Rejected（否决）
                                  └─→ Out-of-Scope（明确范围外）
```

| 状态 | 含义 | 进入条件 |
|------|------|----------|
| Proposed | 已提出未评审 | 需求收集产出 |
| Approved | 评审通过待基线 | 需求评审通过 |
| Baselined | 已纳入范围基准（冻结） | 基线固化 |
| InProgress | 架构/开发中 | 进入架构或开发阶段 |
| Implemented | 代码实现完成 | 开发完成、单元自测通过 |
| Verified | 测试/验收通过 | 测试阶段 TC 通过 |
| Closed | 已交付/归档 | 验收 + 归档 |
| Deferred / Rejected / Out-of-Scope | 不在当前范围 | 评审或变更决策 |

---

## 6. 控制范围（变更与基线）

### 6.1 变更流程（CCB 风格）
1. 提出变更请求 → `CR-<nnn>` 登记 `06_范围变更台账.csv`（五维影响：范围/进度/成本/质量/安全）。
2. 影响评估 + 审批（`user_confirm=同意` 为重大变更硬门槛）。
3. 审批通过 → **升级范围基准版本**，更新受影响 REQ 行的 `BASELINE_VER` 与 `CHANGE_REFS`。
4. 同步 RTM，使追溯连续（禁止事后突击补表）。

### 6.2 范围蔓延 / 缩水检测（自动）
`tools/scope_tracker.py gate` 以 `BASELINE_VER` 为基准快照，对比当前 RTM：
- **范围蔓延（Creep / Gold-plating）**：出现未关联任何已审批 `CR` 的新 `AE/MOD/TC`，或 `PRIORITY` 为 `Won't` 却已实现 → 标记 `CREEP`。
- **范围缩水（Shrink）**：`BASELINE_VER` 中 `Must` 需求在 `BASELINE_VER` 最新版缺失 `MOD` 实现或 `TC` 验证 → 标记 `SHRINK`。
- 任一严重项 → 门禁 `驳回`；主要项 → `警告` + 限期整改。

---

## 7. 一致性门禁（自动校验）

`tools/scope_tracker.py gate` 内部调用 `tools/check_traceability.py` 校验六类关系（见 §3.1）：

1. 需求→架构覆盖（每个 REQ 至少 1 个 AE）
2. 需求→测试覆盖（每个 REQ 至少 1 个 TC）
3. 架构无孤儿（每个 AE 至少回溯 1 个 REQ）
4. 架构已落地（每个 AE 至少 1 个 MOD）
5. 代码无孤儿（每个 MOD 至少归属 1 个 AE）
6. 测试回溯需求（每个 TC 至少回溯 1 个 REQ）

**门禁结论**：违规数 > `--max-violations`（默认 0）则 **exit 1（驳回流转）**；矩阵缺失则提示先建立。
断链率（孤儿数 / 总数）应 **= 0%**；既有项目可设容忍度渐进收敛（参照 ArchUnit `FreezingArchRule` 冻结已知违规、仅报新增）。

---

## 8. 覆盖度指标与健康自检（Health Scorecard）

`tools/scope_tracker.py metrics` 计算并输出（写入 `07_范围跟踪台账.csv` 快照行）：

| 指标 | 定义 | 健康目标 |
|------|------|----------|
| 需求→架构覆盖率 | 有 AE 的 REQ / 总 REQ | 100% |
| 需求→测试覆盖率 | 有 TC 的 REQ / 总 REQ | 100%（Must/Should） |
| 实现率 | `Implemented+` 状态 REQ / 总 REQ | 随阶段爬升 |
| 验证率 | `Verified+` 状态 REQ / 总 REQ | 交付前 100%（Must） |
| 孤儿率 | 孤儿 AE/MOD/TC / 总数 | 0% |
| 范围健康分 | 见 §8.1 精确模型（基准 100 逐项扣减） | ≥ 90 门禁通过 |

### 8.1 范围健康分精确模型（权威公式，`scope_tracker.py health_score`）

基准 100 分，逐项扣减，下限 0，保留 1 位小数。`metrics` 计算第 1-5 项；`gate`/`report` 叠加变更信号（第 6-9 项）：

| # | 维度 | 扣分公式 | 场景 |
|---|------|----------|------|
| 1 | 覆盖缺口（架构） | `-0.2 × (未映射 AE 的需求数 / 需求总数 × 100)` | metrics/gate |
| 2 | 覆盖缺口（测试） | `-0.2 × (未被 TC 验证的需求数 / 需求总数 × 100)` | metrics/gate |
| 3 | 一致性违规 | `-2 × 违规数`（断链/孤儿） | metrics/gate |
| 4 | 范围蔓延 | `-1.5 × 蔓延项`（gold-plating / 孤儿能力） | metrics/gate |
| 5 | 范围缩水 | `-3 × 缩水项`（Must 缺实现/验证） | metrics/gate |
| 6 | 未审批变更触及 Must/基线 | `-4 × open_unapproved_must` | gate/report（F3） |
| 7 | 基线净漂移 | `-2 × baseline_drift` | gate/report（F4） |
| 8 | 已判定 CR 缺审批人 | `-2 × missing_approver` | gate/report（F3） |
| 9 | 超期未决 CR（>14 天） | `-1 × stale_cr` | gate/report（F3/F6） |

> **门禁阈值**：健康分 < `--min-health`（默认 90）→ 驳回。**向后兼容**：变更信号（第 6-9 项）仅在传入 `change_signals` 时生效，`metrics` 场景与 v1.1.1 完全一致。

**ASPICE 追溯健康自检清单**（每次阶段评审自问，任一「是」即待办）：
- [ ] 是否存在无架构映射的需求？（需求-架构断链）
- [ ] 是否存在无代码落地的架构元素？（悬空架构）
- [ ] 是否存在无父架构的代码模块？（孤儿代码）
- [ ] 是否存在无测试验证的需求？（需求-测试断链）
- [ ] 是否存在无回溯需求的测试？（孤儿测试）
- [ ] 是否存在 `Won't` 却已实现（gold-plating）或 `Must` 未实现（缩水）？
- [ ] 最近一次变更是否已同步更新 RTM 与基线版本？

---

## 9. 变更生命周期与基线比对（v1.2.0，F2/F3/F4/F6）

> 权威实现：`tools/scope_tracker.py`（`change` / `change-decide` / `baseline` / `report`）；技能明细 `scope-tracking/domain/change-control.md`·`baseline-diff.md`。

### 9.1 变更请求生命周期状态机（CR 状态，区别于 §5 需求 SCOPE_STATUS）

```
提出 → 分析中 → ┬ 已批准 → 已实施 → 已关闭（终态）
                └ 已驳回
```

- **未决状态** = {提出, 分析中}：尚无审批结论；触及 Must/基线需求即构成门禁风险（§9.2）。
- **已判定状态** = {已批准, 已驳回, 已实施, 已关闭}：写入 `DECIDED_AT`；`已关闭` 为终态禁止再变更。
- `change-decide` 推进状态；`--status ∈ {已批准, 已实施}` 且 `--writeback` → **回写 RTM**：受影响 REQ 行升级 `BASELINE_VER`、追加 `CHANGE_REFS`（落实 §6.1 步骤 3，禁止事后突击补表）。

### 9.2 变更台账合规信号（门禁/健康分输入，F3）

| 信号 | 判定 | 后果 |
|------|------|------|
| `open_unapproved_must` | 未决 CR 触及受保护需求（Must / 有 BASELINE_VER / 已进入 advanced 状态） | >0 且未 `--allow-open-changes` → **门禁驳回**；健康分 -4/项 |
| `missing_approver` | 已批准/已实施/已关闭但无审批人 | 警告；健康分 -2/项 |
| `stale_cr` | 未决 CR 提出距今 > 14 天（`STALE_CR_DAYS`） | 警告；健康分 -1/项 |

### 9.3 基线冻结与真实蔓延/缩水比对（F4，ArchUnit FreezingArchRule 思路）

- `baseline freeze --ver vX.Y.Z`：全量冻结当前 RTM 的 REQ 集到 `范围基准快照.csv`（append-only，同名覆盖需 `--force`），作为历史锚点。
- `baseline diff --against vX.Y.Z [--strict]`：当前 RTM 逐需求比对冻结基线，**区分是否经审批**：
  - **真实蔓延** = 未被已审批 CR 覆盖的新增 REQ；**真实缩水** = 未被已审批 CR 覆盖的删除 REQ；**真实降级** = 未审批的优先级下调。
  - `baseline_drift = 真实蔓延 + 真实缩水 + 真实降级`；已审批变更（`--writeback` 回写后）**不计入漂移**（变更经审批即合法的量化体现）。
  - `--strict`：`baseline_drift > 0` 时 exit 1（CI 阻断）；`gate --against-baseline` 将 drift 纳入健康分（-2/项）。

### 9.4 需求易变性 KPI（F6，IEEE 需求易变性度量）

`metrics`/`report` 输出范围稳定性：需求易变性（发生变更的需求数 / 需求总数 %）、变更单计数（未决/已批/已驳）、未决 CR 平均龄（天）、变更密度（CR / 需求）。`report --json` 汇总覆盖度/一致性/稳定性/变更合规/基线漂移/健康分为结构化输出，供 MCP `scope_metrics` 与 PMO 仪表盘消费。

---

## 10. 流程嵌入（何时做）

- **需求分析阶段**：建立 `REQ-<nnn>`，初始化 RTM（含扩展维度），状态 `Proposed→Approved`。
- **架构/开发阶段**：补充 `AE/MOD`，完成 `REQ→AE→MOD` 映射，状态推进至 `InProgress→Implemented`，`check_gate` 校验无孤儿。
- **测试阶段**：补充 `TC`，状态推进至 `Verified→Closed`。
- **基线固化后**：`baseline freeze --ver vX.Y.Z` 冻结范围基准，作为后续漂移比对锚点。
- **每阶段 `stage_review`**：自动跑 `scope_tracker.py gate`（含一致性 + 蔓延/缩水 + 变更合规 + 基线漂移 + 健康分），**未通过不得流转**。
- **变更时**：走 §6/§9 变更流程（`change` 登记 → `change-decide` 审批 → `--writeback` 回写基线），升级 `BASELINE_VER`，同步 RTM（连续追溯）。
- **监控/汇报**：`report --json` 供 MCP/PMO 消费；迭代中 `baseline diff --strict` 阻断未审批漂移。

---

**文档版本**：v1.2.0　**最后更新**：2026-09-08（最佳实践升级：§8.1 范围健康分精确模型（权威公式）；新增 §9 变更生命周期状态机（F2）+ 变更台账合规信号（F3）+ 基线冻结与真实蔓延/缩水比对（F4）+ 需求易变性 KPI（F6），原 §9 流程嵌入顺延为 §10；对齐 scope_tracker.py v1.2.0，支撑独立可部署技能 scope-tracking。此前 v1.1.1：§3.1 存量 ID 兼容规则）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
