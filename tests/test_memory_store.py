#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory_store.py 增强功能单测"""
import os
import sys
import io
import json
import tempfile
import shutil

# 确保可导入
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

# 使用临时目录
TMP_DIR = tempfile.mkdtemp()
os.environ["PROJECT_ROOT"] = TMP_DIR
os.makedirs(os.path.join(TMP_DIR, "台账"), exist_ok=True)

# 导入模块
import memory_store

# 覆盖路径
memory_store.STORE = os.path.join(TMP_DIR, "台账", "test_memory.jsonl")


def reset_store():
    """重置测试存储"""
    if os.path.exists(memory_store.STORE):
        os.remove(memory_store.STORE)


def test_add_and_list():
    """测试添加和列表"""
    reset_store()
    memory_store.add("decision", "测试决策 A", "TEST-001")
    memory_store.add("todo", "测试待办 B", "TEST-002")
    rows = memory_store._read_all()
    assert len(rows) == 2, "应有 2 条记录"
    assert rows[0]["type"] == "decision"
    assert rows[1]["type"] == "todo"
    print("PASS test_add_and_list")


def test_query_by_keyword():
    """测试关键词查询"""
    reset_store()
    memory_store.add("decision", "Agent 运行时方案", "PLAN-001")
    memory_store.add("todo", "完成 Phase B 实现", "PLAN-001")
    memory_store.add("risk", "GitHub 访问不稳定", "INFRA-001")
    # 查询 "Agent"
    rows = memory_store._read_all()
    matches = [r for r in rows if "agent" in r.get("text", "").lower()]
    assert len(matches) == 1, "应匹配 1 条"
    assert matches[0]["type"] == "decision"
    print("PASS test_query_by_keyword")


def test_query_by_type():
    """测试按类型查询"""
    reset_store()
    memory_store.add("decision", "决策 1")
    memory_store.add("todo", "待办 1")
    memory_store.add("todo", "待办 2")
    rows = memory_store._read_all()
    todos = [r for r in rows if r.get("type") == "todo"]
    assert len(todos) == 2, "应有 2 条 todo"
    print("PASS test_query_by_type")


def test_expire():
    """测试过期标记"""
    reset_store()
    # 添加一条旧记录（手动写入旧时间戳）
    old_rec = {
        "ts": "2020-01-01 10:00:00",
        "type": "decision",
        "text": "旧决策",
        "meta": "OLD-001",
        "status": "active"
    }
    with io.open(memory_store.STORE, "a", encoding="utf-8") as f:
        f.write(json.dumps(old_rec, ensure_ascii=False) + "\n")
    # 添加一条新记录
    memory_store.add("decision", "新决策")
    # 过期 >30 天的记录
    memory_store.expire(days=30)
    rows = memory_store._read_all()
    expired = [r for r in rows if r.get("status") == "expired"]
    active = [r for r in rows if r.get("status", "active") != "expired"]
    assert len(expired) == 1, "应有 1 条过期"
    assert len(active) == 1, "应有 1 条活跃"
    print("PASS test_expire")


def test_get_active():
    """测试获取活跃条目"""
    reset_store()
    memory_store.add("decision", "活跃决策")
    # 手动添加一条已过期记录
    expired_rec = {
        "ts": "2026-09-01 10:00:00",
        "type": "todo",
        "text": "已过期待办",
        "status": "expired"
    }
    with io.open(memory_store.STORE, "a", encoding="utf-8") as f:
        f.write(json.dumps(expired_rec, ensure_ascii=False) + "\n")
    active = memory_store.get_active()
    assert len(active) == 1, "应只有 1 条活跃"
    assert active[0]["text"] == "活跃决策"
    print("PASS test_get_active")


def test_delete():
    """测试删除"""
    reset_store()
    memory_store.add("decision", "要删除的决策")
    memory_store.add("todo", "保留的待办")
    memory_store.delete(0)  # 删除第一条
    rows = memory_store._read_all()
    assert len(rows) == 1, "应剩 1 条"
    assert rows[0]["text"] == "保留的待办"
    print("PASS test_delete")


def test_summarize():
    """测试摘要"""
    reset_store()
    memory_store.add("decision", "决策 A")
    memory_store.add("todo", "待办 A")
    memory_store.add("risk", "风险 A")
    # 验证不抛异常
    memory_store.summarize()
    print("PASS test_summarize")


def test_export_csv():
    """测试 CSV 导出"""
    reset_store()
    memory_store.add("decision", "测试导出", "EXP-001")
    memory_store.CSV_OUT = os.path.join(TMP_DIR, "台账", "test_export.csv")
    memory_store.export_csv()
    assert os.path.exists(memory_store.CSV_OUT), "CSV 应存在"
    with io.open(memory_store.CSV_OUT, "r", encoding="utf-8-sig") as f:
        content = f.read()
    assert "测试导出" in content, "CSV 应含内容"
    print("PASS test_export_csv")


# ─── 运行全部测试 ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        test_add_and_list()
        test_query_by_keyword()
        test_query_by_type()
        test_expire()
        test_get_active()
        test_delete()
        test_summarize()
        test_export_csv()
        print("\nALL MEMORY STORE TESTS PASSED")
    finally:
        # 清理临时目录
        shutil.rmtree(TMP_DIR, ignore_errors=True)
