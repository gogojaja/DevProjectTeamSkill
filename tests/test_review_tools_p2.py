#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_review_tools_p2.py — Phase 2 评审工具单元测试

覆盖 T-04 defect_ledger_sync / T-09 dep_vuln_scan / T-11 req_quality
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

from tools.defect_ledger_sync import sync_defects
from tools.dep_vuln_scan import parse_requirements, parse_pyproject, scan_offline
from tools.req_quality import check_ambiguous, check_completeness, check_testability, DEFAULT_RULES


class TestDefectLedgerSync(unittest.TestCase):
    """T-04 缺陷台账同步器测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.defects = {
            "defects": [
                {"id": "DEF-001", "severity": "严重", "module": "表单A",
                 "type": "一致性", "description": "字段权限不一致", "suggestion": "改为计算后回显"},
                {"id": "DEF-002", "severity": "一般", "module": "列表B",
                 "type": "完整性", "description": "缺少排序规则", "suggestion": "增加默认排序"},
            ]
        }
        self.defects_path = os.path.join(self.tmpdir, "defects.json")
        with io.open(self.defects_path, "w", encoding="utf-8") as f:
            json.dump(self.defects, f, ensure_ascii=False)

    def test_sync_new_defects(self):
        """T-04: 首次同步新增缺陷到台账"""
        result = sync_defects(self.defects_path, self.tmpdir, round_num=1)
        self.assertEqual(result["added"], 2)
        self.assertEqual(result["updated"], 0)
        self.assertTrue(os.path.exists(result["ledger_path"]))

    def test_sync_update_existing(self):
        """T-04: 再次同步更新已有缺陷"""
        sync_defects(self.defects_path, self.tmpdir, round_num=1)
        # 第二轮同步
        result = sync_defects(self.defects_path, self.tmpdir, round_num=2)
        self.assertEqual(result["updated"], 2)
        self.assertEqual(result["added"], 0)

    def test_ledger_csv_format(self):
        """T-04: 台账 CSV 格式正确（UTF-8 BOM + 表头）"""
        result = sync_defects(self.defects_path, self.tmpdir, round_num=1)
        with io.open(result["ledger_path"], "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
        self.assertEqual(header[0], "缺陷编号")
        self.assertEqual(header[7], "状态")

    def test_sync_missing_file(self):
        """T-04: 文件不存在时 sys.exit"""
        with self.assertRaises(SystemExit):
            sync_defects(os.path.join(self.tmpdir, "nonexistent.json"), self.tmpdir, 1)


class TestDepVulnScan(unittest.TestCase):
    """T-09 依赖漏洞扫描器测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_parse_requirements(self):
        """T-09: 解析 requirements.txt 格式"""
        req_path = os.path.join(self.tmpdir, "requirements.txt")
        with io.open(req_path, "w", encoding="utf-8") as f:
            f.write("openpyxl==1.12.0\nrequests>=2.28.0\n# comment\npyyaml\n")
        deps = parse_requirements(req_path)
        self.assertEqual(len(deps), 3)
        self.assertEqual(deps[0], ("openpyxl", "1.12.0"))
        self.assertEqual(deps[1][0], "requests")

    def test_parse_requirements_empty(self):
        """T-09: 空文件返回空列表"""
        deps = parse_requirements(os.path.join(self.tmpdir, "nonexistent.txt"))
        self.assertEqual(deps, [])

    def test_scan_offline(self):
        """T-09: 离线模式标记待扫描"""
        deps = [("flask", "2.0.0"), ("requests", "2.28.0")]
        results = scan_offline(deps)
        self.assertEqual(len(results), 2)
        self.assertIn("待扫描", results[0]["cve_id"])

    def test_parse_pyproject(self):
        """T-09: 解析 pyproject.toml dependencies"""
        pp_path = os.path.join(self.tmpdir, "pyproject.toml")
        with io.open(pp_path, "w", encoding="utf-8") as f:
            f.write('[project]\nname = "test"\ndependencies = [\n  "flask>=2.0.0",\n  "requests",\n]\n')
        deps = parse_pyproject(pp_path)
        self.assertGreaterEqual(len(deps), 1)


class TestReqQuality(unittest.TestCase):
    """T-11 需求质量自动检查器测试"""

    def test_ambiguous_terms_detection(self):
        """T-11: 检测歧义词"""
        count, found = check_ambiguous("用户应快速登录系统", DEFAULT_RULES)
        self.assertGreaterEqual(count, 1)
        self.assertTrue(any("快速" in f for f in found))

    def test_no_ambiguous_terms(self):
        """T-11: 无歧义词"""
        count, found = check_ambiguous("登录时间小于3秒", DEFAULT_RULES)
        self.assertEqual(count, 0)

    def test_completeness_full(self):
        """T-11: 完整需求得满分"""
        req = {"acceptance": "登录<3s", "boundary": "超时提示", "priority": "高", "dependencies": "认证模块"}
        score, missing = check_completeness(req, DEFAULT_RULES)
        self.assertEqual(score, 100)
        self.assertEqual(len(missing), 0)

    def test_completeness_empty(self):
        """T-11: 缺失全部字段得零分"""
        req = {"acceptance": "", "boundary": "", "priority": "", "dependencies": ""}
        score, missing = check_completeness(req, DEFAULT_RULES)
        self.assertEqual(score, 0)
        self.assertEqual(len(missing), 4)

    def test_testability_high(self):
        """T-11: 有量化指标可测性高"""
        score = check_testability("登录时间<3秒，成功率>=99%，超时5次锁定", DEFAULT_RULES)
        self.assertGreaterEqual(score, 90)

    def test_testability_low(self):
        """T-11: 纯定性描述可测性低"""
        score = check_testability("系统应该支持快速登录", DEFAULT_RULES)
        self.assertLessEqual(score, 30)


if __name__ == "__main__":
    unittest.main()
