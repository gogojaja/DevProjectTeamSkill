#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_retro_closure.py — 复盘行动项回环校验（ADR-2026-08-29-001 建议 B/P2 之 companion）

定位：固化（solidify）或复盘会话后检查「上一阶段复盘行动项」是否已关闭。
行业依据（EV-106 Atlassian）：复盘价值在于行动项跟进到位（owner+deadline+验证）；
DORA（EV-105）：复盘是验证改进的步骤。未关闭行动项应列待办并提示人工/模型跟进。

用法：
  python3 tools/check_retro_closure.py                    # 读 22_阶段复盘.csv，列出所有含 owner+deadline 的行动项及其关闭状态
  python3 tools/check_retro_closure.py --stage v21.11.0   # 仅查指定阶段对应行动项
  python3 tools/check_retro_closure.py --mark-closed "<行动项关键词>" [--stage <阶段>]
      # 将匹配「行动项描述含该关键词」的复盘行「行动项」列末尾追加 [已关闭]

关闭判定（启发式）：
  - 行动项列含 "[已关闭]" / "[closed]" → 已关闭
  - 该项出现在 台账/40 大模型成本（无）或 13 审计（无）→ 不作关闭依据（保守）
  - owner+deadline 缺失 → 提示「行动项不可跟进」（Atlassian 标准缺口）

输出：exit 0 = 全部已关闭或无可查行动项；exit 1 = 存在未关闭行动项（供固化流程提示）。
"""
import argparse
import csv
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent)))
LEDGER22 = ROOT / "台账" / "22_阶段复盘.csv"
CLOSED_MARK = "[已关闭]"


def load():
    if not LEDGER22.exists():
        return [], []
    for enc in ("utf-8-sig", "utf-8"):
        try:
            with open(LEDGER22, encoding=enc, newline="") as f:
                rows = list(csv.DictReader(f))
            return list(rows[0].keys()), rows
        except (OSError, csv.Error):
            continue
    return [], []


def action_status(action: str):
    """返回 (closed: bool, has_owner, has_deadline, note)"""
    closed = bool(re.search(r"\[已关闭\]|\[closed\]", action, re.I))
    has_owner = bool(re.search(r"owner[:：]\s*\S+|负责人[:：]\s*\S+", action, re.I))
    has_deadline = bool(re.search(r"deadline[:：]\s*\S+|截止[:：]\s*\S+|[12]\d{3}-\d{2}-\d{2}", action))
    note = ""
    if not action.strip():
        return None, None, None, "无行动项"
    if not has_owner or not has_deadline:
        note = "⚠ 缺 owner 或 deadline（Atlassian 标准：行动项不可跟进）"
    return closed, has_owner, has_deadline, note


def main():
    ap = argparse.ArgumentParser(description="复盘行动项回环校验")
    ap.add_argument("--stage", help="仅查指定阶段")
    ap.add_argument("--mark-closed", help="将匹配关键词的行动项标记为已关闭")
    args = ap.parse_args()

    header, rows = load()
    if not rows:
        print("[info] 22_阶段复盘.csv 无数据，行动项回环校验通过（无待办）")
        return 0

    # mark-closed 处理
    if args.mark_closed:
        kw = args.mark_closed
        changed = 0
        for r in rows:
            if args.stage and r.get("阶段") != args.stage:
                continue
            act = r.get("行动项") or ""
            if kw in act and CLOSED_MARK not in act:
                r["行动项"] = act.rstrip() + CLOSED_MARK
                changed += 1
        # 写回（需保留表头）
        with open(LEDGER22, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            w.writerows(rows)
        print(f"[ok] 已标记 {changed} 条行动项为已关闭（关键词: {kw}）")
        return 0

    pending = []
    total = 0
    for r in rows:
        if args.stage and r.get("阶段") != args.stage:
            continue
        act = r.get("行动项") or ""
        if not act.strip():
            continue
        total += 1
        closed, owner, dl, note = action_status(act)
        state = "✅已关闭" if closed else "🔴未关闭"
        pending_line = f"  {state} [{r.get('阶段')}/{r.get('复盘对象')}] {act[:120]}"
        if note:
            pending_line += f" {note}"
        print(pending_line)
        if not closed:
            pending.append((r.get("阶段"), act))

    print(f"— 行动项共 {total} 条，未关闭 {len(pending)} 条 —")
    if pending:
        print("[warn] 存在未关闭复盘行动项（建议跟进：确认完成 → 以 --mark-closed 标记）", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())