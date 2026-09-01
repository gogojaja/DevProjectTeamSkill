#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
薄封装代理共享路径解析模块（dev-model-router）。
所有 dev-model-router 代理脚本统一经此模块定位项目根目录与本仓库根目录，实现跨机器可移植。

dev-model-router 定位优先级：
  1. 环境变量 DEV_MODEL_ROUTER_ROOT
  2. 同级目录约定：<本仓库>/../dev-model-router
  3. 配置文件 <本仓库>/.model_router_root（内容为 dev-model-router 绝对路径）

PROJECT_ROOT 永远动态计算为本仓库根目录（代理脚本所在 tools/ 的上级）。
"""
import os
from pathlib import Path

# 本仓库根目录（动态计算，不硬编码）
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent)))


def find_model_router_root():
    """定位 dev-model-router 项目根目录。返回 Path 或 None。"""
    # 1. 环境变量
    env_root = os.environ.get("DEV_MODEL_ROUTER_ROOT")
    if env_root:
        p = Path(env_root)
        if p.is_dir() and (p / "router").is_dir():
            return p
    # 2. 同级目录约定：<repo>/../dev-model-router
    sibling = PROJECT_ROOT.parent / "dev-model-router"
    if sibling.is_dir() and (sibling / "router").is_dir():
        return sibling
    # 3. 配置文件
    cfg = PROJECT_ROOT / ".model_router_root"
    if cfg.exists():
        p = Path(cfg.read_text(encoding="utf-8").strip())
        if p.is_dir() and (p / "router").is_dir():
            return p
    return None


def run_model_router_cli(args=None):
    """
    调用 dev-model-router CLI：定位项目根目录并转发参数，注入 PROJECT_ROOT。
    返回退出码（int）。供各代理脚本 main() 调用。
    """
    import subprocess
    import sys

    model_router_root = find_model_router_root()
    if model_router_root is None:
        print("[error] dev-model-router 工具缺失", file=sys.stderr)
        print("        请先初始化 dev-model-router 项目", file=sys.stderr)
        print("        或设置环境变量 DEV_MODEL_ROUTER_ROOT 指向项目根目录", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(PROJECT_ROOT)
    cli_path = model_router_root / "cli.py"
    if not cli_path.exists():
        print("[error] dev-model-router CLI 不存在: %s" % cli_path, file=sys.stderr)
        return 1
    cmd = [sys.executable or "python3", str(cli_path)] + (args or sys.argv[1:])
    return subprocess.call(cmd, env=env)
