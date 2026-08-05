# TRAE 部署步骤与对话启用指令指南

> 本文件说明如何将 DevProjectTeamSkill + ProjectMonitorSkill + RequirementsAnalysisSkill + ArchitectureDesignSkill + TestManagementSkill + DeploymentManagementSkill + DevelopmentManagementSkill + SkillEvolutionSkill 八套技能及配套 Excel 台账体系部署到 TRAE，并在对话中按需启用各业务子角色。

---

## 一、交付内容总览

本次交付物结构如下，可直接复制到本地项目根目录使用：

```
项目根目录/
├── .trae/
│   ├── skills/
│   │   ├── DevProjectTeamSkill/
│   │   │   └── SKILL.md                  ← 6 大业务角色一体化总技能（v8.0.0）
│   │   ├── ProjectMonitorSkill/
│   │   │   └── SKILL.md                  ← 总控保障中枢（v2.3.0）
│   │   ├── RequirementsAnalysisSkill/
│   │   │   └── SKILL.md                  ← 需求工程独立技能（v1.0.0）
│   │   ├── TestManagementSkill/
│   │   │   └── SKILL.md                  ← 测试管理独立技能（v1.0.0）
│   │   ├── DeploymentManagementSkill/
│   │   │   └── SKILL.md                  ← 投产管理独立技能（v1.0.0）
│   │   ├── ArchitectureDesignSkill/
│   │   │   └── SKILL.md                  ← 架构设计独立技能（v1.0.0）
│   │   ├── DevelopmentManagementSkill/
│   │   │   └── SKILL.md                  ← 开发管理独立技能（v1.0.0）
│   │   ├── SkillEvolutionSkill/
│   │   │   ├── SKILL.md                  ← 通用元技能自省诊断（v2.0.0，支持独立/嵌入双模式）
│   │   │   └── evolve_check_log.py       ← SHA256 哈希链校验 + 经验教训管理脚本（v2.0.0）
│   │   ├── 技能说明文档.md               ← 技能体系总体说明
│   │   └── 技能操作手册.md               ← 技能操作参考手册
│   └── 项目总台账.xlsx                   ← 主台账（16 Sheet，部署到实际项目后由技能自动创建）
├── requirements/                          ← 需求工程独立目录（RequirementsAnalysisSkill 读写）
│   ├── 需求收集清单.xlsx
│   ├── 需求分析报告.xlsx
│   ├── 需求规格说明书_SRS_v<版本>.xlsx
│   ├── 需求变更影响评估表_<变更编号>.xlsx
│   └── SRS质量校验报告.xlsx
├── 测试资产/                              ← 测试资产独立目录（TestManagementSkill 读写）
│   ├── 01_测试策略/
│   ├── 02_测试方案/
│   ├── 03_测试用例/
│   ├── 04_环境准备/
│   ├── 05_执行记录/
│   ├── 06_测试报告/
│   └── 07_自动化脚本/
├── 投产资产/                              ← 投产资产独立目录（DeploymentManagementSkill 读写）
│   ├── 01_投产策略/
│   ├── 02_投产方案/
│   ├── 03_投产准备/
│   ├── 04_GoLive评审/
│   ├── 05_执行记录/
│   ├── 06_投产报告/
│   └── 07_运维交接/
├── 架构资产/                              ← 架构资产独立目录（ArchitectureDesignSkill 读写）
│   ├── 01_架构策略/
│   ├── 02_架构设计/
│   ├── 03_架构决策/
│   │   └── ADR/
│   ├── 04_原型验证/
│   ├── 05_架构评审/
│   └── 06_架构基线/
├── 开发资产/                              ← 开发资产独立目录（DevelopmentManagementSkill 读写）
│   ├── 01_开发策略/
│   ├── 02_环境配置/
│   ├── 03_源代码/
│   ├── 04_单元测试/
│   ├── 05_质量检查/
│   └── 06_开发基线/
└── 项目台账模板/                          ← 交付包中的参考模板（部署后由 Excel 台账替代）
├── Skill_Evolution_Log.xlsx              ← 技能演进审计台账（2 Sheet，SkillEvolutionSkill 使用）
└── Skill_Lessons_Learned.xlsx            ← 经验教训累积库（6 Sheet，SkillEvolutionSkill 使用）
    ├── 01_启动组.md
    ├── 02_规划总册.md
    ├── 03_执行记录.md
    ├── 04_监控台账/
    │   ├── 范围变更台账.md
    │   ├── 范围跟踪台账.md
    │   ├── 进度跟踪台账.md
    │   ├── 成本消耗台账.md
    │   ├── 质量缺陷台账.md
    │   ├── 风险&问题台账.md
    │   ├── 安全审计台账.md
    │   └── 门禁验收记录.md
    └── 05_收尾归档册.md
```

