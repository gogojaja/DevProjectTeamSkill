#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evm_ops.py — 进度成本挣值（EVM）权威工具 (schedule-cost 技能)

行业锚定: PMBOK 7th（进度/成本绩效域）· EVM（ANSI/EIA-748）· ISO 21500
技能依赖: schedule-cost 独立可部署技能（.trae/skills/schedule-cost/）
内化来源: 吸收 dev-project-mgmt `evm_calculator.py` 的 EVM 指标公式
          （PV/EV/AC/CPI/SPI/CV/SV/准点率），数据源由 SQLite 改为台账 CSV，
          单一信源迁移至 DevProjectTeamSkill 技能库（D2 内化决策）。

EVM 核心指标（公式与 dev-project-mgmt 一致）:
- PV（Planned Value）计划值 = Σ 里程碑计划值
- EV（Earned Value）挣值   = Σ 已完成里程碑计划值（里程碑 0/100 规则：完成计全额 PV，未完成计 0）
- AC（Actual Cost）实际成本 = 台账 10_成本消耗 累计消耗；缺失时回退「计划值 × 时间进度比」估算
- CPI = EV / AC（成本绩效指数，>1 成本节约）
- SPI = EV / PV（进度绩效指数，>1 进度超前）
- CV  = EV - AC（成本偏差）  SV = EV - PV（进度偏差）
- 准点率 = 准点完成里程碑数 / 里程碑总数（实际完成日 <= 计划完成日）

CLI:
  python3 tools/evm_ops.py calc [--milestone M1] [--json]
  python3 tools/evm_ops.py status
  python3 tools/evm_ops.py add-milestone --id M1 --name "需求基线" [--start 2026-09-01] [--end 2026-09-30] [--value 1000]
  python3 tools/evm_ops.py update-milestone --id M1 [--status 已完成] [--actual-end 2026-09-28] [--completion 100]
