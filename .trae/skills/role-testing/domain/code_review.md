# S-04：code-review-agent —— AI 代码审查技能

> 关联工具：T-08 code_review_agent · desensitize 脱敏扫描 · check_review_artifacts 门禁

## 1. 触发条件

用户表达「代码评审」「review PR」「代码走查」「提交后自动触发」时加载本技能。
post-commit 钩子自动触发（经 `agent_loop_v2.py --compat v1`）。

## 2. 端到端流程

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  ① Git Diff  │    │  ② T-08      │    │  ③ 脱敏扫描   │    │  ④ 门禁判定   │
│  解析变更文件  │───▶│  多层分析     │───▶│  A/B 级检查   │───▶│  通过/驳回   │
│  过滤非源码    │    │  L1+L2+L3    │    │  敏感信息      │    │  报告落盘     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### 步骤 1：获取代码变更

```sh
# 审查最近 1 次提交
python tools/code_review_agent.py --diff HEAD~1 --dry-run

# 审查最近 3 次提交
python tools/code_review_agent.py --diff HEAD~3..HEAD --dry-run

# 审查暂存区
python tools/code_review_agent.py --diff staged --dry-run
```

### 步骤 2：多层分析（T-08 自动执行）

| 层级 | 分析内容 | 自动/手动 |
|---|---|---|
| Layer 1 | AST 静态分析（语法/复杂度/命名） | 自动 |
| Layer 2 | 影响范围分析（依赖图/变更传播） | 自动 |
| Layer 3 | LLM 语义评审（逻辑缺陷/安全漏洞/设计模式） | 可选（需强模型） |

降级策略（§14.1）：
- 强环境 → L1+L2+L3
- 弱环境 → L1+L2
- 最弱 → L1（仅 ast 静态分析）

### 步骤 3：脱敏扫描

对评审报告执行脱敏扫描，确保无 A/B 级敏感信息泄漏：

```sh
python tools/desensitize/desensitize.py --scan docs/reviews/代码评审报告_*.csv
```

### 步骤 4：门禁判定

根据评审结果判定是否通过：

| 指标 | 通过 | 警告 | 驳回 |
|---|---|---|---|
| 严重问题数 | 0 | 1~2 | ≥3 |
| 误报率（Layer 3） | ≤10% | 10~30% | >30% |
| 脱敏扫描 | A/B 全通过 | B 级告警 | A 级发现 |

### 步骤 5：产物落盘

```
docs/reviews/代码评审报告_<日期>.csv    # 结构化评审报告
docs/reviews/代码评审摘要_<日期>.csv    # 摘要统计
```

## 3. 与 agent_loop_v2 集成

post-commit 钩子自动触发时，决策引擎匹配 `git.commit` 事件：

```json
{
  "pattern": "git.commit",
  "tier": 2,
  "action": "code_review",
  "auto": true,
  "params": {"diff_range": "HEAD~1", "dry_run": false}
}
```

Agent 自动执行 T-08 → 脱敏扫描 → 报告落盘 → 台账留痕。

## 4. 与 quality_gate.py 分工

| 维度 | T-08 code_review_agent | quality_gate.py CodeReviewer |
|---|---|---|
| 定位 | 深度评审（发现问题+定位根因） | 门禁判定（通过/驳回） |
| 触发 | 手动/post-commit/PR | solidify/发布前 |
| 输出 | 详细问题清单+建议 | 通过/驳回结论 |
| 层级 | L1+L2+L3 多层 | L1 快速扫描 |

## 5. 质量门禁

- 每次评审须输出结构化 CSV 报告
- 严重问题必须有人工跟进记录
- 脱敏扫描 A 级发现 → 立即驳回
- 评审报告须通过 `check_review_artifacts.py` 校验
