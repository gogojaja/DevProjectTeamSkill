#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raid_ops.py — RAID 四维台账 + 风险扫描权威工具 (risk-mgmt 技能)

行业锚定: PMBOK 7th（风险/问题绩效域）· RAID（Risks/Assumptions/Issues/Dependencies）·
          ISO 31000 风险管理 · PRINCE2 风险与问题管理
技能依赖: risk-mgmt 独立可部署技能（.trae/skills/risk-mgmt/）
内化来源: 吸收 dev-project-mgmt `raid_manager.py`（RAID 四维 CRUD + 状态流转 + 字段校验）
          + 本地 MCP `risk_scan`（概率×影响分级扫描），数据源统一为台账 12_风险问题台账.csv，
          单一信源迁移至 DevProjectTeamSkill 技能库（D2 内化决策）。

RAID 四维: risk（风险）/ assumption（假设）/ issue（问题）/ dependency（依赖）
状态流转: open → mitigating/investigating → closed（closed 为终态）
风险分级: 风险分 = 概率 × 影响（高=4/中=3/低=2）；P1>=12 / P2>=8 / P3>=4 / P4<4

CLI:
  python3 tools/raid_ops.py list [--type risk] [--status open]
  python3 tools/raid_ops.py add --type risk --desc "..." [--probability 高] [--impact 高] [--owner 张三] [--notes "..."]
  python3 tools/raid_ops.py update --id RAID-001 [--status mitigating] [--owner 李四] [--desc "..."] [--probability 中] [--impact 高] [--notes "..."]
  python3 tools/raid_ops.py close --id RAID-001
  python3 tools/raid_ops.py scan [--severity P1] [--json]
