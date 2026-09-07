# S-02：xlsx-auto-fix —— Excel 自动修复技能

> 关联工具：T-05 xlsx_cell_fix · T-06 xlsx_verify · T-04 defect_ledger_sync

## 1. 触发条件

用户表达「自动修复」「修复缺陷」+ 缺陷清单时加载本技能。

## 2. 端到端流程

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  ① 生成修复   │    │  ② T-05      │    │  ③ T-06      │    │  ④ T-04      │
│  指令 JSON    │───▶│  批量修复     │───▶│  逐条验证     │───▶│  台账同步     │
│  从缺陷清单   │    │  备份+修改    │    │  已修复/未修复 │    │  状态更新     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### 步骤 1：生成修复指令 JSON

从缺陷清单自动推导修复指令：

```json
{
  "version": "1.0",
  "source_file": "需求文档.xlsx",
  "fixes": [
    {"defect_id": "DEF-001", "description": "字段权限不一致",
     "sheet": "测试管理-日常检查表", "cells": [
       {"ref": "D21", "old_value": "显示", "new_value": "计算后回显"}
     ]}
  ]
}
```

### 步骤 2：执行修复（T-05）

```sh
python tools/xlsx_cell_fix.py --input req.xlsx --fixes fixes.json --output fixed.xlsx
```

修复前自动备份原始文件到 `.backup/`。

### 步骤 3：验证修复（T-06）

```sh
python tools/xlsx_verify.py --input fixed.xlsx --defects defects.json
```

### 步骤 4：同步台账（T-04）

```sh
python tools/defect_ledger_sync.py --defects defects.json --ledger 台账/ --round 2
```

## 3. 安全策略

- 修复前自动备份原始 xlsx（`.backup/xlsx_fix_backup_<时间戳>`）
- 严重缺陷（`severity=严重`）修复前需人工确认
- 修复后 T-06 验证全部通过才标记为「已修复」
- 部分失败时保留原始文件，输出修复日志供人工跟进

## 4. 质量门禁

- T-06 验证修复率 = 100% → 修复完成
- T-06 验证修复率 < 100% → 标记未修复项，人工跟进
- 修复日志 JSON 须完整记录每步操作
