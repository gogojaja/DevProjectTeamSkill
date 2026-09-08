# RAID 与风险管理标准（RAID & Risk Management）

> 版权声明：`../COPYRIGHT.md`
> 适用：所有启用本技能库的软件项目（对齐 PMBOK 7th 风险/问题绩效域 · PMBOK 6 规划/实施/监督风险 · RAID（Risks/Assumptions/Issues/Dependencies）· ISO 31000 风险管理 · PRINCE2 风险与问题管理 · 问题升级机制 P1~P4）
> 调用：阶段流转门禁 `stage_review` / 定期风险巡检调用 `tools/raid_ops.py` 自动扫描分级
> 权威实现：可独立部署技能 `risk-mgmt`（`tools/raid_ops.py` v1.0.0，内化自 dev-project-mgmt `raid_manager.py` + MCP `risk_scan`）——RAID/风险逻辑单一信源，角色包/MCP 一律引用或委派

---

## 1. 问题定义

软件项目风险与问题反复出现两类失控：

- **风险失察（risk blindness）**：风险未系统登记、未按概率×影响量化分级，高风险与低风险混同处置，直到爆发成问题才被动响应。
- **RAID 割裂**：风险（Risk）、假设（Assumption）、问题（Issue）、依赖（Dependency）分散跟踪或台账外私下管理，缺单一事实来源，升级路径不清、Owner 缺位。

根因：**风险未作为受控 RAID 登记册持续治理**——既缺「有哪些风险/假设/问题/依赖」（RAID 四维登记册），也缺「风险多大、怎么应对、何时升级」（概率×影响分级 + 应对策略 + 升级阶梯）。

本标准在 PMBOK/ISO 31000 风险管理框架上，补齐 **RAID 四维统一治理**能力：登记册、状态机、概率×影响分级、应对策略、问题升级机制、变更协同。

---

## 2. 行业最佳实践（依据）

| 来源 | 核心主张 | 本标准落点 |
|------|----------|-----------|
| PMBOK 7th 风险/问题绩效域 | 风险与问题作为绩效域持续治理，量化不确定性 | §3 RAID 四维；§4 分级 |
| PMBOK 6 规划/实施/监督风险 | 风险登记册 + 定性/定量分析 + 应对规划 + 监督 | §3；§5 巡检；§6 应对 |
| RAID（Risks/Assumptions/Issues/Dependencies） | 四类统一登记册，单一事实来源 | §3 RAID 四维 |
| ISO 31000 风险管理 | 风险识别→分析→评价→应对→监控闭环 | §5 巡检流程；§6 应对 |
| PRINCE2 风险与问题管理 | 风险预算/应对 + 问题分级升级 + 日常日志 | §7 问题分级；§8 升级阶梯 |
| 概率×影响矩阵（P-I Matrix） | 风险分 = 概率 × 影响，映射等级优先级 | §4 分级公式 |
| 问题升级机制（Escalation） | P1~P4 分级 + 四级升级阶梯 + 单一 Owner + 响应时限 | §7；§8 |
| RACI 唯一 A | 每条问题唯一负责人（Accountable） | §8 单一 Owner |

结论：**风险必须作为受控 RAID 登记册 + 概率×影响量化分级 + 应对策略闭环 + 问题分级升级可审计**，而非台账外主观跟踪。

---

## 3. RAID 四维与登记册 schema

### 3.1 RAID 四维定义

| 维度 | 含义 | 默认状态 | 关注点 |
|------|------|----------|--------|
| `risk`（风险） | 尚未发生、可能发生的不确定事件 | mitigating | 预防 + 应对预案 |
| `assumption`（假设） | 未经证实但暂视为真的前提 | open | 验证 + 失效转风险 |
| `issue`（问题） | 已经发生、正在影响的障碍 | investigating | 解决 + 升级 |
| `dependency`（依赖） | 受制于外部/其他任务的约束 | open | 跟踪 + 解耦 |

### 3.2 登记册标识符与列

风险登记册 = `台账/12_风险问题台账.csv`（单一事实来源，兼容旧名 `RAID台账.csv` 只读）。

| 产物 | 前缀 | 示例 |
|------|------|------|
| RAID 条目 | `RAID-<nnn>` | RAID-001 |

规范列（各项目历史列名有差异，工具读取时**防御式别名**兼容）：

