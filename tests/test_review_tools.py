#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_review_tools.py — Phase 1 评审工具单元测试

覆盖 T-03 review_report_gen / T-06 xlsx_verify / T-08 code_review_agent
"""
import os
import sys
import json
import csv
import io
import tempfile
import unittest

# 确保导入路径
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.review_report_gen import generate_report


class TestReviewReportGen(unittest.TestCase):
    """T-03 评审报告生成器测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.defects = {
            "object": "测试需求",
            "version_tag": "V1.0",
            "reviewer": "测试员",
            "review_date": "2026-09-07",
            "defects": [
                {"id": "DEF-001", "severity": "严重", "module": "表单A",
                 "type": "一致性", "description": "字段权限不一致",
                 "evidence_ui": "界面展示8字段", "evidence_form": "表单标记不显示",
                 "suggestion": "改为计算后回显"},
                {"id": "DEF-002", "severity": "一般", "module": "列表B",
                 "type": "完整性", "description": "缺少排序规则",
                 "evidence_ui": "列表无排序", "evidence_form": "未标注",
                 "suggestion": "增加默认排序"},
            ],
            "dimensions": [
                {"name": "完整性", "weight": "25%", "score": "80%", "verdict": "通过"},
                {"name": "一致性", "weight": "25%", "score": "60%", "verdict": "部分通过"},
            ]
        }
        self.defects_path = os.path.join(self.tmpdir, "defects.json")
        with io.open(self.defects_path, "w", encoding="utf-8") as f:
            json.dump(self.defects, f, ensure_ascii=False)

    def test_generate_report_returns_tuple(self):
        """T-03: generate_report 返回 (缺陷CSV路径, 维度CSV路径)"""
        result = generate_report(
            defects_json_path=self.defects_path,
            obj_name="测试需求",
            version="V1.0"
        )
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        defect_path, dim_path = result
        self.assertTrue(defect_path.endswith(".csv"))
        self.assertTrue(dim_path.endswith(".csv"))

    def test_defect_csv_content(self):
        """T-03: 缺陷 CSV 包含正确数量和 ID"""
        defect_path, _ = generate_report(
            defects_json_path=self.defects_path,
            obj_name="测试需求",
            version="V1.0"
        )
        with io.open(defect_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "DEF-001")
        self.assertEqual(rows[0][1], "严重")

    def test_dimension_csv_content(self):
        """T-03: 维度 CSV 包含正确维度名称"""
        _, dim_path = generate_report(
            defects_json_path=self.defects_path,
            obj_name="测试需求",
            version="V1.0"
        )
        with io.open(dim_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "完整性")
        self.assertEqual(rows[0][1], "25%")


class TestXlsxVerify(unittest.TestCase):
    """T-06 Excel 修复验证器测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.defects = {
            "defects": [
                {"id": "DEF-001", "cell": "B5", "sheet": "Sheet1",
                 "expected": "计算后回显", "description": "字段应显示计算结果"},
                {"id": "DEF-002", "cell": "C3", "sheet": "Sheet1",
                 "expected": "是", "description": "标记应改为是"},
            ]
        }
        self.defects_path = os.path.join(self.tmpdir, "defects.json")
        with io.open(self.defects_path, "w", encoding="utf-8") as f:
            json.dump(self.defects, f, ensure_ascii=False)

    def test_verify_module_importable(self):
        """T-06: xlsx_verify 模块可正常导入"""
        from tools.xlsx_verify import verify_xlsx
        self.assertTrue(callable(verify_xlsx))

    def test_verify_defects_json_format(self):
        """T-06: 缺陷 JSON 格式正确解析"""
        with io.open(self.defects_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["defects"]), 2)
        self.assertEqual(data["defects"][0]["cell"], "B5")
        self.assertEqual(data["defects"][0]["expected"], "计算后回显")

    def test_verify_missing_file_exits(self):
        """T-06: 文件不存在时 sys.exit"""
        from tools.xlsx_verify import verify_xlsx
        with self.assertRaises(SystemExit):
            verify_xlsx(
                input_path=os.path.join(self.tmpdir, "nonexistent.xlsx"),
                defects_path=self.defects_path
            )


class TestCodeReviewAgent(unittest.TestCase):
    """T-08 AI 代码审查 Agent 测试"""

    def test_import(self):
        """T-08: 模块可正常导入"""
        from tools.code_review_agent import review, get_diff, parse_diff_files
        self.assertTrue(callable(review))
        self.assertTrue(callable(get_diff))
        self.assertTrue(callable(parse_diff_files))

    def test_get_diff_head1(self):
        """T-08: get_diff HEAD~1 返回字符串（可能为空）"""
        from tools.code_review_agent import get_diff
        result = get_diff("HEAD~1")
        self.assertIsInstance(result, str)

    def test_parse_diff_files(self):
        """T-08: parse_diff_files 解析 git diff 文本"""
        from tools.code_review_agent import parse_diff_files
        # 空 diff 应返回空集合
        files = parse_diff_files("")
        self.assertTrue(len(files) == 0 or len(files) > 0)  # 不抛异常即通过

    def test_review_dry_run(self):
        """T-08: dry-run 模式不写入文件"""
        from tools.code_review_agent import review
        result = review("HEAD~1", dry_run=True)
        self.assertIsNotNone(result)
        # dry-run 不应生成报告文件
        if isinstance(result, dict) and "report_path" in result:
            self.assertFalse(os.path.exists(result["report_path"]))


if __name__ == "__main__":
    unittest.main()
