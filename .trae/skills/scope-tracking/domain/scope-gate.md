# 范围门禁与健康分（Scope Gate & Health Score）

> 所属技能：`scope-tracking` v1.2.0 · 标准：`references/traceability_standard.md` §5-§8
> 权威工具：`tools/scope_tracker.py`（`metrics` / `gate`）· 内部复用 `tools/check_traceability.py` 三方一致性

## 1. 覆盖度指标（metrics）

```bash
python3 tools/scope_tracker.py metrics           # 打印范围健康分卡 + 稳定性 KPI
python3 tools/scope_tracker.py metrics --write    # 追加写 07_范围跟踪台账.csv 快照
```

输出「范围健康分卡」：需求总数、需求→架构覆盖率（`with_ae/req_total`）、需求→测试覆盖率（`with_tc/req_total`）、实现率、验证率、一致性违规数、蔓延项、缩水项、状态分布、优先级分布、范围健康分；并附「范围稳定性 KPI」（需求易变性、变更单计数、未决 CR 平均龄、变更密度，详见 `baseline-diff.md`）。

## 2. 范围门禁（gate）

```bash
python3 tools/scope_tracker.py gate [--max-violations 0] [--min-health 90] \
        [--against-baseline vX.Y.Z] [--allow-open-changes]
```

门禁在覆盖度基础上叠加：**一致性 fail-closed** + **蔓延/缩水** + **变更台账合规（F3）** + **相对冻结基线的真实漂移（F4）** + **健康分阈值**，结论写入 `07_范围跟踪台账.csv`（留痕）并按结论 exit。

| 参数 | 默认 | 作用 |
|------|------|------|
| `--max-violations` | 0 | 一致性违规容忍度；超过 → 严重（驳回） |
| `--min-health` | 90 | 健康分门禁阈值；低于 → 严重（驳回）（标准 §8） |
| `--against-baseline` | 自动取最新冻结 | 指定对比基线版本，计算真实漂移 |
| `--allow-open-changes` | false | 将「未审批变更触及 Must/基线」从**驳回降为警告**（迁移期用，留痕） |

## 3. 范围健康分模型（权威公式，标准 §8）

基准 100，逐项扣减，下限 0，保留 1 位小数：

| 维度 | 扣分 |
|------|------|
| 覆盖缺口（架构） | `-0.2 × 未映射 AE 的需求占比%` |
| 覆盖缺口（测试） | `-0.2 × 未被 TC 验证的需求占比%` |
| 一致性违规 | `-2 × 违规数`（断链/孤儿） |
| 范围蔓延 | `-1.5 × 蔓延项`（gold-plating / 孤儿能力） |
| 范围缩水 | `-3 × 缩水项`（Must 缺实现/验证） |
| 未审批变更触及 Must/基线 | `-4 × open_unapproved_must`（F3） |
| 基线净漂移 | `-2 × baseline_drift`（F4） |
| 已判定 CR 缺审批人 | `-2 × missing_approver`（F3） |
| 超期未决 CR | `-1 × stale_cr`（>14 天，F3/F6） |

> **向后兼容**：变更信号（后 4 项）仅在 `gate`/`report` 传入 `change_signals` 时生效；`metrics` 只算前 5 项，与 v1.1.1 一致。

## 4. 蔓延 / 缩水检测规则

- **缩水（严重）**：`PRIORITY=Must` 且 `SCOPE_STATUS ∈ {Baselined,InProgress,Implemented,Verified,Closed}`，却缺 `MOD_ID`（缺实现）或缺 `TC_ID`（缺验证）。
- **蔓延（警告）**：
  - `PRIORITY=Won't` 却已进入 `Implemented/Verified/Closed`（做了不该做的）；
  - 孤儿架构 `AE`（无回溯 REQ）/ 孤儿代码 `MOD`（无归属 AE）/ 孤儿测试 `TC`（无回溯 REQ）——悬空新增能力。

## 5. 门禁结论判定

```
严重(驳回) = 违规 > max-violations  OR  缩水 > 0  OR  健康分 < min-health
             OR (未审批变更触及 Must/基线 > 0  AND NOT --allow-open-changes)
警告       = 蔓延 > 0  OR  (0 < 违规 ≤ max-violations)  OR  超期未决 CR > 0
             OR  缺审批人 > 0  OR  (未审批触及 Must/基线 > 0  AND --allow-open-changes)
结论       = 通过（无严重且无警告） | 驳回（有严重） | 警告（无严重但有警告）
```

**退出码**：`0`=通过/警告；`1`=驳回；`2`=**fail-closed**（一致性校验模块异常/缺失，防门禁假绿，写快照「一致性校验异常-fail-closed」）。

## 6. fail-closed 原则（防假绿）

`gate` 调用一致性校验（`check_traceability.py` 的 `load_matrix`/`analyze`）时，若模块异常或不可用，**不降级放行**，而是直接驳回（exit 2）并留痕。`metrics`/`report` 为非门禁场景，一致性不可用时降级为告警（不影响覆盖度指标）。

## 7. 最佳实践对齐

- **PMBOK 7th / ITIL v4**：门禁 = 阶段流转前的范围合规裁决，结论可审计、可留痕。
- **ASPICE / ArchUnit**：一致性 fail-closed 对应「追溯健康自检不通过即阻断」，杜绝假绿。
- **量化驱动**：健康分把多维范围风险归一为单一可比指标，阈值化门禁（默认 ≥90）。

---

**文档版本**：v1.2.0 **最后更新**：2026-09-08（补 F3 变更合规 + F4 基线漂移入门禁；健康分模型标准化 §8）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
