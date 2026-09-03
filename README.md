# DevProjectTeamSkill 技能库

**版本**：v21.12.0 ｜ **发布日期**：2026-09-01 ｜ **结构**：10 角色包 + 1 编排器

## 项目简介

DevProjectTeamSkill 是一套**软件研发全生命周期多角色编排技能库**的**本体**（即技能源码），不是业务应用。它把软件研发从启动、需求、架构、开发、测试、投产到总控保障，以及项目群协同与项目管理咨询，拆解为可被 AI Agent 加载执行的角色包，由一个薄壳编排器按阶段渐进调度。

AI Agent 在本仓库的职责是**维护技能库本身**（skill 编写 / 结构 / 打包 / 部署 / 固化），而不是执行软件项目的业务。

## 核心定位

- **本体即源码**：`.trae/skills/` 是唯一事实来源，所有角色包、标准、共享库都在其中。
- **10 角色包 + 1 编排器**：编排器负责路由、调度、阶段门禁、上下文压缩与跨会话交接；10 个角色包各司其职、互不越界。
- **闭环执行**：每个技能维护产物须具备「闭环执行系统」章节（任务入口 / 状态机 / 验收门禁 / 失败恢复 / 交接审计），经校验工具通过后才可发布。
- **单源共享**：公共标准与共享库只存 `shared/`，角色包以相对引用复用，打包时自动内嵌，禁止手工复制。
- **强约束治理**：源码单源、`description` 150~250 字符、CSV 输出、敏感信息三级分级、系统/外部文件操作须经授权→备份→留痕。

## 顶层目录结构概览

```
DevProjectTeamSkill/
├── .trae/skills/          技能源码（唯一事实来源）
│   ├── SKILL_INDEX.md      角色包路由索引（#0 编排器 + #1~#10 角色包）
│   ├── dev-project-team-skill/   编排器（薄壳）
│   ├── role-*/             10 个角色包
│   ├── references/         公共标准（token / csv / api 契约 / 环境 / 模型 / 铁律）
│   └── shared/             单源共享库（governance / evolution / authoring + references 副本）
├── tools/                  打包 / 部署 / 固化 / 校验 / CMDB 脚本（.sh + .py 双实现）
├── scripts/                钩子安装等辅助脚本
├── security/               安全示例与隔离配置（含 secrets-example/，可入库）
├── requirements/           依赖声明
├── tests/                  测试
├── docs/                   文档出口（指南 / 方案 / 台账标准）
├── 台账/                    受控台账库（含 13/14/26/32/34 等 csv，入库）
├── .trae-html-share-packages/   历史共享包留档（gitignored）
├── 交接文档.md             跨会话断点（入库）
├── opencode.json           opencode 技能注册
├── AGENTS.md               本仓库代理行为总规则
└── README.md / CHANGELOG.md / CONTRIBUTING.md / docs/REPO_STRUCTURE.md
```

> 更多目录职责与入库 / gitignored 划分见 `docs/REPO_STRUCTURE.md`。

## 角色包列表（源自 SKILL_INDEX.md）

| # | 角色包 | 域 | 触发词 |
|---|--------|-----|--------|
| 0 | dev-project-team-skill | 编排器 | 全生命周期 / 角色组合加载 / 切换角色 / 技能维护 |
| 1 | role-project-init | 项目启动 | 启动项目 / 立项 / 章程 / 干系人 / 组织架构 / RACI / 问题升级 / 基线初始化 |
| 2 | role-requirements-analysis | 需求 | 收集需求 / 分析需求 / 编写 SRS / 需求变更 / 需求追溯 |
| 3 | role-architecture | 架构 | 架构策略 / 架构设计 / 数据安全 / ADR / 架构评审 |
| 4 | role-development | 开发 | 开发策略 / 编码 / 代码走查 / 单元测试 / 联调 / 质量收口 |
| 5 | role-testing | 测试 | 测试策略 / 测试计划 / 用例设计 / 测试执行 / 缺陷管理 / 测试总结 |
| 6 | role-deployment | 投产 | 投产策略 / 投产计划 / Go-Live / 发布执行 / 回滚 / 运维交接 |
| 7 | role-governance | 总控保障 | 台账读写 / 阶段评审 / 门禁 / 基线固化 / 变更审计 / 归档 / 交接 |
| 8 | role-program-mgmt | 项目群 / 项目集 | 项目群 / 项目集 / 多项目协同 / PMO / 依赖 / 里程碑对齐 / 收益 / IMS |
| 9 | role-mgmt-consulting | 项目管理咨询 | 项目管理咨询 / PMO 咨询 / 成熟度评估 / 差距分析 / 方法论定制 / 变革管理 / 咨询建议书 / PMO 蓝图 / 教练辅导 |
| 10 | role-project-mgmt | 项目经理执行层 | 项目管理 / 日常管控 / RAID / 进展报告 / 变更协调 / 经验教训 / 干系人沟通 / 阶段状态跟踪（不涉及具体工程交付） |

