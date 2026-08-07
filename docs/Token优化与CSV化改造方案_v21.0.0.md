# DevProjectTeamSkill v21.0.1 改造方案：Token 极致瘦身 + 无缝切换 + CSV 化

> 目标：解决三大问题——①加载/运行全链路 Token 消耗（核心：改造为**角色包模型**，分角色独立加载、可联合使用）；②跨工具/跨模型无缝切换；③表格全部弃用 Excel 改用 CSV/Markdown。
> 本文为**方案文档**，仅定义标准与改造清单，不直接修改技能库。经确认后按 `common_standards.md` §3 快照 + skill-authoring-skill 流程逐项落地。
>
> **v21.0.1 修订**（按行业最佳实践评审）：删除「.md 改名防注入」机制（P0-1）；辅助包改「源码单源 + 打包内嵌」（P0-2）；修正「读后用后即弃」与全生命周期峰值估算（P0-3）；description 恢复 150~250 字触发词前置（P1-1）；表格阈值改体积/Token 估算（P1-2）；新增基线测量与实测门禁（P1-3）；新增 Prompt Caching 策略（P1-4）；CSV 增列数上限（P1-5）；P2 项同步修订。

---

## 0. 现状诊断（证据）

| 问题 | 现状 | 浪费量 |
|------|------|--------|
| 技能加载 | 39 个技能正文合计 448KB（≈11 万 token），TRAE/Claude 可能全量注入；opencode 仅注入 description（约 1 万字符） | 全量注入时 ~11 万 token/会话 |
| 技能清单 | 39 个技能 description 全部进系统提示 | ~5K token/会话（opencode） |
| 交接 | `跨会话交接文档.md` 存在但打包脚本未强制含交接文档；新模型无「先读交接文档」硬约束 | 新模型需扫描全部文档定位断点 |
| 表格 | 全库 30+ 处 `.xlsx`（17-Sheet 主台账、评审 5-Sheet、SRS 10-Sheet 等） | openpyxl 依赖 + 无法增量读取 |

---

## 1. 方案一：角色包模型（分角色独立加载 + 联合使用）

> 核心思路：**每个角色 = 一个自包含技能包**，可单独部署、单独加载；辅助技能包因被各角色引用，**随每个角色包内置一份**（自包含，无外部依赖）。联合使用时由编排器按需加载多个角色包。

### 1.1 设计原则

1. **角色包粒度**：7 个角色包 + 1 个编排器，工具**只注册 8 个技能**（每个角色包根 `SKILL.md`），替代现行 39 个技能注册；
2. **自包含（分发产物）**：每个角色包**打包产物**内含「本角色域子技能 + 辅助包副本 + references」，独立解压到任意工具 skills/ 目录即可完整运行，无跨包引用；
3. **源码单源（Source of Truth）**：源码库只保留**一份** `references/` 与辅助能力，各角色包通过相对路径引用；**副本只在打包时由脚本自动内嵌**，禁止源码手工复制（P0-2 修订）；
4. **分/合双模式**：单角色任务只加载对应角色包；全生命周期任务由编排器（dev-project-team-skill）按阶段**渐进加载**所需角色包，阶段切换时执行上下文压缩（P0-3 修订）；不加载全量。

### 1.2 目录结构（源码库单源 vs 分发产物自包含）

**源码库**（唯一事实来源，无重复副本）：

```
skills/
├── dev-project-team-skill/               # ① 编排器（联合使用入口）
│   └── SKILL.md                          #   描述：何时加载哪个角色包
├── role-project-init/                    # ② 角色包：项目启动（标准 SKILL.md 布局）
├── role-requirements/                    # ③ 角色包：需求分析
├── role-architecture/                    # ④ 角色包：架构设计
├── role-development/                     # ⑤ 角色包：开发管理
├── role-testing/                         # ⑥ 角色包：测试管理
├── role-deployment/                      # ⑦ 角色包：投产管理
├── role-governance/                      # ⑧ 角色包：总控保障（文档管理员）
├── shared/                               # 单源共享：辅助能力 + 公共标准（仅此一份）
│   ├── governance.md                     #   总控保障（台账/评审/审计/固化）
│   ├── evolution.md                      #   SkillEvolutionSkill 自省
│   ├── authoring.md                      #   SkillAuthoringSkill 技能维护
│   └── references/                       #   公共标准（common/cross_tool/directory/api_contracts/COPYRIGHT）
└── SKILL_INDEX.md                        # 角色包索引清单
```

