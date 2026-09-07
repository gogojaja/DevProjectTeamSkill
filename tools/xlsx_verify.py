#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xlsx_verify.py — T-06 Excel 修复验证器

读取修复后 xlsx + 原始缺陷 JSON → 逐条验证缺陷是否已修复 → 输出验证矩阵 CSV。
解决痛点 P4（修复后人工逐条核对）。

CLI（跨平台）：
  py -3.11 tools/xlsx_verify.py --input <xlsx路径> --defects <缺陷JSON>
  py -3.11 tools/xlsx_verify.py --input fixed.xlsx --defects defects.json --output verify.csv

缺陷 JSON 格式（与 T-03 输入一致）：
  {"defects":[
    {"id":"DEF-001","cell":"B5","sheet":"Sheet1","expected":"计算后回显","description":"..."},
    ...
  ]}

输出：
  验证矩阵 CSV（UTF-8 BOM）：缺陷编号,结果,实际值,预期值,说明
  结果 = 已修复 / 未修复 / 无法判定

依赖：openpyxl（未安装时提示安装命令）
"""
import os
import sys
import io
import json
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


def verify_xlsx(input_path, defects_path, output_path=None):
    """验证修复后 xlsx 中缺陷是否已修复。

    Args:
        input_path: 修复后 xlsx 文件路径
        defects_path: 原始缺陷 JSON 文件路径
        output_path: 输出 CSV 路径（None 则自动生成）

    Returns:
        str: 输出文件路径
    """
    if not HAS_OPENPYXL:
        print("错误: openpyxl 未安装。请运行: pip install openpyxl")
        sys.exit(1)

    for p in [input_path, defects_path]:
        if not os.path.exists(p):
            print("错误: 文件不存在: %s" % p)
            sys.exit(1)

    # 加载缺陷清单
    with io.open(defects_path, "r", encoding="utf-8") as f:
        defect_data = json.load(f)

    defects = defect_data.get("defects", [])
    if not defects:
        print("警告: 缺陷清单为空")
        return None

    # 加载修复后 xlsx
    wb = openpyxl.load_workbook(input_path, data_only=True)

    if not output_path:
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(ROOT, "docs", "reviews", base + "_verify.csv")

    # 确保输出目录存在
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    results = []
    fixed = 0
    unfixed = 0
    undetermined = 0

    for defect in defects:
        defect_id = defect.get("id", "未知")
        cell_ref = defect.get("cell", "")
        sheet_name = defect.get("sheet", "")
        expected = defect.get("expected", "")
        description = defect.get("description", "")

        actual_value = ""
        verdict = "无法判定"

        if cell_ref and sheet_name:
            try:
                if sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    cell = ws[cell_ref]
                    actual_value = str(cell.value) if cell.value is not None else ""

                    # 验证逻辑：对比实际值与预期值
                    if expected:
                        if expected in actual_value or actual_value == expected:
                            verdict = "已修复"
                            fixed += 1
                        else:
                            verdict = "未修复"
                            unfixed += 1
                    else:
                        # 无预期值，仅记录实际值供人工判定
                        verdict = "无法判定"
                        undetermined += 1
                else:
                    verdict = "无法判定"
                    actual_value = "工作表不存在: %s" % sheet_name
                    undetermined += 1
            except Exception as e:
                verdict = "无法判定"
                actual_value = "读取异常: %s" % str(e)
                undetermined += 1
        else:
            # 无单元格引用，无法自动验证
            verdict = "无法判定"
            undetermined += 1

        results.append({
            "defect_id": defect_id,
            "verdict": verdict,
            "actual_value": actual_value,
            "expected_value": expected,
            "description": description,
        })

    # 写入 CSV（UTF-8 BOM）
    with io.open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["defect_id", "verdict", "actual_value", "expected_value", "description"])
        writer.writeheader()
        writer.writerows(results)

    # 输出摘要
    total = len(results)
    print("xlsx 修复验证完成：")
    print("  输入: %s" % input_path)
    print("  缺陷源: %s" % defects_path)
    print("  输出: %s" % output_path)
    print("  总计: %d 条" % total)
    print("  已修复: %d | 未修复: %d | 无法判定: %d" % (fixed, unfixed, undetermined))
    if total > 0:
        rate = fixed * 100.0 / total
        print("  修复率: %.1f%%" % rate)

    return output_path


def main():
    ap = argparse.ArgumentParser(description="T-06 Excel 修复验证器")
    ap.add_argument("--input", required=True, help="修复后 xlsx 文件路径")
    ap.add_argument("--defects", required=True, help="原始缺陷 JSON 文件路径")
    ap.add_argument("--output", default=None, help="输出验证矩阵 CSV 路径")
    args = ap.parse_args()
    verify_xlsx(args.input, args.defects, args.output)


if __name__ == "__main__":
    main()
