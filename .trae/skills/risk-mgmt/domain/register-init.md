# 风险登记册初始化（Risk Register Init）

> 所属技能：`risk-mgmt` v1.0.0 · 标准：`references/raid_standard.md` §1-§3

## 1. RAID 四维定义

风险登记册以 RAID 四维统一承载，写入 `台账/12_风险问题台账.csv`（单一事实来源）：

| 维度 | 含义 | 默认状态 | 示例 |
|------|------|----------|------|
| `risk`（风险） | 尚未发生、可能发生的不确定事件 | mitigating | 核心人员流失、技术选型失败 |
| `assumption`（假设） | 未经证实但暂视为真的前提 | open | 第三方接口按期交付 |
| `issue`（问题） | 已经发生、正在影响的障碍 | investigating | 生产环境阻断、依赖缺失 |
| `dependency`（依赖） | 受制于外部/其他任务的约束 | open | 上游数据未就绪 |

## 2. 七类初始风险预设

项目初始化时建立初始风险登记册，预设七类常见风险 + 应对策略：

| 风险类别 | 示例风险 | 应对策略 |
|----------|----------|----------|
| 范围风险 | 需求蔓延、范围缩水 | 变更审批 + 范围冻结机制（委派 `scope-tracking`） |
| 进度风险 | 里程碑延期、任务滞后 | 进度预警 + EVM 监控（委派 `schedule-cost`） |
| 成本风险 | 成本超支、资源不足 | 成本阈值 + 超支预警（委派 `schedule-cost`） |
| 技术风险 | 技术选型失败、兼容性问题 | POC 验证 + 备选方案 |
| 质量风险 | 缺陷率高、覆盖率不足 | 质量门禁 + 缺陷闭环（委派 `role-testing`） |
| 安全风险 | 漏洞、数据泄露 | SAST/SCA 扫描 + 安全审计（委派 `role-governance` security-audit） |
| 人员风险 | 关键人员流失 | 知识交接 + 文档化 |

## 3. 登记册 schema（12_风险问题台账.csv）

规范列（防御式别名兼容各项目差异 schema）：

| 列 | 说明 |
|----|------|
| RAID_ID | 唯一编号 `RAID-<nnn>`，自动生成不复用 |
| 类型 | risk/assumption/issue/dependency |
| 描述 | 风险/问题描述 |
| 概率 | 高/中/低（或 1~5） |
| 影响 | 高/中/低（或 1~5） |
| 优先级 | P1~P4（缺省按风险分自动定级） |
| 状态 | open/mitigating/investigating/closed |
| 责任人 | 唯一 Owner（对齐 RACI 唯一 A） |
| 登记日期 / 关闭日期 | 生命周期时间戳 |
| 备注 | 应对方案/升级记录 |

## 4. 登记落地（add）

```bash
python3 tools/raid_ops.py add --type risk --desc "核心人员流失" --probability 高 --impact 高 --owner 张三 --notes "知识交接+文档化"
```

- 自动生成 `RAID-<nnn>`（顺序递增）；类型默认状态自动填入；未指定 `--priority` 时按风险分（概率×影响）自动定级 P1~P4。
- 无效 RAID 类型（非四维）→ rc1，不写台账。
- P1 高风险（风险分≥12）→ `add` 自动 `[WARN] P1 高风险，须立即升级并制定应对方案`。
- 既有台账若为差异 schema，沿用既有表头 + 补规范列（非破坏式追加）。

**DoD**：初始风险登记册完成 · 七类风险已预设 · RAID 四维 schema 就绪 · 每条有唯一 Owner。

> 边界：本环节建登记册与初始风险；巡检分级见 `scan.md`；应对策略见 `response.md`；升级协同见 `coordination.md`。