## 快速开始

```sh
# 1) 克隆仓库
git clone https://github.com/gogojaja/DevProjectTeamSkill.git
cd DevProjectTeamSkill

# 2) 启用运行环境（二选一）
#    a. opencode：本仓库已注册 skills（见 opencode.json），启动即加载角色包
#    b. TRAAE：历史启用指南见 docs/legacy/TRAE部署与启用指南.md（仅留档）

# 3) 安装环境门禁钩子（新 clone 后执行一次）
bash scripts/install-hooks.sh

# 4) 改动技能后固化部署（快照→刷新断点→打包→部署到目标目录）
bash tools/solidify.sh "说明"

# 5) 提交
git commit
```

部署目标：`.github/skills/`、`.claude/skills/`、`.agents/skills/` 及全局库
（Windows：`C:\Users\<user>\.config\opencode\skills`；macOS/Linux：`~/.config/opencode/skills`）。
**永不覆盖 `.trae/skills/` 源**；共享内容经打包自动内嵌，禁止手工复制。

## 打包与部署

```sh
bash tools/package_skills.sh               # 打包全部 10 角色包到 dist/
bash tools/package_skills.sh --role role-testing
bash tools/deploy_skills.sh --roles role-a,role-b   # 部署到 .github/.claude/.agents/ 及全局库
bash tools/solidify.sh "说明"               # 快照→刷新交接断点→打包→部署
```

部署目标：`.github/skills/`、`.claude/skills/`、`.agents/skills/` 及全局库
（Windows：`C:\Users\<user>\.config\opencode\skills`；macOS：`~/.config/opencode/skills`）。
**永不覆盖 `.trae/skills/` 源**；共享内容经打包自动内嵌，禁止手工复制。

## 文档索引（docs/）

| 文档 | 说明 |
|------|------|
| `docs/REPO_STRUCTURE.md` | 仓库目录树与各级目录职责、入库 / gitignored 划分 |
| `docs/opencode启用指南.md` | opencode 当前推荐启用方式 |
| `docs/legacy/TRAE部署与启用指南.md` | TRAE 历史启用指南（v8.0.0，仅留档） |
| `docs/capability-matrix-enhancement-v21.3.0.md` | v21.3.0 能力矩阵增强方案 |
| `docs/data-governance-mode-v21.2.1.md` | v21.2.1 数据治理模式方案 |
| `docs/项目群协同.md` | 项目群 / 项目集协同方案 |
| `docs/Token优化与CSV输出方案_v21.0.0.md` | Token 优化与 CSV 输出方案 |
| `docs/github_ip_records.csv` | GitHub 访问候选 IP 资源记录（动态刷新） |
| `docs/program-control-ledger/` | 项目群控制台账（已迁入 docs，源 台账/ 之外出口） |
| `docs/legacy/` | 双角色 / 精简工作流等历史文档 |

## 关键规则摘要（详见 AGENTS.md）

- **源码单源**：只在 `.trae/skills/` 改技能，改完即跑 `solidify` 部署。
- **修改技能须同步** `SKILL_INDEX.md` + `references/api_contracts.md`；`description` 150~250 字符（`做什么。<触发词>。Load when...`）。
- **输出格式**：≥4K token 或 >20 列 → CSV（UTF-8 with BOM），禁止 .xlsx。
- **敏感信息三级**：A 禁止入库（密钥 / 凭据 / Token 只存别名）、B 脱敏入库（主机名 / IP / 用户名 / 绝对路径）、C 正常入库。
- **系统 / 项目外文件操作**：先授权 → 备份到 `.backup/` → 留痕 `台账/13_安全审计台账.csv`，并走 `security_audit` 前置审计。
- **提交门禁**：`.githooks/pre-commit` 校验 A 级密钥 / B 级脱敏 / `.env` `.secrets` 禁提交 / 大文件 >4K；失败阻断提交。

---

**文档版本**：v21.12.0 ｜ **知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
