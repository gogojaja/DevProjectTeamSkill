
# AGENTS.md

## 项目定位

DevProjectTeamSkill：软件研发全生命周期多角色编排技能库（10 个角色包 + 1 个编排器）。本体即技能源码，不是业务应用。AI Agent 在本仓库的职责是**维护技能库本身**（skill 编写/结构/打包/部署），不是执行软件项目业务。

> **独立关联项目（仅登记不内嵌，单一信源）**：
> - 局域网 Git 基建由**独立项目 `dev-git-hub` 为单一信源**（`/Volumes/BR256G/dev-git-hub`，授权 AUTH-014）承载——Mac 局域网 bare 中枢 + Windows 全量副本 + WAN 灾备 + git 复杂远端操作工具（mirror_push/github_push/github_ip_refresh/restore_github_push/_gh_ip_probe/github_access 标准）。**所有 git 基建方案/工具/标准以 dev-git-hub 为唯一权威（见其 交接文档.md）**；本仓库**不保留实现**，仅经 **薄封装代理调用**（tools/ 下同名代理注入 PROJECT_ROOT 指向目标仓库）+ 引用登记。接口共享：dev-git-hub 脚本以 `PROJECT_ROOT`/`DPB_ROOT` 环境变量为目标仓库工作根（读其远端/台账），本仓库代理转发时注入。避免技能库膨胀与硬件配置耦合。详见 `/Volumes/BR256G/dev-git-hub/交接文档.md` 与 `/Volumes/BR256G/dev-git-hub/README.md`。
> - 定时任务管理由**独立项目 `dev-task-scheduler` 为单一信源**（`/Volumes/BR256G/dev-task-scheduler`，授权 AUTH-015）承载——基于 APScheduler 3.11.3 的跨项目调度引擎（幂等/重试/告警/状态持久化）。**所有调度器方案/工具/标准以 dev-task-scheduler 为唯一权威（见其 README.md）**；本仓库**不保留实现**，仅经 **薄封装代理调用**（tools/scheduler_proxy.py 注入 PROJECT_ROOT 指向目标仓库）+ 引用登记。避免技能库膨胀。详见 `/Volumes/BR256G/dev-task-scheduler/README.md`。
> - 多模型分层编排由**独立项目 `dev-model-router` 为单一信源**（`/Volumes/BR256G/dev-model-router`，授权 AUTH-016）承载——Router + DAG + Executor 三层架构（复杂度评估/模型选择/DAG 分解/分阶段执行/结果组装）。**所有编排器方案/工具/标准以 dev-model-router 为唯一权威（见其 README.md）**；本仓库**不保留实现**，仅经 **薄封装代理调用**（tools/model_router_proxy.py 注入 PROJECT_ROOT 指向目标仓库）+ 引用登记。避免技能库膨胀。详见 `/Volumes/BR256G/dev-model-router/README.md`。
> - 项目管理工具集由**独立项目 `dev-project-mgmt` 为单一信源**（`/Volumes/BR256G/dev-project-mgmt`，授权 AUTH-022）承载——RAID 管理/进展报告/变更协调/EVM 计算工具实现；方法论在本库 `role-project-mgmt` 技能（单一信源互补：方法在技能库，代码在独立项目）。立项 INC-2026-09-01-001（评分 94/100）。远端仓库待建。
> - 安全审计工具集由**独立项目 `dev-security-tools` 为单一信源**（`/Volumes/BR256G/dev-security-tools`，授权 AUTH-023）承载——审计台账/脱敏扫描/授权边界检查/密钥泄漏检测的**新增**工具；本仓库现有 `tools/audit.py`、`tools/desensitize/` **保留原位不迁移**。立项 INC-2026-09-01-002（评分 96/100）。远端仓库待建。
> - 测试工具集由**独立项目 `dev-test-tools` 为单一信源**（`/Volumes/BR256G/dev-test-tools`，授权 AUTH-024）承载——跨项目测试执行/覆盖率聚合/缺陷台账/报告生成工具实现；方法论在本库 `role-testing` 技能（单一信源互补）。立项 INC-2026-09-01-003（评分 95/100）。远端仓库待建。

## 仓库结构

```
.trae/skills/         技能源码（唯一事实来源）
  SKILL_INDEX.md      10 包路由索引
  references/         公共标准（token/csv/api 契约等）
  shared/             单源共享库：governance/evolution/authoring + references 副本
  dev-project-team-skill/   编排器（薄壳）
  role-*/             SKILL.md(根) + domain/ 流程 + *__resources/ 明细
tools/                打包/部署/固化脚本（.sh + .py 双实现）；全部工具支持 PROJECT_ROOT 环境变量注入，可被其他项目直接调用（见 references/tool_calling_standard.md）
交接文档.md            跨会话断点，改动后必须刷新
opencode.json         opencode 技能注册
```

## 核心规则（违反即返工）

