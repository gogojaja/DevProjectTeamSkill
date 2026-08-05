---
name: "requirements-elicitation-skill"
description: "Requirements elicitation sub-skill covering requirement gathering baseline initialization and structured requirement collection from all stakeholder sources. Initializes the requirements working directory CSV template and collects requirements with traceable source mapping, MoSCoW priority classification, and completeness checks against the seven-dimension checklist. Invoke when creating the requirements baseline or gathering raw requirements."
---

# RequirementsElicitationSkill 需求启发与收集技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **定位/调用**：需求工程「启发与收集」阶段技能；由 requirements-analysis-skill 路由分发，DevProjectTeamSkill 需求分析师子角色主动调用（仅调用时临时加载，不常驻上下文）
- **触发时机**：项目初始化需求基线创建、需求收集环节
- **存储介质**：`需求收集清单.csv`
- **参考标准**：BABOK v3、ISO/IEC/IEEE 29148:2018
- **入参**：`{"action": "create_requirements_baseline / gather_requirements", "stage": "需求收集/需求分析/需求编写/需求评审", "content": "项目信息/原始需求材料/需求条目", "project_context": "项目名称/范围边界/相关方/约束条件", "user_confirm": "无/同意/拒绝"}`

| action | 作用 | 触发场景 |
|--------|------|----------|
| `create_requirements_baseline` | 初始化需求工作目录，创建 CSV 模板 | 项目初始化 |
| `gather_requirements` | 结构化收集需求，写入需求收集清单 CSV | 需求收集环节 |

## 2. 流程

**环节 1 目录初始化**（`create_requirements_baseline`）：创建 `requirements/` 目录 → 生成 `需求收集清单.csv`（「需求清单」「来源映射」两区）→ 确认项目启动基线已固化（project-init-skill）。前置：台账「范围基准」已写入范围初定义。

**环节 2 需求收集**（`gather_requirements`）：识别需求来源（业务方/访谈/现有系统/合规/技术约束）→ 结构化登记至「需求清单」（编号/来源/来源类型/原始描述/提出人/日期/优先级/分类标签）→ 初步分类标签 → 来源追溯写入「来源映射」→ 对照七维度清单（func/sec/data/env 必选，nfr/if/ui 可选）校验收集盲区，输出《需求收集完整性检查表》。来源类型明细、字段定义、盲区校验逻辑详见 `.//requirements_elicitation_details.md` §2。

## 3. 输出规范

- `需求收集清单.csv`（「需求清单」「来源映射」两区）；《需求收集完整性检查表》

**质量门禁（向分析环节流转前）**：① 需求清单结构化登记完成（「需求清单」区完整性）；② 来源映射 100% 填充（「来源映射」区无空来源）。

## 4. 边界（刹车规则）

- 同一来源 3 次以上矛盾描述 → 暂停收集，业务方仲裁
- 需求超范围 → 标记「范围外」，转 ProjectMonitorSkill 变更审计

---

> 目录规范详见 `../../shared/references/directory_structure.md`
> 协作接口详见 `../../shared/references/api_contracts.md`

**文档版本**：v21.0.0 | **最后更新**：2026-08-02 | **知识产权所有**：段波（duanbo.douglas@163.com）
