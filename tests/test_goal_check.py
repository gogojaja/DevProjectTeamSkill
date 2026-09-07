#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_goal_check.py — 目标驱动自主执行·完成度自检工具单元测试

覆盖：SGD 格式校验 / 6 种验证类型 / 范围校验 / 主入口
"""
import os
import sys
import json
import io
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.goal_check import validate_sgd, verify_ac, check_scope, goal_check


class TestValidateSGD(unittest.TestCase):
    """SGD 格式校验测试"""

    def test_valid_minimal(self):
        """最小合法 SGD"""
        sgd = {
            "statement": "完成某任务",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "README.md"}
            ]
        }
        errors = validate_sgd(sgd)
        self.assertEqual(errors, [])

    def test_missing_statement(self):
        """缺少 statement"""
        sgd = {"acceptance_criteria": [{"id": "AC-1", "description": "x", "verify_type": "file_exists"}]}
        errors = validate_sgd(sgd)
        self.assertTrue(any("statement" in e for e in errors))

    def test_missing_acceptance_criteria(self):
        """缺少 acceptance_criteria"""
        sgd = {"statement": "完成某任务"}
        errors = validate_sgd(sgd)
        self.assertTrue(any("acceptance_criteria" in e for e in errors))

    def test_empty_acceptance_criteria(self):
        """空验收标准"""
        sgd = {"statement": "完成某任务", "acceptance_criteria": []}
        errors = validate_sgd(sgd)
        self.assertTrue(any("至少 1 条" in e for e in errors))

    def test_invalid_verify_type(self):
        """非法 verify_type"""
        sgd = {
            "statement": "完成某任务",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "x", "verify_type": "invalid_type"}
            ]
        }
        errors = validate_sgd(sgd)
        self.assertTrue(any("verify_type" in e for e in errors))

    def test_invalid_max_iterations(self):
        """max_iterations 超范围"""
        sgd = {"statement": "完成某任务", "acceptance_criteria": [
            {"id": "AC-1", "description": "x", "verify_type": "file_exists"}
        ], "max_iterations": 100}
        errors = validate_sgd(sgd)
        self.assertTrue(any("max_iterations" in e for e in errors))

    def test_valid_full_sgd(self):
        """完整 SGD（含 scope/constraints/tier3_explicit）"""
        sgd = {
            "statement": "实现 Phase 3 全部工具",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "工具可运行", "verify_type": "command_pass", "verify_target": "python --version"},
                {"id": "AC-2", "description": "测试通过", "verify_type": "test_pass", "verify_target": "tests/test.py"},
            ],
            "constraints": ["不修改已有工具"],
            "scope": {"files": ["tools/*.py"], "dirs": ["tools/"]},
            "max_iterations": 10,
            "tier3_explicit": ["git push"]
        }
        errors = validate_sgd(sgd)
        self.assertEqual(errors, [])


class TestVerifyAC(unittest.TestCase):
    """验收标准验证测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_file_exists_pass(self):
        """file_exists: 文件存在 → PASS"""
        test_file = os.path.join(self.tmpdir, "test.txt")
        with io.open(test_file, "w", encoding="utf-8") as f:
            f.write("hello")
        ac = {"verify_type": "file_exists", "verify_target": os.path.basename(test_file)}
        result = verify_ac(ac, self.tmpdir)
        self.assertEqual(result["status"], "PASS")

    def test_file_exists_fail(self):
        """file_exists: 文件不存在 → FAIL"""
        ac = {"verify_type": "file_exists", "verify_target": "nonexistent.txt"}
        result = verify_ac(ac, self.tmpdir)
        self.assertEqual(result["status"], "FAIL")

    def test_file_contains_pass(self):
        """file_contains: 包含内容 → PASS"""
        test_file = os.path.join(self.tmpdir, "test.txt")
        with io.open(test_file, "w", encoding="utf-8") as f:
            f.write("hello world")
        ac = {"verify_type": "file_contains", "verify_target": os.path.basename(test_file), "verify_arg": "world"}
        result = verify_ac(ac, self.tmpdir)
        self.assertEqual(result["status"], "PASS")

    def test_file_contains_fail(self):
        """file_contains: 不包含内容 → FAIL"""
        test_file = os.path.join(self.tmpdir, "test.txt")
        with io.open(test_file, "w", encoding="utf-8") as f:
            f.write("hello")
        ac = {"verify_type": "file_contains", "verify_target": os.path.basename(test_file), "verify_arg": "missing"}
        result = verify_ac(ac, self.tmpdir)
        self.assertEqual(result["status"], "FAIL")

    def test_command_pass(self):
        """command_pass: 命令成功 → PASS"""
        ac = {"verify_type": "command_pass", "verify_target": "python --version"}
        result = verify_ac(ac, self.tmpdir)
        self.assertEqual(result["status"], "PASS")

    def test_command_fail(self):
        """command_pass: 命令失败 → FAIL"""
        ac = {"verify_type": "command_pass", "verify_target": sys.executable + " -c \"import sys; sys.exit(1)\""}
        result = verify_ac(ac, self.tmpdir)
        self.assertEqual(result["status"], "FAIL")

    def test_manual(self):
        """manual: 始终返回 MANUAL"""
        ac = {"verify_type": "manual", "description": "需人工确认"}
        result = verify_ac(ac, self.tmpdir)
        self.assertEqual(result["status"], "MANUAL")

    def test_count_ge_pass(self):
        """count_ge: 数量达标 → PASS"""
        for i in range(3):
            with io.open(os.path.join(self.tmpdir, "file_%d.py" % i), "w") as f:
                f.write("")
        ac = {"verify_type": "count_ge", "verify_target": "*.py", "verify_arg": "3"}
        result = verify_ac(ac, self.tmpdir)
        self.assertEqual(result["status"], "PASS")

    def test_count_ge_fail(self):
        """count_ge: 数量不达标 → FAIL"""
        ac = {"verify_type": "count_ge", "verify_target": "*.py", "verify_arg": "5"}
        result = verify_ac(ac, self.tmpdir)
        self.assertEqual(result["status"], "FAIL")