1. **源码单源**：`.trae/skills/` 是唯一事实来源，`tools/deploy_skills.py`/`solidify.py` 均以它为源；共享内容只存 `shared/`，角色包用 `../shared/...` 相对引用；**禁止手工复制** shared/references 进角色包（打包时自动内嵌）。
2. **源码不备覆盖**：deploy 目标是 `.github/skills/`、`.claude/skills/`、`.agents/skills/`（开发固化）与全局库（生产载体，Windows：`C:\Users\<user>\.config\opencode\skills`；macOS/Linux：`~/.config/opencode/skills`），**永不覆盖 `.trae/skills/`**；改技能只在 `.trae/skills/` 源操作，改完即跑 `solidify` 部署到项目级三目录，生产发布走 `publish_production`（`publish_production` 现同时把发布集同步到 TRAE/WorkBuddy 等工具的全局技能目录，多工具全局生效，详见「生产发布」段）。
3. **新增/修改技能**：必须同步 `SKILL_INDEX.md` + `references/api_contracts.md`；description 150~250 字符（`做什么。<触发词>。Load when...`）。
4. **输出格式**：>4K token 或 >20 列 → CSV（UTF-8 with BOM）；仅回显首 5 行 + 行数。禁止 .xlsx。
5. **改动后固化**：任务完成执行固化脚本并刷新 `交接文档.md` 断点区，然后 git commit。macOS/Linux 用 `bash tools/solidify.sh "<说明>"`，Windows 用 `python tools/solidify.py "<说明>"` 或 `.\tools\solidify.ps1 "<说明>"`。固化后 TRAE 项目级（`.trae/skills/` 源码单源）与项目级三目录同步生效；生产消费需另行 `publish_production`（全局库 `~/.config/opencode/skills/`）。
6. **文件保护**：无明确指令禁止删除/移动/重命名文件。
7. **系统/项目外文件铁律**：修改、删除**系统文件（如 %windir%\System32、hosts、注册表）或项目外部文件（仓库之外路径，含其他项目目录）**必须：①先获得用户明确授权；②操作前强制备份到项目内 `.backup/`（含时间戳）；③操作留痕至 `13_安全审计台账.csv`。未获授权或未备份，一律禁止执行。该操作必须经 `security_audit` 前置审计。
 7a. **目录访问边界铁律**：本项目可读写/删除范围=本项目所在目录（启动时经 `declare_access_boundary` 声明入 `台账/26_访问边界.csv`）；本项目目录之外的任何访问一律经 `register_auth` 授权（`台账/14_授权登记.csv`），**未填有效期默认仅本次对话有效**，会话结束自动失效；跨会话须用户显式指定到期时间并留痕。操作目标在本项目目录外 → 先查 `26_访问边界.csv` + `14_授权登记.csv`，无授权禁止。
 7b. **审计四维定位铁律**：凡属「关键操作」（修改系统/项目外文件、授权登记、发布、基线固化、MCP 注册、客户端工具接入等），审计台账（`台账/13_安全审计台账.csv`）**必须**记录 `主机标识 / 客户端工具 / 模型名称 / 操作时间(ISO8601+TZ)` 四维度，并建议带 `会话ID` 聚合同次运行的多操作；统一由 `tools/audit.py` 写入（自动抓取主机名与操作时间）。主机名明文保留已获用户授权（见 `台账/14_授权登记.csv` AUTH-021，铁律 #8 B 级脱敏例外，范围限定本仓库）。异常发生后凭四维度可定位「哪台机器·什么客户端·什么模型·什么时间」。
