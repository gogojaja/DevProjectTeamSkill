#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scope_tracker.py cmd_gate 重构等价性回归测试
============================================
背景：cmd_gate() 圈复杂度 32（矩阵加载 + 基线漂移解析 + 合规明细打印 + 严重/警告裁决
      四件事混在一个函数），拆为 _gate_load_rows / _gate_resolve_drift /
      _gate_print_compliance / _gate_verdict 四个阶段函数。

验证方式：
  1) 差分等价：分别加载 HEAD 版本与重构版本为独立模块，patch 各自的台账路径到独立沙箱，
     以相同 RTM/变更台账/基线夹具调用 cmd_gate，比对
     退出码 + stdout + stderr + 快照台账（GATE_RESULT / DETAIL / 各计数列）。
  2) 行为契约：不依赖 HEAD 的长期断言（fail-closed、四种裁决、明细打印）。

沙箱化依据：DEFAULT_MATRIX / DEFAULT_TRACK / DEFAULT_CHANGE / DEFAULT_BASELINE
            均为模块级变量，可逐模块实例独立 patch。
归一化说明：快照含 SNAPSHOT_ID 与 SNAPSHOT_AT 时间戳，须归一化后比对。
"""
import argparse
import contextlib
import csv
import importlib.util
import io
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
REL_SCRIPT = "tools/scope_tracker.py"

RTM_COLS = ['REQ_ID', 'REQ_TITLE', 'AE_ID', 'MOD_ID', 'TC_ID', 'PRIORITY',
            'SCOPE_STATUS', 'BASELINE_VER', 'SOURCE', 'VERIFY_METHOD', 'CHANGE_REFS']
CHANGE_COLS = ['CHANGE_ID', 'REQ_IDS', 'TITLE', 'TYPE', 'SOURCE', 'IMPACT_SCOPE',
               'IMPACT_SCHEDULE', 'IMPACT_COST', 'IMPACT_QUALITY', 'IMPACT_SECURITY',
               'SEVERITY', 'STATUS', 'APPROVER', 'BASELINE_FROM', 'BASELINE_TO',
               'PROPOSED_AT', 'DECIDED_AT', 'NOTE']

_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")
_SN_RE = re.compile(r"SN-\d{14}")


# ---------------------------------------------------------------- 双版本加载

def _head_source():
    r = subprocess.run(["git", "show", "HEAD:" + REL_SCRIPT], cwd=str(REPO),
                       capture_output=True)
    if r.returncode != 0:
        pytest.skip("无法从 git HEAD 取基线版本：%s" % r.stderr.decode("utf-8", "replace"))
    return r.stdout.decode("utf-8")


def _work_source():
    return (REPO / REL_SCRIPT).read_text(encoding="utf-8")


def _load(src, name, tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    p = tmp / "scope_tracker.py"
    p.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, str(p))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- 夹具构造

def _write_csv(path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(str(path), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)


def _rtm_row(req, title="需求", ae="AE-001", mod="MOD-001", tc="TC-001",
             prio="Must", status="Verified", bver="v1.0.0",
             source="SRS", verify=None, crefs=""):
    return [req, title, ae, mod, tc, prio, status, bver, source,
            verify if verify is not None else tc, crefs]


def _cr_row(cid, reqs, status="提出", approver="", proposed="2020-01-01 00:00:00",
            decided="", bfrom="", bto=""):
    return [cid, reqs, "变更", "范围调整", "用户诉求", "高", "", "", "", "",
            "主要", status, approver, bfrom, bto, proposed, decided, ""]


# RTM 夹具：完整合规（Must + Verified + 五段追溯齐备）
RTM_CLEAN = [_rtm_row("REQ-001")]

# 两行（供基线净增/净减场景）
RTM_TWO = [_rtm_row("REQ-001"), _rtm_row("REQ-002", ae="AE-002", mod="MOD-002", tc="TC-002")]

# 违规：Must 缺 MOD/TC → 一致性/缩水违规
RTM_INCOMPLETE = [_rtm_row("REQ-001", mod="", tc="", status="Proposed")]

# 空矩阵（仅表头）
RTM_EMPTY = []

# 畸形矩阵：表头缺 AE/MOD/TC 必需列 → 一致性校验模块抛异常 → fail-closed
# （以原始文本形式写入，故用 str 而非行列表作为哨兵）
RTM_MALFORMED = "REQ_ID,REQ_TITLE\nREQ-001,r\n"

# 优先级降级：基线 Must → 当前 Should
RTM_PRIO_DOWN = [_rtm_row("REQ-001", prio="Should")]

CHANGE_NONE = []
CHANGE_OPEN_MUST = [_cr_row("CR-001", "REQ-001", status="提出")]
CHANGE_STALE = [_cr_row("CR-001", "REQ-900", status="分析中",
                        proposed="2020-01-01 00:00:00")]
CHANGE_NO_APPROVER = [_cr_row("CR-001", "REQ-900", status="已批准", approver="")]
CHANGE_APPROVED_NEW = [_cr_row("CR-001", "REQ-002", status="已批准", approver="张三")]


def _args(max_violations=0, min_health=90, against=None, allow_open=False):
    return argparse.Namespace(max_violations=max_violations, min_health=min_health,
                              against_baseline=against, allow_open_changes=allow_open)


# label -> (rtm_rows, change_rows, baseline_setup, args)
#   baseline_setup: None | (版本, 用于冻结的 RTM 行) | [(版本, 行), ...]
SCENARIOS = {
    "matrix_missing": (None, CHANGE_NONE, None, _args()),
    "matrix_malformed": (RTM_MALFORMED, CHANGE_NONE, None, _args()),
    "matrix_empty": (RTM_EMPTY, CHANGE_NONE, None, _args()),
    "clean_pass": (RTM_CLEAN, CHANGE_NONE, None, _args()),
    "clean_pass_loose": (RTM_CLEAN, CHANGE_NONE, None, _args(min_health=0)),
    "min_health_reject": (RTM_CLEAN, CHANGE_NONE, None, _args(min_health=101)),
    "incomplete_violations": (RTM_INCOMPLETE, CHANGE_NONE, None, _args()),
    "incomplete_tolerated": (RTM_INCOMPLETE, CHANGE_NONE, None,
                             _args(max_violations=50, min_health=0)),
    "open_must_reject": (RTM_CLEAN, CHANGE_OPEN_MUST, None, _args(min_health=0)),
    "open_must_allowed": (RTM_CLEAN, CHANGE_OPEN_MUST, None,
                          _args(min_health=0, allow_open=True)),
    "stale_cr_warn": (RTM_CLEAN, CHANGE_STALE, None, _args(min_health=0)),
    "missing_approver_warn": (RTM_CLEAN, CHANGE_NO_APPROVER, None, _args(min_health=0)),
    "baseline_same": (RTM_CLEAN, CHANGE_NONE, ("v1.0.0", RTM_CLEAN), _args(min_health=0)),
    "baseline_added": (RTM_TWO, CHANGE_NONE, ("v1.0.0", RTM_CLEAN), _args(min_health=0)),
    "baseline_added_approved": (RTM_TWO, CHANGE_APPROVED_NEW, ("v1.0.0", RTM_CLEAN),
                                _args(min_health=0)),
    "baseline_removed": (RTM_CLEAN, CHANGE_NONE, ("v1.0.0", RTM_TWO), _args(min_health=0)),
    "baseline_prio_down": (RTM_PRIO_DOWN, CHANGE_NONE, ("v1.0.0", RTM_CLEAN),
                           _args(min_health=0)),
    "baseline_explicit_missing": (RTM_CLEAN, CHANGE_NONE, ("v1.0.0", RTM_CLEAN),
                                  _args(min_health=0, against="v9.9.9")),
    "baseline_explicit_hit": (RTM_CLEAN, CHANGE_NONE, ("v1.0.0", RTM_CLEAN),
                              _args(min_health=0, against="v1.0.0")),
    "baseline_multi_picks_latest": (RTM_CLEAN, CHANGE_NONE,
                                    [("v1.0.0", RTM_TWO), ("v1.0.10", RTM_CLEAN)],
                                    _args(min_health=0)),
}


def _prepare(mod, sandbox: Path, rtm_rows, change_rows, baseline_setup):
    """patch 模块台账路径并写入夹具。rtm_rows=None 表示不创建矩阵文件。"""
    ledger = sandbox / "台账"
    ledger.mkdir(parents=True, exist_ok=True)
    mod.DEFAULT_MATRIX = str(ledger / "rtm.csv")
    mod.DEFAULT_TRACK = str(ledger / "track.csv")
    mod.DEFAULT_CHANGE = str(ledger / "change.csv")
    mod.DEFAULT_BASELINE = str(ledger / "baseline.csv")

    if isinstance(rtm_rows, str):
        # 哨兵：直接写入原始文本（用于构造表头缺列等畸形矩阵）
        Path(mod.DEFAULT_MATRIX).write_text(rtm_rows, encoding="utf-8-sig")
    elif rtm_rows is not None:
        _write_csv(Path(mod.DEFAULT_MATRIX), RTM_COLS, rtm_rows)
    if change_rows:
        _write_csv(Path(mod.DEFAULT_CHANGE), CHANGE_COLS, change_rows)
    if baseline_setup:
        setups = baseline_setup if isinstance(baseline_setup, list) else [baseline_setup]
        for ver, rows in setups:
            dicts = [dict(zip(RTM_COLS, r)) for r in rows]
            ok, msg = mod.freeze_baseline(ver, dicts, force=True)
            assert ok, msg


def _norm(text, sandbox=None):
    """归一化时间戳、快照 ID 与沙箱结对路径（两版本沙箱名不同）。"""
    if sandbox is not None:
        text = text.replace(str(sandbox), "<SB>")
    return _SN_RE.sub("<SN>", _TS_RE.sub("<TS>", text))


def _capture(mod, sandbox, rtm_rows, change_rows, baseline_setup, args):
    _prepare(mod, sandbox, rtm_rows, change_rows, baseline_setup)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = mod.cmd_gate(args)
    track = Path(mod.DEFAULT_TRACK)
    track_rows = []
    if track.exists():
        with io.open(str(track), encoding="utf-8-sig", newline="") as f:
            track_rows = [[_norm(c, sandbox) for c in row] for row in csv.reader(f)]
    return (rc, _norm(out.getvalue(), sandbox), _norm(err.getvalue(), sandbox),
            track_rows)


def test_scenario_matches_head(tmp_path):
    """全部场景下，重构版与 HEAD 版的退出码/输出/快照台账须完全一致。"""
    head = _load(_head_source(), "st_head", tmp_path / "src_head")
    work = _load(_work_source(), "st_work", tmp_path / "src_work")
    try:
        for label, (rtm, changes, baseline, args) in sorted(SCENARIOS.items()):
            h = _capture(head, tmp_path / ("h_" + label), rtm, changes, baseline,
                         _args(args.max_violations, args.min_health,
                               args.against_baseline, args.allow_open_changes))
            w = _capture(work, tmp_path / ("w_" + label), rtm, changes, baseline,
                         _args(args.max_violations, args.min_health,
                               args.against_baseline, args.allow_open_changes))
            assert h[0] == w[0], "[%s] 退出码 head=%s work=%s\n%s\n%s" % (
                label, h[0], w[0], h[1], h[2])
            assert h[1] == w[1], "[%s] stdout 不一致:\n--- head ---\n%s\n--- work ---\n%s" % (
                label, h[1], w[1])
            assert h[2] == w[2], "[%s] stderr 不一致:\n--- head ---\n%s\n--- work ---\n%s" % (
                label, h[2], w[2])
            assert h[3] == w[3], "[%s] 快照台账不一致:\nhead=%s\nwork=%s" % (
                label, h[3], w[3])
    finally:
        for n in ("st_head", "st_work"):
            sys.modules.pop(n, None)


# ---------------------------------------------------------------- 行为契约

class TestGateContract:
    """不依赖 HEAD 的长期契约断言（防回弹）。"""

    @pytest.fixture(autouse=True)
    def _mod(self, tmp_path):
        self.tmp = tmp_path
        self.mod = _load(_work_source(), "st_contract", tmp_path / "src_c")
        yield
        sys.modules.pop("st_contract", None)

    def _gate(self, label, rtm, changes=CHANGE_NONE, baseline=None, args=None):
        out, err = io.StringIO(), io.StringIO()
        _prepare(self.mod, self.tmp / label, rtm, changes, baseline)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = self.mod.cmd_gate(args or _args())
        track = Path(self.mod.DEFAULT_TRACK)
        rows = []
        if track.exists():
            with io.open(str(track), encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
        return rc, out.getvalue(), err.getvalue(), rows

    def test_missing_matrix_returns_1(self):
        rc, _, err, rows = self._gate("c_missing", None)
        assert rc == 1 and "未找到追溯矩阵" in err and not rows

    def test_malformed_matrix_fail_closed_returns_2(self):
        rc, _, err, _ = self._gate("c_bad", RTM_MALFORMED)
        assert rc == 2 and "fail-closed" in err

    def test_empty_matrix_returns_1(self):
        rc, _, err, _ = self._gate("c_empty", RTM_EMPTY)
        assert rc == 1 and "追溯矩阵为空" in err

    def test_clean_passes_and_records_snapshot(self):
        rc, out, _, rows = self._gate("c_clean", RTM_CLEAN)
        assert rc == 0 and "范围门禁结论: 通过" in out
        assert rows and rows[-1]["GATE_RESULT"] == "通过"
        assert "变更合规（F3/F4）" in out

    def test_low_health_rejects(self):
        rc, out, _, rows = self._gate("c_health", RTM_CLEAN,
                                      args=_args(min_health=101))
        assert rc == 1 and "驳回" in out
        assert rows[-1]["GATE_RESULT"] == "驳回"

    def test_open_unapproved_must_rejects(self):
        rc, _, _, rows = self._gate("c_open", RTM_CLEAN, CHANGE_OPEN_MUST,
                                    args=_args(min_health=0))
        assert rc == 1 and rows[-1]["GATE_RESULT"] == "驳回"

    def test_allow_open_downgrades_to_warning(self):
        rc, out, _, rows = self._gate("c_allow", RTM_CLEAN, CHANGE_OPEN_MUST,
                                      args=_args(min_health=0, allow_open=True))
        assert rc == 0 and rows[-1]["GATE_RESULT"] == "警告"
        assert "通过" not in out.split("范围门禁结论:")[-1]

    def test_stale_cr_warns(self):
        rc, _, _, rows = self._gate("c_stale", RTM_CLEAN, CHANGE_STALE,
                                    args=_args(min_health=0))
        assert rc == 0 and rows[-1]["GATE_RESULT"] == "警告"

    def test_missing_approver_warns(self):
        rc, _, _, rows = self._gate("c_appr", RTM_CLEAN, CHANGE_NO_APPROVER,
                                    args=_args(min_health=0))
        assert rc == 0 and rows[-1]["GATE_RESULT"] == "警告"

    def test_no_baseline_reports_no_frozen(self):
        _, out, _, _ = self._gate("c_nobase", RTM_CLEAN, args=_args(min_health=0))
        assert "（无冻结基线）" in out

    def test_baseline_unapproved_addition_printed(self):
        _, out, _, _ = self._gate("c_add", RTM_TWO, baseline=("v1.0.0", RTM_CLEAN),
                                  args=_args(min_health=0))
        assert "未审批新增(蔓延)" in out and "REQ-002" in out
        assert "（对比基线 v1.0.0）" in out

    def test_baseline_approved_addition_not_flagged(self):
        _, out, _, _ = self._gate("c_addok", RTM_TWO, CHANGE_APPROVED_NEW,
                                  baseline=("v1.0.0", RTM_CLEAN),
                                  args=_args(min_health=0))
        assert "未审批新增(蔓延)" not in out

    def test_baseline_removal_printed(self):
        _, out, _, _ = self._gate("c_rm", RTM_CLEAN, baseline=("v1.0.0", RTM_TWO),
                                  args=_args(min_health=0))
        assert "未审批删除(缩水)" in out and "REQ-002" in out

    def test_baseline_priority_down_printed(self):
        _, out, _, _ = self._gate("c_prio", RTM_PRIO_DOWN,
                                  baseline=("v1.0.0", RTM_CLEAN),
                                  args=_args(min_health=0))
        assert "未审批优先级降级" in out and "Must→Should" in out

    def test_explicit_missing_baseline_no_detail(self):
        """指定了未冻结的基线版本 → diff.ok=False，不得打印明细，且不得崩溃。"""
        rc, out, _, _ = self._gate("c_miss_base", RTM_CLEAN,
                                   baseline=("v1.0.0", RTM_CLEAN),
                                   args=_args(min_health=0, against="v9.9.9"))
        assert rc in (0, 1)
        assert "未审批新增(蔓延)" not in out and "（对比基线 v9.9.9）" in out

    def test_latest_baseline_auto_selected(self):
        """未指定 --against-baseline 时应自动选用版本号最大的冻结基线。"""
        _, out, _, _ = self._gate(
            "c_latest", RTM_CLEAN,
            baseline=[("v1.0.0", RTM_TWO), ("v1.0.10", RTM_CLEAN)],
            args=_args(min_health=0))
        assert "（对比基线 v1.0.10）" in out

    def test_detail_column_format(self):
        _, _, _, rows = self._gate("c_detail", RTM_CLEAN, args=_args(min_health=0))
        detail = rows[-1]["DETAIL"]
        assert re.match(r"^违规\d+/蔓延\d+/缩水\d+/健康[\d.]+/未审批\d+/漂移\d+$", detail)

    def test_snapshot_appends_not_overwrites(self):
        """连续两次门禁应追加两条快照。"""
        self._gate("c_twice", RTM_CLEAN, args=_args(min_health=0))
        _, _, _, rows = self._gate("c_twice", RTM_CLEAN, args=_args(min_health=0))
        assert len(rows) == 2
