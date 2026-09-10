#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
remove_watermark.py 重构回归测试
================================

背景：tools/remove_watermark/remove_watermark.py 的 main() 原为 127 行 / 圈复杂度 40，
process_word() 原为 52 行 / 圈复杂度 33（DEEP-CMP-001 SEVERE 级技术债）。已拆分为：
  - process_word → _ancestor_paragraph / _collect_textpath_paras / _is_watermark_shape /
    _collect_pict_paras / _strip_paragraphs / _process_word_part
  - main         → _build_parser / _resolve_target / _parse_rects / _resolve_text_exts /
    _collect_files / _should_skip / _resolve_work_path / _process_one /
    _write_report / _print_summary

本测试的重点是**差分等价**：把 git HEAD 版本与工作区版本放在同一路径沙箱上先后执行，
比对 stdout / 退出码 / 产物字节，确保拆分只是结构变化、语义零漂移。
  1. CLI 端到端差分：文本夹具树 × 15 组参数组合（--auto / --text / --dry-run /
     --in-place / -o / --report / --include-ext / --format / 参数错误路径）。
  2. process_word 差分：本机无 lxml，故注入**同一份 lxml 桩件**到两个版本，
     用真实 zip(docx) 夹具比对删除段落数、结果说明与回写后的 zip 成员字节。
  3. 行为契约：新增私有函数的边界语义（扩展名补点、目录遍历过滤、rect 解析、
     输出路径解析、汇总退出码）。

