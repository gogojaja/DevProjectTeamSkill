# 跨技能协作接口契约

本文件定义各技能之间的调用关系与接口规范，替代在各技能文件中重复描述的依赖说明。

---

## 协作总览

```
DevProjectTeamSkill（总控）
├── role-project-init          ← 第 0 阶段：项目启动（章程/干系人/范围初定/基线）
├── role-governance             ← 所有角色共享：路由分发至 6 子域（评审/门禁/审计/台账/归档/交接）
│   ├── governance              ← 治理：基线/固化/归档/交接
│   ├── scope-change            ← 范围&变更：变更审计/范围门禁
│   ├── progress-cost           ← 进度&成本：里程碑/EVM
│   ├── quality-gate            ← 质量&门禁：评审/门禁/缺陷
│   ├── risk                    ← 风险：巡检/登记册
│   └── security-audit          ← 安全审计：高危操作/回滚/留痕
├── role-requirements-analysis  ← 需求分析师调用（路由包，分发至 4 子域）
│   ├── elicitation             ← 启发收集：基线/收集
│   ├── dimension-analysis      ← 七维度分析
│   ├── specification           ← IEEE 830 SRS 编写
│   └── lifecycle               ← 评审/变更/追溯
├── role-architecture           ← 架构设计师调用（路由包，分发至 4 子域）
│   ├── strategy                ← 策略分析（驱动因素/质量属性/技术选型/风险）
│   ├── design                  ← 逻辑设计（4+1视图/C4/组件/接口/部署）
│   ├── data-security           ← 数据+安全架构（ER字典/存储/STRIDE/纵深防御）
│   └── review                  ← 决策评审+变更（ADR/原型/评审/变更/固化）
├── role-development            ← 开发工程师调用（路由包，分发至 5 子域）
│   ├── strategy                ← 策略/环境（技术栈/分支/规范/拆解）
│   ├── coding                  ← 编码（实现/规范/安全编码）
│   ├── review                  ← 走查/评审（Fagan/PR 审查）
│   ├── testing                 ← 单元测试（TDD/BDD/覆盖率）
│   └── integration             ← 联调/质量/基线/变更
├── role-testing                ← 测试工程师调用（路由包，分发至 6 子域）
│   ├── strategy                ← 策略分析/RTM/度量
│   ├── planning                ← 测试方案编写
│   ├── design                  ← 测试用例设计
│   ├── preparation             ← 环境准备/数据
│   ├── execution               ← 执行/缺陷管理
│   └── summary                 ← 总结/评审
├── role-deployment             ← 运维部署工程师调用（路由包，分发至 4 子域）
│   ├── strategy                ← 投产策略：部署策略选型/风险/DORA/灾备
│   ├── planning                ← 投产方案：12 章编写/变更分类审批
│   ├── release                 ← 投产执行：准备预演/执行监控/回滚
│   └── handover                ← 评审总结交接：Go-Live/总结/交接/阶段评审
└── shared/
    ├── evolution.md            ← 元技能，只读诊断，按需触发
    └── authoring.md            ← 元技能，Skill 创建/修改，简化模式路由
```

---

## 1. role-governance（总控保障路由包）

**调用方**：所有角色  
**核心 action**：路由包，按领域分发至 6 个子域（详见 §1.1~§1.6）。

