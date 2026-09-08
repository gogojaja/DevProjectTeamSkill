#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_evm_ops.py — EVM 挣值工具单测（schedule-cost 独立部署 B-3）

轻量断言式：python tests/test_evm_ops.py（无第三方依赖）
覆盖：add-milestone 登记 / 重复拒绝 / calc 指标(PV/EV/AC/CPI/SPI/CV/SV) /
      AC 台账实际成本优先 + 时间进度比回退 / 准点率 / BAC 均摊回退 / update-milestone /
      与 dev-project-mgmt evm_calculator 公式一致性（AC6：EV=Σ已完成计划值, CPI=EV/AC, SPI=EV/PV）。
台账隔离：patch 模块级 LEDGER + 03/04/09/10 文件全局到 tempfile，不污染真实台账。
"""
import os
import sys
import csv
import io
import argparse
import datetime
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import evm_ops as ev

TRACK_HEADER = ["里程碑编号", "里程碑名称", "计划开始", "计划日期", "计划值",
                "实际日期", "任务完成率", "状态", "更新日期"]


def _patch(d):
    """将模块级台账路径全局重定向到临时目录，实现测试隔离。"""
    ev.LEDGER = d
    ev.PROGRESS_BASE_FILE = os.path.join(d, "03_进度基准.csv")
    ev.COST_BASE_FILE = os.path.join(d, "04_成本基准.csv")
    ev.PROGRESS_TRACK_FILE = os.path.join(d, "09_进度跟踪台账.csv")
    ev.COST_CONSUME_FILE = os.path.join(d, "10_成本消耗台账.csv")


def _tmp():
    d = tempfile.mkdtemp()
    _patch(d)
    return d


def _rows(path):
    with io.open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _seed_09(d, rows):
    """播种 09_进度跟踪台账（规范表头）。rows: list[dict] 用规范列名。"""
    p = os.path.join(d, "09_进度跟踪台账.csv")
    with io.open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TRACK_HEADER, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in TRACK_HEADER})


def _seed_10(d, cumulative):
    """播种 10_成本消耗台账（累计消耗）。"""
    p = os.path.join(d, "10_成本消耗台账.csv")
    with io.open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["记录编号", "日期", "工时消耗", "资源成本", "工具成本", "累计消耗", "状态"])
        w.writerow(["C-001", "2026-09-30", "", "", "", str(cumulative), "已记录"])


def _seed_04(d, threshold):
    """播种 04_成本基准（成本阈值=BAC）。"""
    p = os.path.join(d, "04_成本基准.csv")
    with io.open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["成本编号", "人力工时预估", "成本阈值", "超支标准", "版本", "日期", "状态"])
        w.writerow(["CB-001", "", str(threshold), "10%", "v1.0", "2026-09-01", "已基线"])


def _add_args(mid, name, start="", end="", value=0.0):
    return argparse.Namespace(id=mid, name=name, start=start, end=end, value=value)


def test_add_milestone():
    """add-milestone 写入 09 规范表头，状态默认未开始。"""
    d = _tmp()
    assert ev.cmd_add_milestone(_add_args("M1", "需求基线", "2026-09-01", "2026-09-30", 1000)) == 0
    rows = _rows(ev.PROGRESS_TRACK_FILE)
    assert len(rows) == 1 and rows[0]["里程碑编号"] == "M1"
    assert rows[0]["计划值"] == "1000" and rows[0]["状态"] == "未开始"
    assert rows[0]["计划日期"] == "2026-09-30"


def test_add_milestone_dup_rejected():
    """重复 ID 拒绝（rc1），不重复写入。"""
    d = _tmp()
    ev.cmd_add_milestone(_add_args("M1", "需求基线", value=1000))
    assert ev.cmd_add_milestone(_add_args("M1", "需求基线副本", value=500)) == 1
    assert len(_rows(ev.PROGRESS_TRACK_FILE)) == 1


def test_calc_evm_indicators():
    """PV=2000 EV=1000(M1已完成,0/100) AC=1600(台账) → CPI=0.625 SPI=0.5 CV=-600 SV=-1000。"""
    d = _tmp()
    _seed_09(d, [
        {"里程碑编号": "M1", "里程碑名称": "需求基线", "计划开始": "2026-09-01", "计划日期": "2026-09-30",
         "计划值": "1000", "实际日期": "2026-09-28", "任务完成率": "100", "状态": "已完成"},
        {"里程碑编号": "M2", "里程碑名称": "架构基线", "计划开始": "2026-10-01", "计划日期": "2026-10-31",
         "计划值": "1000", "实际日期": "", "任务完成率": "50", "状态": "进行中"},
    ])
    _seed_10(d, 1600)
    ms = ev._load_milestones()
    r = ev._compute_evm(ms, datetime.date(2026, 9, 30))
    assert r["pv"] == 2000.0 and r["ev"] == 1000.0 and r["ac"] == 1600.0
    assert r["cpi"] == 0.625 and r["spi"] == 0.5
    assert r["cv"] == -600.0 and r["sv"] == -1000.0
    assert r["ac_source"] == "台账10_成本消耗"


def test_calc_ac_time_estimate_fallback():
    """无 10 台账时 AC 回退时间进度比：start=09-01 end=10-01 today=09-16 → ratio 0.5 → AC=500。"""
    d = _tmp()
    _seed_09(d, [
        {"里程碑编号": "M1", "里程碑名称": "开发", "计划开始": "2026-09-01", "计划日期": "2026-10-01",
         "计划值": "1000", "任务完成率": "50", "状态": "进行中"},
    ])
    ms = ev._load_milestones()
    r = ev._compute_evm(ms, datetime.date(2026, 9, 16))
    assert r["ac"] == 500.0 and r["ac_source"] == "时间进度比估算"
    assert r["ev"] == 0.0  # 未完成里程碑 EV=0（0/100 规则）


def test_on_time_rate():
    """准点率：M1准点 M2延期 M3未完成 → 1/3 = 0.3333。"""
    d = _tmp()
    _seed_09(d, [
        {"里程碑编号": "M1", "计划日期": "2026-09-30", "实际日期": "2026-09-28", "计划值": "100", "状态": "已完成"},
        {"里程碑编号": "M2", "计划日期": "2026-09-30", "实际日期": "2026-10-05", "计划值": "100", "状态": "已完成"},
        {"里程碑编号": "M3", "计划日期": "2026-10-31", "实际日期": "", "计划值": "100", "状态": "进行中"},
    ])
    ms = ev._load_milestones()
    r = ev._compute_evm(ms, datetime.date(2026, 10, 10))
    assert r["on_time_rate"] == 0.3333 and r["milestone_count"] == 3


def test_bac_fallback():
    """无计划值时按 04 成本阈值(BAC=2000)均摊 2 里程碑 → 各 PV=1000。"""
    d = _tmp()
    _seed_09(d, [
        {"里程碑编号": "M1", "计划日期": "2026-09-30", "状态": "已完成"},
        {"里程碑编号": "M2", "计划日期": "2026-10-31", "状态": "未开始"},
    ])
    _seed_04(d, 2000)
    ms = ev._load_milestones()
    assert all(m["pv"] == 1000.0 for m in ms)
    r = ev._compute_evm(ms, datetime.date(2026, 9, 30))
    assert r["pv"] == 2000.0 and r["ev"] == 1000.0  # M1 已完成


def test_consistency_with_dev_project_mgmt():
    """AC6 一致性：EV=Σ已完成计划值(0/100) + CPI=EV/AC + SPI=EV/PV，公式与 dev-project-mgmt 一致。"""
    d = _tmp()
    _seed_09(d, [
        {"里程碑编号": "M1", "计划日期": "2026-09-30", "实际日期": "2026-09-30", "计划值": "500", "状态": "已完成"},
        {"里程碑编号": "M2", "计划日期": "2026-09-30", "实际日期": "2026-09-29", "计划值": "300", "状态": "已完成"},
        {"里程碑编号": "M3", "计划日期": "2026-10-31", "实际日期": "", "计划值": "200", "状态": "进行中"},
    ])
    _seed_10(d, 800)
    ms = ev._load_milestones()
    r = ev._compute_evm(ms, datetime.date(2026, 9, 30))
    # dev-project-mgmt: EV = Σ planned_value of 已完成 = 500+300 = 800
    assert r["ev"] == 800.0
    assert r["pv"] == 1000.0 and r["ac"] == 800.0
    # 公式一致性：CPI=EV/AC, SPI=EV/PV
    assert r["cpi"] == round(800.0 / 800.0, 4) == 1.0
    assert r["spi"] == round(800.0 / 1000.0, 4) == 0.8
    assert r["cv"] == 0.0 and r["sv"] == -200.0
    assert r["on_time_rate"] == round(2 / 3, 4)  # M1准点(=) M2准点(<) 均准点


def test_update_milestone():
    """update-milestone 置已完成，自动补实际完成日。"""
    d = _tmp()
    ev.cmd_add_milestone(_add_args("M1", "需求基线", "2026-09-01", "2026-09-30", 1000))
    assert ev.cmd_update_milestone(argparse.Namespace(
        id="M1", status="已完成", actual_end="", completion=100)) == 0
    row = _rows(ev.PROGRESS_TRACK_FILE)[0]
    assert row["状态"] == "已完成" and row["任务完成率"] == "100"
    assert row["实际日期"] != ""  # 自动补今天


def test_update_milestone_not_found():
    """更新不存在里程碑 → rc1。"""
    d = _tmp()
    ev.cmd_add_milestone(_add_args("M1", "需求基线", value=1000))
    assert ev.cmd_update_milestone(argparse.Namespace(
        id="M9", status="已完成", actual_end="", completion=None)) == 1


def test_calc_empty_rc0():
    """无里程碑数据时 calc 仍 rc0（友好提示）。"""
    d = _tmp()
    assert ev.cmd_calc(argparse.Namespace(milestone="", json=False)) == 0


def test_calc_json_and_status():
    """calc --json 输出结构化；status rc0。"""
    d = _tmp()
    ev.cmd_add_milestone(_add_args("M1", "需求基线", "2026-09-01", "2026-09-30", 1000))
    ev.cmd_update_milestone(argparse.Namespace(id="M1", status="已完成", actual_end="2026-09-28", completion=100))
    _seed_10(d, 900)
    assert ev.cmd_calc(argparse.Namespace(milestone="", json=True)) == 0
    assert ev.cmd_status(argparse.Namespace()) == 0


if __name__ == "__main__":
    test_add_milestone()
    test_add_milestone_dup_rejected()
    test_calc_evm_indicators()
    test_calc_ac_time_estimate_fallback()
    test_on_time_rate()
    test_bac_fallback()
    test_consistency_with_dev_project_mgmt()
    test_update_milestone()
    test_update_milestone_not_found()
    test_calc_empty_rc0()
    test_calc_json_and_status()
    print("ALL TESTS PASSED")
