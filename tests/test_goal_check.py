#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_goal_check.py — 目标驱动自主执行·完成度自检工具单元测试

覆盖：SGD 格式校验 / 6 种验证类型 / 范围校验 / 主入口
      v1.1 补强：台账持久化 / 约束验证 / scope 读写分离 / 目标变更 / 错误恢复校验
"""
import os
import sys
import json
import io
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.goal_check import (
    validate_sgd, verify_ac, check_scope, goal_check,
    verify_constraints, save_goal, load_goal, update_status,
    amend_goal, close_goal, _sgd_hash, _load_ledger, _save_ledger,
    LEDGER_PATH,
)


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


class TestValidateSGDv11(unittest.TestCase):
    """v1.1 SGD 格式校验增强测试"""

    def test_valid_v11_scope_read_write(self):
        """v1.1 scope 读写分离格式合法"""
        sgd = {
            "statement": "测试读写分离",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "README.md"}
            ],
            "scope": {
                "write_files": ["tools/*.py"],
                "write_dirs": ["tools/"],
                "read_files": ["docs/*.md"],
                "read_dirs": ["docs/", "references/"]
            }
        }
        errors = validate_sgd(sgd)
        self.assertEqual(errors, [])

    def test_valid_v11_constraints_verifiable(self):
        """v1.1 可机器验证约束格式合法"""
        sgd = {
            "statement": "测试可验证约束",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "README.md"}
            ],
            "constraints": [
                {"type": "file_not_modified", "target": "tools/existing.py", "description": "不修改已有工具"},
                {"type": "file_not_created", "target": "tools/new_forbidden.py"},
                "纯文字约束也允许"  # v1.0 兼容
            ]
        }
        errors = validate_sgd(sgd)
        self.assertEqual(errors, [])

    def test_invalid_v11_constraint_type(self):
        """v1.1 非法约束类型"""
        sgd = {
            "statement": "测试非法约束",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "x"}
            ],
            "constraints": [{"type": "invalid_type", "target": "x"}]
        }
        errors = validate_sgd(sgd)
        self.assertTrue(any("constraint" in e for e in errors))

    def test_valid_v11_error_recovery(self):
        """v1.1 错误恢复策略格式合法"""
        sgd = {
            "statement": "测试错误恢复",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "x"}
            ],
            "error_recovery": {
                "max_retries_per_step": 2,
                "on_circuit_break": "skip_and_continue",
                "on_max_iterations": "abort_goal"
            }
        }
        errors = validate_sgd(sgd)
        self.assertEqual(errors, [])

    def test_invalid_error_recovery_break(self):
        """v1.1 非法 on_circuit_break"""
        sgd = {
            "statement": "测试非法恢复策略",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "x"}
            ],
            "error_recovery": {"on_circuit_break": "invalid_action"}
        }
        errors = validate_sgd(sgd)
        self.assertTrue(any("on_circuit_break" in e for e in errors))

    def test_invalid_error_recovery_max(self):
        """v1.1 非法 on_max_iterations"""
        sgd = {
            "statement": "测试非法恢复策略",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "x"}
            ],
            "error_recovery": {"on_max_iterations": "invalid_action"}
        }
        errors = validate_sgd(sgd)
        self.assertTrue(any("on_max_iterations" in e for e in errors))


class TestVerifyConstraints(unittest.TestCase):
    """v1.1 约束验证测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_file_not_modified_pass(self):
        """file_not_modified: 文件存在 → PASS"""
        test_file = os.path.join(self.tmpdir, "existing.py")
        with io.open(test_file, "w") as f:
            f.write("# original")
        sgd = {"constraints": [{"type": "file_not_modified", "target": "existing.py"}]}
        results = verify_constraints(sgd, self.tmpdir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "PASS")

    def test_file_not_modified_fail(self):
        """file_not_modified: 文件不存在 → FAIL"""
        sgd = {"constraints": [{"type": "file_not_modified", "target": "deleted.py"}]}
        results = verify_constraints(sgd, self.tmpdir)
        self.assertEqual(results[0]["status"], "FAIL")

    def test_file_not_created_pass(self):
        """file_not_created: 文件不存在 → PASS"""
        sgd = {"constraints": [{"type": "file_not_created", "target": "forbidden.py"}]}
        results = verify_constraints(sgd, self.tmpdir)
        self.assertEqual(results[0]["status"], "PASS")

    def test_file_not_created_fail(self):
        """file_not_created: 文件已存在 → FAIL"""
        test_file = os.path.join(self.tmpdir, "forbidden.py")
        with io.open(test_file, "w") as f:
            f.write("# should not exist")
        sgd = {"constraints": [{"type": "file_not_created", "target": "forbidden.py"}]}
        results = verify_constraints(sgd, self.tmpdir)
        self.assertEqual(results[0]["status"], "FAIL")

    def test_text_only_constraint_skip(self):
        """纯文字约束 → SKIP（不可机器验证）"""
        sgd = {"constraints": ["不修改已有工具"]}
        results = verify_constraints(sgd, self.tmpdir)
        self.assertEqual(results[0]["status"], "SKIP")
        self.assertEqual(results[0]["type"], "text_only")

    def test_mixed_constraints(self):
        """混合约束：可验证 + 纯文字"""
        test_file = os.path.join(self.tmpdir, "keep.py")
        with io.open(test_file, "w") as f:
            f.write("# keep")
        sgd = {"constraints": [
            {"type": "file_not_modified", "target": "keep.py"},
            "纯文字声明",
            {"type": "file_not_created", "target": "nope.py"},
        ]}
        results = verify_constraints(sgd, self.tmpdir)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["status"], "PASS")
        self.assertEqual(results[1]["status"], "SKIP")
        self.assertEqual(results[2]["status"], "PASS")


