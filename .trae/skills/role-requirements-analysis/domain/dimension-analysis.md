---
name: "requirements-dimension-analysis-skill"
description: "Requirement dimension analysis sub-skill performing deep analysis of raw requirements across configurable dimensions (dimensions/project_type parameters, with mandatory func/sec/data/env and optional nfr/if/ui dimensions), outputting a dynamic N+1 Sheet analysis report CSV set. Handles dimension selection validation, project-type recommended dimension combinations, conflict resolution with priority chain and record linkage cleanup, and dimension-parameterized analysis. Invoke when analyzing requirements against selected dimensions."
---

# RequirementsDimensionAnalysisSkill 需求七维度分析技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **定位/调用**：需求工程「分析与设计定义」阶段技能；由 requirements-analysis-skill 路由分发，DevProjectTeamSkill 需求分析师子角色主动调用（仅调用时临时加载，不常驻上下文）
- **触发时机**：需求分析环节、需求变更影响分析
- **存储介质**：`需求分析报告/`、`需求冲突消解记录.csv`
- **参考标准**：BABOK v3、ISO/IEC 25010:2011
- **入参**：`{"action": "analyze_requirements", "stage": "需求收集/需求分析/需求编写/需求评审", "content": "原始需求条目", "project_context": "项目名称/范围边界/相关方/约束条件", "dimensions": "维度代码，逗号分隔，默认全7维度；必选 func/sec/data/env 不可移除，可选 nfr/if/ui 按项目类型精选", "project_type": "software_system / pure_business / ui_only / data_migration / embedded（自动推荐维度组合，仅 dimensions 未传时生效）", "user_confirm": "无/同意/拒绝"}`

| action | 作用 | 触发场景 |
|--------|------|----------|
| `analyze_requirements` | 按已选维度需求分析，输出动态 N+1 Sheet 报告 | 需求分析环节 |

## 2. 流程（analyze_requirements）

**维度分级**：必选 func（功能）/ sec（安全）/ data（数据要求）/ env（系统运行环境），任何项目均须分析；可选 nfr（非功能，纯业务流程类可跳过）/ if（接口，无外部系统对接可跳过）/ ui（操作界面，无界面项目可跳过）。详细内容与输出 Sheet 见 `.//dimension_analysis_details.md` §一，项目类型推荐组合见 §二。

**维度选择校验**：未传 dimensions 默认 7 维度；仅传 project_type 按推荐自动填充；必选维度不可移除（移除则报错并自动补回）；可选维度可增删；启动后已选维度不可中途移除（仅可新增）。

**需求冲突消解**：按「安全 > 合规 > 功能 > 非功能 > 界面」优先级链消解；若 nfr 已选：功能与非功能冲突 → 非功能优先；若 ui 已选：安全与易用性冲突 → 安全优先；性能与成本冲突 → 交 ProjectMonitorSkill 风险评估，用户决策；未选维度间冲突不参与。

**冲突消解记录维度联动**：维度移除 → 扫描 `需求冲突消解记录.csv` 涉及维度列，单维度冲突标记「已失效」，多维度冲突更新涉及维度列，生成《冲突记录清理日志》；维度新增 → 全量分析 + 扫描既有条目新冲突，标注「维度新增触发」。

## 3. 输出规范

- `需求分析报告/`（动态 N+1 Sheet：固定「分析维度配置」+ 按已选维度动态生成，未选维度标注原因）
- `需求冲突消解记录.csv`（冲突编号/描述/涉及维度/消解方案/决策人/日期 +「清理日志」区）

**质量门禁（向编写环节流转前）**：① 已选维度分析全部完成；② 必选维度 func/sec/data/env 全部分析；③ 冲突消解记录全部关闭或无冲突。

## 4. 边界（刹车规则）

- 同一需求已选维度分析中 2 次矛盾结论 → 标记高优冲突，暂停分析待干系人确认
- 超范围 → 转变更审计（ProjectMonitorSkill）

---

> 目录规范详见 `../../shared/references/directory_structure.md`
> 协作接口详见 `../../shared/references/api_contracts.md`

**文档版本**：v21.0.0 | **最后更新**：2026-08-02 | **知识产权所有**：段波（duanbo.douglas@163.com）
