# SKILL_INDEX — 角色包索引清单

> 技能库根只读入口：**工具/编排器据此选择角色包**，每包一行。
> 子技能明细由各角色包根 SKILL.md 路由表承载，本索引不重复。
> 规范详见 `references/token_standard.md` §1。
> **弱模型适配**：能力弱模型下技能识别与执行规范见 `references/weak_model_compatibility.md`（description 单语言/触发词前置）。
> **目录访问边界**：本项目可读写/删除范围=本项目目录（`台账/26_访问边界.csv`），本项目目录外访问须经 `register_auth` 授权（默认仅本次对话），见 `references/iron_rules.md` §1a。

| # | 角色包 | 域 | 触发词 | 加载路径 |
|---|--------|-----|--------|----------|
| 0 | dev-project-team-skill | 编排器 | 全生命周期 / 角色组合加载 / 切换角色 / 技能维护 | dev-project-team-skill/ |
| 1 | role-project-init | 项目启动 | 启动项目 / 立项 / 章程 / 干系人 / 组织架构 / RACI / 问题升级 / 基线初始化 | role-project-init/ |
| 2 | role-requirements-analysis | 需求 | 收集需求 / 分析需求 / 编写 SRS / 需求变更 / 需求追溯 | role-requirements-analysis/ |
| 3 | role-architecture | 架构 | 架构策略 / 架构设计 / 数据安全 / ADR / 架构评审 | role-architecture/ |
| 4 | role-development | 开发 | 开发策略 / 编码 / 代码走查 / 单元测试 / 联调 / 质量收口 | role-development/ |
| 5 | role-testing | 测试 | 测试策略 / 测试计划 / 用例设计 / 测试执行 / 缺陷管理 / 测试总结 | role-testing/ |
| 6 | role-deployment | 投产 | 投产策略 / 投产计划 / Go-Live / 发布执行 / 回滚 / 运维交接 | role-deployment/ |
| 7 | role-governance | 总控保障 | 台账读写 / 阶段评审 / 门禁 / 基线固化 / 变更审计 / 归档 / 交接 | role-governance/ |
| 8 | role-program-mgmt | 项目群/项目集 | 项目群 / 项目集 / 多项目协同 / PMO / 依赖 / 里程碑对齐 / 收益 / IMS | role-program-mgmt/ |

## 使用规则

1. **编排器**加载时读取本索引，按用户触发词选择角色包；
2. **阶段裁剪**：项目启动阶段依据项目特点裁剪阶段/活动（`init_tailor`，产出 00_阶段配置.csv），编排器仅加载保留阶段角色包；第 0 阶段与总控保障强制保留；
3. **敏捷迭代**：`init_tailor` 额外产出 18_迭代配置.csv（容量/技术债/DoR/DoD/发布点），迭代循环 + 发布级强门禁（`release_gate`），新增 `iterate_backlog`/`iteration_review` action；
4. **技能维护**：新建/修改 SKILL.md 走 role-governance 的 `skill-authoring` 路由（`../shared/authoring.md` 六步流程，非执行项目业务）；产物目录强制对准该文件 §3（最终产出物落 `.trae/skills/<包名>/`，打包/临时物归 `dist/`、`backup/tmp_migrations/`、`_pkg_tmp/`）；
   - **硬门禁**：维护产出的每个技能必须具备 `闭环执行系统` 标题与模板，包含任务入口、执行状态、验收门禁、失败处理、产出与交接、审计记录，且必须通过 `tools/check_skill_closure.py`、`tools/check_skill_release_gate.py` 与 `tools/check_version_consistency.py`；不得仅停留在描述型流程；
   - **维护 SOP**：详细执行流程与统一模板见 `../shared/skill_maintenance_sop.md`；
   - **维护章程**：最终规则/门禁/交接要求见 `../shared/skill_maintenance_charter.md`；
