# 立项建议书：dev-task-scheduler 定时任务管理工具

> **孵化器编号**：INC-2026-08-31-001
> **决策对象**：定时任务管理工具——独立项目 vs 内嵌实现
> **档位**：LIGHT（本地证据 + web 核验，1 次 webfetch）
> **评审模式**：多视角自评（3 视角：架构/安全/成本+演进）
> **评审结果**：🟢 SIGNED_OFF（3/3 全绿）
> **技能版本**：incubator-initiation v1.0.0 + best-practice-solution v1.2.1

---

## 一、方案调研

### 1.1 现有资产盘点

| 资产 | 说明 | 行数 |
|------|------|------|
| `tools/scheduler/` | APScheduler 封装调度引擎（14 文件） | 3,477 |
| `.secrets/scheduler.db` | SQLite 持久化（4 表：jobs/job_executions/idempotency_keys/scheduler_state） | — |
| `nightly_quality_gate.py` | 夜间质量门禁编排器（跨项目执行） | — |
| `projects_registry.csv` | 项目注册表（project_alias/project_path/test_cmd） | — |

### 1.2 行业最佳实践

| 来源 | 结论 | confidence |
|------|------|------------|
| APScheduler PyPI（T1 webfetch 核验） | 3.11.3（最新稳定版），MIT License，Production/Stable，Python >=3.8 | high |
| 行业共识（T2 recalled） | 单机轻量场景 APScheduler 足够；重负载/分布式需 Celery Beat/Airflow | medium |
| dev-git-hub 先例（T2 recalled） | 三判据全命中 → 独立化；剥离成本低（1 天完成） | medium |

### 1.3 证据卡

| 证据卡 | claim | 来源 | confidence |
|--------|-------|------|------------|
| EV-901 | APScheduler 是 Python 生态最成熟调度库 | T1 recalled + webfetch 核验 | high |
| EV-902 | 跨项目调度推荐独立部署避免耦合 | T2 recalled | medium |
| EV-903 | 本仓库已有 3,477 行完整调度引擎 | 本库实测 T1 | high |
| EV-904 | 三判据全命中 + dev-git-hub 先例 | 孵化器方案 T2 | medium |
| EV-905 | APScheduler 3.11.3 已验证 | T1 webfetch 核验 | high |

---

## 二、可行性评估

### 2.1 三判据独立化评估

| 判据 | 评估 | 判定 |
|------|------|------|
| **复用率** | 用户明确"对各个项目"管理 → 跨项目复用 | ✅ 独立化 |
| **独立性** | 14 文件自包含，不引用 `.trae/skills` 或 `台账/` | ✅ 独立化 |
| **维护成本** | 3,477 行内嵌膨胀技能库，独立后自管理 | ✅ 独立化 |

**结论**：三判据全部命中 → **建议独立化**

### 2.2 可行性五维

| 维度 | 评估 | 档位 |
|------|------|------|
| 技术可行性 | APScheduler 成熟 + 已有实现 | 高 |
| 经济可行性 | 开源免费，开发成本≈0（已有实现） | 高 |
| 合规可行性 | MIT License，无敏感数据 | 高 |
| 资源可行性 | 单人可维护，已有数据可平滑迁移 | 高 |
| 时间可行性 | 剥离+独立化 1-2 天（参照 dev-git-hub 先例） | 高 |

**结论**：五维全高 → **可行性极高**

---

## 三、方案双栏

### ✅ 可稳定达成效果

**方案 A（推荐）：独立为 `dev-task-scheduler` 项目**
- 迁移 `tools/scheduler/` → 独立仓库
- 本仓库保留薄封装代理 + projects_registry.csv 引用
- 跨项目定时任务管理：CLI 注册 → 统一调度 → 结果回写各项目
- 证据：EV-903[high]（已有完整实现）、EV-904[medium]（三判据全命中 + dev-git-hub 先例）

**技术架构**：
- 调度引擎：APScheduler 3.11.3（MIT License）
- 持久化：SQLite（可扩展 SQLAlchemy/Redis）
- CLI 接口：`dev-task-scheduler add/list/remove/run/status`
- 跨项目注册：各项目经 `PROJECT_ROOT` 注入注册任务
- 告警通知：系统通知 + 可选 webhook
- 幂等控制：idempotency_key 防重复执行

### ⚠️ 理论最优效果与当前限制

**方案 B：维持内嵌**
- 限制：3,477 行非核心代码膨胀技能库
- 反信号：用户跨项目需求不满足

**方案 C：cron/LaunchAgent 替代**
- 限制：无执行记录/幂等/重试/告警；跨项目无统一视图
- 反信号：轻量场景足够，但用户要"管理各个项目的定时任务"

---

## 四、评审报告

### 多视角评审（串行）

| 视角 | 对照证据 | 结论 |
|------|----------|------|
| 架构/技术路线 | APScheduler 成熟（T1 webfetch 核验）+ 已有实现（T1 本库实测） | ✅ SIGNED_OFF |
| 安全合规 | MIT License + 无敏感数据 + 幂等/重试/超时控制 | ✅ SIGNED_OFF |
| 成本+演进 | 开发成本≈0 + SQLite 免费 + APScheduler 4.0 渐进升级 | ✅ SIGNED_OFF |

**聚合决策**：🟢 **SIGNED_OFF**（3/3 全绿）

### 未关闭风险

| 风险 | 严重度 | 处理 |
|------|--------|------|
| 独立后远端操作依赖 | 中 | 薄封装兜底（不阻断） |
| APScheduler 4.0 迁移 | 低 | 渐进升级，非阻断 |

---

## 五、决策记录草案

- **标识**：ADR-2026-08-31-001
- **决策**：将 `tools/scheduler/` 独立为 `dev-task-scheduler` 项目，本仓库保留薄封装代理
- **选项**：
  - A. **独立为 dev-task-scheduler（本方案）** → ✅ 三判据全命中
  - B. 维持内嵌 → ❌ 3,477 行非核心代码膨胀
  - C. cron/LaunchAgent 替代 → ❌ 无统一视图
- **理由**：EV-901~905
- **已验证**：APScheduler 3.11.3 PyPI 核验、本仓库 scheduler.db 实测
- **不确定**：APScheduler 4.0 迁移时间
- **未关闭风险**：独立后远端操作依赖（薄封装兜底）
- **反信号**：独立后无人维护 → 回收至本库

---

## 六、移交清单

| 项目 | 说明 | 路径 |
|------|------|------|
| 本方案文档 | 立项建议书 | `docs/incubator/INC-2026-08-31-001_dev-task-scheduler.md` |
| 证据卡 | EV-901~905 | `docs/evidence_cards_dev-task-scheduler_20260831.json` |
| 现有实现 | APScheduler 封装引擎 | `tools/scheduler/`（14 文件，3,477 行） |
| 现有数据 | SQLite 持久化 | `.secrets/scheduler.db`（4 表） |
| ADR 草案 | 决策记录 | `docs/adr/ADR-2026-08-31-001_dev-task-scheduler.md` |

---

**最后更新**：2026-08-31（孵化器立项）
**孵化器**：incubator-initiation v1.0.0
**评审签署**：🟢 SIGNED_OFF（3/3 视角全绿）
