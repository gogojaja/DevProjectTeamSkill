---
name: "role-project-init"
description: "用户启动项目、立项、写章程、登记干系人、定组织架构与 RACI、建问题升级机制、范围初定、可行性检查、启动就绪、初始化基线时加载本项目启动角色包：负责立项登记、项目章程（成功标准/PM 任命职权/签字批准）、干系人登记（权力-利益矩阵）、组织架构与 RACI 矩阵、问题升级机制（P1~P4 分级/四级升级阶梯/Owner）、范围初定义、阶段裁剪、环境与访问边界声明、五维可行性评估、就绪检查与台账基线初始化，对齐 PMBOK 启动过程组。用户说启动项目/初始化/定 RACI/问题升级时加载。Load when the user starts a new project, creates the charter, registers stakeholders, or initializes project baseline."
---

# role-project-init 项目启动角色包

> 版权：`../shared/references/COPYRIGHT.md`　Token：`../shared/references/token_standard.md`　总控：`../shared/governance.md`

## 1. 元数据

- **技能版本**：v21.2.0　**发布日期**：2026-08-16
- **变更记录**：v21.2.0 新增组织架构与责任分配（define_org_structure，27_组织架构.csv）+ 问题解决与升级机制（define_issue_escalation，12_风险问题台账升级字段）+ 章程补成功标准/PM 任命职权/签字批准 + check_ready 治理硬门禁；v21.1.0 新增访问边界声明（declare_access_boundary，26_访问边界.csv）+ 目录边界铁律；v21.0.2 集成 CMDB CLI 工具到 register_env_asset 环节；v21.0.1 新增环境资产注册（register_env_asset）路由与 25_环境资源清单；v21.0.0 由 project-init-skill 重组为角色包（标准 SKILL.md + domain/）
- **参考标准**：PMBOK 启动过程组（initiating process group）

## 2. 触发规则

用户表达「启动项目/立项/写章程/登记干系人/范围初定/可行性检查/就绪检查/基线初始化」时加载本包。单角色场景直接 Read 本文件；需要台账时调用 `../shared/governance.md`。

## 3. 流程（路由到 domain/）

| 环节 | 动作 | 明细 |
|------|------|------|
| 启动登记 | 项目基本信息登记 | `domain/project-init.md` |
| 章程 | create_charter（含成功标准/PM 任命职权/签字批准） | `domain/project-init.md` |
| 干系人 | register_stakeholder | `domain/project-init.md` |
| 组织架构 | define_org_structure（团队构成 + RACI + 决策权限，27_组织架构.csv） | `domain/project-init.md` |
| 问题机制 | define_issue_escalation（P1~P4 分级 + 四级升级阶梯 + 响应时限 + Owner，12_风险问题台账.csv） | `domain/project-init.md` |
| 范围初定 | 范围初步定义 | `domain/project-init.md` |
| 裁剪 | init_tailor + 环境资产注册 | `domain/project-init.md` |
| 访问边界 | declare_access_boundary | `domain/project-init.md` |
| 可行性 | 可行性检查 | `domain/project-init.md` |
| 启动就绪 | check_ready（含组织架构/问题机制硬门禁） | `domain/project-init.md` |
| 基线初始化 | create_baseline（经总控） | `../shared/governance.md` |

> 多项目共享同一服务器时，`init_tailor` 后须执行 `register_env_asset` 资源注册与冲突预检（`台账/25_环境资源清单.csv`，详见 `../references/multi_project_isolation.md` §10），`check_ready` 含「资源无未裁决冲突」门禁。
> **治理铁律**：启动阶段必须执行 `define_org_structure`（组织架构 + RACI，`台账/27_组织架构.csv`）与 `define_issue_escalation`（问题分级 P1~P4 + 升级路径 + 响应时限 + Owner，`台账/12_风险问题台账.csv` 升级字段），未明确禁止进入 `check_ready`（硬门禁）。
> **访问边界铁律**：启动阶段必须执行 `declare_access_boundary` 声明本项目可读写/删除范围=本项目所在目录（`台账/26_访问边界.csv`），未声明禁止进入 `check_ready`；本项目目录之外的任何访问（其他项目目录/系统文件）一律经 `register_auth` 授权（未填有效期默认仅本次对话有效），铁律详见 `../references/iron_rules.md` §1。

## 4. 输出规范与边界

- 基线初始化必须经 `../shared/governance.md`（主台账 CSV 读写，禁止 .xlsx）；
- 输出表格按 token_standard §3 阈值（Markdown/CSV）；
- 边界：仅负责启动阶段；需求/架构等后续阶段路由到对应角色包。

---

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求启动项目、写章程、登记干系人、定义范围、检查可行性、初始化基线；
- 前置：需确认项目阶段、已知参与人、台账模板与工作范围；
- 不适用：项目已处于执行/投产/归档阶段，此时不重复执行启动初始化。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | 启动需求已明确 | 项目基线初始化或中止 | 读取已有台账与项目背景 |
| 执行中 | 章程/干系人/范围已形成 | 关键产出形成 | 按标准流程推进初始化 |
| 校验中 | 启动门禁已生成 | 可行性/就绪通过或退回 | 检查资源、冲突与授权 |
| 阻塞 | 缺少干系人、资源、授权或范围 | 补充信息/人工确认 | 暂停并记录阻塞原因 |
| 完成 | 启动就绪与基线初始化成功 | 进入需求或架构阶段 | 归档证据并交接 |
| 回退 | 启动失败/冲突未决 | 回到最近稳定状态 | 撤销无效初始化，保留审计 |

### 3. 执行动作层
- 执行步骤 1：登记项目基本信息、启动范围与关键干系人；
- 执行步骤 2：编写/校验章程与范围说明；
- 执行步骤 3：执行可行性检查与环境/资源注册，并生成基线；
- 所需工具/脚本：`tools/cmdb/cmdb-cli.py`、总控台账、项目根模板；
- 输入输出约束：输出必须落盘到项目根与台账目录，不能直接跳过审计和基线验证。

### 4. 验收门禁
- 必须产出物：章程、干系人名单、范围初定、可行性检查、启动就绪记录、基线初始化；
- 通过条件：资源无未裁决冲突，门禁已过，基线自动/人工签收；
- 失败条件：范围不清、未登记授权、关键依赖不齐、冲突未解决；
- 审核对象：项目负责人 + role-governance 总控。

### 5. 失败处理
- 失败类型：范围定义冲突、资源冲突、授权缺失、项目可行性不足；
- 恢复策略：回到范围与干系人校验，补足资源/授权信息；
- 回滚方案：撤销受影响草稿，保留上一可用基线；
- 重试策略：在冲突与授权解决后再重试；
- 是否需要人工确认：资源占用、授权登记和阶段启动必须人工确认。

### 6. 产出与交接
- 产出物列表：项目章程、启动台账、资源登记、阶段配置、基线；
- 保存路径：项目根及 `台账/` 目录；
- 交接对象：需求分析/架构/开发角色和总控；
- 下一步动作：进入下一阶段并执行相应角色路由；
- 归档条件：启动阶段门禁通过并形成可追溯基线。

### 7. 审计记录
- 执行时间：启动动作开始/结束时间；
- 关键参数：项目名称、范围、干系人、资源登记、版本标识；
- 关键决策：是否通过启动就绪、是否启用阶段裁剪；
- 结果证据：CSV、章程、授权/资源登记记录；
- 失败原因：记录在总控审计台账与项目交接文档。

---

**文档版本**：v21.2.0　**最后更新**：2026-08-16
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）