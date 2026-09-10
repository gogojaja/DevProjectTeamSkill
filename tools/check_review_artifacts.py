#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# check_review_artifacts.py — 评审产物落盘门禁（solidify Step 1f 硬门禁）
#
# 背景（2026-08-29 评审过程自省，DBD-001~004）：
#   FULL 第三方多视角评审的结论、证据、申明此前仅内嵌在方案文档中，
#   未独立落盘、证据卡存 /tmp 易失、缺乏评审模式申明，导致评审结果无法
#   被门禁/追溯机制引用，且证据链跨会话断裂。
#
# 本门禁强制校验 FULL 评审的四项产物是否就绪：
#   1) 评审报告 CSV 已落盘（docs/reviews/ 存档 + 项目根副本，UTF-8 BOM）；
#   2) 证据卡已入库（docs/evidence_cards_*.json，禁止引用 /tmp）；
#   3) 评审模式申明存在（自评/真实第三方 + 真实外部信号 ≥1 条或显式标记未完成）；
#   4) 方案文档引用的证据/报告路径可达（不留 /tmp 挂链）。
#
# 判定：
#   仓库内 `docs/` 有方案文档且含评审结论（SIGNED_OFF / CHANGES_REQUESTED /
#   BLOCKED）时，按上述 4 项检查；任何一项缺失 → 提示缺失项（warning），
#   仅当存在显式评审但无报告 CSV 时 → exit 1（阻断固化）。
#   纯规则/无评审的文档 → 通过（前向兼容）。
#
# 用法：
#   python3 tools/check_review_artifacts.py            # 门禁校验（exit 0/1）
#   python3 tools/check_review_artifacts.py --scan     # 仅扫描展示，不阻断
# =============================================================================
import argparse
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(ROOT, "docs")
REVIEWS_DIR = os.path.join(DOCS_DIR, "reviews")

REVIEW_DECISION_RE = re.compile(r'(SIGNED_OFF|CHANGES_REQUESTED|BLOCKED)')
REVIEW_MODE_RE = re.compile(r'(多视角自评|自评|真实第三方|第三方评审|评审模式)', re.I)
EXTERNAL_SIGNAL_RE = re.compile(r'(外部信号|外部核验|webfetch|官方文档|实测|工具核验|人工复核)', re.I)
TMP_REF_RE = re.compile(r'(/tmp/|/var/folders/[^`\s]*)')
EVIDENCE_REF_RE = re.compile(r'(evidence_cards[^`"\s]*)')
DECISION_LINE_RE = re.compile(r'(决策记录|决策|评审结论|评审签署|聚合决策|SIGNED_OFF)')

TEXT_EXT = {'.md', '.txt'}
EXCLUDE_DIRS = {'.git', 'dist', 'skills_backup', 'node_modules', '__pycache__',
                '.github', '.claude', '.agents', '.venv', 'venv',
                'skills_backup_v21.6.0', '.backup'}


def walk_docs():
    """返回 docs/ 下所有 .md 文本文件绝对路径（去重）"""
    out = []
    if not os.path.isdir(DOCS_DIR):
        return out
    for dirpath, dirnames, filenames in os.walk(DOCS_DIR):
        rel = os.path.relpath(dirpath, ROOT)
        top = rel.split(os.sep)[0] if rel != '.' else ''
        if top in EXCLUDE_DIRS:
            dirnames[:] = []
            continue
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in TEXT_EXT:
                out.append(os.path.join(dirpath, fn))
    return out


def read_text(p):
    try:
        with open(p, encoding='utf-8', errors='ignore') as f:
            return f.read()
    except OSError:
        return ''


def has_review_decision(content):
    """含评审结论标记（SIGNED_OFF/CHANGES_REQUESTED/BLOCKED）"""
    return REVIEW_DECISION_RE.search(content) is not None


def collect_evidence_docs():
    """docs/ 下 evidence_cards_*.json 文件"""
    out = []
    if os.path.isdir(DOCS_DIR):
        for fn in os.listdir(DOCS_DIR):
            if fn.lower().startswith('evidence_cards') and fn.endswith('.json'):
                out.append(os.path.join(DOCS_DIR, fn))
    return out


def collect_reports():
    """docs/reviews/ 下评审报告 CSV + 项目根评审报告 CSV"""
    out = []
    for base in (REVIEWS_DIR, ROOT):
        if not os.path.isdir(base):
            continue
        for fn in os.listdir(base):
            low = fn.lower()
            if ('评审报告' in fn or 'review' in low) and fn.endswith('.csv'):
                out.append(os.path.join(base, fn))
    return out


class AuditState:
    """评审产物核查过程中的累积状态（软性提示 + 三类硬阻断线索）。"""

    def __init__(self):
        self.warnings = []
        self.unreachable_ev = []      # 证据卡引用不可达（硬阻断）
        self.tmp_refs_all = []        # /tmp 挂链（硬阻断）
        self.missing_report_docs = []  # 显式评审但缺报告 CSV（硬阻断）