| action | 分发子域 | 用途 | 典型调用时机 |
|--------|-----------|------|-------------|
| `create_baseline` | §1.1 governance | 创建全套台账 CSV 与项目基准 | 项目初始化 |
| `change_audit` | §1.2 scope-change（范围/架构）+ §1.6 security-audit（高危操作） | 变更审计/高危操作前置审计 | 变更、高危文件操作 |
| `stage_review` | §1.4 quality-gate | 标准化阶段评审（输出 CSV 报告） | 阶段产出物定稿后 |
| `check_gate` | §1.4 quality-gate（专项门禁）+ §1.2 scope-change（产出物比对）+ §1.3 progress-cost（前置里程碑） | 阶段门禁校验（含范围跟踪比对） | 阶段流转前 |
| `update_milestone` | §1.3 progress-cost | 更新里程碑、工时、成本（EVM） | 阶段验收通过后 |
| `risk_scan` | §1.5 risk | 风险巡检 | 定期、阶段切换 |
| `stage_close` | §1.1 governance | 阶段固化基线 | 评审通过、门禁放行 |
| `release_gate` | §1.1 governance | 发布级门禁（含自动化质量阈值：测试通过率≥95%/关键路径全绿/SAST 无高危） | 敏捷 迭代配置 发布点=Y |
| `iteration_review` | §1.1 governance | 迭代末轻量评审 + 回顾记录 CSV | 每迭代末 |
| `project_archive` | §1.1 governance | 全项目归档 | 所有阶段完工 |
| `handover_export` | §1.1 governance | 跨会话交接打包 | 周期复盘、新建对话 |

### 1.1 governance（项目治理子域）

**调用方**：role-governance 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `create_baseline` | 创建全套台账 CSV 与项目基准（20 个 NN_ 前缀 CSV） | 项目初始化 |
| `stage_close` | 阶段固化基线（备份+版本+产出物清单） | 评审通过、门禁放行 |
| `release_gate` | 发布级门禁（自动化质量阈值：测试通过率≥95%/关键路径全绿/SAST 无高危） | 敏捷 发布点=Y |
| `iteration_review` | 迭代末轻量评审 + 回顾记录（02_迭代回顾.csv） | 每迭代末 |
| `project_archive` | 全项目归档（台账+交付物+审计日志） | 所有阶段完工 |
| `handover_export` | 跨会话交接打包（话术+台账快照+交接文档） | 周期复盘、新建对话 |

### 1.2 scope-change（项目范围与变更管理子域）

**调用方**：role-governance 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `change_audit` | 范围/架构/核心文件变更审计（五维影响评估） | 变更、范围调整 |

> 范围门禁校验、产出物条目化比对、范围跟踪检查为 `check_gate`/`stage_review` 协同子步骤。

### 1.3 progress-cost（项目进度与成本管理子域）

**调用方**：role-governance 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `update_milestone` | 更新里程碑、工时、成本（含 EVM 分析） | 阶段验收通过后 |

> 前置里程碑门禁校验为 `check_gate` 协同子步骤。

### 1.4 quality-gate（项目质量与门禁管理子域）

**调用方**：role-governance 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `stage_review` | 标准化阶段评审（五维校验 + 范围跟踪） | 阶段产出物定稿后 |
| `check_gate` | 阶段门禁校验（含各阶段专项追溯矩阵） | 阶段流转前 |

### 1.5 risk（项目风险管理子域）

**调用方**：role-governance 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `risk_scan` | 风险巡检（登记册更新/新风险识别/等级评估） | 定期、阶段切换、重大变更 |

### 1.6 security-audit（项目安全审计子域）

**调用方**：role-governance 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `change_audit` | 高危操作前置审计（操作影响评估表）+ 全操作留痕 | 高危文件操作、部署启停 |

> 故障回滚与审计留痕为 `change_audit` 协同子流程。

---

## 2. role-requirements-analysis（需求工程路由包）

**调用方**：需求分析师  
**核心 action**：路由包，按领域分发至 4 个子域（详见 §2.1~§2.4）。

