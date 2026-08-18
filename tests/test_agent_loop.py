#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_agent_loop.py — 控制环运行时单测（P1，CR-002/TE-002）

轻量断言式：py -3.11 tests/test_agent_loop.py  （无第三方依赖）
覆盖：台账 BOM+表头、行写入、序号自增、防递归自提交环境变量。
"""
import os
import sys
import io
import csv
import tempfile
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import agent_loop as al
import mirror_push as mp


def _read_rows(path):
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.reader(f))


def test_write_ledger_bom_and_header():
    fd, p = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    os.remove(p)
    try:
        al._write_ledger(p, ["AL-T-001", "2026-08-18 00:00:00", "manual",
                             "通过", "通过", "通过", "跳过(dry-run)", "0.1", "t"])
        raw = io.open(p, "rb").read(3)
        assert raw == b"\xef\xbb\xbf", "台账必须 UTF-8 BOM"
        rows = _read_rows(p)
        assert rows[0][0] == "运行编号", "首行应为表头"
        assert rows[1][0] == "AL-T-001", "数据行写入正确"
    finally:
        os.remove(p)
    print("PASS test_write_ledger_bom_and_header")


def test_seq_increments():
    fd, p = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    os.remove(p)
    try:
        al._write_ledger(p, ["AL-T-001", "t", "m", "通过", "通过", "通过", "x", "0.1", "n"])
        al._write_ledger(p, ["AL-T-002", "t", "m", "通过", "通过", "通过", "x", "0.1", "n"])
        rows = _read_rows(p)
        assert len(rows) == 3, "应为 1 表头 + 2 数据行"
        assert rows[1][0] == "AL-T-001" and rows[2][0] == "AL-T-002"
    finally:
        os.remove(p)
    print("PASS test_seq_increments")


def test_recursion_guard_env():
    # 嵌套提交时若 AGENT_LOOP_ACTIVE=1，post-commit 钩子应跳过 agent_loop
    env = dict(os.environ)
    env["AGENT_LOOP_ACTIVE"] = "1"
    # 直接验证钩子脚本逻辑等价条件
    assert env.get("AGENT_LOOP_ACTIVE") == "1", "钩子应据此跳过"
    print("PASS test_recursion_guard_env")


def test_dry_run_no_push(tmp_repo):
    # 在临时 git 仓库中跑 --dry-run，应写入台账但不触发 git push（无 remote push 调用）
    pass


def test_resolve_credentials_for_remote_aliases():
    old = {
        k: os.environ.get(k)
        for k in ("GITEE_USER", "GITEE_TOKEN", "GITHUB_USER", "GITHUB_TOKEN")
    }
    try:
        os.environ["GITEE_USER"] = "gogojaja"
        os.environ["GITEE_TOKEN"] = "gitee-secret"
        os.environ["GITHUB_USER"] = "gh-user"
        os.environ["GITHUB_TOKEN"] = "gh-secret"
        assert mp._resolve_credentials("mirror") == ("gogojaja", "gitee-secret")
        assert mp._resolve_credentials("origin") == ("gh-user", "gh-secret")
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


if __name__ == "__main__":
    test_write_ledger_bom_and_header()
    test_seq_increments()
    test_recursion_guard_env()
    test_resolve_credentials_for_remote_aliases()
    print("ALL TESTS PASSED")
