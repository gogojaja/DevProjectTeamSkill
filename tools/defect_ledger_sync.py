#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""defect_ledger_sync.py — T-04 缺陷台账同步器

将缺陷 JSON 同步到台账 CSV（追加/更新），解决痛点 P5（台账更新靠手工编辑）。

CLI（跨平台）：
  py -3.11 tools/defect_ledger_sync.py --defects <缺陷JSON> --ledger <台账目录> --round <轮次>
  py -3.11 tools/defect_ledger_sync.py --defects defects.json --ledger 台账/ --round 1

台账格式（CSV UTF-8 BOM）：
  缺陷编号,严重级别,功能模块,缺陷类型,缺陷描述,建议修复,发现轮次,状态,登记时间,更新时间

依赖：无
"""
import os
import sys
import io
import json
import csv
import argparse
from datetime import datetime

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LEDGER_HEADER = [
    "缺陷编号", "严重级别", "功能模块", "缺陷类型", "缺陷描述",
    "建议修复", "发现轮次", "状态", "登记时间", "更新时间"
]
LEDGER_FILENAME = "15_缺陷台账.csv"


def _now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _load_existing(ledger_path):
    """加载已有台账，返回 (已有行列表, 已有ID集合)。"""
    existing_rows = []
    existing_ids = set()
    if os.path.exists(ledger_path):
        with io.open(ledger_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= len(LEDGER_HEADER):
                    existing_rows.append(row)
                    existing_ids.add(row[0])
    return existing_rows, existing_ids


def sync_defects(defects_path, ledger_dir, round_num):
    """将缺陷 JSON 同步到台账 CSV。

    Args:
        defects_path: 缺陷清单 JSON 文件路径
        ledger_dir: 台账目录路径
        round_num: 发现轮次

    Returns:
        dict: {"added": N, "updated": N, "ledger_path": "..."}
    """
    if not os.path.exists(defects_path):
        print("错误: 文件不存在: %s" % defects_path)
        sys.exit(1)

    # 加载缺陷清单
    with io.open(defects_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    defects = data.get("defects", [])
    if not defects:
        print("警告: 缺陷清单为空")
        return {"added": 0, "updated": 0, "ledger_path": ""}

    # 确保台账目录存在
    os.makedirs(ledger_dir, exist_ok=True)
    ledger_path = os.path.join(ledger_dir, LEDGER_FILENAME)

    # 加载已有台账
    existing_rows, existing_ids = _load_existing(ledger_path)

    added = 0
    updated = 0
    now = _now()

    for d in defects:
        defect_id = d.get("id", "未知")
        row = [
            defect_id,
            d.get("severity", ""),
            d.get("module", ""),
            d.get("type", ""),
            d.get("description", ""),
            d.get("suggestion", ""),
            str(round_num),
            "新建",
            now,
            now,
        ]

        if defect_id in existing_ids:
            # 更新已有条目（保留原登记时间，更新更新时间）
            for i, er in enumerate(existing_rows):
                if er[0] == defect_id:
                    # 保留原登记时间（index 8），更新其余字段
                    row[8] = er[8] if len(er) > 8 else now
                    existing_rows[i] = row
                    updated += 1
                    break
        else:
            existing_rows.append(row)
            existing_ids.add(defect_id)
            added += 1

    # 写入台账
    with io.open(ledger_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(LEDGER_HEADER)
        writer.writerows(existing_rows)

    print("缺陷台账同步完成：")
    print("  缺陷源: %s（%d 条）" % (defects_path, len(defects)))
    print("  台账: %s" % ledger_path)
    print("  新增: %d | 更新: %d | 总计: %d" % (added, updated, len(existing_rows)))
    return {"added": added, "updated": updated, "ledger_path": ledger_path}


def main():
    ap = argparse.ArgumentParser(description="T-04 缺陷台账同步器")
    ap.add_argument("--defects", required=True, help="缺陷清单 JSON 文件路径")
    ap.add_argument("--ledger", required=True, help="台账目录路径")
    ap.add_argument("--round", type=int, default=1, help="发现轮次（默认 1）")
    args = ap.parse_args()
    sync_defects(args.defects, args.ledger, args.round)


if __name__ == "__main__":
    main()
