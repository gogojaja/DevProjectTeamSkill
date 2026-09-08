#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_resource_ops.py — 资源运营工具单测（resource-ops 独立部署 A-6）

轻量断言式：python tests/test_resource_ops.py（无第三方依赖）
覆盖：capacity 容量登记 / allocate 分配与利用率重算(过载>85/健康≥50/闲置<50)+未找到 /
      balance 过载 rc1 / skill 技能矩阵+格式错误 / singlespot 单点故障 rc1。
台账隔离：patch 模块级 LEDGER + CAP_FILE/SKILL_FILE 到 tempfile。
"""
import os
import sys
import csv
import io
import argparse
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import resource_ops as rs


def _patch(d):
    rs.LEDGER = d
    rs.CAP_FILE = os.path.join(d, "48_资源容量.csv")
    rs.SKILL_FILE = os.path.join(d, "49_技能矩阵.csv")


def _tmp():
    d = tempfile.mkdtemp()
    _patch(d)
    return d


def _rows(path):
    with io.open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _cap(name="张三", role="后端开发", available=160):
    return rs.cmd_capacity(argparse.Namespace(name=name, role=role, available=available))


def _alloc(name="张三", project="项目A", hours=80):
    return rs.cmd_allocate(argparse.Namespace(name=name, project=project, hours=hours))


def test_capacity():
    d = _tmp()
    assert _cap() == 0
    row = _rows(rs.CAP_FILE)[-1]
    assert row["编号"] == "RC-001" and row["成员"] == "张三"
    assert row["可用工时"] == "160" and row["已分配"] == "0" and row["利用率%"] == "0"


def test_allocate_overload():
    """可用160 分配140 → 利用率87.5% → 过载。"""
    d = _tmp()
    _cap(available=160)
    assert _alloc(hours=140) == 0
    row = _rows(rs.CAP_FILE)[-1]
    assert row["已分配"] == "140" and row["利用率%"] == "87.5"
    assert "项目A:140h" in row["项目分配"]


def test_allocate_healthy_and_idle():
    d = _tmp()
    _cap(name="李四", available=160)
    _alloc(name="李四", hours=80)   # 50.0% → 健康
    assert _rows(rs.CAP_FILE)[-1]["利用率%"] == "50.0"
    _cap(name="王五", available=160)
    _alloc(name="王五", hours=40)   # 25.0% → 闲置
    assert _rows(rs.CAP_FILE)[-1]["利用率%"] == "25.0"


def test_allocate_not_found():
    d = _tmp()
    _cap(name="张三")
    assert _alloc(name="不存在", hours=10) == 1


def test_balance_overload_rc1():
    """存在过载成员 → balance rc1；无过载 → rc0。"""
    d = _tmp()
    _cap(name="张三", available=160)
    _alloc(name="张三", hours=140)  # 过载
    assert rs.cmd_balance(argparse.Namespace()) == 1
    d2 = _tmp()
    _cap(name="李四", available=160)
    _alloc(name="李四", hours=80)   # 健康
    assert rs.cmd_balance(argparse.Namespace()) == 0


def test_skill_and_bad_format():
    d = _tmp()
    assert rs.cmd_skill(argparse.Namespace(name="张三", skills="Python:4,Java:3,SQL:3")) == 0
    row = _rows(rs.SKILL_FILE)[-1]
    assert row["编号"] == "SK-001" and row["成员"] == "张三"
    assert "Python" in row["技能清单"]
    assert rs.cmd_skill(argparse.Namespace(name="李四", skills="格式错误无冒号")) == 1


def test_singlespot_risk_and_ok():
    """仅1人掌握(熟练度≥3) → rc1；≥2人 → rc0；无记录 → rc0。"""
    d = _tmp()
    assert rs.cmd_singlespot(argparse.Namespace()) == 0  # 无记录
    d = _tmp()
    rs.cmd_skill(argparse.Namespace(name="张三", skills="Python:4"))
    assert rs.cmd_singlespot(argparse.Namespace()) == 1  # Python 仅张三 → 单点
    d = _tmp()
    rs.cmd_skill(argparse.Namespace(name="张三", skills="Python:4"))
    rs.cmd_skill(argparse.Namespace(name="李四", skills="Python:3"))
    assert rs.cmd_singlespot(argparse.Namespace()) == 0  # Python 2人 → 无单点


if __name__ == "__main__":
    test_capacity()
    test_allocate_overload()
    test_allocate_healthy_and_idle()
    test_allocate_not_found()
    test_balance_overload_rc1()
    test_skill_and_bad_format()
    test_singlespot_risk_and_ok()
    print("ALL TESTS PASSED")
