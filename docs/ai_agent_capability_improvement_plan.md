# AI Agent 功能提升实施方案

> **方案版本**：v1.0.0 **制定日期**：2026-09-06
> **制定依据**：plan-creation 子技能（IEEE 828 / PMBOK / PRINCE2 对齐）
> **触发来源**：用户指令「本项目的 AI agent 功能提升」
> **关联 ADR**：待分配（ADR-2026-09-06-001）

---

## 一、方案概述

### 1.1 背景与动机

DevProjectTeamSkill 已具备完整的技能结构（11 角色包 + 编排器）、多工具分发体系（7 工具全局库同步）和 MCP Server（7 Tools + 4 Resources + 2 Prompts）。但 AI Agent 在实际使用中存在以下短板：

1. **MCP 工具覆盖不全**：大量 CLI 能力（评审、复盘、范围跟踪、审计查询等）未通过 MCP 暴露
2. **客户端需手动注册**：每换机器/工具需手动配置 `mcpServers` 段
3. **Prompts 过于简单**：仅 `invoke_role` 和 `phase_gate` 两个基础模板
4. **无运行时进度反馈**：自主执行状态不透明

### 1.2 方案目标

| 目标 | 量化指标 | 优先级 |
|------|---------|--------|
| MCP 工具覆盖率 | 从 7 个扩充到 ≥15 个 | P0 |
| 客户端自动注册 | 支持 opencode/TRAE/Claude 三大工具自动注册 | P0 |
| Prompts 引导能力 | 从 2 个扩充到 ≥6 个，覆盖核心场景 | P1 |
| 运行时进度反馈 | 新增 `skill_progress` tool | P1 |

### 1.3 方案范围

**纳入范围**：
- MCP Server 工具扩充（新增 8 个 MCP Tools）
- Prompts 扩充（新增 4 个 MCP Prompts）
- 客户端自动注册机制（`register_mcp_client.py` 工具）
- 运行时进度反馈（`skill_progress` tool）

**排除范围**：
- 语义路由（P2，需 embedding 模型支持，暂不实施）
- 跨工具会话同步（P3，需共享状态存储，后续评估）

---

## 二、技术方案

### 2.1 MCP Server 工具扩充

**目标文件**：`tools/mcp_server/skills_mcp_server.py`（FastMCP 版本，唯一事实来源）

**新增工具清单**：

| # | 工具名 | 功能 | 包装脚本 | 安全级别 |
|---|--------|------|---------|---------|
| 1 | `skill_search` | 语义搜索技能文档 | 内嵌实现（关键词匹配） | Tier1 只读 |
| 2 | `skill_links` | 技能引用可达性检查 | `check_skill_links.py` | Tier1 只读 |
| 3 | `audit_query` | 审计台账查询（只读） | `audit.py --query` | Tier1 只读 |
| 4 | `scope_metrics` | 范围覆盖度指标 | `scope_tracker.py metrics` | Tier1 只读 |
| 5 | `retro_harvest` | 复盘收割 | `retro_cli.py` | Tier2 写（需确认） |
| 6 | `review_execute` | 评审执行 | `mpv_cli.py` | Tier2 写（需确认） |
| 7 | `nightly_gate` | 夜间质量门禁 | `nightly_quality_gate.py` | Tier2 写（需确认） |
| 8 | `skill_progress` | 运行时进度反馈 | 内嵌实现（读交接文档） | Tier1 只读 |

**安全约束**：
- Tier1（只读）：直接执行，无需确认
- Tier2（写）：默认 dry_run=True，正式执行需用户确认（对齐铁律 #15）

### 2.2 Prompts 扩充

**新增 Prompts 清单**：

| # | Prompt 名 | 功能 | 参数 |
|---|-----------|------|------|
| 1 | `architecture_design` | 引导架构设计全流程 | `project_name`, `domain` |
| 2 | `test_planning` | 引导测试计划编写 | `phase`, `risk_level` |
| 3 | `incubation_assess` | 引导孵化评估 | `candidate_name`, `type` |
| 4 | `retrospective` | 引导复盘收割 | `stage`, `object` |

### 2.3 客户端自动注册

**新增工具**：`tools/register_mcp_client.py`

**支持的工具矩阵**：

