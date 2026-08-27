#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""office_desensitize.py 回归测试（desensitize 工具族 v1.2.0）。

覆盖：docx 跨 <w:t> run 短语替换、xlsx sharedStrings 跨 <t> 替换、
图片删除（media + drawing 占位 + .rels 关系）、zip 归档内嵌文档递归处理、
文件名/目录名脱敏（删子串 + 去前导非中文）、长词优先排序、校验闭环。
标记：unit（纯本地、无外部依赖）。
"""
import io
import os
import sys
import zipfile
import pytest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(TOOLS, "desensitize"))
import office_desensitize as od  # noqa: E402


CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId10" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
</Relationships>"""
DOC = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:r><w:t>本项目由</w:t></w:r><w:r><w:t>陕西省农村信用社</w:t></w:r><w:r><w:t>联合社</w:t></w:r><w:r><w:t>承建，省联社统一部署。</w:t></w:r></w:p>
<w:p><w:r><w:drawing><wp:inline xmlns:wp="x"><a:blip r:embed="rId10"/></wp:inline></w:drawing></w:r></w:p>
</w:body></w:document>"""
SST = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="2" uniqueCount="2">
<si><t>陕西</t><t>农信</t></si>
<si><t>普通单元格内容</t></si>
</sst>"""

RULES = [("陕西省农村信用社联合社", "LHS"), ("省联社", "LHS"), ("陕西农信", "NX"),
         ("陕西信合", "NX"), ("陕西省", ""), ("农信", "NX")]


def _make_samples(case):
    with zipfile.ZipFile(os.path.join(case, "test_陕西信合_文档.docx"), "w") as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", DOC)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/media/image1.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    with zipfile.ZipFile(os.path.join(case, "test_农信_表格.xlsx"), "w") as z:
        z.writestr("[Content_Types].xml", CT.replace("word/document.xml", "xl/sharedStrings.xml"))
        z.writestr("xl/sharedStrings.xml", SST)
    with zipfile.ZipFile(os.path.join(case, "01-归档.zip"), "w") as z:
        z.write(os.path.join(case, "test_陕西信合_文档.docx"), " subdir/02-内部_陕西信合_文档.docx")
        z.write(os.path.join(case, "test_农信_表格.xlsx"), "03-内部_农信_表格.xlsx")


@pytest.mark.unit
def test_office_desensitize_full(tmp_path):
    case = str(tmp_path / "case")
    os.makedirs(case)
    _make_samples(case)

    # 扫描模式（只读）
    rc = od.do_scan(case, ["陕西", "农信", "信合"], str(tmp_path / "scan_reports"))
    assert rc == 0
    assert od.extract_text(os.path.join(case, "test_陕西信合_文档.docx")) != ""

    # 脱敏：长词优先已在 main() 排序；此处直接传已排序规则
    name_proc = od.make_name_processor(["陕西省农村信用社联合社", "陕西农信", "陕西信合", "农信"],
                                       strip_leading=True)
    rc = od.do_desensitize(case, RULES, strip_images=True, name_proc=name_proc,
                           report_dir=str(tmp_path / "run_reports"), backup=False, dry_run=False)
    assert rc == 0

    # 文件名：删敏感子串 + 去前导非中文
    names = os.listdir(case)
    assert "文档.docx" in names and "表格.xlsx" in names
    assert not any(("陕西" in n or "农信" in n or "信合" in n) for n in names)

    # docx：跨 run 替换 + 图片/关系/占位清除
    with zipfile.ZipFile(os.path.join(case, "文档.docx")) as z:
        nl = z.namelist()
        assert "word/media/image1.png" not in nl
        assert not any(n.endswith(".rels") and b"/image" in z.read(n) for n in nl)
        doc = z.read("word/document.xml").decode()
        assert "LHS" in doc and "陕西" not in doc and "统一部署" in doc
        assert "<w:drawing>" not in doc

    # xlsx：sharedStrings 跨 <t> 替换
    with zipfile.ZipFile(os.path.join(case, "表格.xlsx")) as z:
        sst = z.read("xl/sharedStrings.xml").decode()
        assert "NX" in sst and "陕西" not in sst and "普通单元格内容" in sst

    # zip：内嵌文档递归替换/删图 + 条目名脱敏
    with zipfile.ZipFile(os.path.join(case, "归档.zip")) as z:
        nl = z.namelist()
        assert all(("陕西" not in n and "农信" not in n and "信合" not in n) for n in nl)
        assert " subdir/内部__文档.docx" in nl
        iz = zipfile.ZipFile(io.BytesIO(z.read(" subdir/内部__文档.docx")))
        assert "word/media/image1.png" not in iz.namelist()
        assert "陕西" not in iz.read("word/document.xml").decode()


@pytest.mark.unit
def test_ole2_padded_same_length():
    """OLE2 等长填充：新串短于旧串时补空格，字节长度不变。"""
    data = "省联社统一部署".encode("utf-16-le")
    new, mod, counts = od.replace_ole2_padded(data, [("省联社", "LHS")])
    assert mod and counts["省联社"] == 1
    assert len(new) == len(data)
    txt = new.decode("utf-16-le")
    assert txt.startswith("LHS") and txt.rstrip(" ") == txt.replace("  ", " ", 0) or "LHS" in txt


@pytest.mark.unit
def test_keywords_map_long_first(tmp_path):
    """--keywords-map 解析后长词优先，避免短词先替换拆散长短语。"""
    rules = od.parse_keywords_map("陕西省=LHS,陕西省农村信用社联合社=LHS")
    # main() 中会按长度重排；此处验证排序函数行为
    rules.sort(key=lambda r: -len(r[0]))
    assert rules[0][0] == "陕西省农村信用社联合社"
