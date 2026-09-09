#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试：MCP Server 功能扩充（v21.13.0 AI Agent 功能提升）。

测试覆盖：
  - 新增 8 个 MCP Tools（skill_search, skill_links, audit_query, scope_metrics,
    retro_harvest, review_execute, nightly_gate, skill_progress）
  - 新增 4 个 MCP Prompts（architecture_design, test_planning, incubation_assess, retrospective）
  - 客户端自动注册工具 register_mcp_client.py

测试范围：Tier1 只读工具全覆盖，Tier2 写工具仅测试 dry_run 模式。
"""
import os
import re
import sys
import json
import tempfile
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))


class TestMCPServerExpansion(unittest.TestCase):
    """MCP Server 扩充功能测试。"""

    @classmethod
    def setUpClass(cls):
        """测试环境初始化。"""
        cls.root = ROOT
        cls.mcp_server_path = ROOT / "tools" / "mcp_server" / "skills_mcp_server.py"
        cls.assertTrue(cls.mcp_server_path.exists(), f"MCP Server 不存在: {cls.mcp_server_path}")

    def test_01_syntax_compile(self):
        """测试 1：MCP Server 语法编译通过。"""
        import py_compile
        try:
            tmp = tempfile.mktemp(suffix=".pyc")
            py_compile.compile(str(self.mcp_server_path), cfile=tmp, doraise=True)
            os.unlink(tmp)
        except py_compile.PyCompileError as e:
            self.fail(f"语法编译失败: {e}")

    def test_02_tool_count(self):
        """测试 2：MCP Tools 数量 ≥ 15。"""
        with open(self.mcp_server_path, encoding="utf-8") as f:
            content = f.read()
        count = content.count("@mcp.tool()")
        self.assertGreaterEqual(count, 15, f"MCP Tools 数量不足: {count} < 15")

    def test_03_prompt_count(self):
        """测试 3：MCP Prompts 数量 ≥ 6。"""
        with open(self.mcp_server_path, encoding="utf-8") as f:
            content = f.read()
        count = content.count("@mcp.prompt()")
        self.assertGreaterEqual(count, 6, f"MCP Prompts 数量不足: {count} < 6")

    def test_04_new_tools_exist(self):
        """测试 4：新增 8 个 Tools 函数定义存在。"""
        with open(self.mcp_server_path, encoding="utf-8") as f:
            content = f.read()
        new_tools = [
            "def skill_search(",
            "def skill_links(",
            "def audit_query(",
            "def scope_metrics(",
            "def retro_harvest(",
            "def review_execute(",
            "def nightly_gate(",
            "def skill_progress(",
        ]
        for tool in new_tools:
            self.assertIn(tool, content, f"新增工具未定义: {tool}")

    def test_05_new_prompts_exist(self):
        """测试 5：新增 4 个 Prompts 函数定义存在。"""
        with open(self.mcp_server_path, encoding="utf-8") as f:
            content = f.read()
        new_prompts = [
            "def architecture_design(",
            "def test_planning(",
            "def incubation_assess(",
            "def retrospective(",
        ]
        for prompt in new_prompts:
            self.assertIn(prompt, content, f"新增 Prompt 未定义: {prompt}")


class TestRegisterMCPClient(unittest.TestCase):
    """客户端自动注册工具测试。"""

    @classmethod
    def setUpClass(cls):
        """测试环境初始化。"""
        cls.root = ROOT
        cls.register_script = ROOT / "tools" / "register_mcp_client.py"
        cls.assertTrue(cls.register_script.exists(), f"注册脚本不存在: {cls.register_script}")

    def test_01_syntax_compile(self):
        """测试 1：注册脚本语法编译通过。"""
        import py_compile
        try:
            tmp = tempfile.mktemp(suffix=".pyc")
            py_compile.compile(str(self.register_script), cfile=tmp, doraise=True)
            os.unlink(tmp)
        except py_compile.CouldNotCompileError as e:
            self.fail(f"语法编译失败: {e}")

    def test_02_dry_run_mode(self):
        """测试 2：dry-run 模式正常运行。"""
        result = subprocess.run(
            [sys.executable, str(self.register_script), "--dry-run"],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        self.assertEqual(result.returncode, 0, f"dry-run 失败: {result.stderr}")
        # 检查输出包含关键信息（探测模式）
        self.assertTrue(len(result.stdout) > 0 or "dry-run" in result.stdout.lower() or len(result.stderr) == 0)

    def test_03_discover_clients(self):
        """测试 3：客户端发现功能。"""
        result = subprocess.run(
            [sys.executable, str(self.register_script), "--dry-run"],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        self.assertEqual(result.returncode, 0)
        # 应检测到至少一个已安装工具或输出探测完成信息
        output = result.stdout + result.stderr
        self.assertTrue(len(output) > 0, "无输出")


class TestMCPServerGateThreshold(unittest.TestCase):
    """MCP Server 门禁阈值测试。"""

    @classmethod
    def setUpClass(cls):
        """测试环境初始化。"""
        cls.root = ROOT
        cls.check_script = ROOT / "tools" / "check_mcp_server.py"

    def test_01_gate_passes(self):
        """测试 1：门禁检查全部通过。"""
        result = subprocess.run(
            [sys.executable, str(self.check_script)],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        self.assertEqual(result.returncode, 0, f"门禁失败: {result.stderr}")
        # 检查通过数（允许不同格式）
        output = result.stdout + result.stderr
        self.assertTrue("通过" in output or "pass" in output.lower() or result.returncode == 0)

    def test_02_tool_threshold_15(self):
        """测试 2：门禁阈值 ≥ 15。"""
        with open(self.check_script, encoding="utf-8") as f:
            content = f.read()
        # 按 docstring 意图断言「阈值 ≥ 15」，而非硬编码字面量 "= 15"：
        # 原实现 assertIn("MIN_TOOLS_DEFAULT = 15") 在阈值随能力扩张升至 24
        # （commit 87787ac：+3 MCP Tools 阈值 21→24）后即永久变红，
        # 而红着的套件会掩盖真实失败（v21.24.1 修正）。
        m = re.search(r"MIN_TOOLS_DEFAULT\s*=\s*(\d+)", content)
        self.assertIsNotNone(m, "check_mcp_server.py 未定义 MIN_TOOLS_DEFAULT")
        self.assertGreaterEqual(int(m.group(1)), 15, f"门禁工具数阈值过低: {m.group(1)}")


class TestNewToolsIntegration(unittest.TestCase):
    """新增工具集成测试（Tier1 只读工具）。"""

    @classmethod
    def setUpClass(cls):
        """测试环境初始化。"""
        cls.root = ROOT

    def _run_tool(self, tool_name, *args):
        """运行工具脚本并返回结果。"""
        script = self.root / "tools" / f"{tool_name}.py"
        if not script.exists():
            self.skipTest(f"工具脚本不存在: {script}")
        result = subprocess.run(
            [sys.executable, str(script), *args],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        return result

    def test_01_check_skill_links(self):
        """测试 1：check_skill_links.py 可运行。"""
        result = self._run_tool("check_skill_links")
        # 允许非零退出码（可能有问题需要报告）
        self.assertIn(result.returncode, [0, 1])

    def test_02_scope_tracker_metrics(self):
        """测试 2：scope_tracker.py metrics 可运行。"""
        result = self._run_tool("scope_tracker", "metrics")
        self.assertIn(result.returncode, [0, 1])

    def test_03_audit_query(self):
        """测试 3：audit.py 可运行（查询模式）。"""
        result = self._run_tool("audit", "--help")
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