### 七技能协同 + 元技能自省架构

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    DevProjectTeamSkill（业务执行层）                      │
│  ┌─────────┬─────────┬─────────┬─────────┬──────────┬───────────────┐   │
│  │需求分析师│架构设计师│开发工程师│测试工程师│运维部署   │文档管理员     │   │
│  │         │         │         │         │工程师↑   │               │   │
│  └─────────┴─────────┴─────────┴─────────┴──────────┴───────────────┘   │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ 调用依赖技能
                               ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ProjectMonitor  │ │Requirements    │ │Architecture    │ │Development     │ │TestManagement  │ │Deployment      │
│Skill           │◄►│AnalysisSkill   │ │DesignSkill     │ │ManagementSkill │ │Skill           │ │ManagementSkill │
│（总控保障层）  │ │（需求工程层）  │ │（架构设计层）  │ │（开发管理层）  │ │（测试管理层）  │ │（投产管理层）  │
│                │ │                │ │                │ │                │ │                │ │                │
│范围/变更管控   │ │需求收集/分析   │ │4+1视图/C4模型  │ │TDD/BDD开发     │ │测试策略/用例   │ │投产策略/方案   │
│进度/成本管控   │ │IEEE 830 SRS    │ │ADR/ATAM评估    │ │SonarQube门禁   │ │测试执行/缺陷   │ │Go-Live评审     │
│质量/评审管控   │ │双向追溯矩阵    │ │七大设计原则    │ │OWASP ASVS安全  │ │测试追溯矩阵    │ │灰度发布/监控   │
│风险/安全审计   │ │                │ │架构追溯矩阵    │ │代码审查/CI/CD  │ │                │ │运维交接/回滚   │
│门禁/基线固化   │ │                │ │                │ │开发追溯矩阵    │ │                │ │                │
│归档/交接/复盘  │ │                │ │                │ │                │ │                │ │                │
└────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘
```

---

## 二、TRAE 部署步骤

### 步骤 1：部署八个 Skill 到 TRAE skills 目录

1. 进入项目目录下的 `.trae/skills/`（若不存在则新建）；
2. 新建八个文件夹：`DevProjectTeamSkill`、`ProjectMonitorSkill`、`RequirementsAnalysisSkill`、`ArchitectureDesignSkill`、`TestManagementSkill`、`DeploymentManagementSkill`、`DevelopmentManagementSkill`、`SkillEvolutionSkill`；
3. 分别在八个文件夹内新建 `SKILL.md`，将交付包中对应文件内容完整粘贴进去；`SkillEvolutionSkill` 文件夹内还需放入 `evolve_check_log.py` 哈希链校验脚本；
4. 八个 Skill 的依赖关系：
   - `DevProjectTeamSkill`（v8.0.0）内置依赖 `ProjectMonitorSkill` + `RequirementsAnalysisSkill` + `ArchitectureDesignSkill` + `TestManagementSkill` + `DeploymentManagementSkill` + `DevelopmentManagementSkill` + `SkillEvolutionSkill`，八者必须同时部署；
   - `ProjectMonitorSkill`（v2.3.0）与 `RequirementsAnalysisSkill`（v1.0.0）、`ArchitectureDesignSkill`（v1.0.0）、`TestManagementSkill`（v1.0.0）、`DeploymentManagementSkill`（v1.0.0）、`DevelopmentManagementSkill`（v1.0.0）双向协同，共享台账数据；
   - `RequirementsAnalysisSkill`、`ArchitectureDesignSkill`、`TestManagementSkill`、`DeploymentManagementSkill`、`DevelopmentManagementSkill` 均依赖 `ProjectMonitorSkill` 提供的台账读写、门禁校验、基线固化能力；
   - `SkillEvolutionSkill`（v2.0.0）为通用只读元技能，支持 standalone 独立部署与 embedded 嵌入模式（自动检测）；embedded 模式下通过四适配器接口（audit/handover/storage/version）与宿主技能协作，standalone 模式下自动降级为 Markdown 日志审计 + 本地 Excel 存储；不具备文件写入权限，所有提案须经审计适配器审批 + 用户确认后落地；可诊断任意技能（target_skill 开放）。
5. 将《技能说明文档.md》和《技能操作手册.md》也放入 `.trae/skills/` 目录，供查阅参考。

### 步骤 2：部署 Excel 台账体系到实际项目根目录

项目初始化时，`ProjectMonitorSkill` 会自动通过 `action=create_baseline` 创建主台账 Excel 文件，无需手动创建。但需确保以下目录结构存在：

**主台账文件**：`项目总台账.xlsx`（存放于项目根文件夹 `.trae/` 目录，共 16 个 Sheet）

| Sheet 序号 | Sheet 名称 | 核心内容 |
|-----------|-----------|----------|
| 1 | 启动组 | 项目立项、相关方、项目目标、沟通记录 |
| 2 | 范围基准 | 范围基准、功能明细、禁止项 |
| 3 | 进度基准 | 阶段划分、里程碑清单、任务拆解 |
| 4 | 成本基准 | 人力工时预估、成本阈值、超支标准 |
| 5 | 质量基准 | 分阶段质量验收标准 |
| 6 | 范围变更台账 | 变更记录、评估表、审批记录 |
| 7 | 范围跟踪台账 | 各阶段产出物清单、阶段比对、偏差跟踪 |
| 8 | 需求追溯矩阵 | 需求-来源-功能模块-接口-数据-测试用例-设计文档双向追溯 |
| 9 | 进度跟踪台账 | 里程碑更新、任务完成率、延期风险 |
| 10 | 成本消耗台账 | 工时消耗、资源成本、超支预警 |
| 11 | 质量缺陷台账 | 评审缺陷、Bug 全生命周期、评审报告归档 |
| 12 | 风险&问题台账 | 风险登记册、技术卡点、风险应对方案 |
| 13 | 安全审计台账 | 高危操作留痕、回滚记录、操作 ID |
| 14 | 门禁验收记录 | 各阶段门禁校验结果、产出物比对表、基线固化记录 |
| 15 | 执行记录 | 开发、编码、部署、资源投入全流程执行记录 |
| 16 | 收尾归档 | 交付物清单、全周期复盘、交接资料、经验总结 |

**需求工程独立目录**（`RequirementsAnalysisSkill` 读写）：

```
项目根文件夹/
└── requirements/
    ├── 需求收集清单.xlsx                    ← 原始需求结构化登记（2 Sheet）
    ├── 需求分析报告.xlsx                    ← 七维度分析结果（7 Sheet）
    ├── 需求规格说明书_SRS_v<版本>.xlsx       ← IEEE 830 标准 SRS（10 Sheet）
    ├── 需求变更影响评估表_<变更编号>.xlsx     ← 变更分析记录
    └── SRS质量校验报告.xlsx                  ← 八项质量特性逐条校验结果
