#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pmo_dashboard.py -- PMO 综合运营仪表盘聚合器 (E2)

对齐 PMI PMO Practice + 治理三层模型

CLI:
  python3 tools/pmo_dashboard.py
"""
import os, sys, io, csv, glob, datetime

# Windows GBK 兼容：强制 UTF-8 输出
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, "台账")
SNAPSHOT_FILE = os.path.join(LEDGER, "54_PMO运营仪表盘.csv")

# 预警阈值
THRESHOLDS = {
    "spi_red": 0.80,
    "cpi_red": 0.85,
    "resource_overload": 85,
    "p1_risk_critical": 3,
}


def _read_csv(path):
    if not os.path.isfile(path):
        return []
    with io.open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _ensure_dir():
    os.makedirs(LEDGER, exist_ok=True)


def _aggregate_progress():
    """聚合进度健康度（SPI）"""
    rows = _read_csv(os.path.join(LEDGER, "30_项目群主进度.csv"))
    if not rows:
        return {"count": 0, "avg_spi": 0, "red_count": 0, "projects": []}
    spis = []
    projects = []
    for r in rows:
        spi_str = r.get("SPI", "")
        try:
            spi = float(spi_str)
            spis.append(spi)
            projects.append({"id": r.get("编号", "?"), "name": r.get("名称", r.get("项目群", "?")), "spi": spi})
        except (ValueError, TypeError):
            pass
    if not spis:
        return {"count": 0, "avg_spi": 0, "red_count": 0, "projects": []}
    avg_spi = sum(spis) / len(spis)
    red_count = sum(1 for s in spis if s < THRESHOLDS["spi_red"])
    return {"count": len(spis), "avg_spi": avg_spi, "red_count": red_count, "projects": projects}


def _aggregate_risks():
    """聚合风险态势（P1/P2）"""
    rows = _read_csv(os.path.join(LEDGER, "12_风险问题台账.csv"))
    if not rows:
        return {"total_p1": 0, "total_p2": 0, "projects": {}}
    p1_count = 0
    p2_count = 0
    project_risks = {}
    for r in rows:
        rtype = r.get("类型", "")
        if rtype != "风险":
            continue
        priority = r.get("优先级", r.get("严重度", ""))
        project = r.get("归属项目", r.get("项目", "未分配"))
        if priority == "P1":
            p1_count += 1
            project_risks.setdefault(project, {"p1": 0, "p2": 0})
            project_risks[project]["p1"] += 1
        elif priority == "P2":
            p2_count += 1
            project_risks.setdefault(project, {"p1": 0, "p2": 0})
            project_risks[project]["p2"] += 1
    return {"total_p1": p1_count, "total_p2": p2_count, "projects": project_risks}


def _aggregate_resources():
    """聚合资源负载"""
    rows = _read_csv(os.path.join(LEDGER, "48_资源容量.csv"))
    if not rows:
        return {"count": 0, "avg_util": 0, "overloaded": 0, "idle": 0}
    utils = []
    overloaded = 0
    idle = 0
    for r in rows:
        try:
            avail = float(r.get("可用工时", 0))
            assigned = float(r.get("已分配工时", 0))
            if avail > 0:
                util = (assigned / avail) * 100
                utils.append(util)
                if util > THRESHOLDS["resource_overload"]:
                    overloaded += 1
                elif util < 50:
                    idle += 1
        except (ValueError, TypeError):
            pass
    if not utils:
        return {"count": 0, "avg_util": 0, "overloaded": 0, "idle": 0}
    return {"count": len(utils), "avg_util": sum(utils) / len(utils),
            "overloaded": overloaded, "idle": idle}


def _aggregate_portfolio():
    """聚合组合状态"""
    rows = _read_csv(os.path.join(LEDGER, "43_组合注册.csv"))
    if not rows:
        return {"total": 0, "categories": {}}
    categories = {}
    for r in rows:
        cat = r.get("投资类别", "未分类")
        categories[cat] = categories.get(cat, 0) + 1
    return {"total": len(rows), "categories": categories}


def _aggregate_alignment():
    """聚合战略对齐"""
    rows = _read_csv(os.path.join(LEDGER, "47_战略对齐矩阵.csv"))
    if not rows:
        return {"mapped": 0, "orphan": 0}
    mapped = 0
    projects = {}
    for r in rows:
        proj = r.get("项目", "")
        score_str = r.get("对齐度评分", "0")
        try:
            score = int(score_str)
        except (ValueError, TypeError):
            score = 0
        projects[proj] = max(projects.get(proj, 0), score)
        if score >= 3:
            mapped += 1
    orphan = sum(1 for s in projects.values() if s < 3)
    return {"mapped": mapped, "orphan": orphan}


def _generate_alerts(progress, risks, resources, alignment):
    """生成预警清单"""
    alerts = []
    # SPI 预警
    for p in progress.get("projects", []):
        if p["spi"] < THRESHOLDS["spi_red"]:
            alerts.append(("🔴 红色", f"进度严重滞后", f"{p['name']} SPI={p['spi']:.2f} < {THRESHOLDS['spi_red']}"))
    # P1 风险集中
    for proj, counts in risks.get("projects", {}).items():
        if counts["p1"] > THRESHOLDS["p1_risk_critical"]:
            alerts.append(("🔴 红色", f"P1 风险集中", f"{proj} P1风险={counts['p1']}项 > {THRESHOLDS['p1_risk_critical']}"))
    # 资源过载
    if resources.get("overloaded", 0) > 0:
        alerts.append(("🟡 黄色", f"资源过载", f"{resources['overloaded']}人利用率>{THRESHOLDS['resource_overload']}%"))
    # 孤儿项目
    if alignment.get("orphan", 0) > 0:
        alerts.append(("🟡 黄色", f"战略脱对齐", f"{alignment['orphan']}个孤儿项目"))
    return alerts


def _write_snapshot(alerts, progress, risks, resources):
    """写入仪表盘快照"""
    _ensure_dir()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    header = ["时间戳", "指标类别", "指标名", "值", "状态", "预警"]
    rows_data = [
        (now, "进度", "平均SPI", f"{progress['avg_spi']:.2f}", "正常" if progress["avg_spi"] >= 1.0 else "偏差", ""),
        (now, "进度", "SPI<0.8项目数", str(progress["red_count"]), "预警" if progress["red_count"] > 0 else "正常", ""),
        (now, "风险", "P1风险总数", str(risks["total_p1"]), "预警" if risks["total_p1"] > 0 else "正常", ""),
        (now, "风险", "P2风险总数", str(risks["total_p2"]), "关注" if risks["total_p2"] > 3 else "正常", ""),
        (now, "资源", "平均利用率", f"{resources['avg_util']:.1f}%", "过载" if resources["avg_util"] > 85 else "正常", ""),
        (now, "资源", "过载人数", str(resources["overloaded"]), "预警" if resources["overloaded"] > 0 else "正常", ""),
    ]
    # 追加预警
    for level, category, detail in alerts:
        rows_data.append((now, "预警", category, detail, level, level))

    file_exists = os.path.isfile(SNAPSHOT_FILE) and os.path.getsize(SNAPSHOT_FILE) > 0
    with io.open(SNAPSHOT_FILE, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(header)
        for row in rows_data:
            w.writerow(row)


def cmd_dashboard(args):
    """PMO 综合仪表盘"""
    progress = _aggregate_progress()
    risks = _aggregate_risks()
    resources = _aggregate_resources()
    portfolio = _aggregate_portfolio()
    alignment = _aggregate_alignment()
    alerts = _generate_alerts(progress, risks, resources, alignment)

    print("=" * 60)
    print("  PMO 综合运营仪表盘")
    print(f"  生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 进度健康度
    print(f"\n【进度健康度】")
    print(f"  里程碑记录: {progress['count']}")
    if progress["count"] > 0:
        spi_status = "✅ 健康" if progress["avg_spi"] >= 1.0 else ("⚠️ 偏差" if progress["avg_spi"] >= THRESHOLDS["spi_red"] else "❗ 严重滞后")
        print(f"  平均 SPI: {progress['avg_spi']:.2f} {spi_status}")
        if progress["red_count"] > 0:
            print(f"  SPI<0.8 项目: {progress['red_count']}个 🔴")

    # 风险态势
    print(f"\n【风险态势】")
    print(f"  P1 风险: {risks['total_p1']}项")
    print(f"  P2 风险: {risks['total_p2']}项")
    if risks["projects"]:
        for proj, counts in risks["projects"].items():
            flag = " 🔴" if counts["p1"] > THRESHOLDS["p1_risk_critical"] else ""
            print(f"    {proj}: P1={counts['p1']} P2={counts['p2']}{flag}")

    # 资源负载
    print(f"\n【资源负载】")
    if resources["count"] > 0:
        util_status = "🔴 过载" if resources["avg_util"] > 85 else ("✅ 健康" if resources["avg_util"] >= 50 else "⚠️ 闲置")
        print(f"  平均利用率: {resources['avg_util']:.1f}% {util_status}")
        print(f"  过载(>85%): {resources['overloaded']}人")
        print(f"  闲置(<50%): {resources['idle']}人")
    else:
        print("  无资源容量数据")

    # 组合状态
    print(f"\n【组合状态】")
    print(f"  注册项目: {portfolio['total']}")
    if portfolio["categories"]:
        for cat, count in portfolio["categories"].items():
            print(f"    {cat}: {count}个")

    # 战略对齐
    print(f"\n【战略对齐】")
    print(f"  已对齐项目: {alignment['mapped']}")
    if alignment["orphan"] > 0:
        print(f"  孤儿项目: {alignment['orphan']}个 🟡")

    # 预警清单
    if alerts:
        print(f"\n{'=' * 60}")
        print(f"【预警清单】{len(alerts)}项")
        for level, category, detail in alerts:
            print(f"  {level} [{category}] {detail}")
    else:
        print(f"\n✅ 无预警项")

    # 写入快照
    _write_snapshot(alerts, progress, risks, resources)
    print(f"\n仪表盘快照已写入: 54_PMO运营仪表盘.csv")
    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser(description="PMO Dashboard Aggregator (E2)")
    ap.add_argument("command", nargs="?", default="dashboard", help="命令（默认 dashboard）")
    args = ap.parse_args()
    sys.exit(cmd_dashboard(args))


if __name__ == "__main__":
    main()
