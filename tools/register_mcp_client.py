#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 客户端自动注册工具（v1.0.0）。

自动检测已安装的 AI 工具并向其配置文件注入 MCP Server 注册信息，
使 DevProjectTeamSkill MCP Server 可在各工具中统一调用。

支持的工具矩阵：
  - opencode: ~/.config/opencode/opencode.jsonc
  - TRAE: ~/.trae/mcp.json
  - TRAE 中国版: ~/.trae-cn/mcp.json
  - Qoder: ~/.qoder/mcp.json
  - Qoder 中国版: ~/.qoder-cn/mcp.json
  - Claude Desktop: ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
                   %APPDATA%/Claude/claude_desktop_config.json (Windows)
  - Cursor: .cursor/mcp.json (项目级)

安全约束（铁律 #7/#7a/#15）：
  - 写入前备份原配置文件到 .backup/
  - 写入审计台账
  - 默认 dry_run=True 仅探测

用法：
  python tools/register_mcp_client.py                    # 自动发现已安装工具并注册
  python tools/register_mcp_client.py --tool opencode    # 仅注册 opencode
  python tools/register_mcp_client.py --dry-run          # 仅探测不写入
  python tools/register_mcp_client.py --verify           # 注册后验证
"""
import os
import sys
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_DIR = os.path.join(ROOT, ".backup")

# MCP Server 配置片段
MCP_SERVER_CONFIG = {
    "command": sys.executable,
    "args": [os.path.join("tools", "mcp_server", "skills_mcp_server.py")],
    "cwd": ROOT,
    "env": {
        "PROJECT_ROOT": ROOT
    }
}


def get_home_dir():
    """获取用户主目录。"""
    if sys.platform.startswith("win"):
        return os.environ.get("USERPROFILE", "")
    return os.path.expanduser("~")


def get_client_configs():
    """获取各工具配置文件路径矩阵。"""
    home = get_home_dir()
    configs = {}

    # opencode
    if sys.platform.startswith("win"):
        opencode_config = os.path.join(home, ".config", "opencode", "opencode.jsonc")
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        opencode_config = os.path.join(xdg, "opencode", "opencode.jsonc")
    configs["opencode"] = {
        "path": opencode_config,
        "parent": os.path.dirname(opencode_config),
        "format": "jsonc"
    }

    # TRAE
    if sys.platform.startswith("win"):
        trae_parent = os.path.join(home, ".trae")
    else:
        trae_parent = os.path.join(home, ".trae")
    configs["trae"] = {
        "path": os.path.join(trae_parent, "mcp.json"),
        "parent": trae_parent,
        "format": "json"
    }

    # TRAE 中国版
    if sys.platform.startswith("win"):
        traecn_parent = os.path.join(home, ".trae-cn")
    else:
        traecn_parent = os.path.join(home, ".trae-cn")
    configs["trae-cn"] = {
        "path": os.path.join(traecn_parent, "mcp.json"),
        "parent": traecn_parent,
        "format": "json"
    }

    # Qoder（全球版 + 中国版）
    # 全球版: ~/.qoder/mcp.json
    qoder_parent = os.path.join(home, ".qoder")
    configs["qoder"] = {
        "path": os.path.join(qoder_parent, "mcp.json"),
        "parent": qoder_parent,
        "format": "json"
    }
    # 中国版: ~/.qoder-cn/mcp.json
    qodercn_parent = os.path.join(home, ".qoder-cn")
    configs["qoder-cn"] = {
        "path": os.path.join(qodercn_parent, "mcp.json"),
        "parent": qodercn_parent,
        "format": "json"
    }

    # Claude Desktop
    if sys.platform == "darwin":
        claude_parent = os.path.join(home, "Library", "Application Support", "Claude")
    elif sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        claude_parent = os.path.join(appdata, "Claude")
    else:
        claude_parent = os.path.join(home, ".config", "Claude")
    configs["claude"] = {
        "path": os.path.join(claude_parent, "claude_desktop_config.json"),
        "parent": claude_parent,
        "format": "json"
    }

    # Cursor (项目级)
    configs["cursor"] = {
        "path": os.path.join(ROOT, ".cursor", "mcp.json"),
        "parent": os.path.join(ROOT, ".cursor"),
        "format": "json"
    }

    return configs


def discover_installed_clients(configs):
    """检测已安装的工具（父目录存在即视为已安装）。"""
    installed = {}
    for name, cfg in configs.items():
        if os.path.isdir(cfg["parent"]):
            installed[name] = cfg
    return installed


def backup_config(config_path):
    """备份原配置文件到 .backup/。"""
    if not os.path.isfile(config_path):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    basename = os.path.basename(config_path)
    backup_path = os.path.join(BACKUP_DIR, f"{basename}.{timestamp}")
    shutil.copy2(config_path, backup_path)
    return backup_path


def inject_mcp_config(config_path, config_format, dry_run=False):
    """向配置文件注入 MCP Server 配置。"""
    # 读取现有配置
    config = {}
    if os.path.isfile(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                content = f.read()
            # 处理 JSONC（去除注释）
            if config_format == "jsonc":
                lines = []
                for line in content.splitlines():
                    stripped = line.strip()
                    if not stripped.startswith("//"):
                        lines.append(line)
                content = "\n".join(lines)
            config = json.loads(content)
        except json.JSONDecodeError as e:
            return False, f"配置文件解析失败: {e}"

    # 注入 MCP Server 配置
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    config["mcpServers"]["dev-project-team-skill"] = MCP_SERVER_CONFIG

    if dry_run:
        return True, f"(dry-run) 将写入 {config_path}"

    # 写入配置
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return True, f"已写入 {config_path}"


def verify_config(config_path, config_format):
    """验证配置文件是否包含正确的 MCP Server 注册。"""
    if not os.path.isfile(config_path):
        return False, f"配置文件不存在: {config_path}"
    try:
        with open(config_path, encoding="utf-8") as f:
            content = f.read()
        # 处理 JSONC
        if config_format == "jsonc":
            lines = []
            for line in content.splitlines():
                if not line.strip().startswith("//"):
                    lines.append(line)
            content = "\n".join(lines)
        config = json.loads(content)
        if "mcpServers" in config and "dev-project-team-skill" in config["mcpServers"]:
            server_cfg = config["mcpServers"]["dev-project-team-skill"]
            if server_cfg.get("cwd") == ROOT:
                return True, "验证通过"
            return False, f"cwd 不匹配: 期望 {ROOT}, 实际 {server_cfg.get('cwd')}"
        return False, "未找到 dev-project-team-skill 注册"
    except Exception as e:
        return False, f"验证失败: {e}"


def write_audit_log(action, target, result):
    """写入审计台账（铁律 #7b）。"""
    ledger_path = os.path.join(ROOT, "台账", "13_安全审计台账.csv")
    if not os.path.isfile(ledger_path):
        return
    import csv
    import socket
    import uuid
    timestamp = datetime.now().astimezone().isoformat()
    session_id = str(uuid.uuid4())[:8]
    row = {
        "操作编号": f"OP-AUDIT-MCP-{datetime.now().strftime('%Y%m%d')}",
        "操作类型": action,
        "操作目标": target,
        "操作结果": result,
        "主机标识": socket.gethostname(),
        "客户端工具": "register_mcp_client",
        "模型名称": "N/A",
        "操作时间": timestamp,
        "会话ID": session_id,
    }
    try:
        with open(ledger_path, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writerow(row)
    except Exception:
        pass  # 审计写入失败不阻断主流程


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MCP 客户端自动注册工具")
    parser.add_argument("--tool", help="仅注册指定工具（opencode/trae/claude/cursor）")
    parser.add_argument("--dry-run", action="store_true", default=True, help="仅探测不写入（默认）")
    parser.add_argument("--write", action="store_true", help="实际写入配置文件")
    parser.add_argument("--verify", action="store_true", help="注册后验证")
    args = parser.parse_args()

    dry_run = not args.write
    configs = get_client_configs()

    if args.tool:
        if args.tool not in configs:
            print(f"未知工具: {args.tool}（可选: {list(configs.keys())}）")
            return 1
        clients = {args.tool: configs[args.tool]}
    else:
        clients = discover_installed_clients(configs)

    if not clients:
        print("未检测到已安装的 AI 工具。请确认工具已安装或手动指定 --tool。")
        return 0

    print(f"{'='*60}")
    print(f"  MCP 客户端自动注册 (v1.0.0)")
    print(f"  模式: {'探测' if dry_run else '写入'}")
    print(f"{'='*60}")
    print(f"检测到 {len(clients)} 个已安装工具: {list(clients.keys())}")
    print()

    success_count = 0
    for name, cfg in clients.items():
        print(f"[{name}] {cfg['path']}")

        # 备份
        if os.path.isfile(cfg["path"]) and not dry_run:
            backup_path = backup_config(cfg["path"])
            if backup_path:
                print(f"  ✓ 已备份到 {backup_path}")

        # 注入
        ok, msg = inject_mcp_config(cfg["path"], cfg["format"], dry_run=dry_run)
        status = "✓" if ok else "✗"
        print(f"  {status} {msg}")

        if ok and not dry_run:
            success_count += 1
            write_audit_log("MCP客户端注册", name, "成功")

        # 验证
        if args.verify and not dry_run:
            v_ok, v_msg = verify_config(cfg["path"], cfg["format"])
            print(f"  {'✓' if v_ok else '✗'} 验证: {v_msg}")

        print()

    print(f"{'='*60}")
    if dry_run:
        print(f"  探测完成。如需实际写入，请添加 --write 参数。")
    else:
        print(f"  注册完成: {success_count}/{len(clients)} 个工具成功。")
    print(f"{'='*60}")

    return 0 if success_count == len(clients) or dry_run else 1


if __name__ == "__main__":
    sys.exit(main())
