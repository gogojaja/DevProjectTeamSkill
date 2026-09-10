#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
handoff_summarizer.py 重构等价性回归测试
========================================
背景：extract_l1_by_rules() 圈复杂度 36（含两个嵌套函数定义），按「切分 → 七节采集
      → 状态叠加 → 组装截断」拆分为 _split_subsections / _sub / _collect_* /
      _apply_state_overlay / _assemble_l1 等模块级函数。

验证方式：
  1) 差分等价：同一输入下 HEAD 版本与重构版本的返回字符串须逐字节一致。
  2) 行为契约：不依赖 HEAD 的长期断言（占位回退、去重限条、硬截断、状态叠加）。

可测性依据：extract_l1_by_rules 为纯函数（无 IO、无全局状态），可直接双版本导入比对。
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
REL_SCRIPT = "tools/handoff_summarizer.py"


# ---------------------------------------------------------------- 双版本加载

def _head_source():
    r = subprocess.run(["git", "show", "HEAD:" + REL_SCRIPT], cwd=str(REPO),
                       capture_output=True)
    if r.returncode != 0:
        pytest.skip("无法从 git HEAD 取基线版本：%s" % r.stderr.decode("utf-8", "replace"))
    return r.stdout.decode("utf-8")


def _work_source():
    return (REPO / REL_SCRIPT).read_text(encoding="utf-8")


def _load(src, name):
    p = Path(name + "_handoff_mod.py")
    p.write_text(src, encoding="utf-8")
    try:
        spec = importlib.util.spec_from_file_location(name, str(p.resolve()))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        p.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def both():
    """一次性加载 HEAD 与重构版本，供全部差分用例复用。"""
    head = _load(_head_source(), "hs_head")
    work = _load(_work_source(), "hs_work")
    yield head, work
    for n in ("hs_head", "hs_work"):
        sys.modules.pop(n, None)


# ---------------------------------------------------------------- 文档夹具

_L1_HEAD = "## 🔴 L1 必读核心\n"
_L2_HEAD = "## 🟡 L2 标准上下文\n"


def _doc(l1_body, with_l2=True, prefix="# 交接文档\n"):
    tail = _L2_HEAD + "L2 内容行（不应进入摘要）\n" if with_l2 else ""
    return prefix + _L1_HEAD + l1_body + tail


def _sub(title, *lines):
    return "### %s\n%s\n" % (title, "\n".join(lines))


FULL_L1 = (
    _sub("项目速览", "TwinForge 双机工作站", "本地部署架构管理", "涉密信息管理")
    + _sub("当前阶段/角色/任务", "阶段：开发", "角色：role-development")
    + _sub("关键风险/阻塞", "- 无阻塞项", "- Mac mini 链路待恢复")
    + _sub("下一步唯一动作", "- 执行两层评审验证")
    + _sub("铁律锚点", "- 授权 → 备份 → 留痕")
    + _sub("关键文件索引",
           "| 文件 | 说明 |",
           "| `scripts/review_all.py` | 静态评审 |",
           "| `scripts/review_deep.py` | AST 评审 |")
)

# 别名子节：风险/阻塞、下一步动作、当前角色
ALIAS_L1 = (
    _sub("项目速览", "别名场景速览")
    + _sub("当前角色", "role-governance")
    + _sub("风险/阻塞", "- 别名风险项一条")
    + _sub("下一步动作", "- 别名动作项一条")
)

# 旧格式：无子节，阶段信息以散行存在于 L1 区
LEGACY_L1 = (
    "当前阶段：投产\n"
    "当前任务：发布准备\n"
    "当前任务类型：轻量\n"
    "无关散行内容\n"
)

# 含四级子标题（应转为加粗内容行）
H4_L1 = _sub("项目速览", "#### 速览细项A", "普通行", "#### 速览细项B")

# 空 L1 区
EMPTY_L1 = ""

# 重复行 + 超限行数（验证 dedupe_lines 限条）
DUP_L1 = (_sub("项目速览", *(["重复行"] * 12))
          + _sub("铁律锚点", *["- 铁律%d" % i for i in range(12)]))

# 风险行过滤：长度 ≤4 的行被丢弃
# （注：以 "### " 开头的行在 _split_subsections 阶段已被当作新子节标题，
#   不会进入本节内容，故此处仅验证长度过滤）
RISK_FILTER_L1 = _sub("关键风险/阻塞", "短行", "- 有效风险项内容")

# 动作行过滤：长度 ≤3
ACTION_FILTER_L1 = _sub("下一步唯一动作", "ab", "- 有效动作项内容")

