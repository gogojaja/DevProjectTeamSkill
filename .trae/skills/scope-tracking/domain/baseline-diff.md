# 基线冻结与差异比对（Baseline Freeze & Diff）

> 所属技能：`scope-tracking` v1.2.0 · 标准：`references/traceability_standard.md` §9
> 权威工具：`tools/scope_tracker.py`（`baseline` / `report`）· 对齐 ArchUnit FreezingArchRule · IEEE 需求易变性度量

## 1. 范围基准快照（范围基准快照.csv）

`BASELINE_COLS`：`BASELINE_VER` · `FROZEN_AT` · `REQ_ID` · `PRIORITY` · `SCOPE_STATUS` · `AE_ID` · `MOD_ID` · `TC_ID`。**append-only**：每次 `freeze` 全量写入该版本的 REQ 集，作为后续 `diff` 的锚点（同名版本再冻结需 `--force` 覆盖）。

## 2. 冻结基线（freeze）

```bash
python3 tools/scope_tracker.py baseline freeze [--ver v1.0.0] [--force]
```

- `--ver` 缺省时取 RTM 最新 `BASELINE_VER`（无则 `v1.0.0`）。
- 已冻结同名版本且无 `--force` → 拒绝（防误覆盖）。
- 冻结即把「当前受控范围」固化为可比对的历史锚点（对应 ArchUnit `FreezingArchRule` 的基线思路：先冻结既有状态，再阻止未经批准的劣化）。

## 3. 差异比对（diff）——识别真实蔓延/缩水

```bash
python3 tools/scope_tracker.py baseline diff [--against v1.0.0] [--strict]
python3 tools/scope_tracker.py baseline list          # 列出已冻结版本
```

将**当前 RTM** 与**指定冻结基线**逐需求比对，输出：新增需求、删除需求、状态变更、优先级变更；并**区分是否经审批**：

| 漂移类型 | 判定 | 语义 |
|----------|------|------|
| `unapproved_added` | 新增 REQ 且未被任何已批准/已实施/已关闭 CR 覆盖 | **真实蔓延**（未审批扩范围） |
| `unapproved_removed` | 删除 REQ 且未被已审批 CR 覆盖 | **真实缩水**（未审批砍范围） |
| `unapproved_prio_down` | 优先级下调（如 Must→Should）且未被已审批 CR 覆盖 | **真实降级** |

**基线净漂移** `baseline_drift = 未审批新增 + 未审批删除 + 未审批降级`。已审批的变更（`change-decide --writeback` 回写后）**不计入漂移**——这正是「变更经审批即合法」的量化体现。

`--strict`：检出未审批漂移（`baseline_drift > 0`）时 exit 1（可作 CI 阻断）。

## 4. 需求易变性 KPI（F6）

`volatility_metrics` 从 RTM + 变更台账计算范围稳定性：

| KPI | 含义 |
|-----|------|
| `req_volatility_pct` | 需求易变性 = 发生过变更的需求数 / 需求总数 ×100% |
| `cr_total` / `open_cr` / `approved_cr` / `rejected_cr` | 变更单总数 / 未决 / 已批 / 已驳 |
| `avg_open_cr_age_days` | 未决 CR 平均龄（天）——越大说明变更积压 |
| `cr_per_req` | 变更密度 = 变更单数 / 需求总数 |

`metrics` 命令会附带打印这些 KPI；`report` 汇总入结构化输出。

## 5. 范围状态综合报告（report）

```bash
python3 tools/scope_tracker.py report                       # 人读文本报告 + 门禁预演
python3 tools/scope_tracker.py report --json                # 机器可读（供 MCP scope_metrics / PMO 仪表盘）
python3 tools/scope_tracker.py report --against-baseline v1.0.0
```

`--json` 输出结构（`build_report`）：

```json
{
  "generated_at": "...", "baseline_ver": "v1.0.0",
  "coverage": {"req_total": 0, "req_ae_pct": 0, "req_tc_pct": 0, "impl_pct": 0, "ver_pct": 0},
  "consistency": {"violations": 0, "creep_items": 0, "shrink_items": 0},
  "stability": {"req_volatility_pct": 0, "open_cr": 0, "avg_open_cr_age_days": 0, "cr_per_req": 0},
  "change_compliance": {"open_unapproved_must": 0, "missing_approver": 0, "stale_cr": 0, "baseline_drift": 0},
  "baseline_diff": {"base_ver": "v1.0.0", "added": [], "removed": [], "unapproved_added": [], "baseline_drift": 0},
  "health_score": 0.0, "status_dist": {}, "priority_dist": {}
}
```

文本报告额外给「门禁预演」结论（不写台账、不阻断），便于流转前自查。

## 6. 典型工作流

```bash
# 1) 需求基线固化后冻结范围基准
python3 tools/scope_tracker.py baseline freeze --ver v1.0.0
# 2) 迭代中随时比对真实漂移（CI 可 --strict 阻断）
python3 tools/scope_tracker.py baseline diff --against v1.0.0 --strict
# 3) 变更经审批回写后，漂移归零，健康分回升
python3 tools/scope_tracker.py change-decide --id CR-001 --status 已批准 --baseline-to v1.0.1 --writeback
# 4) 出范围状态报告供 PMO/MCP 消费
python3 tools/scope_tracker.py report --json
```

## 7. 最佳实践对齐

- **ArchUnit FreezingArchRule**：冻结既有基线，只阻止未经批准的劣化，允许经审批的演进。
- **IEEE 需求易变性 / PMO 度量**：以易变性、变更密度、未决龄量化范围稳定性，驱动过程改进。
- **真实 vs 名义漂移**：区分「已审批合法变更」与「未审批范围漂移」，避免把合规演进误判为失控。

---

**文档版本**：v1.2.0 **最后更新**：2026-09-08（F4 基线冻结/真实蔓延·缩水比对；F6 需求易变性 KPI + report --json）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
