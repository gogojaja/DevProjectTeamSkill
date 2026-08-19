# 去水印工具（remove_watermark）

> 版本：v1.0.0  
> 支持：Word(.docx) / PPT(.pptx) / Excel(.xlsx) / PDF(.pdf) / 图片 / 纯文本

通用去水印小工具，按格式自动选择处理器，支持自动识别（启发式）与显式指定水印文字/区域。

## 支持矩阵

| 格式 | 处理器 | 去水印方式 | 依赖 |
|------|--------|-----------|------|
| Word `.docx` | `process_word` | 删除页眉/页脚/正文中的文字水印（`v:textpath`）与图片水印（`w:pict` 内 `v:shape`） | lxml |
| PPT `.pptx` | `process_ppt` | 删除幻灯片/母版/版式中文字或图片水印形状 | python-pptx |
| Excel `.xlsx/.xlsm` | `process_excel` | 清除工作表背景图 (`sheetPr/picture`)；`--auto` 额外清页眉/页脚图水印 | lxml |
| PDF `.pdf` | `process_pdf` | 文本水印按关键字 redact；`--rect` 区域压制；`--auto` 跨页重复文字识别 | PyMuPDF（可选） |
| 图片 | `process_image` | `--rect` 区域填充 / `--corner` 角落 / `--auto` 边缘密度启发式 | Pillow |
| 纯文本 | `process_text` | 删除整行水印印章、行尾水印短语、`--auto` 高频重复行 | 无 |

## 快速开始

```bash
# Word：自动识别并删除页眉文字水印（原地）
python3 tools/remove_watermark/remove_watermark.py report.docx --in-place --auto
python3 tools/remove_watermark/remove_watermark.py report.docx --text "内部资料"

# PPT：删除含指定文字的水印形状
python3 tools/remove_watermark/remove_watermark.py deck.pptx --text "机密"

# Excel：清除工作表背景图水印
python3 tools/remove_watermark/remove_watermark.py book.xlsx --in-place
python3 tools/remove_watermark/remove_watermark.py book.xlsx --in-place --auto

# PDF：文字水印按关键字 redact（需 pymupdf）；区域压制
python3 tools/remove_watermark/remove_watermark.py doc.pdf --text "CONFIDENTIAL"
python3 tools/remove_watermark/remove_watermark.py doc.pdf --rect 0.05,0.85,0.95,0.95

# 图片：角落 / 像素区域 / 自动启发式
python3 tools/remove_watermark/remove_watermark.py photo.png --corner br --fill edge
python3 tools/remove_watermark/remove_watermark.py photo.png --rect 300,200,800,500
python3 tools/remove_watermark/remove_watermark.py shot.jpg --auto --fill blur

# 文本：删除水印印章行 / 行尾短语
python3 tools/remove_watermark/remove_watermark.py notes.md --text "内部资料 勿外传"
python3 tools/remove_watermark/remove_watermark.py log.txt --auto
```

Windows 用 `py -3.11` 或 `.\tools\remove_watermark\remove_watermark.ps1`。

## 参数

| 参数 | 说明 |
|------|------|
| `target` | 目标文件或目录（目录递归，跳过 .git/.venv/dist 等） |
| `-o, --output` | 输出目录（默认 `_nowater`），保留原件 |
| `--in-place` | 原地修改（危险，先备份） |
| `--text` | 水印文字/文案（关键字匹配） |
| `--auto` | 自动识别水印（各格式启发式） |
| `--rect x0,y0,x1,y1` | 区域（PDF 相对 0~1；图片像素），可多次 |
| `--corner tl/tr/bl/br` | 图片：常见角落水印 |
| `--fill blur/edge/white` | 图片填充方式（默认 blur 模糊化） |
| `--format word/ppt/excel/pdf/image/text` | 强制按指定格式处理 |
| `--dry-run` | 预览不修改 |
| `--report out.csv` | 报告 CSV（UTF-8 with BOM） |
| `--include-ext` | 额外文本扩展名 |

## 各格式注意事项

- **Word**：标准文字水印在页眉部件中以 `v:textpath` 存储，`--auto` 删除所有此类元素；图片水印（PowerPlusWaterMarkObject / 名称含"水印"）同时清除。**正文图片/logo 不受影响**（仅名含水印的 shape 会被清除）。Word 自带水印不可逆，建议先 `-o` 试跑。
- **PPT**：`--auto` 删除名称含 Watermark/水印 或 ≥32pt 短文本的形状；`--text` 删除内容含关键字的任何形状（含母版/版式）。
- **Excel**：默认只删工作表背景 `sheetPr/picture`；`--auto` 额外删除 `legacyDrawingHF`（页眉页脚图片水印）。Excel 无原生"文字水印"对象，文字水印常以形状/图片形式存在，需用其他方式。
- **PDF**：需 `pip install pymupdf`。`--text` 按关键字 redact；`--auto` 识别**跨页重复**的短文本作水印（频度 ≥ 页数/2）；`--rect` 用相对坐标（0~1）压制区域（含红色注解）。普通文本水印（非字体嵌入字形）redact 后可移除。
- **图片**：`--corner` 覆盖四角 14% 区域；`--auto` 取四角边缘密度最高者作水印区；`--rect` 精确区域（像素坐标，可嵌套多次）。填充方式：`blur`（高斯模糊）、`edge`（四边平均色）、`white`。**注**：本工具图像层基于 Pillow 启发式，叠加复杂背景/多色水印效果有限；追求高保真可用 OpenCV inpainting（后续可选增强）。
- **文本**：`--text` 删除整行水印印章 + 行尾水印短语；`--auto` 删除长度 ≤24 且全文出现 ≥3 次的重复行（印章带）。

## 与 desensitize 工具的定位

- `tools/desensitize`：**内容脱敏**（A/B/C 级敏感信息替换：密钥/密钥/IP/路径→占位符），清理的是**信息泄露**。
- `tools/remove_watermark`：**外观清理**（删除文档内嵌水印/印章/背景底图），清理的是**视觉水印**。
- 二者互补互斥：同一文件若既有水印又有敏感信息，先 `remove_watermark` 再去水印，再走 `desensitize` 脱敏 + 提交前 `pre-commit-secret-scan`。

## 退出码

- `0`：全部成功 或 无水印
- `1`：存在失败文件