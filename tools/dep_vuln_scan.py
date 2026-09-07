#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dep_vuln_scan.py — T-09 依赖漏洞扫描器

扫描 Python 依赖的已知漏洞（CVE），输出漏洞清单 CSV。
降级策略（§14.2）：
  在线模式 → 调用 OSV API（https://api.osv.dev/v1/query）
  离线模式 → 仅解析依赖，标记为"待扫描"
  空模式   → 无网络且无缓存，输出空报告

CLI（跨平台）：
  py -3.11 tools/dep_vuln_scan.py --requirements requirements.txt --output report.csv
  py -3.11 tools/dep_vuln_scan.py --pyproject pyproject.toml --output report.csv
  py -3.11 tools/dep_vuln_scan.py --requirements requirements.txt --offline  # 离线模式

输出：
  漏洞清单 CSV（UTF-8 BOM）：包名,当前版本,CVE编号,严重级别,修复版本,摘要

依赖：无（urllib 标准库；可选 requests 加速）
"""
import os
import sys
import io
import csv
import json
import re
import argparse
import hashlib
from datetime import datetime

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(ROOT, ".backup", "vuln_cache")
OSV_API = "https://api.osv.dev/v1/query"


def _now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def parse_requirements(path):
    """解析 requirements.txt，返回 [(包名, 版本), ...]。"""
    deps = []
    if not path or not os.path.exists(path):
        return deps
    with io.open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # 处理 ==, >=, ~= 等版本约束
            m = re.match(r'^([a-zA-Z0-9_.-]+)\s*(?:[=~<>!]+\s*([0-9][0-9.]*))?', line)
            if m:
                name = m.group(1).lower().replace("-", "_")
                version = m.group(2) or ""
                deps.append((name, version))
    return deps


def parse_pyproject(path):
    """解析 pyproject.toml 的 dependencies，返回 [(包名, 版本), ...]。"""
    deps = []
    if not path or not os.path.exists(path):
        return deps
    with io.open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # 简易解析：提取 dependencies 列表中的包名
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("dependencies"):
            in_deps = True
            continue
        if in_deps:
            if stripped == "]":
                break
            # 提取引号内的包名+版本
            m = re.search(r'"([a-zA-Z0-9_.-]+)(?:[><=~!]+([0-9][0-9.]*))?', stripped)
            if m:
                name = m.group(1).lower().replace("-", "_")
                version = m.group(2) or ""
                deps.append((name, version))
    return deps


def _query_osv(package, version):
    """查询 OSV API，返回漏洞列表。"""
    payload = {
        "package": {"name": package, "ecosystem": "PyPI"},
    }
    if version:
        payload["version"] = version

    try:
        import urllib.request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OSV_API,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result.get("vulns", [])
    except Exception as e:
        return [{"error": str(e)}]


def _severity_from_osv(vuln):
    """从 OSV 漏洞信息提取严重级别。"""
    for s in vuln.get("database_specific", {}).get("severity", []):
        if "CRITICAL" in s.get("type", ""):
            return "严重"
    # 检查 CVSS
    for m in vuln.get("metrics", []):
        for cvss in m.get("cvss", []):
            score = cvss.get("baseScore", 0)
            if score >= 9.0:
                return "严重"
            elif score >= 7.0:
                return "高"
            elif score >= 4.0:
                return "中"
            else:
                return "低"
    return "未知"


def _fix_version(vuln):
    """提取修复版本。"""
    for affected in vuln.get("affected", []):
        for r in affected.get("ranges", []):
            for e in r.get("events", []):
                if "fixed" in e:
                    return e["fixed"]
    return ""


def scan_online(deps):
    """在线扫描：逐个查询 OSV API。"""
    results = []
    for name, version in deps:
        vulns = _query_osv(name, version)
        if isinstance(vulns, list) and vulns and "error" not in vulns[0]:
            for v in vulns:
                vuln_id = v.get("id", "")
                # 优先用 CVE
                for alias in v.get("aliases", []):
                    if alias.startswith("CVE-"):
                        vuln_id = alias
                        break
                results.append({
                    "package": name,
                    "version": version,
                    "cve_id": vuln_id,
                    "severity": _severity_from_osv(v),
                    "fix_version": _fix_version(v),
                    "summary": v.get("summary", "")[:80],
                })
        elif isinstance(vulns, list) and vulns and "error" in vulns[0]:
            results.append({
                "package": name,
                "version": version,
                "cve_id": "查询失败",
                "severity": "未知",
                "fix_version": "",
                "summary": vulns[0]["error"][:80],
            })
        # 无漏洞 = 安全，不记录
    return results


def scan_offline(deps):
    """离线模式：仅解析依赖，标记待扫描。"""
    results = []
    for name, version in deps:
        results.append({
            "package": name,
            "version": version,
            "cve_id": "待扫描（离线模式）",
            "severity": "未知",
            "fix_version": "",
            "summary": "需联网后重新扫描",
        })
    return results


def dep_vuln_scan(requirements_path=None, pyproject_path=None, output_path=None, offline=False):
    """依赖漏洞扫描主入口。

    Args:
        requirements_path: requirements.txt 路径
        pyproject_path: pyproject.toml 路径
        output_path: 输出 CSV 路径
        offline: 是否离线模式

    Returns:
        dict: 扫描结果摘要
    """
    # 解析依赖
    deps = []
    deps.extend(parse_requirements(requirements_path))
    deps.extend(parse_pyproject(pyproject_path))

    if not deps:
        print("警告: 未解析到任何依赖")
        return {"total_deps": 0, "total_vulns": 0}

    # 扫描
    if offline:
        results = scan_offline(deps)
        mode = "离线"
    else:
        results = scan_online(deps)
        mode = "在线"

    # 输出
    if not output_path:
        report_dir = os.path.join(ROOT, "docs", "reviews")
        os.makedirs(report_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        output_path = os.path.join(report_dir, "依赖漏洞扫描_%s.csv" % date_str)

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with io.open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "package", "version", "cve_id", "severity", "fix_version", "summary"
        ])
        writer.writeheader()
        writer.writerows(results)

    vuln_count = len([r for r in results if r["cve_id"] and "待扫描" not in r["cve_id"] and "查询失败" not in r["cve_id"]])
    print("依赖漏洞扫描完成（%s模式）：" % mode)
    print("  依赖总数: %d" % len(deps))
    print("  漏洞数量: %d" % vuln_count)
    print("  输出: %s" % output_path)
    if vuln_count > 0:
        severe = len([r for r in results if r["severity"] == "严重"])
        if severe > 0:
            print("  ⚠ 严重漏洞: %d 个，建议立即修复" % severe)
    return {"total_deps": len(deps), "total_vulns": vuln_count, "output_path": output_path}


def main():
    ap = argparse.ArgumentParser(description="T-09 依赖漏洞扫描器")
    ap.add_argument("--requirements", default=None, help="requirements.txt 路径")
    ap.add_argument("--pyproject", default=None, help="pyproject.toml 路径")
    ap.add_argument("--output", default=None, help="输出漏洞清单 CSV 路径")
    ap.add_argument("--offline", action="store_true", help="离线模式（不调用 OSV API）")
    args = ap.parse_args()

    if not args.requirements and not args.pyproject:
        # 默认路径
        default_req = os.path.join(ROOT, "requirements.txt")
        if os.path.exists(default_req):
            args.requirements = default_req
        else:
            print("错误: 请指定 --requirements 或 --pyproject")
            sys.exit(1)

    dep_vuln_scan(args.requirements, args.pyproject, args.output, args.offline)


if __name__ == "__main__":
    main()
