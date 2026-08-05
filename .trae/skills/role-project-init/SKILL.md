---
name: "role-project-init"
description: "项目启动角色包：立项、项目章程、干系人登记、范围初定、可行性检查、启动就绪、台账基线初始化。触发词：启动项目、立项、项目章程、干系人、范围初定、可行性、启动就绪、初始化基线。Load when the user starts a new project, creates the charter, registers stakeholders, checks feasibility/readiness, or initializes the project baseline."
---

# role-project-init 项目启动角色包

> 版权：`../shared/references/COPYRIGHT.md`　Token：`../shared/references/token_standard.md`　总控：`../shared/governance.md`

## 1. 元数据

- **技能版本**：v21.0.0　**发布日期**：2026-08-04
- **变更记录**：v21.0.0 由 project-init-skill 重组为角色包（标准 SKILL.md + domain/）
- **参考标准**：PMBOK 启动过程组（initiating process group）

## 2. 触发规则

用户表达「启动项目/立项/写章程/登记干系人/范围初定/可行性检查/就绪检查/基线初始化」时加载本包。单角色场景直接 Read 本文件；需要台账时调用 `../shared/governance.md`。

## 3. 流程（路由到 domain/）

| 环节 | 动作 | 明细 |
|------|------|------|
| 启动登记 | 项目基本信息登记 | `domain/project-init.md` |
| 章程 | create_charter | `domain/project-init.md` |
| 干系人 | register_stakeholder | `domain/project-init.md` |
| 范围初定 | 范围初步定义 | `domain/project-init.md` |
| 可行性 | 可行性检查 | `domain/project-init.md` |
| 启动就绪 | check_ready | `domain/project-init.md` |
| 基线初始化 | create_baseline（经总控） | `../shared/governance.md` |

## 4. 输出规范与边界

- 基线初始化必须经 `../shared/governance.md`（主台账 CSV 读写，禁止 .xlsx）；
- 输出表格按 token_standard §3 阈值（Markdown/CSV）；
- 边界：仅负责启动阶段；需求/架构等后续阶段路由到对应角色包。

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）