8. **敏感信息分级处理铁律**：敏感信息统一按三级处理（细则见 `.trae/skills/references/iron_rules.md` §3）——**A 级禁止入库**（密钥/凭据/Token 只存别名，真实值走 `.secrets/`+凭据管理器）；**B 级脱敏入库**（本机/环境专属信息——**主机名、IP、用户名、绝对路径**提交公共仓库前必须脱敏，IP 完全脱敏为默认 `192.168.x.x`→`xxx.xxx.xxx.xxx`，保留主机名须用户授权，脱敏后复查全文）；**C 级正常入库**。提交前一律自问属于哪级。违反即禁止提交。
9. **废弃清理门禁铁律**：当 `架构资产/*/ADR` 任意决策状态标记为「废弃」后——①任何后续会话启动第一步必须先做「废弃资产完整性检查」（全库 grep 该资产引用 + 端口监听/进程运行/LaunchAgent 加载三查），发现残留立即登记并清理；②基线固化（`tools/solidify.sh` 第 4 硬门禁 `check_deprecation_cleanup.py`）强制移除废弃资产，存在引用或运行态残留则中止固化（未通过不得固化）。该规则随项目分发生效，与编排器 `dev-project-team-skill` §2.2-7 对齐。
10. **需求-架构-代码 三方一致性铁律**：防止需求↔架构、架构↔代码 漂移——统一标识符（`REQ-/ADR-/AE-/MOD-/TC-`）；以《需求-架构-代码追溯矩阵.csv》为单一事实来源连续维护（禁止事后突击补表）；阶段流转前（尤其 需求→架构、架构→开发、开发→测试）强制运行 `tools/check_traceability.py`，孤儿（无父链接的需求/架构/代码/测试）或断链超容忍度则**驳回流转**；代码评审须含「孤儿代码」检查。依据 NASA SWE-059 / EN 62304 / ASPICE / ArchUnit，与编排器 `dev-project-team-skill` §2.2-8 对齐。
11. **批量编辑铁律（防并行污染）**：对**多个文件**做同类批量修改（引路径替换、前缀补全、关键词替换）时——①**禁用并行 edit 工具**，必须用**单一 python 脚本**串行遍历每个文件、逐文件落盘；②脚本跑完**立即 `git diff --stat` + 抽查若干文件**校验无污染（防止成对替换写入他文件 / 中文标点误删）；③单文件微调用 `edit` 工具，**编辑后立即读回确认**；④发现误写立即 `git checkout -- <文件>` 还原，禁止带病继续。违反即可能污染源码（参考 DEV-001 事故：并行 edit 误把 governance 内容写入 8 个无关 domain 文件）。
12. **运行时自变留痕不入库铁律（防推送死循环）**：由脚本每次运行**自动追加/自变**的日志/台账类产物（如 `32_镜像同步记录.csv` 被 `mirror_push.py` append）**必须 `git rm --cached` + 加入 `.gitignore`**，禁止 git 跟踪——否则每次运行产生未提交改动→又 commit→又要 push，形成无意义推送死循环（参考 DEV-002 事故：为归档镜像台账反复 push 了 3+ 次）。一次性人工登记的审计台账（`13/14/26` 等）不受限。
13. **语言铁律（全程中文）**：所有项目（含本技能库维护）的对话、产出文档、台账、报告、提交说明、面向用户的回复一律使用中文；代码标识符可保留英文，但注释/提交信息/文档/说明文字必须用中文。不主动切换其他语言，除非用户明确要求。细则见 `.trae/skills/references/iron_rules.md` §8。
14. **产物落盘铁律（禁入系统盘/C 盘）**：所有任务生成的产物（文档/报告/台账/脚本/导出文件/快照/构建物等）必须写入**本项目目录内**，严禁写入系统盘或 C 盘等非项目路径；确需新建目录只能建在项目目录内且经用户确认。与目录访问边界铁律（#7a）同源，项目外路径一律经 `register_auth` 授权。细则见 `.trae/skills/references/iron_rules.md` §9；项目初始化时由 `role-project-init` 的 `write_project_iron_rules` 落地为项目根 `项目铁律.md`。
15. **执行合同闸门铁律（防擅作主张）**：AI 执行**任何带副作用操作**（不含 Tier1 纯读）前，必须走「六段执行合同」——①理解（复述本轮指令明确操作项）②拆解（目标文件/改什么/不改什么/量级）③清单（输出审批五要素表：操作编号+操作名/目标路径/完整改动内容/风险级/授权+备份）④确认（等用户确认词白名单 `执行/OK/确认/改吧/方案X`，**不接受模糊措辞**，未确认前什么都不做）⑤执行（严格按清单，参数变更须回确认段）⑥复验（给客观证据链，禁"我认为成功"）。工具风险分级：Tier1 只读自由 / Tier2 范围写（项目内+本轮指令提及文件，清单+确认）/ Tier3 高辐射（外部文件写、`~/.config/*`、删除、推送、`solidify`/`publish_production`/`mirror_push` 等，须 清单+参数哈希+备份+授权+确认词+审计台账 6 件套）。审批绑定**参数哈希**（操作名+目标路径+改动内容 SHA 前10位，由 `tools/audit.py --param-hash` 算），参数变更旧哈希作废须重确认。越界识别：红灯（未确认即执行/顺带范围外/参数变不重申请/路径越界）、黄灯（清单要素不全/风险级标低/接受模糊确认词）；**连续 2 次红灯 → 全闸模式**（下一轮所有 Tier2/Tier3 走完整 6 段 + 额外一轮确认，1 次合规后解除）。本合同为铁律 #7（授权→备份→留痕）的**执行前前置强化**，不替代 #7。台账 13 扩展 `确认词`+`参数哈希` 列、14 扩展 `确认词` 列，由 `tools/audit.py` 写入。单一事实来源：`docs/AI助手行为门禁与授权合同.md`。
16. **同质操作熔断与不胜任检测铁律（防碎片提交循环）**：当某工具/客户端（如 TRAE）反复执行**同质化无实质新进展操作**（固化/提交/审计留痕/交接断点刷新/推送重试等 1~2 文件的小改动完整闭环）时——①**L1 提交批量化**：同质小改动（审计/断点/台账/文档 1~2 文件）应合并到相关功能提交，禁止碎片化单独立提交（`tools/commit_batch_check.py` 检查，`--gate` 强制硬阻断）。②**L2 固化频次提示**：1 小时内固化/审计操作 >3 次且均为同质 → 提示攒批（`commit_batch_check.py --freq-scan`）。③**L3 不胜任判定**：同质操作密度 ≥阈值（缺省 5 次/会话，`tools/incompetence_detector.py --threshold N` 可调）**且无实质新进展**时——判定当前工具/模型**不胜任**；有实质新进展（评审/方案/落地/复盘等）则视为胜任不误伤。④**L4 交接熔断**：触发 L3 且确认多次重复 → **立即明确停止当前工作**（不再固化/提交/重试）→ **开始交接**（写 `交接文档.md` 断点 + 13 审计留痕）→ **推荐替代工具/模型**（按 `references/dev_platform_catalog.md` 平台矩阵给候选：本地 CLI 换 opencode/claude-code、同平台换 WorkBuddy/Cursor、机械操作用低价档/复杂任务用强档）。判定依据对齐 DORA VSM（等待时间/瓶颈为隐藏低效指标）+ GitHub PR（相关变更聚合提交标准）+ 反信号（区分「高频有效」vs「同质无进展」）。违规表现：碎片提交循环反复发生、固化连刷断点、推送失败不停重试。细则见 `docs/工具不胜任熔断方案.md`。