"""
import os, sys, re, io, csv, argparse, datetime, json

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, "台账")

# 台账数据源（directory_structure.md §6 权威 schema；各项目列名有差异，读取时防御式别名）
PROGRESS_BASE_FILE = os.path.join(LEDGER, "03_进度基准.csv")       # 阶段/里程碑/计划日期
COST_BASE_FILE = os.path.join(LEDGER, "04_成本基准.csv")           # 成本阈值/预估工时（BAC 来源）
PROGRESS_TRACK_FILE = os.path.join(LEDGER, "09_进度跟踪台账.csv")   # 里程碑状态/完成率/计划·实际日期
COST_CONSUME_FILE = os.path.join(LEDGER, "10_成本消耗台账.csv")     # 工时消耗/资源成本/累计消耗（AC 来源）

# 里程碑状态归一：判定「已完成」
DONE_TOKENS = ("已完成", "完成", "已交付", "done", "closed", "complete")
# add-milestone 写入 09 的规范表头（向后兼容各项目既有列；读取走别名）
TRACK_HEADER = ["里程碑编号", "里程碑名称", "计划开始", "计划日期", "计划值",
                "实际日期", "任务完成率", "状态", "更新日期"]


def _ensure_dir():
    os.makedirs(LEDGER, exist_ok=True)


def _read_csv(path):
    if not os.path.isfile(path):
        return []
    with io.open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _rewrite_csv(path, header, rows):
    """整表重写（用于 update-milestone）。rows 为 list[dict]。"""
    _ensure_dir()
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _append_row(path, header, row):
    """追加单行（用于 add-milestone）；文件空则先写表头。"""
    _ensure_dir()
    exists = os.path.isfile(path) and os.path.getsize(path) > 0
    with io.open(path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(header)
        w.writerow([row.get(h, "") for h in header])


def _get(row, *aliases, **kw):
    """防御式取列值：按别名顺序返回首个非空值，否则 default。"""
    default = kw.get("default", "")
    for a in aliases:
        v = row.get(a)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return default


def _to_float(s, default=0.0):
    try:
        return float(str(s).strip().rstrip("%"))
    except (ValueError, TypeError, AttributeError):
        return default


def _parse_date(s):
    """解析 YYYY-MM-DD（容错斜杠/中文），失败返回 None。"""
    if not s:
        return None
    s = str(s).strip().replace("/", "-").replace("年", "-").replace("月", "-").replace("日", "")
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _is_done(status):
    s = str(status or "").strip().lower()
    return any(t.lower() in s for t in DONE_TOKENS)


def _bac_from_cost_base():
    """从 04_成本基准 推导总预算 BAC（成本阈值/预算 列；多行取首个非空，否则求和预估工时×费率略）。"""
    rows = _read_csv(COST_BASE_FILE)
    for r in rows:
        v = _get(r, "成本阈值", "预算", "BAC", "总预算", "成本基准")
        if v:
            f = _to_float(v)
            if f > 0:
                return f
    return 0.0


def _load_milestones():
    """从 09_进度跟踪台账 加载里程碑（防御式别名）；缺失计划值时按 BAC 均摊或默认 1.0。"""
    rows = _read_csv(PROGRESS_TRACK_FILE)
    ms = []
    for r in rows:
        mid = _get(r, "里程碑编号", "编号", "ID", "milestone_id", "里程碑")
        name = _get(r, "里程碑名称", "里程碑", "名称", "name")
        if not mid and not name:
            continue
        pv_raw = _get(r, "计划值", "计划值(PV)", "PV", "预算", "planned_value")
        completion = _to_float(_get(r, "任务完成率", "完成率", "completion", default="0"), 0.0)
        completion = max(0.0, min(100.0, completion)) / 100.0
        status = _get(r, "状态", "status", default="未开始")
        ms.append({
            "id": mid or name,
            "name": name or mid,
            "planned_start": _get(r, "计划开始", "计划开始日期", "planned_start"),
            "planned_end": _get(r, "计划日期", "计划完成日期", "计划结束", "planned_end"),
            "actual_end": _get(r, "实际日期", "实际完成日期", "actual_end"),
            "pv": _to_float(pv_raw, -1.0),  # -1 标记「未显式声明」，稍后回退
            "completion": completion,
            "status": status,
            "done": _is_done(status),
        })
    # 计划值回退：BAC 均摊 → 默认 1.0（保证 SPI/CPI 比值可算）
    if ms and any(m["pv"] < 0 for m in ms):
        bac = _bac_from_cost_base()
        n = len(ms)
        fallback = (bac / n) if bac > 0 else 1.0
        for m in ms:
            if m["pv"] < 0:
                m["pv"] = fallback
    return ms


def _actual_cost_from_ledger(pv_total):
    """从 10_成本消耗台账 取实际成本 AC：优先「累计消耗」最大值，否则 Σ(资源成本+工具成本)。
    台账无数据时返回 None（调用方回退时间进度比估算）。"""
    rows = _read_csv(COST_CONSUME_FILE)
    if not rows:
        return None
    cumulative = []
    summed = 0.0
    for r in rows:
        c = _get(r, "累计消耗", "累计成本", "cumulative")
        if c:
            cumulative.append(_to_float(c))
        res = _to_float(_get(r, "资源成本", "resource_cost"))
        tool = _to_float(_get(r, "工具成本", "tool_cost"))
        summed += res + tool
    if cumulative:
        return max(cumulative)
    if summed > 0:
        return summed
    return None


def _estimate_ac_by_time(ms, today):
    """时间进度比估算 AC（dev-project-mgmt 回退逻辑）：
    ac_i = pv_i × clamp((today - planned_start)/(planned_end - planned_start), 0, 1)；
    无计划开始/结束则回退 pv_i × 完成度（完成度缺省 0.5）。"""
    ac = 0.0
    for m in ms:
        ps = _parse_date(m["planned_start"])
        pe = _parse_date(m["planned_end"])
        if ps and pe and pe > ps:
            ratio = (today - ps).days / (pe - ps).days
            ratio = max(0.0, min(1.0, ratio))
            ac += m["pv"] * ratio
        else:
            comp = m["completion"] if m["completion"] > 0 else 0.5
            ac += m["pv"] * comp
    return ac


def _compute_evm(ms, today, milestone_id=None):
    """核心 EVM 计算（公式与 dev-project-mgmt evm_calculator 一致）。"""
    if milestone_id:
        ms = [m for m in ms if m["id"] == milestone_id or m["name"] == milestone_id]
    total = len(ms)
    if total == 0:
        return {
            "calc_date": today.isoformat(), "milestone_id": milestone_id or "全部",
            "pv": 0.0, "ev": 0.0, "ac": 0.0, "cpi": 0.0, "spi": 0.0,
            "cv": 0.0, "sv": 0.0, "on_time_rate": 0.0, "milestone_count": 0,
            "ac_source": "无里程碑", "health": "无数据",
        }
    pv_total = sum(m["pv"] for m in ms)
    # EV 采里程碑 0/100 规则（与 dev-project-mgmt evm_calculator 一致）：已完成里程碑计入全额计划值，未完成计 0
    ev_total = sum(m["pv"] for m in ms if m["done"])
    # 准点率：已完成且实际完成日 <= 计划完成日
    on_time = 0
    for m in ms:
        if m["done"]:
            ae = _parse_date(m["actual_end"])
            pe = _parse_date(m["planned_end"])
            if ae and pe and ae <= pe:
                on_time += 1
    on_time_rate = on_time / total if total else 0.0
    # AC：优先台账实际成本，回退时间进度比估算
    ac_ledger = _actual_cost_from_ledger(pv_total)
    if ac_ledger is not None:
        ac_total = ac_ledger
        ac_source = "台账10_成本消耗"
    else:
        ac_total = _estimate_ac_by_time(ms, today)
        ac_source = "时间进度比估算"
    cpi = ev_total / ac_total if ac_total > 0 else 0.0
    spi = ev_total / pv_total if pv_total > 0 else 0.0
    cv = ev_total - ac_total
    sv = ev_total - pv_total
    # 健康判定（CPI/SPI 双维）
    if cpi >= 1.0 and spi >= 1.0:
        health = "✅ 健康（成本节约+进度超前）"
    elif cpi >= 0.9 and spi >= 0.9:
        health = "⚠️ 轻度偏差（需关注）"
    else:
        health = "❗ 严重偏差（成本超支/进度滞后，须纠偏）"
    return {
        "calc_date": today.isoformat(), "milestone_id": milestone_id or "全部",
        "pv": round(pv_total, 2), "ev": round(ev_total, 2), "ac": round(ac_total, 2),
        "cpi": round(cpi, 4), "spi": round(spi, 4),
        "cv": round(cv, 2), "sv": round(sv, 2),
        "on_time_rate": round(on_time_rate, 4), "milestone_count": total,
        "ac_source": ac_source, "health": health,
    }


def cmd_calc(args):
    """计算 EVM 指标（PV/EV/AC/CPI/SPI/CV/SV/准点率）。"""
    today = datetime.date.today()
    ms = _load_milestones()
    if not ms:
        print("[evm] 09_进度跟踪台账 无里程碑数据。请先 add-milestone 或检查台账。")
        if args.json:
            print(json.dumps({"milestone_count": 0}, ensure_ascii=False))
        return 0
    r = _compute_evm(ms, today, milestone_id=args.milestone or None)
    if args.json:
        print(json.dumps(r, ensure_ascii=False))
        return 0
    print(f"[evm] 挣值分析（{r['milestone_id']}，{r['milestone_count']} 个里程碑，计算日 {r['calc_date']}）")
    print(f"  PV(计划值)={r['pv']}  EV(挣值)={r['ev']}  AC(实际成本)={r['ac']}  [AC来源: {r['ac_source']}]")
    print(f"  CPI={r['cpi']}  SPI={r['spi']}  CV={r['cv']}  SV={r['sv']}  准点率={r['on_time_rate']}")
    print(f"  健康判定: {r['health']}")
    if r["cpi"] and r["cpi"] < 1.0:
        print(f"  [WARN] 成本超支（CPI<1）：每投入 1 元仅产出 {r['cpi']} 元挣值")
    if r["spi"] and r["spi"] < 1.0:
        print(f"  [WARN] 进度滞后（SPI<1）：仅完成计划进度的 {r['spi']*100:.1f}%")
    return 0


def cmd_status(args):
    """查看全部里程碑状态 + 最近 EVM 概览。"""
    today = datetime.date.today()
    ms = _load_milestones()
    if not ms:
        print("[evm] 无里程碑数据。")
        return 0
    print(f"[evm] 里程碑状态（{len(ms)} 个）")
    for m in ms:
        flag = "✓" if m["done"] else ("→" if m["completion"] > 0 else "·")
        pe = m["planned_end"] or "-"
        ae = m["actual_end"] or "-"
        print(f"  {flag} [{m['id']}] {m['name']}  状态={m['status']}  完成率={m['completion']*100:.0f}%  计划完成={pe}  实际完成={ae}  PV={m['pv']}")
    r = _compute_evm(ms, today)
    print(f"\n  EVM 概览: PV={r['pv']} EV={r['ev']} AC={r['ac']} CPI={r['cpi']} SPI={r['spi']} 准点率={r['on_time_rate']}")
    print(f"  健康判定: {r['health']}")
    return 0


def cmd_add_milestone(args):
    """添加里程碑到 09_进度跟踪台账（规范表头，向后兼容既有列）。"""
    rows = _read_csv(PROGRESS_TRACK_FILE)
    # 去重：同 ID 已存在则拒绝（防重复登记）
    for r in rows:
        if _get(r, "里程碑编号", "编号", "ID", "milestone_id", "里程碑") == args.id:
            print(f"[ERROR] 里程碑 {args.id} 已存在（请用 update-milestone 更新）")
            return 1
    today = datetime.date.today().isoformat()
    row = {
        "里程碑编号": args.id, "里程碑名称": args.name,
        "计划开始": args.start or "", "计划日期": args.end or "",
        "计划值": f"{args.value:g}" if args.value else "",
        "实际日期": "", "任务完成率": "0", "状态": "未开始", "更新日期": today,
    }
    # 若既有台账有不同表头，沿用既有表头追加（防御式）
    if rows:
        header = list(rows[0].keys())
        for h in TRACK_HEADER:
            if h not in header:
                header.append(h)
    else:
        header = TRACK_HEADER
    _append_row(PROGRESS_TRACK_FILE, header, row)
    print(f"[evm] 已添加里程碑: {args.id} {args.name}")
    print(f"  计划开始={args.start or '-'}  计划完成={args.end or '-'}  计划值PV={args.value or '-'}")
    return 0


def cmd_update_milestone(args):
    """更新里程碑状态/实际完成日/完成率（整表重写 09）。"""
    rows = _read_csv(PROGRESS_TRACK_FILE)
    if not rows:
        print("[ERROR] 09_进度跟踪台账 为空，无可更新里程碑")
        return 1
    header = list(rows[0].keys())
    for h in TRACK_HEADER:
        if h not in header:
            header.append(h)
    target = None
    for r in rows:
        if _get(r, "里程碑编号", "编号", "ID", "milestone_id", "里程碑") == args.id:
            target = r
            break
    if target is None:
        print(f"[ERROR] 里程碑不存在: {args.id}")
        return 1
    today = datetime.date.today().isoformat()
    if args.status:
        target["状态"] = args.status
    if args.actual_end:
        target["实际日期"] = args.actual_end
    if args.completion is not None:
        target["任务完成率"] = str(max(0, min(100, args.completion)))
    # 状态置为已完成且未填实际完成日时，默认今天
    if _is_done(target.get("状态", "")) and not _get(target, "实际日期", "实际完成日期", "actual_end"):
        target["实际日期"] = today
    target["更新日期"] = today
    _rewrite_csv(PROGRESS_TRACK_FILE, header, rows)
    print(f"[evm] 已更新里程碑: {args.id}  状态={target.get('状态','-')}  完成率={target.get('任务完成率','-')}%  实际完成={target.get('实际日期','-')}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="EVM 挣值分析 CLI (schedule-cost 权威工具)")
    sub = ap.add_subparsers(dest="command")

    c = sub.add_parser("calc", help="计算 EVM 指标 PV/EV/AC/CPI/SPI/CV/SV/准点率")
    c.add_argument("--milestone", default="", help="仅计算指定里程碑（默认全部）")
    c.add_argument("--json", action="store_true", help="JSON 结构化输出（供 MCP/PMO 消费）")

    sub.add_parser("status", help="查看全部里程碑状态 + EVM 概览")

    a = sub.add_parser("add-milestone", help="添加里程碑到 09_进度跟踪台账")
    a.add_argument("--id", required=True, help="里程碑编号")
    a.add_argument("--name", required=True, help="里程碑名称")
    a.add_argument("--start", default="", help="计划开始日期 YYYY-MM-DD")
    a.add_argument("--end", default="", help="计划完成日期 YYYY-MM-DD")
    a.add_argument("--value", type=float, default=0.0, help="计划值 PV（缺省则按 BAC 均摊）")

    u = sub.add_parser("update-milestone", help="更新里程碑状态/实际完成日/完成率")
    u.add_argument("--id", required=True, help="里程碑编号")
    u.add_argument("--status", default="", help="新状态（未开始/进行中/已完成/延期）")
    u.add_argument("--actual-end", dest="actual_end", default="", help="实际完成日期 YYYY-MM-DD")
    u.add_argument("--completion", type=int, default=None, help="任务完成率 0~100")

    args = ap.parse_args()
    dispatch = {
        "calc": cmd_calc, "status": cmd_status,
        "add-milestone": cmd_add_milestone, "update-milestone": cmd_update_milestone,
    }
    if args.command in dispatch:
        sys.exit(dispatch[args.command](args))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