```

**架构资产独立目录**（`ArchitectureDesignSkill` 读写）：

```
项目根文件夹/
└── 架构资产/
    ├── 01_架构策略/                         ← 架构策略分析报告、风险评估矩阵
    ├── 02_架构设计/                         ← 4+1视图、C4模型、组件/接口/数据/安全设计
    ├── 03_架构决策/                         ← ADR架构决策记录、ATAM权衡分析
    │   └── ADR/
    ├── 04_原型验证/                         ← POC验证、跨平台测试、性能基准
    ├── 05_架构评审/                         ← ATAM评估、15类检查、反模式审查、七原则终审
    └── 06_架构基线/                         ← 架构文档定稿、开发指南、资产归档
```

**测试资产独立目录**（`TestManagementSkill` 读写）：

```
项目根文件夹/
└── 测试资产/
    ├── 01_测试策略/
    │   ├── 测试策略分析报告.md
    │   ├── 测试追溯矩阵.xlsx
    │   └── 测试工时估算表.xlsx
    ├── 02_测试方案/
    │   └── 测试方案.md
    ├── 03_测试用例/
    │   └── 测试用例.xlsx
    ├── 04_环境准备/
    │   ├── 环境就绪检查清单.md
    │   └── 冒烟测试结果.md
    ├── 05_执行记录/
    │   ├── 用例执行结果.xlsx
    │   ├── 缺陷清单.xlsx
    │   └── 探索性测试记录.md
    ├── 06_测试报告/
    │   └── 测试总结报告.md
    └── 07_自动化脚本/
        └── （接口自动化脚本/性能测试脚本）
