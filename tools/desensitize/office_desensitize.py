#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
office_desensitize.py — Office 文档脱敏工具（desensitize 工具族 v1.2.0 新增模块）

能力（源自项目实战验证，2026-08-25 项目模板脱敏 49 文件 0 残留）：
  1. docx/xlsx 正文替换：段落级 <w:p>/<si> 跨 run 合并替换（解决 Word 把短语拆进
     多个 <w:t> 导致整词替换不命中的问题），含页眉/页脚/脚注/尾注与 sharedStrings；
  2. OLE2 旧格式 .doc/.xls：UTF-16LE/GBK 双编码字节级等长替换（新串短则空格填充，
     保持字节长度不变不破坏文件结构）；
  3. zip 归档内嵌文档：递归处理内部 docx/xlsx/OLE2/伪 docx（扩展名与真实格式不符自动识别）；
  4. --strip-images：删除 docx/xlsx 内嵌图片（media 部件 + drawing 占位 + .rels 关系 + drawings 部件）；
  5. 文件名/目录名脱敏：--filename-delete 删除指定子串；--strip-leading-non-cjk 去掉开头非中文字符；
  6. 备份先行（--no-backup 关闭）+ 执行记录 CSV + 校验（残余敏感词计数 + zip 完整性）。

依赖：仅 Python 标准库（openpyxl/xlrd 均不需要；xlsx 文本经 sharedStrings.xml 提取）。

用法：
  # 扫描模式（只读，定位敏感词 + 图片清单）
  python office_desensitize.py --scan <目录|文件> --keywords "词1,词2" [--dictionary dict.csv] [--report-dir DIR]

  # 脱敏模式（先备份，再替换/删图/改名，最后校验）
  python office_desensitize.py <目录|文件> \
      --keywords-map "旧=新,旧2=新2" [--dictionary dict.csv] \
      [--strip-images] [--filename-delete "子串1,子串2"] [--strip-leading-non-cjk] \
      [--report-dir DIR] [--no-backup] [--dry-run]

  # 说明：
  #   --keywords-map 中 "旧=" 表示删除该词（替换为空）；
  #   --dictionary 复用 desensitize_dictionary.csv（列：keyword,level,replacement,type,description），
  #       取 keyword→replacement 参与 Office 替换，与 --keywords-map 合并；
  #   --dry-run 仅打印将执行的变更，不写文件、不改名。

