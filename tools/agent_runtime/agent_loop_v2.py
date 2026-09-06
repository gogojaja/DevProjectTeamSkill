#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent_loop_v2.py — 事件驱动主循环（Phase A 核心）

替代 agent_loop.py 的线性管道，升级为事件驱动循环：
  启动 → 加载决策模式 → 拉取事件 → 匹配模式 → 执行动作 → 记录效果 → 循环

触发方式：
  --trigger hook       由 .githooks/post-commit 调用（兼容 v1 行为）
  --trigger schedule   由 dev-task-scheduler 定时调用
  --trigger daemon     后台守护进程模式（持续监听事件总线）
  --trigger manual     手动触发（默认）
  --dry-run            只跑决策分析，不执行任何副作用
  --compat v1          完全兼容 agent_loop.py v1 行为

安全约定（铁律 #3 / #7 / #15）：
  - 不自行改写系统文件；仅复用既有工具
  - 门禁未过则不双推，仅记录
  - Tier3 操作保留 HITL 确认（auto_execute 默认 false）
  - 自动提交台账时置 AGENT_LOOP_ACTIVE=1 防递归

用法（跨平台）：
  py -3.11 tools/agent_runtime/agent_loop_v2.py
  py -3.11 tools/agent_runtime/agent_loop_v2.py --trigger hook
  py -3.11 tools/agent_runtime/agent_loop_v2.py --trigger schedule --event-type health.check
  py -3.11 tools/agent_runtime/agent_loop_v2.py --dry-run
  py -3.11 tools/agent_runtime/agent_loop_v2.py --compat v1
