#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docx_structure_extract.py — T-07 Word 结构提取器

提取 docx 标题树 + 段落 + 表格 → 输出 txt/json。
解决痛点 P7（Word 文档结构分析无工具）。

CLI（跨平台）：
  py -3.11 tools/docx_structure_extract.py --input <docx> --output <txt/json>
  py -3.11 tools/docx_structure_extract.py --input srs.docx --output structure.json

输出：
  txt: 标题树 + 段落摘要 + 表格内容
  json: 结构化数据（标题层级/段落/表格）

依赖：python-docx（未安装时提示安装命令）
"""
import os
import sys
import io
import json
import argparse

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def extract_structure(input_path, output_path=None, fmt="txt"):
    """提取 Word 文档结构。

    Args:
        input_path: docx 文件路径
        output_path: 输出路径
        fmt: "txt" 或 "json"

    Returns:
        str: 输出文件路径
    """
    if not HAS_DOCX:
        print("错误: python-docx 未安装。请运行: pip install python-docx")
        sys.exit(1)

    if not os.path.exists(input_path):
        print("错误: 文件不存在: %s" % input_path)
        sys.exit(1)

    doc = docx.Document(input_path)

    # 提取标题树
    headings = []
    paragraphs = []
    for para in doc.paragraphs:
        if para.style.name.startswith("Heading"):
            level = int(para.style.name.replace("Heading ", "").replace("Heading", "1"))
            headings.append({"level": level, "text": para.text.strip()})
        if para.text.strip():
            paragraphs.append({"style": para.style.name, "text": para.text.strip()[:200]})

    # 提取表格
    tables = []
    for i, table in enumerate(doc.tables):
        rows_data = []
        for row in table.rows:
            cells = [cell.text.strip()[:50] for cell in row.cells]
            rows_data.append(cells)
        tables.append({"index": i, "rows": len(table.rows), "cols": len(table.columns), "data": rows_data})

    structure = {
        "file": os.path.basename(input_path),
        "headings": headings,
        "paragraphs_count": len(paragraphs),
        "tables_count": len(tables),
        "tables": tables,
    }

    if not output_path:
        base = os.path.splitext(os.path.basename(input_path))[0]
        ext = ".json" if fmt == "json" else ".txt"
        output_path = os.path.join(ROOT, "docs", "reviews", base + "_structure" + ext)

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    if fmt == "json":
        with io.open(output_path, "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)
    else:
        with io.open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("文档结构: %s\n" % input_path)
            f.write("=" * 60 + "\n\n")

            f.write("## 标题树\n")
            for h in headings:
                indent = "  " * (h["level"] - 1)
                f.write("%s[H%d] %s\n" % (indent, h["level"], h["text"]))
            f.write("\n")

            f.write("## 段落统计: %d 段\n\n" % len(paragraphs))

            f.write("## 表格: %d 个\n" % len(tables))
            for t in tables:
                f.write("\n### 表格 %d（%d 行 x %d 列）\n" % (t["index"], t["rows"], t["cols"]))
                for row in t["data"][:5]:  # 最多显示 5 行
                    f.write("  | %s |\n" % " | ".join(row))
                if t["rows"] > 5:
                    f.write("  ...（省略 %d 行）\n" % (t["rows"] - 5))

    print("Word 结构提取完成：")
    print("  输入: %s" % input_path)
    print("  标题: %d 个 | 段落: %d 段 | 表格: %d 个" % (
        len(headings), len(paragraphs), len(tables)))
    print("  输出: %s" % output_path)
    return output_path


def main():
    ap = argparse.ArgumentParser(description="T-07 Word 结构提取器")
    ap.add_argument("--input", required=True, help="docx 文件路径")
    ap.add_argument("--output", default=None, help="输出路径")
    ap.add_argument("--format", choices=["txt", "json"], default="txt", help="输出格式")
    args = ap.parse_args()
    extract_structure(args.input, args.output, args.format)


if __name__ == "__main__":
    main()
