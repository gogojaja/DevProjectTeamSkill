# 变更生命周期与控制（Change Control / CCB）

> 所属技能：`scope-tracking` v1.2.0 · 标准：`references/traceability_standard.md` §9
> 权威工具：`tools/scope_tracker.py`（`change` / `change-decide`）· 对齐 PMBOK 实施整体变更控制 · ITIL v4 变更使能

## 1. 变更台账 schema（06_范围变更台账.csv）

`CHANGE_COLS`：`CHANGE_ID`(CR-<nnn>) · `REQ_IDS`(关联需求，多值) · `TITLE` · `TYPE` · `SOURCE` · `IMPACT_SCOPE` `IMPACT_SCHEDULE` `IMPACT_COST` `IMPACT_QUALITY` `IMPACT_SECURITY`(五维影响 高/中/低) · `SEVERITY`(轻微/主要/严重) · `STATUS`(状态机) · `APPROVER` · `BASELINE_FROM` `BASELINE_TO`(基准版本前/后) · `PROPOSED_AT` `DECIDED_AT`(时间戳) · `NOTE`。

## 2. 变更生命周期状态机（F2）

```
提出(Proposed) → 分析中(Analyzing) → ┬ 已批准(Approved) → 已实施(Implemented) → 已关闭(Closed)
                                      └ 已驳回(Rejected)
```

- **未决状态**（`CHANGE_OPEN_STATES` = {提出, 分析中}）：尚未形成审批结论；若触及 Must/基线需求 → 构成范围门禁风险（见 `scope-gate.md` §5）。
- **已判定状态**（`CHANGE_DECIDED_STATES` = {已批准, 已驳回, 已实施, 已关闭}）：写入 `DECIDED_AT`。
- **已关闭**为终态，禁止再变更状态。

## 3. 登记变更（change）

```bash
python3 tools/scope_tracker.py change --req REQ-001 --title "调整对账口径" \
        --type 范围调整 --source 用户诉求 \
        --impact-scope 高 --impact-schedule 中 --impact-cost 低 --impact-quality 中 --impact-security 低 \
        --severity 主要 --approver 用户 --baseline-from v1.0.0 --baseline-to v1.0.1
```

- 追加 `06_范围变更台账.csv`，`STATUS=提出`，`CHANGE_ID` 自增 CR-<nnn>。
- **参照完整性校验（仅告警不阻断，容忍历史自由文本）**：`--req` 引用 RTM 中不存在的需求 → 告警；五维影响值不在 {高/中/低}、严重度不在 {轻微/主要/严重} → 告警。
- `--type` 建议枚举：范围调整 / 接口变化 / 合规新规 / 新诉求 / 缺陷澄清 / 其他。

## 4. 推进生命周期（change-decide）

```bash
python3 tools/scope_tracker.py change-decide --id CR-001 --status 已批准 \
        --approver 用户 --baseline-to v1.0.1 --writeback --note "CCB 批准"
```

| 参数 | 作用 |
|------|------|
| `--id` | 变更编号 CR-<nnn>（必填） |
| `--status` | 目标状态：分析中 / 已批准 / 已驳回 / 已实施 / 已关闭（必填，须为合法目标） |
| `--approver` | 审批人（批准时强烈建议填写；缺失 → 计入 `missing_approver` 扣分） |
| `--baseline-to` | 批准后的新基线版本（回写 RTM 用） |
| `--writeback` | 批准/实施时**回写 RTM**：受影响 REQ 行升级 `BASELINE_VER` + 追加 `CHANGE_REFS` |
| `--note` | 决策备注（追加，保留历史） |

**审批回写（落实范围基准版本化）**：`--status ∈ {已批准, 已实施}` 且 `--writeback` 时，对 `REQ_IDS` 命中的 RTM 行写入 `BASELINE_TO` 到 `BASELINE_VER`、追加本 CR 到 `CHANGE_REFS`，保持 RTM 连续追溯（禁止事后突击补表）。无匹配行/RTM 缺列 → 告警提示核对。已批准但无审批人 → 告警（重大变更强制 `user_confirm=同意`）。

## 5. 变更台账合规信号（F3，供门禁/健康分）

`analyze_change_signals` 从变更台账计算：

| 信号 | 判定 | 门禁/健康分影响 |
|------|------|----------------|
| `open_unapproved_must` | 未决 CR 的 `REQ_IDS` 触及受保护需求（Must / 有 BASELINE_VER / 已进入 advanced 状态） | >0 且未 `--allow-open-changes` → **驳回**；健康分 -4/项 |
| `missing_approver` | 已批准/已实施/已关闭但 `APPROVER` 为空 | 警告；健康分 -2/项 |
| `stale_cr` | 未决 CR 的 `PROPOSED_AT` 距今 > 14 天（`STALE_CR_DAYS`） | 警告；健康分 -1/项 |
| `baseline_drift` | 相对冻结基线的净未审批漂移（见 `baseline-diff.md`） | 健康分 -2/项 |

## 6. 边界规则（刹车）

- **重大变更强制 `user_confirm=同意`**；核心架构文件变更自动转发安全审计。
- **同一需求连续 3 次无审批变更 → 触发范围冻结预警**（应收敛到 `baseline freeze` + 强制审批）。
- **超范围内容（gold-plating / 孤儿新增能力）无审批禁止流转**（门禁拦截，见 `scope-gate.md`）。
- 来源为「已实现内容」的范围基准调整一律驳回（禁止逆向修正基线，见 `scope-baseline.md` §1）。

## 7. 最佳实践对齐

- **PMBOK 实施整体变更控制**：所有变更经 CCB 裁决，批准后方可更新基准，全程留痕。
- **ITIL v4 变更使能**：变更分类（标准/正常/紧急）+ 授权 + 记录，最大化变更成功率同时控风险。
- **CCB 审批回写**：把「审批决定」固化为 RTM 的基线版本与变更引用，实现变更↔需求双向可追溯。

---

**文档版本**：v1.2.0 **最后更新**：2026-09-08（F2 变更生命周期状态机 + 审批回写；F3 变更台账合规信号）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
