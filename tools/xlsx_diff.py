#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xlsx_diff.py — T-02 Excel 版本对比器

对比两个 xlsx 文件的全工作表内容 → 输出差异清单 CSV。
解决痛点 P6（版本一致性检查靠人工对比）。

CLI（跨平台）：
  py -3.11 tools/xlsx_diff.py --old <旧xlsx> --new <新xlsx> --output diff.csv

输出：
  差异清单 CSV（UTF-8 BOM）：工作表,单元格,旧值,新值,变更类型

依赖：openpyxl（未安装时提示安装命令）
"""
import os
import sys
import io
import csv
import argparse

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def xlsx_diff(old_path, new_path, output_path=None):
    """对比两个 xlsx 文件。

    Args:
        old_path: 旧 xlsx 路径
        new_path: 新 xlsx 路径
        output_path: 输出 CSV 路径

    Returns:
        dict: 差异统计
    """
    if not HAS_OPENPYXL:
        print("错误: openpyxl 未安装。请运行: pip install openpyxl")
        sys.exit(1)

    for p in [old_path, new_path]:
        if not os.path.exists(p):
            print("错误: 文件不存在: %s" % p)
            sys.exit(1)

    wb_old = openpyxl.load_workbook(old_path, data_only=True)
    wb_new = openpyxl.load_workbook(new_path, data_only=True)

    diffs = []
    all_sheets = set(wb_old.sheetnames) | set(wb_new.sheetnames)

    for sheet in sorted(all_sheets):
        if sheet not in wb_old.sheetnames:
            diffs.append({"sheet": sheet, "cell": "-", "old": "（不存在）", "new": "（新增工作表）", "type": "新增"})
            continue
        if sheet not in wb_new.sheetnames:
            diffs.append({"sheet": sheet, "cell": "-", "old": "（存在）", "new": "（已删除）", "type": "删除"})
            continue

        ws_old = wb_old[sheet]
        ws_new = wb_new[sheet]
        max_row = max(ws_old.max_row or 0, ws_new.max_row or 0)
        max_col = max(ws_old.max_column or 0, ws_new.max_column or 0)

        for r in range(1, max_row + 1):
            for c in range(1, max_col + 1):
                cell_ref = ws_old.cell(r, c).coordinate
                old_val = ws_old.cell(r, c).value
                new_val = ws_new.cell(r, c).value

                old_str = str(old_val) if old_val is not None else ""
                new_str = str(new_val) if new_val is not None else ""

                if old_str != new_str:
                    change_type = "修改"
                    if not old_str:
                        change_type = "新增"
                    elif not new_str:
                        change_type = "删除"

                    diffs.append({
                        "sheet": sheet,
                        "cell": cell_ref,
                        "old": old_str[:100],
                        "new": new_str[:100],
                        "type": change_type,
                    })

    # 输出
    if not output_path:
        report_dir = os.path.join(ROOT, "docs", "reviews")
        os.makedirs(report_dir, exist_ok=True)
        base_old = os.path.splitext(os.path.basename(old_path))[0]
        base_new = os.path.splitext(os.path.basename(new_path))[0]
        output_path = os.path.join(report_dir, "xlsx_diff_%s_vs_%s.csv" % (base_old, base_new))

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with io.open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sheet", "cell", "old", "new", "type"])
        writer.writeheader()
        writer.writerows(diffs)

    added = len([d for d in diffs if d["type"] == "新增"])
    removed = len([d for d in diffs if d["type"] == "删除"])
    modified = len([d for d in diffs if d["type"] == "修改"])

    print("xlsx 版本对比完成：")
    print("  旧: %s" % old_path)
    print("  新: %s" % new_path)
    print("  差异: %d 处（新增 %d / 删除 %d / 修改 %d）" % (len(diffs), added, removed, modified))
    print("  输出: %s" % output_path)
    return {"total": len(diffs), "added": added, "removed": removed, "modified": modified, "output_path": output_path}


def main():
    ap = argparse.ArgumentParser(description="T-02 Excel 版本对比器")
    ap.add_argument("--old", required=True, help="旧 xlsx 文件路径")
    ap.add_argument("--new", required=True, help="新 xlsx 文件路径")
    ap.add_argument("--output", default=None, help="输出差异清单 CSV 路径")
    args = ap.parse_args()
    xlsx_diff(args.old, args.new, args.output)


if __name__ == "__main__":
    main()