```

**投产资产独立目录**（`DeploymentManagementSkill` 读写）：

```
项目根文件夹/
└── 投产资产/
    ├── 01_投产策略/
    │   ├── 投产策略分析报告.md
    │   ├── 投产风险评估矩阵.xlsx
    │   └── 回滚预案.md
    ├── 02_投产方案/
    │   ├── 投产方案.md
    │   ├── 变更申请单.xlsx
    │   └── 部署清单.xlsx
    ├── 03_投产准备/
    │   ├── 环境就绪检查清单.md
    │   ├── 部署包清单.xlsx
    │   └── 预演报告.md
    ├── 04_GoLive评审/
    │   └── Go-Live评审报告.xlsx
    ├── 05_执行记录/
    │   ├── 部署执行记录.xlsx
    │   ├── 灰度验证报告.md
    │   └── 监控告警记录.md
    ├── 06_投产报告/
    │   └── 投产总结报告.md
    └── 07_运维交接/
        ├── 运维手册_Runbook.md
        ├── 已知问题清单.xlsx
        └── 运维交接签收单.xlsx
```

**注意事项**：
1. 目录名、文件名固定不可修改，各技能按此固定路径读写；
2. `项目总台账.xlsx` 的核心结构 Sheet（范围基准、进度基准、成本基准、质量基准）设置工作表保护，仅允许通过 action 指令修改；
3. 每次 `stage_close` 阶段固化后自动备份，备份文件名：`项目总台账_v<基线版本号>_backup.xlsx`。

### 步骤 3：开启技能加载并刷新识别

1. 打开 TRAE 配置，开启技能加载（Skills）；
2. 刷新识别八个 Skill：`DevProjectTeamSkill`、`ProjectMonitorSkill`、`RequirementsAnalysisSkill`、`ArchitectureDesignSkill`、`TestManagementSkill`、`DeploymentManagementSkill`、`DevelopmentManagementSkill`、`SkillEvolutionSkill`；
3. 确认八个 Skill 均已加载成功后即可在对话中使用。

### 步骤 4：会话启动提醒

对话启动后，技能会第一时间提醒用户「切换专家模式」，保障全部规则生效。请按提示切换，否则子角色强制约束、门禁、刹车等规则无法完整生效。

---

## 三、对话启用指令示例

各阶段按需启用对应子角色，使用以下指令。注意：切换角色前请先输入「重置」指令清空已加载子角色，再加载新角色，保持单线串行推进。

### 1. 项目初始化（仅需求分析师）

```
启用DevProjectTeamSkill，仅加载【需求分析师】子角色
```

> 需求分析师会自动调度 `RequirementsAnalysisSkill` 执行需求收集→分析→编写→评审四环节，调度 `ProjectMonitorSkill` 执行基线创建、变更审计、门禁校验。

### 2. 切换架构设计

```
重置DevProjectTeamSkill，加载【架构设计师】子角色
```

> 架构设计师会自动调度 `ArchitectureDesignSkill` 执行架构策略分析→架构设计→决策记录→原型验证→架构评审→基线固化六大环节，调度 `ProjectMonitorSkill` 执行架构阶段门禁校验（含 4+1视图/C4/ADR/七原则/架构追溯矩阵完整性检查）、基线固化。

### 3. 开发编码阶段

```
重置DevProjectTeamSkill，加载【开发工程师】子角色
```

> 开发工程师会自动调度 `DevelopmentManagementSkill` 执行开发策略分析→环境准备→代码开发→单元测试→质量检查→基线固化六大环节，调度 `ProjectMonitorSkill` 执行开发阶段门禁校验（含 SonarQube 五维指标/SAST/SCA/代码审查/单元测试覆盖率/开发追溯矩阵完整性检查）、基线固化。

### 4. 测试验收

```
重置DevProjectTeamSkill，加载【测试工程师】子角色
```

> 测试工程师会自动调度 `TestManagementSkill` 执行测试策略分析→方案编写→用例设计→依赖准备→测试执行与缺陷管理→测试总结与评审六大环节，调度 `ProjectMonitorSkill` 执行测试阶段门禁校验（含 RTM 完整性检查）、基线固化。

### 5. 投产部署

```
重置DevProjectTeamSkill，加载【运维部署工程师】子角色
```

> 运维部署工程师会自动调度 `DeploymentManagementSkill` 执行投产策略分析→方案编写→准备预演→Go-Live 评审→执行监控→总结交接六大环节，调度 `ProjectMonitorSkill` 执行投产阶段门禁校验（含 Go-Live 六维检查）、基线固化。

### 6. 项目归档复盘、跨会话交接

```
重置DevProjectTeamSkill，加载【文档管理员】子角色，执行全项目归档复盘
```

---

## 四、使用要点与注意事项

1. **八技能必须同时部署**：`DevProjectTeamSkill` 内置依赖 `ProjectMonitorSkill` + `RequirementsAnalysisSkill` + `ArchitectureDesignSkill` + `TestManagementSkill` + `DeploymentManagementSkill` + `DevelopmentManagementSkill` + `SkillEvolutionSkill`，缺少任何一个会导致对应功能失效；
2. **单角色串行**：同一时间仅激活一个子角色，必须完成当前角色全部流程（评审、门禁、基线固化、台账更新）并获取用户确认后，才可切换下一角色；
3. **未启用不加载**：未手动指定的子角色仅保留名称元数据，不载入上下文，控制 Token 长度、抑制幻觉；
4. **三层渐进加载**：公共底座（永久轻量）→ 业务角色（按需手动启用）→ 依赖技能（被调用时临时加载，执行完即释放）；
5. **保障中枢统一调度**：所有评审、变更、门禁、归档、交接操作统一由 `ProjectMonitorSkill` 处理，子角色不得自主执行；需求分析操作由 `RequirementsAnalysisSkill` 处理，架构设计操作由 `ArchitectureDesignSkill` 处理，开发管理操作由 `DevelopmentManagementSkill` 处理，测试管理操作由 `TestManagementSkill` 处理，投产管理操作由 `DeploymentManagementSkill` 处理；
6. **刹车规则**：需求连续 3 次无审批变更、评审最多 2 轮整改、连续 2 次延期/超支、高危操作连续 2 次拒绝等场景会触发刹车，需人工介入；
7. **Excel 台账同源共享**：所有子角色共享同一套本地 Excel 台账（`项目总台账.xlsx`，16 Sheet），多窗口、多对话共用同源数据，跨会话无信息丢失；
8. **双向追溯体系**：需求阶段维护需求双向追溯矩阵（写入主台账 Sheet 8），架构阶段维护架构追溯矩阵（需求→架构元素→组件→接口），开发阶段维护开发追溯矩阵（需求→模块→文件→测试用例），测试阶段维护测试追溯矩阵 RTM（写入测试资产目录），投产阶段维护投产追溯矩阵（变更项→部署包→监控→回滚→交接），门禁校验时断链率超过 20% 将驳回流转；
9. **周期复盘**：对话累计 25 轮自动复述目标/梳理进度，累计 100 轮自动拉取全套台账 Excel 输出复盘与交接话术。
10. **SkillEvolutionSkill 独立部署能力**（v2.0.0 新增）：`SkillEvolutionSkill` 支持 `standalone` 独立部署模式——单独放入任意项目的 `.trae/skills/SkillEvolutionSkill/` 目录即可使用，无需其他七个业务技能；自动降级为 Markdown 日志审计 + 本地 Excel 存储（`Skill_Evolution_Log.xlsx` + `Skill_Lessons_Learned.xlsx`）；首次使用执行 `python evolve_check_log.py genesis` 创建创世基线；可诊断任意技能（`evolve_start target_skill=你的技能名称`）；`evolve_check_log.py --mode auto` 自动检测部署模式，`lessons` 子命令管理经验教训库。

---

## 五、技能版本信息

| 技能名称 | 版本 | 定位 | 核心职责 |
|----------|------|------|----------|
| DevProjectTeamSkill | v8.0.0 | 业务执行层 | 六角色调度、业务规则执行、用户交互、上下文健康监控 |
| ProjectMonitorSkill | v2.3.0 | 总控保障层 | 台账读写、评审、变更审计、门禁校验、基线固化、归档交接 |
| RequirementsAnalysisSkill | v1.0.0 | 需求工程层 | 需求收集/分析/编写/变更分析、IEEE 830 SRS、双向追溯矩阵 |
| ArchitectureDesignSkill | v1.0.0 | 架构设计层 | 六环节架构设计全生命周期、七大设计原则、4+1/C4双轨设计、ATAM/ADR |
| DevelopmentManagementSkill | v1.0.0 | 开发管理层 | 六环节开发全生命周期、七大开发原则、TDD/BDD、SonarQube门禁、OWASP ASVS安全编码 |
| TestManagementSkill | v1.0.0 | 测试管理层 | 六环节测试全生命周期、五大测试类型、RTM、风险驱动测试 |
| DeploymentManagementSkill | v1.0.0 | 投产管理层 | 六环节投产全生命周期、五大部署策略、Go-Live 评审、DORA 度量 |
| SkillEvolutionSkill | v2.0.0 | 通用元技能自省层 | 五步闭环诊断、五层根因诊断（第五层可选）、上下文健康监控、SHA256哈希链审计、经验教训六分类库、定期效果评估、四适配器通用集成、standalone/embedded双模式 |

---

**文档版本**：v8.0.0
**最后更新**：2026-07-31
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
