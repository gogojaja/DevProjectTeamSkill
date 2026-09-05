#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件链路固化门禁（软门禁，不阻断固化）。

检查项：
  1. 各 _xxx_proxy.py 语法编译通过
  2. plugin_registry.json 格式有效
  3. .env.example 存在且包含全部插件环境变量
  4. plugin_registry.json 中 proxy_module 引用的模块在 tools/ 中存在

用法：
  python tools/check_plugin_chain.py          # 默认检查
  python tools/check_plugin_chain.py --json    # JSON 输出

退出码：0=通过，1=失败（但作为软门禁，solidify 不因失败中止）
"""
import os
import sys
import re
import json
import py_compile
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS_DIR = os.path.join(ROOT, "tools")
REFERENCES_DIR = os.path.join(ROOT, "references")

PROXY_SCRIPTS = [
    "_hub_proxy.py",
    "_scheduler_proxy.py",
    "_model_router_proxy.py",
]

PLUGIN_ENV_VARS = [
    "DEV_GIT_HUB_ROOT",
    "DEV_TASK_SCHEDULER_ROOT",
    "DEV_MODEL_ROUTER_ROOT",
    "DEV_PROJECT_MGMT_ROOT",
    "DEV_SECURITY_TOOLS_ROOT",
    "DEV_TEST_TOOLS_ROOT",
    "FREE_API_HUB_ROOT",
]


def check_proxy_compile():
    """检查 1：代理脚本语法编译通过。"""
    failed = []
    for script in PROXY_SCRIPTS:
        path = os.path.join(TOOLS_DIR, script)
        if not os.path.isfile(path):
            failed.append("%s（不存在）" % script)
            continue
        try:
            tmp = os.path.join(TOOLS_DIR, "__pycache__", "_check_%s.pyc" % script.replace(".", "_"))
            py_compile.compile(path, cfile=tmp, doraise=True)
        except py_compile.PyCompileError as e:
            failed.append("%s: %s" % (script, e))
    if failed:
        return False, "代理脚本编译失败: %s" % "; ".join(failed)
    return True, "代理脚本全部编译通过（%d 个）" % len(PROXY_SCRIPTS)


def check_registry():
    """检查 2：plugin_registry.json 格式有效。"""
    path = os.path.join(REFERENCES_DIR, "plugin_registry.json")
    if not os.path.isfile(path):
        return False, "plugin_registry.json 不存在", 0
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        count = len(data.get("plugins", []))
        return True, "plugin_registry.json 有效（%d 个插件）" % count, count
    except (json.JSONDecodeError, KeyError) as e:
        return False, "plugin_registry.json 格式错误: %s" % e, 0


def check_env_example():
    """检查 3：.env.example 存在且包含全部环境变量。"""
    path = os.path.join(ROOT, ".env.example")
    if not os.path.isfile(path):
        return False, ".env.example 不存在"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    missing = [v for v in PLUGIN_ENV_VARS if v not in content]
    if missing:
        return False, ".env.example 缺失变量: %s" % ", ".join(missing)
    return True, ".env.example 包含全部 %d 个插件变量" % len(PLUGIN_ENV_VARS)


def check_proxy_module_refs():
    """检查 4：plugin_registry.json 中 proxy_module 引用的模块存在。"""
    path = os.path.join(REFERENCES_DIR, "plugin_registry.json")
    if not os.path.isfile(path):
        return True, "跳过（plugin_registry.json 不存在）"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return True, "跳过（plugin_registry.json 格式错误）"

    missing = []
    for plugin in data.get("plugins", []):
        mod = plugin.get("proxy_module")
        if mod:
            script = "_%s.py" % mod if not mod.startswith("_") else "%s.py" % mod
            if not os.path.isfile(os.path.join(TOOLS_DIR, script)):
                missing.append("%s → %s" % (plugin["name"], script))
    if missing:
        return False, "proxy_module 引用缺失: %s" % "; ".join(missing)
    return True, "proxy_module 引用全部可达"


def main():
    as_json = "--json" in sys.argv
    passed = 0
    failed = 0
    results = []

    checks = [
        ("代理脚本编译", check_proxy_compile),
        ("插件注册表", check_registry),
        ("环境变量模板", check_env_example),
        ("proxy_module 引用", check_proxy_module_refs),
    ]

    for name, func in checks:
        result = func()
        ok = result[0]
        msg = result[1]
        results.append({"check": name, "ok": ok, "msg": msg})
        print("  %s %s: %s" % ("✓" if ok else "✗", name, msg))
        passed += ok; failed += (not ok)

    print("  插件链路检查（软门禁，不阻断）: %d 通过, %d 失败" % (passed, failed))

    if as_json:
        print(json.dumps({"passed": passed, "failed": failed, "results": results}, ensure_ascii=False))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
