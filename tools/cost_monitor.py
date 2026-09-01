#!/usr/bin/env python3
"""
成本监控脚本（cost_monitor）：读取 40_大模型成本台账，按月/周聚合费用，超阈值告警。

用法：
  python3 tools/cost_monitor.py                          # 默认：按月聚合，阈值 $10
  python3 tools/cost_monitor.py --period week            # 按周聚合
  python3 tools/cost_monitor.py --threshold 5.0          # 告警阈值 $5
  python3 tools/cost_monitor.py --output report.csv      # 输出到指定文件
  python3 tools/cost_monitor.py --dry-run                # 仅探测，不写文件

输出：
  - 控制台：聚合统计 + 告警信息
  - CSV 文件：周期/费用/任务数/告警状态
"""

import csv
import os
import sys
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# 项目根目录
PROJECT_ROOT = os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent)
LEDGER_PATH = PROJECT_ROOT / "台账" / "40_大模型成本台账.csv"


def parse_date(date_str):
    """解析日期字符串（支持 '2026-08-27 14:07' 或 '2026-08-27'）"""
    try:
        return datetime.strptime(date_str.strip().split()[0], "%Y-%m-%d")
    except (ValueError, AttributeError):
        return None


def get_period_key(date, period):
    """获取周期键（周/月）"""
    if period == "week":
        # ISO 周：2026-W34
        return f"{date.isocalendar()[0]}-W{date.isocalendar()[1]:02d}"
    else:  # month
        return f"{date.year}-{date.month:02d}"


def load_ledger(ledger_path):
    """加载成本台账"""
    if not ledger_path.exists():
        print(f"❌ 台账不存在：{ledger_path}")
        sys.exit(1)

    records = []
    with open(ledger_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = parse_date(row.get("日期", ""))
            if not date:
                continue

            # 优先使用实际费用，否则用估算费用
            actual_cost = row.get("实际费用$", "").strip()
            estimated_cost = row.get("估算费用$", "0").strip()

            try:
                cost = float(actual_cost) if actual_cost else float(estimated_cost)
            except ValueError:
                cost = 0.0

            records.append({
                "date": date,
                "task": row.get("任务", ""),
                "model": row.get("模型", ""),
                "tier": row.get("档位(S0-S3)", ""),
                "cost": cost,
            })

    return records


def aggregate_by_period(records, period):
    """按周期聚合"""
    aggregated = defaultdict(lambda: {"cost": 0.0, "count": 0, "tasks": set()})

    for rec in records:
        key = get_period_key(rec["date"], period)
        aggregated[key]["cost"] += rec["cost"]
        aggregated[key]["count"] += 1
        aggregated[key]["tasks"].add(rec["task"])

    # 转换为列表并排序
    result = []
    for key, data in sorted(aggregated.items()):
        result.append({
            "period": key,
            "cost": data["cost"],
            "count": data["count"],
            "task_count": len(data["tasks"]),
        })

    return result


def check_alerts(aggregated, threshold):
    """检查告警"""
    alerts = []
    for item in aggregated:
        if item["cost"] > threshold:
            alerts.append({
                "period": item["period"],
                "cost": item["cost"],
                "threshold": threshold,
                "excess": item["cost"] - threshold,
            })
    return alerts


def write_report(aggregated, alerts, output_path, dry_run):
    """写入报告"""
    if dry_run:
        print(f"[dry-run] 将写入：{output_path}")
        return

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["period", "cost", "count", "task_count", "alert"])
        writer.writeheader()

        alert_periods = {a["period"] for a in alerts}
        for item in aggregated:
            writer.writerow({
                "period": item["period"],
                "cost": f"{item['cost']:.4f}",
                "count": item["count"],
                "task_count": item["task_count"],
                "alert": "⚠️ 超阈值" if item["period"] in alert_periods else "✅ 正常",
            })


def print_summary(aggregated, alerts, period):
    """打印汇总"""
    print(f"\n{'='*60}")
    print(f"成本监控报告（按{period}聚合）")
    print(f"{'='*60}")

    if not aggregated:
        print("无数据")
        return

    total_cost = sum(item["cost"] for item in aggregated)
    total_tasks = sum(item["count"] for item in aggregated)

    print(f"\n📊 总览：")
    print(f"  - 总费用：${total_cost:.4f}（≈¥{total_cost*7.2:.2f}）")
    print(f"  - 总任务数：{total_tasks}")
    print(f"  - 周期数：{len(aggregated)}")

    print(f"\n📈 各周期明细：")
    for item in aggregated:
        alert_mark = " ⚠️" if any(a["period"] == item["period"] for a in alerts) else ""
        print(f"  {item['period']}: ${item['cost']:.4f}（{item['count']} 任务，{item['task_count']} 独立任务）{alert_mark}")

    if alerts:
        print(f"\n⚠️ 告警（超阈值）：")
        for alert in alerts:
            print(f"  - {alert['period']}: ${alert['cost']:.4f}（超 ${alert['excess']:.4f}，阈值 ${alert['threshold']:.2f}）")
    else:
        print(f"\n✅ 无告警（所有周期均在阈值内）")

    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="成本监控脚本：读取台账，聚合费用，超阈值告警")
    parser.add_argument("--period", choices=["week", "month"], default="month", help="聚合周期（默认：month）")
    parser.add_argument("--threshold", type=float, default=10.0, help="告警阈值（美元，默认：$10）")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径（默认：台账/cost_monitor_report.csv）")
    parser.add_argument("--dry-run", action="store_true", help="仅探测，不写文件")

    args = parser.parse_args()

    # 加载台账
    print(f"📖 加载台账：{LEDGER_PATH}")
    records = load_ledger(LEDGER_PATH)
    print(f"  - 记录数：{len(records)}")

    if not records:
        print("❌ 台账无有效记录")
        sys.exit(1)

    # 聚合
    aggregated = aggregate_by_period(records, args.period)

    # 告警检查
    alerts = check_alerts(aggregated, args.threshold)

    # 打印汇总
    print_summary(aggregated, alerts, args.period)

    # 写入报告
    output_path = args.output or (PROJECT_ROOT / "台账" / "cost_monitor_report.csv")
    write_report(aggregated, alerts, output_path, args.dry_run)

    if not args.dry_run:
        print(f"✅ 报告已写入：{output_path}")

    # 退出码：有告警返回 1
    sys.exit(1 if alerts else 0)


if __name__ == "__main__":
    main()
