#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
incompetence_detector.py — 同质操作熔断与不胜任检测（ADR-2026-08-29-002 M2）

背景：TRAE 等客户端反复提交同质化小文件（审计/断点/交接/固化碎片），每次小改动即
触发「固化→提交→双推→重试」完整闭环，形成高频率低价值提交循环。若已发现多次重复
同质操作无实质新进展，即证明当前工具/模型对当前工作不胜任——应立即明确停止当前工作、
开始交接、并推荐替代工具/模型继续。

判定规则（L3 不胜任 + L4 交接熔断）：
  同质操作密度 ≥5 次/会话 且 无实质新进展（同质文件重复提交）→ 判定不胜任
  → 触发 L4：停止当前工作 + 交接（写 交接文档.md 断点 + 13 台账留痕）+ 推荐替代工具/模型

检测源：
  - 台账/13_安全审计台账.csv：OP-AUDIT 操作记录（统计同质操作次数/时间窗）
  - 台账/32_镜像同步记录.csv：推送失败/重试记录（统计推送重试密度）
  - git log：同质提交（审计/交接/断点/固化 关键词提交数量）

用法：
  python3 tools/incompetence_detector.py               # 检测当前不胜任状态（exit 0 胜任 / 1 不胜任）
  python3 tools/incompetence_detector.py --scan        # 仅扫描展示不判定
  python3 tools/incompetence_detector.py --threshold N # 自定义同质阈值（缺省 5）
  python3 tools/incompetence_detector.py --json        # 结构化输出（Agent 用，含推荐替代工具）
  python3 tools/incompetence_detector.py --recommend   # 仅输出替代工具/模型推荐（引用 dev_platform_catalog）

推荐替代工具（引用 .trae/skills/references/dev_platform_catalog.md）：
  - 本地 CLI：opencode（本项目默认）/ claude-code
  - 国产平台：TRAE / WorkBuddy / Cursor（若 TRAE 当前不胜任，推荐切换同平台替代或模型档位）
  - 模型档位：任务越简单（提交/固化/审计）→ 用低价档；复杂任务（评审/架构）→ 强档
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER13 = os.path.join(ROOT, "台账", "13_安全审计台账.csv")
LEDGER32 = os.path.join(ROOT, "台账", "32_镜像同步记录.csv")
CATALOG = os.path.join(ROOT, ".trae", "skills", "references", "dev_platform_catalog.md")

# 同质操作关键词（固化/审计/交接/断点/刷新/留痕/提交小文件）
HOMO_KEYWORDS = ["固化", "审计", "交接", "断点", "刷新", "留痕", "提交", "审计留痕", "OP-AUDIT", "solidify", "audit"]
# 实质新进展关键词（排除了断点/审计等例行操作）
PROGRESS_KEYWORDS = ["评审", "复盘", "工具落地", "方案", "缺陷修复", "重构", "功能", "测试", "技能", "实施", "落地"]


def run_git(args):
    try:
        r = subprocess.run(
            ["git"] + args, capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace", cwd=ROOT,
        )
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def count_ledger13_recent(hours=24):
    """统计最近 N 小时内 13 审计台账同质操作次数"""
    if not os.path.exists(LEDGER13):
        return 0, 0
    cutoff = datetime.now() - timedelta(hours=hours)
    homo = 0
    total = 0
    try:
        with open(LEDGER13, encoding="utf-8", errors="ignore") as f:
            rd = csv.DictReader(f)
            for row in rd:
                # 时间列（尝试常见列名）
                tstr = (row.get("操作时间") or row.get("time") or row.get("时间") or "")
                m = re.search(r"(\d{4})-(\d{2})-(\d{2})T?(\d{2}):(\d{2}):(\d{2})", tstr)
                if not m:
                    continue
                try:
                    t = datetime(*map(int, m.groups()))
                except Exception:
                    continue
                if t < cutoff:
                    continue
                total += 1
                note = " ".join(str(row.get(k, "")) for k in row)
                if any(kw in note for kw in HOMO_KEYWORDS):
                    homo += 1
    except (OSError, csv.Error):
        pass
    return homo, total


def count_push_retries(hours=24):
    """统计 32 镜像台账最近失败/重试次数"""
    if not os.path.exists(LEDGER32):
        return 0
    cutoff = datetime.now() - timedelta(hours=hours)
    fails = 0
    try:
        with open(LEDGER32, encoding="utf-8", errors="ignore") as f:
            rd = csv.DictReader(f)
            for row in rd:
                tstr = row.get("同步时间") or row.get("时间") or ""
                m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", tstr)
                if not m:
                    continue
                try:
                    t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if t < cutoff:
                    continue
                status = str(row.get("状态", "") or "")
                if "失败" in status or "冷却" in status or "重试" in status:
                    fails += 1
    except (OSError, csv.Error):
        pass
    return fails


