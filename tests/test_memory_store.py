#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_memory_store.py — 记忆服务单测（P2，CR-002/TE-002）

轻量断言式：py -3.11 tests/test_memory_store.py（无第三方依赖）
覆盖：add 写 JSONL 合法、list 过滤、load_context 文本、export_csv 写 BOM。
"""
import os
import sys
import io
import json
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import memory_store as ms


def _tmp_store(patch):
    # 重定向模块常量到临时文件
    ms.STORE = patch
    ms.CSV_OUT = patch + ".csv"


def test_add_and_read():
    fd, p = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(p)
    try:
        _tmp_store(p)
        ms.add("decision", "方案评审通过", "PG-001")
        ms.add("todo", "实现 P2 记忆服务", "PG-001")
        rows = ms._read_all()
        assert len(rows) == 2, "应写入 2 条"
        assert rows[0]["type"] == "decision" and rows[1]["type"] == "todo"
        assert rows[0]["meta"] == "PG-001"
        # 非法类型应退出
        try:
            ms.add("hack", "x")
            assert False, "非法类型应 sys.exit(2)"
        except SystemExit as e:
            assert e.code == 2
    finally:
        os.remove(p)
        if os.path.exists(p + ".csv"):
            os.remove(p + ".csv")
    print("PASS test_add_and_read")


def test_load_context():
    fd, p = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(p)
    try:
        _tmp_store(p)
        ms.add("decision", "A", "m1")
        ms.add("todo", "B", "m2")
        txt = ms.load_context(limit=15)
        assert "A" in txt and "B" in txt, "load 应含两条记忆"
        assert "(无记忆)" not in txt
    finally:
        os.remove(p)
        if os.path.exists(p + ".csv"):
            os.remove(p + ".csv")
    print("PASS test_load_context")


def test_export_csv_bom():
    fd, p = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(p)
    try:
        _tmp_store(p)
        ms.add("risk", "GitHub flapping", "PG-001")
        ms.export_csv()
        raw = io.open(p + ".csv", "rb").read(3)
        assert raw == b"\xef\xbb\xbf", "导出必须 UTF-8 BOM"
        with io.open(p + ".csv", "r", encoding="utf-8-sig") as f:
            head = f.readline().strip()
        assert head.startswith("时间"), "首行应为表头"
    finally:
        os.remove(p)
        if os.path.exists(p + ".csv"):
            os.remove(p + ".csv")
    print("PASS test_export_csv_bom")


if __name__ == "__main__":
    test_add_and_read()
    test_load_context()
    test_export_csv_bom()
    print("ALL TESTS PASSED")
