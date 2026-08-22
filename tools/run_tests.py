#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试运行脚本
支持跨平台：Windows/macOS/Linux
"""

import sys
import subprocess
from pathlib import Path

def run_tests(test_type="unit", verbose=False):
    """运行测试套件
    
    Args:
        test_type: 测试类型（unit/integration/all）
        verbose: 是否显示详细输出
    """
    tools_dir = Path(__file__).parent
    tests_dir = tools_dir / "tests"
    
    if not tests_dir.exists():
        print(f"错误：测试目录不存在 {tests_dir}")
        return 1
    
    cmd = [
        sys.executable, "-m", "pytest",
        str(tests_dir),
        "-v" if verbose else "-q"
    ]
    
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    
    try:
        result = subprocess.run(cmd, cwd=tools_dir)
        return result.returncode
    except FileNotFoundError:
        print("错误：pytest 未安装，请运行：pip install pytest")
        return 1

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="运行单元测试")
    parser.add_argument("--type", choices=["unit", "integration", "all"],
                        default="unit", help="测试类型")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="详细输出")
    
    args = parser.parse_args()
    sys.exit(run_tests(args.type, args.verbose))