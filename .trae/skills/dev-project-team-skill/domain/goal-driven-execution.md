# 目标驱动自主执行 —— 领域文档

> 编排器 §2.2-13 / §3 / §5-13 配套文档 | OPT-GOAL-001 | v1.1

## 1. 触发条件

用户下达任务时附带完成目标，或表达「自主执行」「目标驱动」「不用每步确认」时进入本模式。

## 2. SGD 结构化目标定义

### 2.1 JSON Schema（机器验证 v1.1）

AI 从用户自然语言生成 SGD JSON，`tools/goal_check.py` 可机器验证格式合法性。
Schema 定义见 `docs/sgd_schema.json`。

**v1.1 增强**：
- scope 读写分离（write_files/write_dirs vs read_files/read_dirs，v1.0 files/dirs 向后兼容）
- constraints 可机器验证（file_not_modified / file_not_created / content_not_changed）
- error_recovery 错误恢复策略（on_circuit_break / on_max_iterations）

### 2.2 SGD 回显确认（v1.1 新增）

AI 从自然语言生成 SGD 后，**必须先回显 SGD 给用户确认**：

```
我已将你的任务解析为以下结构化目标：
  目标: <statement>
  验收标准: <N> 条
    AC-1: <description> [<verify_type>]
    AC-2: ...
  约束: <constraints>
  范围: 写入 <write_files/dirs> | 读取 <read_files/dirs>
  最大轮次: <max_iterations>
  错误恢复: <on_circuit_break> / <on_max_iterations>

请确认以上解析是否正确，或指出需要修改的部分。
```

用户确认后才进入自主执行。此步骤确保 AI 正确理解了用户意图。

### 2.3 SGD 示例

```json
{
  "statement": "实现 Phase 3 全部 5 个工具 + 1 个技能",
  "acceptance_criteria": [
    {
      "id": "AC-1",
      "description": "5 个工具 CLI --help 正常",
      "verify_type": "command_pass",
      "verify_target": "python tools/arch_compliance.py --help"
    },
    {
      "id": "AC-2",
      "description": "单元测试全部通过",
      "verify_type": "test_pass",
      "verify_target": "tests/test_review_tools_p3.py"
    }
  ],
  "constraints": [
    {"type": "file_not_modified", "target": "tools/xlsx_diff.py", "description": "不修改 Phase 1/2 已有工具"},
    "所有工具支持 PROJECT_ROOT 注入"
  ],
  "scope": {
    "write_files": ["tools/*.py", "tests/test_review_tools_p3.py"],
    "write_dirs": ["tools/", ".trae/skills/role-testing/domain/", "tests/"],
    "read_dirs": ["docs/", "references/"]
  },
  "max_iterations": 10,
  "tier3_explicit": ["git commit", "git push", "solidify 固化"],
  "error_recovery": {
    "max_retries_per_step": 1,
    "on_circuit_break": "pause_wait_user",
    "on_max_iterations": "handoff"
  }
}
```

### 2.4 六种验证类型

| verify_type | 验证逻辑 | verify_target | verify_arg |
|---|---|---|---|
| `file_exists` | 文件存在 | 文件路径 | - |
| `file_contains` | 文件包含指定内容 | 文件路径 | 搜索字符串 |
| `command_pass` | 命令返回码 = 0 | 完整命令 | - |
| `test_pass` | pytest 文件全部通过 | 测试文件路径 | - |
| `count_ge` | 产出数量 >= N | 目录/glob 模式 | 数量阈值 |
| `manual` | 需人工确认 | 描述 | - |

### 2.5 三种约束验证类型（v1.1 新增）

| constraint type | 验证逻辑 | target |
|---|---|---|
| `file_not_modified` | 文件未被修改/删除 | 文件路径 |
| `file_not_created` | 未创建禁止创建的文件 | 文件路径 |
| `content_not_changed` | 文件内容未变（需 baseline hash） | 文件路径 |

纯文字约束（v1.0 兼容）仍支持，但标记为 SKIP（需人工确认）。

## 3. 端到端流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ ① SGD    │    │ ② 回显   │    │ ③ 执行   │    │ ④ 自主   │    │ ⑤ 完成度 │    │ ⑥ 一次   │
│   解析   │───▶│   确认   │───▶│   计划   │───▶│   执行   │───▶│   自检   │───▶│   性交付 │
│ + 校验   │    │ (v1.1)   │    │ + 确认   │    │   循环   │    │ goal_chk │    │ 报告+固化│
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### 步骤 1：SGD 解析与校验

