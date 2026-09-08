---
name: "okr-strategy"
description: "用户提到OKR/目标与关键结果/KPI/战略对齐/战略主题/对齐度检查/孤儿项目/季度目标/绩效指标时加载本 OKR 战略对齐技能：负责 OKR 层级管理（组织级 Objective→项目群 Key Result→项目 KPI）、OKR 进度更新与季度评分（0~1.0，0.6~0.7 理想区间）、项目-战略主题映射与对齐度评分、对齐度审计（孤儿项目检测）。可脱离编排器独立部署运行。用户说OKR/战略对齐/KPI/对齐度审计/孤儿项目时加载。"
---

# okr-strategy OKR 战略对齐技能

> 版权：`../shared/references/COPYRIGHT.md` Token：`../shared/references/token_standard.md`
> 权威工具：`tools/okr_ops.py`（create/update/score/map/audit/dashboard）
> 对齐：Doerr OKR · Kaplan-Norton BSC · SAFe 6.0 Strategic Themes

## 1. 元数据

- **技能版本**：v1.0.0 **发布日期**：2026-09-08
- **变更记录**：
  - v1.0.0：首个**合规独立可部署**版本——从编排器内嵌子技能提升为 `.trae/skills/` 顶层自包含技能；补 YAML frontmatter、三段版本号、闭环执行系统、`skill.manifest.json`（打包期注入 `okr_ops.py`+`test_okr_ops.py`）；注册 SKILL_INDEX 条目 25 + STANDALONE_SKILLS。原 5 action 能力、OKR 层级模型、评分规则、对齐度审计规则全部保留。
- **参考标准**：Doerr《Measure What Matters》OKR · Kaplan-Norton 平衡计分卡 · SAFe 6.0 Strategic Themes
- **定位**：组织战略目标到项目的映射链——确保每个项目都对齐组织战略（把事做在正确方向上）。

## 2. 触发规则

用户表达「OKR / 目标与关键结果 / KPI / 战略对齐 / 战略主题 / 对齐度检查 / 孤儿项目 / 季度目标 / 绩效指标」时加载本技能。

| 环节 | action | 功能 | 台账 | CLI |
|------|--------|------|------|-----|
| OKR 创建 | okr_create | 组织级 Objective→项目群 KR→项目 KPI | 46_OKR登记.csv | `create` |
| 进度更新 | okr_update | 月度检查、调整完成百分比 | 46_OKR登记.csv | `update` |
| 季度评分 | okr_score | 0~1.0 评分（0.6~0.7 理想区间） | 46_OKR登记.csv | `score` |
| 战略映射 | map_alignment | 项目-战略主题映射 + 对齐度评分 | 47_战略对齐矩阵.csv | `map` |
| 对齐审计 | audit_alignment | 检测孤儿项目（不对齐任何战略主题） | 47_战略对齐矩阵.csv | `audit` |

**边界**：组合投资决策→`portfolio-mgmt`；战略对齐→本技能；项目执行→`role-project-mgmt`/`role-program-mgmt`。

## 3. OKR 层级与评分模型（单一信源）

```
组织级 Objective（定性、鼓舞人心）
  ├── Key Result 1（定量、可衡量）← 项目群 A 贡献
  ├── Key Result 2 ← 项目群 B + 项目 C 贡献
  └── Key Result 3 ← 项目 D 贡献
项目群 Key Results └── 项目 KPIs（领先/滞后指标）
```

**OKR 评分规则**（与 `okr_ops.py` cmd_score 一致）：

| 评分区间 | 状态 | 含义 |
|---------|------|------|
| 0.0~0.3 | 失败 | 需复盘根因 |
| 0.4~0.5 | 未达预期 | 需改进 |
| 0.6~0.7 | 理想 | 挑战性目标合理达成 |
| 0.8~0.9 | 超额 | 目标可能不够挑战 |
| 1.0 | 过于保守 | 下季度需提高难度 |

**对齐度审计规则**：项目映射到 ≥1 战略主题且评分 ≥3 = **已对齐**；映射但评分 <3 = **弱对齐**；未映射任何战略主题 = **孤儿项目**（预警，`audit` 退出码 1）。

## 4. 工具调用（CLI）

权威工具 `tools/okr_ops.py`（Python3，零第三方依赖）：

```bash
python3 tools/okr_ops.py create --level org --objective "提升市场份额" [--kr "市占率达15%"] [--owner "VP-Sales"] [--period Q3] [--target "15%"]
python3 tools/okr_ops.py update --id OKR-001 --progress 65 [--actual "12%"]
python3 tools/okr_ops.py score --id OKR-001 --score 0.7
python3 tools/okr_ops.py map --project "项目X" --theme "数字化转型" --score 4
python3 tools/okr_ops.py audit
python3 tools/okr_ops.py dashboard
```

**台账产物**（UTF-8 with BOM）：`46_OKR登记.csv`（编号/层级/Objective/KeyResult_KPI/Owner/周期/目标值/实际值/完成%/评分/状态/创建日期）· `47_战略对齐矩阵.csv`（编号/项目名称/战略主题/对齐度评分/映射日期/确认状态）。

**退出码**：`0`=成功/无孤儿；`1`=参数非法（评分越界/OKR 不存在）或审计检出孤儿项目。

## 5. 核心原则

