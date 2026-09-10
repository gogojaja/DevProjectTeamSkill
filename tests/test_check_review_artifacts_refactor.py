#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_review_artifacts.py 重构等价性回归测试
============================================
背景：main() 圈复杂度 33 / 96 行，按「目标分离 → 三项检查 → 汇总 → 输出」拆分为
      split_review_targets / check_report_present / check_evidence_and_mode /
      check_hard_blockers / summarize_problems / emit_result 六个阶段函数。

验证方式：
  1) 差分等价：同一沙箱夹具下，分别执行 HEAD 版本与重构版本，
     stdout / stderr / 退出码须逐字节一致（重构不得改变门禁语义）。
  2) 行为契约：不依赖 HEAD 的长期断言，防止后续回弹。

沙箱化依据：ROOT 取自环境变量 PROJECT_ROOT，故可用临时目录完全隔离。
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
REL_SCRIPT = "tools/check_review_artifacts.py"
WORK_SCRIPT = REPO / REL_SCRIPT


# ---------------------------------------------------------------- 双版本源码

def _head_source():
    """取 git HEAD 版本源码（重构前基线）。"""
    r = subprocess.run(["git", "show", "HEAD:" + REL_SCRIPT], cwd=str(REPO),
                       capture_output=True)
    if r.returncode != 0:
        pytest.skip("无法从 git HEAD 取基线版本：%s" % r.stderr.decode("utf-8", "replace"))
    return r.stdout.decode("utf-8")


def _work_source():
    return WORK_SCRIPT.read_text(encoding="utf-8")


# ---------------------------------------------------------------- docx 无关，纯文本夹具

def _mkdocs(root: Path, specs):
    """在沙箱内构造 docs/ 文本文件。specs: {相对路径: 内容}"""
    for rel, content in specs.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def _run(src, tag, sandbox: Path, cli=()):
    """在沙箱 PROJECT_ROOT 下执行指定版本脚本，返回 (rc, stdout, stderr)。"""
    script = sandbox.parent / ("cra_%s.py" % tag)
    script.write_text(src, encoding="utf-8")
    env = dict(os.environ)
    env["PROJECT_ROOT"] = str(sandbox)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, str(script), *cli], cwd=str(sandbox),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    # 脚本名出现在 usage/traceback 中时会造成伪差异，统一归一化
    return r.returncode, r.stdout.replace(script.name, "SCRIPT"), \
        r.stderr.replace(script.name, "SCRIPT")


# ---------------------------------------------------------------- 夹具场景
# 说明：check_report_present 的匹配规则为
#   basename(文档)[:6] 去下划线小写 命中报告名，或报告名含「评审」
# 故「缺报告」场景必须使用不含「评审」二字的报告名。

_DOC_FULL_OK = """# 方案文档
评审模式：多视角自评
真实外部信号：实测核验 1 条
决策记录：SIGNED_OFF
证据卡：docs/evidence_cards_arch_20260901.json
"""

_DOC_MISSING_REPORT = """# 方案
评审模式：真实第三方
外部信号：官方文档核验
决策记录：SIGNED_OFF
"""

_DOC_TMP_LINK = """# 方案
评审模式：自评
外部信号：实测
决策记录：CHANGES_REQUESTED
证据留存：/tmp/ev_123.json
"""

_DOC_UNREACHABLE_EV = """# 方案
评审模式：自评
外部信号：工具核验
评审结论：BLOCKED
详见 evidence_cards_missing_20260901.json
"""

_DOC_NO_MODE = """# 方案
决策记录：SIGNED_OFF
"""

_DOC_NO_SIGNAL = """# 方案
评审模式：自评
决策记录：SIGNED_OFF
"""

_DOC_NO_DECISION = """# 纯规则文档
无任何评审相关内容。
"""