**角色包源码结构**（以 role-requirements 为例，`../shared/` 相对引用）：

```
role-requirements/
├── SKILL.md                              # 唯一技能入口（工具仅注入此文件 description）
└── domain/                               # 本角色域子技能（按需 Read，不进系统提示）
    ├── requirements-analysis.md
    ├── requirements-elicitation.md
    ├── requirements-dimension-analysis.md
    ├── requirements-specification.md
    └── requirements-lifecycle.md
```

**分发产物**（`package_skills.sh` 打包时自动生成，自包含）：

```
dist/role-requirements_v21.0.0.zip
├── 00_交接文档.md                         # 包内第一项（见 §2.1）
├── role-requirements/
│   ├── SKILL.md
│   ├── domain/*.md
│   └── shared/                           # 打包时内嵌的辅助能力 + references 副本（自动生成）
```

> **P0-1 修订说明**：不再通过「子技能改名 `.md` 防注入」规避工具扫描——该机制对注入型工具无效且破坏标准格式。改为：
> - **标准工具（opencode / Claude Code）**：保持标准 SKILL.md 布局，靠**元数据预载**（只注入 name+description，正文按需读）天然省 token，无需改名；
> - **注入型工具（TRAE 等递归读整个目录）**：用 `--roles` **只部署所需角色包**，从源头避免全量注入。

### 1.3 加载模式

| 模式 | 触发 | 加载内容 | Token 量级 |
|------|------|----------|-----------|
| 单角色（默认） | 「启用需求分析师」 | 仅 role-requirements 包（根描述 + 按需读 domain） | ~2-4K token |
| 多角色联合 | 「启用需求分析师+测试工程师」 | 加载 role-requirements + role-testing 两包 | ~4-8K token |
| 全生命周期 | 编排器 dev-project-team-skill | 按阶段渐进加载各角色包；**阶段切换时执行上下文压缩**（ContextHealthMonitor），峰值受控 | 单阶段累计未压缩包量级 |

> **P0-3 修订**：工具上下文为**追加式**，Read 过的文件无法手动弃置，只能靠压缩（compaction）回收。因此全生命周期峰值 = **阶段内累计未压缩包量级**（非单包），须在阶段门禁处强制压缩，否则多包累计将接近全量。

- **opencode**：标准技能布局，只注册 8 个角色包根技能，description 合计 ~1.5K 字符；正文按需加载，元数据预载机制天然省 token；
- **TRAE / Claude Code / Copilot**：按需部署——`deploy_skills.sh --roles` 只把需要的角色包放入其 `skills/` 目录，避免全量注入；
- **编排器**：自身为薄文件（~60 行），正文仅含「角色包→触发词→加载路径」路由表 + 阶段调度与压缩规则。

### 1.4 索引清单规范（`SKILL_INDEX.md`）

技能库根保留一张索引清单，编排器与用户据此选择角色包，每包一行：

```markdown
| 角色包 | 域 | 触发词 | 加载路径 |
|--------|-----|--------|----------|
| role-requirements-analysis | 需求 | 收集/分析/编写需求 | role-requirements-analysis/ |
| role-testing | 测试 | 测试策略/用例/执行/缺陷 | role-testing/ |
```

> P2-1：角色包命名采用「域-能力」语义（如 `role-requirements-analysis`），与 gerund 形式对齐；短名仅作别名。

