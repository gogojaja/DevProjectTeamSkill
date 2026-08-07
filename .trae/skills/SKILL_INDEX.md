# SKILL_INDEX — 角色包索引清单

> 技能库根只读入口：**工具/编排器据此选择角色包**，每包一行。
> 子技能明细由各角色包根 SKILL.md 路由表承载，本索引不重复。
> 规范详见 `references/token_standard.md` §1。

| # | 角色包 | 域 | 触发词 | 加载路径 |
|---|--------|-----|--------|----------|
| 0 | dev-project-team-skill | 编排器 | 全生命周期 / 角色组合加载 / 切换角色 / 技能维护 | dev-project-team-skill/ |
| 1 | role-project-init | 项目启动 | 启动项目 / 立项 / 章程 / 干系人 / 基线初始化 | role-project-init/ |
| 2 | role-requirements-analysis | 需求 | 收集需求 / 分析需求 / 编写 SRS / 需求变更 / 需求追溯 | role-requirements-analysis/ |
| 3 | role-architecture | 架构 | 架构策略 / 架构设计 / 数据安全 / ADR / 架构评审 | role-architecture/ |
| 4 | role-development | 开发 | 开发策略 / 编码 / 代码走查 / 单元测试 / 联调 / 质量收口 | role-development/ |
| 5 | role-testing | 测试 | 测试策略 / 测试计划 / 用例设计 / 测试执行 / 缺陷管理 / 测试总结 | role-testing/ |
| 6 | role-deployment | 投产 | 投产策略 / 投产计划 / Go-Live / 发布执行 / 回滚 / 运维交接 | role-deployment/ |
| 7 | role-governance | 总控保障 | 台账读写 / 阶段评审 / 门禁 / 基线固化 / 变更审计 / 归档 / 交接 | role-governance/ |

## 使用规则

1. **编排器**加载时读取本索引，按用户触发词选择角色包；
2. **阶段裁剪**：项目启动阶段依据项目特点裁剪阶段/活动（`init_tailor`，产出 00_阶段配置.csv），编排器仅加载保留阶段角色包；第 0 阶段与总控保障强制保留；
3. **敏捷迭代**：`init_tailor` 额外产出 18_迭代配置.csv（容量/技术债/DoR/DoD/发布点），迭代循环 + 发布级强门禁（`release_gate`），新增 `iterate_backlog`/`iteration_review` action；
4. **技能维护**：新建/修改 SKILL.md 走 role-governance 的 `skill-authoring` 路由（`../shared/authoring.md` 五步流程），非执行项目业务；
5. **增强能力（v21.3.0）**：每阶段开始 `select_model`（21_模型选型）；阶段末 `retrospect_harvest`（22_阶段复盘 + 23_复用资产）；环境准备 `record_env_config`（20_环境配置）；标准见 `references/model_selection.md` 与 `references/environment_standard.md`；
6. **铁律锚点**：压缩/新会话后重读 `references/iron_rules.md`，每轮回显锚点 `授权→备份→留痕`；
7. **授权登记/时效**：系统/外部文件授权经 `register_auth` 登记 `14_授权登记.csv`（含有效期），每阶段末检查并提醒续期/撤销；
8. 单角色任务直接加载对应包；多角色/全生命周期由编排器调度；
9. 各包辅助能力统一指向 `shared/`（源码单源），打包产物内嵌副本。

---

**文档版本**：v21.3.3
**最后更新**：2026-08-07（编排器新增双平台兼容强制约束 §2.2-5；token_standard §6 双平台规则；iron_rules §6 平台兼容铁律）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