SCENARIOS = {
    # 无 docs/ 目录 → 前向兼容通过
    "empty_root": dict(docs={}, reports=[], evidence=[]),
    # docs 存在但无评审结论 → 前向兼容通过
    "no_reviewed_doc": dict(
        docs={"docs/plan.md": _DOC_NO_DECISION}, reports=[], evidence=[]),
    # 完整合规 → 门禁通过
    "all_present": dict(
        docs={"docs/架构方案.md": _DOC_FULL_OK},
        reports=["docs/reviews/评审报告_架构_v1.csv"],
        evidence=["docs/evidence_cards_arch_20260901.json"]),
    # 显式评审但无报告 CSV → 硬阻断（报告名不含「评审」且前缀不命中）
    "missing_report": dict(
        docs={"docs/zzz方案.md": _DOC_MISSING_REPORT},
        reports=["docs/reviews/other_file.csv"],
        evidence=["docs/evidence_cards_x.json"]),
    # /tmp 挂链 → 硬阻断
    "tmp_link": dict(
        docs={"docs/aaa方案.md": _DOC_TMP_LINK},
        reports=["docs/reviews/评审报告_aaa.csv"],
        evidence=["docs/evidence_cards_x.json"]),
    # 证据卡引用不可达 → 硬阻断
    "unreachable_ev": dict(
        docs={"docs/bbb方案.md": _DOC_UNREACHABLE_EV},
        reports=["docs/reviews/评审报告_bbb.csv"],
        evidence=["docs/evidence_cards_other.json"]),
    # 缺评审模式申明 → 仅软性提示
    "no_mode": dict(
        docs={"docs/ccc方案.md": _DOC_NO_MODE},
        reports=["docs/reviews/评审报告_ccc.csv"],
        evidence=["docs/evidence_cards_x.json"]),
    # 缺外部信号 → 仅软性提示
    "no_signal": dict(
        docs={"docs/ddd方案.md": _DOC_NO_SIGNAL},
        reports=["docs/reviews/评审报告_ddd.csv"],
        evidence=["docs/evidence_cards_x.json"]),
    # 无证据卡入库 → 仅软性提示
    "no_evidence": dict(
        docs={"docs/eee方案.md": _DOC_NO_SIGNAL},
        reports=["docs/reviews/评审报告_eee.csv"],
        evidence=[]),
    # 多文档混合：一处硬阻断 + 多处软性提示
    "mixed": dict(
        docs={
            "docs/m1方案.md": _DOC_FULL_OK,
            "docs/m2方案.md": _DOC_TMP_LINK,
            "docs/m3方案.md": _DOC_NO_MODE,
            "docs/sub/m4方案.md": _DOC_UNREACHABLE_EV,
        },
        reports=["docs/reviews/评审报告_m1.csv"],
        evidence=["docs/evidence_cards_arch_20260901.json"]),
    # 报告位于项目根（非 docs/reviews/）
    "report_in_root": dict(
        docs={"docs/fff方案.md": _DOC_MISSING_REPORT},
        reports=["评审报告_fff.csv"],
        evidence=["docs/evidence_cards_x.json"]),
}


def _build_sandbox(sandbox: Path, case):
    if sandbox.exists():
        shutil.rmtree(str(sandbox), ignore_errors=True)
    sandbox.mkdir(parents=True)
    _mkdocs(sandbox, case["docs"])
    for rel in case["reports"]:
        p = sandbox / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("role,verdict\nA,SIGNED_OFF\n", encoding="utf-8-sig")
    for rel in case["evidence"]:
        p = sandbox / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
    return sandbox


# ---------------------------------------------------------------- 差分等价

@pytest.mark.parametrize("label", sorted(SCENARIOS), ids=sorted(SCENARIOS))
@pytest.mark.parametrize("cli", [[], ["--scan"]], ids=["gate", "scan"])
def test_matches_head(tmp_path, label, cli):
    """重构版与 HEAD 版在相同夹具下的 stdout/stderr/退出码须逐字节一致。"""
    head_src, work_src = _head_source(), _work_source()
    case = SCENARIOS[label]

    sb_h = _build_sandbox(tmp_path / "sb_head", case)
    h = _run(head_src, "head", sb_h, cli)
    sb_w = _build_sandbox(tmp_path / "sb_work", case)
    w = _run(work_src, "work", sb_w, cli)

    assert h[0] == w[0], "[%s%s] 退出码不一致 head=%s work=%s\n%s\n%s" % (
        label, cli, h[0], w[0], h[1], w[1])
    assert h[1] == w[1], "[%s%s] stdout 不一致:\n--- head ---\n%s\n--- work ---\n%s" % (
        label, cli, h[1], w[1])
    assert h[2] == w[2], "[%s%s] stderr 不一致:\n--- head ---\n%s\n--- work ---\n%s" % (
        label, cli, h[2], w[2])