- 角色包根 `SKILL.md` 不再重复索引内容，只引用索引行号；
- 索引仅服务**包选择**，子技能明细由包内 `SKILL.md` 路由表承载。

### 1.5 description 压缩模板（角色包根）

> **P1-1 修订**：description 是模型从多个技能中**选择该包的唯一依据**，必须同时含「做什么 + 何时触发」，压到 ~70 字会漏触发词导致召回失败。**建议 150~250 字**，触发词前置、用用户口吻。

```yaml
description: "<role 做什么>。<触发词，前置>。Load when <user says these words>."
```

示例：

```yaml
# role-requirements/SKILL.md
description: "需求分析角色包：收集需求、七维度分析、编写 IEEE 830 SRS、需求评审与变更追溯，含台账/审计/自省辅助。触发词：收集需求、分析需求、编写 SRS、需求变更、需求追溯。Load when the user asks to collect, analyze, specify (SRS), review, or trace requirements."
```

### 1.6 通用 Token 减耗规则（全库强制）

1. **包内只保留「触发规则 + 流程 + 输出规范 + 边界」四段**，明细一律外置包内 `domain/*.md` 与 `shared/references/`（按需 Read）；已读文件**依赖上下文压缩回收**，不依赖「读后即弃」；
2. **表格一律按 §3 规则输出**（Markdown / CSV，阈值见 §3.1），杜绝 Excel；
3. **读文件规则**：先读包根 `SKILL.md` 路由表 → 命中后只读对应 `domain/*.md` 或 `shared/` 目标文件；禁止一次性 Read 包内全部文件；
4. **脚本经 bash 执行**：工具脚本不载入源码，只算输出（沿用既有 solidify/package 模式）；
5. **Prompt Caching 友好排序**（P1-4）：包内**稳定内容（角色规则、流程、铁律）前置**、**动态内容（当前阶段、项目数据、任务上下文）后置**，最大化缓存前缀命中，降低重复输入成本；
6. **命令/日志输出**：仅回显变更与错误，禁止回显完整大文件；
7. 每轮结束沿用 ContextHealthMonitor（SkillEvolutionSkill，shared/evolution.md）监控 Token 占用率，超阈值触发压缩。

---

## 2. 方案二：跨工具/跨模型无缝切换（交接文档优先）

### 2.1 核心机制：交接文档作为唯一入口

- **固化名称**：`交接文档.md`（P2-2：从现有 `跨会话交接文档.md` **改名迁移**，保留全部历史断点内容；迁移期内两文件互斥，不得并存双源）；
- **硬约束（写入 dev-project-team-skill §2.1 与 cross_tool_standard §3.4）**：
  > 新模型/新会话启动，**第一步必须读取 `交接文档.md`**，从「工作断点」区定位上一模型完成/待办，未读交接文档前禁止读取其他项目文档。
- **打包必含**：所有项目打包/归档/交接 zip **必须包含 `交接文档.md` 且置于包内第一项**，命名 `00_交接文档.md`（序号前缀保证排序优先）。

### 2.2 交接文档模板（固定章节，压缩体积）

```markdown
# 交接文档
## 0. 速览（1 段：项目目标 + 当前阶段 + 下一步唯一动作）
## 1. 工作断点（表格：已完成 / 进行中 / 待办 / 阻塞，各 ≤5 条）
## 2. 关键文件索引（表格：文件路径 + 一句话用途，≤10 条）
## 3. 台账指针（主台账 CSV 目录路径 + 最近变更号）
## 4. 约定与铁律（本库强制规则超链接）
```

- 全文目标 **≤150 行**，新模型只读此文件即能续作，无需扫读全库；
- 每次原子任务完成执行 `bash tools/solidify.sh "<说明>"` 时自动刷新断点区（既有机制保留）。

### 2.3 打包/部署脚本增强（tools/*.sh）

