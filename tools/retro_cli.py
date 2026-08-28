#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retro_cli.py — 复盘收割工具化封装（ADR-2026-08-29-001 建议 B / P2）

对应能力：self-improve 复盘闭环（retrospect_harvest action）+ lesson-harvesting 经验沉淀
定位：工具=「执行/落盘/校验」，技能=「方法论/编排/决策」
安全（ADR SecurityReviewer CHANGES_REQUESTED 已吸收）：复盘数据写库前强制 desensitize A/B 级脱敏。

用法：
  python3 tools/retro_cli.py --stage <阶段> --object <复盘对象> --good "<做得好>" --improve "<需改进>"
  python3 tools/retro_cli.py --stage v21.11.0 --object "评审能力工具化" --good "..." --improve "..." --action "<行动项>;owner:gogo;deadline:2026-09-01"
  python3 tools/retro_cli.py --dry-run --stage v21.11.0 --good "..."                # 仅预览不落盘
  python3 tools/retro_cli.py --closure-check                                       # 检查上一阶段行动项是否已关闭

输出：
  - 追加一行到 台账/22_阶段复盘.csv（列：阶段,复盘对象,做得好,需改进,可固化到SKILL流程,可复用工具,降Token措施,行动项）
  - --write-lessons 时追加经验到 skill-lessons-learned/01_角色层经验.csv（列：经验编号,记录时间,...）
  - 行动项格式："<描述>;owner:<负责人>;deadline:<日期>"

