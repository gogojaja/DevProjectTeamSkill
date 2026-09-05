# 项目注册表（P2）

> **定位**：本项目所有关联独立项目的单一注册中心（路径/授权/用途/维护边界）——确保跨项目协同有据可查、不遗漏、不越界。
> **原则**：只登记，不实现；登记即授权（需 `台账/14_授权登记.csv` 同步）；变更必留痕（`台账/13_安全审计台账.csv`）。

---

## 当前登记项目

| 项目名 | 路径 | 授权编号 | 用途 | 维护边界 | 状态 |
|--------|------|----------|------|----------|------|
| **dev-git-hub** | `$DEV_GIT_HUB_ROOT` 或同级目录 `../dev-git-hub` | `AUTH-014` | 局域网 Git 基建（LAN 中枢 + Windows 副本 + WAN 灾备 + git 复杂远端操作工具） | 仅经薄封装代理调用；本项目不维护其实现；改动只落其仓库 | ✅ 已移交 |
| **dev-task-scheduler** | `$DEV_TASK_SCHEDULER_ROOT` 或同级目录 `../dev-task-scheduler` | `AUTH-015` | 定时任务管理（跨项目调度引擎，基于 APScheduler） | 仅经薄封装代理调用；本项目不维护其实现；改动只落其仓库 | ✅ 已移交 |
| **dev-model-router** | `$DEV_MODEL_ROUTER_ROOT` 或同级目录 `../dev-model-router` | `AUTH-016` | 多模型分层编排（Router + DAG + Executor，高阶拆解→低阶执行→高阶组装） | 仅经薄封装代理调用；本项目不维护其实现；改动只落其仓库 | ✅ 已移交 |
| **dev-project-mgmt** | `$DEV_PROJECT_MGMT_ROOT` 或同级目录 `../dev-project-mgmt` | `AUTH-022` | 项目管理工具集（RAID/进展报告/变更协调/EVM；方法论在 role-project-mgmt 技能） | 仅经薄封装代理调用；本项目不维护其实现；改动只落其仓库 | ✅ 已移交 |
| **dev-security-tools** | `$DEV_SECURITY_TOOLS_ROOT` 或同级目录 `../dev-security-tools` | `AUTH-023` | 安全审计工具集（审计台账/脱敏扫描/边界检查/密钥检测；现有 audit.py、desensitize 保留本库不迁移） | 仅经薄封装代理调用；本项目不维护其实现；改动只落其仓库 | ✅ 已移交 |
| **dev-test-tools** | `$DEV_TEST_TOOLS_ROOT` 或同级目录 `../dev-test-tools` | `AUTH-024` | 测试工具集（跨项目测试执行/覆盖率聚合/缺陷台账/报告生成；方法论在 role-testing 技能） | 仅经薄封装代理调用；本项目不维护其实现；改动只落其仓库 | ✅ 已移交 |
| **free-api-hub** | `$FREE_API_HUB_ROOT` 或同级目录 `../free-api-hub` | — | 模型清单管理基础设施（模型清单/余额/费用/优惠；禁止路由/聚合/转发）；选型建议能力已转为本库 `model-selection` 技能 | 清理交接见 `docs/交接事项_free-api-hub功能边界清理_20260901.md` | ✅ 独立保留（边界清理已下发） |
| **TwinForge** | 同级目录 `../TwinForge` | — | 双机 AI 工作站（Mac mini M2 + Dell 7010）；本地部署架构与涉密信息管理 | **私有项目，对外不公开**；本项目不内嵌其实现细节；架构方案已迁至 TwinForge 仓库 `docs/` | 🔒 私有（项目群成员） |

---

## 登记规范

- **路径**：环境变量（如 `$DEV_GIT_HUB_ROOT`）或同级目录约定（`../<project>`）；也可写入 `.env` 文件
- **授权编号**：必须对应 `台账/14_授权登记.csv` 中有效条目
- **用途**：一句话说明职责边界（避免模糊描述）
- **维护边界**：明确本项目能否修改、如何调用、是否托管
- **状态**：✅ 已移交 / ⚠️ 待移交 / ❌ 已废弃 / 🔒 私有（项目群成员，对外不公开）

---

**最后更新**：2026-09-05（Phase 2：新增 TwinForge 私有项目登记；架构方案文档已迁至 TwinForge 仓库）