# 文件索引过滤：非 | 开头 / 无反引号 / 超过 5 条
FILE_FILTER_L1 = _sub(
    "关键文件索引",
    "非表格行",
    "| 无反引号行 |",
    *["| `f%d.py` | 说明 |" % i for i in range(8)],
)

# 文件索引全部被过滤 → 回退占位
FILE_EMPTY_L1 = _sub("关键文件索引", "非表格行", "| 无反引号 |")

# 超长文档（触发 3000 字符硬截断）—— 需绕过各节限条后仍超限，
# 故用 6 条（项目速览上限）+ 6 条（铁律锚点上限）各 400 字的长行
_LONG_LINE = "长" * 400
HUGE_L1 = (
    _sub("项目速览", *["速览%02d %s" % (i, _LONG_LINE) for i in range(6)])
    + _sub("铁律锚点", *["铁律%02d %s" % (i, _LONG_LINE) for i in range(6)])
)

# 无 L1/L2 标记 → extract_l1_zone 退化为全文前 500 行
NO_MARKER_DOC = "# 无标记文档\n" + _sub("项目速览", "退化区速览行") + "\n".join(
    "填充行%03d" % i for i in range(600))

STATES = {
    "none": {},
    "stage_only": {"current_stage": "开发"},
    "role_only": {"current_role": "role-development"},
    "task_only": {"current_task": "补充规则"},
    "all_three": {"current_stage": "开发", "current_role": "role-development",
                  "current_task": "补充规则"},
    "changes_only": {"changes_summary": "重构 5 个工具"},
    "changes_long": {"changes_summary": "长" * 400},
    "full": {"current_stage": "投产", "current_role": "role-deployment",
             "current_task": "发布", "changes_summary": "全量状态"},
    "falsy_values": {"current_stage": "", "current_role": None,
                     "current_task": 0, "changes_summary": ""},
}

DOC_CASES = {
    "full": FULL_L1,
    "alias": ALIAS_L1,
    "legacy_scattered": LEGACY_L1,
    "h4_headings": H4_L1,
    "empty_zone": EMPTY_L1,
    "dup_and_limit": DUP_L1,
    "risk_filter": RISK_FILTER_L1,
    "action_filter": ACTION_FILTER_L1,
    "file_filter": FILE_FILTER_L1,
    "file_empty": FILE_EMPTY_L1,
    "huge_truncate": HUGE_L1,
}


# ---------------------------------------------------------------- 差分等价

@pytest.mark.parametrize("doc_label", sorted(DOC_CASES), ids=sorted(DOC_CASES))
@pytest.mark.parametrize("state_label", sorted(STATES), ids=sorted(STATES))
def test_extract_l1_matches_head(both, doc_label, state_label):
    """重构版与 HEAD 版对相同 (文档, 状态) 的输出须逐字节一致。"""
    head, work = both
    doc = _doc(DOC_CASES[doc_label])
    state = STATES[state_label]
    h = head.extract_l1_by_rules(doc, dict(state))
    w = work.extract_l1_by_rules(doc, dict(state))
    assert h == w, "[%s/%s] 输出不一致:\n--- head ---\n%s\n--- work ---\n%s" % (
        doc_label, state_label, h, w)


@pytest.mark.parametrize("label,doc", [
    ("no_marker", NO_MARKER_DOC),
    ("no_l2_tail", _doc(FULL_L1, with_l2=False)),
    ("empty_string", ""),
    ("no_prefix", _L1_HEAD + FULL_L1 + _L2_HEAD),
], ids=["no_marker", "no_l2_tail", "empty_string", "no_prefix"])
def test_zone_edge_cases_match_head(both, label, doc):
    """L1 区提取的边界形态（无标记 / 无 L2 尾 / 空串 / 无前缀）须一致。"""
    head, work = both
    assert head.extract_l1_by_rules(doc, {}) == work.extract_l1_by_rules(doc, {}), label


def test_real_handoff_doc_matches_head(both):
    """以仓库真实交接文档为输入，输出须一致（端到端最强证据）。"""
    head, work = both
    doc_path = REPO / "交接文档.md"
    if not doc_path.exists():
        pytest.skip("仓库无交接文档.md")
    doc = doc_path.read_text(encoding="utf-8")
    assert head.extract_l1_by_rules(doc, {}) == work.extract_l1_by_rules(doc, {})
    state = {"current_stage": "开发", "current_role": "role-development",
             "current_task": "技术债治理", "changes_summary": "重构 extract_l1_by_rules"}
    assert head.extract_l1_by_rules(doc, state) == work.extract_l1_by_rules(doc, state)


# ---------------------------------------------------------------- 行为契约