1. `package_skills.sh`：**按角色包粒度打包**——从源码单源 `shared/` 自动内嵌辅助能力 + references 副本，输出 `dist/role-<name>_v<版本号>.zip`（自包含：包根 SKILL.md + domain/ + shared/ 副本）；输出包内第一项 = `00_交接文档.md`（技能库打包时取技能库根交接文档；项目归档时取项目交接文档）；
2. `deploy_skills.sh`：新增 `--roles <role-requirements,role-testing,...>` 参数，**按需部署指定角色包**到目标工具 skills/ 目录；不带参数默认全量部署 8 个包；并同步 `SKILL_INDEX.md`；
3. `solidify.sh`：固化时强制刷新 `交接文档.md` 断点区，若缺失则用模板创建。

### 2.4 切换前固化动作（防丢铁律，已在 v20.1.0 强制，本次强化）

任何原子任务完成 / 切换模型前：`solidify.sh` + `git commit`（既有规则保留）；新增硬约束——**固化后交接文档断点区必须反映磁盘最新状态**，否则禁止切换。

---

## 3. 方案三：表格 CSV 化（每 Sheet 一个 CSV）

### 3.1 全局输出规则（新增至 common_standards §4）

> **P1-2 修订**：阈值不以「行数」为准（行数 ≠ token：800 行×3 列很小，800 行×20 列很大），以**体积/Token 估算**为准；行数仅作快速判定参考。

| 估算输出体积 | 输出格式 | 理由 |
|--------------|----------|------|
| 估算 < 4K token（或 <100KB） | **Markdown 表格** | 可直接预览、理解结构，Token 占用可接受 |
| 估算 ≥ 4K token（或 ≥100KB） | **CSV 文件**（UTF-8 with BOM） | 最大化节省 Token，工具可增量读取 |

- **快速判定**：行数 × 列数 × 平均字段长度 ≥ 约 4K token 即转 CSV（如 800 行 × 3 列 ≈ 文本小，仍用 Markdown；20 列以上大表即使 ~200 行也转 CSV）；
- 各技能 DoD 可按数据密度调整阈值（如测试用例、缺陷清单通常更早转 CSV）；
- 导出 CSV 时仅回显首 5 行预览 + 行数，禁止回显全文。

### 3.2 文件布局（每 Sheet 一个 CSV，替换全部 .xlsx）

#### 主台账：`项目总台账.xlsx`（17 Sheet）→ `台账/` 目录 17 个 CSV

| 原 Sheet | 新文件 |
|----------|--------|
| 启动组 | `台账/01_启动组.csv` |
| 范围基准 | `台账/02_范围基准.csv` |
| 进度基准 | `台账/03_进度基准.csv` |
| 成本基准 | `台账/04_成本基准.csv` |
| 质量基准 | `台账/05_质量基准.csv` |
| 范围变更台账 | `台账/06_范围变更台账.csv` |
| 范围跟踪台账 | `台账/07_范围跟踪台账.csv` |
| 需求追溯矩阵 | `台账/08_需求追溯矩阵.csv` |
| 进度跟踪台账 | `台账/09_进度跟踪台账.csv` |
| 成本消耗台账 | `台账/10_成本消耗台账.csv` |
| 质量缺陷台账 | `台账/11_质量缺陷台账.csv` |
| 风险&问题台账 | `台账/12_风险问题台账.csv` |
| 安全审计台账 | `台账/13_安全审计台账.csv` |
| 门禁验收记录 | `台账/14_门禁验收记录.csv` |
| 执行记录 | `台账/15_执行记录.csv` |
| 开发追溯 | `台账/16_开发追溯.csv` |
| 收尾归档 | `台账/17_收尾归档.csv` |

#### 各工作目录（改造清单，节选）

