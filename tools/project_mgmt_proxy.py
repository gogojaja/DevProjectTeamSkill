#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[薄封装代理] 本文件仅转发到 dev-project-mgmt（AUTH-022 独立项目）对应脚本。
原实现已剥离至 dev-project-mgmt/dev_project_mgmt/cli.py，本项目经此代理调用，保持原命令/参数兼容。
路径经 tools/_project_mgmt_proxy.py 动态解析（环境变量 DEV_PROJECT_MGMT_ROOT > 同级目录约定 > .project_mgmt_root 配置），跨机器可移植。

子命令：
  raid list/add/update/close     RAID 四维台账管理
  report weekly/phase            进展报告生成
  change list/register/analyze/approve/reject  变更协调
  evm calc/status/add-milestone  EVM 挣值分析

用法：
  python tools/project_mgmt_proxy.py raid list
  python tools/project_mgmt_proxy.py evm calc
  python tools/project_mgmt_proxy.py report weekly
  python tools/project_mgmt_proxy.py change list
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _project_mgmt_proxy import run_project_mgmt_cli

if __name__ == "__main__":
    sys.exit(run_project_mgmt_cli())
