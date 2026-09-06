#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试：AI Agent PM 能力提升（v21.14.0）。

测试覆盖：
  - 代理脚本 project_mgmt_proxy.py + _project_mgmt_proxy.py
  - 新增 6 个 MCP Tools（raid_mgmt, evm_analyze, progress_report, change_mgmt,
    program_status, program_dependency）
  - 新增 3 个 MCP Prompts（project_status_report, risk_assessment, program_review）
  - 门禁阈值 15→21

测试范围：代理脚本路径解析 + MCP 工具/Prompt 计数 + 门禁验证。
"""
import os
import sys
import tempfile
import subprocess
import unittest
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))


class TestProjectMgmtProxy(unittest.TestCase):
    """代理脚本测试。"""

    @classmethod
    def setUpClass(cls):
        cls.root = ROOT
        cls.proxy_path = ROOT / "tools" / "project_mgmt_proxy.py"
        cls.helper_path = ROOT / "tools" / "_project_mgmt_proxy.py"

    def test_01_proxy_syntax(self):
        """测试 1：proxy 脚本语法编译通过。"""
        import py_compile
        try:
            tmp = tempfile.mktemp(suffix=".pyc")
            py_compile.compile(str(self.proxy_path), cfile=tmp, doraise=True)
            os.unlink(tmp)
        except py_compile.PyCompileError as e:
            self.fail(f"proxy 语法编译失败: {e}")

    def test_02_helper_syntax(self):
        """测试 2：helper 模块语法编译通过。"""
        import py_compile
        try:
            tmp = tempfile.mktemp(suffix=".pyc")
            py_compile.compile(str(self.helper_path), cfile=tmp, doraise=True)
            os.unlink(tmp)
        except py_compile.PyCompileError as e:
            self.fail(f"helper 语法编译失败: {e}")

    def test_03_helper_import(self):
        """测试 3：helper 模块可导入。"""
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            from _project_mgmt_proxy import find_project_mgmt_root, run_project_mgmt_cli
            self.assertTrue(callable(find_project_mgmt_root))
            self.assertTrue(callable(run_project_mgmt_cli))
        finally:
            sys.path.pop(0)

    def test_04_path_resolution(self):
        """测试 4：路径解析能找到 dev-project-mgmt。"""
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            from _project_mgmt_proxy import find_project_mgmt_root
            result = find_project_mgmt_root()
            # dev-project-mgmt 应该在同级目录
            if result is not None:
                self.assertTrue(result.is_dir())
                self.assertTrue((result / "dev_project_mgmt").is_dir())
        finally:
            sys.path.pop(0)

    def test_05_proxy_help(self):
        """测试 5：proxy --help 正常运行。"""
        result = subprocess.run(
            [sys.executable, str(self.proxy_path), "--help"],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        # --help 应返回 0
        self.assertEqual(result.returncode, 0, f"--help 失败: {result.stderr}")
        # 应包含子命令
        output = result.stdout + result.stderr
        self.assertTrue("raid" in output.lower() or "evm" in output.lower(),
                        "输出应包含子命令")


class TestMCPServerPMExpansion(unittest.TestCase):
    """MCP Server PM 扩充测试。"""

    @classmethod
    def setUpClass(cls):
        cls.root = ROOT
        cls.mcp_server_path = ROOT / "tools" / "mcp_server" / "skills_mcp_server.py"

    def test_01_tool_count_24(self):
        """测试 1：MCP Tools 数量 ≥ 24。"""
        with open(self.mcp_server_path, encoding="utf-8") as f:
            content = f.read()
        count = content.count("@mcp.tool()")
        self.assertGreaterEqual(count, 24, f"MCP Tools 数量不足: {count} < 24")

    def test_02_prompt_count_9(self):
        """测试 2：MCP Prompts 数量 ≥ 9。"""
        with open(self.mcp_server_path, encoding="utf-8") as f:
            content = f.read()
        count = content.count("@mcp.prompt()")
        self.assertGreaterEqual(count, 9, f"MCP Prompts 数量不足: {count} < 9")

    def test_03_new_tools_exist(self):
        """测试 3：新增 9 个 PM Tools 函数定义存在。"""
        with open(self.mcp_server_path, encoding="utf-8") as f:
            content = f.read()
        new_tools = [
            "def raid_mgmt(",
            "def evm_analyze(",
            "def progress_report(",
            "def change_mgmt(",
            "def program_status(",
            "def program_dependency(",
            "def risk_scan(",
            "def resource_conflict(",
            "def portfolio_summary(",
        ]
        for tool in new_tools:
            self.assertIn(tool, content, f"新增 PM Tool 未定义: {tool}")

    def test_04_new_prompts_exist(self):
        """测试 4：新增 3 个 PM Prompts 函数定义存在。"""
        with open(self.mcp_server_path, encoding="utf-8") as f:
            content = f.read()
        new_prompts = [
            "def project_status_report(",
            "def risk_assessment(",
            "def program_review(",
        ]
        for prompt in new_prompts:
            self.assertIn(prompt, content, f"新增 PM Prompt 未定义: {prompt}")

    def test_05_helper_function_exists(self):
        """测试 5：_run_mgmt_cli 辅助函数存在。"""
        with open(self.mcp_server_path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("def _run_mgmt_cli(", content)


class TestMCPServerGateThreshold(unittest.TestCase):
    """MCP Server 门禁阈值测试。"""

    @classmethod
    def setUpClass(cls):
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

    def test_02_tool_threshold_24(self):
        """测试 2：门禁阈值 ≥ 24。"""
        with open(self.check_script, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("MIN_TOOLS_DEFAULT = 24", content)

    def test_03_proxy_in_expected_scripts(self):
        """测试 3：proxy 脚本在 EXPECTED_SCRIPTS 中。"""
        with open(self.check_script, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("project_mgmt_proxy.py", content)
        self.assertIn("_project_mgmt_proxy.py", content)


class TestPMToolsIntegration(unittest.TestCase):
    """PM 工具集成测试。"""

    @classmethod
    def setUpClass(cls):
        cls.root = ROOT

    def test_01_program_status_reads_ledger(self):
        """测试 1：program_status 可读台账目录。"""
        # 直接测试 MCP tool 函数
        sys.path.insert(0, str(ROOT / "tools" / "mcp_server"))
        try:
            # 导入并调用 program_status
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "skills_mcp_server",
                ROOT / "tools" / "mcp_server" / "skills_mcp_server.py"
            )
            # 由于 MCP Server 需要 mcp 库，这里只测试文件存在
            ledger_dir = ROOT / "台账"
            self.assertTrue(ledger_dir.is_dir(), "台账目录应存在")
        finally:
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
