#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory_store.py — 结构化持久记忆服务（P2 运行时记忆层）

替代手工交接文档的脆弱长文本，提供跨会话可机读的决策/待办/上下文/风险记忆。
存储：台账/38_项目记忆.jsonl（UTF-8，每行一条 JSON）。导出：台账/38_项目记忆.csv（UTF-8 BOM）。
铁律：A 级信息（密钥/Token）禁止写入记忆；仅存脱敏后的决策与待办。

CLI（跨平台）：
  py -3.11 tools/memory_store.py add --type decision --text "..." [--meta 关联编号]
  py -3.11 tools/memory_store.py list [--type todo] [--limit 20]
  py -3.11 tools/memory_store.py query --keyword "关键词" [--type decision] [--since 2026-01-01]
  py -3.11 tools/memory_store.py summarize                    # 按类型分组统计 + 近期条目
  py -3.11 tools/memory_store.py expire [--days 90]           # 标记 >N 天条目为 expired
  py -3.11 tools/memory_store.py delete --index N             # 按序号删除
  py -3.11 tools/memory_store.py load [--limit 15]            # 输出可注入会话上下文的文本
  py -3.11 tools/memory_store.py export                       # 导出 BOM CSV
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

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STORE = os.path.join(ROOT, "台账", "38_项目记忆.jsonl")
CSV_OUT = os.path.join(ROOT, "台账", "38_项目记忆.csv")
VALID = {"decision", "todo", "context", "risk", "note"}
BOM = b"\xef\xbb\xbf"


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add(entry_type, text, meta=""):
    if entry_type not in VALID:
        print("类型须为: " + ", ".join(sorted(VALID)))
        sys.exit(2)
    rec = {"ts": _now(), "type": entry_type, "text": text, "meta": meta}
    with io.open(STORE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("已记录 %s @ %s" % (entry_type, rec["ts"]))


def _read_all():
    if not os.path.exists(STORE):
        return []
    out = []
    with io.open(STORE, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    return out


def list_entries(t=None, limit=20):
    rows = _read_all()
    if t:
        rows = [r for r in rows if r.get("type") == t]
    for r in rows[-limit:]:
        print("[%s] %s %s: %s" % (r["type"], r["ts"], r.get("meta", ""), r["text"]))


def load_context(limit=15):
    rows = _read_all()[-limit:]
    if not rows:
        return "(无记忆)"
    lines = ["- [%s] %s: %s" % (r["type"], r.get("meta", "") or r["ts"], r["text"])
             for r in rows]
    return "\n".join(lines)


def export_csv():
    rows = _read_all()
    header = ["时间", "类型", "内容", "关联", "状态"]
    with io.open(CSV_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([r["ts"], r["type"], r["text"], r.get("meta", ""), r.get("status", "active")])
    print("已导出 %d 条 -> %s" % (len(rows), CSV_OUT))


def query(keyword=None, t=None, since=None, limit=20):
    """关键词/类型/日期范围查询"""
    rows = _read_all()
    # 过滤已过期条目
    rows = [r for r in rows if r.get("status", "active") != "expired"]
    if t:
        rows = [r for r in rows if r.get("type") == t]
    if since:
        try:
            since_dt = datetime.datetime.strptime(since, "%Y-%m-%d")
            rows = [r for r in rows if datetime.datetime.strptime(r["ts"][:10], "%Y-%m-%d") >= since_dt]
        except ValueError:
            print("日期格式错误，应为 YYYY-MM-DD")
            return
    if keyword:
        kw_lower = keyword.lower()
        rows = [r for r in rows if kw_lower in r.get("text", "").lower() or kw_lower in r.get("meta", "").lower()]
    rows = rows[-limit:]
    if not rows:
        print("无匹配记录")
        return
    print("匹配 %d 条:" % len(rows))
    for i, r in enumerate(rows):
        print("  [%d] [%s] %s %s: %s" % (i, r["type"], r["ts"], r.get("meta", ""), r["text"]))


def summarize():
    """按类型分组统计 + 近期条目"""
    rows = _read_all()
    active = [r for r in rows if r.get("status", "active") != "expired"]
    expired = [r for r in rows if r.get("status", "active") == "expired"]
    # 按类型统计
    by_type = {}
    for r in active:
        t = r.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    print("记忆摘要 (活跃 %d / 已过期 %d):" % (len(active), len(expired)))
    for t in sorted(by_type.keys()):
        print("  %s: %d 条" % (t, by_type[t]))
    # 近期条目（每类最多 3 条）
    print("\n近期记忆:")
    for t in sorted(by_type.keys()):
        items = [r for r in active if r.get("type") == t][-3:]
        for r in items:
            print("  [%s] %s: %s" % (t, r.get("meta", "") or r["ts"][:10], r["text"]))


def expire(days=90):
    """标记超过 N 天的条目为 expired"""
    rows = _read_all()
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    count = 0
    for r in rows:
        if r.get("status", "active") == "expired":
            continue
        try:
            ts = datetime.datetime.strptime(r["ts"], "%Y-%m-%d %H:%M:%S")
            if ts < cutoff:
                r["status"] = "expired"
                r["expired_at"] = _now()
                count += 1
        except (ValueError, KeyError):
            pass
    # 重写文件
    with io.open(STORE, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("已标记 %d 条为 expired (阈值: %d 天)" % (count, days))


def delete(index):
    """按序号删除条目（从当前活跃列表）"""
    rows = _read_all()
    active = [r for r in rows if r.get("status", "active") != "expired"]
    if index < 0 or index >= len(active):
        print("序号越界 (0-%d)" % (len(active) - 1))
        return
    target = active[index]
    # 从原始列表中标记为删除
    for r in rows:
        if r is target:
            r["status"] = "deleted"
            r["deleted_at"] = _now()
            break
    with io.open(STORE, "w", encoding="utf-8") as f:
        for r in rows:
            if r.get("status") != "deleted":
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("已删除: [%s] %s" % (target["type"], target["text"]))


def get_active(limit=50):
    """获取活跃条目（供其他模块调用）"""
    rows = _read_all()
    return [r for r in rows if r.get("status", "active") != "expired"][-limit:]


def _build_parser():
    """构造 CLI 解析器（子命令与参数定义集中于此）。"""
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add")
    a.add_argument("--type", required=True)
    a.add_argument("--text", required=True)
    a.add_argument("--meta", default="")
    l = sub.add_parser("list")
    l.add_argument("--type", default=None)
    l.add_argument("--limit", type=int, default=20)
    q = sub.add_parser("query")
    q.add_argument("--keyword", default=None)
    q.add_argument("--type", default=None)
    q.add_argument("--since", default=None)
    q.add_argument("--limit", type=int, default=20)
    sub.add_parser("summarize")
    e = sub.add_parser("expire")
    e.add_argument("--days", type=int, default=90)
    d = sub.add_parser("delete")
    d.add_argument("--index", type=int, required=True)
    lo = sub.add_parser("load")
    lo.add_argument("--limit", type=int, default=15)
    sub.add_parser("export")
    return ap


def _dispatch(args, ap):
    """按子命令分发到处理函数（字典派发，避开长 elif 链）；无子命令时打印帮助。"""
    handlers = {
        "add": lambda: add(args.type, args.text, args.meta),
        "list": lambda: list_entries(args.type, args.limit),
        "query": lambda: query(args.keyword, args.type, args.since, args.limit),
        "summarize": summarize,
        "expire": lambda: expire(args.days),
        "delete": lambda: delete(args.index),
        "load": lambda: print(load_context(args.limit)),
        "export": export_csv,
    }
    handler = handlers.get(args.cmd)
    if handler is None:
        ap.print_help()
        return
    handler()


def main():
    ap = _build_parser()
    args = ap.parse_args()
    _dispatch(args, ap)


if __name__ == "__main__":
    main()
