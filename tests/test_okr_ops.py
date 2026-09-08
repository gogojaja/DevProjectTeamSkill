#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_okr_ops.py — OKR 战略对齐工具单测（okr-strategy 独立部署 A-6）

轻量断言式：python tests/test_okr_ops.py（无第三方依赖）
覆盖：create 创建 / update 进度 / score 评分分级(失败/未达预期/理想/超额/过于保守)+越界+未找到 /
      map 对齐映射(已对齐/弱对齐)+越界 / audit 孤儿项目 rc1 / dashboard。
台账隔离：patch 模块级 LEDGER + OKR_FILE/ALIGN_FILE 到 tempfile。
"""
import os
import sys
import csv
import io
import argparse
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import okr_ops as ok


def _patch(d):
    ok.LEDGER = d
    ok.OKR_FILE = os.path.join(d, "46_OKR登记.csv")
    ok.ALIGN_FILE = os.path.join(d, "47_战略对齐矩阵.csv")


def _tmp():
    d = tempfile.mkdtemp()
    _patch(d)
    return d


def _rows(path):
    with io.open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _create(oid_obj="提升市场份额"):
    return ok.cmd_create(argparse.Namespace(level="org", objective=oid_obj, kr="市占率达15%",
                                            owner="VP-Sales", period="Q1", target="15%"))


def test_create():
    d = _tmp()
    assert _create() == 0
    row = _rows(ok.OKR_FILE)[-1]
    assert row["编号"] == "OKR-001" and row["层级"] == "org"
    assert row["状态"] == "进行中" and row["完成%"] == "0"


def test_update_progress():
    d = _tmp()
    _create()
    assert ok.cmd_update(argparse.Namespace(id="OKR-001", progress=65, actual="")) == 0
    assert _rows(ok.OKR_FILE)[-1]["完成%"] == "65"
    assert ok.cmd_update(argparse.Namespace(id="OKR-999", progress=10, actual="")) == 1


def test_score_grades():
    """评分分级：<0.3失败 / <0.6未达预期 / ≤0.7理想 / ≤0.9超额 / else过于保守。"""
    cases = [(0.2, "失败"), (0.5, "未达预期"), (0.7, "理想"), (0.8, "超额"), (0.95, "过于保守")]
    for score, expect in cases:
        d = _tmp()
        _create()
        assert ok.cmd_score(argparse.Namespace(id="OKR-001", score=score)) == 0
        assert _rows(ok.OKR_FILE)[-1]["状态"] == expect, f"score={score} 应={expect}"


def test_score_out_of_range_and_notfound():
    d = _tmp()
    _create()
    assert ok.cmd_score(argparse.Namespace(id="OKR-001", score=1.5)) == 1  # 越界
    assert ok.cmd_score(argparse.Namespace(id="OKR-999", score=0.7)) == 1  # 未找到


def test_map_aligned_and_weak():
    d = _tmp()
    assert ok.cmd_map(argparse.Namespace(project="项目X", theme="数字化转型", score=4)) == 0
    row = _rows(ok.ALIGN_FILE)[-1]
    assert row["编号"] == "AL-001" and row["对齐度评分"] == "4"
    assert ok.cmd_map(argparse.Namespace(project="项目Y", theme="数字化转型", score=2)) == 0
    assert ok.cmd_map(argparse.Namespace(project="项目Z", theme="数字化转型", score=6)) == 1  # 越界


def test_audit_orphan_rc1():
    """孤儿项目（对齐度评分=0）→ audit rc1；已对齐 → rc0。"""
    d = _tmp()
    ok.cmd_map(argparse.Namespace(project="项目X", theme="数字化转型", score=4))
    assert ok.cmd_audit(argparse.Namespace()) == 0  # 已对齐无孤儿
    # 手工写入孤儿行（评分0，map 强制 1~5 无法产出，模拟历史脏数据）
    d2 = _tmp()
    with io.open(ok.ALIGN_FILE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["编号", "项目名称", "战略主题", "对齐度评分", "映射日期", "确认状态"])
        w.writerow(["AL-001", "孤儿项目", "", "0", "2026-09-08", "待确认"])
    assert ok.cmd_audit(argparse.Namespace()) == 1


def test_dashboard():
    d = _tmp()
    _create()
    ok.cmd_map(argparse.Namespace(project="项目X", theme="数字化转型", score=4))
    assert ok.cmd_dashboard(argparse.Namespace()) == 0


if __name__ == "__main__":
    test_create()
    test_update_progress()
    test_score_grades()
    test_score_out_of_range_and_notfound()
    test_map_aligned_and_weak()
    test_audit_orphan_rc1()
    test_dashboard()
    print("ALL TESTS PASSED")