| 原文件 | 新文件 |
|--------|--------|
| `requirements/需求收集清单.xlsx` | `requirements/需求收集清单.csv` |
| `requirements/需求分析报告.xlsx` | `requirements/需求分析报告/` 目录（7 维度 7 个 CSV） |
| `requirements/需求规格说明书_SRS_v<版本>.xlsx` | `requirements/SRS_v<版本>/` 目录（10 章 10 个 CSV） |
| `架构资产/.../*.xlsx` | 同名 `.csv`（质量属性矩阵/技术选型/风险登记册/七原则合规/决策矩阵/评审报告/资产清单） |
| `测试资产/.../*.xlsx` | 同名 `.csv`（追溯矩阵/工时/用例/执行结果/缺陷清单） |
| `开发资产/.../*.xlsx` | 同名 `.csv`（技术栈清单/覆盖率/走查问题/代码评审/联调用例/Sonar/技术债务/追溯矩阵/资产清单） |
| `投产资产/.../*.xlsx` | 同名 `.csv`（风险评估/变更申请/部署清单/部署包/Go-Live/执行记录/已知问题/签收单） |
| 评审报告（5-Sheet Excel） | `评审报告_<对象>_<版本>_{摘要|缺陷清单|逐原则|范围跟踪|角色权限}.csv` |

### 3.3 CSV 规范（新增至 common_standards §4.2）

1. **编码**：UTF-8 with BOM（Excel/工具双兼容）；分隔符 `,`；含逗号字段用双引号包裹；多行字段用 `\n`；
2. **结构**：首行表头，与旧 Sheet 表头一致；表头固定列顺序；
3. **命名**：语义化，与旧 Sheet 同名（目录内 `NN_` 序号前缀保持排序）；
4. **列数上限**（P1-5）：单 CSV 列数 >30 列必须按域拆分（如 7 维度分析拆 7 文件），超宽表同样烧 token；
5. **访问**：读取用增量方式（`head -5` 预览 / `grep` 定位），禁止全量 cat；
6. **转换工具**：提供 `tools/excel_to_csv.py`（openpyxl → csv 批量转换存量 .xlsx），存量数据一次性迁移，此后不再产生新 .xlsx；
7. **审计链**：CSV 内容纳入 git 版本控制，替代 Excel 的 openpyxl 依赖；SHA256 校验链（SkillEvolutionSkill）改为对 CSV 文本校验。

### 3.4 受影响技能清单（30+ 处引用，逐项替换）

`project-monitor-skill` / `project-governance-skill` / `project-quality-gate-skill` / `project-init-skill` / `requirements-analysis-skill`(4 子技能) / `architecture-management-skill`(4 子技能) / `test-management-skill`(6 子技能) / `development-management-skill`(5 子技能) / `deployment-management-skill`(4 子技能) / `skill-evolution-skill`（台账 xlsx→csv，**含 `evolve_check_log.py` 脚本由 openpyxl 改造为 csv 读写，P2-4**）/ 以及 `references/directory_structure.md`、`references/api_contracts.md`、`dev-project-team-skill` §2.2 评审输出规则。

---

## 4. 改造步骤（按依赖排序）

> **P1-3 修订**：新增 #0 基线测量与 #11 实测门禁，收益以实测数据为准，不得凭估算宣称达标。

