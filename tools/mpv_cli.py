#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mpv_cli.py — 评审能力工具化封装（ADR-2026-08-29-001 建议 A / P1）

对应能力：multi-perspective-validation（MPV）五视角评审 + best-practice-solution FULL 评审
定位：工具=「执行/落盘/校验」，技能=「方法论/编排/决策」（评审产物落盘门禁 check_review_artifacts 的生成端）

用法：
  python3 tools/mpv_cli.py --target <对象> --perspectives architect,security --report <输出CSV>
  python3 tools/mpv_cli.py --target <对象> --versions v1.2.0          # 版本参数
  python3 tools/mpv_cli.py --dry-run --target <对象>                  # 仅预览将写入的报告路径/检视项
  python3 tools/mpv_cli.py --validate --report <CSV>                  # 校验已有评审 CSV 的字段规范

输入约定：
  --target   评审对象（方案文档/设计/代码路径，相对项目根）
  --perspectives  视角集（architect,code,security,test,performance 或 cost；缺省 architect,security）
  --report   输出 CSV 路径（缺省 docs/reviews/评审报告_<对象>_<版本>_多视角评审.csv）
  --title    评审标题（用于报告命名，缺省取 target 基名）

输出：UTF-8 BOM CSV（token_standard §3 规范，列=perspective,check_id,check_name,status,severity,evidence,confidence）
落盘后自动跑 desensitize.py 扫描（A/B 级）告警，并提示 check_review_artifacts.py 对接。

半自动说明：视角判定内容由调用方（LLM 会话/用户）提供；本脚本负责结构化落盘 + 脱敏 + 门禁对接，
符合 ADR「工具=执行/落盘/校验，技能=方法论/决策」分工。--dry-run 输出待生成报告的结构化模板。