class TestScopeReadWrite(unittest.TestCase):
    """v1.1 scope 读写分离测试"""

    def test_write_scope_v11(self):
        """v1.1 write_files/write_dirs 写范围校验"""
        sgd = {"scope": {"write_files": ["tools/*.py"], "write_dirs": ["tests/"]}}
        self.assertTrue(check_scope("tools/goal_check.py", sgd, mode="write"))
        self.assertTrue(check_scope("tests/test_goal.py", sgd, mode="write"))
        self.assertFalse(check_scope("docs/readme.md", sgd, mode="write"))

    def test_read_scope_v11(self):
        """v1.1 read_files/read_dirs 读范围校验"""
        sgd = {"scope": {"read_files": ["docs/*.md"], "read_dirs": ["references/"]}}
        self.assertTrue(check_scope("docs/plan.md", sgd, mode="read"))
        self.assertTrue(check_scope("references/standard.md", sgd, mode="read"))
        self.assertFalse(check_scope("tools/code.py", sgd, mode="read"))

    def test_read_scope_unlimited_when_not_specified(self):
        """未指定读范围时不限制读取"""
        sgd = {"scope": {"write_files": ["tools/*.py"]}}
        self.assertTrue(check_scope("any/file.md", sgd, mode="read"))

    def test_v10_compatible_write(self):
        """v1.0 files/dirs 向后兼容写范围"""
        sgd = {"scope": {"files": ["tools/*.py"], "dirs": ["tools/"]}}
        self.assertTrue(check_scope("tools/goal_check.py", sgd, mode="write"))
        self.assertFalse(check_scope("docs/readme.md", sgd, mode="write"))