| # | 步骤 | 涉及文件 | 前置 |
|---|------|----------|------|
| 0 | **基线测量**：记录各工具（opencode/TRAE/Claude）启动时实际注入 token、各技能 description 合计、单任务峰值 | 测量记录 | 无 |
| 1 | 快照当前库 `skills_backup_v20.2.0/` | common_standards §3 | 无 |
| 2 | 新增 `references/token_standard.md`（含 §3 表格规则 + CSV 规范 + 角色包规范 + 缓存友好排序） | references | #1 |
| 3 | 新增 `SKILL_INDEX.md` 角色包索引清单 | 技能库根 | #1 |
| 4 | 新增 `tools/excel_to_csv.py` 迁移工具 + 改造 `skill-evolution-skill/evolve_check_log.py` 为 csv 读写 | tools + skill-evolution | #1 |
| 5 | 改造 `tools/package_skills.sh`（源码单源→打包内嵌）/ `deploy_skills.sh`（--roles + 交接文档置首）/ `solidify.sh` | tools | #2 |
| 6 | 编排器 dev-project-team-skill v21.0.0：description 压缩（150~250 字）、§2.2 评审输出改 CSV、§2.1 加「先读交接文档」、角色包路由表、阶段切换压缩规则 | dev-project-team-skill | #2/#3 |
| 7 | 构建 7 个角色包源码目录（标准 SKILL.md + domain/ + `../shared/` 引用），共享能力迁至 `shared/` 单源 | 角色包×7 + shared | #3 |
| 8 | 30 个子技能正文瘦身 + Excel 引用替换 + DoD 输出改 CSV（按角色包逐包落地） | 包内 domain×30 | #4/#6 |
| 9 | 更新 references/directory_structure.md、api_contracts.md | references | #6-#8 |
| 10 | 存量 .xlsx 一次性迁移为 CSV（excel_to_csv.py）+ 交接文档改名迁移 | 项目台账/资产 | #4 |
| 11 | **实测门禁**：对比 #0 基线，验证注入 token / description / 单任务峰值降幅达到目标（见 §5），未达标不得关闭；通过后技能评审 → 打包 → 快照 → 部署 | 全库 | #2-#10 |

---

## 5. 预期收益（目标值，须经 §4-#11 实测门禁验证）

| 指标 | 现状 | 改造后（目标） | 收益 |
|------|------|--------|------|
| 注册技能数 | 39 个 | 8 个（7 角色包 + 1 编排器） | **-79%** |
| 系统提示 description | ~5K token | ~1.5K 字符（8 包 × 150~250 字） | **-60%+** |
| 注入型工具全量注入 | ~11 万 token | `--roles` 只部署所需包，随包数线性下降 | **视部署包数** |
| 单角色任务加载 | 需加载 39 技能 | 只加载对应角色包（标准工具元数据预载） | **-90%+** |
| Prompt Caching 命中 | 未优化 | 稳定规则前置，缓存前缀最大化 | **-30~60% 重复输入** |
| 新模型续作前置读取 | 需扫全库 | 只读 `交接文档.md`（≤150 行） | **-90%+** |
| 表格工具链 | openpyxl 依赖 | 纯 CSV/Markdown | 零依赖、可增量读 |
| 跨模型切换 | 需人工定位断点 | 交接文档优先硬约束 | 无缝续作 |

> 注：数值为**目标**，实施后以 #0 基线 vs #11 实测为准；未达阈值需复盘调整后再验收。

## 6. 风险与对策

| 风险 | 对策 |
|------|------|
| 辅助包「单源引用」与「自包含分发」冲突 | 源码库 `shared/` 单源（P0-2）；仅 `dist` 打包时自动内嵌副本，禁止源码手工复制，杜绝版本漂移 |
| 注入型工具仍递归读整个包 | 不靠改名规避（P0-1）；用 `--roles` 只部署所需包；`deploy_skills.sh --flat` 仅面向此类工具的整库场景 |
| 全生命周期多包累计超上下文 | 阶段门禁处强制 ContextHealthMonitor 压缩（P0-3）；实测峰值并设上限阈值 |
| CSV 丢格式（冻结/着色） | 用列顺序 + 状态列文字值（已闭环/待整改）替代 Excel 样式，工具可用 markdown/csv 渲染 |
| 存量 .xlsx 迁移出错 | excel_to_csv.py 迁移后与源文件行数比对，快照回滚保障 |
| description 压缩后触发失败 | 维持 150~250 字 + 触发词前置（P1-1）；#11 实测门禁覆盖触发召回用例 |
| 交接文档被跳过或双源 | 写入编排器 §2.1 铁律 + solidify.sh 自动刷新；`跨会话交接文档.md` 改名迁移，禁止并存（P2-2） |

---

**文档版本**：v21.0.1（方案稿，含行业最佳实践评审修订）
**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
