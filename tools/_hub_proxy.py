#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
薄封装代理共享路径解析模块。
所有 dev-git-hub 代理脚本（github_push/mirror_push/github_ip_refresh/_gh_ip_probe/check_github_connectivity）
统一经此模块定位 dev-git-hub 项目根目录与本仓库根目录，实现跨机器可移植。

dev-git-hub 定位优先级：
  1. 环境变量 DEV_GIT_HUB_ROOT
  2. 同级目录约定：<本仓库>/../dev-git-hub
  3. 配置文件 <本仓库>/.hub_root（内容为 dev-git-hub 绝对路径）

PROJECT_ROOT 永远动态计算为本仓库根目录（代理脚本所在 tools/ 的上级）。
"""
import os
from pathlib import Path

# 本仓库根目录（动态计算，不硬编码）
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def find_hub_root():
    """定位 dev-git-hub 项目根目录。返回 Path 或 None。"""
    # 1. 环境变量
    env_root = os.environ.get("DEV_GIT_HUB_ROOT")
    if env_root:
        p = Path(env_root)
        if p.is_dir() and (p / "tools").is_dir():
            return p
    # 2. 同级目录约定：<repo>/../dev-git-hub
    sibling = PROJECT_ROOT.parent / "dev-git-hub"
    if sibling.is_dir() and (sibling / "tools").is_dir():
        return sibling
    # 3. 配置文件
    cfg = PROJECT_ROOT / ".hub_root"
    if cfg.exists():
        p = Path(cfg.read_text(encoding="utf-8").strip())
        if p.is_dir() and (p / "tools").is_dir():
            return p
    return None


def find_hub_script(script_name):
    """定位 dev-git-hub 内 tools/<script_name>。返回 Path 或 None。"""
    hub_root = find_hub_root()
    if hub_root is None:
        return None
    script = hub_root / "tools" / script_name
    return script if script.exists() else None


def run_proxy(script_name, label="proxy"):
    """
    通用代理转发：定位 dev-git-hub 对应脚本并转发 sys.argv，注入 PROJECT_ROOT。
    返回退出码（int）。供各代理脚本 main() 调用。
    """
    import subprocess
    import sys

    hub_script = find_hub_script(script_name)
    if hub_script is None:
        print("[error] dev-git-hub 工具缺失: tools/%s" % script_name, file=sys.stderr)
        print("        请先初始化 dev-git-hub 项目（运行 scripts/bootstrap_remotes.sh 或 .py）",
              file=sys.stderr)
        print("        或设置环境变量 DEV_GIT_HUB_ROOT 指向 dev-git-hub 根目录", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(PROJECT_ROOT)
    cmd = [sys.executable or "python3", str(hub_script)] + sys.argv[1:]
    return subprocess.call(cmd, env=env)