返回码：0=成功/扫描完成；1=校验发现残留或损坏文件；2=参数错误。
"""
import os, re, sys, io, csv, shutil, zipfile, argparse
from datetime import datetime

VERSION = "1.2.0"
IMG_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.emf', '.wmf', '.tif', '.tiff', '.svg', '.webp'}


def is_lock(name): return os.path.basename(name).startswith('~$')
def is_zip_bytes(d): return len(d) >= 4 and d[:4] == b'PK\x03\x04'


# ==================== 文件名处理 ====================
def strip_lead_non_cjk(name):
    m = re.search(r'[\u4e00-\u9fff]', name)
    if m and m.start() > 0:
        return name[m.start():]
    return name


def make_name_processor(delete_substrings, strip_leading):
    def process(name):
        n = name
        for s in delete_substrings:
            n = n.replace(s, "")
        if strip_leading:
            n = strip_lead_non_cjk(n)
        return n
    return process


# ==================== docx/xlsx 段落级合并替换 ====================
def fix_docx_paragraphs(xml_text, rules):
    """<w:p> 内合并所有 <w:t> 文本，替换后整体写回首 <w:t>，其余置空。"""
    mod = False

    def process_p(m):
        nonlocal mod
        content = m.group(2)
        tms = list(re.finditer(r'<w:t\b([^>]*)>(.*?)</w:t>', content, re.DOTALL))
        if not tms:
            return m.group(0)
        full = ''.join(tm.group(2) for tm in tms)
        new = full
        for old, ns in rules:
            new = new.replace(old, ns)
        if new == full:
            return m.group(0)
        mod = True
        parts, last = [], 0
        for i, tm in enumerate(tms):
            parts.append(content[last:tm.start()])
            a = tm.group(1)
            if i == 0:
                if 'xml:space' not in a:
                    a += ' xml:space="preserve"'
                parts.append(f'<w:t{a}>{new}</w:t>')
            else:
                parts.append(f'<w:t{a}></w:t>')
            last = tm.end()
        parts.append(content[last:])
        return f'<w:p{m.group(1)}>{"".join(parts)}</w:p>'

    new_xml = re.sub(r'<w:p\b([^>]*)>(.*?)</w:p>', process_p, xml_text, flags=re.DOTALL)
    return new_xml, mod


def fix_xlsx_shared(xml_text, rules):
    """<si> 内合并所有 <t> 文本，替换后整体写回首 <t>。"""
    mod = False

    def process_si(m):
        nonlocal mod
        content = m.group(1)
        tms = list(re.finditer(r'<t\b([^>]*)>(.*?)</t>', content, re.DOTALL))
        if not tms:
            return m.group(0)
        full = ''.join(tm.group(2) for tm in tms)
        new = full
        for old, ns in rules:
            new = new.replace(old, ns)
        if new == full:
            return m.group(0)
        mod = True
        parts, last = [], 0
        for i, tm in enumerate(tms):
            parts.append(content[last:tm.start()])
            a = tm.group(1)
            if i == 0:
                if 'xml:space' not in a:
                    a += ' xml:space="preserve"'
                parts.append(f'<t{a}>{new}</t>')
            else:
                parts.append(f'<t{a}></t>')
            last = tm.end()
        parts.append(content[last:])
        return f'<si>{"".join(parts)}</si>'

    new_xml = re.sub(r'<si\b[^>]*>(.*?)</si>', process_si, xml_text, flags=re.DOTALL)
    return new_xml, mod


# ==================== OLE2 字节级等长替换 ====================
def replace_ole2_padded(data, rules):
    """UTF-16LE + GBK 双编码字节替换；新串短于旧串时空格填充保持等长。"""
    mod, counts = False, {}
    for old_str, new_str in rules:
        c = 0
        old_b = old_str.encode('utf-16-le')
        new_b = new_str.encode('utf-16-le')
        if len(old_b) >= len(new_b):
            pad = b'\x20\x00' * ((len(old_b) - len(new_b)) // 2)
            if (len(old_b) - len(new_b)) % 2:
                pad += b'\x20'
            c += data.count(old_b)
            data = data.replace(old_b, new_b + pad)
        try:
            old_g = old_str.encode('gbk')
            new_g = new_str.encode('gbk')
            if len(old_g) >= len(new_g):
                c += data.count(old_g)
                data = data.replace(old_g, new_g + b'\x20' * (len(old_g) - len(new_g)))
        except Exception:
            pass
        if c > 0:
            counts[old_str] = counts.get(old_str, 0) + c
            mod = True
    return data, mod, counts


# ==================== zip 类文档处理 ====================
def rewrite_zip(items):
    """items: [(ZipInfo|name, bytes)] → 新 zip 字节。"""
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for info, raw in items:
            zf.writestr(info, raw)
    return out.getvalue()


def replace_in_zip_doc(data, rules):
    """docx/xlsx（zip 容器）内所有 XML/rels 做段落级合并替换 + 兜底整串替换。"""
    z = zipfile.ZipFile(io.BytesIO(data))
    items, mod = [], False
    for info in z.infolist():
        raw = z.read(info.filename)
        if info.filename.endswith('.xml') or info.filename.endswith('.rels'):
            try:
                text = raw.decode('utf-8')
                orig = text
                if '<w:p' in text:
                    text, m1 = fix_docx_paragraphs(text, rules)
                    mod = mod or m1
                if 'sharedStrings' in info.filename or ('<si>' in text and '<t>' in text):
                    text, m2 = fix_xlsx_shared(text, rules)
                    mod = mod or m2
                for old, new in rules:  # 兜底：非段落内文本
                    text = text.replace(old, new)
                if text != orig:
                    raw = text.encode('utf-8')
            except UnicodeDecodeError:
                pass
        items.append((info, raw))
    z.close()
    if not mod:
        return data, False
    return rewrite_zip(items), True


def strip_images_in_zip_doc(data):
    """删除 docx/xlsx 内嵌图片：media 部件 + drawings 部件 + .rels image 关系 + 文档内 drawing 占位。"""
    z = zipfile.ZipFile(io.BytesIO(data))
    items, mod, removed = [], False, []
    for info in z.infolist():
        n = info.filename
        raw = z.read(n)
        low = n.lower()
        # 1) media 部件与 drawings 部件直接删除
        if '/media/' in low or low.startswith('word/media/') or low.startswith('xl/media/') \
                or re.match(r'(word|xl)/drawings/drawing\d+\.xml$', low):
            mod = True
            removed.append(n)
            continue
        # 2) .rels 清理 image 关系
        if low.endswith('.rels'):
            try:
                t = raw.decode('utf-8')
                orig = t
                t = re.sub(r'<Relationship\b[^>]*Type="[^"]*/image"[^>]*/>', '', t)
                if t != orig:
                    mod = True
                    raw = t.encode('utf-8')
            except UnicodeDecodeError:
                pass
        # 3) 正文/页眉/页脚/工作表内 drawing 占位删除
        if re.match(r'(word/(document|header\d+|footer\d+|footnotes|endnotes)|xl/worksheets/sheet\d+)\.xml$', low):
            try:
                t = raw.decode('utf-8')
                orig = t
                t = re.sub(r'<w:drawing>.*?</w:drawing>', '', t, flags=re.DOTALL)
                t = re.sub(r'<xdr:wsDr\b[^>]*>.*?</xdr:wsDr>', '', t, flags=re.DOTALL)
                t = re.sub(r'<drawing\b[^>]*/>', '', t)
                if t != orig:
                    mod = True
                    raw = t.encode('utf-8')
            except UnicodeDecodeError:
                pass
        items.append((info, raw))
    z.close()
    if not mod:
        return data, False, []
    return rewrite_zip(items), True, removed


# ==================== 文本提取（扫描/校验） ====================
def docx_text(b):
    out = []
    try:
        z = zipfile.ZipFile(io.BytesIO(b))
        for n in z.namelist():
            if re.match(r'word/(document|header\d+|footer\d+|footnotes|endnotes)\.xml$', n):
                d = z.read(n).decode('utf-8', 'ignore')
                out.append(''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', d, re.DOTALL)))
    except Exception:
        pass
    return ''.join(out)


def xlsx_text(b):
    """无 openpyxl 依赖：直接解析 sharedStrings.xml。"""
    out = []
    try:
        z = zipfile.ZipFile(io.BytesIO(b))
        for n in z.namelist():
            if n.lower() == 'xl/sharedstrings.xml':
                d = z.read(n).decode('utf-8', 'ignore')
                out.append(''.join(re.findall(r'<t[^>]*>(.*?)</t>', d, re.DOTALL)))
    except Exception:
        pass
    return ''.join(out)


def raw_text(b):
    s = ''
    for enc in ('gbk', 'utf-16-le'):
        try:
            s += b.decode(enc, 'ignore')
        except Exception:
            pass
    return s


def extract_text(p):
    """按真实格式提取文本（识别伪 docx/xlsx：扩展名与文件头不符）。"""
    ext = p.lower().rsplit('.', 1)[-1]
    try:
        with open(p, 'rb') as fh:
            b = fh.read()
    except Exception:
        return ''
    if ext == 'docx':
        if is_zip_bytes(b):
            z_names = []
            try:
                z_names = zipfile.ZipFile(io.BytesIO(b)).namelist()
            except Exception:
                pass
            if any(x.startswith('word/') for x in z_names):
                return docx_text(b)
            if any(x.startswith('xl/') for x in z_names):
                return xlsx_text(b)
        return raw_text(b)
    if ext == 'doc':
        if is_zip_bytes(b):
            return docx_text(b)
        return raw_text(b)
    if ext == 'xlsx':
        return xlsx_text(b) if is_zip_bytes(b) else raw_text(b)
    if ext == 'xls':
        return raw_text(b)
    if ext == 'zip':
        txt = ''
        try:
            z = zipfile.ZipFile(p)
            for n in z.namelist():
                if n.lower().endswith(('.docx', '.xlsx', '.xls', '.doc')):
                    try:
                        bb = z.read(n)
                    except Exception:
                        continue
                    txt += extract_text_bytes(bb, n)
        except Exception:
            pass
        return txt
    return ''


def extract_text_bytes(b, name):
    lext = name.lower().rsplit('.', 1)[-1]
    if lext in ('docx', 'doc'):
        if is_zip_bytes(b):
            return docx_text(b)
        return raw_text(b)
    if lext in ('xlsx', 'xls'):
        if is_zip_bytes(b):
            return xlsx_text(b)
        return raw_text(b)
    return ''


def image_inventory_zip_doc(b):
    """返回 docx/xlsx 内图片部件清单 [(部件名, 大小)]。"""
    res = []
    try:
        z = zipfile.ZipFile(io.BytesIO(b))
        for n in z.namelist():
            low = n.lower()
            if '/media/' in low or os.path.splitext(low)[1] in IMG_EXT or re.match(r'(word|xl)/drawings/drawing\d+\.xml$', low):
                res.append((n, z.getinfo(n).file_size))
    except Exception:
        pass
    return res


# ==================== 归档/目录遍历 ====================
def iter_targets(root):
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if is_lock(f):
                continue
            yield os.path.join(dp, f)


def process_zip_archive(zip_path, rules, strip_images, name_proc, text_log, name_log, img_log):
    """处理 .zip 归档：内嵌文档替换/删图 + 条目改名。"""
    with open(zip_path, 'rb') as f:
        data = f.read()
    z = zipfile.ZipFile(io.BytesIO(data))
    new_items, mod = [], False
    for info in z.infolist():
        raw = z.read(info.filename)
        n = info.filename
        if is_lock(n):
            new_items.append((n, raw))
            continue
        lext = n.lower().rsplit('.', 1)[-1] if '.' in n else ''
        try:
            if lext in ('docx', 'xlsx') or (lext in ('doc', 'xls') and is_zip_bytes(raw)):
                if rules:
                    new_raw, m = replace_in_zip_doc(raw, rules)
                    if m:
                        raw, mod = new_raw, True
                        text_log.append((n, 'zip内段落级XML替换', '已替换'))
                if strip_images:
                    new_raw, m, removed = strip_images_in_zip_doc(raw)
                    if m:
                        raw, mod = new_raw, True
                        for r in removed:
                            img_log.append((f'{os.path.basename(zip_path)}::{r}', 'zip内图片部件'))
            elif lext in ('doc', 'xls'):
                if rules:
                    new_raw, m, counts = replace_ole2_padded(raw, rules)
                    if m:
                        raw, mod = new_raw, True
                        text_log.append((n, 'zip内OLE2等长替换', '; '.join(f'{k}→{v}处' for k, v in counts.items())))
        except Exception:
            pass
        if name_proc:
            new_n = '/'.join(name_proc(p) if p else p for p in n.split('/'))
            if new_n != n:
                if not n.endswith('/'):
                    name_log.append(('zip内文件', f'{os.path.basename(zip_path)}::{n}', n, new_n))
                mod = True
                n = new_n
        new_items.append((n, raw))
    z.close()
    if mod:
        with open(zip_path, 'wb') as f:
            f.write(rewrite_zip([(i, r) for i, r in new_items]))


# ==================== 规则装载 ====================
def load_dictionary(path):
    """desensitize_dictionary.csv：keyword,level,replacement,type,description → (keyword, replacement)。"""
    rules = []
    with open(path, encoding='utf-8-sig', newline='') as f:
        for row in csv.reader(f):
            if not row or not row[0].strip() or row[0].lstrip().startswith('#'):
                continue
            kw = row[0].strip()
            rep = row[2].strip() if len(row) > 2 else ''
            rules.append((kw, rep))
    return rules


def parse_keywords_map(s):
    rules = []
    for pair in s.split(','):
        pair = pair.strip()
        if not pair:
            continue
        if '=' in pair:
            old, new = pair.split('=', 1)
        else:
            old, new = pair, ''
        rules.append((old.strip(), new.strip()))
    return rules


# ==================== CSV 报告 ====================
def write_csv(path, header, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    return path


# ==================== 主流程 ====================
def do_scan(root, keywords, report_dir):
    hits, imgs = [], []
    for p in iter_targets(root):
        ext = p.lower().rsplit('.', 1)[-1]
        txt = extract_text(p)
        for kw in keywords:
            idx = 0
            while True:
                i = txt.find(kw, idx)
                if i < 0:
                    break
                ctx = txt[max(0, i - 20):i + len(kw) + 20].replace('\n', ' ')
                hits.append((os.path.relpath(p, root), '正文', ctx, kw))
                idx = i + len(kw)
        # 文件名命中
        base = os.path.basename(p)
        for kw in keywords:
            if kw in base:
                hits.append((os.path.relpath(p, root), '文件名', base, kw))
        # 图片清单
        try:
            with open(p, 'rb') as fh:
                b = fh.read()
            if is_zip_bytes(b):
                z_names = []
                try:
                    z_names = zipfile.ZipFile(io.BytesIO(b)).namelist()
                except Exception:
                    pass
                if any(x.startswith('word/') or x.startswith('xl/') for x in z_names):
                    for n, sz in image_inventory_zip_doc(b):
                        imgs.append((os.path.relpath(p, root), n, sz))
        except Exception:
            pass
    os.makedirs(report_dir, exist_ok=True)
    h = write_csv(os.path.join(report_dir, 'Office脱敏_扫描报告.csv'),
                  ['文件(相对)', '位置', '上下文/文件名', '命中词'], hits)
    i = write_csv(os.path.join(report_dir, 'Office脱敏_图片清单.csv'),
                  ['文件(相对)', '图片/绘图部件', '大小(字节)'], imgs)
    print(f"扫描完成：敏感词命中 {len(hits)} 处；图片/绘图部件 {len(imgs)} 个")
    print(f"报告：{h}\n      {i}")
    return 0


def do_desensitize(root, rules, strip_images, name_proc, report_dir, backup, dry_run):
    # 0. 备份
    if backup and not dry_run:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        if os.path.isdir(root):
            bdir = f"{root.rstrip('/\\\\')}_备份_{ts}"
            shutil.copytree(root, bdir)
        else:
            bdir = f"{root}_备份_{ts}"
            shutil.copy2(root, bdir)
        print(f"[0/4] 已备份 → {bdir}")
    else:
        print("[0/4] 跳过备份" + ("（dry-run）" if dry_run else "（--no-backup）"))

    text_log, name_log, img_log = [], [], []

    # 1. 正文替换 / 删图
    print("[1/4] 正文替换 + 图片删除" + ("（dry-run，仅统计）" if dry_run else ""))
    for p in iter_targets(root):
        ext = p.lower().rsplit('.', 1)[-1]
        with open(p, 'rb') as fh:
            data = fh.read()
        if ext in ('docx', 'xlsx') or (ext in ('doc', 'xls') and is_zip_bytes(data)):
            new_data, changed = data, False
            if rules:
                try:
                    new_data, m = replace_in_zip_doc(data, rules)
                    changed = changed or m
                except Exception:
                    pass
            if strip_images:
                try:
                    nd, m, removed = strip_images_in_zip_doc(new_data)
                    if m:
                        new_data, changed = nd, True
                        for r in removed:
                            img_log.append((os.path.relpath(p, root), r))
                except Exception:
                    pass
            if changed and not dry_run:
                with open(p, 'wb') as fh:
                    fh.write(new_data)
                text_log.append((os.path.relpath(p, root), '段落级XML替换' if rules else '', '已写入'))
        elif ext in ('doc', 'xls'):
            if rules:
                new_data, m, counts = replace_ole2_padded(data, rules)
                if m and not dry_run:
                    with open(p, 'wb') as fh:
                        fh.write(new_data)
                    text_log.append((os.path.relpath(p, root), 'OLE2等长替换(填充)',
                                     '; '.join(f'{k}→{v}处' for k, v in counts.items())))
        elif ext == 'zip':
            try:
                process_zip_archive(p, rules if not dry_run else [], strip_images and not dry_run,
                                    name_proc if not dry_run else None, text_log, name_log, img_log)
            except Exception as e:
                print(f"  [警告] zip 处理失败 {p}: {e}")
    print(f"  正文替换涉及 {len(text_log)} 项；删除图片部件 {len(img_log)} 个")

    # 2. 文件名/目录名脱敏
    if name_proc and not dry_run:
        print("[2/4] 文件名/目录名脱敏")
        file_renames, dir_renames = [], []
        for dp, dn, fn in os.walk(root):
            for f in fn:
                if is_lock(f):
                    continue
                nf = name_proc(f)
                if nf != f:
                    file_renames.append((os.path.join(dp, f), os.path.join(dp, nf), f, nf))
            for d in dn:
                if is_lock(d):
                    continue
                nd = name_proc(d)
                if nd != d:
                    dir_renames.append((dp.count(os.sep) + 1, os.path.join(dp, d), os.path.join(dp, nd), d, nd))
        for old_p, new_p, old_n, new_n in file_renames:
            try:
                os.rename(old_p, new_p)
                name_log.append(('文件', os.path.relpath(old_p, root), old_n, new_n))
            except Exception as e:
                name_log.append(('文件(失败)', os.path.relpath(old_p, root), old_n, f"{new_n} [错误:{e}]"))
        for _, old_p, new_p, old_n, new_n in sorted(dir_renames, key=lambda x: -x[0]):
            try:
                os.rename(old_p, new_p)
                name_log.append(('目录', os.path.relpath(old_p, root), old_n, new_n))
            except Exception as e:
                name_log.append(('目录(失败)', os.path.relpath(old_p, root), old_n, f"{new_n} [错误:{e}]"))
        nf = sum(1 for r in name_log if r[0] == '文件')
        nd = sum(1 for r in name_log if r[0] == '目录')
        nz = sum(1 for r in name_log if r[0] == 'zip内文件')
        print(f"  文件:{nf} 目录:{nd} zip内:{nz}")
    else:
        print("[2/4] 跳过文件名脱敏" + ("（dry-run）" if dry_run else ""))

    # 3. 执行记录
    os.makedirs(report_dir, exist_ok=True)
    print("[3/4] 生成执行记录")
    t_csv = write_csv(os.path.join(report_dir, 'Office脱敏_正文替换执行记录.csv'),
                      ['文件', '方式', '状态'], text_log + [('合计', f'{len(text_log)}项', '')])
    n_csv = write_csv(os.path.join(report_dir, 'Office脱敏_文件名变更执行记录.csv'),
                      ['类型', '路径', '原名', '新名'], name_log)
    i_csv = write_csv(os.path.join(report_dir, 'Office脱敏_图片删除执行记录.csv'),
                      ['文件', '已删图片部件'], img_log + [('合计', f'{len(img_log)}个')])

    # 4. 校验
    print("[4/4] 校验残余敏感词与文件完整性")
    src_words = sorted({old for old, _ in rules})
    tgt_words = sorted({new for _, new in rules if new})
    counts = {t: 0 for t in src_words + tgt_words}
    corrupt, detail = [], []
    for p in iter_targets(root):
        ext = p.lower().rsplit('.', 1)[-1]
        with open(p, 'rb') as fh:
            b = fh.read()
        if ext in ('docx', 'xlsx', 'zip') or (ext in ('doc', 'xls') and is_zip_bytes(b)):
            try:
                z = zipfile.ZipFile(io.BytesIO(b))
                if z.testzip() is not None:
                    corrupt.append((p, 'testzip失败'))
                z.close()
            except Exception as e:
                corrupt.append((p, str(e)))
        txt = extract_text(p)
        for t in counts:
            c = txt.count(t)
            counts[t] += c
            if c > 0 and t in src_words:
                i = txt.find(t)
                detail.append((t, os.path.relpath(p, root),
                               txt[max(0, i - 15):i + len(t) + 15].replace('\n', ' ')))
    v_rows = []
    for w in src_words:
        v_rows.append([w, counts[w], 0, '已清零' if counts[w] == 0 else f'残留{counts[w]}处'])
    for w in tgt_words:
        v_rows.append([f'(目标){w}', counts[w], '>0', '已注入' if counts[w] > 0 else '未注入'])
    v_rows.append(['文件完整性', '全部正常' if not corrupt else f'{len(corrupt)}个损坏', '', ''])
    for d in detail[:50]:
        v_rows.append(['残余', d[0], d[1], d[2]])
    v_csv = write_csv(os.path.join(report_dir, 'Office脱敏_校验结果.csv'),
                      ['词', '数量', '预期', '状态/位置'], v_rows)
    print(f"  源词残留：{ {w: counts[w] for w in src_words} }")
    print(f"  完整性：{'全部正常' if not corrupt else f'{len(corrupt)}个损坏'}")
    if corrupt:
        for p, e in corrupt:
            print(f"    损坏: {p}: {e}")
    print(f"报告目录：{report_dir}")
    rc = 0
    if not dry_run:
        if any(counts[w] for w in src_words) or corrupt:
            rc = 1
    return rc


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description=f'Office 文档脱敏工具 v{VERSION}（docx/xlsx/OLE2 doc·xls/zip 内嵌）')
    ap.add_argument('target', help='目标文件或目录')
    ap.add_argument('--scan', action='store_true', help='扫描模式（只读）')
    ap.add_argument('--keywords', help='检测词，逗号分隔（扫描模式）')
    ap.add_argument('--keywords-map', help='替换映射，如 "旧=新,旧2=新2"（"旧=" 表示删除）')
    ap.add_argument('--dictionary', help='脱敏字典 CSV（keyword,level,replacement,...），与 --keywords-map 合并')
    ap.add_argument('--strip-images', action='store_true', help='删除 docx/xlsx 内嵌图片（含 zip 内文档）')
    ap.add_argument('--filename-delete', help='文件名中需删除的子串，逗号分隔')
    ap.add_argument('--strip-leading-non-cjk', action='store_true', help='删除文件名/目录名开头的非中文字符')
    ap.add_argument('--report-dir', default='office_desens_reports', help='报告输出目录（默认 ./office_desens_reports）')
    ap.add_argument('--no-backup', action='store_true', help='跳过自动备份（默认先备份再修改）')
    ap.add_argument('--dry-run', action='store_true', help='只统计不写入')
    args = ap.parse_args()

    if not os.path.exists(args.target):
        print(f"目标不存在：{args.target}")
        return 2
    root = args.target

    if args.scan:
        kws = [k.strip() for k in args.keywords.split(',')] if args.keywords else []
        if args.dictionary:
            kws += [old for old, _ in load_dictionary(args.dictionary)]
        if not kws:
            print("扫描模式需要 --keywords 或 --dictionary 提供检测词")
            return 2
        return do_scan(root, kws, args.report_dir)

    rules = []
    if args.keywords_map:
        rules += parse_keywords_map(args.keywords_map)
    if args.dictionary:
        rules += load_dictionary(args.dictionary)
    # 长词优先（避免短词先替换拆散长词）
    rules.sort(key=lambda r: -len(r[0]))
    if not rules and not args.strip_images and not args.filename_delete and not args.strip_leading_non_cjk:
        print("脱敏模式需要 --keywords-map/--dictionary/--strip-images/--filename-delete/--strip-leading-non-cjk 至少一项")
        return 2

    name_proc = None
    if args.filename_delete or args.strip_leading_non_cjk:
        subs = [s.strip() for s in args.filename_delete.split(',')] if args.filename_delete else []
        name_proc = make_name_processor(subs, args.strip_leading_non_cjk)

    return do_desensitize(root, rules, args.strip_images, name_proc, args.report_dir,
                          backup=not args.no_backup, dry_run=args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
