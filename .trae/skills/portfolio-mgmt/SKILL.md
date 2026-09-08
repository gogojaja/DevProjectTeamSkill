---
name: "portfolio-mgmt"
description: "用户提到组合管理/项目选择/投资评审/战略评分/组合优化/Portfolio Review/立项优先级/淘汰项目/组合平衡/价值兑现时加载本项目组合管理技能：负责组合注册与分类（战略主题/投资类别/生命周期阶段）、5 维战略评分（对齐度30%/ROI25%/风险20%/可行性15%/紧迫度10% 加权）、组合平衡分析、优化建议、Portfolio Review Board 决策（立项/加速/暂停/终止）、价值兑现跟踪。可脱离编排器独立部署运行。用户说组合管理/战略评分/投资评审/组合优化/价值兑现时加载。"
---

# portfolio-mgmt 项目组合管理技能

> 版权：`../shared/references/COPYRIGHT.md` Token：`../shared/references/token_standard.md`
> 权威工具：`tools/portfolio_ops.py`（register/score/balance/optimize/review/track/dashboard）
> 对齐：PMI PfM (Portfolio Management) · MoP (Management of Portfolios) · SAFe 6.0 LPM · PMBOK 整合/干系人

## 1. 元数据

- **技能版本**：v1.0.0 **发布日期**：2026-09-08
- **变更记录**：
  - v1.0.0：首个**合规独立可部署**版本——从编排器内嵌子技能提升为 `.trae/skills/` 顶层自包含技能；补 YAML frontmatter、三段版本号、闭环执行系统（任务入口/执行状态/执行动作层/验收门禁/失败处理/产出与交接/审计记录）、`skill.manifest.json`（打包期注入 `portfolio_ops.py`+`test_portfolio_ops.py`）；注册 SKILL_INDEX 条目 24 + STANDALONE_SKILLS。原 6 action 能力、战略评分模型、PRB 决策规则、台账规范全部保留。
- **参考标准**：PMI PfM · MoP · SAFe 6.0 LPM · PMBOK（整合/干系人）
- **定位**：组织级项目投资决策能力——回答「做正确的事」，与 role-project-mgmt（把事做正确）、role-program-mgmt（跨项目对齐）互补。

## 2. 触发规则

用户表达「组合管理 / 项目选择 / 投资评审 / 战略评分 / 组合优化 / Portfolio Review / 立项优先级 / 淘汰项目 / 组合平衡 / 价值兑现」时加载本技能。命中后只读对应能力表与 §3 评分模型。

| 环节 | action | 功能 | 台账 | CLI |
|------|--------|------|------|-----|
| 组合注册 | register_portfolio | 注册与分类（战略主题/投资类别/生命周期阶段） | 43_组合注册.csv | `register` |
| 战略评分 | score_strategic | 5 维加权评分（对齐度/ROI/风险/可行性/紧迫度） | 44_战略评分.csv | `score` |
| 平衡分析 | analyze_balance | 风险-收益分布、短中长期投资比、资源负载 | 44_战略评分.csv | `balance` |
| 组合优化 | optimize_portfolio | 约束下资源分配/优先级排序/淘汰建议 | 44_战略评分.csv | `optimize` |
| 组合评审 | review_portfolio | Portfolio Review Board 决策（立项/加速/暂停/终止） | 45_组合价值兑现.csv | `review` |
| 价值兑现 | track_value | 实际 vs 预期收益偏差跟踪 | 45_组合价值兑现.csv | `track` |

**边界**：单项目内部管理→`role-project-mgmt`；项目群协同→`role-program-mgmt`；组合投资→本技能；咨询诊断/成熟度→`role-mgmt-consulting`。

## 3. 战略评分模型（单一信源）

5 维加权评分（总分归一到 5.00）：

| 维度 | 权重 | 评分标准（1~5） |
|------|:---:|----------------|
| 战略对齐度 | 30% | 1=无关 → 5=直接支撑核心战略 |
| ROI 预期 | 25% | 1=负收益 → 5=IRR>30% |
| 风险可控度 | 20% | 1=极高风险 → 5=几乎无风险 |
| 资源可行性 | 15% | 1=严重不足 → 5=完全具备 |
| 紧迫度 | 10% | 1=无时限 → 5=法规/合规强制 |

**决策规则**（与 `portfolio_ops.py` cmd_score 一致）：加权 ≥4.0 且紧迫度 ≥4 → **Accelerate（加速）**；加权 ≥3.5 → **Proceed（立项）**；加权 ≥2.5 → **Pause（暂停）**；<2.5 → **Terminate（终止）**。

**决策铁律**：Portfolio Review Board 做投资决策，PM 提供数据不决策，PMO 提供机制不决策。

## 4. 工具调用（CLI）

权威工具 `tools/portfolio_ops.py`（Python3，零第三方依赖；`PROJECT_ROOT` 环境变量或脚本位置自动解析台账根）：

```bash
python3 tools/portfolio_ops.py register --name "项目X" --theme "数字化转型" [--category "战略投资"] [--stage "评估中"] [--sponsor "张三"]
python3 tools/portfolio_ops.py score --project "项目X" --alignment 4 --roi 3 --risk 4 --feasibility 5 --urgency 3
python3 tools/portfolio_ops.py balance
python3 tools/portfolio_ops.py optimize
python3 tools/portfolio_ops.py review --project "项目X" --decision Proceed   # Proceed/Accelerate/Pause/Terminate
python3 tools/portfolio_ops.py track --project "项目X" --expected 100 --actual 85
python3 tools/portfolio_ops.py dashboard
```

