#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
薄封装代理共享路径解析模块（dev-task-scheduler）。
所有 dev-task-scheduler 代理脚本统一经此模块定位项目根目录与本仓库根目录，实现跨机器可移植。

dev-task-scheduler 定位优先级：
  1. 环境变量 DEV_TASK_SCHEDULER_ROOT
  2. 同级目录约定：<本仓库>/../dev-task-scheduler
  3. 配置文件 <本仓库>/.scheduler_root（内容为 dev-task-scheduler 绝对路径）

PROJECT_ROOT 永远动态计算为本仓库根目录（代理脚本所在 tools/ 的上级）。
"""
import os
from pathlib import Path

# 本仓库根目录（动态计算，不硬编码）
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent)))


def find_scheduler_root():
    """定位 dev-task-scheduler 项目根目录。返回 Path 或 None。"""
    # 1. 环境变量
    env_root = os.environ.get("DEV_TASK_SCHEDULER_ROOT")
    if env_root:
        p = Path(env_root)
        if p.is_dir() and (p / "scheduler").is_dir():
            return p
    # 2. 同级目录约定：<repo>/../dev-task-scheduler
    sibling = PROJECT_ROOT.parent / "dev-task-scheduler"
    if sibling.is_dir() and (sibling / "scheduler").is_dir():
        return sibling
    # 3. 配置文件
    cfg = PROJECT_ROOT / ".scheduler_root"
    if cfg.exists():
        p = Path(cfg.read_text(encoding="utf-8").strip())
        if p.is_dir() and (p / "scheduler").is_dir():
            return p
    return None


def run_scheduler_cli(args=None):
    """
    调用 dev-task-scheduler CLI：定位项目根目录并转发参数，注入 PROJECT_ROOT。
    返回退出码（int）。供各代理脚本 main() 调用。
    """
    import subprocess
    import sys

    scheduler_root = find_scheduler_root()
    if scheduler_root is None:
        print("[error] dev-task-scheduler 工具缺失", file=sys.stderr)
        print("        安装方式：", file=sys.stderr)
        print("          1. 将 dev-task-scheduler 项目 clone 到本仓库同级目录（../dev-task-scheduler）", file=sys.stderr)
        print("          2. 或设置环境变量 DEV_TASK_SCHEDULER_ROOT 指向项目根目录", file=sys.stderr)
        print("          3. 或创建配置文件 .scheduler_root 写入绝对路径", file=sys.stderr)
        print("        替代方案：定时任务功能不可用；核心技能库其他功能不受影响", file=sys.stderr)
        print("        详见 references/plugin_interface.md", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(PROJECT_ROOT)
    cli_path = scheduler_root / "scheduler" / "cli.py"
    if not cli_path.exists():
        print("[error] dev-task-scheduler CLI 不存在: %s" % cli_path, file=sys.stderr)
        return 1
    cmd = [sys.executable or "python3", str(cli_path)] + (args or sys.argv[1:])
    return subprocess.call(cmd, env=env)
