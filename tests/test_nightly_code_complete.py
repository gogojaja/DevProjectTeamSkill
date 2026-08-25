#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_nightly_code_complete.py — 夜间自动补全工具单测（无第三方依赖）

覆盖：候选发现(标记点/桩) / 指纹去重 / 上下文检索 / mock 生成 / 补全应用 /
      门禁 skip(dry-run) / 审计台账 append / 交付降级 patch。
"""
import os
import sys
import io
import csv
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import nightly_code_complete as ncc


def _write(path, text):
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _tmp_src(body):
    d = tempfile.mkdtemp()
    return _write(os.path.join(d, "sample.py"), body), d


def test_find_candidates_marker():
    src, d = _tmp_src(
        "def foo():\n"
        "    # @auto-complete\n"
        "    pass\n"
        "\n"
        "def bar():\n"
        "    return 1\n"
    )
    cands = ncc.find_candidates([d], max_candidates=10)
    assert len(cands) == 1, cands
    c = cands[0]
    assert c["file"] == src
    assert "@auto-complete" in c["marker"]
    assert c["snippet"].strip() == "pass"
    assert c["stub_start"] == 3 and c["stub_end"] == 3


def test_find_candidates_todo():
    src, d = _tmp_src(
        "def baz():\n"
        "    # TODO(@auto-complete): 实现校验\n"
        "    raise NotImplementedError\n"
    )
    cands = ncc.find_candidates([d], max_candidates=10)
    assert len(cands) == 1
    assert "NotImplementedError" in cands[0]["snippet"]


def test_find_ignores_unmarked():
    src, d = _tmp_src("def q():\n    pass\n")
    assert ncc.find_candidates([d], max_candidates=10) == []


def test_fingerprint_stable():
    src, d = _tmp_src("def f():\n    # @auto-complete\n    pass\n")
    c = ncc.find_candidates([d], 10)[0]
    assert ncc._fingerprint(c) == ncc._fingerprint(c)


def test_apply_completion_replaces_stub():
    src, d = _tmp_src("def f():\n    # @auto-complete\n    pass\n")
    c = ncc.find_candidates([d], 10)[0]
    new = ncc.apply_completion(src, c, "    return 42\n")
    assert "return 42" in new
    assert "pass" not in new
    assert "# @auto-complete" in new


def test_context_includes_file():
    src, d = _tmp_src("# -*- coding: utf-8 -*-\ndef f():\n    # @auto-complete\n    pass\n")
    c = ncc.find_candidates([d], 10)[0]
    ctx = ncc.context_for(src, c, ROOT)
    assert "文件上下文" in ctx


def test_generate_mock():
    cfg = type("C", (), {"provider": "mock"})()
    out = ncc.generate("mock", "prompt", cfg)
    assert "mock 补全" in out


def test_dry_run_end_to_end():
    src, d = _tmp_src("def f():\n    # @auto-complete\n    pass\n")
    audit = os.path.join(d, "audit.csv")
    # 重定向 AUDIT/STATE 到临时区（避免污染仓库）
    old_audit, old_state = ncc.AUDIT, ncc.STATE
    ncc.AUDIT = audit
    ncc.STATE = os.path.join(d, "state.json")
    try:
        cfg = type("C", (), {
            "dry_run": True, "no_git": True, "no_pr": True, "provider": "mock",
            "scope": [d], "exclude": [], "max_candidates": 5, "reset_state": True,
            "lint_cmd": "", "test_cmd": "", "gate_timeout": 1, "llm_timeout": 1,
        })()
        rc = ncc.run(cfg)
        assert rc == 0
        with io.open(audit, "r", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        assert rows[0][0] == "候选ID"
        assert len(rows) == 2  # 表头 + 1 候选
        assert rows[1][4] == "ok"
    finally:
        ncc.AUDIT, ncc.STATE = old_audit, old_state


def test_deliver_patch_fallback(tmp_path=None):
    src, d = _tmp_src("def f():\n    # @auto-complete\n    pass\n")
    c = ncc.find_candidates([d], 10)[0]
    cfg = type("C", (), {"dry_run": True, "no_pr": True, "provider": "mock"})()
    status, ref = ncc.deliver(ROOT, c, "    return 1\n", True, "skip", cfg, "b", "R1")
    assert status == "patch"
    assert os.path.exists(os.path.join(ROOT, ref))


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    fail = 0
    for fn in fns:
        try:
            fn()
            print("PASS %s" % fn.__name__)
        except Exception as e:  # noqa: BLE001
            fail += 1
            print("FAIL %s: %s" % (fn.__name__, e))
    print("==== %d passed, %d failed ====" % (len(fns) - fail, fail))
    sys.exit(1 if fail else 0)