class TestLedgerPersistence(unittest.TestCase):
    """v1.1 台账持久化测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # 临时覆盖 LEDGER_PATH
        import tools.goal_check as gc
        self._orig_ledger = gc.LEDGER_PATH
        gc.LEDGER_PATH = os.path.join(self.tmpdir, "test_ledger.json")

    def tearDown(self):
        import tools.goal_check as gc
        gc.LEDGER_PATH = self._orig_ledger

    def _make_sgd(self):
        return {
            "statement": "持久化测试目标",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "README.md"}
            ]
        }

    def test_save_goal(self):
        """save_goal: 保存到台账"""
        sgd = self._make_sgd()
        result = save_goal(sgd)
        self.assertTrue(result["saved"])
        self.assertIn("goal_id", result)
        # 验证台账文件存在
        import tools.goal_check as gc
        self.assertTrue(os.path.exists(gc.LEDGER_PATH))

    def test_save_and_load_goal(self):
        """save → load 往返一致"""
        sgd = self._make_sgd()
        save_result = save_goal(sgd)
        goal_id = save_result["goal_id"]

        loaded = load_goal(goal_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["goal_id"], goal_id)
        self.assertEqual(loaded["sgd"]["statement"], "持久化测试目标")
        self.assertEqual(loaded["status"], "active")
        self.assertIn("AC-1", loaded["ac_status"])

    def test_update_status(self):
        """update_status: 更新 AC 状态 + 迭代计数"""
        sgd = self._make_sgd()
        save_result = save_goal(sgd)
        goal_id = save_result["goal_id"]

        result = update_status(goal_id, "AC-1", "PASS", iteration=3)
        self.assertTrue(result["updated"])

        loaded = load_goal(goal_id)
        self.assertEqual(loaded["ac_status"]["AC-1"], "PASS")
        self.assertEqual(loaded["iteration"], 3)

    def test_close_goal(self):
        """close_goal: 关闭后移入 closed_goals"""
        sgd = self._make_sgd()
        save_result = save_goal(sgd)
        goal_id = save_result["goal_id"]

        result = close_goal(goal_id)
        self.assertTrue(result["closed"])

        import tools.goal_check as gc
        ledger = _load_ledger()
        self.assertEqual(len(ledger["active_goals"]), 0)
        self.assertEqual(len(ledger["closed_goals"]), 1)
        self.assertEqual(ledger["closed_goals"][0]["status"], "completed")

    def test_save_invalid_sgd(self):
        """save_goal: 非法 SGD 不保存"""
        sgd = {"statement": "短"}  # 缺少 acceptance_criteria
        result = save_goal(sgd)
        self.assertFalse(result["saved"])
        self.assertIn("errors", result)


class TestAmendGoal(unittest.TestCase):
    """v1.1 目标变更机制测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        import tools.goal_check as gc
        self._orig_ledger = gc.LEDGER_PATH
        gc.LEDGER_PATH = os.path.join(self.tmpdir, "test_ledger.json")

    def tearDown(self):
        import tools.goal_check as gc
        gc.LEDGER_PATH = self._orig_ledger

    def test_amend_goal(self):
        """amend_goal: 变更目标保留历史"""
        sgd = {
            "statement": "原始目标描述测试",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "README.md"}
            ]
        }
        save_result = save_goal(sgd)
        goal_id = save_result["goal_id"]

        new_sgd = {
            "statement": "变更后新目标描述",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "README.md"},
                {"id": "AC-2", "description": "新增验收标准", "verify_type": "manual", "verify_target": "人工确认"}
            ]
        }
        amend_result = amend_goal(goal_id, new_sgd, "用户要求增加功能")
        self.assertTrue(amend_result["amended"])
        self.assertEqual(amend_result["amendment_seq"], 1)

        loaded = load_goal(goal_id)
        self.assertEqual(loaded["sgd"]["statement"], "变更后新目标描述")
        self.assertEqual(len(loaded["amendment_history"]), 1)
        self.assertEqual(loaded["amendment_history"][0]["reason"], "用户要求增加功能")
        # 新增 AC 自动 PENDING
        self.assertEqual(loaded["ac_status"]["AC-2"], "PENDING")

    def test_amend_nonexistent_goal(self):
        """amend_goal: 不存在的目标"""
        new_sgd = self._make_sgd()
        result = amend_goal("G-999", new_sgd, "test")
        self.assertFalse(result["amended"])

    def _make_sgd(self):
        return {
            "statement": "临时目标用于变更测试",
            "acceptance_criteria": [
                {"id": "AC-1", "description": "文件存在", "verify_type": "file_exists", "verify_target": "x"}
            ]
        }


class TestSGDHash(unittest.TestCase):
    """v1.1 SGD 内容哈希测试"""

    def test_deterministic_hash(self):
        """相同 SGD 哈希值一致"""
        sgd = {"statement": "测试", "acceptance_criteria": []}
        h1 = _sgd_hash(sgd)
        h2 = _sgd_hash(sgd)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 10)

    def test_different_sgd_different_hash(self):
        """不同 SGD 哈希值不同"""
        sgd1 = {"statement": "目标A"}
        sgd2 = {"statement": "目标B"}
        self.assertNotEqual(_sgd_hash(sgd1), _sgd_hash(sgd2))


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
