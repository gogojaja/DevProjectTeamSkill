#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review_report_gen.py — T-03 评审报告生成器

读取缺陷 JSON → 按严重级别统计 → 逐维度评分计算 → 输出标准 CSV（UTF-8 BOM）。
解决痛点 P2（评审报告手工拼接）。

CLI（跨平台）：
  py -3.11 tools/review_report_gen.py --defects <缺陷JSON> --object <评审对象> --version <版本号>
  py -3.11 tools/review_report_gen.py --defects defects.json --object "测试管理需求" --version "V1.2.1"

输入 JSON 格式（§3.5）：
  {"object":"...", "version_tag":"...", "reviewer":"...", "review_date":"...",
   "defects":[{"id":"DEF-001","severity":"严重","module":"...","type":"...","description":"...","suggestion":"..."}],
   "dimensions":[{"name":"完整性","weight":"25%","score":"70%","verdict":"部分通过"}]}

输出：
  台账/reviews/评审报告_<对象>_<版本>_缺陷.csv
  台账/reviews/评审报告_<对象>_<版本>_逐维度.csv
"""
import os
import sys
import io
import json
import csv
import datetime
import argparse

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOM = b"\xef\xbb\xbf"


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_filename(s):
    """将对象名转为安全文件名"""
    return s.replace("/", "_").replace("\\", "_").replace(" ", "_")


def generate_report(defects_json_path, obj_name, version, reviewer="", review_date=""):
    """生成评审报告（缺陷清单 + 逐维度评分）。

    Args:
        defects_json_path: 缺陷清单 JSON 文件路径
        obj_name: 评审对象名称
        version: 版本号
        reviewer: 评审人（可选，从 JSON 读取）
        review_date: 评审日期（可选，从 JSON 读取）

    Returns:
        tuple: (缺陷报告路径, 维度报告路径)
    """
    # 读取缺陷 JSON
    with io.open(defects_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    defects = data.get("defects", [])
    dimensions = data.get("dimensions", [])
    if not reviewer:
        reviewer = data.get("reviewer", "")
    if not review_date:
        review_date = data.get("review_date", _now()[:10])

    safe_obj = _safe_filename(obj_name)
    safe_ver = _safe_filename(version)
    report_dir = os.path.join(ROOT, "docs", "reviews")
    os.makedirs(report_dir, exist_ok=True)

    # ── 缺陷清单 CSV ──
    defect_path = os.path.join(report_dir, "评审报告_%s_%s_缺陷.csv" % (safe_obj, safe_ver))
    defect_header = ["缺陷编号", "严重级别", "功能模块", "缺陷类型", "缺陷描述",
                     "界面设计依据", "表单/规则依据", "建议修复方案", "提出人", "提出日期"]
    with io.open(defect_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(defect_header)
        for d in defects:
            w.writerow([
                d.get("id", ""),
                d.get("severity", ""),
                d.get("module", ""),
                d.get("type", ""),
                d.get("description", ""),
                d.get("evidence_ui", ""),
                d.get("evidence_form", ""),
                d.get("suggestion", ""),
                reviewer,
                review_date,
            ])

    # ── 逐维度评分 CSV ──
    dim_path = os.path.join(report_dir, "评审报告_%s_%s_逐维度.csv" % (safe_obj, safe_ver))
    dim_header = ["评审维度", "权重", "得分", "评审结论", "主要问题说明"]
    # 统计严重级别分布作为"主要问题说明"
    severity_count = {}
    for d in defects:
        s = d.get("severity", "未知")
        severity_count[s] = severity_count.get(s, 0) + 1
    severity_summary = "；".join("%s %d 项" % (k, v) for k, v in sorted(severity_count.items()))

    with io.open(dim_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(dim_header)
        for dim in dimensions:
            # 如果有缺陷，补充问题说明
            note = dim.get("note", "")
            if not note and defects:
                note = "共 %d 项缺陷（%s）" % (len(defects), severity_summary)
            w.writerow([
                dim.get("name", ""),
                dim.get("weight", ""),
                dim.get("score", ""),
                dim.get("verdict", ""),
                note,
            ])

    print("评审报告已生成：")
    print("  缺陷清单: %s（%d 条）" % (defect_path, len(defects)))
    print("  逐维度:   %s（%d 维）" % (dim_path, len(dimensions)))
    return defect_path, dim_path


def main():
    ap = argparse.ArgumentParser(description="T-03 评审报告生成器")
    ap.add_argument("--defects", required=True, help="缺陷清单 JSON 文件路径")
    ap.add_argument("--object", required=True, help="评审对象名称")
    ap.add_argument("--version", required=True, help="版本号")
    ap.add_argument("--reviewer", default="", help="评审人（可选，从 JSON 读取）")
    ap.add_argument("--date", default="", help="评审日期（可选，从 JSON 读取）")
    args = ap.parse_args()

    if not os.path.exists(args.defects):
        print("错误: 缺陷 JSON 文件不存在: %s" % args.defects)
        sys.exit(1)

    generate_report(args.defects, args.object, args.version, args.reviewer, args.date)


if __name__ == "__main__":
    main()
