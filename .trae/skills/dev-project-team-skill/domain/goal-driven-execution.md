# 目标驱动自主执行 —— 领域文档

> 编排器 §2.2-13 / §3 / §5-13 配套文档 | OPT-GOAL-001 | v1.0

## 1. 触发条件

用户下达任务时附带完成目标，或表达「自主执行」「目标驱动」「不用每步确认」时进入本模式。

## 2. SGD 结构化目标定义

### 2.1 JSON Schema（机器验证）

AI 从用户自然语言生成 SGD JSON，`tools/goal_check.py` 可机器验证格式合法性。
Schema 定义见 `docs/sgd_schema.json`。

### 2.2 SGD 示例

```json
{
  "statement": "实现 Phase 3 全部 5 个工具 + 1 个技能",
  "acceptance_criteria": [
    {
      "id": "AC-1",
      "description": "5 个工具 CLI --help 正常",
      "verify_type": "command_pass",
      "verify_target": "python tools/arch_compliance.py --help",
      "verify_arg": ""
    },
    {
      "id": "AC-2",
      "description": "S-03 技能文件存在",
      "verify_type": "file_exists",
      "verify_target": ".trae/skills/role-testing/domain/docx_review.md",
      "verify_arg": ""
    },
    {
      "id": "AC-3",
      "description": "单元测试全部通过",
      "verify_type": "test_pass",
      "verify_target": "tests/test_review_tools_p3.py",
      "verify_arg": ""
    },
    {
      "id": "AC-4",
      "description": "路由表包含 S-03",
      "verify_type": "file_contains",
      "verify_target": ".trae/skills/role-testing/SKILL.md",
      "verify_arg": "docx_review"
    }
  ],
  "constraints": [
    "不修改 Phase 1/2 已有工具",
    "所有工具支持 PROJECT_ROOT 注入"
  ],
  "scope": {
    "files": ["tools/*.py", ".trae/skills/role-testing/**", "tests/test_review_tools_p3.py"],
    "dirs": ["tools/", ".trae/skills/role-testing/domain/", "tests/"]
  },
  "max_iterations": 10,
  "tier3_explicit": [
    "git commit",
    "git push (mirror/origin/mac)",
    "solidify 固化"
  ]
}
```

### 2.3 六种验证类型

| verify_type | 验证逻辑 | verify_target | verify_arg |
|---|---|---|---|
| `file_exists` | 文件存在 | 文件路径 | - |
| `file_contains` | 文件包含指定内容 | 文件路径 | 搜索字符串 |
| `command_pass` | 命令返回码 = 0 | 完整命令 | - |
| `test_pass` | pytest 文件全部通过 | 测试文件路径 | - |
| `count_ge` | 产出数量 ≥ N | 目录/glob 模式 | 数量阈值 |
| `manual` | 需人工确认 | 描述 | - |

## 3. 端到端流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ ① SGD    │    │ ② 执行   │    │ ③ 自主   │    │ ④ 完成度 │    │ ⑤ 一次   │
│   解析   │───▶│   计划   │───▶│   执行   │───▶│   自检   │───▶│   性交付 │
│ + 校验   │    │ + 确认   │    │   循环   │    │ goal_chk │    │ 报告+固化│
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### 步骤 1：SGD 解析与校验

AI 从用户自然语言提取 SGD JSON → 用 `docs/sgd_schema.json` 校验格式 → 格式合法则继续，不合法则向用户澄清（仅一次）。

### 步骤 2：执行计划 + 一次性确认

AI 输出执行计划（步骤列表 + 每步操作 + 风险分级），用户确认后进入自主执行。
确认时一并批准所有 Tier 2 操作范围（由 SGD scope 字段锁定）。

### 步骤 3：自主执行循环

```
FOR iteration = 1 TO max_iterations:
    执行下一步骤（Tier 1/2 自由执行）
    IF 遇到 Tier 3 操作:
        暂停 → 逐项确认 → 执行
    IF 遇到超出 scope 范围的操作:
        暂停 → 等用户确认
    IF 连续 2 步失败:
        暂停 → 报告当前进展
    运行 goal_check.py --goal <SGD文件> 自检
    IF 全部 AC = PASS:
        BREAK → 进入步骤 5
```

### 步骤 4：完成度自检

```sh
python tools/goal_check.py --goal sgd.json
```

输出：每条 AC 的 PASS/FAIL + 总体结论（全部通过/未达标/超限）。

### 步骤 5：一次性交付

输出交付报告（完成项 + 证据链 + Tier 3 操作记录）→ 固化 → 推送。

## 4. 安全护栏

| 护栏 | 触发条件 | 动作 |
|---|---|---|
| 最大轮次 | iteration > max_iterations | 停止循环，交接当前进展 |
| 范围锁定 | 操作超出 scope.files/scope.dirs | 暂停等用户确认 |
| Tier 3 逐项 | 遇到推送/删除/solidify 等高辐射操作 | 走铁律 #15 六段合同 |
| 错误熔断 | 连续 2 步执行失败 | 暂停报告，不盲目重试 |
| 用户中断 | 用户输入"停止" | 保留已完成成果，退出循环 |
| 铁律不降级 | 任何情况 | #7/#7a/#7b/#8/#15 始终生效 |

## 5. 与铁律 #15 的关系

目标驱动模式是铁律 #15 的**效率变体**，不是替代：

| 铁律 #15（标准模式） | 目标驱动模式 |
|---|---|
| 每个 Tier 2 操作单独确认 | Tier 2 批量确认（SGD scope 锁定范围） |
| 每步需输出清单等确认 | 一次性确认计划后自主推进 |
| Tier 3 逐项确认 | Tier 3 逐项确认（不变） |
| 六段合同每步走 | 六段合同仅对 Tier 3 走 |

**不变的部分**：确认词白名单、参数哈希绑定、审计台账、授权→备份→留痕。
