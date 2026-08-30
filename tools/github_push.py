#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[M1 git 剥离薄封装代理] 本文件仅转发到 dev-git-hub（AUTH-014 独立项目）对应脚本。
原实现已剥离至 /Volumes/BR256G/dev-git-hub/tools/tools/github_push.py，本项目经此代理调用，
保持原命令/参数兼容（agent_loop/self_heal/mcp_server/tests 调用链无感）。
本地最小 git 操作（init/status/commit/log/diff）仍用 git 原生，不走此处。
"""
import os
import subprocess
import sys
from pathlib import Path

HUB_SCRIPT = Path("/Volumes/BR256G/dev-git-hub/tools/github_push.py")

def main():
    if not HUB_SCRIPT.exists():
        print("[error] dev-git-hub 工具缺失: {HUB_SCRIPT}（请先初始化 dev-git-hub 项目）", file=sys.stderr)
        return 1
    # 环境变量透传（GITHUB_TOKEN/GITEE_TOKEN 等）
    env = os.environ.copy()
    cmd = [sys.executable or "python3", str(HUB_SCRIPT)] + sys.argv[1:]
    return subprocess.call(cmd, env=env)

if __name__ == "__main__":
    sys.exit(main())
