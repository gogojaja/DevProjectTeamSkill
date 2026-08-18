#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quality_gate.py — 质量门（P5 运行时评审层）

对给定目标（代码/架构文档/配置）跑可自动化的门禁并写 台账/36_质量门记录.csv。
五视角中 Architect/CodeReviewer 由既有 check 脚本代理；Security/Test/Performance 依赖宿主
LLM 强模型，本工具标记「需宿主LLM」(host seam, 见 ARCH-002)，不臆造结论。

CLI（跨平台）：
  py -3.11 tools/quality_gate.py run --target <path>
"""
import os
import sys
import io
import csv
import datetime
import argparse
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
GATE = os.path.join(ROOT, "台账", "36_质量门记录.csv")
BOM = b"\xef\xbb\xbf"


def _run(script):
    r = subprocess.run([sys.executable, os.path.join(TOOLS, script)], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode == 0


def _next_id():
    n = 1
    if os.path.exists(GATE):
        with io.open(GATE, "r", encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                if row and row[0].startswith("QG-"):
                    try:
                        n = max(n, int(row[0].split("-")[1]) + 1)
                    except Exception:
                        pass
    return "QG-%03d" % n


def _append(rows):
    header = ["评审编号", "时间", "目标", "视角", "状态", "严重度", "证据", "结论"]
    new = not os.path.exists(GATE)
    with io.open(GATE, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        for r in rows:
            w.writerow(r)


def run(target):
    rid = _next_id()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tgt = target or "(未指定)"
    rows = []
    arch = _run("check_version_consistency.py") and _run("check_skill_closure.py")
    rows.append([rid, now, tgt, "Architect", "PASS" if arch else "FAIL", "",
                 "version+closure 门禁", "结构/一致性自动校验"])
    rel = _run("check_skill_release_gate.py")
    rows.append([rid, now, tgt, "CodeReviewer", "PASS" if rel else "FAIL", "",
                 "release_gate", "发布级门禁自动校验"])
    for v in ("SecurityReviewer", "TestEngineer", "PerformanceEngineer"):
        rows.append([rid, now, tgt, v, "待宿主LLM", "", "需 opencode 强模型视角",
                     "host seam(ARCH-002)"])
    _append(rows)
    fails = [r for r in rows if r[4] == "FAIL"]
    decision = "CHANGES_REQUESTED" if fails else "SIGNED_OFF(部分视角待宿主LLM)"
    print("[quality-gate] %s 决策=%s (自动视角 FAIL=%d)" % (rid, decision, len(fails)))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", nargs="?", default="run")
    ap.add_argument("--target", default="")
    args = ap.parse_args()
    if args.action == "run":
        sys.exit(run(args.target))
    ap.print_help()


if __name__ == "__main__":
    main()
