#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""portfolio_ops.py — 项目组合管理工具 (S1)

行业锚定: PMI PfM + MoP + SAFe 6.0 LPM
技能依赖: portfolio-mgmt 子技能

CLI:
  python3 tools/portfolio_ops.py register --name "项目X" --theme "数字化转型" --category "战略投资" --sponsor "张三"
  python3 tools/portfolio_ops.py score --project "项目X" --alignment 4 --roi 3 --risk 4 --feasibility 5 --urgency 3
  python3 tools/portfolio_ops.py balance
  python3 tools/portfolio_ops.py optimize
  python3 tools/portfolio_ops.py review --project "项目X" --decision "Proceed"
  python3 tools/portfolio_ops.py track --project "项目X" --expected 100 --actual 85
  python3 tools/portfolio_ops.py dashboard
"""
import os, sys, re, io, csv, argparse, datetime, json

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, "台账")

REG_FILE = os.path.join(LEDGER, "43_组合注册.csv")
SCORE_FILE = os.path.join(LEDGER, "44_战略评分.csv")
VALUE_FILE = os.path.join(LEDGER, "45_组合价值兑现.csv")

# 战略评分默认权重
WEIGHTS = {"alignment": 0.30, "roi": 0.25, "risk": 0.20, "feasibility": 0.15, "urgency": 0.10}


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


def cmd_register(args):
    """组合注册"""
    rows = _read_csv(REG_FILE)
    pid = _next_id("PF", rows)
    now = datetime.date.today().isoformat()
    header = ["编号", "项目名称", "战略主题", "投资类别", "生命周期阶段", "Sponsor", "注册日期", "状态"]
    _write_csv(REG_FILE, header, [pid, args.name, args.theme, args.category, args.stage or "评估中", args.sponsor or "", now, "已注册"])
    print(f"[portfolio] 已注册: {pid} {args.name}")
    print(f"  战略主题: {args.theme}  投资类别: {args.category}  Sponsor: {args.sponsor or '-'}")
    return 0


def cmd_score(args):
    """战略评分"""
    scores = {
        "alignment": args.alignment,
        "roi": args.roi,
        "risk": args.risk,
        "feasibility": args.feasibility,
        "urgency": args.urgency,
    }
    # 验证评分范围
    for k, v in scores.items():
        if not (1 <= v <= 5):
            print(f"[ERROR] {k} 评分须在 1~5 之间（当前: {v}）")
            return 1

    weighted = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    # 决策建议
    if weighted >= 4.0 and scores["urgency"] >= 4:
        decision = "Accelerate"
    elif weighted >= 3.5:
        decision = "Proceed"
    elif weighted >= 2.5:
        decision = "Pause"
    else:
        decision = "Terminate"

    rows = _read_csv(SCORE_FILE)
    sid = _next_id("SC", rows)
    now = datetime.date.today().isoformat()
    header = ["编号", "项目", "战略对齐度", "ROI预期", "风险可控度", "资源可行性", "紧迫度",
              "加权总分", "排名", "评审日期", "决策建议"]
    _write_csv(SCORE_FILE, header, [
        sid, args.project, scores["alignment"], scores["roi"], scores["risk"],
        scores["feasibility"], scores["urgency"], f"{weighted:.2f}", "", now, decision
    ])
    print(f"[portfolio] 战略评分: {args.project}")
    print(f"  对齐度={scores['alignment']} ROI={scores['roi']} 风险={scores['risk']} "
          f"可行性={scores['feasibility']} 紧迫度={scores['urgency']}")
    print(f"  加权总分: {weighted:.2f} / 5.00  决策建议: {decision}")
    return 0


def cmd_balance(args):
    """组合平衡分析"""
    reg = _read_csv(REG_FILE)
    scores = _read_csv(SCORE_FILE)
    if not reg:
        print("[portfolio] 无注册项目")
        return 0

    # 按战略主题分组
    themes = {}
    for r in reg:
        t = r.get("战略主题", "未分类")
        themes.setdefault(t, []).append(r)

    # 按投资类别分组
    categories = {}
    for r in reg:
        c = r.get("投资类别", "未分类")
        categories.setdefault(c, []).append(r)

    print(f"[portfolio] 组合平衡分析（{len(reg)} 个项目）")
    print(f"\n  按战略主题:")
    for t, items in sorted(themes.items()):
        print(f"    {t}: {len(items)} 个项目")
    print(f"\n  按投资类别:")
    for c, items in sorted(categories.items()):
        print(f"    {c}: {len(items)} 个项目")

    # 评分分布
    if scores:
        total_scores = [float(s.get("加权总分", 0)) for s in scores if s.get("加权总分")]
        if total_scores:
            avg = sum(total_scores) / len(total_scores)
            print(f"\n  评分分布: 平均={avg:.2f} 最高={max(total_scores):.2f} 最低={min(total_scores):.2f}")
    return 0


def cmd_optimize(args):
    """组合优化建议"""
    scores = _read_csv(SCORE_FILE)
    if not scores:
        print("[portfolio] 无评分记录")
        return 0

    # 按加权总分排序
    ranked = sorted(scores, key=lambda s: float(s.get("加权总分", 0)), reverse=True)
    print(f"[portfolio] 组合优化建议（{len(ranked)} 个项目）")
    print(f"\n  优先级排序:")
    for i, s in enumerate(ranked, 1):
        score = s.get("加权总分", "?")
        decision = s.get("决策建议", "?")
        print(f"    {i}. {s.get('项目', '?')} (评分={score}, 建议={decision})")

    # 淘汰建议
    terminate = [s for s in ranked if float(s.get("加权总分", 5)) < 2.5]
    if terminate:
        print(f"\n  [WARN] 淘汰建议（评分 < 2.5）:")
        for s in terminate:
            print(f"    - {s.get('项目', '?')} (评分={s.get('加权总分', '?')})")

    # 暂停建议
    pause = [s for s in ranked if 2.5 <= float(s.get("加权总分", 0)) < 3.5]
    if pause:
        print(f"\n  [HINT] 暂停观察（评分 2.5~3.5）:")
        for s in pause:
            print(f"    - {s.get('项目', '?')} (评分={s.get('加权总分', '?')})")
    return 0


def cmd_review(args):
    """组合评审"""
    decision = args.decision
    valid = ["Proceed", "Accelerate", "Pause", "Terminate"]
    if decision not in valid:
        print(f"[ERROR] 决策须为 {valid} 之一")
        return 1

    rows = _read_csv(VALUE_FILE)
    rid = _next_id("VD", rows)
    now = datetime.date.today().isoformat()
    header = ["编号", "项目", "预期收益", "实际收益", "偏差率", "PRB决策", "决策日期", "备注"]
    _write_csv(VALUE_FILE, header, [rid, args.project, "", "", "", decision, now, args.note or ""])
    print(f"[portfolio] PRB 决策: {args.project} -> {decision}")
    return 0


def cmd_track(args):
    """价值兑现跟踪"""
    deviation = ((args.actual - args.expected) / args.expected * 100) if args.expected else 0
    rows = _read_csv(VALUE_FILE)
    tid = _next_id("VT", rows)
    now = datetime.date.today().isoformat()
    header = ["编号", "项目", "预期收益", "实际收益", "偏差率", "PRB决策", "决策日期", "备注"]
    _write_csv(VALUE_FILE, header, [
        tid, args.project, args.expected, args.actual, f"{deviation:.1f}%", "", now, args.note or ""
    ])
    status = "达标" if deviation >= -10 else ("偏差" if deviation >= -30 else "严重偏差")
    print(f"[portfolio] 价值跟踪: {args.project}")
    print(f"  预期={args.expected} 实际={args.actual} 偏差={deviation:.1f}% ({status})")
    return 0


def cmd_dashboard(args):
    """组合仪表盘"""
    reg = _read_csv(REG_FILE)
    scores = _read_csv(SCORE_FILE)
    values = _read_csv(VALUE_FILE)

    print(f"[portfolio] 组合仪表盘")
    print(f"  注册项目: {len(reg)}")
    if scores:
        proceed = len([s for s in scores if s.get("决策建议") == "Proceed"])
        accelerate = len([s for s in scores if s.get("决策建议") == "Accelerate"])
        pause = len([s for s in scores if s.get("决策建议") == "Pause"])
        terminate = len([s for s in scores if s.get("决策建议") == "Terminate"])
        print(f"  评分统计: Proceed={proceed} Accelerate={accelerate} Pause={pause} Terminate={terminate}")
    if values:
        on_track = len([v for v in values if v.get("偏差率", "0%").rstrip("%") not in ("", "N/A")
                        and float(v.get("偏差率", "0%").rstrip("%").replace("%", "")) >= -10])
        print(f"  价值兑现: {on_track}/{len(values)} 项目达标")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Portfolio Management CLI (S1)")
    sub = ap.add_subparsers(dest="command")

    r = sub.add_parser("register", help="组合注册")
    r.add_argument("--name", required=True, help="项目名称")
    r.add_argument("--theme", required=True, help="战略主题")
    r.add_argument("--category", default="战略投资", help="投资类别")
    r.add_argument("--stage", default="", help="生命周期阶段")
    r.add_argument("--sponsor", default="", help="Sponsor")

    s = sub.add_parser("score", help="战略评分")
    s.add_argument("--project", required=True, help="项目名称")
    s.add_argument("--alignment", type=int, required=True, help="战略对齐度 (1-5)")
    s.add_argument("--roi", type=int, required=True, help="ROI预期 (1-5)")
    s.add_argument("--risk", type=int, required=True, help="风险可控度 (1-5)")
    s.add_argument("--feasibility", type=int, required=True, help="资源可行性 (1-5)")
    s.add_argument("--urgency", type=int, required=True, help="紧迫度 (1-5)")

    sub.add_parser("balance", help="组合平衡分析")
    sub.add_parser("optimize", help="组合优化建议")

    v = sub.add_parser("review", help="组合评审")
    v.add_argument("--project", required=True, help="项目名称")
    v.add_argument("--decision", required=True, choices=["Proceed", "Accelerate", "Pause", "Terminate"])
    v.add_argument("--note", default="", help="备注")

    t = sub.add_parser("track", help="价值兑现跟踪")
    t.add_argument("--project", required=True, help="项目名称")
    t.add_argument("--expected", type=float, required=True, help="预期收益")
    t.add_argument("--actual", type=float, required=True, help="实际收益")
    t.add_argument("--note", default="", help="备注")

    sub.add_parser("dashboard", help="组合仪表盘")

    args = ap.parse_args()
    dispatch = {
        "register": cmd_register, "score": cmd_score, "balance": cmd_balance,
        "optimize": cmd_optimize, "review": cmd_review, "track": cmd_track,
        "dashboard": cmd_dashboard,
    }
    if args.command in dispatch:
        sys.exit(dispatch[args.command](args))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