## 命令

> **跨平台约定**：所有脚本均提供 `.sh`（macOS/Linux）+ `.py`（跨平台通用，Windows 主推）双实现，功能一致；Windows 额外提供 `.ps1` 原生封装。优先使用对应平台的脚本。

### 迁移初始化（新机器首次执行）

> 新机器 clone 本仓库后，运行以下脚本完成一键初始化（钩子安装 + dev-git-hub 定位 + remotes 配置 + 凭据引导 + 代理链路验证）：

```sh
bash scripts/bootstrap_remotes.sh       # macOS/Linux
python scripts/bootstrap_remotes.py     # 跨平台/Windows 主推
```

- **dev-git-hub 定位优先级**：`DEV_GIT_HUB_ROOT` 环境变量 > 同级目录 `<repo>/../dev-git-hub` > `.hub_root` 配置文件
- 本仓库**不内嵌推送工具实现**（单一信源在 dev-git-hub），经 `tools/_hub_proxy.py` 动态解析路径 + `tools/*.py` 薄封装代理转发
- **本地提交完全独立**（不依赖 dev-git-hub），仅远端推送需 dev-git-hub 工具；脱离 dev-git-hub 时用原生 `git push` 兜底

### 工具外部调用规范（2026-08-31 起）

> 全部 `tools/*.py` 工具均支持 `PROJECT_ROOT` 环境变量注入，可被其他项目直接调用。规范见 `references/tool_calling_standard.md`。

- **ROOT 解析铁律**：`os.environ.get("PROJECT_ROOT", __file__兜底)` — 禁止硬编码绝对路径、禁止 CWD 独占
- **外部调用方式**：`PROJECT_ROOT=/path/to/target python3 /path/to/DevProjectTeamSkill/tools/<name>.py`
- **今后新工具**：开发时必须遵循 `tool_calling_standard.md`（CLI 入口 + `--help` + PROJECT_ROOT 注入 + 无副作用模式）

### 固化与部署

**macOS / Linux（bash）：**
```sh
bash tools/package_skills.sh            # 打包全部 10 角色包到 dist/
bash tools/package_skills.sh --role role-testing
bash tools/deploy_skills.sh --roles role-a,role-b
bash tools/solidify.sh "说明"           # 一键固化：3 硬门禁+交接刷新+快照+打包+部署项目级三目录(不碰全局库)
```

**Windows（PowerShell / Python，主推）：**
```powershell
.\tools\solidify.ps1 "说明"             # PowerShell 一键固化（自动找 Python）
# 或直接调用 Python 版：
python tools/solidify.py "说明"
python tools/package_skills.py
python tools/deploy_skills.py --roles role-a,role-b
```

### 生产发布（环境/版本隔离，2026-08-20 起）

> **生产消费载体 = 全局库 `~/.config/opencode/skills`**（opencode 仅扫描 6 个固定位置，`skills.paths` 实测不生效）。开发固化（`solidify`）**只部署项目级 `.github/.claude/.agents` 三目录**，不再自动触碰全局库；生产技能由 `publish_production` 独占发布，防开发版本污染生产。

```sh
bash tools/publish_production.sh                  # 门禁(版本/闭环/发布级/废弃/脱敏)→留档~dev 版本目录→current软链→发布全局库
bash tools/publish_production.sh --dry-run        # 仅探测
python tools/publish_production.py                # 跨平台/Windows 主推
```

- 留档：`~/dev-project-team-skill/v<版本>/`（不可变）+ `~/dev-project-team-skill/current`（软链=最新稳定版）
- **发布集（source of truth = 源码单源 + 配套工具/文档）**：角色包 ×10 + `references/` + `shared/` + `SKILL_INDEX.md` + **`tools/` + `docs/`**（SKILL_INDEX/SKILL.md 引用大量 `tools/*` 与 `docs/*`，必须随发布集输出，否则消费端按文档调用脚本路径不存在）。`publish_production`/`deploy_skills`/`solidify` 三套复制集统一（若改发布集必须三处同步）。
- **脱敏门禁语义**：脱敏扫描覆盖**发布集全部源头**（`.trae/skills/` + `tools/` + `docs/`）；A 级**真实凭据**硬拦截（中止发布）；A 级**占位符**（`<...>`）与 `desensitize/desensitize.py` 规则定义示例输入、B 级**示例/公开信息**（GitHub 公网 IP、example 邮箱、示例路径）仅告警+清单，不阻断发布。
- **多工具全局生效（2026-08-27 起）**：`publish_production` 除部署 opencode 全局库（`~/.config/opencode/skills`）外，自动把**同一发布集**同步到**已安装工具**（其父目录存在）的全局技能目录，使各工具同时全局生效。矩阵（依据 `references/cross_tool_standard.md`）：TRAE 国际版 `~/.trae/skills/`、TRAE 中国版 `~/.trae-cn/skills/`、WorkBuddy `~/.workbuddy/skills/`、Claude Code `~/.claude/skills/`、Copilot `~/.copilot/skills/`、Agents `~/.agents/skills/`。opencode 用整库重建；其余工具用**精确同步**（仅清理本仓库发布集子项 `ALL_ROLES+references+shared+tools+docs+SKILL_INDEX.md`，保留用户其他全局技能），并兼容 Windows 目录 junction/symlink（`os.rmdir` 仅删链接本身，不误删目标内容）。
  - 控制参数：`--no-extra-globals`（仅 opencode，原行为）/ `--extra-globals trae,workbuddy`（显式指定）/ `--all-globals`（全部已知工具，即使未安装也创建）；默认自动发现已安装工具。
