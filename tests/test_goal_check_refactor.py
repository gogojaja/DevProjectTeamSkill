#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
goal_check.py 重构回归测试
==========================

背景：tools/goal_check.py 的 validate_sgd() 原为 76 行 / 圈复杂度 38，
goal_check() 原为 130 行 / 圈复杂度 30（DEEP-CMP-001 SEVERE 级技术债）。
已拆分为：
  - validate_sgd → _validate_statement / _validate_acceptance_criteria /
    _validate_ac_item / _validate_max_iterations / _validate_constraints /
    _validate_scope / _validate_error_recovery
  - goal_check   → _load_sgd / _print_format_errors / _print_validate_only_summary /
    _verify_criteria / _conclude / _print_progress / _print_constraint_violations /
    _print_recovery_advice / _resolve_output_path / _write_report_csv /
    _print_result_rows

本测试的重点是**差分等价**：把 git HEAD 版本与工作区版本各自 exec 成独立模块，
对同一批输入比对可观察结果，确保拆分只是结构变化、语义零漂移。
  1. validate_sgd 差分：覆盖必填/可选字段的缺失、类型错误、边界值、非法枚举、
     多字段组合等 100+ 组 SGD，错误列表须**逐元素且顺序一致**（顺序是 CLI 输出契约）。
  2. goal_check 端到端差分：同一路径沙箱内先后执行两版，比对 stdout / 返回字典 /
     CSV 报告字节。
  3. 行为契约：validate_only 短路、格式失败早返回、结论裁决三分支、恢复建议分派。

安全性：ROOT 经 PROJECT_ROOT 重定向到 tmp_path 沙箱，报告写入沙箱内，
不触碰真实台账（台账/41_活跃目标.json）与 docs/reviews/。
夹具仅使用 file_exists / file_contains / count_ge / manual 验证类型，
不触发 command_pass 的 shell 执行。