def count_homogeneous_commits(days=1):
    """统计最近 git 提交中同质提交（审计/交接/断点/固化 关键词）数量"""
    out = run_git(["log", "--since=%d day ago" % days, "--format=%s"])
    if not out:
        return 0, 0
    lines = [l for l in out.split("\n") if l.strip()]
    homo = sum(1 for s in lines if any(kw in s for kw in HOMO_KEYWORDS))
    progress = sum(1 for s in lines if any(kw in s for kw in PROGRESS_KEYWORDS))
    return homo, progress


def recommend_alternatives():
    """推荐替代工具/模型（引用 dev_platform_catalog.md）"""
    recs = []
    recs.append("- 本地 CLI 替代：`claude-code` / `opencode`（本项目默认，若当前工具失效可切换）")
    recs.append("- 同平台替代：TRAE 当前不胜任 → 换 `WorkBuddy` / `Cursor`，或切换 TRAE 模型档位（任务粒度简单用低价档）")
    recs.append("- 模型档位：提交/固化/审计等机械操作 → 低价档（省 token 且不易卡循环）；评审/架构/复盘 → 强档")
    if os.path.exists(CATALOG):
        recs.append(f"- 完整平台/模型矩阵见 references/dev_platform_catalog.md（{os.path.relpath(CATALOG, ROOT)}）")
    return recs


def main():
    ap = argparse.ArgumentParser(description="同质操作熔断与不胜任检测（铁律#16 M2）")
    ap.add_argument("--scan", action="store_true", help="仅扫描展示不判定")
    ap.add_argument("--threshold", type=int, default=5, help="同质操作阈值（缺省 5）")
    ap.add_argument("--json", action="store_true", help="结构化输出（Agent 用）")
    ap.add_argument("--recommend", action="store_true", help="仅输出替代工具/模型推荐")
    args = ap.parse_args()

    if args.recommend:
        for r in recommend_alternatives():
            print(r)
        return 0

    homo13, total13 = count_ledger13_recent()
    push_fails = count_push_retries()
    homo_commits, progress_commits = count_homogeneous_commits()

    # 综合同质密度 = 审计同质 + 推送失败 + 同质提交（保守计数）
    density = homo13 + push_fails + homo_commits
    # 实质进展（应有实质新内容——若不满足则判定风险）
    has_progress = progress_commits > 0 or total13 > homo13

    incompetent = density >= args.threshold and not has_progress

    if args.json:
        print(json.dumps({
            "density": density,
            "threshold": args.threshold,
            "homo_audits_24h": homo13,
            "push_retries_24h": push_fails,
            "homo_commits_1d": homo_commits,
            "progress_commits_1d": progress_commits,
            "has_progress": has_progress,
            "verdict": "INCOMPETENT" if incompetent else "CAPABLE",
            "action": ("停止当前工作+交接+推荐替代" if incompetent else "继续"),
            "recommendations": recommend_alternatives() if incompetent else [],
        }, ensure_ascii=False, indent=2))
        return 1 if incompetent else 0

    print("══ 同质操作熔断与不胜任检测 (铁律#16 M2) ══")
    print(f"  24h 审计同质操作: {homo13} 次 | 24h 推送失败/重试: {push_fails} 次")
    print(f"  1d 同质提交: {homo_commits} 次 | 实质进展提交: {progress_commits} 次")
    print(f"  同质密度: {density} / 阈值 {args.threshold}")
    print(f"  实质新进展: {'有' if has_progress else '无'}")
    if incompetent:
        print("  ━━ L3 判定：不胜任 ━━")
        print("  → 【立即明确停止当前工作】不再固化/提交/重试")
        print("  → 【开始交接】写 交接文档.md 断点 + 13 台账留痕")
        print("  → 【推荐替代工具/模型继续】：")
        for r in recommend_alternatives():
            print(f"      {r}")
        print("  （依据：同质操作密度≥阈值5 且无实质新进展——多次重复同质操作证明工具不胜任）")
    else:
        print("  判定：胜任（继续当前工作）")

    if args.scan:
        print("  （--scan 仅展示，不判定）")
        return 0
    return 1 if incompetent else 0


if __name__ == "__main__":
    sys.exit(main())