#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_dispatch.py — 任务总线单测（P4，SEC-003 脱敏，CR-002/TE-002）

轻量断言式：py -3.11 tests/test_dispatch.py（无第三方依赖）
覆盖：create/list/complete 流转、A 级信息脱敏、角色校验。
"""
import os
import sys
import io
import csv
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import dispatch as d


def _tmp_bus():
    fd, p = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    os.remove(p)
    d.BUS = p
    return p


def test_create_complete_redact():
    p = _tmp_bus()
    try:
        tid = d.create("architect", "设计 CMDB 集成，token=ghp_ABCDEFGHIJKLMNOPQRST")
        assert tid.startswith("TASK-")
        d.complete(tid, "完成，secret=supersecretvalue12345678")
        with io.open(p, "r", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        assert rows[0][0] == "任务ID"
        rec = rows[1]
        assert "***[脱敏]***" in rec[4], "输入中的 token 应被脱敏"
        assert rec[3] == "done"
        assert "***[脱敏]***" in rec[5], "输出中的 secret 应被脱敏"
    finally:
        os.remove(p)
    print("PASS test_create_complete_redact")


def test_role_validation():
    p = _tmp_bus()
    try:
        try:
            d.create("hacker", "x")
            assert False, "非法角色应 sys.exit(2)"
        except SystemExit as e:
            assert e.code == 2
    finally:
        if os.path.exists(p):
            os.remove(p)
    print("PASS test_role_validation")


if __name__ == "__main__":
    test_create_complete_redact()
    test_role_validation()
    print("ALL TESTS PASSED")