5. **增强能力（v21.3.0）**：每阶段开始 `select_model`（21_模型选型）；阶段末 `retrospect_harvest`（22_阶段复盘 + 23_复用资产）；环境准备 `record_env_config`（20_环境配置）；标准见 `references/model_selection.md` 与 `references/environment_standard.md`；
6. **铁律锚点**：压缩/新会话后重读 `references/iron_rules.md`，每轮回显锚点 `授权→备份→留痕`；§3 敏感信息分级处理（A 禁止入库/B 脱敏入库/C 正常入库），B 级脱敏提交前强制；
7. **授权登记/时效**：系统/外部文件授权经 `register_auth` 登记 `14_授权登记.csv`（含有效期），每阶段末检查并提醒续期/撤销；
8. 单角色任务直接加载对应包；多角色/全生命周期由编排器调度；
9. 各包辅助能力统一指向 `shared/`（源码单源），打包产物内嵌副本；
10. **GitHub 访问异常**：`github.com:443` 不可达时，加载 `references/github_access.md`（候选 IP 池 / 连通性验证 / push 带凭据）；
11. **嵌套能力（v21.4.0）**：编排器内嵌 `team-orchestration`（并行编排）与 `multi-perspective-validation`（多视角验证），模型档位 S0~S3 + 免费体系（对齐 `references/model_selection.md` §4）；**多角色并行方案冲突按 `team-orchestration/domain/priority-arbitration.md` 仲裁**（P0~P6 优先级：需求基线/总控→安全→架构→测试→开发→部署→文档，一票否决制，仲裁留痕，见 team-orchestration v1.1.0）；
12. **多项目隔离**：多项目并行开发时，参考 `references/multi_project_isolation.md`（Git/运行时/数据库/Docker 四层隔离架构 + **第 5 层全局环境资产注册与冲突仲裁**：`register_env_asset` 通过 `tools/cmdb/cmdb-cli.py` 登记 CMDB 数据库，独占资源（大模型容器/GPU/Docker 单一运行时/端口）先注册先得，冲突升阶 `change_audit` 留痕；本地工具/脚本运行目标缺省为本地轻量模型档，见 `references/model_selection.md` §7.1）。

13. **CMDB 工具**：多项目共享服务器资源管理工具，参考 `tools/cmdb/README.md`（注册/查询/释放/冲突检测；SQLite 数据库；审计日志；CSV 导出）。

14. **启动治理（v21.5.9）**：启动阶段须完成组织架构与责任分配（`define_org_structure`，`27_组织架构.csv` RACI 矩阵）与问题解决与升级机制（`define_issue_escalation`，`12_风险问题台账.csv` 升级字段 P1~P4 分级 + 四级升级阶梯 + 单一 Owner）；`check_ready` 硬门禁（未明确不得 Go），详见 `role-project-init/SKILL.md`。

15. **项目群协同（v1.1.0）**：多项目协同层由 `role-program-mgmt` 承载（对齐 PMI SPM 5th 八原则/五绩效域、MSP 5th 七原则/转型流、IMS/EVM）；8 环节 `define_program`/`manage_benefits`/`map_dependencies`/`align_schedule`/`standardize_execution`/`manage_documents`/`review_program`/`close_program`；治理三层模型（项目治理<项目群治理<组合治理），Program Board 在 tranche 边界决策（继续/转向/终止），Program Manager 管理不决策、PMO 提供机制不决策；新台账 28_项目群注册/29_项目依赖矩阵/30_项目群主进度/**31_文档配置管理**；**v1.1.0 新增文档与配置管理 discipline**（单一信息源/命名规范/版本生命周期/CI 基线/密级/留存，对齐 ISO 15489/ISO 10007）；与项目级 check_ready/stage_review 叠加为双层门禁，不替代单项目治理，详见 `role-program-mgmt/SKILL.md` 与 `references/program_management.md`。

---

**文档版本**：v21.6.1
**最后更新**：2026-08-17（role-program-mgmt 优化至 v1.1.0：对齐 PMI SPM 5th/MSP 5th，新增文档与配置管理 discipline 与 manage_documents action、31_文档配置管理.csv；依赖矩阵增强度/缓解措施、主进度增健康度/更新日期）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