def split_review_targets(docs):
    """单次读取文档内容，分离出「含评审结论」与「命中决策/评审签署行」两类目标。"""
    reviewed = []
    related = []
    for p in docs:
        content = read_text(p)
        decided = has_review_decision(content)
        if decided:
            reviewed.append(p)
        if DECISION_LINE_RE.search(content) and (REVIEW_MODE_RE.search(content) or decided):
            related.append((p, content))
    return reviewed, related


def check_report_present(p, content, rel, report_names, state):
    """1. 评审报告 CSV 是否落盘：仅当文档显式声明评审（评审模式申明存在）才强制要求报告"""
    if not REVIEW_MODE_RE.search(content):
        return
    base_hint = os.path.splitext(os.path.basename(p))[0].replace('_', '')
    hint = base_hint[:6].lower()
    matched = any(hint in r.lower() or '评审' in r for r in report_names)
    if not matched:
        state.missing_report_docs.append(rel)


def check_evidence_and_mode(rel, content, evidence_docs, state):
    """2/3. 证据卡入库 + 评审模式申明 + 真实外部信号（均为软性提示）"""
    if not evidence_docs:
        state.warnings.append('[%s] 未找到入库证据卡（docs/evidence_cards_<对象>_<日期>.json），证据链可能仅存 /tmp' % rel)
    if not REVIEW_MODE_RE.search(content):
        state.warnings.append('[%s] 评审报告头部缺「评审模式」申明（多视角自评 / 真实第三方，review.md §3.2）' % rel)
    if not EXTERNAL_SIGNAL_RE.search(content):
        state.warnings.append('[%s] 缺「真实外部信号」标注（≥1 条，缺失则评审应标记「未完成」，review.md §5 门禁）' % rel)


def check_hard_blockers(rel, content, evidence_docs, state):
    """4/5. /tmp 挂链与证据卡引用可达性（硬阻断：证据易失 / 证据链断裂）"""
    tmp_hits = TMP_REF_RE.findall(content)
    if tmp_hits:
        state.tmp_refs_all += [(rel, t) for t in set(tmp_hits)]
    for ev_ref in EVIDENCE_REF_RE.findall(content):
        ref_basename = ev_ref.split('/')[-1]
        if not any(ref_basename == os.path.basename(e) for e in evidence_docs):
            state.unreachable_ev.append((rel, ev_ref))


def summarize_problems(state):
    """汇总硬性问题（阻断固化），顺序与原实现一致。"""
    problems = []
    if state.unreachable_ev:
        problems.append('证据卡引用不可达 %d 处（文件未入库，证据链断裂）：' % len(state.unreachable_ev))
        for rel, ref in state.unreachable_ev[:8]:
            problems.append('     - [%s] 引用 %s 未在 docs/ 找到入库文件' % (rel, ref))
    if state.tmp_refs_all:
        problems.append('/tmp 挂链 %d 处（证据易失，须复制入库后改指 docs/）' % len(state.tmp_refs_all))
    if state.missing_report_docs:
        problems.append('存在显式评审声明的文档但未找到评审报告 CSV（docs/reviews/ 应存 评审报告_<对象>_<版本>_<视角>.csv）：%s' % '、'.join(state.missing_report_docs[:5]))
    return problems


def emit_result(problems, warnings, scan_mode):
    """输出门禁结论并返回退出码（硬性问题存在且非 --scan 时返回 1）。"""
    print()
    if problems:
        print('   ✗ 评审产物门禁未通过，中止固化。硬性问题：', file=sys.stderr)
        for line in problems:
            print('     ● ' + line, file=sys.stderr)
        print('   ~ 软性提示（建议修复）：', file=sys.stderr)
        for line in warnings:
            print('     - ' + line, file=sys.stderr)
        if scan_mode:
            print('   → 当前为 --scan 模式，仅展示，不阻断。')
            return 0
        return 1

    print('   ✓ 评审产物门禁通过（含报告 CSV + 证据卡入库 + 评审模式申明 + 无 /tmp 挂链）')
    if warnings:
        print('   ~ 软性提示（建议修复）：')
        for line in warnings:
            print('     - ' + line)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true', help='仅扫描展示，不阻断')
    args = ap.parse_args()

    docs = walk_docs()
    evidence_docs = collect_evidence_docs()
    report_names = {os.path.basename(p) for p in collect_reports()}

    reviewed_docs, review_related = split_review_targets(docs)
    if not reviewed_docs:
        print('   ✓ 未发现含评审结论的方案文档，评审产物门禁通过（前向兼容）')
        return 0

    print('   ⚠ 检测到 %d 个含 FULL 评审结论的文档，校验评审产物：' % len(reviewed_docs))

    state = AuditState()
    for p, content in review_related:
        rel = os.path.relpath(p, ROOT)
        print('     - %s' % rel)
        check_report_present(p, content, rel, report_names, state)
        check_evidence_and_mode(rel, content, evidence_docs, state)
        check_hard_blockers(rel, content, evidence_docs, state)

    return emit_result(summarize_problems(state), state.warnings, args.scan)


if __name__ == '__main__':
    sys.exit(main())