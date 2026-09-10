#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
desensitize.py 重构回归测试
============================

背景：tools/desensitize/desensitize.py 的 main() 原为 244 行、圈复杂度 53 的巨型
CLI 函数（DEEP-CMP-001/002 SEVERE 级技术债），已按阶段拆分为 _build_parser /
_build_rules / _collect_targets / _process_files / _finalize 等函数。

本测试提供两层保障：
  1. 行为契约（永久）：对扫描/脱敏/dry-run/in-place/输出目录/级别过滤/JSON/
     自定义关键词/异常目标等场景断言可观察行为。
  2. 重构等价性（临时）：当 git HEAD 版本与工作区版本不同时，用同一组夹具分别
     运行两个版本，逐字节比对 stdout / 退出码 / 产物文件；一致则证明拆分未改变
     行为。HEAD 与工作区相同（重构已入库）时自动跳过。

运行：python -m pytest tests/test_desensitize_refactor.py -q
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_REL = "tools/desensitize/desensitize.py"
SCRIPT = REPO_ROOT / SCRIPT_REL

# 报告 CSV 内的生成时间戳，比对前归一化
_TS_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")

# 含 A/B/C 三级敏感信息的夹具内容
FIXTURE_DOC = """# 项目内部文档

联系人：张三，手机 13800138000，邮箱 zhangsan@example.com
数据库口令：password = "Sup3rSecret!"
GitHub 令牌：ghp_16C7e42F292c6912E7710c838347Ae178B4a
内网地址：192.168.1.100
普通说明文字，不含敏感信息。
"""

FIXTURE_CLEAN = """# 干净文档

这里没有任何敏感信息，只有普通的技术说明。
"""


# ── 夹具 ──
def _make_fixture(base: Path) -> Path:
    """在 base 下构造待处理目录，返回目标目录路径。"""
    target = base / "src"
    (target / "sub").mkdir(parents=True)
    (target / "doc.md").write_text(FIXTURE_DOC, encoding="utf-8")
    (target / "sub" / "clean.md").write_text(FIXTURE_CLEAN, encoding="utf-8")
    return target


def _decode(data: bytes) -> str:
    """解码子进程输出。

    脚本已将 stdout 重配为 UTF-8，但 stderr 仍是 Windows 本地代码页（GBK），
    因此依次尝试 UTF-8 / GBK，避免中文断言因编码而假失败。
    """
    for enc in ("utf-8", "gbk", "cp936"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def _normalize(text: str, roots=()) -> str:
    """归一化时间戳、脚本路径与工作目录绝对路径，使 orig/new 两轮输出可比对。"""
    out = _TS_PATTERN.sub("<TS>", text)
    for r in roots:
        if not r:
            continue
        # JSON 转义形（双反斜杠）优先，再原形与 POSIX 形
        for variant in (r.replace("\\", "\\\\"), r, r.replace("\\", "/")):
            out = out.replace(variant, "<CWD>")
    return out


def _run(script: Path, args, cwd: Path):
    """运行脚本，返回 (exit_code, stdout, stderr)，输出已归一化。"""
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(cwd), capture_output=True,
    )
    roots = (str(script), str(cwd))
    return (
        proc.returncode,
        _normalize(_decode(proc.stdout), roots),
        _normalize(_decode(proc.stderr), roots),
    )


def _snapshot(root: Path):
    """快照目录下所有文件的相对路径与内容（时间戳与绝对路径归一化）。"""
    snap = {}
    base = str(root)
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                text = repr(p.read_bytes())
            snap[rel] = _normalize(text, (base,))
    return snap


def _head_version() -> str | None:
    """取 git HEAD 中的脚本源码；不可用时返回 None。"""
    proc = subprocess.run(
        ["git", "show", f"HEAD:{SCRIPT_REL}"],
        cwd=str(REPO_ROOT), capture_output=True,
    )
    if proc.returncode != 0:
        return None
    try:
        return proc.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None


