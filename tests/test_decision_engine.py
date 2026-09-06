#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_decision_engine.py — 决策引擎单测（Phase A）

轻量断言式：py -3.11 tests/test_decision_engine.py（无第三方依赖）
覆盖：模式加载/事件匹配/决策执行/待决策队列/决策历史/dry-run。
"""
import os
import sys
import io
import json
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "agent_runtime"))

from event_bus import AgentEvent
from decision_engine import DecisionEngine, _append_jsonl, _read_jsonl


def _tmp_dir():
    d = tempfile.mkdtemp()
    patterns_dir = os.path.join(d, "patterns")
    os.makedirs(patterns_dir)
    return d, patterns_dir


def _write_default_patterns(patterns_dir, patterns=None):
    data = {
        "_version": "1.0.0",
        "patterns": patterns or [
            {
                "id": "test-commit-gates",
                "description": "测试：提交→门禁",
                "match": {"event": "git.commit"},
                "action": "run_gates_and_push",
                "params": {},
                "risk": "Tier2",
                "auto_execute": True,
            },
            {
                "id": "test-heal-diverged",
                "description": "测试：分叉→自愈",
                "match": {"event": "git.diverged"},
                "action": "self_heal",
                "params": {"dry_run": True},  # 测试用 dry_run
                "risk": "Tier3",
                "auto_execute": True,
            },
            {
                "id": "test-escalate",
                "description": "测试：门禁失败→升级",
                "match": {"event": "gate.fail"},
                "action": "escalate",
                "params": {"notify": True},
                "risk": "Tier2",
                "auto_execute": True,
            },
        ]
    }
    with io.open(os.path.join(patterns_dir, "default.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def test_load_patterns():
    d, patterns_dir = _tmp_dir()
    try:
        _write_default_patterns(patterns_dir)
        engine = DecisionEngine(patterns_dir=patterns_dir)
        patterns = engine.list_patterns()
        assert len(patterns) == 3
        assert patterns[0]["id"] == "test-commit-gates"
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print("PASS test_load_patterns")


def test_match_git_commit():
    d, patterns_dir = _tmp_dir()
    try:
        _write_default_patterns(patterns_dir)
        engine = DecisionEngine(patterns_dir=patterns_dir)

        ev = AgentEvent("git.commit", {"msg": "test"})
        pattern = engine.match(ev)
        assert pattern is not None
        assert pattern["id"] == "test-commit-gates"
        assert pattern["action"] == "run_gates_and_push"
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print("PASS test_match_git_commit")


def test_match_git_diverged():
    d, patterns_dir = _tmp_dir()
    try:
        _write_default_patterns(patterns_dir)
        engine = DecisionEngine(patterns_dir=patterns_dir)

        ev = AgentEvent("git.diverged", {"remote": "origin"})
        pattern = engine.match(ev)
        assert pattern is not None
        assert pattern["id"] == "test-heal-diverged"
        assert pattern["action"] == "self_heal"
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print("PASS test_match_git_diverged")


def test_match_gate_fail():
    d, patterns_dir = _tmp_dir()
    try:
        _write_default_patterns(patterns_dir)
        engine = DecisionEngine(patterns_dir=patterns_dir)

        ev = AgentEvent("gate.fail", {"gate": "version"})
        pattern = engine.match(ev)
        assert pattern is not None
        assert pattern["id"] == "test-escalate"
        assert pattern["action"] == "escalate"
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print("PASS test_match_gate_fail")


def test_match_unknown_event():
    d, patterns_dir = _tmp_dir()
    try:
        _write_default_patterns(patterns_dir)
        engine = DecisionEngine(patterns_dir=patterns_dir)

        ev = AgentEvent("file.change", {"path": "test.md"})
        pattern = engine.match(ev)
        assert pattern is None, "未注册的事件类型应返回 None"
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print("PASS test_match_unknown_event")


def test_decide_dry_run():
    d, patterns_dir = _tmp_dir()
    decision_ledger = os.path.join(d, "42_test.jsonl")
    pending_queue = os.path.join(d, "41_test.jsonl")
    try:
        _write_default_patterns(patterns_dir)
        engine = DecisionEngine(patterns_dir=patterns_dir)

        # 覆盖台账路径（通过 monkey-patch 模块变量）
        import decision_engine as de
        old_dl = de.DECISION_LEDGER
        old_pq = de.PENDING_QUEUE
        de.DECISION_LEDGER = decision_ledger
        de.PENDING_QUEUE = pending_queue

        ev = AgentEvent("git.commit", {"msg": "test"})
        decision = engine.decide(ev, dry_run=True)

        assert decision["pattern_id"] == "test-commit-gates"
        assert decision["auto_execute"] is True
        assert decision["dry_run"] is True
        # dry-run 不应写台账
        assert not os.path.exists(decision_ledger)

        de.DECISION_LEDGER = old_dl
        de.PENDING_QUEUE = old_pq
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print("PASS test_decide_dry_run")


def test_decide_escalate_unknown():
    d, patterns_dir = _tmp_dir()
    decision_ledger = os.path.join(d, "42_test.jsonl")
    pending_queue = os.path.join(d, "41_test.jsonl")
    try:
        _write_default_patterns(patterns_dir)
        engine = DecisionEngine(patterns_dir=patterns_dir)

        import decision_engine as de
        old_dl = de.DECISION_LEDGER
        old_pq = de.PENDING_QUEUE
        de.DECISION_LEDGER = decision_ledger
        de.PENDING_QUEUE = pending_queue

        # 未匹配的事件应升级
        ev = AgentEvent("file.change", {"path": "test.md"})
        decision = engine.decide(ev, dry_run=False)

        assert decision["pattern_id"] is None
        assert decision["action"] == "escalate"
        assert decision["auto_execute"] is False
        # 应写待决策队列
        assert os.path.exists(pending_queue)
        pending = _read_jsonl(pending_queue)
        assert len(pending) >= 1

        de.DECISION_LEDGER = old_dl
        de.PENDING_QUEUE = old_pq
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print("PASS test_decide_escalate_unknown")


def test_decide_records_history():
    d, patterns_dir = _tmp_dir()
    decision_ledger = os.path.join(d, "42_test.jsonl")
    pending_queue = os.path.join(d, "41_test.jsonl")
    try:
        _write_default_patterns(patterns_dir)
        engine = DecisionEngine(patterns_dir=patterns_dir)

        import decision_engine as de
        old_dl = de.DECISION_LEDGER
        old_pq = de.PENDING_QUEUE
        de.DECISION_LEDGER = decision_ledger
        de.PENDING_QUEUE = pending_queue

        ev = AgentEvent("gate.fail", {"gate": "version"})
        decision = engine.decide(ev, dry_run=False)

        assert decision["decision_id"].startswith("DEC-")
        history = engine.decision_history()
        assert len(history) >= 1
        assert history[-1]["event_type"] == "gate.fail"

        de.DECISION_LEDGER = old_dl
        de.PENDING_QUEUE = old_pq
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print("PASS test_decide_records_history")


def test_match_with_payload_filter():
    d, patterns_dir = _tmp_dir()
    try:
        _write_default_patterns(patterns_dir, patterns=[
            {
                "id": "nightly-scan",
                "match": {"event": "schedule.tick", "task": "nightly_scan"},
                "action": "nightly_quality_gate",
                "params": {},
                "risk": "Tier2",
                "auto_execute": True,
            },
        ])
        engine = DecisionEngine(patterns_dir=patterns_dir)

        # 匹配 payload 中有 task=nightly_scan 的事件
        ev1 = AgentEvent("schedule.tick", {"task": "nightly_scan"})
        assert engine.match(ev1)["id"] == "nightly-scan"

        # 不匹配 payload 中 task 不同的事件
        ev2 = AgentEvent("schedule.tick", {"task": "other_task"})
        assert engine.match(ev2) is None
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print("PASS test_match_with_payload_filter")


if __name__ == "__main__":
    test_load_patterns()
    test_match_git_commit()
    test_match_git_diverged()
    test_match_gate_fail()
    test_match_unknown_event()
    test_decide_dry_run()
    test_decide_escalate_unknown()
    test_decide_records_history()
    test_match_with_payload_filter()
    print("ALL DECISION ENGINE TESTS PASSED")
