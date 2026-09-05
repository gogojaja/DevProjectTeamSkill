#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Server 固化门禁（硬门禁）。

检查项（全部为静态分析，不导入 MCP Server 模块，避免触发依赖安装）：
  1. skills_mcp_server.py 语法编译通过（py_compile）
  2. @mcp.tool() 装饰的函数数量 ≥ 阈值（默认 5，当前实际 7 的 ~80%）
  3. 工具函数引用的核心脚本在 tools/ 中存在（可达性）
  4. requirements.txt 存在且包含 mcp 依赖声明

用法：
  python tools/check_mcp_server.py              # 默认检查
  python tools/check_mcp_server.py --min-tools 5  # 自定义工具数下限
  python tools/check_mcp_server.py --json         # JSON 输出

退出码：0=通过，1=失败
"""
import os
import sys
import re
import py_compile
import tempfile
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCP_SERVER = os.path.join(ROOT, "tools", "mcp_server", "skills_mcp_server.py")
REQUIREMENTS = os.path.join(ROOT, "tools", "mcp_server", "requirements.txt")
TOOLS_DIR = os.path.join(ROOT, "tools")

# MCP 工具函数引用的核心脚本（静态分析提取）
EXPECTED_SCRIPTS = [
    "estimate_cost.py",
    "mirror_push.py",
    "solidify.py",
    "publish_production.py",
]

MIN_TOOLS_DEFAULT = 5


def check_compile():
    """检查 1：语法编译通过。"""
    try:
        tmp = tempfile.mktemp(suffix=".pyc")
        py_compile.compile(MCP_SERVER, cfile=tmp, doraise=True)
        os.unlink(tmp)
        return True, "语法编译通过"
    except py_compile.PyCompileError as e:
        return False, "语法编译失败: %s" % e


def check_tool_count(min_tools=MIN_TOOLS_DEFAULT):
    """检查 2：@mcp.tool() 数量 ≥ 阈值。"""
    if not os.path.isfile(MCP_SERVER):
        return False, "文件不存在: %s" % MCP_SERVER, 0
    with open(MCP_SERVER, encoding="utf-8") as f:
        content = f.read()
    count = len(re.findall(r"@mcp\.tool\(\)", content))
    ok = count >= min_tools
    return ok, "@mcp.tool() 数量: %d（阈值 ≥%d）" % (count, min_tools), count


def check_script_reachability():
    """检查 3：工具引用的核心脚本存在。"""
    missing = []
    for script in EXPECTED_SCRIPTS:
        path = os.path.join(TOOLS_DIR, script)
        if not os.path.isfile(path):
            missing.append(script)
    if missing:
        return False, "缺失脚本: %s" % ", ".join(missing)
    return True, "核心脚本可达（%d 个）" % len(EXPECTED_SCRIPTS)


def check_requirements():
    """检查 4：requirements.txt 存在且包含 mcp 依赖。"""
    if not os.path.isfile(REQUIREMENTS):
        return False, "requirements.txt 不存在"
    with open(REQUIREMENTS, encoding="utf-8") as f:
        content = f.read()
    if "mcp" not in content:
        return False, "requirements.txt 未声明 mcp 依赖"
    return True, "requirements.txt 有效（含 mcp 依赖）"


def main():
    min_tools = MIN_TOOLS_DEFAULT
    as_json = False
    for arg in sys.argv[1:]:
        if arg == "--json":
            as_json = True
        elif arg.startswith("--min-tools"):
            try:
                min_tools = int(arg.split("=", 1)[1]) if "=" in arg else int(sys.argv[sys.argv.index(arg) + 1])
            except (ValueError, IndexError):
                pass

    passed = 0
    failed = 0
    results = []

    # 检查 1: 语法编译
    ok, msg = check_compile()
    results.append({"check": "语法编译", "ok": ok, "msg": msg})
    print("  %s 语法编译: %s" % ("✓" if ok else "✗", msg))
    passed += ok; failed += (not ok)

    # 检查 2: 工具计数
    ok, msg, count = check_tool_count(min_tools)
    results.append({"check": "工具计数", "ok": ok, "msg": msg})
    print("  %s %s" % ("✓" if ok else "✗", msg))
    passed += ok; failed += (not ok)

    # 检查 3: 脚本可达性
    ok, msg = check_script_reachability()
    results.append({"check": "脚本可达性", "ok": ok, "msg": msg})
    print("  %s %s" % ("✓" if ok else "✗", msg))
    passed += ok; failed += (not ok)

    # 检查 4: requirements.txt
    ok, msg = check_requirements()
    results.append({"check": "依赖声明", "ok": ok, "msg": msg})
    print("  %s %s" % ("✓" if ok else "✗", msg))
    passed += ok; failed += (not ok)

    print("  MCP Server 门禁: %d 通过, %d 失败" % (passed, failed))

    if as_json:
        import json
        print(json.dumps({"passed": passed, "failed": failed, "results": results}, ensure_ascii=False))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
