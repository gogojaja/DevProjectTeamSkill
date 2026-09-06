#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""session_init.py — 会话初始化简报（Phase A 预留，Phase B 增强）

宿主 LLM 启动时调用，生成结构化简报：
  - 自上次会话以来的变更摘要
  - 待处理事件
  - 自动已处理记录
  - 建议行动（按优先级排序）
  - 记忆摘要

Phase A：基础框架，从事件总线和决策记录生成简报。
Phase B：增强为完整的会话自主层（含目标追踪、自适应建议）。

CLI（跨平台）：
  py -3.11 tools/agent_runtime/session_init.py                # 生成完整简报
  py -3.11 tools/agent_runtime/session_init.py --format json   # JSON 格式
  py -3.11 tools/agent_runtime/session_init.py --format brief  # 简要格式
"""
import os
import sys
import io
import json
import csv
import datetime
import argparse

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from event_bus import get_event_bus
from decision_engine import DecisionEngine

ROOT = os.environ.get(
    "PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
CONTROL_LEDGER = os.path.join(ROOT, "台账", "34_控制环执行记录.csv")
MEMORY_STORE = os.path.join(ROOT, "台账", "38_项目记忆.jsonl")


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _read_jsonl(path, limit=100):
    if not os.path.exists(path):
        return []
    rows = []
    with io.open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows[-limit:]


def _read_csv_ledger(path, limit=50):
    if not os.path.exists(path):
        return []
    with io.open(path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    return rows[-limit:] if len(rows) > 1 else []


# ─── 简报生成 ────────────────────────────────────────────────
class SessionBriefing:
    """会话简报生成器。"""

    def __init__(self):
        self.bus = get_event_bus()
        self.engine = DecisionEngine()

    def generate(self, fmt="text"):
        """生成会话简报。

        Args:
            fmt: "text"（默认文本）/ "json" / "brief"（简要）

        Returns:
            str: 简报内容
        """
        now = _now()
        data = self._collect_data()

        if fmt == "json":
            return json.dumps({
                "generated_at": now,
                "changes": data["changes"],
                "pending_events": data["pending_events"],
                "auto_processed": data["auto_processed"],
                "suggested_actions": data["suggested_actions"],
                "memory_summary": data["memory_summary"],
            }, ensure_ascii=False, indent=2)

        if fmt == "brief":
            return self._format_brief(data, now)

        return self._format_full(data, now)

    def _collect_data(self):
        """收集简报数据。"""
        # 1. 控制环执行记录（最近 10 条）
        control_records = _read_csv_ledger(CONTROL_LEDGER, limit=10)

        # 2. 待处理事件
        pending = self.bus.drain(limit=20)
        pending_events = []
        for ev in pending:
            pending_events.append({
                "id": ev.event_id,
                "type": ev.event_type,
                "priority": ev.priority,
                "source": ev.source,
                "ts": ev.ts,
            })

        # 3. 待决策队列
        pending_decisions = self.engine.pending_decisions(limit=10)

        # 4. 最近自动处理
        history = self.engine.decision_history(limit=10)
        auto_processed = [d for d in history if d.get("auto_execute")]

        # 5. 记忆摘要
        memory_records = _read_jsonl(MEMORY_STORE, limit=20)
        memory_summary = self._summarize_memory(memory_records)

        # 6. 建议行动
        suggested_actions = self._generate_suggestions(
            pending_events, pending_decisions, memory_summary)

        # 7. 变更摘要
        changes = self._summarize_changes(control_records)

        return {
            "changes": changes,
            "pending_events": pending_events,
            "auto_processed": auto_processed[-5:],  # 最近 5 条
            "suggested_actions": suggested_actions,
            "memory_summary": memory_summary,
        }

    def _summarize_changes(self, control_records):
        """汇总控制环记录。"""
        if not control_records:
            return {"commits": 0, "push_status": "unknown", "gate_status": "unknown"}

        # 统计最近的执行
        total = len(control_records) - 1  # 减去表头
        push_results = {}
        gate_pass = 0
        gate_fail = 0

        for row in control_records[1:]:  # 跳过表头
            if len(row) >= 7:
                push_result = row[6] if len(row) > 6 else "N/A"
                push_results[push_result] = push_results.get(push_result, 0) + 1
                # 检查门禁（v1 格式有版本/闭环/发布列）
                if len(row) >= 6:
                    if row[3] == "通过" and row[4] == "通过" and row[5] == "通过":
                        gate_pass += 1
                    elif row[3] in ("v1", "v2"):
                        pass  # v2 格式不检查单门禁
                    else:
                        gate_fail += 1

        gate_status = "全绿" if gate_fail == 0 else ("%d 通过 / %d 失败" % (gate_pass, gate_fail))
        return {
            "executions": total,
            "push_status": push_results,
            "gate_status": gate_status,
        }

    def _summarize_memory(self, records):
        """生成记忆摘要。"""
        by_type = {}
        for r in records:
            t = r.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        # 提取关键记忆
        active_decisions = [r for r in records if r.get("type") == "decision"]
        active_todos = [r for r in records if r.get("type") == "todo"]
        risks = [r for r in records if r.get("type") == "risk"]

        return {
            "total": len(records),
            "by_type": by_type,
            "recent_decisions": active_decisions[-3:],
            "recent_todos": active_todos[-5:],
            "recent_risks": risks[-3:],
        }

    def _generate_suggestions(self, pending_events, pending_decisions, memory_summary):
        """生成建议行动。"""
        suggestions = []

        # 1. 待决策项
        for d in pending_decisions[:3]:
            suggestions.append({
                "priority": "P1",
                "action": "处理待决策项",
                "detail": d.get("reason", ""),
                "command": "py -3.11 tools/agent_runtime/decision_engine.py pending",
                "risk": "Tier2",
            })

        # 2. 高优先级事件
        for ev in pending_events[:3]:
            if ev["priority"] in ("P0", "P1"):
                suggestions.append({
                    "priority": ev["priority"],
                    "action": "处理 %s 事件" % ev["type"],
                    "detail": "来源: %s, 时间: %s" % (ev["source"], ev["ts"]),
                    "command": "py -3.11 tools/agent_runtime/agent_loop_v2.py --trigger manual",
                    "risk": "Tier2",
                })

        # 3. 未完成待办
        for todo in memory_summary.get("recent_todos", [])[:2]:
            suggestions.append({
                "priority": "P2",
                "action": "跟进待办",
                "detail": todo.get("text", ""),
                "command": "",
                "risk": "Tier1",
            })

        # 按优先级排序
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        suggestions.sort(key=lambda s: priority_order.get(s.get("priority", "P2"), 2))

        return suggestions[:5]  # 最多 5 条建议

    def _format_full(self, data, now):
        """格式化完整简报。"""
        lines = [
            "=" * 50,
            " Agent 会话简报 (%s)" % now,
            "=" * 50,
            "",
        ]

        # 变更摘要
        changes = data["changes"]
        lines.append("[变更摘要] 自上次会话以来：")
        lines.append("  - 控制环执行: %d 次" % changes.get("executions", 0))
        lines.append("  - 双推状态: %s" % changes.get("push_status", "unknown"))
        lines.append("  - 门禁状态: %s" % changes.get("gate_status", "unknown"))
        lines.append("")

        # 待处理事件
        pending = data["pending_events"]
        lines.append("[待处理事件] %d 项" % len(pending))
        for i, ev in enumerate(pending[:5], 1):
            lines.append("  %d. [%s] %s（事件 %s, 来源 %s）"
                         % (i, ev["priority"], ev["type"], ev["id"], ev["source"]))
        if not pending:
            lines.append("  (无)")
        lines.append("")

        # 自动已处理
        auto = data["auto_processed"]
        lines.append("[自动已处理] %d 项" % len(auto))
        for d in auto[-3:]:
            lines.append("  - %s → %s (pattern=%s)"
                         % (d.get("event_type", "?"), d.get("action", "?"),
                            d.get("pattern_id", "none")))
        if not auto:
            lines.append("  (无)")
        lines.append("")

        # 建议行动
        suggestions = data["suggested_actions"]
        lines.append("[建议行动] 按优先级排序")
        for i, s in enumerate(suggestions, 1):
            lines.append("  %d. [%s] %s（%s, %s）"
                         % (i, s["priority"], s["action"],
                            s.get("risk", ""), s.get("detail", "")[:60]))
            if s.get("command"):
                lines.append("     命令: %s" % s["command"])
        if not suggestions:
            lines.append("  (无建议)")
        lines.append("")

        # 记忆摘要
        mem = data["memory_summary"]
        lines.append("[记忆摘要]")
        lines.append("  - 总记忆: %d 条" % mem.get("total", 0))
        lines.append("  - 近期决策: %d 条" % len(mem.get("recent_decisions", [])))
        lines.append("  - 未完成待办: %d 条" % len(mem.get("recent_todos", [])))
        lines.append("  - 已知风险: %d 条" % len(mem.get("recent_risks", [])))

        return "\n".join(lines)

    def _format_brief(self, data, now):
        """格式化简要简报。"""
        pending_count = len(data["pending_events"])
        suggestion_count = len(data["suggested_actions"])
        return ("Agent 简报 @%s: 待处理 %d 项, 建议 %d 项, 记忆 %d 条"
                % (now, pending_count, suggestion_count,
                   data["memory_summary"].get("total", 0)))


# ─── CLI ─────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="会话初始化简报")
    ap.add_argument("--format", default="text",
                    choices=["text", "json", "brief"],
                    help="输出格式")
    args = ap.parse_args()

    briefing = SessionBriefing()
    print(briefing.generate(fmt=args.format))


if __name__ == "__main__":
    main()