| action | 分发子域 | 用途 | 典型调用时机 |
|--------|-----------|------|-------------|
| `create_requirements_baseline` | §2.1 elicitation | 初始化需求工作目录与 CSV 模板 | 项目初始化 |
| `gather_requirements` | §2.1 elicitation | 结构化收集需求 | 需求收集环节 |
| `analyze_requirements` | §2.2 dimension-analysis | 按维度分析需求（支持 dimensions/project_type 参数） | 需求分析环节 |
| `document_requirements` | §2.3 specification | 编写 IEEE 830 SRS CSV（10 章） | 需求编写环节 |
| `review_requirements` | §2.4 lifecycle | 需求评审准备 | 需求评审环节 |
| `change_analysis` | §2.4 lifecycle | 需求变更已选维度影响评估 | 需求变更 |
| `update_traceability` | §2.4 lifecycle | 更新需求双向追溯矩阵 | 需求变更/新增/删除 |
| `iterate_backlog` | §2.1 elicitation | PBI 原子化入产品待办 + S/M/L 规模估算 + MoSCoW 分级 | 敏捷迭代计划 |

### 2.1 elicitation（需求启发与收集子域）

**调用方**：role-requirements-analysis 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `create_requirements_baseline` | 初始化需求工作目录与 CSV 模板 | 项目初始化 |
| `gather_requirements` | 结构化收集需求（来源载体提炼/EARS 原子化/MoSCoW+验收标准） | 需求收集环节 |

### 2.2 dimension-analysis（需求七维度分析子域）

**调用方**：role-requirements-analysis 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `analyze_requirements` | 按已选维度需求分析（动态 N+1 Sheet + 冲突消解 + 维度联动清理） | 需求分析环节 |

### 2.3 specification（需求规格化子域）

**调用方**：role-requirements-analysis 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `document_requirements` | 编写 IEEE 830 SRS CSV 集（10 章）+ 质量校验报告 | 需求编写环节 |

### 2.4 lifecycle（需求生命周期管理子域）

**调用方**：role-requirements-analysis 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `review_requirements` | 需求评审准备（五维度 + 门禁） | 需求评审环节 |
| `change_analysis` | 需求变更已选维度影响评估（必选维度强制全维度扫描） | 需求变更 |
| `update_traceability` | 更新需求双向追溯矩阵 | 需求变更/新增/删除 |

---

## 3. role-architecture（架构域路由包）

**调用方**：架构设计师  
**核心 action**：路由包，按领域分发至 4 个子域（详见 §3.1~§3.4）。

| action | 分发子域 | 用途 | 典型调用时机 |
|--------|-----------|------|-------------|
| `analyze_strategy` | §3.1 strategy | 业务上下文分析、驱动因素识别、质量属性量化、技术选型、风险 | 需求基线固化后 |
| `design_architecture` | §3.2 design | 4+1视图 + C4模型 + 组件/接口/部署设计 | 策略分析评审通过后 |
| `design_data_security` | §3.3 data-security | 数据架构 + 安全架构设计 | 逻辑设计评审通过后 |
| `change_analysis` | §3.4 review | 架构变更七维度影响评估 | 基线固化后需变更时 |

> 架构设计详情逻辑下沉，role-architecture 作为路由包分发执行。

### 3.1 strategy（架构策略分析子域）

**调用方**：role-architecture（路由包）  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `analyze_strategy` | 业务上下文/驱动因素/质量属性量化/技术选型/风险 | 需求基线固化后 |
| `prepare_strategy` | 编写架构策略分析报告 | 策略分析完成 |

---

### 3.2 design（架构逻辑设计子域）

**调用方**：role-architecture（路由包）  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `design_architecture` | 4+1视图 + C4模型 + 组件/接口/部署设计 | 策略分析评审通过后 |

---

### 3.3 data-security（架构数据与安全设计子域）

**调用方**：role-architecture（路由包）  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `design_data_security` | 数据架构 + 安全架构设计（ER/字典/存储/STRIDE/纵深防御） | 逻辑设计评审通过后 |

---

### 3.4 review（架构决策评审子域）

**调用方**：role-architecture（路由包）  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `change_analysis` | 架构变更七维度影响评估 | 基线固化后需变更时 |
| `record_decisions` | ADR 编写 + ATAM 权衡分析 | 架构设计过程中 |
| `validate_prototype` | POC + 跨平台 + 性能验证 | 架构设计初稿完成后 |
| `review_architecture` | ATAM 评估 + 反模式检查 + 七原则终审 | 设计定稿后 |
| `finalize_baseline` | 架构基线固化 | 评审通过后 |

