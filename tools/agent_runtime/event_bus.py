#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""event_bus.py — 事件总线（Phase A 核心）

轻量发布-订阅模型，连接所有触发源（git hook / 定时 / 健康检查 / 手动）
到决策引擎。事件持久化到 JSONL（UTF-8），支持限速合并与优先级。

铁律 #3（SEC-003）：事件台账禁止承载 A 级信息（密钥/Token），
写入前对 payload 做脱敏，命中 token/secret 模式即替换。

CLI（跨平台）：
  py -3.11 tools/agent_runtime/event_bus.py publish --type git.commit [--payload '{"key":"val"}']
  py -3.11 tools/agent_runtime/event_bus.py drain [--type git.commit] [--limit 20]
  py -3.11 tools/agent_runtime/event_bus.py stats                     # 事件统计
  py -3.11 tools/agent_runtime/event_bus.py pending                   # 待处理事件数
"""
import os
import sys
import io
import json
import re
import datetime
import argparse
import hashlib

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get(
    "PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
LEDGER = os.path.join(ROOT, "台账", "40_事件总线.jsonl")

# ─── 事件类型枚举 ───────────────────────────────────────────
EVENT_TYPES = {
    "git.commit",       # post-commit 钩子触发
    "git.push_fail",    # 推送失败
    "git.diverged",     # 远端分叉
    "schedule.tick",    # 定时触发（对接 scheduler）
    "health.check",     # 健康检查异常
    "gate.fail",        # 门禁失败
    "file.change",      # 关键文件变更
    "manual",           # 手动触发
}

# ─── 敏感信息正则（铁律 #3） ────────────────────────────────
SECRET_RE = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}"
    r"|token[\"=:\s]{0,4}[A-Za-z0-9_\-]{16,}"
    r"|secret[\"=:\s]{0,4}[A-Za-z0-9_\-]{16,}"
    r"|password[\"=:\s]{0,4}[A-Za-z0-9_\-]{8,})",
    re.IGNORECASE,
)

# ─── 限速窗口（秒）：同类事件在此窗口内合并 ─────────────────
RATE_LIMIT_WINDOW = 300  # 5 分钟


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _redact(text):
    """脱敏：替换 A 级凭据模式。"""
    if not text:
        return text
    if isinstance(text, dict):
        return {k: _redact(v) for k, v in text.items()}
    return SECRET_RE.sub("***[脱敏]***", str(text))


def _event_hash(event_type, payload):
    """同类事件限速用的摘要哈希。"""
    key = "%s:%s" % (event_type, json.dumps(payload, sort_keys=True, ensure_ascii=False))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


# ─── AgentEvent ──────────────────────────────────────────────
class AgentEvent:
    """智能体事件。

    Attributes:
        event_type: 事件类型（见 EVENT_TYPES）
        payload:    事件负载（dict，禁止含 A 级信息）
        priority:   优先级 P0(最高)~P3(最低)
        source:     事件来源（hook/schedule/manual/health）
    """

    def __init__(self, event_type, payload=None, priority="P2", source="manual"):
        if event_type not in EVENT_TYPES:
            raise ValueError("未知事件类型: %s（合法值: %s）"
                             % (event_type, ", ".join(sorted(EVENT_TYPES))))
        self.event_type = event_type
        self.payload = _redact(payload or {})
        self.priority = priority if priority in ("P0", "P1", "P2", "P3") else "P2"
        self.source = source
        self.ts = _now()
        self.event_id = ""  # 写入时分配

    def to_dict(self):
        return {
            "ts": self.ts,
            "event_id": self.event_id,
            "type": self.event_type,
            "priority": self.priority,
            "source": self.source,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, d):
        ev = cls.__new__(cls)
        ev.ts = d.get("ts", "")
        ev.event_id = d.get("event_id", "")
        ev.event_type = d.get("type", "manual")
        ev.priority = d.get("priority", "P2")
        ev.source = d.get("source", "manual")
        ev.payload = d.get("payload", {})
        return ev

    def __repr__(self):
        return ("AgentEvent(%s, priority=%s, source=%s, payload_keys=%s)"
                % (self.event_type, self.priority, self.source,
                   list(self.payload.keys()) if isinstance(self.payload, dict) else "?"))


# ─── EventBus ────────────────────────────────────────────────
class EventBus:
    """事件总线：发布-订阅 + JSONL 持久化 + 限速合并。"""

    def __init__(self, ledger_path=None):
        self.ledger_path = ledger_path or LEDGER
        self._handlers = {}   # event_type -> [callable, ...]
        self._seq = 0
        self._recent_hashes = {}  # hash -> timestamp（限速用）

    # ── 发布 ──────────────────────────────────────────────
    def publish(self, event):
        """发布事件：脱敏 → 限速检查 → 持久化 → 通知订阅者。

        Returns:
            True=已发布, False=被限速合并
        """
        if not isinstance(event, AgentEvent):
            raise TypeError("参数须为 AgentEvent 实例")

        # 限速检查
        eh = _event_hash(event.event_type, event.payload)
        now_ts = datetime.datetime.now()
        if eh in self._recent_hashes:
            last = self._recent_hashes[eh]
            if (now_ts - last).total_seconds() < RATE_LIMIT_WINDOW:
                return False  # 被限速合并
        self._recent_hashes[eh] = now_ts

        # 清理过期限速记录（>2 倍窗口）
        cutoff = now_ts - datetime.timedelta(seconds=RATE_LIMIT_WINDOW * 2)
        self._recent_hashes = {
            k: v for k, v in self._recent_hashes.items() if v > cutoff
        }

        # 分配事件 ID
        self._seq += 1
        event.event_id = "EVT-%s-%04d" % (
            datetime.datetime.now().strftime("%Y%m%d"), self._seq)

        # 持久化
        self._append_jsonl(event.to_dict())

        # 通知订阅者
        handlers = self._handlers.get(event.event_type, [])
        for h in handlers:
            try:
                h(event)
            except Exception as e:
                # 订阅者异常不影响总线
                sys.stderr.write("[event-bus] handler 异常: %s\n" % e)

        return True

    # ── 订阅 ──────────────────────────────────────────────
    def subscribe(self, event_type, handler):
        """注册事件处理器。

        Args:
            event_type: 事件类型（支持 "*" 表示全部）
            handler:    callable(AgentEvent) -> None
        """
        if event_type != "*" and event_type not in EVENT_TYPES:
            raise ValueError("未知事件类型: %s" % event_type)
        if not callable(handler):
            raise TypeError("handler 须为 callable")
        self._handlers.setdefault(event_type, []).append(handler)

    # ── 拉取未处理事件 ────────────────────────────────────
    def drain(self, event_type=None, limit=50):
        """拉取事件（默认全部，可按类型过滤）。

        Returns:
            list[AgentEvent]
        """
        rows = self._read_jsonl()
        if event_type:
            rows = [r for r in rows if r.get("type") == event_type]
        # 按优先级排序（P0 最高）
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        rows.sort(key=lambda r: priority_order.get(r.get("priority", "P2"), 2))
        return [AgentEvent.from_dict(r) for r in rows[-limit:]]

    # ── 统计 ──────────────────────────────────────────────
    def stats(self):
        """返回事件统计 dict。"""
        rows = self._read_jsonl()
        by_type = {}
        by_priority = {}
        for r in rows:
            t = r.get("type", "unknown")
            p = r.get("priority", "P2")
            by_type[t] = by_type.get(t, 0) + 1
            by_priority[p] = by_priority.get(p, 0) + 1
        return {
            "total": len(rows),
            "by_type": by_type,
            "by_priority": by_priority,
        }

    def pending_count(self):
        """待处理事件数（全部事件，因当前无消费确认机制）。"""
        return len(self._read_jsonl())

    # ── 内部方法 ──────────────────────────────────────────
    def _append_jsonl(self, record):
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        with io.open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _read_jsonl(self):
        if not os.path.exists(self.ledger_path):
            return []
        rows = []
        with io.open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
        return rows


# ─── 全局单例 ────────────────────────────────────────────────
_event_bus = None


def get_event_bus():
    """获取全局事件总线单例。"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# ─── CLI ─────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="事件总线 CLI")
    sub = ap.add_subparsers(dest="cmd")

    # publish
    p_pub = sub.add_parser("publish", help="发布事件")
    p_pub.add_argument("--type", required=True, help="事件类型")
    p_pub.add_argument("--payload", default="{}", help="JSON 格式负载")
    p_pub.add_argument("--priority", default="P2", help="优先级 P0~P3")
    p_pub.add_argument("--source", default="manual", help="事件来源")

    # drain
    p_drain = sub.add_parser("drain", help="拉取事件")
    p_drain.add_argument("--type", default=None, help="按类型过滤")
    p_drain.add_argument("--limit", type=int, default=50, help="最大返回数")

    # stats
    sub.add_parser("stats", help="事件统计")

    # pending
    sub.add_parser("pending", help="待处理事件数")

    args = ap.parse_args()
    bus = get_event_bus()

    if args.cmd == "publish":
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as e:
            print("payload JSON 解析失败: %s" % e)
            sys.exit(2)
        ev = AgentEvent(args.type, payload, args.priority, args.source)
        ok = bus.publish(ev)
        if ok:
            print("已发布 %s (id=%s)" % (ev.event_type, ev.event_id))
        else:
            print("被限速合并（5 分钟内同类事件）")

    elif args.cmd == "drain":
        events = bus.drain(args.type, args.limit)
        if not events:
            print("(无事件)")
        else:
            for ev in events:
                print("[%s] %s %s/%s: %s"
                      % (ev.event_id, ev.event_type, ev.priority,
                         ev.source, json.dumps(ev.payload, ensure_ascii=False)[:120]))

    elif args.cmd == "stats":
        s = bus.stats()
        print("事件总数: %d" % s["total"])
        for t, c in sorted(s["by_type"].items()):
            print("  %s: %d" % (t, c))
        print("按优先级:")
        for p in ("P0", "P1", "P2", "P3"):
            if p in s["by_priority"]:
                print("  %s: %d" % (p, s["by_priority"][p]))

    elif args.cmd == "pending":
        print("待处理: %d" % bus.pending_count())

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