class TestCheckScope(unittest.TestCase):
    """范围校验测试"""

    def test_no_scope(self):
        """无 scope 定义 → 不限制"""
        self.assertTrue(check_scope("any/path.py", {}))

    def test_file_in_scope(self):
        """文件在 scope 内"""
        sgd = {"scope": {"files": ["tools/*.py"], "dirs": ["tests/"]}}
        self.assertTrue(check_scope("tools/goal_check.py", sgd))
        self.assertTrue(check_scope("tests/test_goal.py", sgd))

    def test_file_out_of_scope(self):
        """文件不在 scope 内"""
        sgd = {"scope": {"files": ["tools/*.py"]}}
        self.assertFalse(check_scope("docs/readme.md", sgd))


class TestGoalCheckMain(unittest.TestCase):
    """主入口测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_validate_only(self):
        """--validate 仅校验格式"""
        sgd_path = os.path.join(self.tmpdir, "goal.json")
        sgd = {
            "statement": "测试任务目标",  # >= 5 字符
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "README.md"}
            ]
        }
        with io.open(sgd_path, "w", encoding="utf-8") as f:
            json.dump(sgd, f, ensure_ascii=False)
        result = goal_check(sgd_path, validate_only=True)
        self.assertTrue(result["valid"])

    def test_goal_check_with_real_ac(self):
        """实际验证 AC"""
        # 创建测试文件（使用绝对路径）
        test_file = os.path.join(self.tmpdir, "hello.txt")
        with io.open(test_file, "w", encoding="utf-8") as f:
            f.write("hello world")

        sgd_path = os.path.join(self.tmpdir, "goal.json")
        sgd = {
            "statement": "验证文件存在目标",  # >= 5 字符
            "acceptance_criteria": [
                {"id": "AC-1", "description": "hello.txt 存在", "verify_type": "file_exists", "verify_target": test_file},
                {"id": "AC-2", "description": "包含 hello", "verify_type": "file_contains", "verify_target": test_file, "verify_arg": "hello"},
            ]
        }
        with io.open(sgd_path, "w", encoding="utf-8") as f:
            json.dump(sgd, f, ensure_ascii=False)

        output_path = os.path.join(self.tmpdir, "report.csv")
        result = goal_check(sgd_path, output_path=output_path)
        self.assertEqual(result["pass"], 2)
        self.assertEqual(result["fail"], 0)
        self.assertEqual(result["conclusion"], "全部通过")


if __name__ == "__main__":
    unittest.main()