# ── 行为契约（永久） ──
class TestDesensitizeCliContract:
    """CLI 可观察行为契约，独立于内部实现。"""

    def test_scan_detects_and_exits_nonzero_on_a_level(self, tmp_path):
        """扫描模式发现 A 级敏感信息时返回 1，且不修改原文件。"""
        target = _make_fixture(tmp_path)
        before = (target / "doc.md").read_text(encoding="utf-8")
        report = tmp_path / "scan.csv"

        code, out, err = _run(
            SCRIPT, ["--scan", str(target), "--report", str(report)], tmp_path)

        assert code == 1, f"A 级发现应返回 1，实际 {code}；stderr={err}"
        assert "发现敏感信息" in out
        assert "A 级:" in out
        assert (target / "doc.md").read_text(encoding="utf-8") == before
        assert report.exists()

    def test_scan_json_output_is_valid(self, tmp_path):
        """--json 输出可被解析，且字段齐全。"""
        import json

        target = _make_fixture(tmp_path)
        code, out, _ = _run(
            SCRIPT,
            ["--scan", "--json", str(target), "--report", str(tmp_path / "s.csv")],
            tmp_path,
        )
        payload = json.loads(out[out.index("{"):])
        assert payload["mode"] == "scan"
        assert payload["files_total"] == 2
        assert payload["files_processed"] == 2
        assert payload["findings_count"] > 0

    def test_level_filter_limits_rules(self, tmp_path):
        """--level A 只保留 A 级规则，发现数不超过全量扫描。"""
        target = _make_fixture(tmp_path)
        _, out_all, _ = _run(
            SCRIPT, ["--scan", str(target), "--report", str(tmp_path / "a.csv")], tmp_path)
        _, out_a, _ = _run(
            SCRIPT,
            ["--scan", "--level", "A", str(target), "--report", str(tmp_path / "b.csv")],
            tmp_path,
        )
        n_all = int(re.search(r"发现敏感信息: (\d+) 处", out_all).group(1))
        n_a = int(re.search(r"发现敏感信息: (\d+) 处", out_a).group(1))
        assert 0 < n_a <= n_all

    def test_desensitize_to_output_dir(self, tmp_path):
        """脱敏到输出目录：原文件不变，输出文件已替换敏感值。"""
        target = _make_fixture(tmp_path)
        out_dir = tmp_path / "out"

        code, out, err = _run(
            SCRIPT,
            [str(target), "-o", str(out_dir), "--report", str(tmp_path / "d.csv")],
            tmp_path,
        )

        assert code == 0, f"stderr={err}"
        produced = out_dir / "doc.md"
        assert produced.exists()
        text = produced.read_text(encoding="utf-8")
        assert text != FIXTURE_DOC, "输出文件应已发生替换"
        assert "ghp_16C7e42F292c6912E7710c838347Ae178B4a" not in text
        assert "192.168.1.100" not in text
        # 原文件保持原样
        assert (target / "doc.md").read_text(encoding="utf-8") == FIXTURE_DOC

    def test_dry_run_writes_nothing(self, tmp_path):
        """--dry-run 预览但不落盘。"""
        target = _make_fixture(tmp_path)
        code, out, _ = _run(
            SCRIPT,
            ["--dry-run", str(target), "--report", str(tmp_path / "dry.csv")],
            tmp_path,
        )
        assert code == 0
        assert "将替换" in out
        assert not list(target.rglob("*.desensitized"))

    def test_in_place_modifies_source(self, tmp_path):
        """--in-place 原地替换单个文件。"""
        target = _make_fixture(tmp_path)
        doc = target / "doc.md"

        code, _, err = _run(
            SCRIPT,
            ["--in-place", str(doc), "--report", str(tmp_path / "ip.csv")],
            tmp_path,
        )

        assert code == 0, f"stderr={err}"
        text = doc.read_text(encoding="utf-8")
        assert text != FIXTURE_DOC, "--in-place 应已原地替换"
        assert "ghp_16C7e42F292c6912E7710c838347Ae178B4a" not in text

    def test_custom_keywords_applied(self, tmp_path):
        """--keywords 追加的自定义关键词参与替换。"""
        target = tmp_path / "src"
        target.mkdir()
        (target / "kw.md").write_text("代号 Titan 与联系人 张三 出现。\n", encoding="utf-8")

        code, out, _ = _run(
            SCRIPT,
            ["--keywords", "Titan,张三", "--dry-run", str(target),
             "--report", str(tmp_path / "kw.csv")],
            tmp_path,
        )
        assert code == 0
        assert "已加载 2 个自定义关键词" in out
        assert "将替换" in out

    def test_list_rules_short_circuits(self, tmp_path):
        """--list-rules 直接返回 0，不需要 target。"""
        code, out, _ = _run(SCRIPT, ["--list-rules"], tmp_path)
        assert code == 0
        assert "当前脱敏规则集" in out

    def test_missing_target_exits_nonzero(self, tmp_path):
        """目标不存在时返回 1 并输出错误。"""
        code, _, err = _run(
            SCRIPT,
            ["--scan", str(tmp_path / "nope"), "--report", str(tmp_path / "x.csv")],
            tmp_path,
        )
        assert code == 1
        assert "目标不存在" in err

    def test_no_rules_file_exits_nonzero(self, tmp_path):
        """--rules 指向不存在的文件时返回 1。"""
        target = _make_fixture(tmp_path)
        code, _, err = _run(
            SCRIPT,
            ["--scan", "--rules", str(tmp_path / "missing.json"), str(target)],
            tmp_path,
        )
        assert code == 1
        assert "自定义规则文件不存在" in err

    def test_empty_target_returns_zero(self, tmp_path):
        """目录内无可处理文件时返回 0 并提示。"""
        empty = tmp_path / "empty"
        empty.mkdir()
        code, out, _ = _run(
            SCRIPT, ["--scan", str(empty), "--report", str(tmp_path / "e.csv")], tmp_path)
        assert code == 0
        assert "未找到可处理的文件" in out


