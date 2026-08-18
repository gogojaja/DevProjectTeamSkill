#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory_store.py — 结构化持久记忆服务（P2 运行时记忆层）

替代手工交接文档的脆弱长文本，提供跨会话可机读的决策/待办/上下文/风险记忆。
存储：台账/38_项目记忆.jsonl（UTF-8，每行一条 JSON）。导出：台账/38_项目记忆.csv（UTF-8 BOM）。
铁律：A 级信息（密钥/Token）禁止写入记忆；仅存脱敏后的决策与待办。

CLI（跨平台）：
  py -3.11 tools/memory_store.py add --type decision --text "..." [--meta 关联编号]
  py -3.11 tools/memory_store.py list [--type todo] [--limit 20]
  py -3.11 tools/memory_store.py load [--limit 15]      # 输出可注入会话上下文的文本
  py -3.11 tools/memory_store.py export                  # 导出 BOM CSV
"""
import os
import sys
import io
import json
import csv
import datetime
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    header = ["时间", "类型", "内容", "关联"]
    with io.open(CSV_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([r["ts"], r["type"], r["text"], r.get("meta", "")])
    print("已导出 %d 条 -> %s" % (len(rows), CSV_OUT))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add")
    a.add_argument("--type", required=True)
    a.add_argument("--text", required=True)
    a.add_argument("--meta", default="")
    l = sub.add_parser("list")
    l.add_argument("--type", default=None)
    l.add_argument("--limit", type=int, default=20)
    lo = sub.add_parser("load")
    lo.add_argument("--limit", type=int, default=15)
    sub.add_parser("export")
    args = ap.parse_args()
    if args.cmd == "add":
        add(args.type, args.text, args.meta)
    elif args.cmd == "list":
        list_entries(args.type, args.limit)
    elif args.cmd == "load":
        print(load_context(args.limit))
    elif args.cmd == "export":
        export_csv()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
