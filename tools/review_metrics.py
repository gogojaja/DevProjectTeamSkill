#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review_metrics.py — T-13 评审效能度量器

从评审报告 CSV + 缺陷台账 + 决策记录聚合 → 计算效能指标。
解决痛点 P14（评审效能无法量化）。

CLI（跨平台）：
  py -3.11 tools/review_metrics.py --period 2026-09 --output metrics.csv
  py -3.11 tools/review_metrics.py --output metrics.csv  # 默认当月

输出：
  效能仪表盘数据 CSV（UTF-8 BOM）：
  评审类型,评审次数,发现缺陷数,严重缺陷数,平均缺陷/评审,评审覆盖率

数据源：
  - docs/reviews/*.csv（评审报告）
  - 台账/15_缺陷台账.csv（缺陷台账）
  - 台账/42_决策记录.jsonl（决策记录）

依赖：无
"""
import os
import sys
import io
import csv
import json
import re
import argparse
from datetime import datetime
from collections import defaultdict

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _scan_review_reports(period, reviews_dir):
    """扫描评审报告目录，统计评审次数和缺陷数。

    Returns:
        dict: {"review_count": N, "defect_count": N, "severe_count": N, "by_type": {...}}
    """
    stats = {"review_count": 0, "defect_count": 0, "severe_count": 0, "by_type": defaultdict(int)}

    if not os.path.exists(reviews_dir):
        return stats

    for fname in os.listdir(reviews_dir):
        if not fname.endswith(".csv"):
            continue

        fpath = os.path.join(reviews_dir, fname)
        # 按文件名判断评审类型
        review_type = "其他"
        if "评审报告" in fname and "缺陷" in fname:
            review_type = "文档评审"
        elif "代码评审" in fname:
            review_type = "代码评审"
        elif "架构合规" in fname:
            review_type = "架构评审"
        elif "需求质量" in fname:
            review_type = "需求评审"
        elif "依赖漏洞" in fname:
            review_type = "安全评审"
        elif "环境比对" in fname:
            review_type = "投产评审"

        # 检查文件修改时间是否在周期内
        try:
            mtime = os.path.getmtime(fpath)
            file_date = datetime.fromtimestamp(mtime)
            if period:
                if file_date.strftime("%Y-%m") != period:
                    continue
        except Exception:
            pass

        # 读取 CSV 统计缺陷
        try:
            with io.open(fpath, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    continue
                rows = list(reader)

            stats["review_count"] += 1
            stats["by_type"][review_type] += 1

            # 统计缺陷数（如果有严重级别列）
            for row in rows:
                if len(row) >= 2:
                    stats["defect_count"] += 1
                    severity = row[1] if len(row) > 1 else ""
                    if severity in ("严重", "高", "critical", "high"):
                        stats["severe_count"] += 1
        except Exception:
            pass

    return stats


def _scan_defect_ledger(period, ledger_path):
    """扫描缺陷台账，统计缺陷流转。

    Returns:
        dict: {"total": N, "closed": N, "open": N, "reopened": N}
    """
    stats = {"total": 0, "closed": 0, "open": 0, "reopened": 0}

    if not os.path.exists(ledger_path):
        return stats

    try:
        with io.open(ledger_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 8:
                    stats["total"] += 1
                    status = row[7]  # 状态列
                    if "关闭" in status or "已修复" in status:
                        stats["closed"] += 1
                    elif "重新打开" in status:
                        stats["reopened"] += 1
                    else:
                        stats["open"] += 1
    except Exception:
        pass

    return stats


def review_metrics(period=None, output_path=None):
    """评审效能度量主入口。

    Args:
        period: 统计周期（YYYY-MM，None 则全量）
        output_path: 输出 CSV 路径

    Returns:
        dict: 效能指标摘要
    """
    reviews_dir = os.path.join(ROOT, "docs", "reviews")
    ledger_path = os.path.join(ROOT, "台账", "15_缺陷台账.csv")

    # 扫描评审报告
    review_stats = _scan_review_reports(period, reviews_dir)

    # 扫描缺陷台账
    defect_stats = _scan_defect_ledger(period, ledger_path)

    # 计算效能指标
    review_count = review_stats["review_count"]
    defect_count = review_stats["defect_count"]
    avg_defects = round(defect_count / review_count, 1) if review_count > 0 else 0

    # 修复率
    fix_rate = 0
    if defect_stats["total"] > 0:
        fix_rate = round(defect_stats["closed"] * 100.0 / defect_stats["total"], 1)

    # 构建结果
    results = []
    for rtype, count in sorted(review_stats["by_type"].items()):
        results.append({
            "review_type": rtype,
            "review_count": count,
            "defect_count": "-",
            "severe_count": "-",
            "avg_defects": "-",
            "fix_rate": "-",
        })

    # 汇总行
    results.append({
        "review_type": "合计",
        "review_count": review_count,
        "defect_count": defect_count,
        "severe_count": review_stats["severe_count"],
        "avg_defects": avg_defects,
        "fix_rate": "%s%%" % fix_rate,
    })

    # 缺陷台账摘要
    results.append({
        "review_type": "缺陷台账",
        "review_count": defect_stats["total"],
        "defect_count": "已关闭: %d" % defect_stats["closed"],
        "severe_count": "待处理: %d" % defect_stats["open"],
        "avg_defects": "重开: %d" % defect_stats["reopened"],
        "fix_rate": "%s%%" % fix_rate,
    })

    # 输出
    if not output_path:
        os.makedirs(os.path.join(ROOT, "docs", "reviews"), exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        output_path = os.path.join(ROOT, "docs", "reviews", "评审效能度量_%s.csv" % date_str)

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with io.open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "review_type", "review_count", "defect_count",
            "severe_count", "avg_defects", "fix_rate"
        ])
        writer.writeheader()
        writer.writerows(results)

    print("评审效能度量完成：")
    if period:
        print("  周期: %s" % period)
    print("  评审次数: %d" % review_count)
    print("  发现缺陷: %d（严重 %d）" % (defect_count, review_stats["severe_count"]))
    print("  平均缺陷/评审: %.1f" % avg_defects)
    print("  缺陷修复率: %.1f%%" % fix_rate)
    print("  输出: %s" % output_path)
    return {"review_count": review_count, "defect_count": defect_count, "fix_rate": fix_rate, "output_path": output_path}


def main():
    ap = argparse.ArgumentParser(description="T-13 评审效能度量器")
    ap.add_argument("--period", default=None, help="统计周期（YYYY-MM，默认全量）")
    ap.add_argument("--output", default=None, help="输出效能数据 CSV 路径")
    args = ap.parse_args()
    review_metrics(args.period, args.output)


if __name__ == "__main__":
    main()
