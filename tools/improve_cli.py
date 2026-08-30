#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
improve_cli.py — self-improve 独立工具形态（ADR-2026-08-29-001 建议 D / P3）

对应能力：self-improve 子技能 OODA 循环（Observe→Orient→Decide→Act）核心环节。
定位：工具=「结构化 I/O + 落盘 + 校验」，技能=「方法论/编排/决策」。
启用条件（ADR 反信号）：复用率持续增长（跨阶段/跨项目复盘需求）时启用，否则收缩回纯子技能。

用法：
  python3 tools/improve_cli.py --diagnose --target <对象>            # 偏差侦测清单（Observe）
  python3 tools/improve_cli.py --propose --id DEV-001 --title <问题> --root-cause <根因> --fix <方案>
      # 改进提案卡（Decide），追加到 .trae/skills/shared/evolution/... 改进提案台账
  python3 tools/improve_cli.py --experiment --proposal <提案ID> --result pass|fail
      # 实验评估记录（Act 验证）

输出/落盘：
  - --diagnose 输出偏差清单 JSON（结构化，供会话/工具消费）
  - --propose 追加到 台账/33_改进提案.csv（或 shared/evolution 提案台账，自动定位）
  - --experiment 回填提案「验证状态」。

设计依据：ADR-2026-08-29-001 建议 D；self-improve/domain/*.md（deviation-detection/improvement-proposal/experiment-evaluation）。
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent)))

# 提案台账自动定位：shared/evolution 或 台账
PROPOSAL_TARGETS = [
    ROOT / "台账" / "33_改进提案.csv",
    ROOT / ".trae" / "skills" / "shared" / "evolution" / "改善提案.csv",
]

PROPOSAL_COLS = ["提案编号", "记录时间", "问题标题", "根因分析", "改进方案", "优先级", "预期收益", "验证状态", "操作人员", "备注"]


def locate_proposal_ledger():
    for p in PROPOSAL_TARGETS:
        if p.exists():
            return p
    # 都不存在用默认台账 33
    return ROOT / "台账" / "33_改进提案.csv"


def load_csv(path):
    if not path.exists():
        return PROPOSAL_COLS, []
    for enc in ("utf-8-sig", "utf-8"):
        try:
            with open(path, encoding=enc, newline="") as f:
                rows = list(csv.reader(f))
            if rows:
                return rows[0], rows[1:]
        except (OSError, csv.Error):
            continue
    return PROPOSAL_COLS, []


def write_csv(path, header, rows, fieldnames=None):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        if fieldnames:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            w.writerows(rows)
        else:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)


def new_proposal_id(path):
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"P-{today}-"
    _, rows = load_csv(path)
    seq = [r[0] for r in rows if r and r[0].startswith(prefix)]
    return f"{prefix}{len(seq) + 1:02d}"


def diagnose(target: str) -> int:
    """偏差侦测清单（Observe）：结构化输出待核对项，供会话按 OODA 判定"""
    checks = [
        {"id": "DEV-CHECK-1", "question": f"目标「{target}」的预期行为是什么？（对照文档描述/标准）"},
        {"id": "DEV-CHECK-2", "question": f"实际行为是什么？（对照真实运行态/执行结果）"},
        {"id": "DEV-CHECK-3", "question": "预期 vs 实际是否偏离？（偏离→登记偏差、频次与影响）"},
        {"id": "DEV-CHECK-4", "question": "根因是什么？（5-Why / 鱼骨图，人/流程/工具/标准/环境五类）"},
    ]
    print("══ self-improve 诊断工具化 (improve_cli --diagnose) ══")
    print(f" 目标: {target}")
    print(" 偏差侦测清单（Observe，待会话按方法论判定）:")
    for c in checks:
        print(f"   - {c['id']}: {c['question']}")
    print(" 输出：OODA 闭环（Observe→Orient→Decide→Act）由 self-improve 子技能编排，本工具提供结构化入口。")
    return 0


def propose(pid, title, root_cause, fix, priority="P2", benefit="", result: str = "") -> int:
    ledger = locate_proposal_ledger()
    header, rows = load_csv(ledger)
    if len(header) != len(PROPOSAL_COLS):
        header = PROPOSAL_COLS
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pid = pid or new_proposal_id(ledger)
    rows.append([pid, now, title, root_cause, fix, priority, benefit, result or "待验证", "gogo", ""])
    write_csv(ledger, header, rows)
    print(f"[ok] 改进提案已落盘: {ledger.relative_to(ROOT)}")
    print(f"  {pid} | {title} | 优先级={priority} | 验证状态={result or '待验证'}")
    return 0


def experiment(proposal_id, result, note: str = "") -> int:
    ledger = locate_proposal_ledger()
    header, rows = load_csv(ledger)
    found = False
    for r in rows:
        if len(r) >= 8 and r[0] == proposal_id:
            r[7] = result
            if note:
                r[9] = note
            found = True
            break
    if not found:
        print(f"[error] 提案 {proposal_id} 不存在于 {ledger.relative_to(ROOT)}", file=sys.stderr)
        return 1
    write_csv(ledger, header, rows)
    print(f"[ok] 提案 {proposal_id} 验证状态已更新: {result}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="self-improve 独立工具形态（improve_cli）")
    ap.add_argument("--diagnose", metavar="目标", help="偏差侦测清单（Observe）")
    ap.add_argument("--propose", action="store_true", help="登记改进提案（Decide）")
    ap.add_argument("--experiment", action="store_true", help="记录实验评估（Act 验证）")
    ap.add_argument("--id", help="提案号（--propose 自动生成；--experiment 必填）")
    ap.add_argument("--title", help="问题标题（--propose 必填）")
    ap.add_argument("--root-cause", help="根因分析（--propose）")
    ap.add_argument("--fix", help="改进方案（--propose）")
    ap.add_argument("--priority", default="P2", help="优先级（P0~P3，缺省 P2）")
    ap.add_argument("--benefit", default="", help="预期收益（--propose）")
    ap.add_argument("--result", help="实验结果 pass|fail（--experiment）")
    ap.add_argument("--note", default="", help="实验备注（--experiment）")
    args = ap.parse_args()

    if args.diagnose:
        return diagnose(args.diagnose)

    if args.experiment:
        if not args.id or args.result not in ("pass", "fail"):
            print("[error] --experiment 需 --id 且 --result pass|fail", file=sys.stderr)
            return 1
        return experiment(args.id, args.result, args.note)

    if args.propose:
        if not args.title or not args.fix:
            print("[error] --propose 需 --title 与 --fix", file=sys.stderr)
            return 1
        return propose(args.id, args.title, args.root_cause or "", args.fix, args.priority, args.benefit)

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())