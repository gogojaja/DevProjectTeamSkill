#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dispatch.py — 多 Agent 任务消息总线（P4 运行时调度层）

在 opencode 宿主之上编排并行角色 worker：本工具负责「任务登记 / 状态流转 / handoff 记录」，
真实 worker 派工由宿主 Task 原语执行（见 ARCH-002 可行性探针）；本工具输出可机读的派工指令。

铁律 #3（SEC-003）：消息总线禁止承载 A 级信息（密钥/Token）。写入前对输入/输出做脱敏，
命中 token/secret 模式即替换为 ***[脱敏]*** 并标记。

CLI（跨平台）：
  py -3.11 tools/dispatch.py create --role architect --input "..." [--parent TID]
  py -3.11 tools/dispatch.py complete --tid TID --output "..."
  py -3.11 tools/dispatch.py list [--role x] [--status todo|doing|done]
  py -3.11 tools/dispatch.py spawn --tid TID        # 打印宿主派工指令(handoff)
"""
import os
import sys
import io
import csv
import re
import datetime
import argparse

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUS = os.path.join(ROOT, "台账", "35_任务消息总线.csv")
ROLES = {"architect", "developer", "tester", "security", "governance", "pm"}
SEQ = 0
SECRET_RE = re.compile(r"(ghp_[A-Za-z0-9]{20,}|token[\"=:\s]{0,4}[A-Za-z0-9_\-]{16,}|secret[\"=:\s]{0,4}[A-Za-z0-9_\-]{16,})",
                       re.IGNORECASE)


def _redact(text):
    return SECRET_RE.sub("***[脱敏]***", text or "")


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _next_tid():
    n = 1
    if os.path.exists(BUS):
        with io.open(BUS, "r", encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                if row and row[0].startswith("TASK-"):
                    try:
                        n = max(n, int(row[0].split("-")[1]) + 1)
                    except Exception:
                        pass
    return "TASK-%03d" % n


def _append(row):
    header = ["任务ID", "父任务ID", "角色", "状态", "输入摘要", "输出摘要",
              "创建时间", "完成时间", "关联台账"]
    new = not os.path.exists(BUS)
    with io.open(BUS, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


def create(role, text, parent=""):
    if role not in ROLES:
        print("角色须为: " + ", ".join(sorted(ROLES)))
        sys.exit(2)
    tid = _next_tid()
    _append([tid, parent, role, "todo", _redact(text), "", _now(), "", ""])
    print("已登记 %s (role=%s)" % (tid, role))
    return tid


def complete(tid, text):
    rows = []
    found = False
    if os.path.exists(BUS):
        with io.open(BUS, "r", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
    for r in rows[1:]:
        if r and r[0] == tid:
            r[3] = "done"
            r[5] = _redact(text)
            r[7] = _now()
            found = True
            break
    if not found:
        print("未找到 %s" % tid)
        sys.exit(1)
    with io.open(BUS, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)
    print("已完成 %s" % tid)


def list_tasks(role=None, status=None):
    if not os.path.exists(BUS):
        print("(空)")
        return
    with io.open(BUS, "r", encoding="utf-8-sig") as f:
        for r in csv.reader(f):
            if not r:
                continue
            if role and r[2] != role:
                continue
            if status and r[3] != status:
                continue
            print("[%s] %s %s/%s: in=%s out=%s" % (r[0], r[2], r[3], r[1], r[4], r[5]))


def spawn(tid):
    rows = []
    if os.path.exists(BUS):
        with io.open(BUS, "r", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
    for r in rows[1:]:
        if r and r[0] == tid:
            print("【宿主派工指令】请调用 opencode Task 派生 worker：")
            print("  角色=%s  任务=%s  输入=%s" % (r[2], r[0], r[4]))
            print("  worker 完成后果：dispatch.py complete --tid %s --output \"<脱敏摘要>\"" % tid)
            return
    print("未找到 %s" % tid)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("create")
    c.add_argument("--role", required=True)
    c.add_argument("--input", required=True)
    c.add_argument("--parent", default="")
    cp = sub.add_parser("complete")
    cp.add_argument("--tid", required=True)
    cp.add_argument("--output", required=True)
    l = sub.add_parser("list")
    l.add_argument("--role", default=None)
    l.add_argument("--status", default=None)
    sp = sub.add_parser("spawn")
    sp.add_argument("--tid", required=True)
    args = ap.parse_args()
    if args.cmd == "create":
        create(args.role, args.input, args.parent)
    elif args.cmd == "complete":
        complete(args.tid, args.output)
    elif args.cmd == "list":
        list_tasks(args.role, args.status)
    elif args.cmd == "spawn":
        spawn(args.tid)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
