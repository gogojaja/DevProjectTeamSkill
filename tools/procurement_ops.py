#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""procurement_ops.py -- 采购管理工具 (E1)

对齐 PMBOK Procurement Management

CLI:
  python3 tools/procurement_ops.py register --item "云服务" --vendor "AWS" --amount 50000 --strategy "外包"
  python3 tools/procurement_ops.py evaluate --vendor "AWS" --tech 4 --price 3 --delivery 4 --quality 5 --service 4
  python3 tools/procurement_ops.py track --item "云服务" --milestone "Phase 1" --paid 20000
  python3 tools/procurement_ops.py dashboard
"""
import os, sys, re, io, csv, argparse, datetime

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, "台账")
PROC_FILE = os.path.join(LEDGER, "53_采购登记.csv")

WEIGHTS = {"tech": 0.25, "price": 0.20, "delivery": 0.20, "quality": 0.20, "service": 0.15}


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


def _next_id(prefix, rows):
    nums = []
    for r in rows:
        m = re.search(r"(\d+)$", r.get("编号", ""))
        if m:
            nums.append(int(m.group(1)))
    return f"{prefix}-{(max(nums) + 1) if nums else 1:03d}"


PROC_HEADER = ["编号", "采购项", "供应商", "金额", "采购策略", "技术评分", "价格评分",
               "交付评分", "质量评分", "服务评分", "加权总分", "已付款", "里程碑", "登记日期", "状态"]


def cmd_register(args):
    rows = _read_csv(PROC_FILE)
    pid = _next_id("PR", rows)
    now = datetime.date.today().isoformat()
    _write_csv(PROC_FILE, PROC_HEADER, [
        pid, args.item, args.vendor or "", args.amount, args.strategy or "自制",
        "", "", "", "", "", "", 0, "", now, "已登记"
    ])
    print(f"[procurement] 已登记: {pid} {args.item}")
    print(f"  供应商: {args.vendor or '-'}  金额: {args.amount}  策略: {args.strategy or '自制'}")
    return 0


def cmd_evaluate(args):
    scores = {"tech": args.tech, "price": args.price, "delivery": args.delivery,
              "quality": args.quality, "service": args.service}
    for k, v in scores.items():
        if not (1 <= v <= 5):
            print(f"[ERROR] {k} 评分须在 1~5 之间")
            return 1
    weighted = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)

    rows = _read_csv(PROC_FILE)
    found = False
    for r in rows:
        if r.get("供应商") == args.vendor or r.get("采购项") == args.vendor:
            r["技术评分"] = str(scores["tech"])
            r["价格评分"] = str(scores["price"])
            r["交付评分"] = str(scores["delivery"])
            r["质量评分"] = str(scores["quality"])
            r["服务评分"] = str(scores["service"])
            r["加权总分"] = f"{weighted:.2f}"
            r["状态"] = "已评估"
            found = True
            break
    if not found:
        print(f"[WARN] 未找到供应商/采购项: {args.vendor}，新建评估记录")
        pid = _next_id("PR", rows)
        now = datetime.date.today().isoformat()
        _write_csv(PROC_FILE, PROC_HEADER, [
            pid, "", args.vendor, "", "", scores["tech"], scores["price"],
            scores["delivery"], scores["quality"], scores["service"],
            f"{weighted:.2f}", 0, "", now, "已评估"
        ])
    else:
        with io.open(PROC_FILE, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=PROC_HEADER)
            w.writeheader()
            w.writerows(rows)

    print(f"[procurement] 供应商评估: {args.vendor}")
    print(f"  技术={scores['tech']} 价格={scores['price']} 交付={scores['delivery']} "
          f"质量={scores['quality']} 服务={scores['service']}")
    print(f"  加权总分: {weighted:.2f} / 5.00")
    return 0


def cmd_track(args):
    rows = _read_csv(PROC_FILE)
    found = False
    for r in rows:
        if r.get("采购项") == args.item:
            r["已付款"] = str(args.paid)
            r["里程碑"] = args.milestone
            found = True
            break
    if not found:
        print(f"[ERROR] 未找到采购项: {args.item}")
        return 1
    with io.open(PROC_FILE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PROC_HEADER)
        w.writeheader()
        w.writerows(rows)
    print(f"[procurement] 付款跟踪: {args.item} 里程碑={args.milestone} 已付={args.paid}")
    return 0


def cmd_dashboard(args):
    rows = _read_csv(PROC_FILE)
    if not rows:
        print("[procurement] 无采购记录")
        return 0
    total = len(rows)
    evaluated = len([r for r in rows if r.get("状态") == "已评估"])
    total_amount = sum(float(r.get("金额", 0)) for r in rows if r.get("金额"))
    total_paid = sum(float(r.get("已付款", 0)) for r in rows if r.get("已付款"))
    print(f"[procurement] 采购仪表盘")
    print(f"  采购项: {total}")
    print(f"  已评估: {evaluated}")
    print(f"  总金额: {total_amount:,.0f}")
    print(f"  已付款: {total_paid:,.0f}")
    if total_amount > 0:
        print(f"  付款率: {total_paid/total_amount*100:.1f}%")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Procurement Management CLI (E1)")
    sub = ap.add_subparsers(dest="command")

    r = sub.add_parser("register", help="采购登记")
    r.add_argument("--item", required=True)
    r.add_argument("--vendor", default="")
    r.add_argument("--amount", type=float, required=True)
    r.add_argument("--strategy", default="自制")

    e = sub.add_parser("evaluate", help="供应商评估")
    e.add_argument("--vendor", required=True)
    e.add_argument("--tech", type=int, required=True)
    e.add_argument("--price", type=int, required=True)
    e.add_argument("--delivery", type=int, required=True)
    e.add_argument("--quality", type=int, required=True)
    e.add_argument("--service", type=int, required=True)

    t = sub.add_parser("track", help="付款跟踪")
    t.add_argument("--item", required=True)
    t.add_argument("--milestone", required=True)
    t.add_argument("--paid", type=float, required=True)

    sub.add_parser("dashboard", help="采购仪表盘")

    args = ap.parse_args()
    dispatch = {"register": cmd_register, "evaluate": cmd_evaluate,
                "track": cmd_track, "dashboard": cmd_dashboard}
    if args.command in dispatch:
        sys.exit(dispatch[args.command](args))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
