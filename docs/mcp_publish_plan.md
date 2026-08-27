# 将 DevProjectTeamSkill 发布为各工具可调用的 MCP 服务 · 方案与执行计划

- **文档版本**：v1.0.0　**制定日期**：2026-08-27
- **来源技能**：`best-practice-solution` FULL 水线（Triage→Research→Draft→Review→Converge）
- **评审结论**：SIGNED_OFF（三视角：架构一致性 / 安全合规 / 成本可演进；1 项 CR 已采纳）
- **关联版本**：技能库 v21.10.3（MCP 版本随其发布自动更新）

---

## 1. 决策记录草案（ADR 草案，正式编号交 role-architecture）

- **标识**：ADR-MCP-001（占位）
- **决策**：将 DevProjectTeamSkill 以 MCP 服务形式发布，使用**官方 MCP Python SDK**（`pip install "mcp[cli]"` → `mcp.server.fastmcp.FastMCP`），而非独立 Prefect `fastmcp` 包。
- **选项**：
  1. 官方 SDK（FastMCP 内置，`@mcp.tool()` 带括号）— **采纳**
  2. 独立 Prefect `fastmcp` 包（v3.x，`@mcp.tool` 无括号）— 弃（依赖混淆、与官方 import 冲突）
  3. 仅保留现有 skill 文件部署，不做 MCP — 基线项，弃（无法满足跨工具统一调用）
- **理由**：官方 SDK spec 对齐、依赖最少、与协议修订同步；社区存在「两个 FastMCP」混淆风险，选官方包规避（证据 EV-001/002）。
- **已验证**：官方 SDK 文档（modelcontextprotocol.python-sdk / py.sdk.modelcontextprotocol.io，2026-08）、教程 cross-check（codersera 2026-06-30）确认装饰器/import 差异与 stdio+Streamable HTTP+SSE 传输。
- **不确定**：各工具（Copilot/Agents/WorkBuddy）mcpServers 配置字段细节可能微调；以各工具官方文档为准，本方案提供片段模板。
- **未关闭风险**：经 MCP 暴露 solidify/publish/mirror_push 具副作用 → 已采纳 CR：经 MCP 调用时默认 `dry_run=True` 或禁用正式发布，正式动作仅限本地终端。
- **反信号**：若官方 SDK 弃用 FastMCP 内置 API，则迁移至独立包（装饰器机械化替换）。

---

## 2. 方案（双栏）

### ✅ 可稳定达成效果
- 用官方 `mcp[cli]` + `FastMCP` 装饰器，将现有 `tools/*.py` 零逻辑复制地包装为 MCP **tools**「证据: EV-001 [T1]」。
- 将 `references/*.md` / `SKILL_INDEX.md` 暴露为 MCP **resources**（`skill://...` URI），只读、无副作用「证据: EV-001」。
- 角色调用/阶段评审暴露为 MCP **prompts**（模板化）。
- 默认 **stdio** 传输，各客户端本地拉起、读取同一份 `.trae/skills` 单源 → 天然版本一致「证据: 铁律#1」。
- **版本治理（用户核心诉求）**：server 运行时**动态读取**编排器 `SKILL.md` 版本（不硬编码）；`publish_production.py` 发布时自动生成 `tools/mcp_server/manifest.json` + `VERSION`；client 经 `skill://version` 即得最新 → **多工具共享同一 MCP 端点版本，无需各自同步**「证据: 设计」。
- 各工具接入仅需在 `mcpServers` 指向 `python3 tools/mcp_server/skills_mcp_server.py`（片段见 docs/mcp_client_config.md）「证据: EV-002」。

### ⚠️ 理论最优与当前限制
- 角色路由/成本预警「判断」属 LLM 推理，MCP 仅暴露**执行工具+知识**，推理仍留 `SKILL.md`（prompt 编排）「反信号: 若强行把推理函数化会损失灵活性」。
- 客户端需预装 `mcp` 包（提供 `requirements.txt` + 自动探测）「证据: insufficient 客户端环境差异」。
- 共享 HTTP 端点需独立部署进程+鉴权，超出本期；本期以 stdio 为主、预留 `transport="streamable-http"`「证据: EV-002」。

---

## 3. 多视角评审报告（FULL，串行自评 + 1 真实外部信号）

| 视角 | 结论 | 关键意见 |
|------|------|----------|
| 架构/技术路线一致性 | SIGNED_OFF | 官方 SDK 避免与独立 fastmcp 混淆；单源读取符合铁律#1；与现有 skill 文件部署互补不替代 |
| 安全合规 | SIGNED_OFF | 凭据不经 MCP（环境变量/`.secrets`）；副作用工具（solidify/publish/mirror_push）经 MCP 默认 dry_run 或禁用；脱敏门禁已在 publish 链路（铁律#3/#8/#12） |
| 成本+可演进 | SIGNED_OFF | 版本动态读取+发布即更新，彻底解决多工具反复同步；官方 SDK 依赖少、长期可演进 |
| **聚合** | **SIGNED_OFF** | 1 CR（副作用工具安全默认）已采纳为设计约束 |

---

## 4. 执行计划（分阶段落地）

- **Phase A（核心服务）**：新建 `tools/mcp_server/skills_mcp_server.py`（官方 SDK），包装 tools/resources/prompts；`tools/mcp_server/requirements.txt`。
- **Phase B（版本治理）**：server 动态读版本；`publish_production.py` 注入 `emit_mcp_manifest()` 生成 `manifest.json`+`VERSION`。
- **Phase C（接入文档）**：`docs/mcp_client_config.md` 提供 opencode/Claude/Cursor/Trae/Copilot/Agents/WorkBuddy 的 `mcpServers` 片段。
- **收尾**：`py_compile` 语法校验 → 四门禁 → `solidify` → commit → `mirror_push` 双推。

---

## 5. 验收门禁
- `python3 -m py_compile tools/mcp_server/skills_mcp_server.py tools/publish_production.py` 通过。
- `publish_production.py --dry-run` 输出含「将写入 manifest.json + VERSION」。
- 四门禁（closure/version/release/links）通过。
- `docs/mcp_client_config.md` 含 ≥4 种工具片段。
