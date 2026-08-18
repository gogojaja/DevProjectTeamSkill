# CHANGELOG — DevProjectTeamSkill 版本演进史

> 版本基于各角色包 SKILL.md 版本号与 SKILL_INDEX.md 末尾推断整理。
> 编排器文档版本：v21.7.0（2026-08-18）。

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

**文档版本**：v21.7.0 ｜ **知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