class TestContract:
    """不依赖 HEAD 的长期契约断言（防回弹）。"""

    @pytest.fixture(autouse=True)
    def _mod(self, both):
        self.mod = both[1]

    def _run(self, l1_body, state=None, **kw):
        return self.mod.extract_l1_by_rules(_doc(l1_body, **kw), state or {})

    def test_all_sections_in_fixed_order(self):
        out = self._run(FULL_L1)
        titles = [ln[4:] for ln in out.split("\n") if ln.startswith("### ")]
        assert titles == ["项目速览", "当前阶段/角色/任务", "关键风险/阻塞",
                          "下一步唯一动作", "铁律锚点", "关键文件索引"]

    def test_placeholders_when_sections_missing(self):
        out = self._run(EMPTY_L1)
        assert "- **无阻塞项**" in out
        assert "- 待定" in out
        assert "- **核心**：授权 → 备份 → 留痕" in out
        assert "- 见 L2 完整索引" in out

    def test_empty_zone_still_returns_placeholders(self):
        """空 L1 区也必须产出四节占位，不得返回空串。"""
        assert self._run(EMPTY_L1).strip()

    def test_aliases_resolved(self):
        out = self._run(ALIAS_L1)
        assert "别名风险项一条" in out and "别名动作项一条" in out
        assert "role-governance" in out

    def test_legacy_scattered_stage_lines(self):
        out = self._run(LEGACY_L1)
        assert "当前阶段：投产" in out and "当前任务：发布准备" in out
        assert "无关散行内容" not in out

    def test_h4_becomes_bold_content(self):
        out = self._run(H4_L1)
        assert "- **速览细项A**" in out and "- **速览细项B**" in out

    def test_dedupe_and_limit(self):
        out = self._run(DUP_L1)
        assert out.count("重复行") == 1
        # 项目速览限 6 条、铁律锚点限 6 条
        assert "- 铁律6" not in out and "- 铁律5" in out

    def test_risk_line_filter(self):
        out = self._run(RISK_FILTER_L1)
        assert "有效风险项内容" in out and "短行" not in out

    def test_action_line_filter(self):
        out = self._run(ACTION_FILTER_L1)
        assert "有效动作项内容" in out

    def test_file_index_filter_and_cap(self):
        out = self._run(FILE_FILTER_L1)
        assert "`f0.py`" in out and "`f4.py`" in out and "`f5.py`" not in out
        assert "非表格行" not in out and "无反引号行" not in out

    def test_hard_truncate_over_3000(self):
        out = self._run(HUGE_L1)
        assert len(out) <= 3100
        assert "摘要超限，已裁剪" in out

    def test_no_marker_falls_back_to_head_500_lines(self):
        out = self.mod.extract_l1_by_rules(NO_MARKER_DOC, {})
        assert "退化区速览行" in out

    def test_l2_content_never_leaks(self):
        assert "L2 内容行" not in self._run(FULL_L1)

    @pytest.mark.parametrize("state_label", sorted(STATES), ids=sorted(STATES))
    def test_state_overlay(self, state_label):
        state = STATES[state_label]
        out = self._run(FULL_L1, state)
        if state.get("current_stage"):
            assert "- **当前阶段**：%s" % state["current_stage"] in out
        if state.get("current_role"):
            assert "- **当前角色**：%s" % state["current_role"] in out
        if state.get("current_task"):
            assert "- **当前任务**：%s" % state["current_task"] in out
        if state.get("changes_summary"):
            assert "本轮变更" in out
            assert state["changes_summary"][:200] in out
        if not any(state.get(k) for k in
                   ("current_stage", "current_role", "current_task", "changes_summary")):
            assert "本轮变更" not in out

    def test_state_overlay_appends_to_existing_stage_section(self):
        """已有「当前阶段/角色/任务」子节时，state 内容应追加而非新建小节。"""
        out = self._run(FULL_L1, {"current_stage": "投产"})
        assert out.count("### 当前阶段/角色/任务") == 1
        assert "- **当前阶段**：投产" in out

    def test_state_overlay_creates_section_when_absent(self):
        """子节缺失但 state 有值时，应新建该小节（置于固定顺序位）。"""
        out = self._run(_sub("项目速览", "仅速览"), {"current_role": "role-testing"})
        assert "### 当前阶段/角色/任务" in out
        assert "- **当前角色**：role-testing" in out

    def test_changes_summary_truncated_to_200(self):
        out = self._run(FULL_L1, {"changes_summary": "长" * 400})
        assert "长" * 200 in out and "长" * 201 not in out

    def test_pure_function_no_input_mutation(self):
        """state 入参不得被修改（多次调用结果稳定）。"""
        state = {"current_stage": "开发", "changes_summary": "x"}
        snapshot = dict(state)
        first = self._run(FULL_L1, state)
        second = self._run(FULL_L1, state)
        assert state == snapshot
        assert first == second
