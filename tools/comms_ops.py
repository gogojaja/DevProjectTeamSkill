#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""comms_ops.py -- 干系人沟通管理工具 (S4)

行业锚定: PMBOK Stakeholder/Communications Management + Salience Model

CLI:
  python3 tools/comms_ops.py stakeholder --name "Sponsor" --org "管理层" --power high --interest high
  python3 tools/comms_ops.py engage --name "Sponsor" --current S --expected A
  python3 tools/comms_ops.py plan --stakeholder "Sponsor" --content "进展摘要" --freq weekly --channel "面对面" --owner "PM"
  python3 tools/comms_ops.py log --stakeholder "Sponsor" --content "周报汇报" --feedback "认可进度"
  python3 tools/comms_ops.py dashboard
"""
import os, sys, re, io, csv, argparse, datetime

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, "台账")
STK_FILE = os.path.join(LEDGER, "50_干系人映射.csv")
PLAN_FILE = os.path.join(LEDGER, "51_沟通计划.csv")
LOG_FILE = os.path.join(LEDGER, "52_沟通记录.csv")

QUADRANT_MAP = {
    ("high", "high"): "重点管理",
    ("high", "low"): "保持满意",
    ("low", "high"): "保持知情",
    ("low", "low"): "最少关注",
}
ENGAGE_LEVELS = {"C": "Compliant", "U": "Unaware", "N": "Neutral", "S": "Supportive", "A": "Leading"}


def _ensure_dir():
    os.makedirs(LEDGER, exist_ok=True)


def _read_csv(path):
    if not os.path.isfile(path):
        return []
    with io.open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _write_csv(path, header, rows):
    _ensure_dir()
    with io.open(path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            w.writerow(header)
        w.writerow(rows)


def _rewrite_csv(path, header, rows):
    _ensure_dir()
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def _next_id(prefix, rows):
    nums = []
    for r in rows:
        m = re.search(r"(\d+)$", r.get("编号", ""))
        if m:
            nums.append(int(m.group(1)))
    return f"{prefix}-{(max(nums) + 1) if nums else 1:03d}"


def cmd_stakeholder(args):
    rows = _read_csv(STK_FILE)
    sid = _next_id("SH", rows)
    quadrant = QUADRANT_MAP.get((args.power.lower(), args.interest.lower()), "未分类")
    header = ["编号", "姓名或角色", "组织", "权力", "利益", "象限", "当前参与度", "期望参与度", "策略"]
    _write_csv(STK_FILE, header, [sid, args.name, args.org or "", args.power, args.interest, quadrant, "", "", ""])
    print(f"[comms] 干系人映射: {sid} {args.name}")
    print(f"  权力={args.power} 利益={args.interest} 象限={quadrant}")
    return 0


def cmd_engage(args):
    rows = _read_csv(STK_FILE)
    found = False
    for r in rows:
        if r.get("姓名或角色") == args.name:
            r["当前参与度"] = args.current.upper()
            r["期望参与度"] = args.expected.upper()
            # 计算差距
            levels = ["U", "N", "C", "S", "A"]
            try:
                cur_idx = levels.index(args.current.upper())
                exp_idx = levels.index(args.expected.upper())
                gap = exp_idx - cur_idx
                if gap >= 2:
                    r["策略"] = f"需重点提升参与度（差距{gap}级）"
                elif gap > 0:
                    r["策略"] = f"适度提升（差距{gap}级）"
                elif gap == 0:
                    r["策略"] = "已达标"
                else:
                    r["策略"] = "超出期望"
            except ValueError:
                r["策略"] = "级别无效"
            found = True
            print(f"[comms] 参与度评估: {args.name}")
            print(f"  当前={ENGAGE_LEVELS.get(args.current.upper(), '?')} -> 期望={ENGAGE_LEVELS.get(args.expected.upper(), '?')}")
            print(f"  策略: {r['策略']}")
            break
    if not found:
        print(f"[ERROR] 未找到干系人: {args.name}")
        return 1
    header = ["编号", "姓名或角色", "组织", "权力", "利益", "象限", "当前参与度", "期望参与度", "策略"]
    _rewrite_csv(STK_FILE, header, rows)
    return 0


def cmd_plan(args):
    rows = _read_csv(PLAN_FILE)
    pid = _next_id("CP", rows)
    now = datetime.date.today().isoformat()
    header = ["编号", "干系人", "沟通内容", "频率", "渠道", "责任人", "创建日期"]
    _write_csv(PLAN_FILE, header, [pid, args.stakeholder, args.content, args.freq, args.channel, args.owner, now])
    print(f"[comms] 沟通计划: {pid}")
    print(f"  {args.stakeholder} <- {args.content} ({args.freq}, {args.channel}, {args.owner})")
    return 0


def cmd_log(args):
    rows = _read_csv(LOG_FILE)
    lid = _next_id("CL", rows)
    now = datetime.date.today().isoformat()
    header = ["编号", "日期", "干系人", "沟通内容", "反馈", "后续行动", "升级级别"]
    _write_csv(LOG_FILE, header, [lid, now, args.stakeholder, args.content, args.feedback or "", "", ""])
    print(f"[comms] 沟通记录: {lid}")
    print(f"  {args.stakeholder}: {args.content}")
    if args.feedback:
        print(f"  反馈: {args.feedback}")
    return 0


def cmd_dashboard(args):
    stk = _read_csv(STK_FILE)
    plans = _read_csv(PLAN_FILE)
    logs = _read_csv(LOG_FILE)
    print("[comms] 干系人沟通仪表盘")
    print(f"  干系人: {len(stk)}")
    if stk:
        quadrants = {}
        for s in stk:
            q = s.get("象限", "?")
            quadrants.setdefault(q, []).append(s.get("姓名或角色", "?"))
        for q, names in quadrants.items():
            print(f"    {q}: {', '.join(names)}")
    print(f"  沟通计划: {len(plans)}")
    print(f"  沟通记录: {len(logs)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Stakeholder & Comms CLI (S4)")
    sub = ap.add_subparsers(dest="command")

    s = sub.add_parser("stakeholder", help="干系人映射")
    s.add_argument("--name", required=True)
    s.add_argument("--org", default="")
    s.add_argument("--power", required=True, choices=["high", "medium", "low"])
    s.add_argument("--interest", required=True, choices=["high", "medium", "low"])

    e = sub.add_parser("engage", help="参与度评估")
    e.add_argument("--name", required=True)
    e.add_argument("--current", required=True, choices=["C", "U", "N", "S", "A"])
    e.add_argument("--expected", required=True, choices=["C", "U", "N", "S", "A"])

    p = sub.add_parser("plan", help="沟通计划")
    p.add_argument("--stakeholder", required=True)
    p.add_argument("--content", required=True)
    p.add_argument("--freq", required=True, help="频率(如 weekly/daily/monthly)")
    p.add_argument("--channel", required=True, help="渠道(如 面对面/邮件/站会)")
    p.add_argument("--owner", required=True)

    l = sub.add_parser("log", help="沟通记录")
    l.add_argument("--stakeholder", required=True)
    l.add_argument("--content", required=True)
    l.add_argument("--feedback", default="")

    sub.add_parser("dashboard", help="沟通仪表盘")

    args = ap.parse_args()
    dispatch = {
        "stakeholder": cmd_stakeholder, "engage": cmd_engage, "plan": cmd_plan,
        "log": cmd_log, "dashboard": cmd_dashboard,
    }
    if args.command in dispatch:
        sys.exit(dispatch[args.command](args))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
