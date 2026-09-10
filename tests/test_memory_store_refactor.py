#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_store.py 重构等价性回归测试
==================================
背景：main() 嵌套深度 8（8 段 elif 子命令分发链），拆为 _build_parser()（解析器构造）
      + _dispatch()（字典派发）+ main()（三行编排）。

验证方式：
  1) 差分等价：在两个独立沙箱中对 HEAD 版本与重构版本执行**完全相同的 CLI 命令序列**，
     逐条比对 stdout/stderr/退出码，并比对最终 jsonl 存储与导出 CSV 的内容。
  2) 行为契约：不依赖 HEAD 的长期断言（子命令覆盖、帮助回退、类型校验）。

归一化说明：条目时间戳取自 datetime.now()，导出路径含沙箱绝对路径，
            二者均须归一化后比对，否则产生与重构无关的伪差异。
"""
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
REL_SCRIPT = "tools/memory_store.py"
SCRIPT_NAME = "memory_store.py"   # 两版本统一文件名，规避 argparse prog 名差异

_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _head_source():
    r = subprocess.run(["git", "show", "HEAD:" + REL_SCRIPT], cwd=str(REPO),
                       capture_output=True)
    if r.returncode != 0:
        pytest.skip("无法从 git HEAD 取基线版本：%s" % r.stderr.decode("utf-8", "replace"))
    return r.stdout.decode("utf-8")


def _work_source():
    return (REPO / REL_SCRIPT).read_text(encoding="utf-8")


def _norm(text, root):
    """归一化时间戳、日期与沙箱绝对路径。"""
    text = text.replace(str(root), "<ROOT>").replace(root.replace("\\", "/"), "<ROOT>")
    text = _TS_RE.sub("<TS>", text)
    return _DATE_RE.sub("<DATE>", text)


def _setup(base: Path, src: str):
    """构造沙箱：base/script/memory_store.py + base/root/台账/"""
    if base.exists():
        shutil.rmtree(str(base), ignore_errors=True)
    script_dir = base / "script"
    root = base / "root"
    (root / "台账").mkdir(parents=True)
    script_dir.mkdir(parents=True)
    script = script_dir / SCRIPT_NAME
    script.write_text(src, encoding="utf-8")
    return script, root


def _exec(script: Path, root: Path, cli):
    env = dict(os.environ)
    env["PROJECT_ROOT"] = str(root)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, str(script), *cli], cwd=str(root),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return r.returncode, r.stdout, r.stderr


def _store_lines(root: Path):
    """读取 jsonl 存储并归一化（保留记录顺序与字段集合）。"""
    p = root / "台账" / "38_项目记忆.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln:
            out.append(_norm(ln, str(root)))
    return out


def _csv_rows(root: Path):
    p = root / "台账" / "38_项目记忆.csv"
    if not p.exists():
        return None
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    return bom, [[_norm(c, str(root)) for c in row] for row in rows]


def _run_sequence(tmp_path, seq):
    """对 HEAD 与重构版本执行同一命令序列，返回可比对的归一化结果。"""
    results = {}
    for tag, src in (("head", _head_source()), ("work", _work_source())):
        base = tmp_path / tag
        script, root = _setup(base, src)
        steps = []
        for cli in seq:
            rc, out, err = _exec(script, root, cli)
            steps.append((rc, _norm(out, str(root)), _norm(err, str(root))))
        results[tag] = dict(steps=steps, store=_store_lines(root), csv=_csv_rows(root))
    return results["head"], results["work"]


# ---------------------------------------------------------------- 命令序列

_ADD_SEED = [
    ["add", "--type", "decision", "--text", "采用双机架构", "--meta", "ADR-001"],
    ["add", "--type", "todo", "--text", "补充扫描规则"],
    ["add", "--type", "risk", "--text", "Mac mini 链路断裂", "--meta", "R-01"],
    ["add", "--type", "context", "--text", "评审脚本位于 scripts/"],
    ["add", "--type", "note", "--text", "备注一条"],
]

SEQUENCES = {
    # 空存储下的各类读取路径
    "empty_reads": [
        ["list"], ["query", "--keyword", "x"], ["summarize"], ["load"],
    ],
    # 无子命令 → print_help
    "no_subcommand": [[], ["--help"]],
    # 类型校验失败（sys.exit(2)）
    "invalid_type": [
        ["add", "--type", "bogus", "--text", "x"],
        ["list"],
    ],
    # 必填参数缺失 → argparse 退出码 2
    "missing_required": [
        ["add", "--type", "todo"],
        ["delete"],
    ],
    # 完整读取矩阵
    "read_matrix": _ADD_SEED + [
        ["list"],
        ["list", "--type", "decision"],
        ["list", "--type", "todo", "--limit", "1"],
        ["list", "--limit", "2"],
        ["query", "--keyword", "评审"],
        ["query", "--keyword", "ADR-001"],
        ["query", "--type", "risk"],
        ["query", "--keyword", "架构", "--type", "decision"],
        ["query", "--since", "2000-01-01"],
        ["query", "--since", "2099-01-01"],
        ["query", "--since", "bad-date"],
        ["query", "--keyword", "不存在的关键字"],
        ["summarize"],
        ["load"],
        ["load", "--limit", "2"],
    ],
    # 过期标记 → 影响 query/summarize/load 的过滤
    "expire_flow": _ADD_SEED + [
        ["expire", "--days", "0"],
        ["summarize"],
        ["query", "--keyword", "架构"],
        ["load"],
        ["list"],
        ["expire", "--days", "90"],
        ["summarize"],
    ],
    # 删除（含越界）→ 影响后续序号语义
    "delete_flow": _ADD_SEED + [
        ["delete", "--index", "0"],
        ["list"],
        ["delete", "--index", "0"],
        ["delete", "--index", "99"],
        ["delete", "--index", "-1"],
        ["summarize"],
        ["load"],
    ],
    # 导出 CSV（含 BOM 与状态列）
    "export_flow": _ADD_SEED + [
        ["expire", "--days", "0"],
        ["add", "--type", "note", "--text", "过期后新增"],
        ["export"],
        ["summarize"],
    ],
    # 空存储导出
    "export_empty": [["export"]],
}


@pytest.mark.parametrize("label", sorted(SEQUENCES), ids=sorted(SEQUENCES))
def test_cli_sequence_matches_head(tmp_path, label):
    """同一命令序列下，stdout/stderr/退出码与最终存储产物须完全一致。"""
    h, w = _run_sequence(tmp_path, SEQUENCES[label])

    assert len(h["steps"]) == len(w["steps"])
    for i, ((h_rc, h_out, h_err), (w_rc, w_out, w_err)) in enumerate(
            zip(h["steps"], w["steps"])):
        cli = SEQUENCES[label][i]
        assert h_rc == w_rc, "[%s] 第%d步 %s 退出码 head=%s work=%s" % (
            label, i, cli, h_rc, w_rc)
        assert h_out == w_out, "[%s] 第%d步 %s stdout 不一致:\nhead=%s\nwork=%s" % (
            label, i, cli, h_out, w_out)
        assert h_err == w_err, "[%s] 第%d步 %s stderr 不一致:\nhead=%s\nwork=%s" % (
            label, i, cli, h_err, w_err)

    assert h["store"] == w["store"], "[%s] jsonl 存储不一致" % label
    assert h["csv"] == w["csv"], "[%s] 导出 CSV 不一致" % label


# ---------------------------------------------------------------- 行为契约

class TestContract:
    """不依赖 HEAD 的长期契约断言（防回弹）。"""

    @pytest.fixture(autouse=True)
    def _sandbox(self, tmp_path):
        self.script, self.root = _setup(tmp_path / "work", _work_source())

    def _run(self, *cli):
        return _exec(self.script, self.root, list(cli))

    @pytest.mark.parametrize("cmd", ["add", "list", "query", "summarize",
                                     "expire", "delete", "load", "export"])
    def test_all_subcommands_dispatch(self, cmd):
        """八个子命令均须被正确派发（不得落入 print_help 分支）。"""
        extra = {"add": ["--type", "note", "--text", "x"],
                 "delete": ["--index", "0"]}.get(cmd, [])
        if cmd == "delete":
            self._run("add", "--type", "note", "--text", "待删")
        rc, out, err = self._run(cmd, *extra)
        assert rc == 0, "%s 执行失败: %s" % (cmd, err)
        assert "usage:" not in out.lower(), "%s 未被派发，回落到帮助输出" % cmd

    def test_no_subcommand_prints_help(self):
        rc, out, _ = self._run()
        assert rc == 0 and "usage:" in out.lower()

    def test_invalid_type_exits_2(self):
        rc, out, _ = self._run("add", "--type", "nope", "--text", "x")
        assert rc == 2 and "类型须为" in out

    def test_load_prints_context(self):
        """load 子命令须把 load_context() 的结果打印到 stdout。"""
        self._run("add", "--type", "decision", "--text", "决策甲", "--meta", "M-1")
        rc, out, _ = self._run("load")
        assert rc == 0 and "- [decision] M-1: 决策甲" in out

    def test_load_empty_store(self):
        rc, out, _ = self._run("load")
        assert rc == 0 and "(无记忆)" in out

    def test_export_writes_bom_csv(self):
        self._run("add", "--type", "todo", "--text", "任务乙")
        self._run("export")
        p = self.root / "台账" / "38_项目记忆.csv"
        assert p.exists() and p.read_bytes().startswith(b"\xef\xbb\xbf")
        rows = list(csv.reader(io.StringIO(p.read_bytes().decode("utf-8-sig"))))
        assert rows[0] == ["时间", "类型", "内容", "关联", "状态"]
        assert rows[1][1] == "todo" and rows[1][2] == "任务乙"

    def test_help_lists_every_subcommand(self):
        """解析器构造须完整保留八个子命令。"""
        _, out, _ = self._run("--help")
        for cmd in ("add", "list", "query", "summarize", "expire",
                    "delete", "load", "export"):
            assert cmd in out

    def test_store_is_jsonl_append(self):
        for i in range(3):
            self._run("add", "--type", "note", "--text", "n%d" % i)
        p = self.root / "台账" / "38_项目记忆.jsonl"
        recs = [json.loads(ln) for ln in
                p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert [r["text"] for r in recs] == ["n0", "n1", "n2"]
        assert all(set(r) == {"ts", "type", "text", "meta"} for r in recs)
