---
name: "stakeholder-comms"
description: "用户提到干系人管理/沟通计划/干系人映射/权力利益/参与度评估/沟通矩阵/沟通频率/沟通渠道/沟通记录时加载本干系人沟通管理技能：负责干系人权力-利益矩阵映射（重点管理/保持满意/保持知情/最少关注）、参与度评估（U/N/C/S/A 五级 + 差距策略）、沟通计划（对象/内容/频率/渠道/责任人）、沟通记录。可脱离编排器独立部署运行。用户说干系人映射/沟通计划/参与度评估/权力利益矩阵时加载。"
---

# stakeholder-comms 干系人沟通管理技能

> 版权：`../shared/references/COPYRIGHT.md` Token：`../shared/references/token_standard.md`
> 权威工具：`tools/comms_ops.py`（stakeholder/engage/plan/log/dashboard）
> 对齐：PMBOK Stakeholder/Communications Management · Salience Model

## 1. 元数据

- **技能版本**：v1.0.0 **发布日期**：2026-09-08
- **变更记录**：
  - v1.0.0：首个**合规独立可部署**版本——从编排器内嵌子技能提升为 `.trae/skills/` 顶层自包含技能；补 YAML frontmatter、三段版本号、闭环执行系统、`skill.manifest.json`（打包期注入 `comms_ops.py`+`test_comms_ops.py`）；注册 SKILL_INDEX 条目 27 + STANDALONE_SKILLS。**修正 doc-code 漂移**：原声称的 `escalate` 命令工具未实现，问题升级机制（P1~P4）实际归 role-project-init 的 `define_issue_escalation`，本技能按真实工具（stakeholder/engage/plan/log/dashboard）文档化，`log` 保留升级级别列。
- **参考标准**：PMBOK 干系人管理/沟通管理 · Salience Model（权力-利益-影响）
- **定位**：干系人映射、参与度评估与沟通计划管理。

## 2. 触发规则

用户表达「干系人管理 / 沟通计划 / 干系人映射 / 权力利益 / 参与度评估 / 沟通矩阵 / 沟通频率 / 沟通渠道 / 沟通记录」时加载本技能。

| 环节 | action | 功能 | 台账 | CLI |
|------|--------|------|------|-----|
| 干系人映射 | stakeholder_map | 权力-利益矩阵分类 | 50_干系人映射.csv | `stakeholder` |
| 参与度评估 | engagement_assess | 当前/期望 U-N-C-S-A + 差距策略 | 50_干系人映射.csv | `engage` |
| 沟通计划 | comms_plan | 对象/内容/频率/渠道/责任人 | 51_沟通计划.csv | `plan` |
| 沟通记录 | comms_log | 日期/对象/内容/反馈/后续行动 | 52_沟通记录.csv | `log` |
| 沟通仪表盘 | comms_dashboard | 象限分布 + 计划/记录计数 | — | `dashboard` |

**边界**：RACI 矩阵/组织架构→`role-project-init`；问题升级机制（P1~P4）→`role-project-init` 的 `define_issue_escalation`（写 12_风险问题台账）；干系人沟通→本技能。

## 3. 权力-利益矩阵与参与度模型（单一信源）

**权力-利益矩阵**（与 `comms_ops.py` QUADRANT_MAP 一致）：

| | 高利益 | 低利益 |
|------|--------|--------|
| **高权力** | 重点管理 | 保持满意 |
| **低权力** | 保持知情 | 最少关注 |

**参与度阶梯（由低到高，用于差距计算）**：`U`(Unaware 不知晓) < `N`(Neutral 中立) < `C`(Compliant 顺从) < `S`(Supportive 支持) < `A`(Leading 引领)。参与度差距 = 期望级别索引 − 当前级别索引；**差距 ≥2 级 → 需重点提升参与度**；差距 1 级 → 适度提升；0 → 已达标；负 → 超出期望。

## 4. 工具调用（CLI）

权威工具 `tools/comms_ops.py`（Python3，零第三方依赖）：

```bash
python3 tools/comms_ops.py stakeholder --name "Sponsor" --org "管理层" --power high --interest high
python3 tools/comms_ops.py engage --name "Sponsor" --current S --expected A
python3 tools/comms_ops.py plan --stakeholder "Sponsor" --content "进展摘要" --freq weekly --channel "面对面" --owner "PM"
python3 tools/comms_ops.py log --stakeholder "Sponsor" --content "周报汇报" --feedback "认可进度"
python3 tools/comms_ops.py dashboard
```

**台账产物**（UTF-8 with BOM）：`50_干系人映射.csv`（编号/姓名或角色/组织/权力/利益/象限/当前参与度/期望参与度/策略）· `51_沟通计划.csv`（编号/干系人/沟通内容/频率/渠道/责任人/创建日期）· `52_沟通记录.csv`（编号/日期/干系人/沟通内容/反馈/后续行动/升级级别）。

**退出码**：`0`=成功；`1`=参数非法（干系人不存在/权力利益非 high·medium·low/参与度非 C·U·N·S·A）。

## 5. 核心原则

