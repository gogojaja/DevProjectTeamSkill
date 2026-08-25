#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_scope_tracker.py — 范围跟踪工具单测（DEV-11，审计整改 v1.1.1）

轻量断言式：python tests/test_scope_tracker.py（无第三方依赖）
覆盖：split_ids / compute_metrics / 蔓延(Won't 已实现) / 缩水(Must 缺MOD/TC) /
      MOD·TC 孤儿蔓延(v1.1.1) / health_score / gate 端到端(GATE_RESULT 留痕) /
      min-health 门禁 / fail-closed(exit 2) / change 登记。
"""
import os
import sys
import csv
import io
import argparse
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import scope_tracker as st

HDR = ["REQ_ID", "REQ_TITLE", "AE_ID", "MOD_ID", "TC_ID", "PRIORITY",
       "SCOPE_STATUS", "BASELINE_VER", "SOURCE", "VERIFY_METHOD", "CHANGE_REFS"]


def _write_csv(path, rows):
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(HDR)
        w.writerows(rows)
    return path


def _tmp_rtm(rows):
    d = tempfile.mkdtemp()
    return _write_csv(os.path.join(d, "rtm.csv"), rows), d


def _D(rows):
    """list 行 → dict 行（对齐 csv.DictReader 语义）。"""
    return [dict(zip(HDR, r)) for r in rows]


def _patch_paths(d, base="ok"):
    st.DEFAULT_MATRIX = os.path.join(d, "rtm.csv")
    st.DEFAULT_TRACK = os.path.join(d, base + "_track.csv")
    st.DEFAULT_CHANGE = os.path.join(d, base + "_change.csv")


def test_split_ids():
    assert st.split_ids("") == []
    assert st.split_ids(None) == []
    assert st.split_ids("REQ-001") == ["REQ-001"]
    assert st.split_ids("MOD-001,MOD-002") == ["MOD-001", "MOD-002"]
    assert st.split_ids("TC-001;TC-002") == ["TC-001", "TC-002"]


def test_compute_metrics():
    rows = [
        ["REQ-001", "r1", "AE-001", "MOD-001", "TC-001", "Must", "Verified", "v1.0.0", "s", "TC-001", ""],
        ["REQ-002", "r2", "AE-001", "MOD-002", "TC-002", "Should", "Implemented", "v1.0.0", "s", "TC-002", ""],
        ["REQ-003", "r3", "", "", "", "Could", "Proposed", "v1.0.0", "s", "", ""],
    ]
    m = st.compute_metrics(_D(rows))
    assert m["req_total"] == 3 and m["with_ae"] == 2 and m["with_tc"] == 2
    assert m["impl"] == 2 and m["ver"] == 1
    assert m["cov_ae"] == 66.7 and m["cov_tc"] == 66.7


def test_creep_wont_implemented():
    rows = [["REQ-001", "r", "AE-001", "MOD-001", "TC-001", "Won't", "Verified", "v1.0.0", "s", "TC-001", ""]]
    creep, shrink = st.detect_creep_shrink(_D(rows))
    assert len(creep) >= 1 and any("Won't" in c for c in creep)
    assert not shrink


def test_shrink_must_missing_mod_tc():
    rows = [["REQ-001", "r", "AE-001", "", "", "Must", "Implemented", "v1.0.0", "s", "", ""]]
    creep, shrink = st.detect_creep_shrink(_D(rows))
    assert len(shrink) == 2  # 缺 MOD + 缺 TC
    assert not creep


def test_orphan_mod_tc_creep():
    # 孤儿 MOD-999（无 AE）与孤儿 TC-999（无 REQ）应判蔓延（v1.1.1）
    rows = [
        ["REQ-001", "r", "AE-001", "MOD-001", "TC-001", "Must", "Verified", "v1.0.0", "s", "TC-001", ""],
        ["", "孤儿行", "", "MOD-999", "TC-999", "", "", "", "", "", ""],
    ]
    creep, _ = st.detect_creep_shrink(_D(rows))
    assert any("MOD-999" in c for c in creep), creep
    assert any("TC-999" in c for c in creep), creep


def test_health_score():
    m = {"req_total": 10, "with_ae": 10, "with_tc": 10}
    assert st.health_score(m, [], [], []) == 100.0
    assert st.health_score(m, ["v"], [], []) == 98.0       # 1 违规 -2
    assert st.health_score(m, [], ["c"], []) == 98.5       # 1 蔓延 -1.5
    assert st.health_score(m, [], [], ["s"]) == 97.0       # 1 缩水 -3
    assert st.health_score(m, ["v"] * 60, [], []) == 0.0   # 下限 0


def test_gate_pass_and_result_written():
    rtm, d = _tmp_rtm([
        ["REQ-001", "r1", "AE-001", "MOD-001", "TC-001", "Must", "Verified", "v1.0.0", "s", "TC-001", ""],
        ["REQ-002", "r2", "AE-002", "MOD-002", "TC-002", "Should", "Verified", "v1.0.0", "s", "TC-002", ""],
    ])
    _patch_paths(d)
    args = argparse.Namespace(max_violations=0, min_health=90)
    rc = st.cmd_gate(args)
    assert rc == 0, "合法矩阵 gate 应通过"
    with io.open(st.DEFAULT_TRACK, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows and rows[-1]["GATE_RESULT"] == "通过", "GATE_RESULT 应写实际结论(v1.1.1)"
    assert rows[-1]["HEALTH_SCORE"] == "100.0"


def test_gate_min_health_reject():
    rtm, d = _tmp_rtm([
        ["REQ-001", "r1", "AE-001", "MOD-001", "TC-001", "Must", "Verified", "v1.0.0", "s", "TC-001", ""],
    ])
    _patch_paths(d)
    args = argparse.Namespace(max_violations=0, min_health=101)  # 健康 100 < 101
    rc = st.cmd_gate(args)
    assert rc == 1, "健康分低于阈值应驳回"


def test_gate_fail_closed_on_bad_matrix():
    d = tempfile.mkdtemp()
    bad = os.path.join(d, "rtm.csv")  # 文件名对齐 _patch_paths
    with io.open(bad, "w", encoding="utf-8-sig") as f:
        f.write("REQ_ID,REQ_TITLE\nREQ-001,r\n")  # 缺 AE/MOD/TC 基础列
    _patch_paths(d)
    args = argparse.Namespace(max_violations=0, min_health=90)
    rc = st.cmd_gate(args)
    assert rc == 2, "一致性校验异常应 fail-closed exit 2（防门禁假绿）"


def test_change_register():
    rtm, d = _tmp_rtm([["REQ-001", "r", "AE-001", "MOD-001", "TC-001", "Must", "Baselined", "v1.0.0", "s", "TC-001", ""]])
    _patch_paths(d)
    args = argparse.Namespace(
        req="REQ-001", title="范围调整", type="范围调整", source="用户诉求",
        impact_scope="高", impact_schedule="", impact_cost="", impact_quality="", impact_security="",
        severity="主要", approver="用户", baseline_from="v1.0.0", baseline_to="v1.0.1", note="测试")
    rc = st.cmd_change(args)
    assert rc == 0
    with io.open(st.DEFAULT_CHANGE, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows and rows[-1]["CHANGE_ID"] == "CR-001" and rows[-1]["REQ_IDS"] == "REQ-001"


if __name__ == "__main__":
    test_split_ids()
    test_compute_metrics()
    test_creep_wont_implemented()
    test_shrink_must_missing_mod_tc()
    test_orphan_mod_tc_creep()
    test_health_score()
    test_gate_pass_and_result_written()
    test_gate_min_health_reject()
    test_gate_fail_closed_on_bad_matrix()
    test_change_register()
    print("ALL TESTS PASSED")
