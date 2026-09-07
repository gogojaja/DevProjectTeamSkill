#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""env_compare.py — T-12 投产环境比对器

读取各环境配置 → 逐项比对 → 差异标注 → 风险评级。
解决痛点 P13（环境差异导致投产故障）。

CLI（跨平台）：
  py -3.11 tools/env_compare.py --env-dev dev.json --env-test test.json --env-prod prod.json
  py -3.11 tools/env_compare.py --env-dev dev.json --env-prod prod.json --output diff.csv

配置格式（JSON）：
  {"env_name": "dev", "items": {"DB_HOST": "localhost", "DB_PORT": "5432", ...}}

  也支持 .env 格式：
  DB_HOST=localhost
  DB_PORT=5432

输出：
  差异清单 CSV（UTF-8 BOM）：配置项,dev值,test值,prod值,风险标注

依赖：无
"""
import os
import sys
import io
import csv
import json
import re
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

# ── 风险标注规则 ──
RISK_RULES = {
    "password": "高（密码差异）",
    "secret": "高（密钥差异）",
    "token": "高（令牌差异）",
    "key": "中（密钥路径差异）",
    "host": "中（主机差异）",
    "port": "中（端口差异）",
    "url": "中（URL 差异）",
    "db": "中（数据库差异）",
    "version": "低（版本差异）",
    "timeout": "低（超时差异）",
    "debug": "低（调试开关差异）",
}


def _load_env_file(path):
    """加载环境配置文件，返回 dict。支持 JSON 和 .env 格式。"""
    if not os.path.exists(path):
        print("错误: 文件不存在: %s" % path)
        sys.exit(1)

    ext = os.path.splitext(path)[1].lower()
    data = {}

    if ext == ".json":
        with io.open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # 支持嵌套 {"env_name": "...", "items": {...}} 或直接 {...}
        if "items" in raw and isinstance(raw["items"], dict):
            data = {str(k): str(v) for k, v in raw["items"].items()}
        else:
            data = {str(k): str(v) for k, v in raw.items()}
    else:
        # .env 格式
        with io.open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip().strip('"').strip("'")

    return data


def _assess_risk(key):
    """根据配置项名称评估风险等级。"""
    key_lower = key.lower()
    for pattern, risk in RISK_RULES.items():
        if pattern in key_lower:
            return risk
    return "低"


def env_compare(env_paths, output_path=None):
    """环境比对主入口。

    Args:
        env_paths: dict {"dev": path, "test": path, "prod": path}（test 可选）
        output_path: 输出 CSV 路径

    Returns:
        dict: 比对结果摘要
    """
    envs = {}
    for env_name, path in env_paths.items():
        if path:
            envs[env_name] = _load_env_file(path)

    if len(envs) < 2:
        print("错误: 至少需要 2 个环境配置")
        sys.exit(1)

    # 收集所有配置项
    all_keys = set()
    for env_data in envs.values():
        all_keys.update(env_data.keys())

    # 逐项比对
    results = []
    diff_count = 0

    env_names = sorted(envs.keys())
    for key in sorted(all_keys):
        values = {}
        for en in env_names:
            values[en] = envs[en].get(key, "（未配置）")

        # 检查是否有差异
        unique_vals = set(values.values())
        if len(unique_vals) <= 1:
            continue  # 无差异，跳过

        diff_count += 1
        risk = _assess_risk(key)

        row = {"config_key": key}
        for en in env_names:
            row[en] = values[en]
        row["risk"] = risk
        results.append(row)

    # 输出
    if not output_path:
        report_dir = os.path.join(ROOT, "docs", "reviews")
        os.makedirs(report_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        output_path = os.path.join(report_dir, "环境比对_%s.csv" % date_str)

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    fieldnames = ["config_key"] + env_names + ["risk"]
    with io.open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    high_risk = len([r for r in results if r["risk"].startswith("高")])
    print("环境比对完成：")
    for en in env_names:
        print("  %s: %s（%d 项）" % (en, env_paths.get(en, "-"), len(envs.get(en, {}))))
    print("  总配置项: %d | 有差异: %d" % (len(all_keys), diff_count))
    print("  高风险: %d | 输出: %s" % (high_risk, output_path))
    if high_risk > 0:
        print("  ⚠ 高风险差异 %d 项，投产前须确认" % high_risk)
    return {"total_keys": len(all_keys), "diff_count": diff_count, "high_risk": high_risk, "output_path": output_path}


def main():
    ap = argparse.ArgumentParser(description="T-12 投产环境比对器")
    ap.add_argument("--env-dev", required=True, help="开发环境配置路径")
    ap.add_argument("--env-test", default=None, help="测试环境配置路径（可选）")
    ap.add_argument("--env-prod", required=True, help="生产环境配置路径")
    ap.add_argument("--output", default=None, help="输出差异清单 CSV 路径")
    args = ap.parse_args()

    env_paths = {"dev": args.env_dev, "prod": args.env_prod}
    if args.env_test:
        env_paths["test"] = args.env_test

    env_compare(env_paths, args.output)


if __name__ == "__main__":
    main()