- 其他项目 opencode 通过全局库自动发现生产技能；本项目开发用项目级三目录
- 生产发布为外部目录操作，按铁律 #7/#7a `register_auth` 授权 + `.backup/` 备份 + 台账留痕

### 其他工具

```sh
python tools/check_skill_links.py       # 技能库引用可达性门禁（拦截 .// 残留与 __resources 断链；已纳入 lint_repo ⑥）
python tools/mpv_cli.py --target <对象> --perspectives architect,security --report <CSV>  # 评审能力工具化（ADR-2026-08-29-001 A）：MPV 五视角评审落盘 CSV + 脱敏扫描 + 对接 check_review_artifacts 门禁；--dry-run 预览 / --validate 校验已有报告
python tools/retro_cli.py --stage <阶段> --object <对象> --good "" --improve "" --action "<行动项>;owner:x;deadline:yyyy-mm-dd"  # 复盘收割工具化（ADR-2026-08-29-001 B）：写 22_阶段复盘 + 提取行动项(owner/deadline) + --write-lessons 登记经验库；写库前强制脱敏扫描
python tools/check_retro_closure.py     # 复盘行动项回环（ADR-2026-08-29-001 B companion）：列出未关闭行动项；--mark-closed "<关键词>" 标记已关闭；Atlassian 复盘闭环标准
python tools/improve_cli.py --diagnose <目标>  # self-improve 独立工具形态（ADR-2026-08-29-001 D）：偏差侦测清单 / --propose 登记提案台账 33 / --experiment 回填验证状态
python tools/commit_batch_check.py       # 同质操作熔断 L1/L2（铁律#16）：提交批量化检查（--gate 硬阻断）+ 1 小时固化频次提示（--freq-scan）；防碎片提交循环
python tools/incompetence_detector.py --threshold N   # 同质操作熔断 L3/L4（铁律#16）：同质操作密度 ≥阈值(缺省5)且无实质新进展 → 判定不胜任 → 立即停止+交接+推荐替代工具/模型；--json 结构化输出 / --recommend 推荐替代；对齐 DORA VSM + GitHub PR 聚合提交标准
python tools/scope_tracker.py init      # 范围跟踪初始化：建扩展 RTM（含 PRIORITY/SCOPE_STATUS/BASELINE_VER 等）+ 06/07 范围台账（含表头与示例）
python tools/scope_tracker.py metrics [--write]   # 范围覆盖度指标 + 健康分（--write 写 07_范围跟踪台账 快照）
python tools/scope_tracker.py gate [--max-violations 0]  # 范围门禁：一致性+蔓延/缩水检测+健康分，写 07，结论 exit(驳回/警告/通过)
python tools/scope_tracker.py change --req REQ-001 --title "..." --type 范围调整 --severity 主要 --approver 用户 --baseline-from v1.0.0 --baseline-to v1.0.1  # 登记变更请求→06_范围变更台账（CCB 五维影响）
python tools/excel_to_csv.py            # 迁移存量 xlsx→csv
python tools/github_push.py --dry-run   # GitHub 真实 IP 推送：dry-run 预览（仅探测，不推送）
python tools/github_push.py             # GitHub 真实 IP 一键推送（固定动作：候选IP→可达+TLS证书合法探测→绑定真实IP push origin）
python tools/mirror_push.py --verify    # 双端同步检查（会话启动必经步骤：fetch origin+mirror → 对比领先/落后，分叉即阻断推送）
python tools/mirror_push.py             # 双推：origin(GitHub) 直走真实 IP（缓存IP→探测候选→失败自动刷新；mirror 普通推送）
python tools/scheduler_proxy.py status  # 调度器状态（经薄封装代理调用 dev-task-scheduler）
python tools/scheduler_proxy.py list    # 列出任务
python tools/scheduler_proxy.py run <任务名>  # 手动执行任务
python tools/model_router_proxy.py assess "任务描述"  # 评估任务复杂度（经薄封装代理调用 dev-model-router）
python tools/model_router_proxy.py select "任务描述"  # 选择模型
python tools/model_router_proxy.py decompose "任务描述" --output tasks.json  # 分解任务为 DAG
python tools/model_router_proxy.py execute tasks.json  # 执行 DAG
python tools/model_router_proxy.py assemble tasks.json  # 组装结果
python tools/desensitize/desensitize.py --scan <目标>  # 文档脱敏：扫描模式
python tools/desensitize/desensitize.py <目标> -o <输出>  # 文档脱敏：按内置规则批量替换
python tools/desensitize/desensitize.py --dictionary tools/desensitize/desensitize_dictionary.csv <目标> -o <输出>  # 文档脱敏：规则 + 脱敏字典关键字联合脱敏（字典维护见 tools/desensitize/DESENSITIZE_DICTIONARY.md）
python tools/nightly_quality_gate.py list  # 夜间质量门禁：列举 registry 项目
python tools/nightly_quality_gate.py run --dry-run  # 夜间质量门禁：仅探测 registry（不做副作用）
python tools/nightly_quality_gate.py run [--target <alias>]  # 夜间质量门禁：对全部/指定项目跑 quality_gate+单测+脱敏扫描→36/39 台账+告警（AI 语义评审默认关，ENABLE_AI_REVIEW=true 开启且非阻断）
python tools/remove_watermark/remove_watermark.py <目标> --auto --in-place  # 去水印：自动识别（Word/PPT/Excel/PDF/图片/文本 6 类；--text 关键字 / --rect/--corner 区域 / -o 输出副本；详见 tools/remove_watermark/README.md）
bash scripts/install-hooks.sh           # 新 clone 后一键安装 pre-commit 环境门禁钩子
git commit                              # 每原子改动一次提交（钩子未安装时先跑 install-hooks.sh）
```