"""
import os
import sys
import io
import json
import csv
import datetime
import subprocess
import time
import argparse

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 确保可导入同包模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from event_bus import EventBus, AgentEvent, get_event_bus
from decision_engine import DecisionEngine

ROOT = os.environ.get(
    "PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
TOOLS = os.path.join(ROOT, "tools")
LEDGER = os.path.join(ROOT, "台账", "34_控制环执行记录.csv")
SYNC_LEDGER = os.path.join(ROOT, "台账", "32_镜像同步记录.csv")
BOM = b"\xef\xbb\xbf"

# 守护模式轮询间隔（秒）
DAEMON_POLL_INTERVAL = 10


def _run(script, *args, cwd=None):
    return subprocess.run(
        [sys.executable, os.path.join(TOOLS, script), *args],
        cwd=cwd or ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace")


def _gate_ok(name):
    return _run(name).returncode == 0


# ─── v1 兼容模式 ─────────────────────────────────────────────
def _run_v1(trigger="manual", dry_run=False):
    """完全兼容 agent_loop.py v1 行为。"""
    start = datetime.datetime.now()
    v = _gate_ok("check_version_consistency.py")
    c = _gate_ok("check_skill_closure.py")
    rel = _gate_ok("check_skill_release_gate.py")
    all_pass = v and c and rel

    push_txt = "跳过(dry-run)" if dry_run else "跳过(门禁未过)"
    if all_pass and not dry_run:
        pr = _run("mirror_push.py")
        if pr.returncode == 0:
            push_txt = "成功"
        elif pr.returncode == 2:
            push_txt = "跳过(阻断)"
        else:
            push_txt = "失败"

    elapsed = (datetime.datetime.now() - start).total_seconds()
    seq = _next_seq()
    rid = "AL-%s-%03d" % (datetime.date.today().strftime("%Y%m%d"), seq)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    note = "门禁全过" if all_pass else "门禁未过，未双推，待人工处置"
    if all_pass and not dry_run and push_txt == "失败":
        note = "门禁全过但双推失败(网络/凭据)"
    elif all_pass and not dry_run and push_txt == "跳过(阻断)":
        note = "双推被熔断(凭据/网络)"

    _append_csv_ledger([rid, now, trigger,
                        "通过" if v else "失败", "通过" if c else "失败",
                        "通过" if rel else "失败", push_txt,
                        "%.1f" % elapsed, note])

    commit_ok = True
    if all_pass and not dry_run:
        commit_ok = _safe_git_commit(rid)

    print("[agent-loop-v2/compat-v1] trigger=%s 版本=%s 闭环=%s 发布=%s 双推=%s 提交=%s (%.1fs)"
          % (trigger, "PASS" if v else "FAIL", "PASS" if c else "FAIL",
             "PASS" if rel else "FAIL", push_txt,
             "OK" if commit_ok else "SKIP/FAIL", elapsed))
    return all_pass


# ─── v2 事件驱动模式 ─────────────────────────────────────────
def _run_v2(trigger="manual", event_type=None, dry_run=False):
    """v2 事件驱动循环：单次触发。"""
    bus = get_event_bus()
    engine = DecisionEngine()
    start = datetime.datetime.now()

    # 1. 如果是 hook 触发，发布 git.commit 事件
    if trigger == "hook":
        ev = AgentEvent("git.commit", {"trigger": "post-commit"},
                        priority="P1", source="hook")
        bus.publish(ev)

    # 2. 如果指定了事件类型，发布对应事件
    if event_type and event_type != "git.commit":
        ev = AgentEvent(event_type, {"trigger": trigger},
                        priority="P1", source=trigger)
        bus.publish(ev)

    # 3. 拉取事件并逐个决策
    events = bus.drain(limit=20)
    decisions = []
    for ev in events:
        decision = engine.decide(ev, dry_run=dry_run)
        decisions.append(decision)

    elapsed = (datetime.datetime.now() - start).total_seconds()

    # 4. 汇总结果
    auto_count = sum(1 for d in decisions if d.get("auto_execute"))
    pending_count = sum(1 for d in decisions if not d.get("auto_execute"))
    matched_count = sum(1 for d in decisions if d.get("pattern_id"))

    # 5. 写入控制环记录
    if not dry_run:
        _record_v2_execution(trigger, decisions, elapsed)

    print("[agent-loop-v2] trigger=%s events=%d matched=%d auto=%d pending=%d (%.1fs)%s"
          % (trigger, len(events), matched_count, auto_count, pending_count,
             elapsed, " [dry-run]" if dry_run else ""))

    # 6. 输出决策摘要
    for d in decisions:
        status = "AUTO" if d.get("auto_execute") else "PENDING"
        print("  [%s] %s → %s (pattern=%s)"
              % (status, d.get("event_type", "?"), d.get("action", "?"),
                 d.get("pattern_id", "none")))

    return pending_count == 0  # 全部自动处理则返回 True


def _run_daemon(dry_run=False):
    """守护进程模式：持续监听事件总线。"""
    print("[agent-loop-v2/daemon] 启动（轮询间隔 %ds）%s"
          % (DAEMON_POLL_INTERVAL, "[dry-run]" if dry_run else ""))
    try:
        while True:
            _run_v2(trigger="daemon", dry_run=dry_run)
            time.sleep(DAEMON_POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n[agent-loop-v2/daemon] 已停止")


# ─── 辅助函数 ────────────────────────────────────────────────
def _next_seq():
    if not os.path.exists(LEDGER):
        return 1
    with io.open(LEDGER, "r", encoding="utf-8-sig") as f:
        lines = [l for l in f.read().splitlines() if l.strip()]
    return max(0, len(lines) - 1) + 1


def _append_csv_ledger(row):
    header = ["运行编号", "运行时间", "触发源", "版本一致性门禁", "闭环门禁",
              "发布级门禁", "双推结果", "耗时秒", "说明"]
    new = not os.path.exists(LEDGER)
    with io.open(LEDGER, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


def _record_v2_execution(trigger, decisions, elapsed):
    """记录 v2 执行到控制环台账。"""
    seq = _next_seq()
    rid = "AL-%s-%03d" % (datetime.date.today().strftime("%Y%m%d"), seq)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    auto_count = sum(1 for d in decisions if d.get("auto_execute"))
    pending_count = sum(1 for d in decisions if not d.get("auto_execute"))
    note = "自动处理=%d 待决策=%d" % (auto_count, pending_count)

    _append_csv_ledger([rid, now, "v2:" + trigger,
                        "v2", "v2", "v2",  # v2 不使用单门禁列
                        "N/A", "%.1f" % elapsed, note])

    # 自动提交台账
    _safe_git_commit(rid)


def _safe_git_commit(rid, msg=None):
    """安全提交台账（防递归）。"""
    env = dict(os.environ)
    env["AGENT_LOOP_ACTIVE"] = "1"

    # 检查是否有变更
    changed = False
    for path in (LEDGER, SYNC_LEDGER):
        if os.path.exists(path):
            r = subprocess.run(
                ["git", "status", "--short", "--", path],
                cwd=ROOT, capture_output=True, text=True,
                encoding="utf-8", errors="replace")
            if r.stdout.strip():
                changed = True
                break

    if not changed:
        return False

    # git add
    files_to_add = [f for f in (LEDGER, SYNC_LEDGER) if os.path.exists(f)]
    add = subprocess.run(
        ["git", "add"] + files_to_add,
        cwd=ROOT, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    if add.returncode != 0:
        return False

    # git commit
    commit_msg = msg or ("chore(agent-loop-v2): 控制环执行记录 %s" % rid)
    commit = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=ROOT, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    return commit.returncode == 0


# ─── CLI ─────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Agent 主循环 v2")
    ap.add_argument("--trigger", default="manual",
                    choices=["hook", "schedule", "daemon", "manual"],
                    help="触发方式")
    ap.add_argument("--event-type", default=None,
                    help="手动指定事件类型（schedule 模式用）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只跑决策分析，不执行副作用")
    ap.add_argument("--compat", default=None,
                    choices=["v1"],
                    help="兼容模式（v1=完全兼容 agent_loop.py）")
    args = ap.parse_args()

    # v1 兼容
    if args.compat == "v1":
        ok = _run_v1(trigger=args.trigger, dry_run=args.dry_run)
        sys.exit(0 if ok else 1)

    # 守护模式
    if args.trigger == "daemon":
        _run_daemon(dry_run=args.dry_run)
        return

    # v2 单次触发
    ok = _run_v2(trigger=args.trigger, event_type=args.event_type,
                 dry_run=args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