| 列 | 含义 | 别名回退 |
|----|------|----------|
| RAID_ID | 唯一编号（不复用） | 风险编号 / 编号 / ID / id |
| 类型 | risk/assumption/issue/dependency | 类型(风险/问题) / RAID类型 / type |
| 描述 | 风险/问题描述 | 风险描述 / 问题描述 / desc |
| 概率 | 高/中/低（或 1~5） | 可能性 / probability |
| 影响 | 高/中/低（或 1~5） | 严重度 / impact |
| 优先级 | P1~P4 | 问题级别(P1~P4) / 问题级别 / 级别 / priority |
| 状态 | open/mitigating/investigating/closed | status |
| 责任人 | 唯一 Owner | Owner / owner / 负责人 |
| 登记日期 | 创建时间戳 | 创建日期 / 登记时间 / created |
| 关闭日期 | 关闭时间戳 | 解决日期 / closed_date |
| 备注 | 应对方案/升级记录 | 应对方案 / notes |

> 向后兼容：既有台账若为差异 schema，写入时保留既有列 + 补规范列（非破坏式），读取一律走别名回退。

---

## 4. 风险分级（概率×影响，权威公式）

### 4.1 等级词 → 数值（吸收 MCP `risk_scan._parse_level`）

| 等级词 | 数值 |
|--------|------|
| 高 / high / h / 4 / 5 | 4 |
| 中 / medium / m / 3 | 3 |
| 低 / low / l / 1 / 2 | 2 |
| 缺省（无值） | 1 |

### 4.2 风险分 → P1~P4（`SEVERITY_MAP`）

**风险分 = 概率 × 影响**（最高 4×4=16）：

| 等级 | 风险分阈值 | 处理 | 响应时限 |
|------|-----------|------|----------|
| P1 | ≥ 12 | 立即制定应对方案，升级决策 | ≤ 4h |
| P2 | ≥ 8 | 制定应对预案，持续监控 | ≤ 1 个工作日 |
| P3 | ≥ 4 | 登记监测，定期复核 | ≤ 3 个工作日 |
| P4 | < 4 | 记录即可 | — |

- `add` 未指定 `--priority` 时按风险分自动定级 P1~P4。
- P1 高风险（≥12）→ `add`/`scan` 自动 `[WARN]` 提示立即升级。

---

## 5. 状态机与风险巡检

### 5.1 状态流转（权威规则，与 dev-project-mgmt `raid_manager` 一致）

```
open → {mitigating, investigating, closed}
mitigating → {closed, open}
investigating → {closed, open}
closed → {}（终态，不可再变更）
```

- 类型默认状态（`TYPE_DEFAULT_STATUS`）：risk→mitigating / assumption→open / issue→investigating / dependency→open。
- 非法流转（如 mitigating→investigating）→ rc1，台账不变。
- 流转到 closed 自动填 `关闭日期`；重复 close 已关闭条目 → rc0（幂等）。

### 5.2 巡检流程（五步）

① 读取台账 → ② 状态复核 → ③ 新风险识别（结合进度/成本/质量/安全数据）→ ④ 概率×影响等级评估 → ⑤ 登记册更新。

- **触发时机**：定期巡检（阶段切换/周期复盘）、项目重大变更后。
- `scan --severity <P1~P4>`：输出风险分 ≥ 阈值的**未关闭**条目，按风险分降序；排除 closed（已闭环不预警）。

---

## 6. 风险应对策略

| 应对策略 | 适用场景 | 状态落地 |
|----------|----------|----------|
| 规避（Avoid） | 高风险且可避免 | 消除风险源，`update` 记方案 |
| 减轻（Mitigate） | 降低概率或影响 | `mitigating` + 重估概率/影响 |
| 转移（Transfer） | 可转移至第三方 | `update --owner` 改责任人 |
| 接受（Accept） | 低风险且应对成本高 | 登记监测 + 应急储备 |
| 应急预案（Contingency） | 高风险但不可控 | 预设触发条件 + 应急动作 |

- 应对后须重估风险分（概率/影响下调后重新 `scan` 确认降级）。
- P1 高风险不可仅登记不处置，须立即制定应对方案 + 升级。

---

## 7. 问题分级（P1~P4）

启动阶段 `role-project-init` 的 `define_issue_escalation` 确立，本技能承接巡检期升级执行：