> **环境门禁钩子**：`.githooks/pre-commit` 提交前自动检查 A 级密钥/B 级脱敏/.env 与 .secrets 禁提交/大文件 >4K。失败阻断提交（`git commit --no-verify` 仅应急，不推荐）。
>
> **固化闭环说明**：`solidify` 内置 3 个硬门禁（版本一致性/闭环执行/发布级），门禁未过则中止；通过后自动刷新交接文档断点区、生成版本快照、打包 dist、部署到项目级 3 个目标目录（项目级 .github/.claude/.agents）。TRAE 项目级直接从 `.trae/skills/` 读取（源码单源）；opencode 全局生产载体（`~/.config/opencode/skills/`）由 `publish_production` 独占发布，`solidify` 不再触碰，防开发版本污染生产。
>
> **Auto-deploy 注意**：`post-commit` 钩子的自动部署（`.auto-deploy-enabled`）默认同步到项目级三目录；如需同步全局库请改跑 `publish_production`（生产发布才应更新全局库）。
>
> **提交后自动部署（可选）**：在仓库根创建 `.auto-deploy-enabled` 文件后，每次提交若包含 `.trae/skills/` 下的变更，`post-commit` 钩子会自动执行 `deploy_skills.py` 将技能同步到 opencode 全局库（轻量部署，不含门禁/快照/打包）。启用方式：`touch .auto-deploy-enabled`（macOS/Linux）或 `New-Item .auto-deploy-enabled`（PowerShell）。

## GitHub 访问异常处理规则（win32 / macOS / PowerShell / zsh 环境）

> **固定动作（P-001，减少反复操作）**：GitHub push 一律用 `py -3.11 tools/github_push.py`（自动探测可达+证书合法 IP → 绑定真实 IP push origin；**探测失败自动刷新 IP 重试**）；双推场景用 `py -3.11 tools/mirror_push.py`（origin **直走真实 IP**——先试上次成功 IP 缓存、失效再探测候选、探测失败自动刷新重试；mirror 普通推送）。手动 `git push origin` 仅在该命令失效后用于人工兜底。

本机访问 `github.com:443` 偶发 DNS 解析到坏 IP 或全部候选 IP 不可达，最常见根因是 DNS 实效，导致远端环境无法访问。故障现象：`Failed to connect` / `Could not connect` / `Recv failure: Connection was reset` / `nc: connection failed, SOCKS error 2`。

### 0. 动态补充 DNS Resource Records（ipaddress.com）

`docs/github_ip_records.csv` 的候选 IP（§1）是**静态快照，可能过期**。出现「全部候选 IP 不可达 / DNS 实效」时，**先动态刷新最新 A 记录，再决定恢复路径**：

1. **一键动态刷新**（首选；只要本机 DNS 正常即可解析，即使 `github.com:443` 被墙也能解析）：
   ```powershell
   py -3.11 tools/github_ip_refresh.py            # 系统解析器(nslookup) 动态补充
   py -3.11 tools/github_ip_refresh.py --doh      # 追加 DNS-over-HTTPS(1.1.1.1/dns.google)
   ```
    工具经系统解析器 / DoH 动态解析 `github.com / api.github.com / gist.github.com / codeload.github.com / raw.githubusercontent.com / github.global.ssl.fastly.net / assets-cdn.github.com / fastly.net / github.io` 的当前 A 记录，去重追加进 `docs/github_ip_records.csv`，并对 `github.com` 候选 IP 做**可达性 + TLS 证书合法性双重探测**（SNI=github.com，仅「可达且签发合法 github.com 证书」的 IP 才能用于 hosts 覆盖——部分存活 IP 如 140.82.112.4 证书主体不匹配，git/schannel 会 `SEC_E_WRONG_PRINCIPAL` 失败）；打印仅含证书合法 IP 的 hosts 覆盖块，并可 `py -3.11 tools/github_ip_refresh.py --write-hosts` 自动备份+写入（需管理员/root 权限）。
