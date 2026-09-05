# DevProjectTeamSkill MCP 逐 IDE 验证步骤

> 目的：各 AI 工具已接入本技能 MCP（`dev-project-team-skill`，stdio server = `.venv/bin/python tools/mcp_server/skills_mcp_server.py`）。
> 本文档给出在无头环境之外、于各 GUI 工具内**肉眼确认连接成功（绿点）并实测调用**的步骤。
> Server 端已通过 stdio 握手实测（7 tools / 2 resources / 2 prompts，`skill_list` 可调用）。

## 通用验证方法

1. 打开对应 IDE / 工具，加载本项目（或任意工作区）。
2. 进入该工具的 **MCP / MCP Servers** 面板（各工具入口见下表）。
3. 找到 `dev-project-team-skill`，确认状态为 **已连接 / Connected / 绿点**。
4. 实测调用：在对话/命令中调用一个 MCP 工具，例如列出技能 `skill_list`，或执行门禁 `run_gate`，确认返回正常（非报错、非超时）。
5. 若状态异常，优先排查：① venv 路径是否存在（`<repo-root>/.venv/bin/python`）；② server 文件是否存在（`tools/mcp_server/skills_mcp_server.py`）；③ 网络/权限（opencode 全局库需在 `~/.config/opencode/skills` 发布后才对本仓库外生效）。

## 各工具验证入口

| 工具 | MCP 面板 / 入口位置 | 配置文件（已写入） |
|---|---|---|
| opencode（项目级） | 命令面板 `MCP: List Servers`；或查看 `opencode.json` 的 `mcp` 段 | `<repo>/opencode.json`（`mcp.dev-project-team-skill`, type=local） |
| Trae CN | 设置 → MCP → 已连接服务 | `~/Library/Application Support/Trae CN/User/settings.json` |
| Qoder CN | 设置 → MCP Servers | `~/Library/Application Support/QoderCN/User/settings.json` |
| Comate | 左侧/设置 → MCP | `~/Library/Application Support/Comate/User/settings.json` |
| CodeBuddy CN | 设置 → MCP | `~/Library/Application Support/CodeBuddy CN/User/settings.json` |
| CodeGeeX（VS Code 宿主） | VS Code 命令面板 `MCP: List Servers` | `~/Library/Application Support/Code/User/settings.json` |
| CodeFlicker | 设置 → MCP | `~/Library/Application Support/CodeFlicker/User/settings.json` |
| Windsurf | Cascade 面板 → 齿轮 → MCP Servers | `~/Library/Application Support/Windsurf/User/settings.json` |
| Cline | Cline 扩展 → MCP Servers 标签 | `~/.cline/mcp_settings.json` |
| Roo Code | Roo 扩展 → MCP 标签 | `~/.roo/mcp.json` |
| Continue.dev | 底部 Continue 图标 → 配置/MCP；或命令 `Continue: Open MCP Servers` | `~/.continue/config.yaml`（`mcpServers`） |
| Zed | 设置 → MCP（命令面板 `Zed: Open User Settings (JSON)` 查 `mcp` 段或底部状态栏） | `~/.config/zed/settings.json`（v1.17.2, type=stdio） |

> VS Code 系工具（Trae / Qoder / Comate / CodeBuddy / CodeGeeX / CodeFlicker / Windsurf）均复用 VS Code 的 `mcpServers` 配置键，验证入口基本一致。

## 故障排查

- **状态黄/红或拉起失败**：确认 `.venv` 已创建（开发固化 `solidify` 或 `python -m venv .venv && .venv/bin/pip install -r tools/mcp_server/requirements.txt`）。
- **opencode 全局调用不到技能**：开发版本在仓库项目级生效；跨项目消费需 `bash tools/publish_production.sh` 发布到 `~/.config/opencode/skills`。
- **Continue.dev 未出现条目**：确认 `~/.continue/config.yaml` 已含 `mcpServers` 段并已重启 VS Code / Continue 扩展。
- **调用超时**：检查 `START_MCP_TIMEOUT_MS`/`RUN_MCP_TIMEOUT_MS`（opencode 已设 60s/300s）；其余工具默认超时若过短，可在对应配置加 `env` 覆盖。

## 已实测

- Server 握手：`initialize` → `DevProjectTeamSkill v1.29.1`；`tools/list` 返回 7 个工具；`resources/list` 2 个；`prompts/list` 2 个；`tools/call skill_list` 正常。
- 配置校验：上述 12 个工具（含 opencode）配置文件均含 `dev-project-team-skill` 且指向正确 server（10/10 stdio/type 一致 PASS；Continue.dev/Zed 本次新接入，Zed GUI 绿点待启动后确认）。