| 级别 | 定义 | 示例 | 响应时限 |
|------|------|------|----------|
| P1 阻断 | 项目无法推进/主流程不可用/数据丢失 | 生产阻断、关键链路宕机、范围致命冲突 | ≤ 4h |
| P2 高 | 关键功能受阻/里程碑延期风险 | 核心接口不可用、依赖缺失、资源冲突未决 | ≤ 1 个工作日 |
| P3 中 | 局部功能受影响/可绕行 | 非核心缺陷、进度轻微滞后 | ≤ 3 个工作日 |
| P4 低 | 一般性问题/优化建议 | 文档缺失、体验优化 | 记录即可 |

> 风险分自动映射 P1~P4（§4.2）；issue 类可另按业务影响定级。

---

## 8. 升级阶梯（四级路径）

| 级别 | 处理主体 | 职责 | 响应时限 |
|------|----------|------|----------|
| L1 | 项目团队（Owner） | 识别问题、记录台账、尝试解决 | 问题发生时 |
| L2 | 项目经理 | 分析决策、资源调配、跨团队协调 | P1/P2 即时、P3 ≤ 1 工作日 |
| L3 | 指导委员会/项目委员会 | 决策仲裁、范围/预算/优先级裁决 | P1 ≤ 1 个工作日 |
| L4 | 高层/Sponsor | 战略干预、资源追加、终止决策 | 按治理节奏 |

- **单一 Owner 原则**：每条问题唯一 Owner（对齐 RACI 唯一 A），Owner 缺失不得升级，路径清晰可追溯。
- **升级条件**：超过本级响应时限未决 / 超出本级权限（预算·范围·人员）/ 多干系人冲突无法裁决。
- **协同**：P1/P2 升级与 multi-perspective-validation 的 P0~P6 仲裁、`change_audit` 变更审计衔接；升级不经审批链外绕过，全程留痕（涉高危操作另记 `13_安全审计台账.csv`）。
- **关闭**：问题处理完成须记解决动作与验证结果，Owner 确认后 `close`，关闭记录在阶段评审复核。

---

## 9. 退出码与 CLI 契约（`raid_ops.py`）

```bash
python3 tools/raid_ops.py add --type risk --desc "..." [--probability 高] [--impact 高] [--owner 张三] [--notes "..."]
python3 tools/raid_ops.py list [--type risk] [--status open]
python3 tools/raid_ops.py update --id RAID-001 [--status mitigating] [--owner 李四] [--probability 中] [--notes "..."]
python3 tools/raid_ops.py close --id RAID-001
python3 tools/raid_ops.py scan [--severity P1] [--json]
```

| 退出码 | 含义 |
|--------|------|
| `0` | 成功；或无数据友好提示（台账为空 → scan 提示无可扫描风险）；重复 close 已关闭（幂等） |
| `1` | 参数非法：无效 RAID 类型 / 条目不存在 / 非法状态流转 |

- 工具经 `PROJECT_ROOT` 环境变量解析目标项目根，无论副本位于何处，读写的都是目标项目的 `台账/12_风险问题台账.csv`。

---

## 10. 流程嵌入（何时做）

- **启动阶段**：`role-project-init` 建初始风险登记册（七类风险预设）+ 确立 P1~P4 分级与升级阶梯。
- **执行阶段**：`add` 登记新风险/假设/问题/依赖；`update` 推进状态流转 + 应对策略；成本消耗/进度偏差联动登记（委派 `schedule-cost`）。
- **每阶段 `stage_review`**：自动跑 `raid_ops.py scan`（概率×影响分级），P1 高风险无应对方案/未升级不得流转。
- **定期巡检/重大变更后**：`scan` 重新识别风险；变更联动 `scope-tracking`（范围）/`role-architecture`（架构）。
- **监控/汇报**：`scan --json` 供 MCP `risk_scan`/PMO 仪表盘消费；跨项目风险升级归 `role-program-mgmt`。

---

**文档版本**：v1.0.0　**最后更新**：2026-09-08（首个 RAID 与风险管理标准：§3 RAID 四维 + 登记册防御式别名 schema；§4 概率×影响分级权威公式 + P1~P4 阈值；§5 状态机（与 dev-project-mgmt raid_manager 一致）+ 巡检流程；§6 应对策略五选；§7 问题分级 P1~P4；§8 四级升级阶梯 + 单一 Owner；§9 CLI 退出码契约；对齐 raid_ops.py v1.0.0（内化自 dev-project-mgmt raid_manager.py + MCP risk_scan），支撑独立可部署技能 risk-mgmt）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
