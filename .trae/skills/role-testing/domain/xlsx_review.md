# S-01：xlsx-requirement-review —— Excel 需求评审技能

> 关联工具：T-01 xlsx_dump · T-03 review_report_gen · T-06 xlsx_verify · T-04 defect_ledger_sync

## 1. 触发条件

用户表达「评审 xlsx 需求文档」「需求评审」「Excel 评审」「xlsx 检查」时加载本技能。

## 2. 端到端流程

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  ① T-01     │    │  ② 规则检查   │    │  ③ T-03      │    │  ④ T-04      │
│  xlsx_dump  │───▶│  一致性/完整性 │───▶│  报告生成     │───▶│  台账同步     │
│  导出全量    │    │  字段/权限/排序│    │  CSV 落盘     │    │  缺陷登记     │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### 步骤 1：导出 xlsx 内容

```sh
python tools/xlsx_dump.py --input <需求文档.xlsx> --output dump.json --format json
```

读取 dump.json 获取全量单元格数据（含工作表名/单元格坐标/值/合并信息）。

### 步骤 2：规则配置检查

按外置规则（YAML/JSON）逐项检查：

| 检查维度 | 规则示例 | 缺陷级别 |
|---|---|---|
| 字段权限一致性 | 界面展示字段 vs 表单标记字段是否一致 | 严重 |
| 下钻参数完整性 | 列表页字段是否有对应详情页字段 | 一般 |
| 排序规则明确性 | 列表是否有默认排序规则 | 建议 |
| 术语一致性 | 同一概念在不同工作表是否用同一术语 | 一般 |
| 除零/空值处理 | 计算字段是否标注除零/空值处理策略 | 严重 |
| 数据类型标注 | 字段是否有明确的数据类型/格式要求 | 建议 |

规则配置文件路径：`requirements/review_rules.json`（可选，无则使用内置默认规则）。

### 步骤 3：生成评审报告

将步骤 2 发现的缺陷组装为 JSON → 调用 T-03 生成标准报告：

```python
# 组装缺陷 JSON
defects_json = {
    "object": "需求文档名称",
    "version_tag": "V1.0",
    "reviewer": "AI Agent",
    "review_date": "2026-09-07",
    "defects": [
        {"id": "DEF-001", "severity": "严重", "module": "表单A",
         "type": "一致性", "description": "...", "suggestion": "..."}
    ],
    "dimensions": [
        {"name": "完整性", "weight": "25%", "score": "80%", "verdict": "通过"},
        {"name": "一致性", "weight": "25%", "score": "60%", "verdict": "部分通过"}
    ]
}
```

```sh
python tools/review_report_gen.py --defects defects.json --object "需求文档" --version "V1.0"
```

### 步骤 4：同步缺陷台账

```sh
python tools/defect_ledger_sync.py --defects defects.json --ledger 台账/ --round 1
```

### 步骤 5（可选）：修复后验证

```sh
python tools/xlsx_verify.py --input <修复后.xlsx> --defects defects.json
```

## 3. 输出产物

| 产物 | 路径 | 格式 |
|---|---|---|
| xlsx 导出 | docs/reviews/<名称>_dump.json | JSON |
| 缺陷清单 | docs/reviews/缺陷清单_<对象>_<版本>.csv | CSV UTF-8 BOM |
| 评审报告 | docs/reviews/评审报告_<对象>_<版本>.csv | CSV UTF-8 BOM |
| 验证矩阵 | docs/reviews/<名称>_verify.csv | CSV UTF-8 BOM |

## 4. 质量门禁

- 严重缺陷数 = 0 → 评审通过
- 严重缺陷数 > 0 → 评审不通过，需修复后重审
- 一般缺陷数 > 5 → 建议修复
- 全部缺陷须有唯一 ID（DEF-NNN）+ 可追溯建议
