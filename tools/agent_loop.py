#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent_loop.py — 控制环运行时 MVP（Phase 1）

触发后：跑三道门禁(version/closure/release) → 全过则双推(mirror_push) → 写 台账/34_控制环执行记录.csv
→ 自动提交记录（以 AGENT_LOOP_ACTIVE 环境变量防递归触发 post-commit）。

安全约定（铁律 #3 / #7）：
- 不自行改写系统文件；仅复用既有 mirror_push（token 经 load_secret/insteadOf，URL 脱敏入台账）。
- 门禁未过则**不双推**，仅记录，交由人工处置。
- 自动提交台账记录时置 AGENT_LOOP_ACTIVE=1，嵌套 post-commit 据此跳过，避免无限递归。

用法（跨平台）：
  py -3.11 tools/agent_loop.py                  # Windows 手动
  python3 tools/agent_loop.py                   # macOS / Linux
  py -3.11 tools/agent_loop.py --trigger hook    # 由 .githooks/post-commit 调用
  py -3.11 tools/agent_loop.py --dry-run        # 只跑门禁+记录，不双推、不提交（安全验证）
"""
import os
import sys
import io
import csv
import datetime
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
LEDGER = os.path.join(ROOT, "台账", "34_控制环执行记录.csv")
SYNC_LEDGER = os.path.join(ROOT, "台账", "32_镜像同步记录.csv")
BOM = b"\xef\xbb\xbf"


def _run(script, *args):
    return subprocess.run([sys.executable, os.path.join(TOOLS, script), *args], cwd=ROOT)


def _gate_ok(name):
    return _run(name).returncode == 0


def _push():
    """调用 mirror_push 双推。返回 (rc, label)：rc=0 成功 / 1 失败 / 2 全部被阻断/冷却跳过。"""
    r = _run("mirror_push.py")
    if r.returncode == 0:
        return 0, "成功"
    if r.returncode == 2:
        return 2, "跳过(阻断)"
    return 1, "失败"


def _next_seq():
    if not os.path.exists(LEDGER):
        return 1
    with io.open(LEDGER, "r", encoding="utf-8-sig") as f:
        lines = [l for l in f.read().splitlines() if l.strip()]
    return max(0, len(lines) - 1) + 1


def _write_ledger(path, row):
    header = ["运行编号", "运行时间", "触发源", "版本一致性门禁", "闭环门禁",
              "发布级门禁", "双推结果", "耗时秒", "说明"]
    new = not os.path.exists(path)
    with io.open(path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


def _append_ledger(row):
    _write_ledger(LEDGER, row)


def _git_has_changes(path):
    res = subprocess.run(["git", "diff", "--quiet", "--", path], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode == 0:
        # 若文件已跟踪且未修改；仍可能存在未追踪文件，则检查 status。
        status = subprocess.run(["git", "status", "--short", "--", path], cwd=ROOT,
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        return bool(status.stdout.strip())
    return True


def _safe_git_commit(rid):
    env = dict(os.environ)
    env["AGENT_LOOP_ACTIVE"] = "1"
    # 连带提交 32_镜像同步记录（mirror_push 留痕），避免每次提交后台账脏残留；
    # 凭据认证失败已由熔断器阻断不入台账，故无 Gitee 失败留痕被连带提交的风险。
    changed = _git_has_changes(LEDGER) or _git_has_changes(SYNC_LEDGER)
    if not changed:
        return False, "no_changes"
    add = subprocess.run(["git", "add", LEDGER, SYNC_LEDGER], cwd=ROOT, env=env,
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if add.returncode != 0:
        return False, add.stderr.strip() or "git add failed"
    commit = subprocess.run(["git", "commit", "-m", "chore(agent-loop): 控制环执行记录 %s" % rid],
                            cwd=ROOT, env=env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if commit.returncode != 0:
        return False, commit.stderr.strip() or commit.stdout.strip() or "git commit failed"
    return True, "ok"


def main():
    argv = sys.argv[1:]
    dry = "--dry-run" in argv
    trigger = "manual"
    if "--trigger" in argv:
        i = argv.index("--trigger")
        if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            trigger = argv[i + 1]
        else:
            trigger = "hook"

    start = datetime.datetime.now()
    v = _gate_ok("check_version_consistency.py")
    c = _gate_ok("check_skill_closure.py")
    rel = _gate_ok("check_skill_release_gate.py")
    all_pass = v and c and rel

    if all_pass and not dry:
        push_rc, push_txt = _push()
    else:
        push_txt = "跳过(dry-run)" if dry else "跳过(门禁未过)"

    elapsed = (datetime.datetime.now() - start).total_seconds()
    seq = _next_seq()
    rid = "AL-%s-%03d" % (datetime.date.today().strftime("%Y%m%d"), seq)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    note = "门禁全过" if all_pass else "门禁未过，未双推，待人工处置"
    if all_pass and not dry and push_txt == "失败":
        note = "门禁全过但双推失败(网络/凭据)，已按熔断处理；mirror_push --status 查看状态"
    elif all_pass and not dry and push_txt == "跳过(阻断)":
        note = "双推被熔断(凭据/网络)，已停止重试；见 tools/mirror_push.py --status"
    _append_ledger([rid, now, trigger,
                    "通过" if v else "失败", "通过" if c else "失败",
                    "通过" if rel else "失败", push_txt, "%.1f" % elapsed, note])

    commit_ok = True
    commit_msg = "ok"
    if all_pass and not dry:
        commit_ok, commit_msg = _safe_git_commit(rid)
        if not commit_ok:
            print("[agent-loop] 自动提交失败: %s" % commit_msg)

    print("[agent-loop] trigger=%s 版本=%s 闭环=%s 发布=%s 双推=%s 提交=%s (%.1fs)"
          % (trigger, "PASS" if v else "FAIL", "PASS" if c else "FAIL",
             "PASS" if rel else "FAIL", push_txt, "OK" if commit_ok else "SKIP/FAIL", elapsed))
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