运行：python -m pytest tests/test_remove_watermark_refactor.py -q
"""

import io
import os
import shutil
import subprocess
import sys
import types
import xml.etree.ElementTree as ET
import zipfile
from contextlib import contextmanager
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_REL = "tools/remove_watermark/remove_watermark.py"
SCRIPT = REPO_ROOT / SCRIPT_REL

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


# ---------------------------------------------------------------- 版本源码

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


def _both_sources():
    """返回 (head, work) 源码；两者一致时跳过差分。"""
    head, work = _head_source(), _work_source()
    if head == work:
        pytest.skip("HEAD 与工作区一致（重构已提交），无需差分对比")
    return head, work


def _load(src, name):
    """把源码 exec 成独立模块（不注册到 sys.modules，避免污染其他测试）。"""
    mod = types.ModuleType(name)
    mod.__file__ = str(SCRIPT)
    exec(compile(src, str(SCRIPT), "exec"), mod.__dict__)  # nosec: 测试装载，src 读自本地被测脚本(SCRIPT)非外部输入
    return mod


# ---------------------------------------------------------------- lxml 桩件
# 本机未安装 lxml，而 process_word 的水印识别逻辑全部依赖 lxml 接口。
# 桩件只实现被用到的子集（fromstring / tostring / getparent / findall / find /
# iter / remove / get），足以驱动真实分支；两个版本注入**同一份**桩件，
# 因此产物差异只可能来自重构本身。

class _FakeEl:
    """lxml 元素的最小子集实现（带父指针，支持文档序遍历）。"""

    def __init__(self, tag, attrib=None, parent=None):
        self.tag = tag
        self.attrib = dict(attrib or {})
        self.text = None
        self.tail = None
        self._parent = parent
        self._children = []

    def get(self, key, default=None):
        return self.attrib.get(key, default)

    def getparent(self):
        return self._parent

    def append(self, child):
        child._parent = self
        self._children.append(child)

    def remove(self, child):
        self._children.remove(child)

    def _descendants(self):
        for c in self._children:
            yield c
            for g in c._descendants():
                yield g

    def findall(self, path):
        tag = path.split("//")[-1]
        return [n for n in self._descendants() if n.tag == tag]

    def find(self, path):
        tag = path.split("//")[-1]
        for n in self._descendants():
            if n.tag == tag:
                return n
        return None

    def iter(self, tag=None):
        if tag is None or self.tag == tag:
            yield self
        for n in self._descendants():
            if tag is None or n.tag == tag:
                yield n


def _from_et(el, parent=None):
    """把标准库 ElementTree 节点递归转成桩件节点。"""
    node = _FakeEl(el.tag, el.attrib, parent)
    node.text = el.text
    node.tail = el.tail
    for ch in el:
        node.append(_from_et(ch, node))
    return node


def _esc(s):
    """转义文本节点中的 XML 特殊字符。"""
    if not s:
        return ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _serialize(el):
    """确定性序列化：属性按名排序，保留文本与 tail（供内容级断言使用）。"""
    attrs = "".join(' %s="%s"' % (k, v) for k, v in sorted(el.attrib.items()))
    text = _esc(el.text)
    tail = _esc(el.tail)
    if el._children:
        inner = text + "".join(_serialize(c) for c in el._children)
        return "<%s%s>%s</%s>%s" % (el.tag, attrs, inner, el.tag, tail)
    if text:
        return "<%s%s>%s</%s>%s" % (el.tag, attrs, text, el.tag, tail)
    return "<%s%s/>%s" % (el.tag, attrs, tail)


class _FakeEtree:
    """lxml.etree 桩件：fromstring / tostring / XMLParser。"""

    @staticmethod
    def fromstring(data):
        s = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
        return _from_et(ET.fromstring(s))

    @staticmethod
    def tostring(root, xml_declaration=False, encoding=None, standalone=None):
        prefix = "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" if xml_declaration else ""
        return (prefix + _serialize(root)).encode("utf-8")

    @staticmethod
    def XMLParser(**kwargs):
        return None


@contextmanager
def _fake_lxml():
    """临时把 lxml 桩件注入 sys.modules，退出时还原（含真实 lxml 存在的情况）。"""
    saved = sys.modules.get("lxml")
    fake = types.ModuleType("lxml")
    fake.etree = _FakeEtree
    sys.modules["lxml"] = fake
    try:
        yield fake
    finally:
        if saved is None:
            sys.modules.pop("lxml", None)
        else:
            sys.modules["lxml"] = saved


# ---------------------------------------------------------------- docx 夹具

_DOC_HEAD = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:document xmlns:w="%s" xmlns:v="%s" xmlns:o="%s" xmlns:r="%s">'
    "<w:body>" % (NS["w"], NS["v"], NS["o"], NS["r"])
)
_DOC_TAIL = "</w:body></w:document>"


def _textpath_shape(wm_text, shape_id="PowerPlusWaterMarkObject1"):
    """构造含 v:textpath 的文字水印形状（真实 docx 页眉水印结构）。"""
    return (
        '<w:p><w:r><w:pict>'
        '<v:shape id="%s" o:spid="_x0000_s1025" style="position:absolute">'
        '<v:textpath string="%s" style="font-family:SimSun"/>'
        '<o:lock v:ext="edit" rotation="t" title="watermark picture"/>'
        "</v:shape></w:pict></w:r></w:p>" % (shape_id, wm_text)
    )


def _pict_only_shape(shape_id="PowerPlusWaterMarkObject2"):
    """构造仅含图片水印（无 v:textpath）的形状，用于驱动 picture 分支。"""
    return (
        '<w:p><w:r><w:pict>'
        '<v:shape id="%s" o:spid="_x0000_s1026" style="position:absolute">'
        '<v:imagedata r:id="rId9" o:title="watermark picture"/>'
        "</v:shape></w:pict></w:r></w:p>" % shape_id
    )


def _plain_shape(shape_id="NormalShape"):
    """构造非水印形状（id/name 均不含 Watermark/水印），不得被删除。"""
    return (
        '<w:p><w:r><w:pict>'
        '<v:shape id="%s" o:spid="_x0000_s1027">'
        '<v:imagedata r:id="rId8" o:title="logo picture"/>'
        "</v:shape></w:pict></w:r></w:p>" % shape_id
    )


def _para(text):
    return "<w:p><w:r><w:t>%s</w:t></w:r></w:p>" % text


def _header_xml(body_inner):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:hdr xmlns:w="%s" xmlns:v="%s" xmlns:o="%s" xmlns:r="%s">'
            "%s</w:hdr>" % (NS["w"], NS["v"], NS["o"], NS["r"], body_inner))


def _build_docx(path: Path, document_body, header_body=None, footer_body=None):
    """构造最小 docx（zip）夹具：Content_Types + document + 可选页眉/页脚。"""
    members = {
        "[Content_Types].xml": b'<?xml version="1.0"?><Types/>',
        "word/document.xml": (_DOC_HEAD + document_body + _DOC_TAIL).encode("utf-8"),
    }
    if header_body is not None:
        members["word/header1.xml"] = _header_xml(header_body).encode("utf-8")
    if footer_body is not None:
        members["word/footer1.xml"] = _header_xml(footer_body).encode("utf-8")
    # 无水印标记的部件，用于验证 textpath/picture 前置过滤
    members["word/styles.xml"] = (
        '<?xml version="1.0"?><w:styles xmlns:w="%s"/>' % NS["w"]).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return path


def _zip_members(path: Path) -> dict:
    """读取 zip 全部成员字节，供产物比对。"""
    if not path.exists():
        return {}
    with zipfile.ZipFile(str(path)) as z:
        return {n: z.read(n) for n in z.namelist()}


# ---------------------------------------------------------------- 文本夹具

STAMP_LINE = "内部资料"
TAIL_MARK = "内部资料 勿外传"


def _make_text_tree(base: Path) -> Path:
    """构造文本夹具树：印章整行、行尾短语、高频重复行、非文本扩展名、子目录。"""
    base.mkdir(parents=True, exist_ok=True)
    (base / "notes.md").write_text(
        "# 标题\n\n%s\n\n正文第一段。\n\n正文第二段%s\n\n结尾。\n" % (STAMP_LINE, TAIL_MARK),
        encoding="utf-8")
    (base / "plain.txt").write_text(
        "无水印的普通文本。\n第二行。\n第三行。\n", encoding="utf-8")
    (base / "stamped.log").write_text(
        "机密\n机密\n机密\n真实日志内容一行。\n", encoding="utf-8")
    (base / "data.csv").write_text(
        "a,b,c\n1,2,3\n%s\n" % STAMP_LINE, encoding="utf-8")
    (base / "app.conf").write_text(
        "key=value\n%s\n" % STAMP_LINE, encoding="utf-8")
    (base / "binary.dat").write_bytes(b"\x00\x01\x02\xff\xfe")
    sub = base / "sub"
    sub.mkdir()
    (sub / "deep.md").write_text("深层文件\n%s\n" % STAMP_LINE, encoding="utf-8")
    skip = base / ".git"
    skip.mkdir()
    (skip / "ignored.md").write_text("%s\n" % STAMP_LINE, encoding="utf-8")
    return base


def _tree_bytes(root: Path) -> dict:
    """快照目录树：相对路径 → 字节内容（跳过链接）。"""
    out = {}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            continue
        rel = p.relative_to(root).as_posix()
        out[rel] = "<dir>" if p.is_dir() else p.read_bytes()
    return out


# ================================================================ CLI 端到端差分

CLI_SCENARIOS = [
    ("auto_inplace", ["stamped.log", "--auto", "--in-place"]),
    ("text_inplace", ["notes.md", "--text", STAMP_LINE, "--in-place"]),
    ("text_tail", ["notes.md", "--text", TAIL_MARK, "--in-place"]),
    ("text_no_match", ["plain.txt", "--text", "不存在的水印", "--in-place"]),
    ("dir_auto_out", [".", "--auto", "-o", "out"]),
    ("dir_text_out", [".", "--text", STAMP_LINE, "-o", "out"]),
    ("dir_dry_run", [".", "--auto", "--dry-run"]),
    ("dir_report", [".", "--auto", "-o", "out", "--report", "r.csv"]),
    ("dir_include_ext", [".", "--text", STAMP_LINE, "-o", "out",
                         "--include-ext", "conf,properties"]),
    ("dir_include_ext_dotted", [".", "--text", STAMP_LINE, "-o", "out",
                                "--include-ext", ".conf"]),
    ("dir_include_ext_empty", [".", "--text", STAMP_LINE, "-o", "out",
                                "--include-ext", "a,,b"]),
    ("force_format_text", ["binary.dat", "--format", "text", "--auto", "-o", "out"]),
    ("single_default_out", ["notes.md", "--text", STAMP_LINE]),
    ("rect_ok", ["notes.md", "--text", STAMP_LINE, "-o", "out",
                 "--rect", "0.1,0.2,0.3,0.4"]),
    ("subdir_only", ["sub", "--text", STAMP_LINE, "-o", "out2"]),
]


@pytest.mark.parametrize("label,cli", CLI_SCENARIOS, ids=[c[0] for c in CLI_SCENARIOS])
def test_cli_matches_head(tmp_path, label, cli):
    """重构后 CLI 的 stdout / 退出码 / 产物树须与 HEAD 版本逐字节一致。"""
    head_src, work_src = _both_sources()
    sandbox = tmp_path / "sb"          # 两版复用同一路径，避免绝对路径造成伪差异

    runs = []
    for tag, src in (("head", head_src), ("work", work_src)):
        if sandbox.exists():
            shutil.rmtree(str(sandbox), ignore_errors=True)
        fixture = _make_text_tree(sandbox)
        script = tmp_path / f"rw_{tag}.py"
        script.write_text(src, encoding="utf-8")
        r = subprocess.run([sys.executable, str(script), *cli], cwd=str(fixture),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        runs.append((r.returncode, r.stdout, r.stderr, _tree_bytes(fixture)))

    (h_rc, h_out, h_err, h_tree), (w_rc, w_out, w_err, w_tree) = runs
    assert h_rc == w_rc, f"[{label}] 退出码不一致 head={h_rc} work={w_rc}\nstderr={w_err}"
    assert h_out == w_out, f"[{label}] stdout 不一致:\n{_first_diff(h_out, w_out)}"
    assert h_tree == w_tree, (
        f"[{label}] 产物树不一致:\n" + "\n".join(
            "  %s: head=%r work=%r" % (k, h_tree.get(k), w_tree.get(k))
            for k in sorted(set(h_tree) | set(w_tree)) if h_tree.get(k) != w_tree.get(k)))


ERROR_SCENARIOS = [
    ("no_target", [], 2),
    ("mutex_inplace_output", ["notes.md", "--in-place", "-o", "out"], 2),
    ("target_missing", ["nope.md", "--auto"], 2),
    ("rect_bad_count", ["notes.md", "--rect", "1,2,3"], 2),
    ("rect_not_number", ["notes.md", "--rect", "a,b,c,d"], 1),
    ("bad_corner", ["notes.md", "--corner", "xx"], 2),
    ("bad_fill", ["notes.md", "--fill", "xx"], 2),
    ("bad_format", ["notes.md", "--format", "xx"], 2),
]


@pytest.mark.parametrize("label,cli,expect_rc", ERROR_SCENARIOS,
                         ids=[c[0] for c in ERROR_SCENARIOS])
def test_cli_error_paths_match_head(tmp_path, label, cli, expect_rc):
    """参数校验与错误路径（含 parser.error 的退出码 2）须与 HEAD 一致。"""
    head_src, work_src = _both_sources()
    sandbox = tmp_path / "sb"

    runs = []
    for tag, src in (("head", head_src), ("work", work_src)):
        if sandbox.exists():
            shutil.rmtree(str(sandbox), ignore_errors=True)
        fixture = _make_text_tree(sandbox)
        # 两版本使用同名脚本（置于不同目录），规避 argparse prog 名造成的伪差异
        run_dir = tmp_path / f"err_{tag}"
        run_dir.mkdir(parents=True, exist_ok=True)
        script = run_dir / "rw_err.py"
        script.write_text(src, encoding="utf-8")
        r = subprocess.run([sys.executable, str(script), *cli], cwd=str(fixture),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        runs.append((r.returncode, _tail_usage(r.stderr)))

    (h_rc, h_err), (w_rc, w_err) = runs
    assert h_rc == w_rc == expect_rc, f"[{label}] 退出码 head={h_rc} work={w_rc} 期望={expect_rc}"
    assert h_err == w_err, f"[{label}] 错误输出尾段不一致:\n  head={h_err}\n  work={w_err}"


def _tail_usage(stderr):
    """取 stderr 的最后一段（argparse 用法提示含脚本路径，需去掉首行差异）。"""
    lines = [ln for ln in stderr.splitlines() if ln.strip()]
    return "\n".join(lines[-3:]) if lines else ""


def _first_diff(a, b):
    la, lb = a.splitlines(), b.splitlines()
    for i, (x, y) in enumerate(zip(la, lb)):
        if x != y:
            return "  L%d: head=%r\n  L%d: work=%r" % (i, x, i, y)
    return "  行数不同: head=%d work=%d" % (len(la), len(lb))


# ================================================================ process_word 差分

DOCX_CASES = {
    # 页眉文字水印 + 正文文字水印：--auto 应全部清除
    "auto_textpath": dict(
        document_body=_para("正文一") + _textpath_shape("内部资料") + _para("正文二"),
        header_body=_textpath_shape("机密文件", "PowerPlusWaterMarkObject9"),
        args=(None, True),
    ),
    # 指定文案：仅命中关键字的 textpath 被清除
    "text_match": dict(
        document_body=_para("正文一") + _textpath_shape("内部资料") + _para("正文二"),
        header_body=_textpath_shape("其他水印", "PowerPlusWaterMarkObject8"),
        args=("内部资料", False),
    ),
    # 指定文案但不匹配：不应有任何删除
    "text_no_match": dict(
        document_body=_para("正文一") + _textpath_shape("内部资料"),
        header_body=None,
        args=("完全不同的文案", False),
    ),
    # 指定文案时图片水印分支被 (auto or not text) 抑制
    "pict_suppressed_by_text": dict(
        document_body=_para("正文一") + _pict_only_shape(),
        header_body=None,
        args=("内部资料", False),
    ),
    # --auto 且无 text：图片水印分支生效
    "pict_auto": dict(
        document_body=_para("正文一") + _pict_only_shape(),
        header_body=None,
        args=(None, True),
    ),
    # 非水印形状不得误删
    "plain_shape_kept": dict(
        document_body=_para("正文一") + _plain_shape() + _para("正文二"),
        header_body=None,
        args=(None, True),
    ),
    # 中文 name 命中：水印命名含“水印”
    "chinese_name": dict(
        document_body=_para("正文一") + _textpath_shape("内部资料", "水印形状1"),
        header_body=None,
        args=(None, True),
    ),
    # 页脚也有水印
    "footer_watermark": dict(
        document_body=_para("正文一"),
        header_body=None,
        footer_body=_textpath_shape("内部资料", "PowerPlusWaterMarkObject7"),
        args=(None, True),
    ),
    # 全无水印
    "no_watermark": dict(
        document_body=_para("正文一") + _para("正文二"),
        header_body=None,
        args=(None, True),
    ),
}


@pytest.mark.parametrize("label", sorted(DOCX_CASES), ids=sorted(DOCX_CASES))
def test_process_word_matches_head(tmp_path, label):
    """注入同一份 lxml 桩件后，process_word 的返回值与回写 zip 字节须与 HEAD 一致。"""
    head_src, work_src = _both_sources()
    case = DOCX_CASES[label]
    text, auto = case["args"]
    sandbox = tmp_path / "sb"

    runs = []
    with _fake_lxml():
        for tag, src in (("head", head_src), ("work", work_src)):
            if sandbox.exists():
                shutil.rmtree(str(sandbox), ignore_errors=True)
            sandbox.mkdir(parents=True)
            docx = _build_docx(sandbox / "report.docx", case["document_body"],
                               case.get("header_body"), case.get("footer_body"))
            before = _zip_members(docx)
            mod = _load(src, f"rw_{tag}")
            rv = mod.process_word(str(docx), text, auto)
            runs.append((rv, _zip_members(docx), before))

    (h_rv, h_zip, h_before), (w_rv, w_zip, w_before) = runs
    assert h_before == w_before, "夹具构造不一致，差分前提不成立"
    assert h_rv == w_rv, f"[{label}] 返回值不一致 head={h_rv} work={w_rv}"
    assert h_zip == w_zip, (
        f"[{label}] 回写 zip 成员不一致: "
        + ", ".join(k for k in sorted(set(h_zip) | set(w_zip)) if h_zip.get(k) != w_zip.get(k)))


def test_process_word_non_zip(tmp_path):
    """非 zip 文件须返回 (0, '非有效 docx(zip)')，且不得抛异常。"""
    head_src, work_src = _both_sources()
    results = []
    with _fake_lxml():
        for tag, src in (("head", head_src), ("work", work_src)):
            p = tmp_path / f"bad_{tag}.docx"
            p.write_text("this is not a zip", encoding="utf-8")
            results.append(_load(src, f"rw_nz_{tag}").process_word(str(p), None, True))
    assert results[0] == results[1] == (0, "非有效 docx(zip)")


class TestProcessWordContract:
    """process_word 的行为契约（不依赖 HEAD，可长期留存防回弹）。"""

    def _run(self, tmp_path, tag, document_body, header_body=None, footer_body=None,
             text=None, auto=False):
        sandbox = tmp_path / tag
        sandbox.mkdir(parents=True, exist_ok=True)
        docx = _build_docx(sandbox / "d.docx", document_body, header_body, footer_body)
        with _fake_lxml():
            mod = _load(_work_source(), "rw_c_" + tag)
            rv = mod.process_word(str(docx), text, auto)
        return rv, _zip_members(docx)

    def test_auto_removes_watermark_paragraph_only(self, tmp_path):
        body = _para("正文一") + _textpath_shape("内部资料") + _para("正文二")
        (n, detail), members = self._run(tmp_path, "c_auto", body, None, None, None, True)
        assert n == 1 and detail == "删除 1 个水印段落"
        xml = members["word/document.xml"].decode("utf-8")
        assert "正文一" in xml and "正文二" in xml
        assert "textpath" not in xml

    def test_text_keyword_selective(self, tmp_path):
        body = _para("正文一") + _textpath_shape("内部资料") + _textpath_shape("其他水印", "Obj2")
        (n, _), members = self._run(tmp_path, "c_text", body, None, None, "内部资料", False)
        assert n == 1
        xml = members["word/document.xml"].decode("utf-8")
        assert "内部资料" not in xml and "其他水印" in xml

    def test_no_watermark_leaves_file_untouched(self, tmp_path):
        body = _para("正文一") + _para("正文二")
        (n, detail), members = self._run(tmp_path, "c_none", body, None, None, None, True)
        assert n == 0 and detail == "未发现文字水印"
        assert "textpath" not in members["word/document.xml"].decode("utf-8")

    def test_multiple_parts_accumulate(self, tmp_path):
        (n, _), _ = self._run(
            tmp_path, "c_multi",
            _para("正文") + _textpath_shape("内部资料"),
            _textpath_shape("机密", "ObjH"),
            _textpath_shape("草稿", "ObjF"), None, True)
        assert n == 3

    def test_plain_shape_not_removed(self, tmp_path):
        body = _para("正文一") + _plain_shape()
        (n, detail), members = self._run(tmp_path, "c_plain", body, None, None, None, True)
        assert n == 0 and detail == "未发现文字水印"
        assert "NormalShape" in members["word/document.xml"].decode("utf-8")

    def test_styles_part_skipped_by_prefilter(self, tmp_path):
        """不含 textpath/picture 的部件（styles.xml）不得被解析或改写。"""
        body = _para("正文") + _textpath_shape("内部资料")
        _, members = self._run(tmp_path, "c_styles", body, None, None, None, True)
        assert members["word/styles.xml"] == (
            '<?xml version="1.0"?><w:styles xmlns:w="%s"/>' % NS["w"]).encode("utf-8")


# ================================================================ 私有函数契约

@pytest.fixture()
def mod(tmp_path):
    """工作区版本模块（无需 lxml，仅测纯函数）。"""
    return _load(_work_source(), "rw_unit")


class TestResolveTextExts:
    def test_default_contains_builtin(self, mod):
        exts = mod._resolve_text_exts(None)
        assert {".txt", ".md", ".conf", ".json"} <= exts

    def test_appends_without_dot(self, mod):
        assert ".properties" in mod._resolve_text_exts("properties")

    def test_appends_with_dot(self, mod):
        assert ".conf2" in mod._resolve_text_exts(".conf2")

    def test_lowercases_and_strips(self, mod):
        assert ".abc" in mod._resolve_text_exts("  ABC  ")

    def test_empty_segment_kept_as_is(self, mod):
        """空段会被原样加入集合（保留原实现的既有行为，勿“顺手修正”）。"""
        assert "" in mod._resolve_text_exts("a,,b")


class TestShouldSkip:
    def _fp(self, name):
        return Path(name)

    def test_text_ext_not_skipped(self, mod):
        assert mod._should_skip(self._fp("a.md"), "text", None, mod._resolve_text_exts(None)) is False

    def test_unknown_ext_skipped_in_dir_scan(self, mod):
        assert mod._should_skip(self._fp("a.xyz"), "text", None, mod._resolve_text_exts(None)) is True

    def test_forced_format_never_skips_ext(self, mod):
        assert mod._should_skip(self._fp("a.xyz"), "text", "text", mod._resolve_text_exts(None)) is False

    def test_include_ext_widens(self, mod):
        exts = mod._resolve_text_exts("properties")
        assert mod._should_skip(self._fp("a.properties"), "text", None, exts) is False

    def test_core_exts_always_pass(self, mod):
        for name in ("a.txt", "a.md", "a.log", "a.csv"):
            assert mod._should_skip(self._fp(name), "text", None, set()) is False

    def test_non_text_kind_never_skipped(self, mod):
        for kind in ("word", "ppt", "excel", "pdf", "image"):
            assert mod._should_skip(self._fp("a.bin"), kind, None, set()) is False


class TestCollectFiles:
    def test_single_file(self, mod, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("x", encoding="utf-8")
        assert mod._collect_files(f) == [f]

    def test_dir_recursive_and_skips_vcs(self, mod, tmp_path):
        _make_text_tree(tmp_path / "t")
        got = {p.name for p in mod._collect_files(tmp_path / "t")}
        assert {"notes.md", "plain.txt", "stamped.log", "data.csv", "app.conf",
                "binary.dat", "deep.md"} <= got
        assert "ignored.md" not in got, ".git 目录必须被跳过"


class TestParseRects:
    def test_multiple_rects(self, mod):
        class P:
            def error(self, m):
                raise SystemExit(2)
        assert mod._parse_rects(P(), ["1,2,3,4", "0.1, 0.2 ,0.3,0.4"]) == [
            (1.0, 2.0, 3.0, 4.0), (0.1, 0.2, 0.3, 0.4)]

    def test_bad_count_errors(self, mod):
        class P:
            def error(self, m):
                raise AssertionError(m)
        with pytest.raises(AssertionError):
            mod._parse_rects(P(), ["1,2,3"])

    def test_empty(self, mod):
        class P:
            def error(self, m):
                raise AssertionError(m)
        assert mod._parse_rects(P(), []) == []


class TestResolveWorkPath:
    class _Args:
        def __init__(self, in_place=False, output=None):
            self.in_place = in_place
            self.output = output

    def test_in_place_returns_original(self, mod, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("x", encoding="utf-8")
        assert mod._resolve_work_path(f, self._Args(in_place=True), tmp_path) == str(f)

    def test_default_nowater_dir(self, mod, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("x", encoding="utf-8")
        work = mod._resolve_work_path(f, self._Args(), tmp_path)
        assert Path(work) == tmp_path / "_nowater" / "a.md"
        assert Path(work).read_text(encoding="utf-8") == "x"

    def test_explicit_output_single_file_uses_name(self, mod, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("x", encoding="utf-8")
        out = tmp_path / "o"
        work = mod._resolve_work_path(f, self._Args(output=str(out)), tmp_path)
        assert Path(work) == out / "a.md"

    def test_dir_target_preserves_relative_layout(self, mod, tmp_path):
        target = tmp_path / "tree"
        (target / "sub").mkdir(parents=True)
        f = target / "sub" / "b.md"
        f.write_text("y", encoding="utf-8")
        out = tmp_path / "o"
        work = mod._resolve_work_path(f, self._Args(output=str(out)), target)
        assert Path(work) == out / "sub" / "b.md"


class TestSummaryAndReport:
    def test_exit_code_zero_without_error(self, mod, capsys):
        rc = mod._print_summary([{"status": "OK"}, {"status": "NO_WATERMARK"}])
        assert rc == 0
        assert "处理 2 个文件：清理 1，无水印 1，失败 0" in capsys.readouterr().out

    def test_exit_code_one_on_error(self, mod, capsys):
        assert mod._print_summary([{"status": "ERROR"}]) == 1
        assert "失败 1" in capsys.readouterr().out

    def test_empty_summary(self, mod, capsys):
        assert mod._print_summary([]) == 0
        assert "处理 0 个文件" in capsys.readouterr().out

    def test_report_csv_bom_and_rows(self, mod, tmp_path):
        p = tmp_path / "r.csv"
        mod._write_report(str(p), [
            {"file": "a.md", "kind": "text", "status": "OK", "detail": "删除 1 处水印行/短语"},
            {"file": "b.bin", "status": "DRY_RUN"},
        ])
        raw = p.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf"), "报告须为 utf-8-sig（Excel 直开）"
        lines = raw.decode("utf-8-sig").splitlines()
        assert lines[0] == "file,kind,status,detail"
        assert lines[1].startswith("a.md,text,OK,")
        assert lines[2] == "b.bin,,DRY_RUN,"


class TestProcessOne:
    class _Args:
        def __init__(self, **kw):
            self.text = kw.get("text")
            self.auto = kw.get("auto", False)
            self.corner = None
            self.fill = "blur"
            self.format = None
            self.in_place = kw.get("in_place", True)
            self.output = None
            self.dry_run = kw.get("dry_run", False)

    def test_dry_run_records_without_touching(self, mod, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("%s\n" % STAMP_LINE, encoding="utf-8")
        rv = mod._process_one(f, "text", self._Args(dry_run=True), [], tmp_path)
        assert rv["status"] == "DRY_RUN" and "count" not in rv
        assert f.read_text(encoding="utf-8") == "%s\n" % STAMP_LINE

    def test_ok_status_when_removed(self, mod, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("正文\n%s\n" % STAMP_LINE, encoding="utf-8")
        rv = mod._process_one(f, "text", self._Args(text=STAMP_LINE), [], tmp_path)
        assert rv["status"] == "OK" and rv["count"] >= 1
        assert rv["file"] == str(f) and rv["kind"] == "text"

    def test_no_watermark_status(self, mod, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("干净文本\n", encoding="utf-8")
        rv = mod._process_one(f, "text", self._Args(text=STAMP_LINE), [], tmp_path)
        assert rv["status"] == "NO_WATERMARK" and rv["count"] == 0

    def test_error_captured_not_raised(self, mod, tmp_path, monkeypatch):
        f = tmp_path / "a.md"
        f.write_text("x\n", encoding="utf-8")
        monkeypatch.setattr(mod, "process_file", lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("boom")))
        rv = mod._process_one(f, "text", self._Args(), [], tmp_path)
        assert rv["status"] == "ERROR" and rv["detail"] == "boom"


# ================================================================ 结构指标

def test_target_functions_below_threshold():
    """main / process_word 须降到阈值内（防债务回弹）。"""
    import ast
    tree = ast.parse(_work_source())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ("main", "process_word"):
            length = node.end_lineno - node.lineno + 1
            cc = 1 + sum(isinstance(x, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                                        ast.BoolOp, ast.IfExp, ast.comprehension))
                         for x in ast.walk(node))
            assert length <= 80, "%s 长度 %d 超阈值 80" % (node.name, length)
            assert cc <= 15, "%s 圈复杂度 %d 超阈值 15" % (node.name, cc)


def test_epilog_examples_preserved():
    """帮助示例是对外文档契约，重构后须逐条保留。"""
    src = _work_source()
    for frag in ("report.docx --in-place --auto", 'deck.pptx --text "机密"',
                 "book.xlsx --in-place --auto", 'doc.pdf --text "CONFIDENTIAL"',
                 "photo.png --corner br --fill edge", "shot.jpg --auto --fill blur",
                 "notes.md --text", "log.txt --auto"):
        assert frag in src, f"帮助示例缺失: {frag}"


def test_cli_help_runs(tmp_path):
    """--help 必须可用（epilog 提取为常量后仍能被 argparse 正常渲染）。"""
    r = subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=str(tmp_path),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0
    assert "去水印工具" in r.stdout and "--include-ext" in r.stdout
