#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[薄封装代理] 本文件仅转发到 dev-git-hub（AUTH-014 独立项目）对应脚本。
原实现已剥离至 dev-git-hub/tools/init_mac_bare_repos.py（2026-09-05 整改 R-1），本项目经此代理调用，保持原命令/参数兼容。
本地最小 git 操作（init/status/commit/log/diff）仍用 git 原生。
路径经 tools/_hub_proxy.py 动态解析（环境变量 DEV_GIT_HUB_ROOT > 同级目录约定 > .hub_root 配置），跨机器可移植。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hub_proxy import run_proxy

if __name__ == "__main__":
    sys.exit(run_proxy("init_mac_bare_repos.py", "init_mac_bare_repos.py"))