# ── 重构等价性（git HEAD 与工作区不同时生效） ──
SCENARIOS = [
    ("scan", ["--scan", "{target}", "--report", "r.csv"]),
    ("scan_json", ["--scan", "--json", "{target}", "--report", "r.csv"]),
    ("scan_level_a", ["--scan", "--level", "A", "{target}", "--report", "r.csv"]),
    ("scan_keywords", ["--scan", "--keywords", "张三,Titan", "{target}", "--report", "r.csv"]),
    ("output_dir", ["{target}", "-o", "out", "--report", "r.csv"]),
    ("dry_run", ["--dry-run", "{target}", "--report", "r.csv"]),
    ("in_place", ["--in-place", "{doc}", "--report", "r.csv"]),
    ("list_rules", ["--list-rules"]),
    ("missing_target", ["--scan", "nope", "--report", "r.csv"]),
    ("empty_dir", ["--scan", "{empty}", "--report", "r.csv"]),
]


def _prepare_case(base: Path) -> dict:
    """构造单个场景的夹具，返回路径占位符映射。"""
    target = _make_fixture(base)
    empty = base / "empty"
    empty.mkdir()
    return {
        "target": str(target),
        "doc": str(target / "doc.md"),
        "empty": str(empty),
    }


@pytest.mark.parametrize("name,argv", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_refactor_is_behaviorally_equivalent(name, argv, tmp_path):
    """重构版与 git HEAD 版在同夹具下输出完全一致。"""
    head_src = _head_version()
    if head_src is None:
        pytest.skip("无法从 git HEAD 取得重构前版本")
    if head_src == SCRIPT.read_text(encoding="utf-8"):
        pytest.skip("HEAD 与工作区一致（重构已入库），无需等价性比对")

    orig = tmp_path / "orig_desensitize.py"
    orig.write_text(head_src, encoding="utf-8")

    results = []
    for label, script in (("orig", orig), ("new", SCRIPT)):
        work = tmp_path / label
        work.mkdir()
        paths = _prepare_case(work)
        args = [a.format(**paths) for a in argv]
        code, out, err = _run(script, args, work)
        results.append((code, out, err, _snapshot(work)))

    (o_code, o_out, o_err, o_snap), (n_code, n_out, n_err, n_snap) = results

    assert n_code == o_code, f"[{name}] 退出码不同: orig={o_code} new={n_code}\nstderr={n_err}"
    assert n_out == o_out, f"[{name}] stdout 不同:\n--- orig ---\n{o_out}\n--- new ---\n{n_out}"
    assert n_err == o_err, f"[{name}] stderr 不同:\n--- orig ---\n{o_err}\n--- new ---\n{n_err}"

    # 产物比对：忽略 __pycache__
    o_files = {k: v for k, v in o_snap.items() if "__pycache__" not in k}
    n_files = {k: v for k, v in n_snap.items() if "__pycache__" not in k}
    o_files.pop("orig_desensitize.py", None)
    assert n_files == o_files, (
        f"[{name}] 产物文件不同:\norig={sorted(o_files)}\nnew={sorted(n_files)}")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
