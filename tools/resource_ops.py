#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resource_ops.py -- 资源运营管理工具 (S3)

行业锚定: PMI Resource Management + Theory of Constraints + Skills Matrix

CLI:
  python3 tools/resource_ops.py capacity --name "张三" --role "后端开发" --available 160
  python3 tools/resource_ops.py allocate --name "张三" --project "项目A" --hours 80
  python3 tools/resource_ops.py balance
  python3 tools/resource_ops.py skill --name "张三" --skills "Python:4,Java:3,SQL:3"
  python3 tools/resource_ops.py singlespot
"""
import os, sys, re, io, csv, argparse, datetime, json

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, "台账")
CAP_FILE = os.path.join(LEDGER, "48_资源容量.csv")
SKILL_FILE = os.path.join(LEDGER, "49_技能矩阵.csv")


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


CAP_HEADER = ["编号", "成员", "角色", "可用工时", "已分配", "利用率%", "项目分配", "登记日期"]


def cmd_capacity(args):
    rows = _read_csv(CAP_FILE)
    rid = _next_id("RC", rows)
    now = datetime.date.today().isoformat()
    _write_csv(CAP_FILE, CAP_HEADER, [rid, args.name, args.role, args.available, 0, "0", "", now])
    print(f"[resource] 已登记: {rid} {args.name} ({args.role}) 可用工时={args.available}h")
    return 0


def cmd_allocate(args):
    rows = _read_csv(CAP_FILE)
    found = False
    for r in rows:
        if r.get("成员") == args.name:
            prev = int(r.get("已分配", 0))
            avail = int(r.get("可用工时", 1))
            new_alloc = prev + args.hours
            util = round(new_alloc / avail * 100, 1) if avail else 0
            r["已分配"] = str(new_alloc)
            r["利用率%"] = str(util)
            prev_proj = r.get("项目分配", "")
            r["项目分配"] = f"{prev_proj}; {args.project}:{args.hours}h" if prev_proj else f"{args.project}:{args.hours}h"
            found = True
            status = "过载" if util > 85 else ("健康" if util >= 50 else "闲置")
            print(f"[resource] 已分配: {args.name} +{args.hours}h -> {args.project}")
            print(f"  已分配={new_alloc}h / 可用={avail}h 利用率={util}% ({status})")
            break
    if not found:
        print(f"[ERROR] 未找到成员: {args.name}")
        return 1
    _rewrite_csv(CAP_FILE, CAP_HEADER, rows)
    return 0


def cmd_balance(args):
    rows = _read_csv(CAP_FILE)
    if not rows:
        print("[resource] 无资源记录")
        return 0
    overload, healthy, idle = [], [], []
    for r in rows:
        util = float(r.get("利用率%", 0))
        name = r.get("成员", "?")
        if util > 85:
            overload.append((name, util))
        elif util >= 50:
            healthy.append((name, util))
        else:
            idle.append((name, util))
    print(f"[resource] 负载均衡（{len(rows)} 人）")
    print(f"  过载(>85%): {len(overload)}")
    for n, u in overload:
        print(f"    [WARN] {n}: {u}%")
    print(f"  健康(50-85%): {len(healthy)}")
    print(f"  闲置(<50%): {len(idle)}")
    for n, u in idle:
        print(f"    [HINT] {n}: {u}%")
    return 1 if overload else 0


SKILL_HEADER = ["编号", "成员", "技能清单", "熟练度", "登记日期", "单点风险"]


def cmd_skill(args):
    # 解析技能: "Python:4,Java:3,SQL:3"
    skills = {}
    for item in args.skills.split(","):
        parts = item.strip().split(":")
        if len(parts) == 2:
            skills[parts[0]] = int(parts[1])
    if not skills:
        print("[ERROR] 技能格式错误，示例: Python:4,Java:3,SQL:3")
        return 1
    rows = _read_csv(SKILL_FILE)
    sid = _next_id("SK", rows)
    now = datetime.date.today().isoformat()
    _write_csv(SKILL_FILE, SKILL_HEADER, [
        sid, args.name, json.dumps(list(skills.keys()), ensure_ascii=False),
        json.dumps(skills, ensure_ascii=False), now, ""
    ])
    print(f"[resource] 技能矩阵: {args.name}")
    for s, lv in skills.items():
        print(f"  {s}: {lv}/5")
    return 0


def cmd_singlespot(args):
    rows = _read_csv(SKILL_FILE)
    if not rows:
        print("[resource] 无技能记录")
        return 0
    # 统计每项技能有多少人掌握（熟练度>=3）
    skill_owners = {}
    for r in rows:
        try:
            prof = json.loads(r.get("熟练度", "{}"))
        except:
            continue
        for s, lv in prof.items():
            if lv >= 3:
                skill_owners.setdefault(s, []).append(r.get("成员", "?"))
    risks = {s: owners for s, owners in skill_owners.items() if len(owners) == 1}
    print(f"[resource] 单点故障检测（{len(skill_owners)} 项技能）")
    if risks:
        print(f"  [WARN] {len(risks)} 项技能仅 1 人掌握:")
        for s, owners in risks.items():
            print(f"    {s}: {owners[0]}")
    else:
        print("  无单点故障风险")
    return 1 if risks else 0


def main():
    ap = argparse.ArgumentParser(description="Resource Operations CLI (S3)")
    sub = ap.add_subparsers(dest="command")

    c = sub.add_parser("capacity", help="资源容量登记")
    c.add_argument("--name", required=True)
    c.add_argument("--role", required=True)
    c.add_argument("--available", type=int, required=True, help="可用工时(h)")

    a = sub.add_parser("allocate", help="资源分配")
    a.add_argument("--name", required=True)
    a.add_argument("--project", required=True)
    a.add_argument("--hours", type=int, required=True)

    sub.add_parser("balance", help="负载均衡检查")

    s = sub.add_parser("skill", help="技能矩阵")
    s.add_argument("--name", required=True)
    s.add_argument("--skills", required=True, help="格式: Python:4,Java:3")

    sub.add_parser("singlespot", help="单点故障检测")

    args = ap.parse_args()
    dispatch = {
        "capacity": cmd_capacity, "allocate": cmd_allocate, "balance": cmd_balance,
        "skill": cmd_skill, "singlespot": cmd_singlespot,
    }
    if args.command in dispatch:
        sys.exit(dispatch[args.command](args))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
