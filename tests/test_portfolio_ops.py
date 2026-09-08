#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_portfolio_ops.py — 组合管理工具单测（portfolio-mgmt 独立部署 A-6）

轻量断言式：python tests/test_portfolio_ops.py（无第三方依赖）
覆盖：register 注册 / score 5维加权评分与决策(Accelerate/Proceed/Pause/Terminate) /
      评分越界拒绝 / review PRB决策(枚举校验) / track 价值兑现偏差 / balance·optimize·dashboard。
台账隔离：patch 模块级 LEDGER + REG_FILE/SCORE_FILE/VALUE_FILE 到 tempfile，不污染真实台账。
"""
import os
import sys
import csv
import io
import argparse
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import portfolio_ops as pf


def _patch(d):
    """将模块级台账路径全局重定向到临时目录，实现测试隔离。"""
    pf.LEDGER = d
    pf.REG_FILE = os.path.join(d, "43_组合注册.csv")
    pf.SCORE_FILE = os.path.join(d, "44_战略评分.csv")
    pf.VALUE_FILE = os.path.join(d, "45_组合价值兑现.csv")


def _tmp():
    d = tempfile.mkdtemp()
    _patch(d)
    return d


def _rows(path):
    with io.open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _score_args(project, a, r, rk, fe, u):
    return argparse.Namespace(project=project, alignment=a, roi=r, risk=rk,
                              feasibility=fe, urgency=u)


def test_register():
    d = _tmp()
    args = argparse.Namespace(name="项目X", theme="数字化转型", category="战略投资",
                              stage="评估中", sponsor="张三")
    assert pf.cmd_register(args) == 0
    rows = _rows(pf.REG_FILE)
    assert len(rows) == 1 and rows[0]["编号"] == "PF-001"
    assert rows[0]["项目名称"] == "项目X" and rows[0]["战略主题"] == "数字化转型"
    assert rows[0]["状态"] == "已注册"


def test_score_proceed():
    """加权 3.80（对齐4/ROI3/风险4/可行5/紧迫3）→ Proceed。"""
    d = _tmp()
    assert pf.cmd_score(_score_args("项目X", 4, 3, 4, 5, 3)) == 0
    row = _rows(pf.SCORE_FILE)[-1]
    assert row["编号"] == "SC-001" and row["加权总分"] == "3.80"
    assert row["决策建议"] == "Proceed"


def test_score_accelerate():
    """加权 4.90 且紧迫度≥4 → Accelerate。"""
    d = _tmp()
    pf.cmd_score(_score_args("项目A", 5, 5, 5, 5, 4))
    row = _rows(pf.SCORE_FILE)[-1]
    assert row["加权总分"] == "4.90" and row["决策建议"] == "Accelerate"


def test_score_pause():
    """加权 2.75（2.5~3.5）→ Pause。"""
    d = _tmp()
    pf.cmd_score(_score_args("项目B", 3, 3, 3, 2, 2))
    row = _rows(pf.SCORE_FILE)[-1]
    assert row["加权总分"] == "2.75" and row["决策建议"] == "Pause"


def test_score_terminate():
    """加权 1.15（<2.5）→ Terminate。"""
    d = _tmp()
    pf.cmd_score(_score_args("项目C", 1, 1, 1, 2, 1))
    row = _rows(pf.SCORE_FILE)[-1]
    assert row["加权总分"] == "1.15" and row["决策建议"] == "Terminate"


def test_score_out_of_range_rejected():
    """评分越界（非 1~5）→ rc1，不写台账。"""
    d = _tmp()
    assert pf.cmd_score(_score_args("项目D", 6, 3, 4, 5, 3)) == 1
    assert pf.cmd_score(_score_args("项目E", 0, 3, 4, 5, 3)) == 1
    assert not os.path.isfile(pf.SCORE_FILE) or _rows(pf.SCORE_FILE) == []


def test_review_decision_and_guard():
    """PRB 决策写 VALUE_FILE；非法决策 rc1。"""
    d = _tmp()
    assert pf.cmd_review(argparse.Namespace(project="项目X", decision="Proceed", note="")) == 0
    row = _rows(pf.VALUE_FILE)[-1]
    assert row["编号"] == "VD-001" and row["PRB决策"] == "Proceed"
    assert pf.cmd_review(argparse.Namespace(project="项目X", decision="胡来", note="")) == 1


def test_track_deviation():
    """价值兑现：预期100/实际85 → 偏差 -15.0%。"""
    d = _tmp()
    assert pf.cmd_track(argparse.Namespace(project="项目X", expected=100, actual=85, note="")) == 0
    row = _rows(pf.VALUE_FILE)[-1]
    assert row["偏差率"] == "-15.0%" and row["预期收益"] == "100" and row["实际收益"] == "85"


def test_balance_optimize_dashboard():
    """平衡/优化/仪表盘端到端 rc0。"""
    d = _tmp()
    pf.cmd_register(argparse.Namespace(name="项目X", theme="数字化转型", category="战略投资", stage="", sponsor=""))
    pf.cmd_score(_score_args("项目X", 4, 3, 4, 5, 3))
    assert pf.cmd_balance(argparse.Namespace()) == 0
    assert pf.cmd_optimize(argparse.Namespace()) == 0
    assert pf.cmd_dashboard(argparse.Namespace()) == 0


if __name__ == "__main__":
    test_register()
    test_score_proceed()
    test_score_accelerate()
    test_score_pause()
    test_score_terminate()
    test_score_out_of_range_rejected()
    test_review_decision_and_guard()
    test_track_deviation()
    test_balance_optimize_dashboard()
    print("ALL TESTS PASSED")
