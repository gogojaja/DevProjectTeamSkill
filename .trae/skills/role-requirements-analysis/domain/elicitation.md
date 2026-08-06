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

**环节 1 目录初始化**（`create_requirements_baseline`）：创建 `requirements/` 目录 → 生成 `需求收集清单_<对象>_<版本>_v2.csv`（字段见 §3，含来源载体/原子行为/验收标准）→ 确认项目启动基线已固化（总控 role-governance）。前置：台账「范围基准」已写入范围初定义。

**环节 2 需求收集**（`gather_requirements`）：识别需求来源（业务方/访谈/现有系统/合规/技术约束）→ **来源载体 ≠ 需求条目**：基本原则/角色定义/权限矩阵/流程类均降级为「来源载体」（RB/RD/ORG/PRJ/FLOW/TODO），提炼为 EARS 风格原子需求（`[条件]+[角色]+动作+对象+数据范围`）登记「原子行为描述」→ MoSCoW 优先级 + 可量化「验收标准」必填 → 约束依据回标所属基本原则 → 对照七维度清单（func/sec/data/env 必选，nfr/if/ui 可选）校验收集盲区，输出《需求收集完整性检查表》。来源载体编码、原子化提炼模板（INVEST/EARS）、字段强制项详见 `requirements_elicitation_details.md` §2.2~§2.6。

## 3. 输出规范

- `需求收集清单_<对象>_<版本>_v2.csv`（UTF-8 with BOM，字段：需求编号｜来源载体｜原子行为描述｜MoSCoW｜分类｜验收标准｜约束依据｜状态）；《需求收集完整性检查表》
- 基本原则（R-RB-xx）并入「合规约束区」单独列出，不进入待实现需求清单；纯角色定义/权限矩阵/流程类不作为需求条目。

**质量门禁（向分析环节流转前）**：① 需求清单结构化登记完成；② 每条含「原子行为描述 + MoSCoW + 验收标准」三必填；③ 来源载体 100% 填充。

## 4. 边界（刹车规则）

- 同一来源 3 次以上矛盾描述 → 暂停收集，业务方仲裁
- 需求超范围 → 标记「范围外」，转 ProjectMonitorSkill 变更审计

---

> 目录规范详见 `../../shared/references/directory_structure.md`
> 协作接口详见 `../../shared/references/api_contracts.md`

**文档版本**：v21.0.1 | **最后更新**：2026-08-06 | **知识产权所有**：段波（duanbo.douglas@163.com）
