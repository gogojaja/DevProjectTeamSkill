#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""okr_ops.py -- OKR/KPI 战略对齐工具 (S2)

行业锚定: Doerr OKR + Kaplan-Norton BSC + SAFe 6.0 Strategic Themes
技能依赖: okr-strategy 子技能

CLI:
  python3 tools/okr_ops.py create --level org --objective "提升市场份额" --kr "市占率达15%" --owner "VP-Sales"
  python3 tools/okr_ops.py update --id OKR-001 --progress 65
  python3 tools/okr_ops.py score --id OKR-001 --score 0.7
  python3 tools/okr_ops.py map --project "项目X" --theme "数字化转型" --score 4
  python3 tools/okr_ops.py audit
  python3 tools/okr_ops.py dashboard
"""
import os, sys, re, io, csv, argparse, datetime

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, "台账")

OKR_FILE = os.path.join(LEDGER, "46_OKR登记.csv")
ALIGN_FILE = os.path.join(LEDGER, "47_战略对齐矩阵.csv")


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


OKR_HEADER = ["编号", "层级", "Objective", "KeyResult_KPI", "Owner", "周期",
              "目标值", "实际值", "完成%", "评分", "状态", "创建日期"]


def cmd_create(args):
    rows = _read_csv(OKR_FILE)
    oid = _next_id("OKR", rows)
    now = datetime.date.today().isoformat()
    q = args.period or ("Q" + str((datetime.date.today().month - 1) // 3 + 1))
    _write_csv(OKR_FILE, OKR_HEADER, [
        oid, args.level, args.objective, args.kr or "", args.owner or "",
        q, args.target or "", "", "0", "", "进行中", now
    ])
    print(f"[okr] 已创建: {oid}")
    print(f"  层级: {args.level}  Objective: {args.objective}")
    if args.kr:
        print(f"  Key Result: {args.kr}")
    return 0


def cmd_update(args):
    rows = _read_csv(OKR_FILE)
    found = False
    for r in rows:
        if r.get("编号") == args.id:
            r["完成%"] = str(args.progress)
            if args.actual:
                r["实际值"] = args.actual
            found = True
            break
    if not found:
        print(f"[ERROR] 未找到 {args.id}")
        return 1
    _rewrite_csv(OKR_FILE, OKR_HEADER, rows)
    print(f"[okr] 已更新: {args.id} 完成度={args.progress}%")
    return 0


def cmd_score(args):
    if not (0 <= args.score <= 1.0):
        print("[ERROR] 评分须在 0~1.0 之间")
        return 1
    rows = _read_csv(OKR_FILE)
    found = False
    interpretation = ""
    for r in rows:
        if r.get("编号") == args.id:
            r["评分"] = str(args.score)
            if args.score < 0.3:
                r["状态"] = "失败"
                interpretation = "失败 - 需复盘根因"
            elif args.score < 0.6:
                r["状态"] = "未达预期"
                interpretation = "未达预期 - 需改进"
            elif args.score <= 0.7:
                r["状态"] = "理想"
                interpretation = "理想区间 - 挑战性目标合理达成"
            elif args.score <= 0.9:
                r["状态"] = "超额"
                interpretation = "目标可能不够挑战"
            else:
                r["状态"] = "过于保守"
                interpretation = "过于保守 - 下季度需提高难度"
            found = True
            break
    if not found:
        print(f"[ERROR] 未找到 {args.id}")
        return 1
    _rewrite_csv(OKR_FILE, OKR_HEADER, rows)
    print(f"[okr] 评分: {args.id} = {args.score} ({interpretation})")
    return 0


def cmd_map(args):
    if not (1 <= args.score <= 5):
        print("[ERROR] 对齐度评分须在 1~5 之间")
        return 1
    rows = _read_csv(ALIGN_FILE)
    mid = _next_id("AL", rows)
    now = datetime.date.today().isoformat()
    header = ["编号", "项目名称", "战略主题", "对齐度评分", "映射日期", "确认状态"]
    _write_csv(ALIGN_FILE, header, [mid, args.project, args.theme, args.score, now, "待确认"])
    status = "已对齐" if args.score >= 3 else "弱对齐"
    print(f"[okr] 已映射: {args.project} -> {args.theme} (对齐度={args.score}, {status})")
    return 0


def cmd_audit(args):
    align = _read_csv(ALIGN_FILE)
    if not align:
        print("[okr] 无对齐记录")
        return 0
    projects = {}
    for a in align:
        p = a.get("项目名称", "?")
        projects.setdefault(p, []).append(a)
    aligned, weak, orphan = [], [], []
    for p, items in projects.items():
        max_score = max(int(i.get("对齐度评分", 0)) for i in items)
        if max_score >= 3:
            aligned.append(p)
        elif max_score > 0:
            weak.append((p, max_score))
        else:
            orphan.append(p)
    print(f"[okr] 对齐度审计（{len(projects)} 个项目）")
    print(f"  已对齐: {len(aligned)}")
    print(f"  弱对齐: {len(weak)}")
    for p, s in weak:
        print(f"    [WARN] {p} (最高评分={s})")
    print(f"  孤儿项目: {len(orphan)}")
    for p in orphan:
        print(f"    [FAIL] {p} (未映射任何战略主题)")
    if orphan:
        print(f"\n  建议: 孤儿项目须尽快映射战略主题，否则建议暂停或终止")
    return 1 if orphan else 0


def cmd_dashboard(args):
    okrs = _read_csv(OKR_FILE)
    align = _read_csv(ALIGN_FILE)
    print("[okr] OKR 仪表盘")
    if okrs:
        levels = {}
        for o in okrs:
            lv = o.get("层级", "?")
            levels.setdefault(lv, []).append(o)
        print(f"  OKR 总数: {len(okrs)}")
        for lv, items in sorted(levels.items()):
            print(f"    {lv}: {len(items)} 条")
        scored = [o for o in okrs if o.get("评分")]
        if scored:
            avg = sum(float(o["评分"]) for o in scored) / len(scored)
            print(f"  已评分: {len(scored)} 条，平均={avg:.2f}")
    else:
        print("  OKR 总数: 0")
    if align:
        projects = set(a.get("项目名称") for a in align)
        print(f"  已映射项目: {len(projects)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="OKR & Strategic Alignment CLI (S2)")
    sub = ap.add_subparsers(dest="command")

    c = sub.add_parser("create", help="创建 OKR")
    c.add_argument("--level", required=True, choices=["org", "program", "project"])
    c.add_argument("--objective", required=True)
    c.add_argument("--kr", default="")
    c.add_argument("--owner", default="")
    c.add_argument("--period", default="")
    c.add_argument("--target", default="")

    u = sub.add_parser("update", help="更新进度")
    u.add_argument("--id", required=True)
    u.add_argument("--progress", type=float, required=True)
    u.add_argument("--actual", default="")

    sc = sub.add_parser("score", help="OKR 评分")
    sc.add_argument("--id", required=True)
    sc.add_argument("--score", type=float, required=True)

    m = sub.add_parser("map", help="项目-战略主题映射")
    m.add_argument("--project", required=True)
    m.add_argument("--theme", required=True)
    m.add_argument("--score", type=int, required=True)

    sub.add_parser("audit", help="对齐度审计")
    sub.add_parser("dashboard", help="OKR 仪表盘")

    args = ap.parse_args()
    dispatch = {
        "create": cmd_create, "update": cmd_update, "score": cmd_score,
        "map": cmd_map, "audit": cmd_audit, "dashboard": cmd_dashboard,
    }
    if args.command in dispatch:
        sys.exit(dispatch[args.command](args))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