1. **层级贯通**：组织 Objective→项目群 KR→项目 KPI 逐级分解，禁止断层。
2. **每条 OKR 有 Owner**：无 Owner 的 OKR 不得创建。
3. **挑战性目标**：理想评分 0.6~0.7，长期 1.0 说明目标过于保守。
4. **无孤儿项目**：每个项目必须映射至少 1 个战略主题，否则预警。
5. **对齐驱动优先级**：对齐度评分作为组合评审（portfolio-mgmt）的输入。

## 6. 输出规范

- 所有台账 CSV（UTF-8 with BOM，禁止 .xlsx）；输出回显关键行 + 计数。
- 边界仅 OKR/战略对齐域；不承接组合投资决策（归 portfolio-mgmt）、不承接项目日常执行（归 role-project-mgmt）。

## 7. 独立部署与镜像同步

本技能为**自包含可独立部署技能**：权威工具保留在仓库根 `tools/okr_ops.py`（单一信源），`skill.manifest.json` 声明打包/部署期注入 `okr_ops.py`+`test_okr_ops.py` 副本。`package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 按 manifest 注入后，产物含 `SKILL.md + skill.manifest.json + tools/ + tests/`，脱离编排器即可 `python3 tools/okr_ops.py ...` 运行。

**分发清单（STANDALONE_SKILLS）**：已登记为 `package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 的 `STANDALONE_SKILLS`（独立于 11 个 `ALL_ROLES`），全量同步（无参）自动纳入；按需 `--role okr-strategy` 单独分发。**镜像目标**：`.github/skills/` · `.claude/skills/` · `.agents/skills/` · 全局 opencode 库。

> **同步命令**：改动后运行 `python3 tools/package_skills.py` + `python3 tools/deploy_skills.py`。

---

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求创建/更新/评分 OKR 或检查项目战略对齐度；
- 前置：需确认战略主题定义、项目清单；
- 不适用：组合投资决策（归 portfolio-mgmt）、项目日常执行（归 role-project-mgmt）。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | OKR/对齐需求明确 | 确认战略主题与项目清单 | 读取现有台账 |
| 执行中 | OKR 创建/更新/评分中 | 产出形成 | 按 action 执行 |
| 校验中 | 对齐审计完成 | 孤儿项目处理 | 预警 + 建议 |
| 阻塞 | 缺战略主题/OKR 无 Owner | 补充信息 | 暂停并记录阻塞 |
| 完成 | 台账更新 | 归档 | 通知相关方 |
| 回退 | 检出孤儿项目/评分越界 | 补映射或修正评分 | 预警并限期整改 |

### 3. 执行动作层
- 步骤 1：`create` 创建 OKR（层级 org/program/project + Owner + 周期）；
- 步骤 2：`update` 更新完成百分比/实际值；
- 步骤 3：`score` 季度评分（0~1.0，映射状态失败/未达/理想/超额/保守）；
- 步骤 4：`map` 项目-战略主题映射（对齐度 1~5）；
- 步骤 5：`audit` 对齐度审计（孤儿项目检测，退出码 1 预警）；`dashboard` 汇总；
- 输入输出约束：OKR 必有 Owner；评分 0~1.0、对齐度 1~5；台账 UTF-8 BOM。

### 4. 验收门禁
- 必须产出物：OKR 登记表（46）、战略对齐矩阵（47）、对齐审计报告；
- 通过条件：OKR 层级完整、每条有 Owner、对齐映射覆盖全部项目、无未处理孤儿；
- 失败条件：存在孤儿项目未处理、OKR 无 Owner、评分/对齐度越界；
- 审核对象：role-program-mgmt（战略对齐）+ portfolio-mgmt（组合输入）。

### 5. 失败处理
- 失败类型：战略主题缺失、OKR 无 Owner、评分越界（非 0~1.0）、孤儿项目、对齐度越界（非 1~5）；
- 恢复策略：补战略主题/Owner 后重建；孤儿项目须尽快映射，否则建议暂停或终止；评分越界则拒绝写入；
- 是否需要人工确认：孤儿项目处置（暂停/终止/补映射）须人工确认。

### 6. 产出与交接
- 产出物列表：46_OKR登记.csv、47_战略对齐矩阵.csv、对齐审计报告、OKR 仪表盘；
- 交接对象：portfolio-mgmt（对齐度作为组合评分输入）、role-program-mgmt（项目群战略对齐）、MCP okr_manage/alignment_check；
- 下一步动作：已对齐 → 纳入组合评审；孤儿 → 预警并限期整改。

### 7. 审计记录
- 执行时间：create/update/score/map/audit 时间点（台账创建日期/映射日期）；
- 关键参数：OKR 层级、Owner、周期、完成%、评分、对齐度评分；
- 关键决策：OKR 状态判定（失败/未达/理想/超额/保守）、孤儿项目预警；
- 结果证据：46/47 台账 CSV、对齐审计报告、仪表盘输出。

---

**文档版本**：v1.0.0 **最后更新**：2026-09-08（从编排器内嵌子技能提升为顶层独立可部署技能；补 frontmatter/三段版本/闭环执行系统/skill.manifest.json；注册 SKILL_INDEX 条目25 + STANDALONE_SKILLS；原 5 action 能力与 OKR 层级/评分/对齐审计规则全保留）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
