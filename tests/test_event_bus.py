#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_event_bus.py — 事件总线单测（Phase A）

轻量断言式：py -3.11 tests/test_event_bus.py（无第三方依赖）
覆盖：事件创建/发布/订阅/限速/脱敏/持久化/统计。
"""
import os
import sys
import io
import json
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "agent_runtime"))

from event_bus import AgentEvent, EventBus, EVENT_TYPES, _redact


def _tmp_ledger():
    fd, p = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(p)
    return p


def test_event_types_defined():
    assert "git.commit" in EVENT_TYPES
    assert "git.diverged" in EVENT_TYPES
    assert "schedule.tick" in EVENT_TYPES
    assert "health.check" in EVENT_TYPES
    assert "gate.fail" in EVENT_TYPES
    assert "manual" in EVENT_TYPES
    print("PASS test_event_types_defined")


def test_agent_event_creation():
    ev = AgentEvent("git.commit", {"msg": "test"}, "P1", "hook")
    assert ev.event_type == "git.commit"
    assert ev.priority == "P1"
    assert ev.source == "hook"
    assert ev.payload == {"msg": "test"}
    d = ev.to_dict()
    assert d["type"] == "git.commit"
    assert d["priority"] == "P1"
    print("PASS test_agent_event_creation")


def test_agent_event_invalid_type():
    try:
        AgentEvent("invalid.type")
        assert False, "应抛出 ValueError"
    except ValueError:
        pass
    print("PASS test_agent_event_invalid_type")


def test_agent_event_roundtrip():
    ev = AgentEvent("health.check", {"status": "anomaly"}, "P0", "schedule")
    d = ev.to_dict()
    ev2 = AgentEvent.from_dict(d)
    assert ev2.event_type == ev.event_type
    assert ev2.priority == ev.priority
    assert ev2.payload == ev.payload
    print("PASS test_agent_event_roundtrip")


def test_redact_secrets():
    # 铁律 #3：A 级凭据脱敏
    assert "***[脱敏]***" in _redact("token=ghp_abcdefghij1234567890")
    assert "***[脱敏]***" in _redact("secret=my-super-secret-value")
    assert "正常文本" == _redact("正常文本")
    # dict 递归脱敏
    result = _redact({"key": "token=ghp_abcdefghij1234567890"})
    assert "***[脱敏]***" in result["key"]
    print("PASS test_redact_secrets")


def test_event_bus_publish_and_drain():
    path = _tmp_ledger()
    try:
        bus = EventBus(ledger_path=path)
        ev = AgentEvent("git.commit", {"msg": "test commit"}, "P1", "hook")
        ok = bus.publish(ev)
        assert ok is True, "首次发布应成功"
        assert ev.event_id.startswith("EVT-"), "应分配事件 ID"

        events = bus.drain()
        assert len(events) == 1
        assert events[0].event_type == "git.commit"
        assert events[0].payload["msg"] == "test commit"
    finally:
        if os.path.exists(path):
            os.remove(path)
    print("PASS test_event_bus_publish_and_drain")


def test_event_bus_subscribe():
    path = _tmp_ledger()
    received = []
    try:
        bus = EventBus(ledger_path=path)
        bus.subscribe("git.commit", lambda ev: received.append(ev))
        ev = AgentEvent("git.commit", {"msg": "test"})
        bus.publish(ev)
        assert len(received) == 1
        assert received[0].event_type == "git.commit"
    finally:
        if os.path.exists(path):
            os.remove(path)
    print("PASS test_event_bus_subscribe")


def test_event_bus_rate_limit():
    path = _tmp_ledger()
    try:
        bus = EventBus(ledger_path=path)
        ev1 = AgentEvent("git.commit", {"msg": "first"})
        ev2 = AgentEvent("git.commit", {"msg": "first"})  # 相同 payload
        ok1 = bus.publish(ev1)
        ok2 = bus.publish(ev2)
        assert ok1 is True
        assert ok2 is False, "5 分钟内同类同 payload 事件应被限速"

        events = bus.drain()
        assert len(events) == 1, "仅首条入库"
    finally:
        if os.path.exists(path):
            os.remove(path)
    print("PASS test_event_bus_rate_limit")


def test_event_bus_stats():
    path = _tmp_ledger()
    try:
        bus = EventBus(ledger_path=path)
        bus.publish(AgentEvent("git.commit", {"msg": "a"}))
        bus.publish(AgentEvent("health.check", {"status": "ok"}))
        bus.publish(AgentEvent("git.commit", {"msg": "b"}))  # 不同 payload，不限速

        stats = bus.stats()
        assert stats["total"] == 3
        assert stats["by_type"]["git.commit"] == 2
        assert stats["by_type"]["health.check"] == 1
    finally:
        if os.path.exists(path):
            os.remove(path)
    print("PASS test_event_bus_stats")


def test_event_bus_drain_by_type():
    path = _tmp_ledger()
    try:
        bus = EventBus(ledger_path=path)
        bus.publish(AgentEvent("git.commit", {"msg": "a"}))
        bus.publish(AgentEvent("health.check", {"status": "ok"}))
        bus.publish(AgentEvent("git.commit", {"msg": "b"}))

        commits = bus.drain(event_type="git.commit")
        assert len(commits) == 2
        checks = bus.drain(event_type="health.check")
        assert len(checks) == 1
    finally:
        if os.path.exists(path):
            os.remove(path)
    print("PASS test_event_bus_drain_by_type")


def test_event_bus_priority_sort():
    path = _tmp_ledger()
    try:
        bus = EventBus(ledger_path=path)
        bus.publish(AgentEvent("manual", {"x": 1}, "P3"))
        bus.publish(AgentEvent("manual", {"x": 2}, "P0"))
        bus.publish(AgentEvent("manual", {"x": 3}, "P1"))

        events = bus.drain()
        assert events[0].priority == "P0"
        assert events[1].priority == "P1"
        assert events[2].priority == "P3"
    finally:
        if os.path.exists(path):
            os.remove(path)
    print("PASS test_event_bus_priority_sort")


def test_event_bus_jsonl_utf8():
    path = _tmp_ledger()
    try:
        bus = EventBus(ledger_path=path)
        bus.publish(AgentEvent("manual", {"msg": "中文事件测试"}))

        raw = io.open(path, "r", encoding="utf-8").read()
        assert "中文事件测试" in raw
        # 验证 JSON 可解析
        for line in raw.strip().split("\n"):
            json.loads(line)
    finally:
        if os.path.exists(path):
            os.remove(path)
    print("PASS test_event_bus_jsonl_utf8")


if __name__ == "__main__":
    test_event_types_defined()
    test_agent_event_creation()
    test_agent_event_invalid_type()
    test_agent_event_roundtrip()
    test_redact_secrets()
    test_event_bus_publish_and_drain()
    test_event_bus_subscribe()
    test_event_bus_rate_limit()
    test_event_bus_stats()
    test_event_bus_drain_by_type()
    test_event_bus_priority_sort()
    test_event_bus_jsonl_utf8()
    print("ALL EVENT BUS TESTS PASSED")
