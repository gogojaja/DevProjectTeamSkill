# 各工具接入 DevProjectTeamSkill MCP 服务 · 配置片段

- **文档版本**：v1.0.0　**关联**：`tools/mcp_server/skills_mcp_server.py`（官方 `mcp[cli]` SDK）
- **前置**：客户端环境需 `pip install "mcp[cli]<2"`（见 `tools/mcp_server/requirements.txt`）；server 以 **stdio** 拉起，工作目录须为**仓库根**。
- ⚠️ **版本引脚**：当前 server 使用官方 SDK **v1.x（FastMCP 装饰器）**；`mcp 2.x` 已把 `FastMCP` 重命名为 `MCPServer` 并改 API，装到 2.x 会导入失败，务必 `<2`。
- **本机可用解释器**：`/opt/homebrew/bin/python3.12`（brew 3.12.13）或 `uv` 自带 3.10/3.12；系统 `/usr/bin/python3` 因 PEP 668 受限，需建 venv。已验证 `.venv`（brew 3.12 + mcp 1.29.1）可正常 `list_tools`。
- **Resources 说明**：`skill://index` 与 `skill://version` 为静态；`skill://role/{name}/SKILL`、`skill://references/{file}` 为 **URI 模板**（按具体 name/file 取值，不出现在 list 中）。

> 单一事实来源：技能库版本由 server 运行时动态读取 `.trae/skills/dev-project-team-skill/SKILL.md`；
> 每次 `publish_production` 还会生成 `tools/mcp_server/manifest.json` + `VERSION`。
> 所有工具指向**同一个 server 入口**，版本自动随发布更新，**无需各工具各自同步版本**。

## 通用 mcpServers 片段（stdin/stdio）

```json
{
  "mcpServers": {
    "dev-project-team-skill": {
      "command": "python3",
      "args": ["<仓库根>/tools/mcp_server/skills_mcp_server.py"]
    }
  }
}
```

## 各工具落点

### opencode
- 文件：`opencode.json`（项目级或全局 `~/.config/opencode/opencode.json`）
- 直接并入顶层 `mcpServers` 字段（使用上方片段，路径填绝对路径或相对仓库根的 `tools/mcp_server/skills_mcp_server.py`）。

### Claude Code
- 方式 A（CLI）：`claude mcp add dev-project-team-skill -- python3 <仓库根>/tools/mcp_server/skills_mcp_server.py`
- 方式 B（文件）：`~/Library/Application Support/Claude/claude_desktop_config.json`（macOS）或 `%APPDATA%\Claude\claude_desktop_config.json`（Windows）的 `mcpServers` 字段并入上方片段。

### Cursor
- 文件：`.cursor/mcp.json`（项目级）或 `~/.cursor/mcp.json`（全局），结构同通用片段。

### Trae（国际版 / 中国版）
- Trae 全局技能目录已含本技能；如需经 MCP 调用执行工具，在其 MCP 配置（对应 `mcpServers`）并入上方片段即可。

### GitHub Copilot / Agents / WorkBuddy
- 在其 MCP 服务器配置中以 **通用片段** 登记 `dev-project-team-skill` 条目（command + args），字段名通常即为 `mcpServers`；具体键名以各工具官方文档为准。

## 可用能力（server 暴露）
- **Tools**：`skill_list` / `skill_load` / `run_gate` / `estimate_cost` / `solidify`(默认 dry_run) / `publish_production`(默认 dry_run) / `mirror_push`
- **Resources**：`skill://index` / `skill://role/{name}/SKILL` / `skill://references/{file}` / `skill://version`
- **Prompts**：`invoke_role` / `phase_gate`

## 共享单端点（可选，团队场景）
- 默认 stdio 每个客户端本地拉起一份，已天然版本一致（读同一份 `.trae/skills`）。
- 如需团队共享单端点，可将 server 以 `transport="streamable-http"` 部署为常驻进程并加鉴权，各工具改为 `url` 型 `mcpServers` 配置。
