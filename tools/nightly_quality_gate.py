#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nightly_quality_gate.py — 夜间全项目质量门禁编排器

对 projects_registry.csv 中每个启用的项目执行：
  1) quality_gate.py run --target <project> （五视角门禁，自动视角写台帐 36）
  2) 单元测试全量（registry 的 test_cmd）
  3) 脱敏扫描（desensitize.py --scan，只扫不修改，铁律 #8）
  4) 聚合裁决：自动视角 FAIL / 单测失败 → CHANGES_REQUESTED；全绿 → SIGNED_OFF
  5) 需人工授权项（凭据缺失 / 高严重度 FAIL / AI 高置信阻断 / 受保护副作用）→ 39_待决策事项.csv 队列，不阻断整体
  6) 失败告警（系统通知；可选 webhook）

AI 语义评审（Security/Test/Performance 视角）默认关闭；ENABLE_AI_REVIEW=true 时启用但仅记录、非阻断（EV-004 约束）。

CLI（跨平台，Windows 用 py -3.11，macOS/Linux 用 python3）：
  python3 tools/nightly_quality_gate.py run --target <alias>   # 跑全部或单项目
  python3 tools/nightly_quality_gate.py run --dry-run          # 仅探测 registry，不做任何副作用
  python3 tools/nightly_quality_gate.py list                    # 列举 registry 项目