## 4. role-development（开发域路由包）

**调用方**：开发工程师  
**核心 action**：路由包，按生命周期过程分发至 5 个子域（详见 §4.1~§4.5）。

| action | 分发子域 | 用途 | 典型调用时机 |
|--------|-----------|------|-------------|
| `analyze_strategy` | §4.1 strategy | 开发策略分析（技术栈/分支/规范/拆解/ASVS 映射） | 架构基线固化后 |
| `prepare_env` | §4.1 strategy | 开发环境准备（环境/依赖/工具链/CI-CD/安全工具） | 策略分析完成后 |
| `develop_code` | §4.2 coding | 代码开发（功能实现/规范/安全编码/注释） | 环境就绪后 |
| `walkthrough_code` | §4.3 review | 代码走查（Fagan Inspection、问题分级） | 代码开发完成后 |
| `review_pr` | §4.3 review | PR 审查（12 项清单、评审报告） | PR 提交后 |
| `run_unit_test` | §4.4 testing | 单元测试（TDD/BDD、覆盖率、Mock、回归） | 代码开发完成后 |
| `integrate_system` | §4.5 integration | 系统联调（策略/用例/缺陷管理） | 单测通过后 |
| `check_quality` | §4.5 integration | 代码质量检查（静态/SAST/SCA/门禁） | 联调完成后 |
| `solidify_baseline` | §4.5 integration | 开发基线固化（总结报告/追溯矩阵） | 质量门禁通过后 |
| `analyze_change` | §4.5 integration | 开发变更影响评估 | 基线固化后需变更时 |

> 开发领域详情逻辑下沉子域，role-development 作为路由包分发执行。

### 4.1 strategy（开发策略与环境子域）

**调用方**：role-development 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `analyze_strategy` | 开发策略分析（技术栈/分支/规范/拆解/ASVS 映射） | 架构基线固化后 |
| `prepare_env` | 开发环境准备（环境/依赖/工具链/CI-CD/安全工具） | 策略分析完成后 |

---

### 4.2 coding（代码开发子域）

**调用方**：role-development 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `develop_code` | 代码开发（功能实现/规范/安全编码/注释） | 环境就绪后 |

---

### 4.3 review（代码走查与评审子域）

**调用方**：role-development 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `walkthrough_code` | 代码走查（Fagan Inspection、问题分级） | 代码开发完成后 |
| `review_pr` | PR 审查（12 项清单、评审报告） | PR 提交后 |

### 4.4 testing（单元测试子域）

**调用方**：role-development 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `run_unit_test` | 单元测试（TDD/BDD、覆盖率、Mock、回归） | 代码开发完成后 |

---

### 4.5 integration（系统联调与质量收口子域）

**调用方**：role-development 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `integrate_system` | 系统联调（策略/用例/缺陷管理） | 单测通过后 |
| `check_quality` | 代码质量检查（静态/SAST/SCA/门禁） | 联调完成后 |
| `solidify_baseline` | 开发基线固化（总结报告/追溯矩阵） | 质量门禁通过后 |
| `analyze_change` | 开发变更影响评估 | 基线固化后需变更时 |

---

## 5. role-testing（测试域路由包）

**调用方**：测试工程师  
**核心 action**：路由包，按领域分发至 6 个子域（详见 §5.1~§5.6）。

