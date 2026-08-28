#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计/授权台账自动埋点助手（铁律#7 四维定位增强）。

统一写入入口，自动捕获：
  - 主机标识   : socket.gethostname()  （铁律#8 B级，经 AUTH-021 授权明文保留）
  - 操作时间   : datetime.now().astimezone().isoformat() 含时区偏移（如 +08:00）
  - 会话ID     : 未传则生成 uuid4()，聚合同次 agent 运行的多操作
  - 模型名称   : 未传时读 opencode.json 的 model 字段，再降级 "未知"

用法：
  # 关键操作审计
  python3 tools/audit.py op \
      --type "修改项目外文件" --target "~/.config/opencode/opencode.jsonc" \
      --risk 中 --auth AUTH-020 --backup 是 --backup-path ".backup/xxx" \
      --result "成功" [--tool Trae] [--model ark-coding/deepseek-v4-flash] \
      [--session-id <uuid>] [--note "..."]

  # 授权登记
  python3 tools/audit.py auth \
      --object "..." --otype 文件 --path "..." --perm 改 \
      [--host gogojajadeMac-mini] [--valid-until 2026-08-28] \
      [--status 有效] --note "..."

输出：写入 台账/13_安全审计台账.csv 或 台账/14_授权登记.csv（UTF-8 / LF）。
"""
import argparse
import csv
import datetime
import json
import os
import re
import socket
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "台账", "13_安全审计台账.csv")
P14 = os.path.join(ROOT, "台账", "14_授权登记.csv")
TZ = datetime.timezone(datetime.timedelta(hours=8))


def now_iso():
    return datetime.datetime.now().astimezone(TZ).isoformat()


def normalize_host():
    """返回与 CMDB/授权台账一致的主机标识（剥离 macOS .local 与 -N 碰撞后缀）。"""
    h = socket.gethostname().split(".")[0]
    return re.sub(r"-\d+$", "", h)


def next_op_id():
    mx = 0
    if os.path.exists(P13):
        with open(P13, encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f):
                m = re.search(r"OP-AUDIT-(\d+)", row[0]) if row else None
                if m:
                    mx = max(mx, int(m.group(1)))
                m2 = re.search(r"AUD-(\d{8})-(\d+)", row[0]) if row else None
                if m2:
                    mx = max(mx, int(m2.group(2)))
    return f"OP-AUDIT-{mx+1:03d}"


def next_auth_id():
    mx = 0
    if os.path.exists(P14):
        with open(P14, encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f):
                m = re.search(r"AUTH-(\d+)", row[0]) if row else None
                if m:
                    mx = max(mx, int(m.group(1)))
    return f"AUTH-{mx+1:03d}"


def default_model():
    oc = os.path.join(ROOT, "opencode.json")
    try:
        with open(oc, encoding="utf-8") as f:
            cfg = json.load(f)
        m = cfg.get("model")
        if m:
            return m
    except Exception:
        pass
    return "未知"


def read_header(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f))


def write_row(path, header, row):
    existed = os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if not existed:
            w.writerow(header)
        w.writerow(row)


def cmd_op(args):
    header = ["操作ID", "会话ID", "主机标识", "客户端工具", "模型名称", "操作时间",
              "操作类型", "对象", "风险等级", "授权人", "授权ID", "是否备份",
              "备份路径", "留痕时间", "结果"]
    op_id = args.op_id or next_op_id()
    session = args.session_id or str(uuid.uuid4())
    host = normalize_host()
    tool = args.tool or "opencode"
    model = args.model or default_model()
    op_time = now_iso()
    note = args.note or ""
    result = args.result + (f"；{note}" if note else "")
    row = [op_id, session, host, tool, model, op_time, args.type, args.target,
           args.risk, args.actor, args.auth, args.backup, args.backup_path,
           op_time, result]
    write_row(P13, header, row)
    print(f"[audit] 已写 13 台账: {op_id} host={host} tool={tool} model={model} time={op_time}")


def cmd_auth(args):
    header = ["授权ID", "主机标识", "授权对象", "对象类型(目录/文件/系统)", "路径",
              "权限(读/写/改/删)", "授权人", "授权时间", "有效期至",
              "状态(有效/过期/已撤销)", "备注"]
    auth_id = args.auth_id or next_auth_id()
    host = args.host or normalize_host()
    note = args.note or ""
    row = [auth_id, host, args.object, args.otype, args.path, args.perm,
           args.actor, args.auth_time, args.valid_until, args.status, note]
    write_row(P14, header, row)
    print(f"[audit] 已写 14 台账: {auth_id} host={host} object={args.object}")


def main():
    ap = argparse.ArgumentParser(description="审计/授权台账自动埋点助手")
    sub = ap.add_subparsers(dest="kind", required=True)

    op = sub.add_parser("op", help="关键操作审计")
    op.add_argument("--op-id", default=None)
    op.add_argument("--session-id", default=None)
    op.add_argument("--type", required=True)
    op.add_argument("--target", required=True)
    op.add_argument("--risk", default="低")
    op.add_argument("--actor", default="<user>(本机)")
    op.add_argument("--auth", default="未知")
    op.add_argument("--backup", default="否")
    op.add_argument("--backup-path", default="不适用")
    op.add_argument("--result", required=True)
    op.add_argument("--tool", default=None)
    op.add_argument("--model", default=None)
    op.add_argument("--note", default=None)
    op.set_defaults(func=cmd_op)

    au = sub.add_parser("auth", help="授权登记")
    au.add_argument("--auth-id", default=None)
    au.add_argument("--host", default=None)
    au.add_argument("--object", required=True)
    au.add_argument("--otype", default="文件")
    au.add_argument("--path", required=True)
    au.add_argument("--perm", default="改")
    au.add_argument("--actor", default="<user>(本机)")
    au.add_argument("--auth-time", default=datetime.datetime.now(TZ).strftime("%Y-%m-%d"))
    au.add_argument("--valid-until", default="本会话")
    au.add_argument("--status", default="有效")
    au.add_argument("--note", default=None)
    au.set_defaults(func=cmd_auth)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