# ---------------------------------------------------------------- 截断上限差分

def _many(label, doc_tpl, n_docs, reports, evidence):
    """构造多文档场景，验证 [:8] / [:5] 截断行为一致。"""
    docs = {}
    for i in range(n_docs):
        docs["docs/%s" % (doc_tpl % i)] = {
            "ev": _DOC_UNREACHABLE_EV.replace(
                "evidence_cards_missing_20260901.json",
                "evidence_cards_miss%d.json" % i),
            "report": _DOC_MISSING_REPORT,
        }[label]
    return dict(docs=docs, reports=reports, evidence=evidence)


@pytest.mark.parametrize("label,tpl,n", [
    ("ev", "d%02d方案.md", 12),
    ("report", "r%02d方案.md", 9),
])
def test_truncation_limits_match_head(tmp_path, label, tpl, n):
    """证据卡不可达列表截断 8 条、缺报告文档列表截断 5 条，须与 HEAD 一致。"""
    case = _many(label, tpl, n,
                 reports=["docs/reviews/x%d.csv" % i for i in range(n)],
                 evidence=["docs/evidence_cards_x.json"])
    sb_h = _build_sandbox(tmp_path / "t_head", case)
    h = _run(_head_source(), "thead", sb_h)
    sb_w = _build_sandbox(tmp_path / "t_work", case)
    w = _run(_work_source(), "twork", sb_w)
    assert h == w, "截断行为不一致:\n--- head ---\n%s\n%s\n--- work ---\n%s\n%s" % (
        h[1], h[2], w[1], w[2])
    assert h[0] == 1


# ---------------------------------------------------------------- 行为契约

class TestContract:
    """不依赖 HEAD 的长期契约断言。"""

    def _exec(self, tmp_path, tag, case, cli=()):
        sb = _build_sandbox(tmp_path / tag, case)
        return _run(_work_source(), tag, sb, cli)

    def test_no_docs_passes(self, tmp_path):
        rc, out, _ = self._exec(tmp_path, "c_empty", SCENARIOS["empty_root"])
        assert rc == 0 and "前向兼容" in out

    def test_compliant_passes(self, tmp_path):
        rc, out, err = self._exec(tmp_path, "c_ok", SCENARIOS["all_present"])
        assert rc == 0, err
        assert "门禁通过" in out and "软性提示" not in out

    def test_missing_report_blocks(self, tmp_path):
        rc, _, err = self._exec(tmp_path, "c_mr", SCENARIOS["missing_report"])
        assert rc == 1 and "未找到评审报告 CSV" in err

    def test_tmp_link_blocks(self, tmp_path):
        rc, _, err = self._exec(tmp_path, "c_tmp", SCENARIOS["tmp_link"])
        assert rc == 1 and "/tmp 挂链" in err

    def test_unreachable_evidence_blocks(self, tmp_path):
        rc, _, err = self._exec(tmp_path, "c_ev", SCENARIOS["unreachable_ev"])
        assert rc == 1 and "证据卡引用不可达" in err

    def test_scan_mode_never_blocks(self, tmp_path):
        for label in ("missing_report", "tmp_link", "unreachable_ev"):
            rc, out, err = self._exec(tmp_path, "c_scan_" + label,
                                      SCENARIOS[label], ["--scan"])
            assert rc == 0, "%s 在 --scan 下不应阻断" % label
            assert "--scan 模式" in out
            assert "门禁未通过" in err

    def test_soft_warnings_do_not_block(self, tmp_path):
        for label in ("no_mode", "no_signal", "no_evidence"):
            rc, out, _ = self._exec(tmp_path, "c_soft_" + label, SCENARIOS[label])
            assert rc == 0, "%s 仅应产生软性提示" % label
            assert "软性提示" in out

    def test_report_in_root_satisfies_gate(self, tmp_path):
        """报告 CSV 置于项目根（非 docs/reviews/）同样应被识别。"""
        rc, _, err = self._exec(tmp_path, "c_root", SCENARIOS["report_in_root"])
        assert rc == 0, err