**台账产物**（写入 `台账/`，UTF-8 with BOM）：`43_组合注册.csv`（编号/项目名称/战略主题/投资类别/生命周期阶段/Sponsor/注册日期/状态）· `44_战略评分.csv`（编号/项目/5维评分/加权总分/排名/评审日期/决策建议）· `45_组合价值兑现.csv`（编号/项目/预期收益/实际收益/偏差率/PRB决策/决策日期/备注）。

**退出码**：`0`=成功；`1`=参数非法（评分越界 1~5 / 决策不在枚举）。

## 5. 核心原则

1. **投资决策分离**：PRB 决策、PM 提供数据、PMO 提供机制，三者不越位。
2. **战略对齐前置**：无战略主题的项目不得进入组合评分。
3. **评分量化**：5 维加权，禁止拍脑袋；Go≥3.5、淘汰<2.5。
4. **人工确认**：组合评审决策（立项/加速/暂停/终止）须人工确认。
5. **价值闭环**：立项后跟踪价值兑现，实际 vs 预期偏差回写台账。

## 6. 输出规范

- 所有台账 CSV（UTF-8 with BOM，禁止 .xlsx）；输出回显关键行 + 计数。
- 组合评审决策须人工确认；边界仅组合投资决策域，不承接单项目内部管理（归 role-project-mgmt）、不承接项目群协同（归 role-program-mgmt）。

## 7. 独立部署与镜像同步

本技能为**自包含可独立部署技能**：权威工具保留在仓库根 `tools/portfolio_ops.py`（单一信源），`skill.manifest.json` 声明打包/部署期注入 `portfolio_ops.py`+`test_portfolio_ops.py` 副本。`package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 按 manifest 注入后，产物含 `SKILL.md + skill.manifest.json + tools/ + tests/`，脱离编排器即可 `python3 tools/portfolio_ops.py ...` 运行。

**分发清单（STANDALONE_SKILLS）**：已登记为 `package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 的 `STANDALONE_SKILLS`（独立于 11 个 `ALL_ROLES`），全量同步（无参）自动纳入；按需 `--role portfolio-mgmt` 单独分发。**镜像目标**：`.github/skills/` · `.claude/skills/` · `.agents/skills/` · 全局 opencode 库。

> **同步命令**：改动本技能或权威工具后运行 `python3 tools/package_skills.py` + `python3 tools/deploy_skills.py`。

---

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求对项目组合进行注册/评分/优化/评审/价值跟踪；
- 前置：需确认项目清单、战略主题定义、资源约束；
- 不适用：单项目内部管理（归 role-project-mgmt）、项目群协同（归 role-program-mgmt）。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | 组合管理需求明确 | 确认项目清单与战略主题 | 读取现有台账 |
| 执行中 | 评分/分析/优化进行中 | 产出形成 | 按 action 流程执行 |
| 校验中 | 评审决策形成 | 用户确认 | 提交 PRB 决策 |
| 阻塞 | 缺战略主题/项目清单 | 补充信息 | 暂停并记录阻塞 |
| 完成 | 评审决策确认 | 台账更新 | 归档并通知 |
| 回退 | 决策依据不足/评分维度缺失 | 补齐后重评 | 撤回决策，补数据重跑 |

### 3. 执行动作层
- 步骤 1：`register` 组合注册与分类（战略主题/投资类别/生命周期阶段）；
- 步骤 2：`score` 5 维战略评分（加权 + 决策建议）；
- 步骤 3：`balance`/`optimize` 组合平衡分析与优化建议；
- 步骤 4：`review` PRB 决策（立项/加速/暂停/终止，人工确认）；
- 步骤 5：`track` 价值兑现跟踪（偏差率）；`dashboard` 汇总；
- 输入输出约束：无战略主题不评分；决策须人工确认；台账 UTF-8 BOM；退出码 0/1。

### 4. 验收门禁
- 必须产出物：组合注册表（43）、战略评分（44）、优化建议、PRB 决策记录、价值兑现（45）；
- 通过条件：评分维度完整、决策经人工确认、台账更新；
- 失败条件：评分维度缺失、未经确认即决策、无战略主题映射；
- 审核对象：role-program-mgmt（组合治理）+ Portfolio Review Board。

### 5. 失败处理
- 失败类型：战略主题缺失、项目清单不全、评分越界（非 1~5）、决策未确认；
- 恢复策略：补齐战略主题/项目清单/评分维度后重跑；决策未确认则挂起不入台账；
- 是否需要人工确认：组合评审决策（立项/加速/暂停/终止）强制人工确认。

### 6. 产出与交接
- 产出物列表：43_组合注册.csv、44_战略评分.csv、45_组合价值兑现.csv、组合优化建议、PRB 决策记录；
- 交接对象：role-program-mgmt（项目群协同）、okr-strategy（战略对齐）、role-mgmt-consulting（组合诊断）、MCP portfolio_dashboard；
- 下一步动作：立项 → 进入项目启动（role-project-init）；淘汰 → 归档并记录理由。

### 7. 审计记录
- 执行时间：register/score/review/track 时间点（台账注册日期/评审日期/决策日期/兑现时间）；
- 关键参数：5 维评分值、加权总分、决策类型、预期/实际收益、偏差率；
- 关键决策：PRB 决策（立项/加速/暂停/终止）、淘汰建议；
- 结果证据：43/44/45 台账 CSV、评分排名表、决策记录。

---

**文档版本**：v1.0.0 **最后更新**：2026-09-08（从编排器内嵌子技能提升为顶层独立可部署技能；补 frontmatter/三段版本/闭环执行系统/skill.manifest.json；注册 SKILL_INDEX 条目24 + STANDALONE_SKILLS；原 6 action 能力与战略评分/PRB 决策规则全保留）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
