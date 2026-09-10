#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nightly_quality_gate.py 重构回归测试
=====================================

背景：tools/nightly_quality_gate.py 的 run_project() 原为 143 行、圈复杂度 52 的
巨型编排函数（DEEP-CMP-001 SEVERE 级技术债），已按阶段 0~8 拆分为
_phase_credential / _phase_quality_gate / _phase_unit_tests / _phase_desensitize /
_phase_dev_views / _phase_ai_review / _write_gate_rows / _enqueue_pending。

验证策略：run_project 会级联调用 quality_gate、pytest、desensitize 等多个外部工具，
其输出依赖这些工具自身的状态，无法做端到端逐字节比对。因此改为**确定性等价测试**：
把模块加载进隔离的 PROJECT_ROOT 沙箱，将 _run / subprocess.run / notify 替换为
记录桩，再对 git HEAD 原版与工作区重构版施加同一组场景，比对
  · run_project 返回值
  · 全部 stdout
  · _run / subprocess.run / notify 的调用序列与参数
  · 台账 36/39 CSV 的落盘内容

运行：python -m pytest tests/test_nightly_quality_gate_refactor.py -q
"""

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_REL = "tools/nightly_quality_gate.py"
SCRIPT = REPO_ROOT / SCRIPT_REL

# 台账中的时间戳（各轮运行相差数秒，比对前归一化）
_TS = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?")

DEV_TOOLS = (
    "tools/arch_fitness.py",
    "tools/pattern_guard.py",
    "tools/adr_trace.py",
)


# ── 沙箱与模块加载 ──
def _make_root(base: Path, *, load_secret=True, desensitize=True, dev_tools=()):
    """构造隔离的 PROJECT_ROOT，通过文件存在性控制各阶段分支。"""
    (base / "tools" / "desensitize").mkdir(parents=True)
    (base / "台账").mkdir(parents=True)
    if load_secret:
        (base / "tools" / "load_secret.py").write_text("", encoding="utf-8")
    if desensitize:
        (base / "tools" / "desensitize" / "desensitize.py").write_text("", encoding="utf-8")
    for rel in dev_tools:
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("", encoding="utf-8")
    return base


def _load_module(src: str, name: str, root: Path, *, ai_env=False, ai_budget="0"):
    """在指定 PROJECT_ROOT 下把源码加载为独立模块实例。"""
    env_backup = {k: os.environ.get(k) for k in ("PROJECT_ROOT", "ENABLE_AI_REVIEW", "AI_BUDGET")}
    os.environ["PROJECT_ROOT"] = str(root)
    os.environ["ENABLE_AI_REVIEW"] = "true" if ai_env else "false"
    os.environ["AI_BUDGET"] = ai_budget
    try:
        spec = importlib.util.spec_from_loader(name, loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPT)
        exec(compile(src, str(SCRIPT), "exec"), mod.__dict__)  # nosec: 测试装载，src 读自本地被测脚本(SCRIPT)非外部输入
        return mod
    finally:
        for k, v in env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _head_source() -> str:
    """取 git HEAD 中的脚本源码。"""
    proc = subprocess.run(["git", "show", f"HEAD:{SCRIPT_REL}"],
                          cwd=str(REPO_ROOT), capture_output=True)
    assert proc.returncode == 0, "无法从 git HEAD 取得重构前版本"
    return proc.stdout.decode("utf-8")


# ── 桩件 ──
class Recorder:
    """记录模块对外部世界的全部副作用，用于两版逐条比对。"""

    def __init__(self, mod, run_results=None, unit_test=None):
        self.mod = mod
        self.events = []
        self.run_results = run_results or {}
        self.unit_test = unit_test or (0, "pytest ok", "")
        # subprocess 是全局共享模块，打桩后必须还原，否则会泄漏到后续用例
        self._saved_subprocess_run = mod.subprocess.run
        self._install()

    def restore(self):
        """还原对全局 subprocess.run 的桩替换。"""
        self.mod.subprocess.run = self._saved_subprocess_run

    def _install(self):
        mod = self.mod

        def fake_run(script_args, cwd=None):
            key = tuple(script_args)
            self.events.append(("tool_run", key))
            return self.run_results.get(key, (True, "", ""))

        def fake_subprocess_run(cmd, **kwargs):
            self.events.append(("subprocess", tuple(str(c) for c in cmd)))

            class R:
                returncode = self.unit_test[0]
                stdout = self.unit_test[1]
                stderr = self.unit_test[2]

            if self.unit_test[0] == "timeout":
                raise mod.subprocess.TimeoutExpired(cmd, 1)
            if self.unit_test[0] == "boom":
                raise OSError("simulated failure")
            return R()

        def fake_notify(level, msg, project="", webhook=""):
            self.events.append(("notify", level, msg, project, webhook))

        mod._run = fake_run
        mod.subprocess.run = fake_subprocess_run
        mod.notify = fake_notify

    def ledger(self):
        """读取沙箱台账内容（时间戳归一化）。"""
        out = {}
        for p in sorted((Path(self.mod.ROOT) / "台账").glob("*.csv")):
            out[p.name] = _TS.sub("<TS>", p.read_text(encoding="utf-8-sig", errors="replace"))
        return out


# ── 场景定义 ──
PROJECT = {
    "project_alias": "demo-proj",
    "project_path": "/tmp/demo",
    "test_cmd": "pytest tests -q",
    "secret_ref": "DB_DSN",
}

PROJECT_NO_EXTRAS = {
    "project_alias": "bare-proj",
    "project_path": "",
    "test_cmd": "",
    "secret_ref": "",
}

QG_FAIL = ("tools/quality_gate.py", "run", "--target", "demo-proj")
LOAD_SECRET = ("tools/load_secret.py", "DB_DSN")


SCENARIOS = [
    ("all_green_dry", dict(p=PROJECT, dry=True, results={}, unit=(0, "", ""))),
    ("all_green_wet", dict(p=PROJECT, dry=False, results={}, unit=(0, "ok", ""))),
    ("gate_fail", dict(p=PROJECT, dry=False,
                       results={QG_FAIL: (False, "", "version mismatch")},
                       unit=(0, "ok", ""))),
    ("unit_test_fail", dict(p=PROJECT, dry=False, results={}, unit=(1, "", "assert x == y"))),
    ("unit_test_timeout", dict(p=PROJECT, dry=False, results={}, unit=("timeout", "", ""))),
    ("unit_test_crash", dict(p=PROJECT, dry=False, results={}, unit=("boom", "", ""))),
    ("secret_unresolvable", dict(p=PROJECT, dry=False,
                                 results={LOAD_SECRET: (False, "", "not found")},
                                 unit=(0, "", ""))),
    ("bare_project", dict(p=PROJECT_NO_EXTRAS, dry=False, results={}, unit=(0, "", ""))),
    ("bare_project_dry", dict(p=PROJECT_NO_EXTRAS, dry=True, results={}, unit=(0, "", ""))),
    ("ai_review_on", dict(p=PROJECT, dry=False, results={}, unit=(0, "", ""), ai_env=True)),
    ("ai_budget_without_switch", dict(p=PROJECT, dry=False, results={}, unit=(0, "", ""),
                                      ai_budget="500")),
    ("webhook_on_fail", dict(p=PROJECT, dry=False,
                             results={QG_FAIL: (False, "", "boom")},
                             unit=(0, "", ""), webhook="http://127.0.0.1:1/hook")),
]


def _run_scenario(src, name, cfg, tmp_path):
    """在沙箱中执行一个场景，返回可比对的结果元组。"""
    root = _make_root(
        tmp_path / name,
        load_secret=True,
        desensitize=cfg.get("desensitize", True),
        dev_tools=DEV_TOOLS if cfg.get("dev_tools", True) else (),
    )
    mod = _load_module(src, f"nqg_{name}", root,
                       ai_env=cfg.get("ai_env", False),
                       ai_budget=cfg.get("ai_budget", "0"))
    rec = Recorder(mod, run_results=cfg.get("results", {}), unit_test=cfg.get("unit", (0, "", "")))

    import io as _io
    import contextlib
    buf_out, buf_err = _io.StringIO(), _io.StringIO()
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc = mod.run_project(dict(cfg["p"]), dry=cfg.get("dry", False),
                                 webhook=cfg.get("webhook", ""))
    finally:
        rec.restore()

    def norm(text):
        return _TS.sub("<TS>", text).replace(str(root), "<ROOT>")

    events = []
    for ev in rec.events:
        events.append(tuple(str(x).replace(str(root), "<ROOT>") for x in ev))

    return (rc, norm(buf_out.getvalue()), norm(buf_err.getvalue()),
            tuple(events), rec.ledger())


@pytest.fixture(scope="module")
def sources():
    """返回 (原版源码, 重构版源码)；两者相同时跳过等价比对。"""
    head = _head_source()
    new = SCRIPT.read_text(encoding="utf-8")
    return head, new


@pytest.mark.parametrize("name,cfg", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_run_project_equivalent_to_pre_refactor(name, cfg, tmp_path, sources, capsys):
    """重构版 run_project 与 git HEAD 版在相同场景下副作用完全一致。"""
    head, new = sources
    if head == new:
        pytest.skip("HEAD 与工作区一致（重构已入库），无需等价性比对")

    expected = _run_scenario(head, "orig_" + name, cfg, tmp_path)
    actual = _run_scenario(new, "new_" + name, cfg, tmp_path)

    labels = ("returncode", "stdout", "stderr", "events", "ledger")
    for label, exp, act in zip(labels, expected, actual):
        assert act == exp, (
            f"[{name}] {label} 不一致\n--- 重构前 ---\n{exp}\n--- 重构后 ---\n{act}")


@pytest.mark.parametrize("name,cfg", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_run_project_contract(name, cfg, tmp_path, sources):
    """行为契约：不依赖 git 历史，独立断言 run_project 的可观察行为。"""
    _, new = sources
    root = _make_root(
        tmp_path / ("c_" + name),
        desensitize=cfg.get("desensitize", True),
        dev_tools=DEV_TOOLS if cfg.get("dev_tools", True) else (),
    )
    mod = _load_module(new, f"nqgc_{name}", root,
                       ai_env=cfg.get("ai_env", False),
                       ai_budget=cfg.get("ai_budget", "0"))
    rec = Recorder(mod, run_results=cfg.get("results", {}), unit_test=cfg.get("unit", (0, "", "")))

    try:
        rc = mod.run_project(dict(cfg["p"]), dry=cfg.get("dry", False),
                             webhook=cfg.get("webhook", ""))
    finally:
        rec.restore()

    ledger = rec.ledger()
    kinds = {ev[0] for ev in rec.events}
    assert rc in (0, 1)

    if cfg.get("dry"):
        # dry-run 不得写台账、不得告警
        assert ledger == {}, f"dry-run 不应写台账，实际 {list(ledger)}"
        assert "notify" not in kinds
        return

    assert ledger.get("36_质量门记录.csv"), "非 dry-run 应写入 36_质量门记录.csv"
    has_fail = ",FAIL," in ledger.get("36_质量门记录.csv", "")
    has_pending = bool(ledger.get("39_待决策事项.csv"))
    # 自动视角 FAIL → 返回 1；否则 0（AI 视角不阻断）
    assert rc == (1 if has_fail else 0)
    # 存在 FAIL 或待决策项时才告警
    assert ("notify" in kinds) == (has_fail or has_pending)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