AI 从用户自然语言提取 SGD JSON → 用 `docs/sgd_schema.json` 校验格式 → 格式合法则继续，不合法则向用户澄清（仅一次）。

### 步骤 2：回显确认（v1.1 新增）

AI 回显 SGD 解析结果 → 用户确认解析正确 → 保存 SGD 到台账（`goal_check.py --save`）。

### 步骤 3：执行计划 + 一次性确认

AI 输出执行计划（步骤列表 + 每步操作 + 风险分级），用户确认后进入自主执行。
确认时一并批准所有 Tier 2 操作范围（由 SGD scope.write_files/write_dirs 锁定）。

### 步骤 4：自主执行循环

```
FOR iteration = 1 TO max_iterations:
    执行下一步骤（Tier 1/2 自由执行）
    IF 遇到 Tier 3 操作:
        暂停 → 逐项确认 → 执行
    IF 写操作超出 scope.write_files/write_dirs:
        暂停 → 等用户确认
    IF 连续 2 步失败:
        按 error_recovery.on_circuit_break 处理:
            pause_wait_user → 暂停报告，等用户介入
            skip_and_continue → 跳过失败项继续
            abort_goal → 中止目标并交接
    运行 goal_check.py --goal <SGD文件> 自检
    更新台账状态（goal_check.py --status）
    IF 全部 AC = PASS:
        BREAK → 进入步骤 6
```

### 步骤 5：完成度自检

```sh
python tools/goal_check.py --goal sgd.json          # 执行验证
python tools/goal_check.py --status                  # 查看台账状态
python tools/goal_check.py --save --goal sgd.json    # 保存到台账
```

输出：每条 AC 的 PASS/FAIL + 进度百分比 + 约束验证结果 + 错误恢复建议。

### 步骤 6：一次性交付

输出交付报告（完成项 + 证据链 + Tier 3 操作记录）→ 关闭目标（`goal_check.py --close`）→ 固化 → 推送。

## 4. 持久化与交接（v1.1 新增）

### 4.1 台账持久化

活跃目标持久化到 `台账/41_活跃目标.json`，包含：
- SGD 完整定义 + 内容哈希
- 执行状态（iteration / AC 状态 / 连续失败计数）
- 变更历史（amendment_history）
- 创建/更新时间戳

### 4.2 交接文档集成

会话启动时，编排器读 `交接文档.md` 断点区。若有活跃目标驱动任务：
- 新会话自动加载 SGD + 执行状态
- 从上次中断处继续执行（无需重新定义目标）
- 目标完成后在交接文档登记完成记录

### 4.3 目标变更机制

用户中途修改需求时：
```sh
python tools/goal_check.py --amend --goal-id G-001 --goal new_sgd.json --amend-reason "用户要求增加 X 功能"
```
变更记录保留在 amendment_history 中，新增 AC 自动重置为 PENDING。

## 5. 安全护栏

| 护栏 | 触发条件 | 动作 |
|---|---|---|
| 最大轮次 | iteration > max_iterations | 按 on_max_iterations 处理（默认 handoff） |
| 写范围锁定 | 写操作超出 scope.write_files/write_dirs | 暂停等用户确认 |
| 读范围 | 未指定 read_files/read_dirs 则不限制 | 指定后超出范围暂停 |
| Tier 3 逐项 | 遇到推送/删除/solidify 等高辐射操作 | 走铁律 #15 六段合同 |
| 错误熔断 | 连续 2 步执行失败 | 按 on_circuit_break 处理（默认 pause_wait_user） |
| 约束验证 | constraints 中可机器验证项被违反 | 报告违反 + 暂停 |
| 用户中断 | 用户输入"停止" | 保留已完成成果，退出循环 |
| 铁律不降级 | 任何情况 | #7/#7a/#7b/#8/#15 始终生效 |

## 6. 与铁律 #15 的关系

目标驱动模式是铁律 #15 的**效率变体**，不是替代：

| 铁律 #15（标准模式） | 目标驱动模式 |
|---|---|
| 每个 Tier 2 操作单独确认 | Tier 2 批量确认（SGD scope.write 锁定范围） |
| 每步需输出清单等确认 | 一次性确认计划后自主推进 |
| Tier 3 逐项确认 | Tier 3 逐项确认（不变） |
| 六段合同每步走 | 六段合同仅对 Tier 3 走 |

**不变的部分**：确认词白名单、参数哈希绑定、审计台账、授权→备份→留痕。
