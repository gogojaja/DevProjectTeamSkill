#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scheduled_tasks.py — Agent 定时任务注册（Phase A 触发源集成）

对接 dev-task-scheduler 的定时任务注册模块。
注册 Agent 运行时的周期性任务：健康检查、夜间扫描、记忆清理等。

用法（作为模块导入）：
  from tools.agent_runtime.scheduled_tasks import register_agent_tasks
  register_agent_tasks()  # 注册所有 Agent 定时任务到 scheduler

用法（CLI 查看注册的任务）：
  py -3.11 tools/agent_runtime/scheduled_tasks.py list
  py -3.11 tools/agent_runtime/scheduled_tasks.py run <task_name>
"""
import os
import sys
import json
import datetime
import subprocess
import argparse

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from event_bus import AgentEvent, get_event_bus

ROOT = os.environ.get(
    "PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
TOOLS = os.path.join(ROOT, "tools")


def _run_tool(script, *args):
    """调用工具脚本。"""
    cmd = [sys.executable, os.path.join(TOOLS, script), *args]
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        return {"rc": r.returncode, "stdout": r.stdout[:500], "stderr": r.stderr[:200]}
    except Exception as e:
        return {"rc": -1, "stdout": "", "stderr": str(e)}


# ─── 定时任务定义 ────────────────────────────────────────────

def task_health_check():
    """定期健康检查：远端同步状态 + 门禁健康。

    触发频率：每 4 小时
    动作：检查远端同步状态，异常时发布 health.check 事件
    """
    bus = get_event_bus()

    # 检查 git 远端状态
    result = _run_tool("mirror_push.py", "--verify")
    if result["rc"] != 0:
        bus.publish(AgentEvent(
            "health.check",
            {"check": "mirror_sync", "status": "anomaly",
             "detail": result["stderr"][:200] or result["stdout"][:200]},
            priority="P1", source="schedule"))
        return {"status": "anomaly", "action": "event_published"}

    # 检查门禁健康
    gates_ok = True
    for gate in ("check_version_consistency.py", "check_skill_closure.py"):
        r = _run_tool(gate)
        if r["rc"] != 0:
            gates_ok = False
            break

    if not gates_ok:
        bus.publish(AgentEvent(
            "health.check",
            {"check": "gate_health", "status": "fail"},
            priority="P2", source="schedule"))
        return {"status": "gate_fail", "action": "event_published"}

    return {"status": "healthy"}


def task_nightly_scan():
    """夜间扫描：质量门禁 + 脱敏复查。

    触发频率：每天凌晨 2:00
    动作：发布 schedule.tick 事件，由决策引擎处理
    """
    bus = get_event_bus()
    bus.publish(AgentEvent(
        "schedule.tick",
        {"task": "nightly_scan", "checks": ["quality_gate", "desensitize_review"]},
        priority="P2", source="schedule"))
    return {"status": "scan_triggered"}


def task_memory_cleanup():
    """记忆清理：清理 >90 天的过期事件/决策记录。

    触发频率：每天凌晨 3:00
    动作：压缩旧记录（保留统计摘要，删除详细记录）
    """
    bus = get_event_bus()
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")

    # 统计待清理记录数
    ledger_dir = os.path.join(ROOT, "台账")
    cleanup_files = [
        os.path.join(ledger_dir, "40_事件总线.jsonl"),
        os.path.join(ledger_dir, "42_决策记录.jsonl"),
    ]

    total_cleaned = 0
    for path in cleanup_files:
        if not os.path.exists(path):
            continue
        kept = []
        removed = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    ts = record.get("ts", "")
                    if ts >= cutoff:
                        kept.append(line)
                    else:
                        removed += 1
                except Exception:
                    kept.append(line)  # 解析失败保留

        if removed > 0:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(kept) + ("\n" if kept else ""))
            total_cleaned += removed

    return {"cleaned": total_cleaned, "cutoff": cutoff}


# ─── 任务注册表 ──────────────────────────────────────────────
AGENT_TASKS = {
    "agent_health_check": {
        "func": task_health_check,
        "trigger": "interval",
        "trigger_config": {"hours": 4},
        "description": "定期健康检查：远端同步 + 门禁健康",
    },
    "agent_nightly_scan": {
        "func": task_nightly_scan,
        "trigger": "cron",
        "trigger_config": {"hour": 2, "minute": 0},
        "description": "夜间扫描：质量门禁 + 脱敏复查",
    },
    "agent_memory_cleanup": {
        "func": task_memory_cleanup,
        "trigger": "cron",
        "trigger_config": {"hour": 3, "minute": 0},
        "description": "记忆清理：清理 >90 天过期记录",
    },
}


def register_agent_tasks():
    """注册所有 Agent 定时任务到 scheduler（如可用）。

    尝试导入 dev-task-scheduler 的注册装饰器；
    如不可用则仅返回任务定义（供外部集成）。
    """
    try:
        # 尝试导入 dev-task-scheduler
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        from scheduler import register_task

        for name, defn in AGENT_TASKS.items():
            trigger = defn["trigger"]
            config = defn["trigger_config"]
            register_task(
                name=name,
                trigger=trigger,
                description=defn["description"],
                **config
            )(defn["func"])

        return len(AGENT_TASKS)
    except ImportError:
        # dev-task-scheduler 不可用，返回任务定义供外部集成
        return AGENT_TASKS


# ─── CLI ─────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Agent 定时任务管理")
    sub = ap.add_subparsers(dest="cmd")

    # list
    sub.add_parser("list", help="列出注册的定时任务")

    # run
    p_run = sub.add_parser("run", help="手动执行指定任务")
    p_run.add_argument("task_name", help="任务名称")

    # dry-run
    p_dry = sub.add_parser("dry-run", help="预览任务执行计划")
    p_dry.add_argument("task_name", nargs="?", default=None)

    args = ap.parse_args()

    if args.cmd == "list":
        print("已注册 %d 个 Agent 定时任务：" % len(AGENT_TASKS))
        for name, defn in AGENT_TASKS.items():
            print("  [%s] %s (%s %s)"
                  % (name, defn["description"],
                     defn["trigger"], defn["trigger_config"]))

    elif args.cmd == "run":
        if args.task_name not in AGENT_TASKS:
            print("未知任务: %s（可用: %s）"
                  % (args.task_name, ", ".join(AGENT_TASKS.keys())))
            sys.exit(1)
        func = AGENT_TASKS[args.task_name]["func"]
        result = func()
        print("[%s] 执行完成: %s" % (args.task_name, json.dumps(result, ensure_ascii=False)))

    elif args.cmd == "dry-run":
        tasks = {args.task_name: AGENT_TASKS[args.task_name]} if args.task_name else AGENT_TASKS
        print("任务执行计划（dry-run）：")
        for name, defn in tasks.items():
            print("  [%s] %s → %s %s"
                  % (name, defn["trigger"], defn["func"].__name__,
                     defn["trigger_config"]))

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