| action | 分发子域 | 用途 | 典型调用时机 |
|--------|-----------|------|-------------|
| `analyze_strategy` | §5.1 strategy | 测试策略分析 | 需求/开发基线固化后 |
| `create_rtm` | §5.1 strategy | 创建/更新测试追溯矩阵 | 策略分析后 |
| `estimate_effort` | §5.1 strategy | 测试工作量估算 | 策略分析后 |
| `write_plan` | §5.2 planning | 编写测试方案 | 策略分析评审通过后 |
| `design_cases` | §5.3 design | 设计测试用例 | 方案评审通过后 |
| `review_cases` | §5.3 design | 测试用例评审 | 用例设计完成后 |
| `prepare_env` | §5.4 preparation | 准备测试环境与数据 | 用例设计完成后 |
| `execute_test` | §5.5 execution | 执行测试并记录结果 | 环境就绪后 |
| `explore_test` | §5.5 execution | 探索性测试 | 功能测试期间或之后 |
| `manage_defect` | §5.5 execution | 缺陷全生命周期管理 | 测试执行中发现缺陷时 |
| `write_report` | §5.6 summary | 编写测试总结报告 | 全部测试执行完成后 |
| `stage_review` | §5.6 summary | 测试阶段评审与门禁校验 | 报告定稿后 |

### 5.1 strategy（测试策略分析子域）

**调用方**：role-testing 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `analyze_strategy` | 测试策略分析 | 需求/开发基线固化后 |
| `create_rtm` | 创建/更新测试追溯矩阵 | 策略分析后 |
| `estimate_effort` | 测试工作量估算 | 策略分析后 |

---

### 5.2 planning（测试方案编写子域）

**调用方**：role-testing 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `write_plan` | 编写测试方案 | 策略分析评审通过后 |

---

### 5.3 design（测试用例设计子域）

**调用方**：role-testing 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `design_cases` | 设计测试用例 | 方案评审通过后 |
| `review_cases` | 测试用例评审 | 用例设计完成后 |

---

### 5.4 preparation（测试环境准备子域）

**调用方**：role-testing 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `prepare_env` | 准备测试环境与数据 | 用例设计完成后 |

---

### 5.5 execution（测试执行与缺陷管理子域）

**调用方**：role-testing 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `execute_test` | 执行测试并记录结果 | 环境就绪后 |
| `explore_test` | 探索性测试 | 功能测试期间或之后 |
| `manage_defect` | 缺陷全生命周期管理 | 测试执行中发现缺陷时 |

---

### 5.6 summary（测试总结与评审子域）

**调用方**：role-testing 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `write_report` | 编写测试总结报告 | 全部测试执行完成后 |
| `stage_review` | 测试阶段评审与门禁校验 | 报告定稿后 |

---

## 6. role-deployment（投产域路由包）

**调用方**：运维部署工程师  
**核心 action**：路由包，按投产子域分发至 4 个子域（详见 §6.1~§6.4）。

| action | 分发子域 | 用途 | 典型调用时机 |
|--------|-----------|------|-------------|
| `analyze_strategy` | §6.1 strategy | 投产策略分析（选型/风险/回滚/DORA/灾备） | 测试基线固化后 |
| `write_plan` | §6.2 planning | 编写投产方案（12 章 + 变更审批） | 策略分析评审通过后 |
| `prepare_release` | §6.3 release | 投产准备与预演 | 方案审批通过后 |
| `go_live_review` | §6.4 handover | Go-Live 评审（六维 + 门禁） | 投产前 24-48h |
| `execute_release` | §6.3 release | 执行投产部署（灰度/全量 + 监控） | Go-Live 评审通过后 |
| `rollback` | §6.3 release | 执行回滚 + 数据回退 | 投产失败时 |
| `write_report` | §6.4 handover | 编写投产总结报告（10 章） | 投产执行完成后 |
| `handover_ops` | §6.4 handover | 运维交接（Runbook/监控/值班） | 总结报告完成后 |
| `stage_review` | §6.4 handover | 投产阶段评审与门禁校验 | 报告定稿后 |

> 投产详情逻辑下沉子域，role-deployment 作为路由包分发执行。

### 6.1 strategy（投产策略分析子域）

