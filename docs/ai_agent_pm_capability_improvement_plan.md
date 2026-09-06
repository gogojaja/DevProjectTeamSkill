# AI Agent 项目管理/PMO 能力提升实施方案

> **版本**：v1.0.0 | **日期**：2026-09-07 | **状态**：待评审
> **前置依赖**：dev-project-mgmt（AUTH-022，本地已就绪，远端仓库待建）

---

## 一、背景与动机

### 1.1 现状诊断

| 层级 | 能力 | 方法论（角色包） | 工具（dev-project-mgmt） | MCP 暴露（AI Agent） |
|------|------|:---:|:---:|:---:|
| RAID 管理 | role-project-mgmt §3 | ✅ raid_manager.py | ❌ |
| EVM 挣值 | role-governance update_milestone | ✅ evm_calculator.py | ❌ |
| 进展报告 | role-project-mgmt §4 | ✅ report_generator.py | ⚠️ 仅 skill_progress |
| 变更协调 | role-project-mgmt §5 | ✅ change_coordinator.py | ❌ |
| 项目群视图 | role-program-mgmt §5/§6 | ⚠️ sync_program_progress.py | ❌ |
| 范围跟踪 | role-requirements-analysis | ✅ scope_tracker.py | ✅ scope_metrics |

**核心问题**：方法论强（5/5）、工具有基础（4/5）、MCP 暴露严重不足（2/5）。
AI Agent 知道「怎么做」也有「工具可用」，但缺少「操作接口」。

### 1.2 目标

- **P0**：RAID + EVM 经 MCP 可直接操作（AI Agent 可管理风险、评估项目健康度）
- **P1**：进展报告 + 项目群视图经 MCP 可查询（AI Agent 可生成报告、感知跨项目全貌）
- **P2**：变更协调 + PM Prompt 模板（AI Agent 可发起变更、标准化输出格式）
- **量化**：MCP Tools 15→21（+6），Prompts 6→9（+3），项目管理能力覆盖率 2/5→4.5/5

---

## 二、技术方案

### 2.1 架构设计

```
┌─────────────────────────────────────────────────────┐
│  MCP Server (skills_mcp_server.py)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │raid_mgmt │ │evm_analyze│ │progress_ │ │program │ │
│  │(新增)    │ │(新增)    │ │report    │ │_status │ │
│  │          │ │          │ │(新增)    │ │(新增)  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
│       │            │            │            │      │
│  ┌────▼────────────▼────────────▼────────────▼────┐ │
│  │  project_mgmt_proxy.py（新增·薄封装代理）       │ │
│  │  PROJECT_ROOT 注入 + CLI 子命令路由             │ │
│  └────────────────────┬───────────────────────────┘ │
└───────────────────────┼─────────────────────────────┘
                        │ subprocess
┌───────────────────────▼─────────────────────────────┐
│  dev-project-mgmt CLI (d:\Myprojects\dev-project-mgmt) │
│  cli.py → raid/report/change/evm 四子命令           │
│  + boundary_validator.py 访问边界校验                │
└─────────────────────────────────────────────────────┘
```

**设计原则**：
- 与 scheduler_proxy.py / model_router_proxy.py 一致的薄封装代理模式
- 三级路径解析：`$DEV_PROJECT_MGMT_ROOT` > 同级目录 `../dev-project-mgmt` > 配置兜底
- 所有写操作默认 `dry_run=True`（MCP 安全约束）
- `--format json` 结构化输出，便于 MCP 解析

### 2.2 新增 MCP Tools（6 个）

| # | Tool 名称 | 包装 CLI | 风险级 | 说明 |
|---|-----------|---------|--------|------|
| 1 | `raid_mgmt` | `cli.py raid list/add/update/close` | Tier2 | RAID 四维台账 CRUD |
| 2 | `evm_analyze` | `cli.py evm calc/status/add-milestone` | Tier2 | EVM 挣值分析 |
| 3 | `progress_report` | `cli.py report weekly/phase` | Tier1 | 进展报告生成 |
| 4 | `change_mgmt` | `cli.py change list/register/analyze/approve/reject` | Tier2 | 变更协调 |
| 5 | `program_status` | 读 `台账/28_29_30*.csv` | Tier1 | 项目群整体视图 |
| 6 | `program_dependency` | 读 `台账/29_项目依赖矩阵.csv` | Tier1 | 跨项目依赖查询 |