1. **全员映射**：每个干系人必须映射到权力-利益象限。
2. **参与度差距驱动**：差距 ≥2 级须制定沟通策略。
3. **计划覆盖关键干系人**：高权力高利益（重点管理）必有沟通计划。
4. **沟通留痕**：每次沟通记录内容/反馈/后续行动。
5. **升级机制边界**：问题升级（P1~P4）归 role-project-init，本技能 log 仅记升级级别。

## 6. 输出规范

- 所有台账 CSV（UTF-8 with BOM，禁止 .xlsx）；输出回显象限/参与度/计划关键行 + 计数。
- 边界仅干系人沟通域；不承接 RACI 责任分配（归 role-project-init）、不承接问题升级机制设计（归 role-project-init）。

## 7. 独立部署与镜像同步

本技能为**自包含可独立部署技能**：权威工具保留在仓库根 `tools/comms_ops.py`（单一信源），`skill.manifest.json` 声明打包/部署期注入 `comms_ops.py`+`test_comms_ops.py` 副本。`package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 按 manifest 注入后，产物含 `SKILL.md + skill.manifest.json + tools/ + tests/`，脱离编排器即可 `python3 tools/comms_ops.py ...` 运行。

**分发清单（STANDALONE_SKILLS）**：已登记为 `package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 的 `STANDALONE_SKILLS`（独立于 11 个 `ALL_ROLES`），全量同步（无参）自动纳入；按需 `--role stakeholder-comms` 单独分发。**镜像目标**：`.github/skills/` · `.claude/skills/` · `.agents/skills/` · 全局 opencode 库。

> **同步命令**：改动后运行 `python3 tools/package_skills.py` + `python3 tools/deploy_skills.py`。

---

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求映射干系人、评估参与度、制定沟通计划或记录沟通；
- 前置：需确认项目干系人清单、权力/利益判定；
- 不适用：RACI 责任分配（归 role-project-init）、问题升级机制设计（归 role-project-init）。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | 干系人/沟通需求明确 | 确认干系人清单 | 读取现有台账 |
| 执行中 | 映射/评估/计划/记录中 | 产出形成 | 按 action 执行 |
| 校验中 | 参与度评估完成 | 差距策略形成 | 差距≥2 制定策略 |
| 阻塞 | 干系人未映射即评估 | 补映射 | 暂停并记录阻塞 |
| 完成 | 台账更新 | 归档 | 通知相关方 |
| 回退 | 关键干系人未覆盖沟通计划 | 补计划 | 预警并补齐 |

### 3. 执行动作层
- 步骤 1：`stakeholder` 干系人映射（权力×利益 → 象限）；
- 步骤 2：`engage` 参与度评估（当前/期望 U-N-C-S-A + 差距策略）；
- 步骤 3：`plan` 沟通计划（对象/内容/频率/渠道/责任人）；
- 步骤 4：`log` 沟通记录（内容/反馈/后续行动/升级级别）；
- 步骤 5：`dashboard` 象限分布 + 计划/记录汇总；
- 输入输出约束：先映射后评估；权力/利益/参与度取枚举值；台账 UTF-8 BOM；退出码 0/1。

### 4. 验收门禁
- 必须产出物：干系人映射表（50）、沟通计划（51）、沟通记录（52）、参与度评估；
- 通过条件：全部干系人映射到象限、沟通计划覆盖关键干系人、参与度差距≥2 有策略；
- 失败条件：关键干系人未映射、无沟通计划、干系人未映射即评估参与度；
- 审核对象：role-project-mgmt（干系人沟通）+ role-project-init（RACI/升级衔接）。

### 5. 失败处理
- 失败类型：干系人未映射、权力/利益/参与度取值非法、关键干系人无沟通计划；
- 恢复策略：补映射后重评估；修正枚举取值；为高权力高利益干系人补沟通计划；
- 是否需要人工确认：参与度差距≥2 的提升策略须人工确认。

### 6. 产出与交接
- 产出物列表：50_干系人映射.csv、51_沟通计划.csv、52_沟通记录.csv、沟通仪表盘；
- 交接对象：role-project-mgmt（日常沟通）、role-project-init（RACI/问题升级衔接）、MCP comms_plan；
- 下一步动作：重点管理象限 → 高频面对面沟通；差距≥2 → 执行提升策略。

### 7. 审计记录
- 执行时间：stakeholder/engage/plan/log 时间点（台账创建日期/沟通日期）；
- 关键参数：权力/利益取值、象限、当前/期望参与度、差距、频率/渠道/责任人；
- 关键决策：象限分类、参与度差距策略、关键干系人沟通覆盖；
- 结果证据：50/51/52 台账 CSV、沟通仪表盘输出。

---

**文档版本**：v1.0.0 **最后更新**：2026-09-08（从编排器内嵌子技能提升为顶层独立可部署技能；补 frontmatter/三段版本/闭环执行系统/skill.manifest.json；注册 SKILL_INDEX 条目27 + STANDALONE_SKILLS；修正原 escalate 命令 doc-code 漂移，升级机制归 role-project-init）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