2. **权威站点人工核验**（页面受 Cloudflare 挑战保护，无法自动抓取，可人工抄录后登记）：
   - https://sites.ipaddress.com/github.com/
   - https://sites.ipaddress.com/fastly.net/
   - https://sites.ipaddress.com/assets-cdn.github.com/
   
   在页面「DNS Resource Records」区读取最新 A 记录，用以下命令登记（避免手改 CSV）：
   ```powershell
   py -3.11 tools/github_ip_refresh.py --manual github.com=20.205.243.166,140.82.112.4 assets-cdn.github.com=185.199.108.153 fastly.net=151.101.0.0
   ```
3. **刷新后仍不可达**：走 §3 token 推送或 §4 VPN/代理；必要时按铁律 #7 临时 hosts 覆盖 `github.com <可达且证书合法IP>`（先备份、留痕 `13_安全审计台账.csv`）。最简方式：`py -3.11 tools/github_ip_refresh.py --write-hosts`（自动挑「可达+证书合法」IP、备份 `hosts`、写入；**需管理员/root 权限运行 opencode**，否则仅备份并提示授权）。镜像兜底：直接 `git pull mirror main`（Gitee 与 GitHub 历史一致）。

> 设计原则：**DNS 解析与 TCP/443 可达性解耦**——`nslookup` 能解析说明 DNS 正常、问题在路由；动态刷新保证候选池始终是最新「DNS Resource Records」，而非依赖过期快照。

### 1. 候选 IP 池（按优先级排序）

优先保留真实 IP 记录；若 DNS 失效，直接用候选 IP 做临时解析回退。完整 DNS 资源记录见 `docs/github_ip_records.csv`（含 api/ssh/gist/raw/pages/Fastly CDN 等子域）。

**github.com 主站（当前解析）：**
```
20.205.243.166    ← 多 DNS 服务器确认（8.8.8.8/1.1.1.1/208.67.222.222）
```

**github.com 历史可达 IP（AS36459 140.82.112.0/20）：**
```
140.82.112.4      ← 已验
140.82.113.4      ← corpus.lantern.io 记录
140.82.114.4      ← 已验
140.82.121.4      ← 已验
```

**GitHub Pages / assets-cdn（AS36459 185.199.108.0/22）：**
```
185.199.108.153   ← github.io / assets-cdn
185.199.109.153
185.199.110.153
185.199.111.153
```

**raw.githubusercontent.com / github.map.fastly.net（Camo/头像/媒体 CDN）：**
```
185.199.108.133   ← raw / camo / avatars
185.199.109.133
185.199.110.133
185.199.111.133
```

**github.global.ssl.fastly.net（Fastly 全局 CDN）：**
```
162.125.34.133    ← DNS 确认
```

**Fastly 公网 IP 段（assets-cdn 走 Fastly）：**
```
23.235.32.0/20    151.101.0.0/16    199.232.0.0/16    146.75.0.0/17
104.156.80.0/20   140.248.64.0/18   185.31.16.0/22
```

### 2. 连通性验证流程

```powershell
# 先解除代理，避免 SOCKS/HTTP 代理造成误判
Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:ALL_PROXY -ErrorAction SilentlyContinue

# 逐个测试候选 IP（超时 8 秒）
$ips = @("20.205.243.166","140.82.112.4","140.82.113.4","140.82.114.4","140.82.121.4","185.199.108.153","162.125.34.133")
foreach ($ip in $ips) {
  $r = curl.exe -s -o NUL -w "%{http_code}" --connect-timeout 8 --resolve github.com:443:$ip https://github.com
  Write-Output "$ip -> $r"
}
```

```powershell
# 尝试刷新本地 DNS 缓存
ipconfig /flushdns
```

```powershell
# 如全部不可达，用 --resolve 强制绑定可达 IP 执行 git 操作
curl.exe -s --resolve github.com:443:140.82.112.4 https://github.com
curl.exe -s --resolve github.com:443:20.205.243.166 https://github.com
```

### 3. push 需带凭据 token（fine-grained PAT，Contents read/write；token 由用户提供，勿硬编码入库）

```powershell
$url="https://gogojaja:<token>@github.com/gogojaja/DevProjectTeamSkill.git"
git remote set-url origin $url        # 临时带凭据
git push origin main
git remote set-url origin "https://github.com/gogojaja/DevProjectTeamSkill.git"  # 用完还原
```

> PowerShell 拼接 `https://user:token@host/path` 直传会损坏 URL，必须经 `git remote set-url` 传参。

### 4. 其他故障处理

- `api.github.com` 偶发 CRL 离线（`CRYPT_E_REVOCATION_OFFLINE`）为瞬时网络问题，重试即可。
- 推送成功后 `git rev-parse HEAD origin/main` 应一致（领先/落后 0）。
- 全部 IP 不可达时，建议用户使用 VPN/代理打通 GitHub 后再操作。

### 5. 数据来源

- DNS 解析：`nslookup -type=A github.com 8.8.8.8` / `1.1.1.1` / `208.67.222.222`
- **动态刷新工具**：`tools/github_ip_refresh.py`（系统解析器 / DoH 动态补充 `docs/github_ip_records.csv`；`--manual` 登记 ipaddress.com 人工抄录）
- GitHub Meta API：`https://api.github.com/meta`（返回完整服务 IP 段）
- Fastly 公网 IP：`https://api.fastly.com/public-ip-list`
- 权威站点核验：`sites.ipaddress.com/{github.com,fastly.net,assets-cdn.github.com}`（Cloudflare 挑战保护，人工读取 DNS Resource Records）
- 社区记录：`docs/github_ip_records.csv`（含历史 IP、各子域、Fastly CDN 节点）

