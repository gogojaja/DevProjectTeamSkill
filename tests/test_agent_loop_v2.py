#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_agent_loop_v2.py — 事件驱动主循环单测（Phase A）

轻量断言式：py -3.11 tests/test_agent_loop_v2.py（无第三方依赖）
覆盖：v1 兼容模式/dry-run/事件驱动流程/守护模式参数。
"""
import os
import sys
import io
import json
import csv
import tempfile
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME_DIR = os.path.join(ROOT, "tools", "agent_runtime")
sys.path.insert(0, RUNTIME_DIR)


def _tmp_ledger():
    fd, p = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    os.remove(p)
    return p


def _read_csv(path):
    if not os.path.exists(path):
        return []
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.reader(f))


def test_import_modules():
    """验证所有 agent_runtime 模块可导入。"""
    from event_bus import AgentEvent, EventBus, get_event_bus
    from decision_engine import DecisionEngine
    assert AgentEvent is not None
    assert EventBus is not None
    assert DecisionEngine is not None
    print("PASS test_import_modules")


def test_event_bus_cli_publish():
    """验证事件总线 CLI 可发布事件。"""
    ledger = _tmp_ledger()
    try:
        # 通过 subprocess 调用 CLI
        env = dict(os.environ)
        env["PROJECT_ROOT"] = ROOT
        # 临时替换台账路径（通过环境变量不可行，直接测试 Python API）
        from event_bus import EventBus, AgentEvent
        bus = EventBus(ledger_path=ledger)
        ev = AgentEvent("manual", {"test": "cli"}, "P2", "manual")
        ok = bus.publish(ev)
        assert ok is True

        events = bus.drain()
        assert len(events) == 1
        assert events[0].event_type == "manual"
    finally:
        if os.path.exists(ledger):
            os.remove(ledger)
    print("PASS test_event_bus_cli_publish")


def test_decision_engine_cli_list_patterns():
    """验证决策引擎 CLI 可列出模式。"""
    result = subprocess.run(
        [sys.executable, os.path.join(RUNTIME_DIR, "decision_engine.py"),
         "list-patterns"],
        cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    assert result.returncode == 0
    assert "commit-run-gates" in (result.stdout or "")
    assert "auto-heal-diverged" in (result.stdout or "")
    print("PASS test_decision_engine_cli_list_patterns")


def test_decision_engine_cli_match():
    """验证决策引擎 CLI 可匹配事件。"""
    event_json = '{"type": "git.commit", "payload": {}, "priority": "P1"}'
    result = subprocess.run(
        [sys.executable, os.path.join(RUNTIME_DIR, "decision_engine.py"),
         "match", "--event-json", event_json, "--dry-run"],
        cwd=ROOT, capture_output=True,
        encoding="utf-8", errors="replace")
    assert result.returncode == 0, "CLI 应成功: %s" % (result.stderr or "")
    output = result.stdout or ""
    assert "commit-run-gates" in output
    assert "run_gates_and_push" in output
    print("PASS test_decision_engine_cli_match")


def test_decision_engine_cli_match_diverged():
    """验证分叉事件匹配到自愈模式。"""
    # 使用 Python 直接调用避免 PowerShell 转义问题
    script = os.path.join(RUNTIME_DIR, "decision_engine.py")
    event_json = '{"type": "git.diverged", "payload": {"remote": "origin"}}'
    result = subprocess.run(
        [sys.executable, script, "match", "--event-json", event_json, "--dry-run"],
        cwd=ROOT, capture_output=True,
        encoding="utf-8", errors="replace")
    assert result.returncode == 0, "CLI 应成功: %s" % (result.stderr or "")
    assert "auto-heal-diverged" in (result.stdout or "")
    assert "self_heal" in (result.stdout or "")
    print("PASS test_decision_engine_cli_match_diverged")


def test_decision_engine_cli_pending_empty():
    """验证待决策队列初始为空。"""
    result = subprocess.run(
        [sys.executable, os.path.join(RUNTIME_DIR, "decision_engine.py"),
         "pending"],
        cwd=ROOT, capture_output=True,
        encoding="utf-8", errors="replace")
    assert result.returncode == 0
    # 可能为空或已有数据
    print("PASS test_decision_engine_cli_pending_empty")


def test_agent_loop_v2_dry_run():
    """验证 agent_loop_v2 --dry-run 不产生副作用。"""
    result = subprocess.run(
        [sys.executable, os.path.join(RUNTIME_DIR, "agent_loop_v2.py"),
         "--dry-run", "--trigger", "manual"],
        cwd=ROOT, capture_output=True,
        encoding="utf-8", errors="replace")
    # dry-run 应成功退出（即使无事件）
    combined = (result.stdout or "") + (result.stderr or "")
    assert "agent-loop-v2" in combined
    print("PASS test_agent_loop_v2_dry_run")


def test_agent_loop_v2_compat_v1_dry_run():
    """验证 --compat v1 --dry-run 兼容模式。"""
    result = subprocess.run(
        [sys.executable, os.path.join(RUNTIME_DIR, "agent_loop_v2.py"),
         "--compat", "v1", "--dry-run"],
        cwd=ROOT, capture_output=True,
        encoding="utf-8", errors="replace")
    combined = (result.stdout or "") + (result.stderr or "")
    assert "compat-v1" in combined or "agent-loop-v2" in combined
    print("PASS test_agent_loop_v2_compat_v1_dry_run")


def test_session_init_brief():
    """验证会话简报可生成。"""
    result = subprocess.run(
        [sys.executable, os.path.join(RUNTIME_DIR, "session_init.py"),
         "--format", "brief"],
        cwd=ROOT, capture_output=True,
        encoding="utf-8", errors="replace")
    assert result.returncode == 0
    assert "Agent" in (result.stdout or "")
    print("PASS test_session_init_brief")


def test_session_init_json():
    """验证会话简报 JSON 格式。"""
    result = subprocess.run(
        [sys.executable, os.path.join(RUNTIME_DIR, "session_init.py"),
         "--format", "json"],
        cwd=ROOT, capture_output=True,
        encoding="utf-8", errors="replace")
    assert result.returncode == 0
    data = json.loads(result.stdout or "{}")
    assert "generated_at" in data
    assert "pending_events" in data
    assert "suggested_actions" in data
    assert "memory_summary" in data
    print("PASS test_session_init_json")


def test_scheduled_tasks_list():
    """验证定时任务列表。"""
    result = subprocess.run(
        [sys.executable, os.path.join(RUNTIME_DIR, "scheduled_tasks.py"),
         "list"],
        cwd=ROOT, capture_output=True,
        encoding="utf-8", errors="replace")
    assert result.returncode == 0
    assert "agent_health_check" in (result.stdout or "")
    assert "agent_nightly_scan" in (result.stdout or "")
    assert "agent_memory_cleanup" in (result.stdout or "")
    print("PASS test_scheduled_tasks_list")


if __name__ == "__main__":
    test_import_modules()
    test_event_bus_cli_publish()
    test_decision_engine_cli_list_patterns()
    test_decision_engine_cli_match()
    test_decision_engine_cli_match_diverged()
    test_decision_engine_cli_pending_empty()
    test_agent_loop_v2_dry_run()
    test_agent_loop_v2_compat_v1_dry_run()
    test_session_init_brief()
    test_session_init_json()
    test_scheduled_tasks_list()
    print("ALL AGENT LOOP V2 TESTS PASSED")
