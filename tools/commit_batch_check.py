#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
commit_batch_check.py — 提交批量化检查 + 固化频次提示（ADR-2026-08-29-002 M1）

背景：TRAE 等客户端反复提交同质化小文件（审计留痕/交接断点刷新等 1~2 文件/次），
每小改动即触发「固化→提交→双推→重试」完整闭环，形成高频率低价值提交循环
（DORA VSM：wait time 是隐藏低效指标；GitHub PR：相关变更聚合提交是协作标准）。

功能（三层）：
  L1 提交批量化检查：git diff 暂存文件数 ≤2 且均为「同质小改动」（审计/断点/留痕/README）时
      输出提示「建议合并到相关功能提交」，不阻断（可 --gate 强制阻断）。
  L2 固化频次提示：扫描 1 小时内 `solidify`/`audit` 操作日志（13 审计台账 + 32 镜像台账），
      固化频次 >3 次/小时且均为同质 → 提示「攒批，避免碎片固化循环」。
  L3 交互模式：TRAE/opencode Agent 调用时直接输出结构化 JSON（供 Agent 判定是否批量化）。

用法：
  python3 tools/commit_batch_check.py                 # 检查当前暂存区（交互友好）
  python3 tools/commit_batch_check.py --gate          # 检查 + 硬阻断（exit 1 若碎片化）
  python3 tools/commit_batch_check.py --staged-only   # 仅检查暂存文件清单
  python3 tools/commit_batch_check.py --json          # 结构化输出（Agent 用）
  python3 tools/commit_batch_check.py --freq-scan     # 固化频次提示（1h 内同质固化>3）

落地配套：
  - pre-commit 钩子建议加 `python3 tools/commit_batch_check.py --freq-scan`（软提示）
  - AGENTS.md 铁律 #16 L1/L2 对应本节。
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 同质小改动特征：审计留痕/断点刷新/README/台账微调/配置微调
HOMOGENEOUS_RE = re.compile(r"(^|/)(13_|14_|26_|32_|文档|.*\.csv|.*\.json|.*\.yaml)")
# 同质操作关键词（固化/审计/交接/刷新/推荐）
HOMO_ACTION_RE = re.compile(r"(固化|审计|交接|刷新|留痕|部署|推送)", re.I)


def run_git(args):
    try:
        r = subprocess.run(
            ["git"] + args, capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace", cwd=ROOT,
        )
        return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def staged_files():
    """返回暂存文件列表（相对路径）"""
    out = run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if not out:
        return []
    return [l for l in out.split("\n") if l.strip()]


def classify_homogeneous(files):
    """判断文件集合是否『同质小改动』：全部为审计/断点/台账/README 类微调"""
    if not files:
        return False
    hom = 0
    for f in files:
        base = os.path.basename(f)
        if HOMOGENEOUS_RE.search(base) or any(k in f.lower() for k in
            ["审计", "台账", "交接", "断点", "doc", "readme", "manifest", "version"]):
            hom += 1
    return hom == len(files)  # 全部同质才判定


def inspect_git_status():
    """返回 (staged_files, is_homogeneous, 说明)"""
    files = staged_files()
    h = classify_homogeneous(files)
    desc = ""
    if files and h:
        desc = "本次改动均为审计/断点/台账/文档类小文件——建议合并到相关功能提交，避免碎片化提交循环（参考铁律#16 L1）"
    elif files and not h:
        desc = "本次含实质代码/技能改动——正常提交"
    else:
        desc = "无暂存文件（git add 前）"
    return files, h, desc


def gate_fail(files, h, args):
    if args.gate and files and h:
        return 1
    return 0


def freq_scan():
    """L2 固化频次提示：扫描 1h 内固化/审计操作频次"""
    ledger13 = os.path.join(ROOT, "台账", "13_安全审计台账.csv")
    freq = 0
    now = datetime.now()
    cutoff = now - timedelta(hours=1)
    if os.path.exists(ledger13):
        # CSV 简易扫描：找最近 1h 内含"固化/审计/交接"关键词的行
        try:
            with open(ledger13, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if not HOMO_ACTION_RE and "OP-AUDIT" not in line:
                        continue
                    if "OP-AUDIT" not in line:
                        continue
                    # 时间戳提取（最后一列附近）
                    m = re.search(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", line)
                    if m:
                        try:
                            t = datetime(*map(int, m.groups()))
                            if t >= cutoff:
                                freq += 1
                        except Exception:
                            pass
        except OSError:
            pass
    if freq > 3:
        return f"⚠ 1 小时内固化/审计操作 {freq} 次（>3 阈值），疑似碎片固化循环——建议攒批合并后一次固化（铁律#16 L2）"
    return f"ℹ 1 小时固化/审计操作 {freq} 次（阈值 3），正常"


def main():
    ap = argparse.ArgumentParser(description="提交批量化检查 + 固化频次提示（铁律#16）")
    ap.add_argument("--gate", action="store_true", help="硬阻断模式（同质小改动则 exit 1）")
    ap.add_argument("--staged-only", action="store_true", help="仅列出暂存文件")
    ap.add_argument("--json", action="store_true", help="结构化 JSON 输出（Agent 用）")
    ap.add_argument("--freq-scan", action="store_true", help="固化频次提示（1h 内同质固化>3）")
    args = ap.parse_args()

    # L2 固化频次提示（软提示，不阻断）
    freq_note = freq_scan()

    files, h, desc = inspect_git_status()

    if args.staged_only:
        if args.json:
            print(json.dumps({"staged": files, "homogeneous": h},
                             ensure_ascii=False, indent=2))
        else:
            print("\n".join(files) if files else "(无暂存文件)")
        return 0

    if args.json:
        print(json.dumps({
            "staged": files,
            "homogeneous": h,
            "verdict": "MERGE" if h else "COMMIT",
            "message": desc,
            "freq_note": freq_note,
        }, ensure_ascii=False, indent=2))
        code = gate_fail(files, h, args)
        return code

    print("══ 提交批量化检查 (commit_batch_check / 铁律#16) ══")
    print(f"  暂存文件数: {len(files)}")
    print(f"  同质小改动: {'是' if h else '否'}")
    print(f"  判定: {desc}")
    print(f"  {freq_note}")
    if files:
        print("  暂存文件:")
        for f in files[:12]:
            print(f"    - {f}")
    code = gate_fail(files, h, args)
    if code:
        print("  ✗ 碎片化提交（--gate 模式阻断）", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())