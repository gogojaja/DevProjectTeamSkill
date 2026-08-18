#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_self_heal.py — 自愈单测（P3，CR-002/TE-002）

轻量断言式：py -3.11 tests/test_self_heal.py（无第三方依赖）
覆盖：分叉分类纯逻辑、dry-run 修复计划生成（mock 远端状态，避免真实网络耗时）。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import self_heal as sh


def test_classify():
    assert sh._classify(0, 0, False) == "clean"
    assert sh._classify(3, 0, False) == "ahead"
    assert sh._classify(0, 2, False) == "behind"
    assert sh._classify(2, 2, True) == "diverged"
    print("PASS test_classify")


def test_heal_dry_diverged(monkeypatch):
    monkeypatch.setattr(sh, "_remote_state", lambda r: (2, 2, True))
    # dry-run 不应执行真实 git push/fetch；仅返回计划
    ok = sh._heal_remote("mirror", dry=True)
    assert ok is True, "dry-run 分叉应返回 True 并仅打印计划"
    print("PASS test_heal_dry_diverged")


def test_heal_dry_ahead(monkeypatch):
    monkeypatch.setattr(sh, "_remote_state", lambda r: (1, 0, False))
    assert sh._heal_remote("mirror", dry=True) is True
    print("PASS test_heal_dry_ahead")


if __name__ == "__main__":
    # 简单 monkeypatch 替代（不依赖 pytest）
    import types
    mp = types.SimpleNamespace()
    _orig = sh._remote_state

    def patch(state):
        sh._remote_state = lambda r: state

    try:
        test_classify()
        patch((2, 2, True)); assert sh._heal_remote("mirror", dry=True) is True
        print("PASS test_heal_dry_diverged")
        patch((1, 0, False)); assert sh._heal_remote("mirror", dry=True) is True
        print("PASS test_heal_dry_ahead")
        print("ALL TESTS PASSED")
    finally:
        sh._remote_state = _orig