**调用方**：role-deployment 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `analyze_strategy` | 部署策略选型/风险矩阵/回滚预案/DORA/灾备 | 测试基线固化后 |

---

### 6.2 planning（投产方案编写子域）

**调用方**：role-deployment 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `write_plan` | 编写《投产方案》12 章 + 变更分类审批 | 策略分析评审通过后 |

---

### 6.3 release（投产准备与执行子域）

**调用方**：role-deployment 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `prepare_release` | 投产准备六项 + 预演五步 | 方案审批通过后 |
| `execute_release` | 执行部署（灰度/全量）+ 实时监控 | Go-Live 评审通过后 |
| `rollback` | 执行回滚 + 数据回退 | 投产失败、监控告警 |

---

### 6.4 handover（投产评审总结与交接子域）

**调用方**：role-deployment 路由分发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `go_live_review` | Go-Live 六维评审 + 决策 + 门禁准入 | 投产前 24-48h |
| `write_report` | 编写投产总结报告（10 章） | 投产执行完成后 |
| `handover_ops` | 运维交接（Runbook/监控/值班/SLA） | 总结报告完成后 |
| `stage_review` | 投产阶段评审 + 门禁准出 | 报告定稿后 |

---

## 7. shared/evolution.md（元技能，诊断侧）

**调用方**：用户手动触发 / 自动条件触发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `evolve_start` | 五步闭环诊断 | 手动触发或自动条件满足 |
| `evolve_check_log` | SHA256 哈希链校验 | 怀疑篡改、定期校验 |
| `evolve_review` | 定期效果评估 | 月度/季度 |
| `ctx_health_check` | 上下文健康检查 | 每轮对话后自动执行 |

**部署模式**：`standalone`（独立）或 `embedded`（嵌入宿主技能体系）

---

## 8. shared/authoring.md（技能创建/修改元技能，写入侧）

**调用方**：用户手动触发（Skill 新建/修改）/ DevProjectTeamSkill §5.2 简化模式路由转发  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `author_define` | 需求定义（1 段描述 + 版本建议） | 新建技能 |
| `author_write` | SKILL.md 编写（frontmatter + 正文四部分） | 需求定义通过后 |
| `author_validate` | 三项结构校验（frontmatter/完整性/无重复） | 编写完成 |
| `author_test` | 功能验证（正向/反向/边界三触发） | 结构校验通过 |
| `author_pack` | 打包发布（zip + 快照备份 + 变更登记） | 功能验证通过 |

**与 shared/evolution.md 边界**：本文件产出新技能/新版本（写入侧）；shared/evolution.md 诊断已有技能缺陷（只读诊断侧）。

---

## 9. role-project-init（项目启动路由包）

**调用方**：DevProjectTeamSkill 标准模式第 0 阶段 / 用户直接触发（"启动一个项目"）  
**核心 action**：

| action | 用途 | 典型调用时机 |
|--------|------|-------------|
| `init_kickoff` | 启动登记（项目编号/目标/背景） | 新项目立项 |
| `create_charter` | 输出项目章程（授权/目标/约束/预算） | 立项登记后 |
| `register_stakeholder` | 干系人登记册（角色/权力-利益/沟通需求） | 章程确认后 |
| `define_scope_prelim` | 范围初定义（边界/排除项/假设/制约） | 干系人确认后 |
| `init_tailor` | 阶段/活动裁剪决策（依据项目特点裁剪生命周期阶段与活动） | 范围初定后 |
| `assess_feasibility` | 五维可行性评估 | 裁剪确认后 |
| `check_ready` | 启动就绪检查（Go/No-Go/暂缓） | 可行性通过后 |
| `init_baseline` | 调用 role-governance `create_baseline` 初始化台账 | 就绪=Go 后 |

**与 role-requirements-analysis 边界**：本包输出范围初定义与项目上下文（第 0 阶段）；需求收集与 SRS 编写由 role-requirements-analysis 承接（需求阶段）。