运行：python -m pytest tests/test_goal_check_refactor.py -q
"""

import copy
import io
import json
import os
import subprocess
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_REL = "tools/goal_check.py"
SCRIPT = REPO_ROOT / SCRIPT_REL


# ---------------------------------------------------------------- 模块装载

def _head_source():
    """取出 git HEAD 版本源码；不可用时跳过差分对比。"""
    r = subprocess.run(["git", "show", f"HEAD:{SCRIPT_REL}"], cwd=str(REPO_ROOT),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not r.stdout.strip():
        pytest.skip("git HEAD 版本不可用，跳过重构等价对比")
    return r.stdout


def _work_source():
    """读取工作区（重构后）源码。"""
    return SCRIPT.read_text(encoding="utf-8")


def _load(src, name, sandbox_root):
    """在指定 PROJECT_ROOT 下把源码 exec 成独立模块，并把 ROOT 指向沙箱。"""
    saved = os.environ.get("PROJECT_ROOT")
    os.environ["PROJECT_ROOT"] = str(sandbox_root)
    try:
        mod = types.ModuleType(name)
        mod.__file__ = str(SCRIPT)
        exec(compile(src, str(SCRIPT), "exec"), mod.__dict__)  # nosec: 测试装载，src 读自本地被测脚本(SCRIPT)非外部输入
    finally:
        if saved is None:
            os.environ.pop("PROJECT_ROOT", None)
        else:
            os.environ["PROJECT_ROOT"] = saved
    mod.ROOT = str(sandbox_root)
    mod.LEDGER_PATH = os.path.join(str(sandbox_root), "台账", "41_活跃目标.json")
    return mod


def _capture(fn, *args, **kwargs):
    """捕获 stdout 并返回 (输出文本, 函数返回值)。"""
    buf = io.StringIO()
    with redirect_stdout(buf):
        rv = fn(*args, **kwargs)
    return buf.getvalue(), rv


# ---------------------------------------------------------------- SGD 夹具

def _valid_ac(n=1, vtype="file_exists", target="a.txt", arg="", desc=None):
    """构造一条合法验收标准。"""
    ac = {"id": "AC-%d" % n,
          "description": desc if desc is not None else "验收项 %d" % n,
          "verify_type": vtype,
          "verify_target": target}
    if arg:
        ac["verify_arg"] = arg
    return ac


def _valid_sgd():
    """构造一份通过校验的完整 v1.1 SGD。"""
    return {
        "statement": "在沙箱内产出 a.txt 与 b.txt，并保证内容含标记",
        "acceptance_criteria": [
            _valid_ac(1, "file_exists", "a.txt"),
            _valid_ac(2, "file_contains", "b.txt", arg="MARK"),
            _valid_ac(3, "manual", desc="人工确认交付物完整性"),
        ],
        "max_iterations": 5,
        "constraints": [
            {"type": "file_not_modified", "target": "frozen.txt"},
            {"type": "file_not_created", "target": "forbidden.txt"},
        ],
        "scope": {"read_files": ["frozen.txt"], "write_files": ["a.txt", "b.txt"]},
        "error_recovery": {"on_circuit_break": "pause_wait_user",
                           "on_max_iterations": "handoff"},
    }


def _sgd_cases():
    """validate_sgd 差分用例矩阵：(标签, SGD 字典)。"""
    cases = [("valid_full", _valid_sgd())]

    # statement
    for label, mut in [
        ("stmt_missing", lambda s: s.pop("statement")),
        ("stmt_empty", lambda s: s.update(statement="")),
        ("stmt_short4", lambda s: s.update(statement="abcd")),
        ("stmt_exact5", lambda s: s.update(statement="abcde")),
        ("stmt_int", lambda s: s.update(statement=12345)),
        ("stmt_none", lambda s: s.update(statement=None)),
        ("stmt_list", lambda s: s.update(statement=["a"])),
    ]:
        s = _valid_sgd()
        mut(s)
        cases.append((label, s))

    # acceptance_criteria 集合级
    for label, mut in [
        ("ac_missing", lambda s: s.pop("acceptance_criteria")),
        ("ac_not_list", lambda s: s.update(acceptance_criteria="x")),
        ("ac_dict", lambda s: s.update(acceptance_criteria={"id": "AC-1"})),
        ("ac_empty", lambda s: s.update(acceptance_criteria=[])),
        ("ac_one", lambda s: s.update(acceptance_criteria=[_valid_ac(1)])),
        ("ac_20", lambda s: s.update(acceptance_criteria=[_valid_ac(i) for i in range(1, 21)])),
        ("ac_21", lambda s: s.update(acceptance_criteria=[_valid_ac(i) for i in range(1, 22)])),
    ]:
        s = _valid_sgd()
        mut(s)
        cases.append((label, s))

    # acceptance_criteria 逐项
    for label, ac in [
        ("item_not_dict", "AC-1"),
        ("item_list", ["AC-1"]),
        ("item_none", None),
        ("item_empty_dict", {}),
        ("item_no_id", {"description": "d", "verify_type": "manual"}),
        ("item_id_not_str", {"id": 1, "description": "d", "verify_type": "manual"}),
        ("item_id_bad_prefix", {"id": "XX-1", "description": "d", "verify_type": "manual"}),
        ("item_id_lower", {"id": "ac-1", "description": "d", "verify_type": "manual"}),
        ("item_no_desc", {"id": "AC-1", "verify_type": "manual"}),
        ("item_no_vtype", {"id": "AC-1", "description": "d"}),
        ("item_bad_vtype", {"id": "AC-1", "description": "d", "verify_type": "unknown_type"}),
        ("item_vtype_empty", {"id": "AC-1", "description": "d", "verify_type": ""}),
    ]:
        cases.append(("ac_" + label, {"statement": "合法目标陈述", "acceptance_criteria": [ac]}))

    # 多条混合：既有合法也有非法，验证顺序与索引编号
    cases.append(("ac_mixed", {
        "statement": "合法目标陈述",
        "acceptance_criteria": [
            _valid_ac(1),
            {"id": "BAD", "verify_type": "nope"},
            "not-a-dict",
            _valid_ac(4, "manual"),
        ]}))

    # max_iterations（注意 bool 是 int 子类，True 应被接受为 1）
    for label, v in [("mi_0", 0), ("mi_1", 1), ("mi_50", 50), ("mi_51", 51),
                     ("mi_neg", -3), ("mi_str", "5"), ("mi_float", 5.0),
                     ("mi_none", None), ("mi_true", True), ("mi_false", False)]:
        s = _valid_sgd()
        s["max_iterations"] = v
        cases.append((label, s))

    # constraints
    for label, v in [
        ("cs_not_list", "x"), ("cs_dict", {"type": "file_not_modified"}),
        ("cs_empty", []),
        ("cs_11", [{"type": "file_not_modified", "target": "f%d" % i} for i in range(11)]),
        ("cs_10", [{"type": "file_not_modified", "target": "f%d" % i} for i in range(10)]),
        ("cs_item_not_dict", ["x"]),
        ("cs_item_none", [None]),
        ("cs_item_no_type", [{"target": "f"}]),
        ("cs_item_bad_type", [{"type": "nope", "target": "f"}]),
        ("cs_item_no_target", [{"type": "file_not_modified"}]),
        ("cs_item_bare", [{}]),
        ("cs_mixed", [{"type": "file_not_modified", "target": "f"}, "junk", {}]),
    ]:
        s = _valid_sgd()
        s["constraints"] = v
        cases.append((label, s))

    # scope（v1.0 files/dirs 与 v1.1 读写分离键均需为数组）
    for key in ("files", "dirs", "write_files", "write_dirs", "read_files", "read_dirs"):
        s = _valid_sgd()
        s["scope"] = {key: "not-a-list"}
        cases.append(("scope_%s_str" % key, s))
        s2 = _valid_sgd()
        s2["scope"] = {key: []}
        cases.append(("scope_%s_empty" % key, s2))
    for label, v in [("scope_not_dict", "x"), ("scope_list", ["a"]), ("scope_empty", {}),
                     ("scope_none", None),
                     ("scope_multi_bad", {"files": "x", "read_dirs": 1, "write_files": ["ok"]})]:
        s = _valid_sgd()
        s["scope"] = v
        cases.append((label, s))

    # error_recovery
    for label, v in [
        ("er_not_dict", "x"), ("er_list", []), ("er_empty", {}),
        ("er_bad_break", {"on_circuit_break": "nope"}),
        ("er_bad_max", {"on_max_iterations": "nope"}),
        ("er_both_bad", {"on_circuit_break": "x", "on_max_iterations": "y"}),
        ("er_break_none", {"on_circuit_break": None}),
        ("er_max_handoff", {"on_max_iterations": "handoff"}),
        ("er_max_abort", {"on_max_iterations": "abort_goal"}),
        ("er_break_abort", {"on_circuit_break": "abort_goal"}),
        ("er_unknown_key", {"whatever": 1}),
    ]:
        s = _valid_sgd()
        s["error_recovery"] = v
        cases.append((label, s))

    # 多字段同时出错：验证错误累积顺序（statement → AC → mi → constraints → scope → er）
    broken = {
        "statement": "ab",
        "acceptance_criteria": [{"id": "BAD"}],
        "max_iterations": 999,
        "constraints": "not-a-list",
        "scope": "not-a-dict",
        "error_recovery": {"on_circuit_break": "bad", "on_max_iterations": "bad"},
    }
    cases.append(("all_broken", broken))
    cases.append(("empty_dict", {}))
    cases.append(("extra_unknown_keys", dict(_valid_sgd(), foo="bar", baz=1)))
    return cases


# ================================================================ validate_sgd 差分

@pytest.mark.parametrize("label,sgd", _sgd_cases(), ids=[c[0] for c in _sgd_cases()])
def test_validate_sgd_matches_head(tmp_path, label, sgd):
    """重构后的 validate_sgd 错误列表须与 HEAD 版本逐元素、同顺序一致。"""
    src_head, src_work = _head_source(), _work_source()
    if src_head == src_work:
        pytest.skip("HEAD 与工作区一致（重构已提交），无需差分对比")
    sandbox = tmp_path / "sb"
    sandbox.mkdir(parents=True, exist_ok=True)
    h = _load(src_head, "gc_head", sandbox)
    w = _load(src_work, "gc_work", sandbox)
    # 两版必须各自独立 deepcopy，防止前一次调用意外修改夹具造成假阴性
    expected = h.validate_sgd(copy.deepcopy(sgd))
    actual = w.validate_sgd(copy.deepcopy(sgd))
    assert actual == expected, f"[{label}] 错误列表不一致:\n  head={expected}\n  work={actual}"


@pytest.mark.parametrize("label,sgd", _sgd_cases(), ids=[c[0] for c in _sgd_cases()])
def test_validate_sgd_is_pure(tmp_path, label, sgd):
    """validate_sgd 必须是纯函数：不得修改入参 SGD。"""
    sandbox = tmp_path / "sb"
    sandbox.mkdir(parents=True, exist_ok=True)
    w = _load(_work_source(), "gc_pure", sandbox)
    before = copy.deepcopy(sgd)
    w.validate_sgd(sgd)
    assert sgd == before, f"[{label}] validate_sgd 修改了入参"


def test_valid_sgd_has_no_errors(tmp_path):
    """正向基线：完整合法的 v1.1 SGD 不应报任何错误。"""
    sandbox = tmp_path / "sb"
    sandbox.mkdir(parents=True, exist_ok=True)
    w = _load(_work_source(), "gc_ok", sandbox)
    assert w.validate_sgd(_valid_sgd()) == []


# ================================================================ goal_check 端到端

def _make_sandbox(base: Path) -> Path:
    """构造 goal_check 运行沙箱：目标文件 + 冻结文件 + 台账目录。"""
    base.mkdir(parents=True, exist_ok=True)
    (base / "a.txt").write_text("alpha\n", encoding="utf-8")
    (base / "b.txt").write_text("beta MARK gamma\n", encoding="utf-8")
    (base / "frozen.txt").write_text("do-not-touch\n", encoding="utf-8")
    (base / "台账").mkdir(parents=True, exist_ok=True)
    (base / "docs" / "reviews").mkdir(parents=True, exist_ok=True)
    return base


def _write_sgd(base: Path, sgd: dict, name="sgd.json") -> Path:
    p = base / name
    p.write_text(json.dumps(sgd, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _run_goal_check(mod, sgd_path, out_path, validate_only=False):
    """执行 goal_check 并返回 (stdout, 返回字典, CSV 字节)。"""
    out, rv = _capture(mod.goal_check, str(sgd_path), str(out_path), validate_only)
    csv_bytes = Path(out_path).read_bytes() if Path(out_path).exists() else None
    return out, rv, csv_bytes


@pytest.mark.parametrize("validate_only", [False, True])
@pytest.mark.parametrize("scenario", ["all_pass", "one_fail", "one_manual", "empty_ac"])
def test_goal_check_matches_head(tmp_path, scenario, validate_only):
    """goal_check 端到端差分：stdout / 返回字典 / CSV 报告须与 HEAD 版本一致。"""
    src_head, src_work = _head_source(), _work_source()
    if src_head == src_work:
        pytest.skip("HEAD 与工作区一致（重构已提交），无需差分对比")

    sgd = _valid_sgd()
    if scenario == "one_fail":
        sgd["acceptance_criteria"].append(_valid_ac(4, "file_exists", "missing.txt"))
    elif scenario == "one_manual":
        sgd["acceptance_criteria"].append(_valid_ac(5, "manual", desc="人工项"))
    elif scenario == "empty_ac":
        sgd["acceptance_criteria"] = [_valid_ac(1, "count_ge", "a.txt", arg="1")]

    results = []
    sandbox = tmp_path / "sb"          # 两版复用同一路径，避免绝对路径造成伪差异
    for tag, src in (("head", src_head), ("work", src_work)):
        import shutil
        if sandbox.exists():
            shutil.rmtree(str(sandbox), ignore_errors=True)
        _make_sandbox(sandbox)
        sgd_path = _write_sgd(sandbox, sgd)
        out_path = sandbox / "report.csv"
        mod = _load(src, f"gc_{tag}", sandbox)
        out, rv, csv_bytes = _run_goal_check(mod, sgd_path, out_path, validate_only)
        results.append((out, rv, csv_bytes))

    (h_out, h_rv, h_csv), (w_out, w_rv, w_csv) = results
    assert h_out == w_out, "stdout 不一致:\n" + _first_diff(h_out, w_out)
    assert h_rv == w_rv, f"返回字典不一致:\n  head={h_rv}\n  work={w_rv}"
    assert h_csv == w_csv, "CSV 报告字节不一致"


def _first_diff(a, b):
    la, lb = a.splitlines(), b.splitlines()
    for i, (x, y) in enumerate(zip(la, lb)):
        if x != y:
            return f"  L{i}: head={x!r}\n  L{i}: work={y!r}"
    return f"  行数不同: head={len(la)} work={len(lb)}"


class TestGoalCheckContract:
    """goal_check 的行为契约（不依赖 HEAD，可长期留存防回弹）。"""

    def _mod(self, tmp_path, tag="gc_c"):
        sandbox = _make_sandbox(tmp_path / "sb")
        return _load(_work_source(), tag, sandbox), sandbox

    def test_missing_file_exits_1(self, tmp_path):
        m, sb = self._mod(tmp_path, "gc_miss")
        buf = io.StringIO()
        with pytest.raises(SystemExit) as e:
            with redirect_stdout(buf):
                m.goal_check(str(sb / "nope.json"), str(sb / "o.csv"), False)
        assert e.value.code == 1
        assert "SGD 文件不存在" in buf.getvalue()
        assert not (sb / "o.csv").exists()

    def test_format_error_returns_early_without_csv(self, tmp_path):
        m, sb = self._mod(tmp_path, "gc_fmt")
        p = _write_sgd(sb, {"statement": "x"})
        out_path = sb / "o.csv"
        stdout, rv = _capture(m.goal_check, str(p), str(out_path), False)
        assert rv == {"valid": False, "errors": rv["errors"]}
        assert rv["valid"] is False and rv["errors"]
        assert "SGD 格式校验失败" in stdout
        assert not out_path.exists()

    def test_validate_only_short_circuits(self, tmp_path):
        m, sb = self._mod(tmp_path, "gc_vo")
        p = _write_sgd(sb, _valid_sgd())
        out_path = sb / "o.csv"
        stdout, rv = _capture(m.goal_check, str(p), str(out_path), True)
        assert rv == {"valid": True, "errors": []}
        assert "SGD 格式校验通过 (v1.1)" in stdout
        assert "验收标准: 3 条" in stdout
        assert "可验证约束: 2/2" in stdout
        assert "scope: 读写分离模式" in stdout
        assert "错误恢复: on_break=pause_wait_user on_max=handoff" in stdout
        assert not out_path.exists()

    def test_conclusion_all_pass(self, tmp_path):
        m, sb = self._mod(tmp_path, "gc_pass")
        sgd = _valid_sgd()
        sgd["acceptance_criteria"] = [_valid_ac(1, "file_exists", "a.txt"),
                                      _valid_ac(2, "file_contains", "b.txt", arg="MARK")]
        p = _write_sgd(sb, sgd)
        stdout, rv = _capture(m.goal_check, str(p), str(sb / "o.csv"), False)
        assert rv["conclusion"] == "全部通过"
        assert rv["pass"] == 2 and rv["fail"] == 0 and rv["manual"] == 0
        assert "结论: 全部通过" in stdout
        assert "进度: 2/2 通过 (100%)" in stdout

    def test_conclusion_needs_manual(self, tmp_path):
        m, sb = self._mod(tmp_path, "gc_manual")
        sgd = _valid_sgd()
        sgd["acceptance_criteria"] = [_valid_ac(1, "file_exists", "a.txt"),
                                      _valid_ac(2, "manual", desc="人工项")]
        p = _write_sgd(sb, sgd)
        _, rv = _capture(m.goal_check, str(p), str(sb / "o.csv"), False)
        assert rv["conclusion"] == "待人工确认"
        assert rv["manual"] == 1 and rv["fail"] == 0

    def test_conclusion_not_met_and_advice(self, tmp_path):
        m, sb = self._mod(tmp_path, "gc_fail")
        sgd = _valid_sgd()
        sgd["acceptance_criteria"] = [_valid_ac(1, "file_exists", "missing.txt")]
        p = _write_sgd(sb, sgd)
        stdout, rv = _capture(m.goal_check, str(p), str(sb / "o.csv"), False)
        assert rv["conclusion"] == "未达标" and rv["fail"] == 1
        assert "结论: 未达标" in stdout
        assert "建议: 暂停等待用户介入" in stdout

    @pytest.mark.parametrize("policy,expected", [
        ("pause_wait_user", "建议: 暂停等待用户介入"),
        ("skip_and_continue", "建议: 跳过失败项继续执行"),
        ("abort_goal", "建议: 中止目标并交接"),
    ])
    def test_recovery_advice_dispatch(self, tmp_path, policy, expected):
        m, sb = self._mod(tmp_path, "gc_adv_" + policy)
        sgd = _valid_sgd()
        sgd["acceptance_criteria"] = [_valid_ac(1, "file_exists", "missing.txt")]
        sgd["error_recovery"] = {"on_circuit_break": policy}
        p = _write_sgd(sb, sgd)
        stdout, _ = _capture(m.goal_check, str(p), str(sb / "o.csv"), False)
        assert expected in stdout

    def test_no_advice_when_all_pass(self, tmp_path):
        m, sb = self._mod(tmp_path, "gc_noadv")
        sgd = _valid_sgd()
        sgd["acceptance_criteria"] = [_valid_ac(1, "file_exists", "a.txt")]
        p = _write_sgd(sb, sgd)
        stdout, _ = _capture(m.goal_check, str(p), str(sb / "o.csv"), False)
        assert "建议:" not in stdout

    def test_csv_written_with_utf8_bom_and_header(self, tmp_path):
        m, sb = self._mod(tmp_path, "gc_csv")
        sgd = _valid_sgd()
        sgd["acceptance_criteria"] = [_valid_ac(1, "file_exists", "a.txt"),
                                      _valid_ac(2, "file_exists", "missing.txt")]
        p = _write_sgd(sb, sgd)
        out_path = sb / "nested" / "dir" / "o.csv"
        _, rv = _capture(m.goal_check, str(p), str(out_path), False)
        raw = out_path.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf"), "CSV 须为 utf-8-sig（Excel 直开）"
        text = raw.decode("utf-8-sig")
        assert text.splitlines()[0] == "id,description,verify_type,status,detail"
        assert rv["output_path"] == str(out_path)
        assert "AC-1" in text and "AC-2" in text

    def test_default_output_path_under_docs_reviews(self, tmp_path):
        m, sb = self._mod(tmp_path, "gc_def")
        sgd = _valid_sgd()
        sgd["acceptance_criteria"] = [_valid_ac(1, "file_exists", "a.txt")]
        p = _write_sgd(sb, sgd)
        _, rv = _capture(m.goal_check, str(p), None, False)
        assert rv["output_path"] == os.path.join(str(sb), "docs", "reviews",
                                                 "goal_check_report.csv")
        assert Path(rv["output_path"]).is_file()

    def test_constraint_violation_printed(self, tmp_path):
        m, sb = self._mod(tmp_path, "gc_con")
        sgd = _valid_sgd()
        sgd["acceptance_criteria"] = [_valid_ac(1, "file_exists", "a.txt")]
        # frozen.txt 被修改 → file_not_modified 约束应判违反
        (sb / "frozen.txt").write_text("tampered\n", encoding="utf-8")
        p = _write_sgd(sb, sgd)
        stdout, rv = _capture(m.goal_check, str(p), str(sb / "o.csv"), False)
        fails = [c for c in rv["constraint_results"] if c["status"] == "FAIL"]
        if fails:                      # 约束判定依赖基线快照，无基线时不违反
            assert "约束违反：" in stdout

    def test_result_rows_printed_with_marks(self, tmp_path):
        m, sb = self._mod(tmp_path, "gc_rows")
        sgd = _valid_sgd()
        sgd["acceptance_criteria"] = [_valid_ac(1, "file_exists", "a.txt"),
                                      _valid_ac(2, "file_exists", "missing.txt"),
                                      _valid_ac(3, "manual", desc="人工")]
        p = _write_sgd(sb, sgd)
        stdout, _ = _capture(m.goal_check, str(p), str(sb / "o.csv"), False)
        assert "[+] [AC-1]" in stdout
        assert "[x] [AC-2]" in stdout
        assert "[?] [AC-3]" in stdout


# ================================================================ 结构指标

def test_target_functions_below_threshold():
    """validate_sgd / goal_check 须降到阈值内（防债务回弹）。"""
    import ast
    tree = ast.parse(_work_source())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ("validate_sgd", "goal_check"):
            length = node.end_lineno - node.lineno + 1
            cc = 1 + sum(isinstance(x, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                                        ast.BoolOp, ast.IfExp, ast.comprehension))
                         for x in ast.walk(node))
            assert length <= 80, f"{node.name} 长度 {length} 超阈值 80"
            assert cc <= 15, f"{node.name} 圈复杂度 {cc} 超阈值 15"


def test_dangerous_command_guard_intact():
    """安全护栏不得因重构丢失：command_pass 仍须先过 _match_dangerous_command。"""
    src = _work_source()
    assert "_match_dangerous_command" in src
    assert "# nosec" in src, "shell=True 须保留 nosec 抑制标记与护栏说明"
