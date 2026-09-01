#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[薄封装代理] 本文件仅转发到 dev-model-router（AUTH-016 独立项目）对应脚本。
原实现已剥离至 dev-model-router/cli.py，本项目经此代理调用，保持原命令/参数兼容。
路径经 tools/_model_router_proxy.py 动态解析（环境变量 DEV_MODEL_ROUTER_ROOT > 同级目录约定 > .model_router_root 配置），跨机器可移植。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _model_router_proxy import run_model_router_cli

if __name__ == "__main__":
    sys.exit(run_model_router_cli())
