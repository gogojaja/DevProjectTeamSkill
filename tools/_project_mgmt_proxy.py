#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
薄封装代理共享路径解析模块（dev-project-mgmt）。
所有 dev-project-mgmt 代理脚本统一经此模块定位项目根目录与本仓库根目录，实现跨机器可移植。

dev-project-mgmt 定位优先级：
  1. 环境变量 DEV_PROJECT_MGMT_ROOT
  2. 同级目录约定：<本仓库>/../dev-project-mgmt
  3. 配置文件 <本仓库>/.project_mgmt_root（内容为 dev-project-mgmt 绝对路径）

PROJECT_ROOT 永远动态计算为本仓库根目录（代理脚本所在 tools/ 的上级）。
"""
import os
import subprocess
import sys
from pathlib import Path

# 本仓库根目录（动态计算，不硬编码）
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent)))


def find_project_mgmt_root():
    """定位 dev-project-mgmt 项目根目录。返回 Path 或 None。"""
    # 1. 环境变量
    env_root = os.environ.get("DEV_PROJECT_MGMT_ROOT")
    if env_root:
        p = Path(env_root)
        if p.is_dir() and (p / "dev_project_mgmt").is_dir():
            return p
    # 2. 同级目录约定：<repo>/../dev-project-mgmt
    sibling = PROJECT_ROOT.parent / "dev-project-mgmt"
    if sibling.is_dir() and (sibling / "dev_project_mgmt").is_dir():
        return sibling
    # 3. 配置文件
    cfg = PROJECT_ROOT / ".project_mgmt_root"
    if cfg.exists():
        p = Path(cfg.read_text(encoding="utf-8").strip())
        if p.is_dir() and (p / "dev_project_mgmt").is_dir():
            return p
    return None


def run_project_mgmt_cli(args=None, capture=False):
    """
    调用 dev-project-mgmt CLI：定位项目根目录并转发参数，注入 PROJECT_ROOT。

    Args:
        args: 命令行参数列表（None 时使用 sys.argv[1:]）
        capture: 是否捕获输出（True 返回 CompletedProcess，False 直接转发）

    Returns:
        capture=True 时返回 subprocess.CompletedProcess；capture=False 时返回退出码（int）
    """
    mgmt_root = find_project_mgmt_root()
    if mgmt_root is None:
        msg = (
            "[error] dev-project-mgmt 工具缺失\n"
            "        安装方式：\n"
            "          1. 将 dev-project-mgmt 项目 clone 到本仓库同级目录（../dev-project-mgmt）\n"
            "          2. 或设置环境变量 DEV_PROJECT_MGMT_ROOT 指向项目根目录\n"
            "          3. 或创建配置文件 .project_mgmt_root 写入绝对路径\n"
            "        替代方案：项目管理工具不可用；核心技能库其他功能不受影响\n"
            "        详见 references/plugin_interface.md"
        )
        if capture:
            return subprocess.CompletedProcess(
                args=args or [], returncode=1, stdout="", stderr=msg
            )
        print(msg, file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(PROJECT_ROOT)
    # 使用 python -m dev_project_mgmt 方式运行（支持相对导入）
    pkg_dir = str(mgmt_root)
    main_py = mgmt_root / "dev_project_mgmt" / "__main__.py"
    if not main_py.exists():
        msg = "[error] dev-project-mgmt CLI 不存在: %s" % main_py
        if capture:
            return subprocess.CompletedProcess(
                args=args or [], returncode=1, stdout="", stderr=msg
            )
        print(msg, file=sys.stderr)
        return 1
    cmd = [sys.executable or "python3", "-m", "dev_project_mgmt"] + (args or sys.argv[1:])
    if capture:
        return subprocess.run(
            cmd, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
            cwd=pkg_dir,
        )
    return subprocess.call(cmd, env=env, cwd=pkg_dir)
