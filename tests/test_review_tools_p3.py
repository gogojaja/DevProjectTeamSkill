#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_review_tools_p3.py — Phase 3 评审工具单元测试

覆盖 T-02 xlsx_diff / T-10 arch_compliance / T-12 env_compare / T-13 review_metrics
"""
import os
import sys
import json
import csv
import io
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.arch_compliance import _extract_adr_constraints, CONSTRAINT_PATTERNS
from tools.env_compare import _load_env_file, _assess_risk, env_compare
from tools.review_metrics import _scan_review_reports, review_metrics


class TestArchCompliance(unittest.TestCase):
    """T-10 架构合规检查器测试"""

    def test_constraint_patterns_defined(self):
        """T-10: 约束模式库非空"""
        self.assertGreater(len(CONSTRAINT_PATTERNS), 0)

    def test_extract_from_empty_dir(self):
        """T-10: 空目录返回空列表"""
        tmpdir = tempfile.mkdtemp()
        constraints = _extract_adr_constraints(tmpdir)
        self.assertEqual(constraints, [])

    def test_extract_from_nonexistent_dir(self):
        """T-10: 不存在的目录返回空列表"""
        constraints = _extract_adr_constraints("/nonexistent/path")
        self.assertEqual(constraints, [])


class TestEnvCompare(unittest.TestCase):
    """T-12 投产环境比对器测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_load_json_config(self):
        """T-12: 加载 JSON 配置"""
        config_path = os.path.join(self.tmpdir, "env.json")
        with io.open(config_path, "w", encoding="utf-8") as f:
            json.dump({"DB_HOST": "localhost", "DB_PORT": "5432"}, f)
        data = _load_env_file(config_path)
        self.assertEqual(data["DB_HOST"], "localhost")
        self.assertEqual(data["DB_PORT"], "5432")

    def test_load_env_format(self):
        """T-12: 加载 .env 格式"""
        env_path = os.path.join(self.tmpdir, ".env")
        with io.open(env_path, "w", encoding="utf-8") as f:
            f.write("DB_HOST=localhost\nDB_PORT=5432\n# comment\n")
        data = _load_env_file(env_path)
        self.assertEqual(data["DB_HOST"], "localhost")
        self.assertEqual(len(data), 2)

    def test_risk_assessment(self):
        """T-12: 风险评估正确"""
        self.assertTrue(_assess_risk("DB_PASSWORD").startswith("高"))
        self.assertTrue(_assess_risk("DB_HOST").startswith("中"))
        self.assertTrue(_assess_risk("LOG_LEVEL").startswith("低"))

    def test_env_compare_two_envs(self):
        """T-12: 两环境比对输出差异"""
        dev_path = os.path.join(self.tmpdir, "dev.json")
        prod_path = os.path.join(self.tmpdir, "prod.json")
        with io.open(dev_path, "w", encoding="utf-8") as f:
            json.dump({"DB_HOST": "localhost", "DB_PORT": "5432", "DEBUG": "true"}, f)
        with io.open(prod_path, "w", encoding="utf-8") as f:
            json.dump({"DB_HOST": "prod-server", "DB_PORT": "5432", "DEBUG": "false"}, f)

        result = env_compare(
            {"dev": dev_path, "prod": prod_path},
            output_path=os.path.join(self.tmpdir, "diff.csv")
        )
        self.assertEqual(result["diff_count"], 2)  # DB_HOST + DEBUG
        self.assertTrue(os.path.exists(result["output_path"]))


class TestReviewMetrics(unittest.TestCase):
    """T-13 评审效能度量器测试"""

    def test_scan_reviews_empty_dir(self):
        """T-13: 空目录返回零统计"""
        tmpdir = tempfile.mkdtemp()
        stats = _scan_review_reports(None, tmpdir)
        self.assertEqual(stats["review_count"], 0)
        self.assertEqual(stats["defect_count"], 0)

    def test_scan_reviews_nonexistent_dir(self):
        """T-13: 不存在的目录返回零统计"""
        stats = _scan_review_reports(None, "/nonexistent/path")
        self.assertEqual(stats["review_count"], 0)

    def test_metrics_output(self):
        """T-13: 度量结果输出 CSV"""
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "metrics.csv")
        result = review_metrics(output_path=output_path)
        self.assertTrue(os.path.exists(output_path))
        self.assertIn("review_count", result)


class TestXlsxDiff(unittest.TestCase):
    """T-02 Excel 版本对比器测试"""

    def test_import(self):
        """T-02: 模块可导入"""
        from tools.xlsx_diff import xlsx_diff
        self.assertTrue(callable(xlsx_diff))

    def test_docx_extract_import(self):
        """T-07: 模块可导入"""
        from tools.docx_structure_extract import extract_structure
        self.assertTrue(callable(extract_structure))


if __name__ == "__main__":
    unittest.main()
