#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""decision_engine.py — 决策引擎（Phase A 核心）

基于模式匹配的决策系统：加载 JSON 决策模式 → 匹配事件 → 执行动作 → 记录决策。

设计原则：
  - auto_execute=true 仅用于已有安全保护的操作
  - 未匹配模式 → 写入待决策队列，等宿主 LLM 处理
  - 所有决策留痕到 42_决策记录.jsonl
  - 动作执行通过 subprocess 调用现有 tools/*.py（零逻辑复制）

CLI（跨平台）：
  py -3.11 tools/agent_runtime/decision_engine.py match --event-json '{"type":"git.commit"}'
  py -3.11 tools/agent_runtime/decision_engine.py execute --decision-id DEC-xxx
  py -3.11 tools/agent_runtime/decision_engine.py list-patterns
  py -3.11 tools/agent_runtime/decision_engine.py pending              # 待决策队列
  py -3.11 tools/agent_runtime/decision_engine.py history [--limit 20]
"""
import os
import sys
import io
import json
import datetime
import argparse
import subprocess

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
TOOLS = os.path.join(ROOT, "tools")
PATTERNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patterns")
DECISION_LEDGER = os.path.join(ROOT, "台账", "42_决策记录.jsonl")
PENDING_QUEUE = os.path.join(ROOT, "台账", "41_待决策队列.jsonl")


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _print_utf8(text):
    """Windows GBK 控制台安全输出。"""
    try:
        sys.stdout.buffer.write((str(text) + "\n").encode("utf-8"))
    except Exception:
        sys.stdout.write(str(text) + "\n")


def _run_tool(script, *args, dry_run=False):
    """调用现有 tools/*.py 脚本。

    Returns:
        dict: {"rc": int, "stdout": str, "stderr": str}
    """
    cmd = [sys.executable, os.path.join(TOOLS, script), *args]
    if dry_run:
        return {"rc": 0, "stdout": "[dry-run] 将执行: %s" % " ".join(cmd),
                "stderr": "", "dry_run": True}
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=120)
        stdout = r.stdout.decode("utf-8", errors="replace")[:2000]
        stderr = r.stderr.decode("utf-8", errors="replace")[:1000]
        return {"rc": r.returncode, "stdout": stdout, "stderr": stderr}
    except subprocess.TimeoutExpired:
        return {"rc": -1, "stdout": "", "stderr": "执行超时(120s)"}
    except Exception as e:
        return {"rc": -1, "stdout": "", "stderr": str(e)}


# ─── 动作注册表 ──────────────────────────────────────────────
# 每个动作对应一个函数，接收 params dict + event dict，返回结果 dict

def _action_run_gates_and_push(params, event, dry_run=False):
    """提交事件 → 三道门禁 + 双推（兼容 agent_loop v1）。"""
    results = {}
    for gate in ("check_version_consistency.py", "check_skill_closure.py",
                 "check_skill_release_gate.py"):
        r = _run_tool(gate, dry_run=dry_run)
        results[gate] = "PASS" if r["rc"] == 0 else "FAIL"

    all_pass = all(v == "PASS" for v in results.values())
    push_result = "跳过(门禁未过)"
    if all_pass and not dry_run:
        pr = _run_tool("mirror_push.py")
        push_result = "成功" if pr["rc"] == 0 else ("跳过(阻断)" if pr["rc"] == 2 else "失败")
    elif all_pass and dry_run:
        push_result = "跳过(dry-run)"

    return {"gates": results, "all_pass": all_pass, "push": push_result}


def _action_self_heal(params, event, dry_run=False):
    """远端分叉 → 调用 self_heal。"""
    args = []
    if dry_run or params.get("dry_run"):
        args.append("--dry-run")
    return _run_tool("self_heal.py", *args)


def _action_escalate(params, event, dry_run=False):
    """升级：写待决策队列 + 记录。"""
    decision = {
        "ts": _now(),
        "event_type": event.get("type", "unknown"),
        "event_id": event.get("event_id", ""),
        "action": "escalate",
        "params": params,
        "reason": "事件需人工/宿主决策",
        "status": "pending",
    }
    if not dry_run:
        _append_jsonl(PENDING_QUEUE, decision)
    return {"status": "queued", "decision": decision}


def _action_nightly_quality_gate(params, event, dry_run=False):
    """夜间质量扫描。"""
    target = params.get("target", "")
    args = ["run"]
    if target:
        args.extend(["--target", target])
    return _run_tool("quality_gate.py", *args, dry_run=dry_run)


def _action_code_review(params, event, dry_run=False):
    """OPT-REVIEW-002: 提交后代码审查 → T-08 code_review_agent。"""
    diff_range = params.get("diff_range", "HEAD~1")
    args = ["--diff", diff_range]
    if dry_run:
        args.append("--dry-run")
    return _run_tool("code_review_agent.py", *args, dry_run=dry_run)


def _action_security_scan(params, event, dry_run=False):
    """OPT-REVIEW-002: 依赖漏洞扫描 → T-09 dep_vuln_scan。"""
    args = []
    if params.get("offline"):
        args.append("--offline")
    return _run_tool("dep_vuln_scan.py", *args, dry_run=dry_run)


def _action_arch_compliance(params, event, dry_run=False):
    """OPT-REVIEW-002: 架构合规检查 → T-10 arch_compliance。"""
    adr_dir = params.get("adr_dir", os.path.join(ROOT, "架构资产"))
    args = ["--adr-dir", adr_dir]
    return _run_tool("arch_compliance.py", *args, dry_run=dry_run)


# 动作注册表
ACTION_REGISTRY = {
    "run_gates_and_push": _action_run_gates_and_push,
    "self_heal": _action_self_heal,
    "escalate": _action_escalate,
    "nightly_quality_gate": _action_nightly_quality_gate,
    "code_review": _action_code_review,
    "security_scan": _action_security_scan,
    "arch_compliance": _action_arch_compliance,
}


# ─── 决策引擎 ────────────────────────────────────────────────
class DecisionEngine:
    """模式匹配决策引擎。"""

    def __init__(self, patterns_dir=None):
        self.patterns_dir = patterns_dir or PATTERNS_DIR
        self.patterns = []
        self._load_patterns()

    def _load_patterns(self):
        """加载 default.json + custom.json（如存在）。"""
        self.patterns = []
        for fname in ("default.json", "custom.json"):
            path = os.path.join(self.patterns_dir, fname)
            if os.path.isfile(path):
                try:
                    with io.open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.patterns.extend(data.get("patterns", []))
                except Exception as e:
                    sys.stderr.write("[decision-engine] 加载 %s 失败: %s\n" % (fname, e))

    def match(self, event):
        """匹配事件到决策模式。

        Args:
            event: AgentEvent 实例或 dict

        Returns:
            dict or None: 匹配的决策模式
        """
        if hasattr(event, "to_dict"):
            ev_dict = event.to_dict()
        elif isinstance(event, dict):
            ev_dict = event
        else:
            return None

        ev_type = ev_dict.get("type", "")
        ev_payload = ev_dict.get("payload", {})

        for pattern in self.patterns:
            match_spec = pattern.get("match", {})
            # 匹配事件类型
            if match_spec.get("event") and match_spec["event"] != ev_type:
                continue
            # 匹配 payload 字段（如 task=nightly_scan）
            payload_match = True
            for key, val in match_spec.items():
                if key == "event":
                    continue
                if ev_payload.get(key) != val:
                    payload_match = False
                    break
            if payload_match:
                return pattern

        return None

    def decide(self, event, dry_run=False):
        """决策：匹配模式 → 执行或排队 → 记录。

        Returns:
            dict: {"matched": bool, "pattern_id": str, "action": str,
                   "auto_execute": bool, "result": dict, "decision_id": str}
        """
        if hasattr(event, "to_dict"):
            ev_dict = event.to_dict()
        elif isinstance(event, dict):
            ev_dict = event
        else:
            ev_dict = {}

        pattern = self.match(event)
        decision_id = "DEC-%s-%04d" % (
            datetime.datetime.now().strftime("%Y%m%d"),
            self._next_decision_seq())

        if pattern is None:
            # 未匹配 → 写待决策队列
            result = _action_escalate(
                {"reason": "无匹配模式，需人工/宿主决策"}, ev_dict, dry_run)
            decision = {
                "ts": _now(),
                "decision_id": decision_id,
                "event_type": ev_dict.get("type", "unknown"),
                "event_id": ev_dict.get("event_id", ""),
                "pattern_id": None,
                "action": "escalate",
                "auto_execute": False,
                "result": result,
                "note": "未匹配模式",
            }
            if not dry_run:
                _append_jsonl(DECISION_LEDGER, decision)
            return decision

        # 匹配成功
        action_name = pattern.get("action", "escalate")
        auto_exec = pattern.get("auto_execute", False)
        params = pattern.get("params", {})

        result = {}
        if auto_exec:
            action_fn = ACTION_REGISTRY.get(action_name)
            if action_fn:
                result = action_fn(params, ev_dict, dry_run)
            else:
                result = {"error": "未知动作: %s" % action_name}
                # 未知动作也升级
                _action_escalate({"reason": "动作未实现: %s" % action_name},
                                 ev_dict, dry_run)
        else:
            # 非自动执行 → 排队
            result = _action_escalate(
                {"reason": "模式 auto_execute=false，需确认",
                 "pattern_id": pattern.get("id")},
                ev_dict, dry_run)

        decision = {
            "ts": _now(),
            "decision_id": decision_id,
            "event_type": ev_dict.get("type", "unknown"),
            "event_id": ev_dict.get("event_id", ""),
            "pattern_id": pattern.get("id"),
            "action": action_name,
            "auto_execute": auto_exec,
            "risk": pattern.get("risk", "Tier2"),
            "result": result,
            "dry_run": dry_run,
        }
        if not dry_run:
            _append_jsonl(DECISION_LEDGER, decision)
        return decision

    def list_patterns(self):
        """返回所有已加载的决策模式。"""
        return self.patterns

    def pending_decisions(self, limit=20):
        """读取待决策队列。"""
        return _read_jsonl(PENDING_QUEUE)[-limit:]

    def decision_history(self, limit=20):
        """读取决策历史。"""
        return _read_jsonl(DECISION_LEDGER)[-limit:]

    def _next_decision_seq(self):
        rows = _read_jsonl(DECISION_LEDGER)
        n = 1
        for r in rows:
            did = r.get("decision_id", "")
            if did and "-" in did:
                try:
                    n = max(n, int(did.rsplit("-", 1)[-1]) + 1)
                except (ValueError, IndexError):
                    pass
        return n


# ─── 工具函数 ────────────────────────────────────────────────
def _append_jsonl(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_jsonl(path):
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
    return rows


# ─── CLI ─────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="决策引擎 CLI")
    sub = ap.add_subparsers(dest="cmd")

    # match
    p_match = sub.add_parser("match", help="匹配事件到决策模式")
    p_match.add_argument("--event-json", required=True, help="JSON 格式事件")
    p_match.add_argument("--dry-run", action="store_true")

    # execute（从待决策队列手动执行）
    p_exec = sub.add_parser("execute", help="手动执行待决策项")
    p_exec.add_argument("--decision-id", required=True)

    # list-patterns
    sub.add_parser("list-patterns", help="列出决策模式")

    # pending
    p_pending = sub.add_parser("pending", help="待决策队列")
    p_pending.add_argument("--limit", type=int, default=20)

    # history
    p_hist = sub.add_parser("history", help="决策历史")
    p_hist.add_argument("--limit", type=int, default=20)

    args = ap.parse_args()
    engine = DecisionEngine()

    if args.cmd == "match":
        try:
            ev = json.loads(args.event_json)
        except json.JSONDecodeError as e:
            _print_utf8("event-json 解析失败: %s" % e)
            sys.exit(2)
        decision = engine.decide(ev, dry_run=args.dry_run)
        _print_utf8(json.dumps(decision, ensure_ascii=False, indent=2))

    elif args.cmd == "execute":
        # 从待决策队列中找到对应项
        pending = engine.pending_decisions(limit=1000)
        target = None
        for p in pending:
            if p.get("decision_id") == args.decision_id:
                target = p
                break
        if not target:
            _print_utf8("未找到 %s" % args.decision_id)
            sys.exit(1)
        _print_utf8("待决策项: %s" % json.dumps(target, ensure_ascii=False))
        _print_utf8("（手动执行需直接调用对应工具）")

    elif args.cmd == "list-patterns":
        for p in engine.list_patterns():
            _print_utf8("[%s] %s → %s (auto=%s, risk=%s)"
                        % (p["id"], p.get("description", ""),
                           p.get("action", ""), p.get("auto_execute", False),
                           p.get("risk", "")))

    elif args.cmd == "pending":
        items = engine.pending_decisions(args.limit)
        if not items:
            _print_utf8("(待决策队列为空)")
        else:
            for item in items:
                _print_utf8("[%s] %s %s: %s"
                            % (item.get("decision_id", "?"), item.get("event_type", "?"),
                               item.get("ts", ""), item.get("reason", "")))

    elif args.cmd == "history":
        items = engine.decision_history(args.limit)
        if not items:
            _print_utf8("(无决策历史)")
        else:
            for item in items:
                _print_utf8("[%s] %s → %s (auto=%s, pattern=%s)"
                            % (item.get("decision_id", "?"), item.get("event_type", "?"),
                               item.get("action", "?"), item.get("auto_execute", False),
                               item.get("pattern_id", "none")))

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