"""
import os, sys, re, io, csv, argparse, datetime, json

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, "台账")

# RAID 台账（directory_structure.md §6 权威 = 12_风险问题台账.csv；兼容旧名 RAID台账.csv 只读）
RAID_FILE = os.path.join(LEDGER, "12_风险问题台账.csv")
RAID_FILE_ALT = os.path.join(LEDGER, "RAID台账.csv")

# 规范 RAID 表头（吸收 raid_manager.RAID_HEADERS）
RAID_HEADERS = ["RAID_ID", "类型", "描述", "概率", "影响",
                "优先级", "状态", "责任人", "登记日期", "关闭日期", "备注"]
VALID_TYPES = {"risk", "assumption", "issue", "dependency"}
VALID_TRANSITIONS = {
    "open": {"mitigating", "investigating", "closed"},
    "mitigating": {"closed", "open"},
    "investigating": {"closed", "open"},
    "closed": set(),
}
TYPE_DEFAULT_STATUS = {"risk": "mitigating", "assumption": "open",
                       "issue": "investigating", "dependency": "open"}
# 防御式列名别名（兼容各项目 12_风险问题台账 差异 schema）
FIELD_ALIASES = {
    "RAID_ID": ["RAID_ID", "风险编号", "编号", "ID", "id"],
    "类型": ["类型", "类型(风险/问题)", "RAID类型", "type"],
    "描述": ["描述", "风险描述", "问题描述", "desc"],
    "概率": ["概率", "可能性", "probability"],
    "影响": ["影响", "严重度", "impact"],
    "优先级": ["优先级", "问题级别(P1~P4)", "问题级别", "级别", "priority"],
    "状态": ["状态", "status"],
    "责任人": ["责任人", "Owner", "owner", "负责人"],
    "登记日期": ["登记日期", "创建日期", "登记时间", "created"],
    "关闭日期": ["关闭日期", "解决日期", "closed_date"],
    "备注": ["备注", "应对方案", "notes"],
}
SEVERITY_MAP = {"P1": 12, "P2": 8, "P3": 4, "P4": 0}  # 风险分阈值（概率×影响，最高 4×4=16）


def _ensure_dir():
    os.makedirs(LEDGER, exist_ok=True)


def _raid_path():
    """返回写入目标（主文件）；主文件不存在但旧名存在时仍以主文件为准（只读兼容旧名）。"""
    return RAID_FILE


def _read_raw():
    """读取原始 RAID 行（主文件优先，回退旧名）。返回 (header, rows)。"""
    path = RAID_FILE if os.path.isfile(RAID_FILE) else (RAID_FILE_ALT if os.path.isfile(RAID_FILE_ALT) else RAID_FILE)
    if not os.path.isfile(path):
        return list(RAID_HEADERS), []
    with io.open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or RAID_HEADERS)
        rows = [dict(r) for r in reader]
    return header, rows


def _col_for(header, field):
    """在既有表头中找到 field 对应的实际列名（按别名）；无则返回规范名。"""
    for a in FIELD_ALIASES.get(field, [field]):
        if a in header:
            return a
    return field


def _get(row, field, default=""):
    """按别名从原始行取规范字段值。"""
    for a in FIELD_ALIASES.get(field, [field]):
        v = row.get(a)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return default


def _write_all(header, rows):
    """整表写入（保留既有列 + 补充规范列，非破坏式）。"""
    _ensure_dir()
    # 有效表头 = 既有 header ∪ 规范 RAID_HEADERS（缺失的规范列追加末尾）
    eff = list(header)
    for h in RAID_HEADERS:
        if h not in eff:
            eff.append(h)
    with io.open(RAID_FILE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=eff, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in eff})


def _next_id(rows):
    """生成下一个 RAID_ID（RAID-NNN）。"""
    max_num = 0
    for r in rows:
        rid = _get(r, "RAID_ID")
        m = re.search(r"(\d+)$", rid)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"RAID-{max_num + 1:03d}"


def _now_date():
    return datetime.date.today().isoformat()


def _parse_level(s, default=1):
    """解析概率/影响等级为数值（吸收 MCP risk_scan._parse_level）。"""
    if not s:
        return default
    s = str(s).strip().lower()
    if s in ("高", "high", "h", "4", "5"):
        return 4
    if s in ("中", "medium", "m", "3"):
        return 3
    if s in ("低", "low", "l", "1", "2"):
        return 2
    try:
        return int(s)
    except ValueError:
        return default


def _risk_score(row):
    """风险分 = 概率 × 影响。"""
    return _parse_level(_get(row, "概率", "1")) * _parse_level(_get(row, "影响", "1"))


def _severity_of(score):
    """风险分 → 等级 P1~P4。"""
    if score >= SEVERITY_MAP["P1"]:
        return "P1"
    if score >= SEVERITY_MAP["P2"]:
        return "P2"
    if score >= SEVERITY_MAP["P3"]:
        return "P3"
    return "P4"


def cmd_list(args):
    """列出 RAID 条目（可按类型/状态过滤）。"""
    header, rows = _read_raw()
    if args.type:
        if args.type not in VALID_TYPES:
            print(f"[ERROR] 无效 RAID 类型: {args.type}（合法: {sorted(VALID_TYPES)}）")
            return 1
        rows = [r for r in rows if _get(r, "类型") == args.type]
    if args.status:
        rows = [r for r in rows if _get(r, "状态") == args.status]
    if not rows:
        print("[raid] 无匹配 RAID 条目")
        return 0
    print(f"[raid] RAID 条目（{len(rows)} 条）")
    for r in rows:
        rid = _get(r, "RAID_ID", "?")
        typ = _get(r, "类型", "?")
        desc = _get(r, "描述", "")[:40]
        status = _get(r, "状态", "?")
        owner = _get(r, "责任人", "-")
        score = _risk_score(r)
        print(f"  [{rid}] 类型={typ} 状态={status} 风险分={score}({_severity_of(score)}) 责任人={owner} | {desc}")
    return 0


def cmd_add(args):
    """添加 RAID 条目。"""
    if args.type not in VALID_TYPES:
        print(f"[ERROR] 无效 RAID 类型: {args.type}（合法: {sorted(VALID_TYPES)}）")
        return 1
    header, rows = _read_raw()
    new_id = _next_id(rows)
    # 以规范字段构建，再映射到既有列名（非破坏式）
    canon = {
        "RAID_ID": new_id, "类型": args.type, "描述": args.desc,
        "概率": args.probability, "影响": args.impact,
        "优先级": args.priority or _severity_of(_parse_level(args.probability) * _parse_level(args.impact)),
        "状态": TYPE_DEFAULT_STATUS.get(args.type, "open"),
        "责任人": args.owner, "登记日期": _now_date(), "关闭日期": "", "备注": args.notes,
    }
    row = {}
    for field, val in canon.items():
        row[_col_for(header, field)] = val
    rows.append(row)
    _write_all(header, rows)
    score = _parse_level(args.probability) * _parse_level(args.impact)
    print(f"[raid] 已添加: {new_id} 类型={args.type} 状态={canon['状态']} 风险分={score}({_severity_of(score)})")
    print(f"  描述: {args.desc}")
    if args.type == "risk" and score >= SEVERITY_MAP["P1"]:
        print(f"  [WARN] P1 高风险，须立即升级并制定应对方案")
    return 0


def cmd_update(args):
    """更新 RAID 条目（含状态流转校验）。"""
    header, rows = _read_raw()
    target = None
    for r in rows:
        if _get(r, "RAID_ID") == args.id:
            target = r
            break
    if target is None:
        print(f"[ERROR] RAID 条目不存在: {args.id}")
        return 1
    # 状态流转校验（吸收 raid_manager.VALID_TRANSITIONS）
    if args.status:
        cur = _get(target, "状态", "open")
        allowed = VALID_TRANSITIONS.get(cur, set())
        if args.status not in allowed:
            print(f"[ERROR] 非法状态流转: {cur} → {args.status}（允许: {sorted(allowed) if allowed else '终态不可变更'}）")
            return 1
        target[_col_for(header, "状态")] = args.status
        if args.status == "closed":
            target[_col_for(header, "关闭日期")] = _now_date()
    # 其他可选字段
    for field, val in (("描述", args.desc), ("概率", args.probability), ("影响", args.impact),
                       ("责任人", args.owner), ("备注", args.notes), ("优先级", args.priority)):
        if val:
            target[_col_for(header, field)] = val
    _write_all(header, rows)
    print(f"[raid] 已更新: {args.id} 状态={_get(target,'状态','-')} 责任人={_get(target,'责任人','-')}")
    return 0


def cmd_close(args):
    """关闭 RAID 条目（等价 update --status closed）。"""
    header, rows = _read_raw()
    target = None
    for r in rows:
        if _get(r, "RAID_ID") == args.id:
            target = r
            break
    if target is None:
        print(f"[ERROR] RAID 条目不存在: {args.id}")
        return 1
    cur = _get(target, "状态", "open")
    if cur == "closed":
        print(f"[raid] {args.id} 已是关闭状态")
        return 0
    if "closed" not in VALID_TRANSITIONS.get(cur, set()):
        print(f"[ERROR] 非法状态流转: {cur} → closed（允许: {sorted(VALID_TRANSITIONS.get(cur, set()))}）")
        return 1
    target[_col_for(header, "状态")] = "closed"
    target[_col_for(header, "关闭日期")] = _now_date()
    _write_all(header, rows)
    print(f"[raid] 已关闭: {args.id}（关闭日期 {_now_date()}）")
    return 0


def cmd_scan(args):
    """风险扫描：概率×影响分级，过滤 >= severity 阈值（吸收 MCP risk_scan）。"""
    header, rows = _read_raw()
    if not rows:
        print("[raid] RAID 台账为空，无可扫描风险")
        if args.json:
            print(json.dumps({"total": 0, "matched": 0}, ensure_ascii=False))
        return 0
    threshold = SEVERITY_MAP.get(args.severity, SEVERITY_MAP["P1"])
    scored = []
    for r in rows:
        # 仅扫描未关闭项（closed 不再预警）
        if _get(r, "状态") == "closed":
            continue
        s = _risk_score(r)
        if s >= threshold:
            scored.append((s, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    if args.json:
        out = [{"RAID_ID": _get(r, "RAID_ID"), "类型": _get(r, "类型"), "描述": _get(r, "描述"),
                "概率": _get(r, "概率"), "影响": _get(r, "影响"), "风险分": s,
                "等级": _severity_of(s), "状态": _get(r, "状态"), "责任人": _get(r, "责任人")}
               for s, r in scored]
        print(json.dumps({"total": len(rows), "matched": len(scored), "severity": args.severity, "items": out}, ensure_ascii=False))
        return 0
    if not scored:
        print(f"[raid] 无 {args.severity} 及以上风险（共 {len(rows)} 条 RAID，未关闭项已扫描）")
        return 0
    print(f"[raid] 风险扫描：{len(scored)} 条 {args.severity}+ 风险（共 {len(rows)} 条 RAID）")
    for s, r in scored[:10]:
        rid = _get(r, "RAID_ID", "?")
        desc = _get(r, "描述", "")[:40]
        status = _get(r, "状态", "?")
        owner = _get(r, "责任人", "-")
        print(f"  [{rid}] 风险分={s}({_severity_of(s)}) 状态={status} 责任人={owner} | {desc}")
    if len(scored) > 10:
        print(f"  ... 共 {len(scored)} 条")
    print(f"\n铁律：P1 风险须立即升级；连续 2 次延期停止 AI 自动调整，推送人工决策。")
    return 0


def main():
    ap = argparse.ArgumentParser(description="RAID 四维台账 + 风险扫描 CLI (risk-mgmt 权威工具)")
    sub = ap.add_subparsers(dest="command")

    l = sub.add_parser("list", help="列出 RAID 条目")
    l.add_argument("--type", default="", help="按类型过滤 risk/assumption/issue/dependency")
    l.add_argument("--status", default="", help="按状态过滤 open/mitigating/investigating/closed")

    a = sub.add_parser("add", help="添加 RAID 条目")
    a.add_argument("--type", required=True, help="类型 risk/assumption/issue/dependency")
    a.add_argument("--desc", required=True, help="描述")
    a.add_argument("--probability", default="", help="概率（高/中/低 或 1~5）")
    a.add_argument("--impact", default="", help="影响（高/中/低 或 1~5）")
    a.add_argument("--priority", default="", help="优先级（缺省按风险分自动定级 P1~P4）")
    a.add_argument("--owner", default="", help="责任人")
    a.add_argument("--notes", default="", help="备注/应对方案")

    u = sub.add_parser("update", help="更新 RAID 条目（含状态流转校验）")
    u.add_argument("--id", required=True, help="RAID_ID")
    u.add_argument("--status", default="", help="新状态 open/mitigating/investigating/closed")
    u.add_argument("--desc", default="", help="描述")
    u.add_argument("--probability", default="", help="概率")
    u.add_argument("--impact", default="", help="影响")
    u.add_argument("--priority", default="", help="优先级")
    u.add_argument("--owner", default="", help="责任人")
    u.add_argument("--notes", default="", help="备注")

    c = sub.add_parser("close", help="关闭 RAID 条目")
    c.add_argument("--id", required=True, help="RAID_ID")

    s = sub.add_parser("scan", help="风险扫描（概率×影响分级）")
    s.add_argument("--severity", default="P1", choices=["P1", "P2", "P3", "P4"], help="最低等级阈值（默认 P1）")
    s.add_argument("--json", action="store_true", help="JSON 结构化输出")

    args = ap.parse_args()
    dispatch = {"list": cmd_list, "add": cmd_add, "update": cmd_update,
                "close": cmd_close, "scan": cmd_scan}
    if args.command in dispatch:
        sys.exit(dispatch[args.command](args))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
