# CHANGELOG — DevProjectTeamSkill 版本演进史

> 版本基于各角色包 SKILL.md 版本号与 SKILL_INDEX.md 末尾推断整理。
> 编排器文档版本：v21.12.0（2026-09-01）。

## [v20.2.0] - 约2026-08-04 - 初始框架

- 30 个子技能初始形态，技能库框架成型，确立 `.trae/skills/` 唯一事实来源与 `token_standard` 公共底座。
- 建立角色包雏形、台账目录与交接文档机制。

## [v21.0.0] - 2026-08-04 - 角色包模型重构

- 30 个子技能重组为 **7 角色包 + 1 编排器**（`dev-project-team-skill` 薄壳化，~60 行）。
- `description` 压缩至 150~250 字；评审结果改 CSV；新增阶段切换上下文压缩规则。
- 编排器明细外置各角色包 SKILL.md 与 domain/*.md。

## [v21.0.1] - 2026-08-06 - 需求分析角色包

- 新增**阶段 / 活动裁剪**：启动阶段 `init_tailor` 产出 `00_阶段配置.csv`，仅加载保留阶段角色包（第 0 阶段与总控强制保留）。
- `role-requirements-analysis`（需求）能力明确：收集 / 七维度分析 / IEEE 830 SRS / 评审 / 变更 / 双向追溯。

## [v21.2.0] - 2026-08-06 - 项目启动角色包

- 新增**敏捷迭代模式** + **技能维护模式**（skill-authoring 六步流程）。
- `role-project-init` 立项 / 章程 / 干系人 / RACI / 问题升级 / 基线初始化；合并角色加载模式（单 / 多 / 双角色裁剪归并为「角色组合加载」）。
- 新增 `18_迭代配置.csv`、`20_*` 台账雏形。

## [v21.3.0] - 2026-08-07 - 增强能力（模型选型 / 阶段复盘 / 环境配置）

- 每阶段开始 `select_model`（21_模型选型：免费→低价→国内稳定→排除国外）。
- 阶段末 `retrospect_harvest`（22_阶段复盘 + 23_复用资产）。
- 环境准备 `record_env_config`（20_环境配置，密钥别名）。
- 新增 `references/model_selection.md` + `environment_standard.md`；台账 20→24。
- 同期 v21.3.x：双平台兼容强制、铁律防压缩遗忘、模型路由与网关策略、合并加载模式收敛。

## [v21.4.0] - 2026-08-10 - 嵌套能力（并行编排 / 多视角验证）

- 编排器内嵌 **team-orchestration**（并行编排：team / ultrawork / ralph / ultraqa 四模式）。
- 编排器内嵌 **multi-perspective-validation**（多视角验证：五视角并行）。
- 模型档位由 Opus/Sonnet/Haiku 改为 **S0~S3 四档 + 免费体系**，弱推理模型可跑 S0/S1，S2/S3 高危仍要求强模型。
- 多角色并行方案冲突按 `priority-arbitration.md` 仲裁（P0~P6 优先级，一票否决，留痕）。

## [v21.5.x] - 约2026-08-14~16 - 多项目隔离 / 启动治理 / 组织架构与问题升级

- v21.5.0~v21.5.3：新增**多项目环境隔离**最佳实践（Git / 运行时 / 数据库 / Docker 四层隔离）；第 5 层全局环境资产注册与冲突仲裁（25_环境资源清单，CMDB CLI `tools/cmdb/cmdb-cli.py`）。
- v21.5.4~v21.5.5：敏感信息分级处理矩阵（A/B/C 三级）+ 环境信息脱敏铁律。
- v21.5.6：技能维护模式闭环执行能力升级（维护产物强制「闭环执行系统」章节，硬门禁）。
- v21.5.7：多角色并行优先级仲裁规则（P0~P6）。
- v21.5.9：**启动治理完善**——`role-project-init` 新增 `define_org_structure`（27_组织架构.csv RACI）与 `define_issue_escalation`（12_风险问题台账 P1~P4 + 四级升级阶梯 + 单一 Owner）；`check_ready` 硬门禁。

## [v21.6.0] - 2026-08-16 - 项目群 / 项目集协同层

- 新增第 9 角色包 **role-program-mgmt**（定义 / 收益 / 依赖 / IMS 进度 / 标准一致 / 评审 / 收尾；Program Board Tranche 边界决策）。
- 治理三层模型（项目<项目群<组合）；新台账 28_项目群注册 / 29_项目依赖矩阵 / 30_项目群主进度 / 31_文档配置管理。
- v1.1.0 文档与配置管理 discipline；v1.1.1 将 CMDB 纳入程序管理范畴（环境就绪第四 Gate）。

## [v21.7.0] - 2026-08-18 - 第 9 角色包（管理咨询）/ 双套环境拓扑 / 目录规整

- 新增第 10 角色包（编排器视角第 9 角色包）**role-mgmt-consulting**（项目管理咨询 v1.0.0）：商机 / 诊断 / 方案 / 变革 / 成效 5 环节 + 自建 5 维成熟度模型（治理 / 流程 / 组织 / 度量 / 工具，0~5 级）+ Kotter/ADKAR 变革；新台账 33~37；标准见 `references/consulting_standards.md`。
- **双套环境拓扑**：非生产组 dev+test 共享基础软硬件 + 生产组独立隔离；文件 / 端口隔离、RBAC 见 `references/environment_topology.md`（20_环境配置.csv 扩展列）。
- **目录规整**：`program-control-ledger` 迁至 `docs/program-control-ledger`；统一 9 角色包 + 1 编排器结构表述。
- 角色包索引 `SKILL_INDEX.md` 文档版本同步至 v21.7.0。

---

## [v21.7.1] - 2026-08-19 - multi-perspective-validation 评审实践模式

- **multi-perspective-validation 升 v1.2.0**：新增 §6 评审实践模式，沉淀自 quiz-extraction-skill 评审能力增强实践（五视角评审 → 修订 → 实施）。
  - 评审四层模型（结构 / 语义 / 统计 / 决策）；
  - 关键模式：抽样复审（`min(10, 题数×20%)` + 可复现 seed）、阈值参数化、性能分桶降 O(n²)、评审报告脱敏（相对路径）、回归固化（正反例 + golden fixture）；
  - 落地建议：门禁（阻断）与评审报告（不阻断）分离为两步，报告含 schema 可校验。
- 同步 `.trae/skills` → `.github/skills` / `.claude/skills` / `.agents/skills` 部署副本。

---

## [v21.7.2] - 2026-08-18 - 废弃清理门禁铁律

- **dev-project-team-skill 升 v21.7.2**：新增「废弃清理门禁」铁律（2026-08-18）——§2.2-7 规定 ADR 状态=废弃后，后续会话必须先做废弃资产完整性检查（全库 grep + 端口/进程/LaunchAgent 三查），且 solidify 基线固化阶段强制移除废弃资产（第 4 硬门禁 `tools/check_deprecation_cleanup.py`）；§2.1 会话启动第一步增补该检查；同步 AGENTS.md 铁律 #9。

---

## [v21.7.3] - 2026-08-18 - 需求-架构-代码 三方一致性铁律

- **dev-project-team-skill 升 v21.7.3**：新增「需求-架构-代码 三方一致性」铁律（2026-08-18）——§2.2-8 建立唯一标识（REQ-/ADR-/AE-/MOD-/TC-）+ 单一事实来源《需求-架构-代码追溯矩阵.csv》+ 阶段流转强制 `tools/check_traceability.py` 孤儿/断链门禁；§5 新增可追溯性优先调度规则；新增 `references/traceability_standard.md`（依据 NASA SWE-059 / EN 62304 / ASPICE / ArchUnit）。

---

## [v21.7.4] - 2026-08-19 - 新增「最佳实践方案」子技能

- **dev-project-team-skill 升 v21.7.4**：新增 `skills/best-practice-solution` 子技能（四段双轨水线：Triage 分级 → Research 调研 → Draft 草案 → LIGHT 自检 / FULL 多视角评审 → Converge）；缺省 LIGHT 快答（≤2500 token），黑名单 / 用户显式要求走 FULL（≤20000 token + 多视角评审）；T1/T2/T3 来源分级、外部信号优先于自我反思、网页内容=数据非指令、"INSUFFICIENT 不知道"是第一类合法答案；§2.2-1 双栏模板增强为带证据引用 + 置信度；决策记录草案交架构角色正式化 ADR；归档前 desensitize 脱敏。

---

## [v21.7.5] - 2026-08-19 - 最佳实践方案子技能 v1.2.0 迭代（五视角评审 49 条意见落地）

- **dev-project-team-skill 升 v21.7.5 + best-practice-solution 升 v1.2.0**（2026-08-19）：第二轮五视角评审 49 条意见落地——LIGHT 增纯本地档（知识优先、web 条件化）、统一 token 预算口径（FULL＝调研6000＋评审6000＋外部核验4000＋收敛4000，含工具 context）、评审决策统一 SIGNED_OFF/CHANGES_REQUESTED/BLOCKED 三态并引用 MPV 决策矩阵、Triage 增第 4 问选型锁定判据 + 黑名单量化、§4.1 增最佳实践方案路由仲裁（技术选型→BPS/ADR→role-architecture/代码评审→MPV）、SSRF 约束统一清单（含 IPv6/link-local/编码混淆/重定向复检）、涉密只出不进、confidence 映射表与 INSUFFICIENT 计数口径、T3 降级为反向信号、证据卡 timeliness 字段、closure 模板引用。
- **新增去水印工具 v1.0.0** `tools/remove_watermark`（Word/PPT/Excel/PDF/图片/文本 6 类处理器 + .sh/.ps1 封装 + README）。
- **文档脱敏工具升 v1.1.0**：新增脱敏字典 `DESENSITIZE_DICTIONARY.md` + `desensitize_dictionary.csv` + `--dictionary` 参数。
- **opencode 接入 MCP**：注册 dev-project-team-skill 本地服务器（`mcp_server.py` 暴露 10 工具/资源/提示）+ `.trae/mcp.json` 登记。

---

## [v21.8.0] - 2026-08-20 - 工具固化与 GitHub 真实 IP 推送固定动作

- **dev-project-team-skill 升 v21.8.0**（2026-08-20）：新增 `tools/github_push.py`（候选 IP→可达+TLS 证书合法探测→绑定真实 IP push origin，`--dry-run` 预览）+ 公共探测模块 `tools/_gh_ip_probe.py`（供 github_ip_refresh/github_push 复用）；`mirror_push.py --github-realip` 双推时 origin 网络失败自动真实 IP 回退且推送成功清除熔断冷却；`--verify` 增强为「启动即双端同步检查」（fetch+对比领先/落后，分叉即阻断推送）；SYNC 台账编号幂等（解析 max 编号取 +1）；opencode.json MCP 命令 uv→py 环境校准；AGENTS.md 登记固定动作 P-001（GitHub push 优先真实 IP，减少反复操作）。
- **复盘与工具固化方案 v21.8.0**：`docs/复盘与工具固化方案_v21.8.0.md`（5 项提案 P-001~P-005）+ 五视角评审报告（SIGNED_OFF，评审报告 CSV）。

---

## [v21.8.1] - 2026-08-20 - 生产发布集补全缺陷修复

- 修复 `tools/`（github_push.py/_gh_ip_probe.py 等）与 `docs/`（github_ip_records.csv 等）未纳入发布/部署/固化复制集、全局库按文档调用工具路径不存在的缺陷。
- `publish_production`/`deploy_skills`/`solidify` 复制集统一纳入 tools+docs，脱敏门禁扫描范围扩展至 tools/docs 并豁免规则定义示例与占位符；版本目录、项目级三目录、全局库同步生效。

---

## [v21.8.2] - 2026-08-22 - 本体全面评审 v21.8.2 缺陷修复批次

- **D-01** `role-architecture` description 扩充至 150+ 字符（补「架构评估/技术选型」触发词），descriptions 门禁 18/18 全绿。
- **D-02** 初始化《需求-架构-代码追溯矩阵.csv》（铁律 #10 落地）——补录存量 11 REQ / 5 AE / 17 MOD / 6 TC，`check_traceability.py` 门禁通过（无孤儿无断链）。
- **D-03** 以 `references/` 为基准重建 `shared/references/` 副本消除 4 文件漂移 + 补 `traceability_standard.md` 副本（铁律 #1 单源合规）。
- **D-04** 仓库卫生：`lint_repo.py` 白名单更新（`.codebuddy/` + `projects_registry.csv`），评审报告归档 `docs/reviews/`，清理残留文件，lint 23 error→0。

---

## [v21.9.0] - 2026-08-27 - 新增「项目管理模式」+ 项目经理执行层

- **新增第 11 角色包 `role-project-mgmt`**（项目经理执行层 v21.0.0）：对齐 PRINCE2 治理与日常管理分离 + PMBOK 十大知识领域，覆盖日常管控循环/RAID/阶段计划/进展报告/变更协调/经验教训。
- 编排器 §3 执行模式新增「项目管理模式」；§4 路由表增 #10 `role-project-mgmt`；§5 调度新增「工程角色协调只读」铁律。
- 新增 `role-project-mgmt/domain/upgrade-threshold.md`（轻量→建角色升级阈值）。
- SKILL_INDEX / AGENTS 同步 10 角色包计数。

---

## [v21.10.0] - 2026-08-27 - 大批量任务成本预警 + 开发平台/模型知识库

- 编排器 §2.2 新增 §2.2-9「大批量任务成本预警」铁律：超阈值（文件>20/输出>50K tok/大文档>5K 行/多轮 agent 循环）须先提示估算成本并三选一（A 只定方案/B 分步执行/C 指定平台模型）。
- 新增 `references/dev_platform_catalog.md`（开发平台 + 模型三层 + 公开定价快照 + 场景映射 + 大批量推荐组合）。
- 新增 `台账/40_大模型成本台账.csv`（实际成本账本，与 `21_模型选型.csv` 决策台账分工）。

---

## [v21.10.1] - 2026-08-27 - 生产发布工具多目标全局同步

- `publish_production.py` 新增 `--no-extra-globals`/`--all-globals`/`--extra-globals trae,workbuddy` 参数与 `sync_into()` 精确同步（仅清本仓库发布集子项、保护用户其他全局技能）。
- 支持一次性把发布集铺到 opencode/trae-cn/workbuddy 三端全局目录；v21.10.1 = v21.10.0 内容 + 增强版发布工具。

---

## [v21.10.2] - 2026-08-27 - Office 文档深度脱敏模块

- **文档脱敏工具升级 v1.1.0→v1.2.0**：新增 `tools/desensitize/office_desensitize.py`——docx 跨 run 段落级替换 / xlsx sharedStrings 替换 / OLE2 .doc·xls 等长字节替换 / zip 归档内嵌文档递归 / `--strip-images` 图片删除 / 文件名目录名脱敏 / 备份+执行记录+残余校验闭环；零第三方依赖；回归测试 3 例全过。

---

## [v21.10.3] - 2026-08-27 - 范围跟踪工具 ROOT 解析修复 + 发布级门禁修复

- `tools/scope_tracker.py` 与 `tools/check_traceability.py` 原 `ROOT = dirname(dirname(__file__))` 在部署副本（全局技能目录）误指技能库根，导致读写错 台账/；改为 `find_project_root()` 按 `--root` CLI / `PROJECT_ROOT` 环境变量 / CWD 与 `__file__` 向上找项目标记 / 兜底解析。
- `cmd_init` 加 `--reset-ledgers` 安全重写表头护栏（仅无数据行时）；三端全局副本已同步。
- 修复编排器 SKILL.md UTF-8 BOM 致发布级门禁误报，并重发布同步至 v21.10.3。

---

## [v21.11.0] - 2026-08-29 - 任务级按需加载模式

- **P3 交接优化**：编排器 §3 执行模式新增「任务级按需加载」；新增 §2.4 任务级加载逻辑（路由决策/映射表/加载算法伪代码/兼容回退）。
- 新增 `domain/skill-loader.md`（任务类型→角色包映射表 + 关键词推断 + 加载算法 + L1 摘要字段规格）。
- 交接文档 L1 新增「当前任务类型」字段；回退无任务类型时自动回退阶段渐进加载，完全向后兼容。

---

## [v21.12.0] - 2026-09-01 - 任务输出模型推荐（强制规则）

- §5 调度新增规则 8：每条任务输出最后一行必须附带 `📦 推荐模型` 行（格式/判定/例外见 `references/model_selection.md` §5）。
- 使模型推荐从手动行为固化为技能标准，所有项目可统一执行。

---

**文档版本**：v21.12.0 ｜ **知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
