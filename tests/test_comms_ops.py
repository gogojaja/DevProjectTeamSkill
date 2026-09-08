#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_comms_ops.py — 干系人沟通工具单测（stakeholder-comms 独立部署 A-6）

轻量断言式：python tests/test_comms_ops.py（无第三方依赖）
覆盖：stakeholder 权力-利益四象限映射(重点管理/保持满意/保持知情/最少关注/未分类) /
      engage 参与度差距策略(需重点提升/适度提升/已达标/超出期望)+未找到 / plan / log / dashboard。
台账隔离：patch 模块级 LEDGER + STK_FILE/PLAN_FILE/LOG_FILE 到 tempfile。
"""
import os
import sys
import csv
import io
import argparse
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import comms_ops as cm


def _patch(d):
    cm.LEDGER = d
    cm.STK_FILE = os.path.join(d, "50_干系人映射.csv")
    cm.PLAN_FILE = os.path.join(d, "51_沟通计划.csv")
    cm.LOG_FILE = os.path.join(d, "52_沟通记录.csv")


def _tmp():
    d = tempfile.mkdtemp()
    _patch(d)
    return d


def _rows(path):
    with io.open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _stk(name="Sponsor", org="管理层", power="high", interest="high"):
    return cm.cmd_stakeholder(argparse.Namespace(name=name, org=org, power=power, interest=interest))


def test_stakeholder_quadrants():
    """权力-利益四象限映射。"""
    cases = [("high", "high", "重点管理"), ("high", "low", "保持满意"),
             ("low", "high", "保持知情"), ("low", "low", "最少关注"),
             ("medium", "high", "未分类")]
    for power, interest, expect in cases:
        d = _tmp()
        assert _stk(power=power, interest=interest) == 0
        row = _rows(cm.STK_FILE)[-1]
        assert row["象限"] == expect, f"{power}/{interest} 应={expect}"
        assert row["编号"] == "SH-001"


def test_engage_gap_strategies():
    """参与度差距：U→A gap4 需重点提升 / S→A gap1 适度提升 / A→A 已达标 / A→U 超出期望。"""
    cases = [("U", "A", "需重点提升参与度（差距4级）"),
             ("S", "A", "适度提升（差距1级）"),
             ("A", "A", "已达标"),
             ("A", "U", "超出期望")]
    for cur, exp, expect in cases:
        d = _tmp()
        _stk(name="Sponsor")
        assert cm.cmd_engage(argparse.Namespace(name="Sponsor", current=cur, expected=exp)) == 0
        assert _rows(cm.STK_FILE)[-1]["策略"] == expect, f"{cur}→{exp} 应={expect}"


def test_engage_not_found():
    d = _tmp()
    _stk(name="Sponsor")
    assert cm.cmd_engage(argparse.Namespace(name="不存在", current="U", expected="A")) == 1


def test_plan():
    d = _tmp()
    assert cm.cmd_plan(argparse.Namespace(stakeholder="Sponsor", content="进展摘要",
                                          freq="weekly", channel="面对面", owner="PM")) == 0
    row = _rows(cm.PLAN_FILE)[-1]
    assert row["编号"] == "CP-001" and row["干系人"] == "Sponsor" and row["频率"] == "weekly"


def test_log():
    d = _tmp()
    assert cm.cmd_log(argparse.Namespace(stakeholder="Sponsor", content="周报汇报",
                                         feedback="认可进度")) == 0
    row = _rows(cm.LOG_FILE)[-1]
    assert row["编号"] == "CL-001" and row["干系人"] == "Sponsor" and row["反馈"] == "认可进度"


def test_dashboard():
    d = _tmp()
    _stk(name="Sponsor")
    cm.cmd_plan(argparse.Namespace(stakeholder="Sponsor", content="进展摘要", freq="weekly", channel="面对面", owner="PM"))
    cm.cmd_log(argparse.Namespace(stakeholder="Sponsor", content="周报汇报", feedback=""))
    assert cm.cmd_dashboard(argparse.Namespace()) == 0


if __name__ == "__main__":
    test_stakeholder_quadrants()
    test_engage_gap_strategies()
    test_engage_not_found()
    test_plan()
    test_log()
    test_dashboard()
    print("ALL TESTS PASSED")