"""
from __future__ import annotations

import csv
import io
import os
import sys
import argparse
import datetime
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
REGISTRY = os.path.join(ROOT, "projects_registry.csv")
GATE = os.path.join(ROOT, "台账", "36_质量门记录.csv")
DECISION_Q = os.path.join(ROOT, "台账", "39_待决策事项.csv")
BOM = b"\xef\xbb\xbf"

AI_ENV = os.environ.get("ENABLE_AI_REVIEW", "false").lower() in ("1", "true", "yes")
AI_BUDGET = int(os.environ.get("AI_BUDGET", "0") or "0") or None


def _run(script_args, cwd=None):
    try:
        r = subprocess.run([sys.executable] + script_args, cwd=cwd or ROOT,
                           capture_output=True, text=True, encoding="utf-8", timeout=1800)
        return r.returncode == 0, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return False, "", "timeout"
    except Exception as e:  # noqa: BLE001
        return False, "", str(e)


def _next_id(path, prefix, width=3):
    n = 1
    if os.path.exists(path):
        with io.open(path, "r", encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                if row and row[0].startswith(prefix):
                    try:
                        n = max(n, int(row[0].split("-")[1]) + 1)
                    except Exception:
                        pass
    return "%s-%03d" % (prefix, n)


def _append(path, header, rows):
    new = not os.path.exists(path)
    with io.open(path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        for r in rows:
            w.writerow(r)


def load_registry():
    projects = []
    if not os.path.exists(REGISTRY):
        print("[nightly] registry 不存在: %s" % REGISTRY)
        return projects
    with io.open(REGISTRY, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not row or not row.get("project_alias"):
                continue
            if row.get("enabled", "y").strip().lower() in ("n", "no", "0", "false"):
                print("[nightly] 跳过(enabled=no): %s" % row["project_alias"])
                continue
            projects.append(row)
    return projects


def notify(level, msg, project="", webhook=""):
    if not msg:
        return
    print("[nightly][%s] %s" % (level, msg))
    try:
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", 'display notification "%s" with title "%s"' %
                            (msg.replace('"', '\\"'), "nightly-qg %s %s" % (level, project))],
                           capture_output=True, timeout=10)
    except Exception:
        pass
    if webhook:
        try:
            import urllib.request
            urllib.request.urlopen(urllib.request.Request(webhook, data=msg.encode("utf-8"),
                                                          headers={"Content-Type": "text/plain"}),
                                   timeout=10)
        except Exception as e:  # noqa: BLE001
            print("[nightly] webhook 失败(不阻断): %s" % e)


def run_project(p, dry=False, webhook=""):
    alias = p["project_alias"]
    path = p.get("project_path", "").strip()
    test_cmd = p.get("test_cmd", "").strip()
    secret_ref = p.get("secret_ref", "").strip()
    print("[nightly] ── %s ──" % alias)

    pending = []
    gate_rows = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rid = _next_id(GATE, "QG")

    # 0) 凭据前置检查：需要凭据但无法经 load_secret 解析 → 待决策（4.9.2 类别1）
    if secret_ref:
        ok, _, err = _run(["tools/load_secret.py", secret_ref]) if os.path.exists(
            os.path.join(TOOLS, "load_secret.py")) else (False, "", "load_secret 不存在")
        if not ok:
            pending.append(["DB", alias, "credential_missing",
                            "secret_ref 无法解析（真实值走 .secrets/，铁律#3）",
                            "夜间无法运行需凭据步骤", "pending", ""])
            print("[nightly] 凭据缺失 → 待决策(不阻断): %s" % secret_ref)

    # 1) quality_gate run（自动视角）
    if dry:
        print("[nightly][dry] 将执行 quality_gate run --target %s" % alias)
    else:
        qok, qout, qerr = _run(["tools/quality_gate.py", "run", "--target",
                                alias or path or "(未指定)"])
        gate_rows.append([rid, now, alias or path, "Architect", "PASS" if qok else "FAIL", "",
                          "version+closure 门禁", "quality_gate 自动校验"])
        gate_rows.append([rid, now, alias or path, "CodeReviewer", "PASS" if qok else "FAIL", "",
                          "release_gate", "quality_gate 自动校验"])
        if not qok:
            pending.append(["DB", alias, "high_severity_fail",
                            "自动门禁 FAIL（版本一致性/发布级）",
                            "高严重度阻断发现，日间研判", "pending", ""])
            print("[nightly] 门禁 FAIL → 待决策(不阻断整夜)")

    # 2) 单元测试全量（registry test_cmd）
    if test_cmd and not dry:
        # 直接执行项目测试命令（registry 定义，默认 pytest）
        import shlex
        cmd = shlex.split(test_cmd)
        try:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                               encoding="utf-8", timeout=3600)
            tok = r.returncode == 0
            tout, terr = r.stdout or "", r.stderr or ""
        except subprocess.TimeoutExpired:
            tok, tout, terr = False, "", "timeout"
        except Exception as e:  # noqa: BLE001
            tok, tout, terr = False, "", str(e)
        gate_rows.append([rid, now, alias, "TestEngineer", "PASS" if tok else "FAIL", "" if tok else "high",
                          test_cmd, "单测全量"])
        if not tok:
            pending.append(["DB", alias, "unit_test_fail",
                            "单测失败 %s" % (terr or tout)[:200],
                            "跨模块回归，日间研判 flaky 与否", "pending", ""])
            print("[nightly] 单测失败 → 待决策(不阻断整夜)")

    # 3) 脱敏扫描（铁律 #8，只扫本次新增产物 36/39 CSV，不扫全仓历史避免存量 B 级误判）
    if not dry:
        den_path = os.path.join(TOOLS, "desensitize", "desensitize.py")
        nightly_artifacts = []
        for f in (GATE, DECISION_Q):
            if os.path.exists(f):
                nightly_artifacts.append(f)
        if os.path.exists(den_path) and nightly_artifacts:
            sok, sout, _ = _run([den_path, "--scan"] + nightly_artifacts + ["--report",
                                 os.path.join(ROOT, "台账", "scan_report_nightly.csv")])
            gate_rows.append([rid, now, alias, "SecurityReviewer",
                              "PASS" if sok else "WARN", "", "desensitize --scan(新增产物)",
                              "脱敏扫描（只扫不改）"])
            if not sok:
                pending.append(["DB", alias, "desensitize_hit",
                                "脱敏扫描命中（仅新增产物，报告见 scan_report_nightly.csv）",
                                "脱敏疑似项，日间研判", "pending", ""])
        else:
            gate_rows.append([rid, now, alias, "SecurityReviewer", "SKIP", "", "desensitize 缺失或无新增产物",
                              "宿主未安装 desensitize"])

    # 4) AI 语义评审：默认关闭；开启时仅记录、非阻断（EV-004）
    if AI_ENV:
        for v, tgt in (("SecurityReviewer", "AI 语义安全视角"), ("PerformanceEngineer", "AI 语义性能视角")):
            print("[nightly][AI] 记录(非阻断): %s" % tgt)
            gate_rows.append([rid, now, alias, v, "记录-非阻断", "",
                              "ENABLE_AI_REVIEW=true", "AI 语义评审(非阻断, EV-004)"])
    elif AI_BUDGET:
        # 用户错误设置了 AI_BUDGET 但未开开关 → 提示
        print("[nightly] 注意：AI_BUDGET 已设但 ENABLE_AI_REVIEW 未开，AI 评审未启用")

    # 5) 写 36 门记录（dry 不写）
    if gate_rows and not dry:
        _append(GATE,
                ["评审编号", "时间", "目标", "视角", "状态", "严重度", "证据", "结论"], gate_rows)
        print("[nightly] 36_质量门记录.csv 追加 %d 行 (QG-%s)" % (len(gate_rows), rid.split("-")[-1]))

    # 6) 聚合裁决（只取自动视角 + 单测，AI 不阻断）
    fails = [r for r in gate_rows if r[4] == "FAIL"]
    decision = "CHANGES_REQUESTED" if fails else "SIGNED_OFF"
    print("[nightly] %s 裁决=%s (自动视角 FAIL=%d, 待决策=%d)" % (alias, decision, len(fails), len(pending)))

    # 7) 待决策入 39 队列（含日间 replay 字段）
    if pending and not dry:
        now2 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = []
        for i, (dtype, palias, cat, payload, rationale, status, _) in enumerate(pending, 1):
            sid = _next_id(DECISION_Q, "DB")
            exp = (datetime.datetime.now() + datetime.timedelta(hours=12)).strftime("%Y-%m-%d %H:%M")
            rows.append([sid, now2, palias, cat, payload, rationale, status, exp, "", "", ""])
        _append(DECISION_Q,
                ["decision_id", "time", "project_alias", "category", "payload", "rationale",
                 "status", "expires_at", "daytime_decision", "approver", "rollback"], rows)
        print("[nightly] 39_待决策事项.csv 追加 %d 条" % len(rows))

    # 8) 失败告警
    if not dry and (fails or pending):
        notify("WARN", "%s 夜间门禁：FAIL=%d 待决策=%d" % (alias, len(fails), len(pending)),
               project=alias, webhook=webhook)

    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser(prog="nightly_quality_gate.py")
    ap.add_argument("action", nargs="?", default="run", help="run/list")
    ap.add_argument("--target", default="", help="仅跑指定 project_alias（默认全部）")
    ap.add_argument("--dry-run", action="store_true", help="仅探测，不做副作用")
    ap.add_argument("--webhook", default="", help="失败告警 webhook URL（可选）")
    args = ap.parse_args()

    if args.action == "list":
        for p in load_registry():
            print("%s | %s | test=%s | enabled=%s" %
                  (p["project_alias"], p.get("project_path", ""), p.get("test_cmd", ""), p.get("enabled", "y")))
        return 0

    projects = load_registry()
    if not projects:
        print("[nightly] 无可执行项目（registry 为空或全部 disabled）")
        return 0

    if args.target:
        projects = [p for p in projects if p["project_alias"] == args.target]
        if not projects:
            print("[nightly] 未找到 target: %s" % args.target)
            return 1

    overall = 0
    skipped_pending = 0
    for p in projects:
        try:
            rc = run_project(p, dry=args.dry_run, webhook=args.webhook)
            overall |= rc
            skipped_pending += rc  # FAIL 计为待研判
        except Exception as e:  # noqa: BLE001
            print("[nightly] 项目异常(隔离不阻断, 4.9.3 Skip-and-Flag): %s → %s" % (p["project_alias"], e))
            skipped_pending += 1

    print("[nightly] 整体完成（跳过/待研判项=%d），退出码=%d" % (skipped_pending, 1 if overall else 0))
    if args.dry_run:
        print("[nightly] dry-run：未写任何台账/未执行门禁，仅探测。")
    return 1 if overall else 0


if __name__ == "__main__":
    sys.exit(main())