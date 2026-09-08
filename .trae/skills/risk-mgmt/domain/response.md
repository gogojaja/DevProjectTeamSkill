# 风险应对（Risk Response）

> 所属技能：`risk-mgmt` v1.0.0 · 标准：`references/raid_standard.md` §6

## 1. 应对策略（五选一或组合）

| 应对策略 | 适用场景 | 落地动作 |
|----------|----------|----------|
| 规避（Avoid） | 高风险且可避免 | 消除风险源/改变计划，`update` 记应对方案 |
| 减轻（Mitigate） | 降低概率或影响 | 状态转 `mitigating`，`update --probability/--impact` 重估 |
| 转移（Transfer） | 可转移至第三方 | 外包/保险/合同条款，`update --owner` 改责任人 |
| 接受（Accept） | 低风险且应对成本高 | 登记监测，预留应急储备，`notes` 记接受理由 |
| 应急预案（Contingency） | 高风险但不可控 | 预设触发条件 + 应急动作，`notes` 记预案 |

## 2. 状态流转（受控，与 dev-project-mgmt 一致）

```
open ──→ mitigating ──→ closed（终态）
  │           │  ↑
  │           └──┘（可回退 open 重开）
  ├──→ investigating ──→ closed
  │           │  ↑
  │           └──┘（可回退 open 重开）
  └──→ closed
```

| 当前状态 | 允许流转到 |
|----------|-----------|
| open | mitigating / investigating / closed |
| mitigating | closed / open |
| investigating | closed / open |
| closed | —（终态，不可再变更） |

- 类型默认状态：risk→mitigating / assumption→open / issue→investigating / dependency→open。
- 非法流转（如 mitigating→investigating）→ rc1，台账不变。

## 3. 应对落地（update / close）

```bash
# 推进状态 + 记应对方案（可同步重估概率/影响、改责任人）
python3 tools/raid_ops.py update --id RAID-001 --status mitigating --owner 李四 --notes "启用备选技术方案，概率降为中"
python3 tools/raid_ops.py update --id RAID-001 --probability 中 --impact 高

# 风险已消除/关闭（终态校验，自动填关闭日期）
python3 tools/raid_ops.py close --id RAID-001
```

- `update --status closed` 自动填 `关闭日期`；`close` 等价于 `update --status closed`（含终态校验）。
- 重复 `close` 已关闭条目 → rc0（幂等，提示已关闭）。
- 条目不存在 → rc1。
- 应对后须重估风险分：概率/影响下调后重新 `scan` 确认降级。

## 4. 高风险强制动作

- **P1 高风险（风险分≥12）**：立即制定应对方案 + 升级决策（见 `coordination.md` 升级阶梯），不可仅登记不处置。
- **高风险不可控**：预设应急预案触发条件（何时启动、启动后动作、责任人）。
- 应对无效/风险恶化 → 重新分级 + 升级更高决策层。

**DoD**：应对策略已确定 · 状态流转合法 · 高风险预案已预设 · 应对后已重估风险分。

> 边界：本环节做应对策略与状态流转；分级扫描见 `scan.md`；升级阶梯与变更协同见 `coordination.md`。