### 2.3 新增 MCP Prompts（3 个）

| # | Prompt 名称 | 说明 |
|---|-------------|------|
| 1 | `project_status_report` | 引导生成进展报告（聚合 RAID+EVM+进度） |
| 2 | `risk_assessment` | 引导 RAID 分析与风险预警 |
| 3 | `program_review` | 引导 Program Board 评审（四 Gate） |

### 2.4 新增代理脚本

**`tools/project_mgmt_proxy.py`**（~200 行）：
- 路径解析：`$DEV_PROJECT_MGMT_ROOT` > `../dev-project-mgmt` > `~/dev-project-mgmt`
- 子命令路由：`raid` / `evm` / `report` / `change`
- 安全约束：写操作强制 `--dry-run` 默认 + `PROJECT_ROOT` 注入
- 输出截断：stdout 限 4000 字符（防 MCP 响应过大）

### 2.5 项目群视图（直接读台账）

`program_status` 和 `program_dependency` 不包装 dev-project-mgmt CLI，而是直接读取本仓库 `台账/28_29_30*.csv`（项目群数据在本仓库，不在 dev-project-mgmt）。

---

## 三、WBS 执行计划

| 阶段 | 任务 | 预估 | 验收标准 |
|------|------|------|----------|
| **S1 代理层** | ① 创建 `project_mgmt_proxy.py` | 1h | 路径解析正确 + 4 子命令路由通过 + `--help` 可用 |
| **S2 MCP 扩充** | ② 新增 6 个 MCP Tools | 1.5h | `@mcp.tool()` 计数 ≥21 |
|  | ③ 新增 3 个 MCP Prompts | 0.5h | `@mcp.prompt()` 计数 ≥9 |
| **S3 门禁更新** | ④ `check_mcp_server.py` 阈值 15→21 | 0.5h | 门禁通过 |
| **S4 测试** | ⑤ 单元测试（≥15 用例） | 1h | pytest 全通过 |
|  | ⑥ 固化 + 交接刷新 | 0.5h | solidify 门禁全通过 |
| **合计** | 6 任务 | **5h** | |

---

## 四、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| dev-project-mgmt CLI 接口变更 | 低 | 高 | 代理层做接口适配，不直接依赖内部 API |
| 项目群台账路径漂移 | 低 | 中 | 使用 ROOT 动态解析，不硬编码 |
| EVM SQLite 数据库不存在 | 中 | 中 | 首次调用自动 `init_evm_tables`，优雅降级 |
| MCP 响应过大 | 低 | 低 | stdout 截断 4000 字符 |

---

## 五、验收标准

1. **MCP Tools 数量** ≥ 21（当前 15 + 新增 6）
2. **MCP Prompts 数量** ≥ 9（当前 6 + 新增 3）
3. **代理脚本可用**：`python tools/project_mgmt_proxy.py --help` 正常输出
4. **RAID 端到端**：经 MCP `raid_mgmt(action="list")` 可读台账
5. **EVM 端到端**：经 MCP `evm_analyze(action="status")` 可查状态
6. **进展报告**：经 MCP `progress_report(type="weekly")` 可生成周报
7. **项目群视图**：经 MCP `program_status()` 可读 28/29/30 台账
8. **单元测试** ≥ 15 用例全通过
9. **solidify 门禁**全通过

---

## 六、交付物清单

| # | 交付物 | 路径 | 说明 |
|---|--------|------|------|
| 1 | 本方案 | `docs/ai_agent_pm_capability_improvement_plan.md` | 方案文档 |
| 2 | 评审报告 | `docs/reviews/评审报告_AI_Agent_PM能力提升_v1.0_五维评审.csv` | 五维评审 |
| 3 | 代理脚本 | `tools/project_mgmt_proxy.py` | 薄封装代理（~200 行） |
| 4 | MCP Server 扩充 | `tools/mcp_server/skills_mcp_server.py` | +6 Tools +3 Prompts |
| 5 | 门禁更新 | `tools/check_mcp_server.py` | 阈值 15→21 |
| 6 | 单元测试 | `tools/tests/test_pm_mcp_expansion.py` | ≥15 用例 |
