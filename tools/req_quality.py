#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""req_quality.py — T-11 需求质量自动检查器

检查需求文档质量：歧义词检测 + 完整性检查 + 可测性评分 → 质量评分卡 CSV。
解决痛点 P10（需求质量人工评估主观性强）。

CLI（跨平台）：
  py -3.11 tools/req_quality.py --input <需求CSV或JSON> --output <评分卡CSV>
  py -3.11 tools/req_quality.py --input requirements.csv --rules rules.yaml

输入格式（CSV）：
  需求编号,需求描述,验收标准,边界条件,备注
  REQ-001,用户应快速登录,登录<3s,超时提示,

输入格式（JSON）：
  {"requirements":[
    {"id":"REQ-001","description":"...","acceptance":"...","boundary":"..."}
  ]}

输出：
  质量评分卡 CSV（UTF-8 BOM）：需求编号,歧义词数,完整性得分,可测性得分,总分,主要问题

依赖：无（可选 PyYAML 加载规则文件）
"""
import os
import sys
import io
import csv
import json
import argparse
import re

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 歧义词库 ──
AMBIGUOUS_TERMS = {
    # 程度模糊
    "快速": "应量化具体指标（如 <3s）",
    "尽快": "应明确截止时间",
    "适当": "应给出具体范围",
    "尽量": "应明确是否必须",
    "大致": "应给出精确范围",
    "差不多": "应量化容差",
    "基本上": "应明确例外情况",
    "一般": "应给出具体标准",
    # 范围模糊
    "等等": "应穷举或明确范围",
    "其他": "应列举具体项",
    "相关": "应明确关联项",
    "某些": "应列举具体项",
    "各种": "应列举具体类型",
    # 强度模糊
    "应该": "区分「必须」与「建议」",
    "可以": "区分「允许」与「可选」",
    "需要": "区分「必须」与「建议」",
    "可能": "明确是否允许不确定性",
    "或许": "应明确是否支持",
    # 时间模糊
    "暂时": "应明确持续时间",
    "目前": "应标注截止日期",
    "以后": "应明确时间节点",
}

# ── 默认规则 ──
DEFAULT_RULES = {
    "ambiguous_terms": AMBIGUOUS_TERMS,
    "completeness_weights": {
        "acceptance_criteria": 0.4,
        "boundary_conditions": 0.3,
        "priority": 0.15,
        "dependencies": 0.15,
    },
    "testability_keywords": [
        "秒", "ms", "%", "个", "次", "条", "倍",
        "大于", "小于", "等于", "不超过", "至少",
        "通过", "失败", "成功", "错误",
    ],
}


def _load_rules(rules_path=None):
    """加载规则（YAML/JSON），无则用默认。"""
    if rules_path and os.path.exists(rules_path):
        ext = os.path.splitext(rules_path)[1].lower()
        with io.open(rules_path, "r", encoding="utf-8") as f:
            if ext in (".yaml", ".yml"):
                try:
                    import yaml
                    return yaml.safe_load(f)
                except ImportError:
                    print("警告: PyYAML 未安装，使用默认规则")
            elif ext == ".json":
                return json.load(f)
    return DEFAULT_RULES


def _load_requirements(input_path):
    """加载需求列表，支持 CSV 和 JSON。"""
    ext = os.path.splitext(input_path)[1].lower()
    reqs = []

    if ext == ".json":
        with io.open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for r in data.get("requirements", []):
            reqs.append({
                "id": r.get("id", ""),
                "description": r.get("description", ""),
                "acceptance": r.get("acceptance", ""),
                "boundary": r.get("boundary", ""),
                "priority": r.get("priority", ""),
                "dependencies": r.get("dependencies", ""),
            })
    elif ext == ".csv":
        with io.open(input_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                reqs.append({
                    "id": row.get("需求编号", row.get("id", "")),
                    "description": row.get("需求描述", row.get("description", "")),
                    "acceptance": row.get("验收标准", row.get("acceptance", "")),
                    "boundary": row.get("边界条件", row.get("boundary", "")),
                    "priority": row.get("优先级", row.get("priority", "")),
                    "dependencies": row.get("依赖", row.get("dependencies", "")),
                })
    else:
        print("错误: 不支持的格式 %s（支持 .csv / .json）" % ext)
        sys.exit(1)

    return reqs


def check_ambiguous(text, rules):
    """检测歧义词，返回 (数量, 命中列表)。"""
    terms = rules.get("ambiguous_terms", AMBIGUOUS_TERMS)
    found = []
    for term, hint in terms.items():
        if term in text:
            found.append("%s（%s）" % (term, hint))
    return len(found), found


def check_completeness(req, rules):
    """检查完整性，返回得分 0~100。"""
    weights = rules.get("completeness_weights", DEFAULT_RULES["completeness_weights"])
    score = 0
    missing = []

    if req.get("acceptance", "").strip():
        score += weights.get("acceptance_criteria", 0.4) * 100
    else:
        missing.append("缺验收标准")

    if req.get("boundary", "").strip():
        score += weights.get("boundary_conditions", 0.3) * 100
    else:
        missing.append("缺边界条件")

    if req.get("priority", "").strip():
        score += weights.get("priority", 0.15) * 100
    else:
        missing.append("缺优先级")

    if req.get("dependencies", "").strip():
        score += weights.get("dependencies", 0.15) * 100
    else:
        missing.append("缺依赖")

    return int(score), missing


def check_testability(description, rules):
    """评估可测性，返回得分 0~100。"""
    keywords = rules.get("testability_keywords", DEFAULT_RULES["testability_keywords"])
    found = sum(1 for kw in keywords if kw in description)
    # 有量化指标 → 高分；纯定性 → 低分
    if found >= 3:
        return 90
    elif found >= 1:
        return 60
    else:
        return 30


def assess_quality(input_path, output_path=None, rules_path=None):
    """需求质量评估主入口。

    Args:
        input_path: 需求文件路径（CSV/JSON）
        output_path: 输出评分卡路径
        rules_path: 规则文件路径（可选）

    Returns:
        dict: 评估结果摘要
    """
    if not os.path.exists(input_path):
        print("错误: 文件不存在: %s" % input_path)
        sys.exit(1)

    rules = _load_rules(rules_path)
    reqs = _load_requirements(input_path)

    if not reqs:
        print("警告: 需求列表为空")
        return {"total": 0, "avg_score": 0}

    if not output_path:
        base = os.path.splitext(os.path.basename(input_path))[0]
        report_dir = os.path.join(ROOT, "docs", "reviews")
        os.makedirs(report_dir, exist_ok=True)
        output_path = os.path.join(report_dir, "需求质量评分卡_%s.csv" % base)

    results = []
    total_score = 0

    for req in reqs:
        desc = req.get("description", "")
        # 歧义词检测
        amb_count, amb_found = check_ambiguous(desc, rules)
        # 完整性检查
        comp_score, comp_missing = check_completeness(req, rules)
        # 可测性评分
        test_score = check_testability(desc, rules)

        # 总分 = 完整性 * 0.5 + 可测性 * 0.3 + (100 - 歧义词*15) * 0.2
        amb_penalty = min(amb_count * 15, 100)
        total = int(comp_score * 0.5 + test_score * 0.3 + (100 - amb_penalty) * 0.2)
        total_score += total

        # 主要问题
        issues = []
        if amb_found:
            issues.append("歧义词: %s" % "、".join(amb_found[:3]))
        if comp_missing:
            issues.append("、".join(comp_missing))
        if test_score < 60:
            issues.append("可测性不足（缺量化指标）")

        results.append({
            "req_id": req.get("id", ""),
            "ambiguous_count": amb_count,
            "completeness_score": comp_score,
            "testability_score": test_score,
            "total_score": total,
            "issues": "；".join(issues) if issues else "无",
        })

    # 写入评分卡
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with io.open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "req_id", "ambiguous_count", "completeness_score",
            "testability_score", "total_score", "issues"
        ])
        writer.writeheader()
        writer.writerows(results)

    avg = total_score // len(results) if results else 0
    print("需求质量评估完成：")
    print("  输入: %s（%d 条需求）" % (input_path, len(reqs)))
    print("  输出: %s" % output_path)
    print("  平均得分: %d/100" % avg)
    if avg >= 80:
        print("  结论: 良好（可进入架构设计）")
    elif avg >= 60:
        print("  结论: 一般（建议补充验收标准后进入下一阶段）")
    else:
        print("  结论: 不足（需需求澄清后再流转）")
    return {"total": len(results), "avg_score": avg, "output_path": output_path}


def main():
    ap = argparse.ArgumentParser(description="T-11 需求质量自动检查器")
    ap.add_argument("--input", required=True, help="需求文件路径（CSV/JSON）")
    ap.add_argument("--output", default=None, help="输出评分卡 CSV 路径")
    ap.add_argument("--rules", default=None, help="规则文件路径（YAML/JSON，可选）")
    args = ap.parse_args()
    assess_quality(args.input, args.output, args.rules)


if __name__ == "__main__":
    main()
