"""office_desensitize 阶段化重构的回归测试。

重构背景：do_desensitize() 原圈复杂度 77、153 行，被深度评审（review_deep.py）
判定为 SEVERE 级技术债，已拆分为五个阶段函数：
    _phase_backup   → 阶段 0 备份
    _phase_replace  → 阶段 1 正文替换 / 图片删除
    _phase_rename   → 阶段 2 文件名与目录名脱敏
    _phase_records  → 阶段 3 执行记录 CSV
    _phase_verify   → 阶段 4 残余校验与完整性检查
本测试锁定拆分前后的可观测行为一致（落盘结果、报告产物、退出码）。

运行：pytest tests/test_office_desensitize_refactor.py -q
"""

import os
import subprocess
import sys
import zipfile
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "desensitize" / "office_desensitize.py"

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType='
    '"application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType='
    '"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '</Types>'
)

RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type='
    '"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
    ' Target="word/document.xml"/>'
    '</Relationships>'
)


def _document_xml(text: str) -> str:
    """构造单段落 word/document.xml。"""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w='
        '"http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>'
    )


def make_docx(path: Path, text: str) -> None:
    """生成最小可用 docx（单段落），用于脱敏回归。"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("word/document.xml", _document_xml(text))


def read_docx_text(path: Path) -> str:
    """读取 docx 正文 XML。"""
    with zipfile.ZipFile(path) as zf:
        return zf.read("word/document.xml").decode("utf-8")


def run_tool(target: Path, *extra: str) -> subprocess.CompletedProcess:
    """以子进程方式调用脱敏工具，避免污染测试进程的 stdout 编码设置。"""
    return subprocess.run(
        [sys.executable, str(TOOL), str(target), *extra],
        capture_output=True, timeout=180,
    )


def _output(proc: subprocess.CompletedProcess) -> str:
    """合并子进程 stdout/stderr 便于断言失败时定位。"""
    return (proc.stdout.decode("utf-8", "replace")
            + proc.stderr.decode("utf-8", "replace"))


def test_replace_and_verify(tmp_path):
    """阶段 1 + 3 + 4：正文替换落盘、报告齐备、源词清零、退出码 0。"""
    work = tmp_path / "work"
    work.mkdir()
    make_docx(work / "a.docx", "负责人张三，联系电话 1234")
    rep = tmp_path / "rep"

    proc = run_tool(work, "--keywords-map", "张三=李四",
                    "--report-dir", str(rep), "--no-backup")

    assert proc.returncode == 0, _output(proc)
    body = read_docx_text(work / "a.docx")
    assert "李四" in body
    assert "张三" not in body
    assert (rep / "Office脱敏_正文替换执行记录.csv").exists()
    assert (rep / "Office脱敏_文件名变更执行记录.csv").exists()
    assert (rep / "Office脱敏_图片删除执行记录.csv").exists()
    assert (rep / "Office脱敏_校验结果.csv").exists()
    verify_text = (rep / "Office脱敏_校验结果.csv").read_text(encoding="utf-8-sig")
    assert "已清零" in verify_text
    assert "全部正常" in verify_text


def test_dry_run_does_not_modify(tmp_path):
    """阶段 1 dry-run：仅统计不落盘，原文件保持不变。"""
    work = tmp_path / "work"
    work.mkdir()
    make_docx(work / "a.docx", "负责人张三")
    before = read_docx_text(work / "a.docx")

    proc = run_tool(work, "--keywords-map", "张三=李四",
                    "--report-dir", str(tmp_path / "rep"),
                    "--no-backup", "--dry-run")

    assert proc.returncode == 0, _output(proc)
    assert read_docx_text(work / "a.docx") == before
    assert "dry-run" in _output(proc)


def test_backup_phase_creates_snapshot(tmp_path):
    """阶段 0：未指定 --no-backup 时生成 *_备份_<时间戳> 目录，且备份保留原文。"""
    work = tmp_path / "work"
    work.mkdir()
    make_docx(work / "a.docx", "负责人张三")

    proc = run_tool(work, "--keywords-map", "张三=李四",
                    "--report-dir", str(tmp_path / "rep"))

    assert proc.returncode == 0, _output(proc)
    backups = [p for p in tmp_path.iterdir() if p.is_dir() and "_备份_" in p.name]
    assert len(backups) == 1, f"未生成唯一备份目录: {list(tmp_path.iterdir())}"
    assert "张三" in read_docx_text(backups[0] / "a.docx")
    assert "李四" in read_docx_text(work / "a.docx")


def test_rename_phase_rewrites_filename(tmp_path):
    """阶段 2：--filename-delete 删除文件名子串，并写入文件名变更记录。"""
    work = tmp_path / "work"
    work.mkdir()
    make_docx(work / "机密报告.docx", "负责人张三")

    proc = run_tool(work, "--keywords-map", "张三=李四",
                    "--filename-delete", "机密",
                    "--report-dir", str(tmp_path / "rep"), "--no-backup")

    assert proc.returncode == 0, _output(proc)
    assert not (work / "机密报告.docx").exists()
    assert (work / "报告.docx").exists()
    name_log = (tmp_path / "rep" / "Office脱敏_文件名变更执行记录.csv")
    assert "机密报告.docx" in name_log.read_text(encoding="utf-8-sig")


def test_scan_mode_is_readonly(tmp_path):
    """--scan 模式：只读扫描，产出命中报告且不修改原文件。"""
    work = tmp_path / "work"
    work.mkdir()
    make_docx(work / "a.docx", "负责人张三")
    before = read_docx_text(work / "a.docx")

    proc = run_tool(work, "--scan", "--keywords", "张三",
                    "--report-dir", str(tmp_path / "rep"))

    assert proc.returncode == 0, _output(proc)
    assert read_docx_text(work / "a.docx") == before
    assert (tmp_path / "rep" / "Office脱敏_扫描报告.csv").exists()


if __name__ == "__main__":
    import tempfile

    failures = 0
    for fn in (test_replace_and_verify, test_dry_run_does_not_modify,
               test_backup_phase_creates_snapshot, test_rename_phase_rewrites_filename,
               test_scan_mode_is_readonly):
        with tempfile.TemporaryDirectory() as td:
            try:
                fn(Path(td))
                print("PASS %s" % fn.__name__)
            except AssertionError as exc:
                failures += 1
                print("FAIL %s: %s" % (fn.__name__, str(exc)[:400]))
    print("failures=%d" % failures)
    sys.exit(1 if failures else 0)
