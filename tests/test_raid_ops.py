#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_raid_ops.py — RAID 四维台账 + 风险扫描工具单测（risk-mgmt 独立部署 B-3）

轻量断言式：python tests/test_raid_ops.py（无第三方依赖）
覆盖：add 四维(类型校验+默认状态+自动定级) / list 过滤 / update 状态流转校验 /
      close 关闭+终态 / scan 概率×影响分级(排除已关闭) / RAID_ID 序列 / JSON 输出 /
      与 dev-project-mgmt raid_manager 一致性（AC6：TYPE_DEFAULT_STATUS + VALID_TRANSITIONS 完全一致）。
台账隔离：patch 模块级 LEDGER + RAID_FILE/RAID_FILE_ALT 到 tempfile，不污染真实台账。
"""
import os
import sys
import csv
import io
import json
import argparse
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import raid_ops as rd


def _patch(d):
    """将模块级台账路径全局重定向到临时目录，实现测试隔离。"""
    rd.LEDGER = d
    rd.RAID_FILE = os.path.join(d, "12_风险问题台账.csv")
    rd.RAID_FILE_ALT = os.path.join(d, "RAID台账.csv")


def _tmp():
    d = tempfile.mkdtemp()
    _patch(d)
    return d


def _rows(path=None):
    with io.open(path or rd.RAID_FILE, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _add(typ, desc, prob="", impact="", owner="", priority="", notes=""):
    return argparse.Namespace(type=typ, desc=desc, probability=prob, impact=impact,
                              owner=owner, priority=priority, notes=notes)


def test_add_risk_default_status_and_priority():
    """add risk 高/高 → RAID-001，默认状态 mitigating，风险分16→自动定级 P1。"""
    d = _tmp()
    assert rd.cmd_add(_add("risk", "核心人员流失", "高", "高", "张三")) == 0
    rows = _rows()
    assert len(rows) == 1 and rows[0]["RAID_ID"] == "RAID-001"
    assert rows[0]["类型"] == "risk" and rows[0]["状态"] == "mitigating"
    assert rows[0]["优先级"] == "P1" and rows[0]["责任人"] == "张三"
    assert rows[0]["概率"] == "高" and rows[0]["影响"] == "高"


def test_add_invalid_type_rejected():
    """非法类型 → rc1，不写台账。"""
    d = _tmp()
    assert rd.cmd_add(_add("bug", "非法类型", "高", "高")) == 1
    assert not os.path.isfile(rd.RAID_FILE) or _rows() == []


def test_add_auto_priority_levels():
    """自动定级：中/中=9→P2；低/中=6→P3；低/低=4→P3。"""
    d = _tmp()
    rd.cmd_add(_add("risk", "R中中", "中", "中"))
    rd.cmd_add(_add("risk", "R低中", "低", "中"))
    rd.cmd_add(_add("risk", "R低低", "低", "低"))
    rows = _rows()
    assert rows[0]["优先级"] == "P2"  # 3×3=9
    assert rows[1]["优先级"] == "P3"  # 2×3=6
    assert rows[2]["优先级"] == "P3"  # 2×2=4


def test_id_sequence():
    """RAID_ID 顺序递增 RAID-001/002/003。"""
    d = _tmp()
    rd.cmd_add(_add("risk", "A", "高", "高"))
    rd.cmd_add(_add("issue", "B", "中", "中"))
    rd.cmd_add(_add("assumption", "C"))
    ids = [r["RAID_ID"] for r in _rows()]
    assert ids == ["RAID-001", "RAID-002", "RAID-003"]


def test_list_filter():
    """list 按类型/状态过滤 rc0。"""
    d = _tmp()
    rd.cmd_add(_add("risk", "R1", "高", "高"))
    rd.cmd_add(_add("issue", "I1", "中", "中"))
    assert rd.cmd_list(argparse.Namespace(type="risk", status="")) == 0
    assert rd.cmd_list(argparse.Namespace(type="", status="mitigating")) == 0
    assert rd.cmd_list(argparse.Namespace(type="badtype", status="")) == 1


def test_update_status_transition_valid():
    """assumption(open) → investigating 合法流转。"""
    d = _tmp()
    rd.cmd_add(_add("assumption", "假设A"))  # 默认 open
    assert rd.cmd_update(argparse.Namespace(
        id="RAID-001", status="investigating", desc="", probability="",
        impact="", owner="", notes="", priority="")) == 0
    assert _rows()[0]["状态"] == "investigating"


def test_update_illegal_transition_rejected():
    """risk(mitigating) → investigating 非法（mitigating 仅允许 closed/open）→ rc1。"""
    d = _tmp()
    rd.cmd_add(_add("risk", "R1", "高", "高"))  # 默认 mitigating
    assert rd.cmd_update(argparse.Namespace(
        id="RAID-001", status="investigating", desc="", probability="",
        impact="", owner="", notes="", priority="")) == 1
    assert _rows()[0]["状态"] == "mitigating"  # 未变更


def test_update_not_found():
    """更新不存在条目 → rc1。"""
    d = _tmp()
    rd.cmd_add(_add("risk", "R1", "高", "高"))
    assert rd.cmd_update(argparse.Namespace(
        id="RAID-999", status="closed", desc="", probability="",
        impact="", owner="", notes="", priority="")) == 1


def test_close_and_terminal():
    """close：mitigating→closed 合法，填关闭日期；重复 close rc0；closed→open 非法 rc1。"""
    d = _tmp()
    rd.cmd_add(_add("risk", "R1", "高", "高"))  # mitigating
    assert rd.cmd_close(argparse.Namespace(id="RAID-001")) == 0
    row = _rows()[0]
    assert row["状态"] == "closed" and row["关闭日期"] != ""
    # 重复关闭 → rc0（已关闭）
    assert rd.cmd_close(argparse.Namespace(id="RAID-001")) == 0
    # 终态不可再流转 → update open 非法 rc1
    assert rd.cmd_update(argparse.Namespace(
        id="RAID-001", status="open", desc="", probability="",
        impact="", owner="", notes="", priority="")) == 1


def test_scan_severity_threshold():
    """scan 分级：P1(阈值12) 仅命中16；P2(阈值8) 命中16/9；P3(阈值4) 命中16/9/4。"""
    d = _tmp()
    rd.cmd_add(_add("risk", "高高16", "高", "高"))   # 16 P1
    rd.cmd_add(_add("issue", "中中9", "中", "中"))    # 9  P2
    rd.cmd_add(_add("risk", "低低4", "低", "低"))     # 4  P3
    # scan 用内部函数精确断言命中数
    header, rows = rd._read_raw()
    open_rows = [r for r in rows if rd._get(r, "状态") != "closed"]
    p1 = [r for r in open_rows if rd._risk_score(r) >= rd.SEVERITY_MAP["P1"]]
    p2 = [r for r in open_rows if rd._risk_score(r) >= rd.SEVERITY_MAP["P2"]]
    p3 = [r for r in open_rows if rd._risk_score(r) >= rd.SEVERITY_MAP["P3"]]
    assert len(p1) == 1 and len(p2) == 2 and len(p3) == 3
    assert rd.cmd_scan(argparse.Namespace(severity="P1", json=False)) == 0


def test_scan_excludes_closed():
    """scan 排除已关闭项：关闭唯一高风险后 scan P1 → 0 命中。"""
    d = _tmp()
    rd.cmd_add(_add("risk", "高高16", "高", "高"))  # mitigating, 16
    rd.cmd_close(argparse.Namespace(id="RAID-001"))
    header, rows = rd._read_raw()
    open_rows = [r for r in rows if rd._get(r, "状态") != "closed"]
    p1 = [r for r in open_rows if rd._risk_score(r) >= rd.SEVERITY_MAP["P1"]]
    assert len(p1) == 0
    assert rd.cmd_scan(argparse.Namespace(severity="P1", json=False)) == 0


def test_scan_json():
    """scan --json 输出结构化（total/matched/items）。"""
    d = _tmp()
    rd.cmd_add(_add("risk", "高高16", "高", "高"))
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = rd.cmd_scan(argparse.Namespace(severity="P1", json=True))
    assert rc == 0
    data = json.loads(buf.getvalue().strip().splitlines()[-1])
    assert data["total"] == 1 and data["matched"] == 1
    assert data["items"][0]["RAID_ID"] == "RAID-001" and data["items"][0]["风险分"] == 16


def test_consistency_with_dev_project_mgmt():
    """AC6 一致性：TYPE_DEFAULT_STATUS + VALID_TRANSITIONS 与 dev-project-mgmt raid_manager 完全一致。"""
    # 类型默认状态（吸收 raid_manager.TYPE_DEFAULT_STATUS）
    assert rd.TYPE_DEFAULT_STATUS == {
        "risk": "mitigating", "assumption": "open",
        "issue": "investigating", "dependency": "open",
    }
    # 状态流转规则（吸收 raid_manager.VALID_TRANSITIONS）
    assert rd.VALID_TRANSITIONS["open"] == {"mitigating", "investigating", "closed"}
    assert rd.VALID_TRANSITIONS["mitigating"] == {"closed", "open"}
    assert rd.VALID_TRANSITIONS["investigating"] == {"closed", "open"}
    assert rd.VALID_TRANSITIONS["closed"] == set()  # 终态
    # 四维类型集合一致
    assert rd.VALID_TYPES == {"risk", "assumption", "issue", "dependency"}
    # 概率×影响分级映射（吸收 MCP risk_scan._parse_level）
    assert rd._parse_level("高") == 4 and rd._parse_level("中") == 3 and rd._parse_level("低") == 2


if __name__ == "__main__":
    test_add_risk_default_status_and_priority()
    test_add_invalid_type_rejected()
    test_add_auto_priority_levels()
    test_id_sequence()
    test_list_filter()
    test_update_status_transition_valid()
    test_update_illegal_transition_rejected()
    test_update_not_found()
    test_close_and_terminal()
    test_scan_severity_threshold()
    test_scan_excludes_closed()
    test_scan_json()
    test_consistency_with_dev_project_mgmt()
    print("ALL TESTS PASSED")