| 工具 | 配置文件路径 | 配置格式 |
|------|-------------|---------|
| opencode | `~/.config/opencode/opencode.jsonc` | JSONC `mcpServers` 段 |
| TRAE | `~/.trae/mcp.json` | JSON `mcpServers` 段 |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` | JSON `mcpServers` 段 |
| Cursor | `.cursor/mcp.json`（项目级） | JSON `mcpServers` 段 |

**注册逻辑**：
1. 检测目标工具是否已安装（父目录存在）
2. 读取现有配置文件（若存在）
3. 注入/更新 `mcpServers.dev-project-team-skill` 段
4. 备份原配置文件到 `.backup/`
5. 写入审计台账

**用法**：
```bash
python tools/register_mcp_client.py                    # 自动发现已安装工具并注册
python tools/register_mcp_client.py --tool opencode    # 仅注册 opencode
python tools/register_mcp_client.py --dry-run          # 仅探测不写入
```

### 2.4 运行时进度反馈

**新增 MCP Tool**：`skill_progress`

**功能**：读取 `交接文档.md` L1 核心摘要，返回当前任务状态、已完成步骤、下一步预期。

**实现**：
```python
@mcp.tool()
def skill_progress() -> str:
    """查询当前任务执行状态与进度。"""
    handoff = os.path.join(ROOT, "交接文档.md")
    # 解析 L1 核心摘要区
    # 返回：当前阶段/角色/任务 + 关键风险/阻塞 + 下一步动作
```

---

## 三、执行计划（WBS）

| 阶段 | 任务 | 产出 | 预计工时 |
|------|------|------|---------|
| **Phase 1** | MCP 工具扩充 | `skills_mcp_server.py` 更新 | 2h |
| 1.1 | 新增 8 个 MCP Tools | 代码 + 单元测试 | |
| 1.2 | 更新 `check_mcp_server.py` 门禁阈值 | 门禁脚本 | |
| **Phase 2** | Prompts 扩充 | `skills_mcp_server.py` 更新 | 1h |
| 2.1 | 新增 4 个 MCP Prompts | 代码 | |
| **Phase 3** | 客户端自动注册 | `register_mcp_client.py` | 2h |
| 3.1 | 实现注册逻辑 | 代码 + 测试 | |
| 3.2 | 集成到 `publish_production` | 发布流程更新 | |
| **Phase 4** | 固化验证 | 交接文档 + 审计台账 | 0.5h |
| 4.1 | 运行 solidify 固化 | 项目级三目录部署 | |
| 4.2 | 验证 MCP Server 启动与工具可达 | 测试报告 | |

**总计**：约 5.5h

---

## 四、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| MCP Server 依赖版本冲突 | 低 | 中 | 锁定 `mcp[cli]<2`，CI 验证 |
| 客户端配置文件格式变更 | 中 | 低 | 备份原文件 + 降级处理 |
| 新增工具引入回归 | 低 | 中 | 单元测试 + 门禁阈值提升 |
| 跨平台兼容性问题 | 低 | 中 | 优先 Python 实现，避免平台特定代码 |

---

## 五、验收标准

| 验收项 | 标准 |
|--------|------|
| MCP Tools 数量 | ≥15 个（当前 7 + 新增 8） |
| MCP Prompts 数量 | ≥6 个（当前 2 + 新增 4） |
| 客户端自动注册 | opencode/TRAE 至少 2 个工具可自动注册 |
| MCP Server 门禁 | `check_mcp_server.py` 通过（工具计数阈值 ≥15） |
| 单元测试 | 新增工具均有对应测试用例 |

---

## 六、交付物

1. **方案文档**：`docs/ai_agent_capability_improvement_plan.md`（本文件）
2. **执行计划**：本文 §三 WBS
3. **评审报告**：`docs/reviews/评审报告_AI_Agent功能提升_v1.0_*.csv`
4. **代码变更**：
   - `tools/mcp_server/skills_mcp_server.py`（工具+Prompts 扩充）
   - `tools/register_mcp_client.py`（客户端自动注册）
   - `tools/check_mcp_server.py`（门禁阈值更新）
5. **测试**：`tools/tests/test_mcp_server_expansion.py`

---

**文档版本**：v1.0.0
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
