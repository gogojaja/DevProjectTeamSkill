# SKILL_INDEX — 角色包索引清单

> 技能库根只读入口：**工具/编排器据此选择角色包**，每包一行。
> 子技能明细由各角色包根 SKILL.md 路由表承载，本索引不重复。
> 规范详见 `references/token_standard.md` §1。

| # | 角色包 | 域 | 触发词 | 加载路径 |
|---|--------|-----|--------|----------|
| 0 | dev-project-team-skill | 编排器 | 全生命周期 / 多角色联合 / 切换角色 | dev-project-team-skill/ |
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
3. 单角色任务直接加载对应包；多角色/全生命周期由编排器调度；
4. 各包辅助能力统一指向 `shared/`（源码单源），打包产物内嵌副本。

---

**文档版本**：v21.0.1
**最后更新**：2026-08-06
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
