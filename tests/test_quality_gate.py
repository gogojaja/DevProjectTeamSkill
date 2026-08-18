#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_quality_gate.py — 质量门单测（P5，CR-002/TE-002）

轻量断言式：py -3.11 tests/test_quality_gate.py（无第三方依赖）
覆盖：run 写 BOM CSV、自动视角结论、决策聚合。
"""
import os
import sys
import io
import csv
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import quality_gate as qg


def test_run_writes_bom():
    fd, p = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    os.remove(p)
    try:
        qg.GATE = p
        rc = qg.run(".")
        assert rc == 0, "当前仓库自动门禁应全过"
        raw = io.open(p, "rb").read(3)
        assert raw == b"\xef\xbb\xbf", "质量门台账必须 UTF-8 BOM"
        with io.open(p, "r", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        assert rows[0][0] == "评审编号"
        # 5 视角：Architect/CodeReviewer + 3 个待宿主LLM
        views = [r[3] for r in rows[1:]]
        assert "Architect" in views and "SecurityReviewer" in views
        assert any(r[4] == "待宿主LLM" for r in rows[1:])
    finally:
        os.remove(p)
    print("PASS test_run_writes_bom")


if __name__ == "__main__":
    test_run_writes_bom()
    print("ALL TESTS PASSED")
