#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arch_compliance.py — T-10 架构合规检查器

解析 ADR 中的技术约束 → 在代码中扫描违反模式 → 输出合规报告 CSV。
解决痛点 P12（架构决策与代码实现脱节）。

CLI（跨平台）：
  py -3.11 tools/arch_compliance.py --adr-dir 架构资产/ --scan-dir tools/ --output report.csv
  py -3.11 tools/arch_compliance.py --adr-dir 架构资产/ --output report.csv

ADR 约束提取：
  扫描 ADR 文件中的"约束"/"决策"/"禁止"等关键词段落，提取技术约束模式。
  支持格式：Markdown（## 决策/约束/禁止 段落）

输出：
  合规报告 CSV（UTF-8 BOM）：ADR编号,约束描述,检查结果,违反位置,严重级别

依赖：无
"""
import os
import sys
import io
import csv
import re
import json
import argparse
from datetime import datetime

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 约束模式库（从 ADR 中提取的常见技术约束 → 代码扫描正则） ──
CONSTRAINT_PATTERNS = {
    "禁止使用 ORM": {
        "keywords": ["禁止.*ORM", "不使用.*ORM", "不用.*ORM"],
        "scan_pattern": re.compile(r"(from\s+(django|sqlalchemy)\.db|import\s+ORM|Base\.metadata)", re.IGNORECASE),
        "severity": "严重",
    },
    "必须 REST 接口": {
        "keywords": ["必须.*REST", "仅.*REST", "RESTful"],
        "scan_pattern": re.compile(r"(SOAPAction|wsdl|\.soap\b)", re.IGNORECASE),
        "severity": "高",
    },
    "禁止硬编码密码": {
        "keywords": ["禁止.*硬编码.*密码", "禁止.*明文.*密码", "密码.*不得.*硬编码"],
        "scan_pattern": re.compile(r"(password\s*=\s*['\"][^'\"]+['\"]|passwd\s*=\s*['\"][^'\"]+['\"])", re.IGNORECASE),
        "severity": "严重",
    },
    "禁止硬编码 IP": {
        "keywords": ["禁止.*硬编码.*IP", "不得.*硬编码.*IP"],
        "scan_pattern": re.compile(r"(https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"),
        "severity": "高",
    },
    "CSV 输出 UTF-8 BOM": {
        "keywords": ["CSV.*UTF-8.*BOM", "UTF-8.*BOM", "utf-8-sig"],
        "scan_pattern": None,  # 正向检查，非违反检查
        "severity": "一般",
    },
    "禁止 xlsx 输出": {
        "keywords": ["禁止.*xlsx", "不.*xlsx", "仅.*csv"],
        "scan_pattern": re.compile(r"(openpyxl\.Workbook|xlsxwriter\.Workbook|\.save_workbook)"),
        "severity": "一般",
    },
}


def _extract_adr_constraints(adr_path):
    """从 ADR 文件中提取技术约束。

    Returns:
        list: [{"adr_id": "...", "constraint": "...", "source_file": "..."}]
    """
    constraints = []
    if not os.path.exists(adr_path):
        return constraints

    for fname in sorted(os.listdir(adr_path)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(adr_path, fname)
        with io.open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取 ADR 编号
        adr_id = ""
        m = re.search(r'ADR[-_ ]?(\d{4}[-_ ]\d{2}[-_ ]\d{2}[-_ ]\d{3}|\d+)', fname)
        if m:
            adr_id = "ADR-%s" % m.group(1)
        else:
            m = re.search(r'ADR[-_ ]?(\d{4}[-_ ]\d{2}[-_ ]\d{2}[-_ ]\d{3}|\d+)', content)
            if m:
                adr_id = "ADR-%s" % m.group(1)
            else:
                adr_id = os.path.splitext(fname)[0]

        # 提取约束关键词
        for constraint_name, config in CONSTRAINT_PATTERNS.items():
            for kw in config["keywords"]:
                if re.search(kw, content):
                    constraints.append({
                        "adr_id": adr_id,
                        "constraint": constraint_name,
                        "source_file": fname,
                        "severity": config["severity"],
                    })
                    break

    return constraints


def _scan_violations(scan_dir, constraint_name, pattern):
    """在代码目录中扫描违反模式的文件。

    Returns:
        list: [{"file": "...", "line": N, "content": "..."}]
    """
    violations = []
    if pattern is None or not os.path.exists(scan_dir):
        return violations

    for root_dir, dirs, files in os.walk(scan_dir):
        # 跳过隐藏目录和 __pycache__
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for fname in files:
            if not fname.endswith((".py", ".js", ".ts", ".java", ".go", ".sh")):
                continue
            fpath = os.path.join(root_dir, fname)
            try:
                with io.open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    for line_no, line in enumerate(f, 1):
                        if pattern.search(line):
                            violations.append({
                                "file": os.path.relpath(fpath, ROOT),
                                "line": line_no,
                                "content": line.strip()[:80],
                            })
            except Exception:
                pass
    return violations


def arch_compliance(adr_dir, scan_dir=None, output_path=None):
    """架构合规检查主入口。

    Args:
        adr_dir: ADR 目录路径
        scan_dir: 代码扫描目录（None 则用 ROOT）
        output_path: 输出 CSV 路径

    Returns:
        dict: 检查结果摘要
    """
    if not os.path.exists(adr_dir):
        print("错误: ADR 目录不存在: %s" % adr_dir)
        sys.exit(1)

    if scan_dir is None:
        scan_dir = ROOT

    # 提取 ADR 约束
    constraints = _extract_adr_constraints(adr_dir)
    if not constraints:
        print("未从 ADR 中提取到已知约束模式（已检查 %d 个文件）" % len([
            f for f in os.listdir(adr_dir) if f.endswith(".md")
        ]))
        # 即使无约束也输出空报告
        constraints = []

    # 扫描违反
    results = []
    total_violations = 0

    for c in constraints:
        pattern = CONSTRAINT_PATTERNS.get(c["constraint"], {}).get("scan_pattern")
        violations = _scan_violations(scan_dir, c["constraint"], pattern)

        if violations:
            for v in violations:
                results.append({
                    "adr_id": c["adr_id"],
                    "constraint": c["constraint"],
                    "result": "违反",
                    "location": "%s:%d" % (v["file"], v["line"]),
                    "severity": c["severity"],
                    "detail": v["content"],
                })
                total_violations += 1
        else:
            results.append({
                "adr_id": c["adr_id"],
                "constraint": c["constraint"],
                "result": "合规",
                "location": "-",
                "severity": c["severity"],
                "detail": "未发现违反",
            })

    # 输出
    if not output_path:
        report_dir = os.path.join(ROOT, "docs", "reviews")
        os.makedirs(report_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        output_path = os.path.join(report_dir, "架构合规检查_%s.csv" % date_str)

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with io.open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "adr_id", "constraint", "result", "location", "severity", "detail"
        ])
        writer.writeheader()
        writer.writerows(results)

    compliant = len([r for r in results if r["result"] == "合规"])
    print("架构合规检查完成：")
    print("  ADR 目录: %s" % adr_dir)
    print("  扫描目录: %s" % scan_dir)
    print("  约束数: %d | 合规: %d | 违反: %d" % (len(constraints), compliant, total_violations))
    print("  输出: %s" % output_path)
    if total_violations > 0:
        severe = len([r for r in results if r["result"] == "违反" and r["severity"] == "严重"])
        if severe > 0:
            print("  ⚠ 严重违反: %d 处，建议立即修复" % severe)
    return {"constraints": len(constraints), "compliant": compliant, "violations": total_violations, "output_path": output_path}


def main():
    ap = argparse.ArgumentParser(description="T-10 架构合规检查器")
    ap.add_argument("--adr-dir", required=True, help="ADR 目录路径")
    ap.add_argument("--scan-dir", default=None, help="代码扫描目录（默认项目根）")
    ap.add_argument("--output", default=None, help="输出合规报告 CSV 路径")
    args = ap.parse_args()
    arch_compliance(args.adr_dir, args.scan_dir, args.output)


if __name__ == "__main__":
    main()