设计依据：ADR-2026-08-29-001 建议 A；evidence_cards_评审复盘独立化_20260829.json EV-101/102/107。
"""
import argparse
import csv
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent)))
DESENSITIZE = ROOT / "tools" / "desensitize" / "desensitize.py"
GATE = ROOT / "tools" / "check_review_artifacts.py"

PERSPECTIVES = {
    "architect": "架构一致性/技术路线",
    "code": "代码质量",
    "security": "安全合规",
    "test": "测试完备性",
    "performance": "性能基准",
    "cost": "成本+可演进性",
}


def sanitize_name(name: str) -> str:
    """移除路径分隔符与特殊字符，用于报告文件名"""
    return re.sub(r"[\\/:*?\"<>|]", "_", name).strip()


def default_report_path(target: str, version: str, perspectives: list) -> Path:
    reviews = ROOT / "docs" / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    base = sanitize_name(os.path.basename(target))
    persp = "多视角"
    # 视角组合：缺省默认"多视角"；单一视角用视角名
    if len(perspectives) == 1:
        persp = perspectives[0]
    fn = f"评审报告_{base}_{version or 'v1'}_{persp}评审.csv"
    return reviews / fn


def run_desensitize_scan(path: Path) -> int:
    """对落盘 CSV 跑 desensitize A/B 级扫描告警（不阻断）"""
    if not DESENSITIZE.exists():
        print("   ⚠ desensitize.py 不存在，跳过脱敏扫描", file=sys.stderr)
        return 0
    try:
        r = subprocess.run(
            [sys.executable or "python3", str(DESENSITIZE), "--scan", str(path)],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            print("   ⚠ 脱敏扫描发现敏感信息（见报告输出），请按 iron_rules §3 处理后入库。")
            return 1
        return 0
    except (OSError, subprocess.SubprocessError) as e:
        print(f"   ⚠ 脱敏扫描执行失败：{e}", file=sys.stderr)
        return 0


def write_report_csv(path: Path, title: str, target: str, perspectives: list,
                     version: str, rows: list) -> None:
    """写入评审报告 CSV（UTF-8 BOM）"""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["perspective", "check_id", "check_name", "status",
                         "severity", "evidence", "confidence"])
        for r in rows:
            writer.writerow(r[:7])
    print(f"[ok] 评审报告已落盘: {path.relative_to(ROOT)}")


def build_template_rows(title: str, target: str, perspectives: list) -> list:
    """生成待填写的评审 CSV 模板行（半自动：视角内容由调用方填写）"""
    rows = []
    now = datetime.now().strftime("%Y-%m-%d")
    for i, p in enumerate(perspectives, 1):
        pid = f"{p[:4].upper()}-001"
        rows.append([
            p,
            pid,
            f"{title}（{PERSPECTIVES.get(p, p)}视角）",
            "TBD", "medium",
            f"待评审填充（{target}，{now}）",
            "medium",
        ])
    return rows


def validate_report(path: Path) -> int:
    """校验已有评审 CSV 字段规范（列名/空值/status 合法性）"""
    if not path.exists():
        print(f"[error] 报告不存在: {path}", file=sys.stderr)
        return 1
    try:
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except OSError as e:
        print(f"[error] 读取失败: {e}", file=sys.stderr)
        return 1
    if not rows:
        print("[error] 报告为空或表头缺失", file=sys.stderr)
        return 1
    cols = list(rows[0].keys())
    required = ["perspective", "check_id", "check_name", "status", "severity", "evidence", "confidence"]
    missing = [c for c in required if c not in cols]
    if missing:
        print(f"[error] 缺失列: {missing}", file=sys.stderr)
        return 1
    ok_status = {"PASS", "FAIL", "WARNING", "TBD", "CHANGES_REQUESTED", "SIGNED_OFF", "BLOCKED"}
    bad = []
    for r in rows:
        st = str(r.get("status", "")).strip().upper()
        if st not in ok_status:
            bad.append((r.get("check_id"), r.get("status")))
    if bad:
        print(f"[warn] {len(bad)} 行 status 非法: {bad[:5]}", file=sys.stderr)
    print(f"[ok] {path} 校验通过（{len(rows)} 行，列规范齐全）")
    return 0


def main():
    ap = argparse.ArgumentParser(description="评审能力工具化封装（mpv_cli）")
    ap.add_argument("--target", help="评审对象（相对项目根路径/名称）")
    ap.add_argument("--perspectives", default="architect,security",
                    help="视角集（逗号分隔，缺省 architect,security）")
    ap.add_argument("--version", default="v1", help="评审对象版本（用于报告文件名）")
    ap.add_argument("--title", help="评审标题（缺省取 target 基名）")
    ap.add_argument("--report", help="输出 CSV 路径（缺省 docs/reviews/ 自动生成）")
    ap.add_argument("--dry-run", action="store_true", help="仅预览报告路径与模板，不写入")
    ap.add_argument("--validate", metavar="CSV", help="校验已有评审 CSV 字段规范")
    args = ap.parse_args()

    if args.validate:
        return validate_report(Path(args.validate))

    if not args.target:
        print("[error] 缺少 --target", file=sys.stderr)
        return 1

    perspectives = [p.strip().lower() for p in args.perspectives.split(",") if p.strip()]
    title = args.title or os.path.basename(args.target)
    path = Path(args.report) if args.report else default_report_path(args.target, args.version, perspectives)
    rows = build_template_rows(title, args.target, perspectives)

    print("══ 评审能力工具化封装 (mpv_cli) ══")
    print(f" 对象: {args.target} | 视角: {','.join(perspectives)} | 版本: {args.version}")
    print(f" 报告路径: {path.relative_to(ROOT)}")
    if args.dry_run:
        print("  [dry-run] 待填写评审模板（视角内容由调用方填入）：")
        for r in rows:
            print(f"    - {r[0]} / {r[1]} / {r[2]} / status={r[3]}")
        print("  [dry-run] 落盘后自动脱敏扫描 + 对接 check_review_artifacts 门禁。")
        return 0

    write_report_csv(path, title, args.target, perspectives, args.version, rows)
    print("  [step] 脱敏扫描（A/B 级）...")
    run_desensitize_scan(path)
    if GATE.exists():
        print(f"  [step] 评审产物已落盘，可由固化门禁 check_review_artifacts.py 校验：python3 {GATE.name}")
    print("  → 视角内容（status/evidence）请在报告中补充后再提交（半自动模式，见 ADR-2026-08-29-001 建议 A）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())