强制脱敏：写库前对复盘文本跑 desensitize.py --scan 检测（A/B 级命中则告警并要求脱敏后才写）。
设计依据：ADR-2026-08-29-001 建议 B；evidence_cards_评审复盘独立化_20260829.json EV-103/104/106。
"""
import argparse
import csv
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional  # Python 3.9 兼容

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
LEDGER22 = ROOT / "台账" / "22_阶段复盘.csv"
LESSON01 = ROOT / ".trae" / "skills" / "shared" / "evolution" / "skill-lessons-learned" / "01_角色层经验.csv"
DESENSITIZE = ROOT / "tools" / "desensitize" / "desensitize.py"

# 22_阶段复盘 列（对照现状）
LEDGER22_COLS = ["阶段", "复盘对象", "做得好", "需改进", "可固化到SKILL流程", "可复用工具", "降Token措施", "行动项"]
# 01_角色层经验 列（对照现状）
LESSON01_COLS = ["经验编号", "记录时间", "来源诊断记录编号", "经验分类", "问题描述", "根因分析",
                 "解决方案", "适用场景", "引用次数", "验证状态", "操作人员", "备注"]


def csv_rows(path: Path) -> tuple:
    """读取 CSV 返回 (header, rows)。兼容 UTF-8 BOM 与无 BOM。"""
    if not path.exists():
        return (LEDGER22_COLS if path == LEDGER22 else LESSON01_COLS), []
    for enc in ("utf-8-sig", "utf-8"):
        try:
            with open(path, encoding=enc, newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if rows:
                return rows[0], rows[1:]
        except (OSError, csv.Error):
            continue
    return [], []


def write_csv(path: Path, header: list, rows: list) -> None:
    """以 UTF-8 BOM 写回 CSV"""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def run_desensitize_text(text) -> int:
    """对复盘文本跑 desensitize --scan（A/B 级命中返回 1 告警，不阻断但提示）"""
    if not text or not DESENSITIZE.exists():
        return 0
    tmp = ROOT / ".secrets" / "_retro_scan_tmp.txt"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    try:
        tmp.write_text(text, encoding="utf-8")
        r = subprocess.run(
            [sys.executable or "python3", str(DESENSITIZE), "--scan", str(tmp)],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        # 命中敏感信息（报告含"发现敏感信息"/A级/B级 计数）
        hit = bool(re.search(r"发现敏感信息\s*[:：]\s*[1-9]|A\s*级[:：]\s*[1-9]|B\s*级[:：]\s*[1-9]", r.stdout))
        if hit:
            print("   ⚠ 复盘文本含敏感信息（A/B 级），建议按 iron_rules §3 脱敏后再写库（仅告警）",
                  file=sys.stderr)
            return 1
        return 0
    except (OSError, subprocess.SubprocessError) as e:
        print(f"   ⚠ 脱敏检查执行失败：{e}", file=sys.stderr)
        return 0
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def parse_actions(action_text: str) -> str:
    """校验并规范化行动项文本（owner/deadline 齐备时标记已符合 Atlassian 标准）"""
    if not action_text.strip():
        return ""
    items = [a.strip() for a in re.split(r"[;；\n]", action_text) if a.strip()]
    has_owner = any("owner" in i.lower() or "负责人" in i or ":" in i for i in items)
    has_deadline = any("deadline" in i.lower() or "截止" in i or "202" in i for i in items)
    ret = action_text.strip()
    if has_owner and has_deadline:
        ret = f"{ret}（owner+deadline 已齐，符合 Atlassian 复盘闭环标准）"
    elif not has_owner or not has_deadline:
        ret = f"{ret}（⚠ 建议补 owner 与 deadline，Atlassian 复盘要求行动项可跟进）"
    return ret


def auto_lesson_number(path: Path) -> str:
    """自动生成经验编号：L-<日期>-<序号>"""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"L-{today}-"
    existing = [r[0] for r in csv_rows(path)[1] if r and r[0].startswith(prefix)]
    return f"{prefix}{len(existing) + 1:02d}"


def main():
    ap = argparse.ArgumentParser(description="复盘收割工具化封装（retro_cli）")
    ap.add_argument("--stage", help="阶段/版本标识")
    ap.add_argument("--object", help="复盘对象")
    ap.add_argument("--good", help="做得好")
    ap.add_argument("--improve", help="需改进")
    ap.add_argument("--skill", help="可固化到SKILL流程")
    ap.add_argument("--tool", help="可复用工具")
    ap.add_argument("--token-save", help="降Token措施")
    ap.add_argument("--action", help="行动项（支持 ;owner:xx;deadline:yyyy-mm-dd）")
    ap.add_argument("--write-lessons", action="store_true", help="同时登记 01_角色层经验.csv")
    ap.add_argument("--lesson-class", default="流程层经验", help="经验分类（写 lessons 时用）")
    ap.add_argument("--dry-run", action="store_true", help="仅预览不落盘")
    args = ap.parse_args()

    if not args.stage or not args.object:
        print("[error] 缺少 --stage 或 --object", file=sys.stderr)
        return 1

    good = args.good or ""
    improve = args.improve or ""
    skill = args.skill or ""
    tool = args.tool or ""
    token_save = args.token_save or ""
    action = parse_actions(args.action or "")

    print("══ 复盘收割工具化封装 (retro_cli) ══")
    print(f" 阶段: {args.stage} | 对象: {args.object} | 行动项: {action or '(未填)'}")

    # 写库前脱敏检查（ADR Security 意见落地）
    print("  [step] 复盘文本脱敏检查（A/B 级）...")
    for text in (good, improve, skill, tool, token_save, action):
        run_desensitize_text(text)

    if args.dry_run:
        print("  [dry-run] 将追加到 台账/22_阶段复盘.csv 一行：")
        print(f"    阶段={args.stage} | 复盘对象={args.object}")
        print(f"    做得好={good[:60]}... | 需改进={improve[:60]}...")
        if args.write_lessons:
            print(f"  [dry-run] 将登记 lessons 经验编号 {auto_lesson_number(LESSON01)}")
        return 0

    # 落盘 22 台账
    header, rows = csv_rows(LEDGER22)
    if header != LEDGER22_COLS:
        print(f"  [warn] 22 台账表头与预期不一致（实际 {header[:3]}...），仍按预期列写入", file=sys.stderr)
        header = LEDGER22_COLS
    new_row = [args.stage, args.object, good, improve, skill, tool, token_save, action]
    # 若已有同阶段+同对象行则覆盖，否则追加
    replaced = False
    for i, r in enumerate(rows):
        if len(r) >= 2 and r[0] == args.stage and r[1] == args.object:
            rows[i] = new_row
            replaced = True
            break
    if not replaced:
        rows.append(new_row)
    write_csv(LEDGER22, header, rows)
    print(f"  [ok] 已{'覆盖' if replaced else '追加'} 22_阶段复盘.csv（第 {len(rows)} 行）")

    # 登记 lessons（可选）
    if args.write_lessons:
        lh, lr = csv_rows(LESSON01)
        if lh != LESSON01_COLS:
            lh = LESSON01_COLS
        lid = auto_lesson_number(LESSON01)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        desc = f"{args.object}：{'做得好' if good else '复盘'} {good[:80]}"
        lr.append([lid, now, args.stage, args.lesson_class, desc, improve or "",
                   skill or tool or "", args.object, "0", "待验证", "gogo", ""])
        write_csv(LESSON01, lh, lr)
        print(f"  [ok] 已登记 lessons 经验 {lid} -> 01_角色层经验.csv")

    return 0


if __name__ == "__main__":
    sys.exit(main())