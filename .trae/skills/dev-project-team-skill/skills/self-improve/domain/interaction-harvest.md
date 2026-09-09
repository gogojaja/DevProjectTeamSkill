# 交互自动收割 — 确认清单模板复用

> 承载技能：self-improve（`../SKILL.md`）｜提案卡 P-002b｜版本：v1.0.0
> 补齐诉求 #6「多次必要交互 → 形成经验 → 以后遇到类似情况可参考」
> 衔接：铁律 #10 六段合同（提前一次性确认）、铁律 #13 SGD（减少交互）、self-improve §4.2 经验采集

---

## 1. 定位与边界

**解决**：把"同类任务反复出现的确认问答"跨会话沉淀为**可复用确认清单模板**，下次同类任务在 Planner 阶段提前命中、一次性确认，使交互次数随经验积累递减。

**不重复**：
- 单次任务的提前确认 → 铁律 #10 六段合同（本域只做"跨会话模板化"）；
- 目标驱动的减少交互 → 铁律 #13 SGD（本域给 SGD 的"澄清清单"喂复用模板）；
- 经验采集的存储机制 → self-improve §4.2（本域复用 `create_memory`，不新建存储）。

---

## 2. 闭环流程（触发 → 抽取 → 沉淀 → 复用）

```
① 触发 detect      同类任务确认交互 ≥ N 轮（默认 N=3），或同一澄清问题跨任务重复 ≥ 2 次
       │
② 抽取 extract     从交互历史抽取 Q&A 对 → 归纳为「确认清单模板」（任务类型 + 必答项 + 常见答案）
       │
③ 沉淀 sink        create_memory(MCP) 写外部 Memory（category=skill_experience）
       │           + 可选登记 台账/23_复用资产.csv（类型=确认清单模板）
       │
④ 复用 recall      下次同类任务 Planner 阶段 → search_memory 命中模板
                   → 提前一次性确认（铁律#10）→ 减少交互（铁律#13 SGD）
```

## 3. 触发器规格

| 参数 | 默认 | 说明 |
|------|------|------|
| `harvest_threshold_rounds` | 3 | 单个任务内确认交互轮数阈值，达到即触发抽取 |
| `repeat_question_threshold` | 2 | 同一澄清问题跨任务重复出现次数阈值 |
| `task_pattern_key` | 任务类型(§2.4.2映射表) | 归并"同类任务"的键，如"配置审计""基线固化""发布部署" |

**计数载体**：交互计数器（会话内）+ 跨任务重复检测（查 `search_memory` 是否已有同类问题的确认记录）。

## 4. 确认清单模板结构

```yaml
confirmation_template:
  id: CT-<任务类型>-<序号>
  task_pattern: "配置审计"          # 对应编排器 §2.4.2 任务类型
  required_questions:               # 必答项（提前一次性问全）
    - q: "审计范围？(全库/指定角色/指定CI类别)"
      common_answers: ["全库", "role-governance"]
    - q: "偏差处置？(登记漂移窗口/立即升版闭合)"
      common_answers: ["登记漂移窗口(决策A)"]
  reuse_count: 0                    # 命中复用次数（越多越可信）
  source_session: "<会话ID>"
```

## 5. 闭环执行系统（三要素，满足铁律 #1）

- **工具承载**：`create_memory` / `search_memory`（外部 Memory MCP，已集成见 self-improve §4.3）；可选 `台账/23_复用资产.csv` 登记（类型=确认清单模板）。
- **台账承载**：外部 Memory（主 sink）+ `23_复用资产.csv`（可选本地索引）。
- **触发**：交互计数器达 `harvest_threshold_rounds` 或重复问题达 `repeat_question_threshold` → 自动抽取沉淀；Planner 阶段自动 `search_memory` 复用。

## 6. 复用示例（呼应 P-001 dry-run）

> 任务"跑一次 config_audit"首次需确认 3 项（范围/偏差处置/输出路径）→ 达阈值触发收割 → 生成 `CT-配置审计-001`。下次同类任务 Planner 先 `search_memory("配置审计 确认清单")` 命中模板 → 直接按常见答案预填、一次性向用户确认 → 交互从 3 轮降至 1 轮。

---

**文档版本**：v1.0.0　**最后更新**：2026-09-09　**编制**：role-governance（self-improve 改进行动）　**密级**：C 级