## 国内镜像同步（地缘风险对冲）

GitHub 为境外服务器，**网络访问不稳定 + 存在地缘政治风险**。为避免单点失联导致源码/台账无法推送或丢失，采用**国内代码托管镜像**对冲：以 Gitee（码云）为主镜像（最像 GitHub、免费导入+同步、HTTPS/SSH 稳），备选 GitCode / 阿里云效 Codeup / 腾讯工蜂 / 华为云 CodeHub / AtomGit。

### 1. 同步策略（双推为主，定时校验为辅）
- **主策略：每次提交双推** `origin`(GitHub) + `mirror`(Gitee)。用 `tools/mirror_push.py` 逐目标推送，**单目标失败不阻断另一个**，并写 `台账/32_镜像同步记录.csv` 留痕。
- **熔断器（杜绝反复重试）**：`mirror_push.py` 内置熔断，凭据认证失败（Authentication failed/403 等）→ 对目标 remote 置**阻断**状态，此后直接跳过**不再重试**、也不写 32 台账（凭据失败留痕不入库）；仅当凭据更新（token 哈希变化）或 `--force`/`--unblock` 才解除。网络/其他失败（连接重置/超时/DNS）→ **默认自动真实 IP 回退**（先试 `.secrets/gh_push_ip_cache.txt` 成功 IP，失效探测候选；`--no-realip` 关闭）→ 仍失败才置**冷却**（默认 15 分钟），冷却期内跳过不重试。状态存 `.secrets/mirror_push_state.json`（gitignore）。辅助命令：`--force`（立即重试）、`--status`（查看状态）、`--unblock <remote|all>`（解除）。退出码 0=成功 / 1=本次尝试失败 / 2=全部被阻断或冷却跳过。
- **辅策略：Gitee 侧「仓库同步」** 周期性从 GitHub 拉取兜底（即使本机某次双推遗漏，也能补回）；也可在 Gitee 创建仓库时「从 GitHub 导入」。
- 不要依赖「本机定时从 GitHub 拉取再推国内」作为唯一手段——本机访问 GitHub 本身会 flapping，反而单点失败。

### 2. 凭据（铁律 #3 A 级，禁止入库）
- 国内 token（fine-grained PAT，Contents read/write）**只经环境变量 / `.secrets/` 文件 / 系统钥匙串提供**，`tools/mirror_push.py` 通过 `tools/load_secret.py` 跨平台自动装载（env > `.secrets/<name>` > macOS Keychain），并以 `url.<auth>@.insteadOf` 注入，**绝不打印、不写入仓库、不硬编码**。
- 三种提供方式（任选其一，脚本自动读取，无需手动 export）：
  - **a) 环境变量**（临时、最常用）：
    ```powershell
    # Windows (PowerShell)
    $env:GITEE_TOKEN="<从 Gitee 设置→私人令牌 读取>"; $env:GITEE_USER="gogojaja"
    py -3.11 tools/mirror_push.py
    ```
    ```bash
    # macOS / Linux (zsh/bash)
    export GITEE_TOKEN="<从 Gitee 设置→私人令牌 读取>"; export GITEE_USER="gogojaja"
    python3 tools/mirror_push.py
    ```
  - **b) 文件**（持久、gitignore 不入库）：写 `.secrets/gitee_token` 与 `.secrets/gitee_user`
  - **c) macOS Keychain**（系统级安全存储）：
    ```bash
    security add-generic-password -s gitee_token -a gogojaja -w "<token>"
    python3 tools/mirror_push.py     # 自动从钥匙串取密，无需 export
    ```
- 跨平台约定：本仓库 `tools/*.py` 均为跨平台脚本——Windows 用 `py -3.11`，macOS/Linux 用 `python3`，其余逻辑一致。

### 3. 初始化步骤（搭框架后由用户补全）
1. 在 Gitee 建仓库 `DevProjectTeamSkill`（建议「从 GitHub 导入」或空仓）；
2. 添加 remote：`git remote add mirror https://gitee.com/<user>/DevProjectTeamSkill.git`；
3. 配置凭据：把 `GITEE_TOKEN` 放入系统凭据管理器 / `.secrets/gitee_token`（仓库已 gitignore `.secrets/`）；
4. 此后统一用 `py -3.11 tools/mirror_push.py` 替代裸 `git push`（脚本会自动跳过未配置的 remote，框架阶段不报错阻断）。

### 4. 同步台账
- `台账/32_镜像同步记录.csv`（UTF-8 BOM）：同步编号 / 同步时间 / 源commit / 目标remote / 远程URL(脱敏) / 状态 / 耗时秒 / 说明。每次双推追加，便于审计与故障回溯。

## 效率约定

- 先读根 `SKILL.md` 路由表 → 命中后只读目标文件，**禁止**一次性 Read 全部文件。
- 目录内先 `ls` / 文件列表，小文件直接 Read，大文件 grep 定位后读片段。
- 日志与命令输出仅回显变更/错误，不 cat 大文件全文。
- 引用路径保持相对，避免改动后全文失效。
