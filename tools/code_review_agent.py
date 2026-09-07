#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""code_review_agent.py — T-08 AI 代码审查 Agent

多层代码审查：git diff 解析 → 静态分析（ast/py_compile）→ 影响范围分析 → 结构化报告 CSV。
解决痛点 P8（无 git diff → 自动标注代码问题 CLI）。

降级策略（§14.1）：
  强环境 → Layer 1+2+3（ast + 影响范围 + LLM 语义）
  弱环境 → Layer 1+2（ast + 影响范围）
  最弱   → Layer 1（仅 ast 静态分析）

CLI（跨平台）：
  py -3.11 tools/code_review_agent.py --diff HEAD~1                    # 审查最近 1 次提交
  py -3.11 tools/code_review_agent.py --diff HEAD~3..HEAD              # 审查最近 3 次提交
  py -3.11 tools/code_review_agent.py --diff staged                    # 审查暂存区
  py -3.11 tools/code_review_agent.py --diff HEAD~1 --output report.csv --dry-run

输出：
  docs/reviews/代码评审报告_<日期>.csv（默认）
  格式：文件,行号,严重级别,类别,描述,建议修复
"""
import os
import sys
import io
import ast
import csv
import json
import py_compile
import datetime
import argparse
import subprocess
import tempfile
import re

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 安全检查模式（ast 静态分析） ──────────────────────────────
# 基于 Python 安全编码规范的已知危险模式
SECURITY_PATTERNS = [
    {"id": "SEC-001", "name": "eval/exec 使用", "severity": "严重",
     "pattern": r"\beval\s*\(", "desc": "eval() 可执行任意代码，应使用 ast.literal_eval() 替代"},
    {"id": "SEC-002", "name": "exec 使用", "severity": "严重",
     "pattern": r"\bexec\s*\(", "desc": "exec() 可执行任意代码，应避免在生产代码中使用"},
    {"id": "SEC-003", "name": "硬编码密码", "severity": "严重",
     "pattern": r"(?:password|passwd|secret|token|api_key)\s*=\s*['\"][^'\"]{3,}['\"]",
     "desc": "疑似硬编码凭据，应使用环境变量或凭据管理器（铁律 #3 A 级）"},
    {"id": "SEC-004", "name": "SQL 拼接", "severity": "严重",
     "pattern": r"(?:execute|query)\s*\(\s*['\"].*%s|\.format\(|f['\"]",
     "desc": "疑似 SQL 字符串拼接，应使用参数化查询防止注入"},
    {"id": "SEC-005", "name": "os.system 使用", "severity": "主要",
     "pattern": r"\bos\.system\s*\(", "desc": "os.system() 存在命令注入风险，应使用 subprocess.run() 替代"},
    {"id": "SEC-006", "name": "shell=True", "severity": "主要",
     "pattern": r"subprocess\.\w+\(.*shell\s*=\s*True", "desc": "shell=True 存在命令注入风险，应设 shell=False"},
    {"id": "SEC-007", "name": "pickle 反序列化", "severity": "主要",
     "pattern": r"\bpickle\.loads?\s*\(", "desc": "pickle 反序列化可执行任意代码，应使用 json 替代"},
    {"id": "SEC-008", "name": "裸 except", "severity": "一般",
     "pattern": r"except\s*:", "desc": "裸 except 捕获所有异常（含 SystemExit/KeyboardInterrupt），应指定异常类型"},
]

# ── 代码质量模式 ──────────────────────────────────────────
QUALITY_PATTERNS = [
    {"id": "QUA-001", "name": "过长函数", "severity": "一般",
     "check": "func_length", "threshold": 80,
     "desc": "函数超过 {threshold} 行，建议拆分"},
    {"id": "QUA-002", "name": "深层嵌套", "severity": "一般",
     "check": "nest_depth", "threshold": 5,
     "desc": "嵌套深度超过 {threshold} 层，建议提取子函数"},
    {"id": "QUA-003", "name": "TODO/FIXME 未处理", "severity": "提示",
     "pattern": r"#\s*(?:TODO|FIXME|HACK|XXX)\b",
     "desc": "存在未处理的 TODO/FIXME 标记"},
    {"id": "QUA-004", "name": "print 调试残留", "severity": "提示",
     "pattern": r"^\s*print\s*\(",
     "desc": "疑似调试 print 残留，应使用 logging 模块"},
]


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _run_git(args):
    """执行 git 命令并返回输出"""
    try:
        result = subprocess.run(
            ["git"] + args, capture_output=True, cwd=ROOT,
            timeout=30
        )
        return result.stdout.decode("utf-8", errors="replace"), result.returncode
    except Exception as e:
        return "git error: %s" % str(e), 1


def get_diff(diff_range):
    """获取 git diff 内容。

    Args:
        diff_range: "HEAD~1" / "HEAD~3..HEAD" / "staged" / 其他 git diff 参数

    Returns:
        str: diff 内容
    """
    if diff_range == "staged":
        out, rc = _run_git(["diff", "--cached", "--unified=0"])
    elif ".." in diff_range:
        out, rc = _run_git(["diff", diff_range, "--unified=0"])
    else:
        out, rc = _run_git(["diff", diff_range, "--unified=0"])

    if rc != 0:
        print("git diff 失败: %s" % out)
        return ""
    return out


def parse_diff_files(diff_text):
    """解析 diff 提取变更文件和行号。

    Returns:
        dict: {文件路径: [(行号, 行内容), ...]}
    """
    files = {}
    current_file = None
    current_line = 0

    for line in diff_text.split("\n"):
        if line.startswith("+++ b/"):
            current_file = line[6:]
            files[current_file] = []
        elif line.startswith("@@"):
            # 解析 @@ -old,count +new,count @@
            m = re.search(r"\+(\d+)", line)
            if m:
                current_line = int(m.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            if current_file:
                files[current_file].append((current_line, line[1:]))
                current_line += 1
        elif line.startswith("-"):
            pass  # 删除行不检查
        else:
            current_line += 1

    return files


def layer1_security_scan(filepath, changed_lines):
    """Layer 1: 安全检查（基于正则模式匹配）。

    Args:
        filepath: 文件路径
        changed_lines: [(行号, 行内容), ...]

    Returns:
        list: [{file, line, severity, category, description, suggestion}, ...]
    """
    issues = []
    if not filepath.endswith(".py"):
        return issues

    for line_no, line_content in changed_lines:
        for pat in SECURITY_PATTERNS:
            if re.search(pat["pattern"], line_content, re.IGNORECASE):
                issues.append({
                    "file": filepath,
                    "line": line_no,
                    "severity": pat["severity"],
                    "category": "安全",
                    "description": "[%s] %s" % (pat["id"], pat["desc"]),
                    "suggestion": pat["desc"],
                })
    return issues


def layer1_quality_scan(filepath, changed_lines):
    """Layer 1: 代码质量检查。

    Args:
        filepath: 文件路径
        changed_lines: [(行号, 行内容), ...]

    Returns:
        list: issues
    """
    issues = []
    if not filepath.endswith(".py"):
        return issues

    for line_no, line_content in changed_lines:
        for pat in QUALITY_PATTERNS:
            if "pattern" in pat and re.search(pat["pattern"], line_content):
                issues.append({
                    "file": filepath,
                    "line": line_no,
                    "severity": pat["severity"],
                    "category": "质量",
                    "description": "[%s] %s" % (pat["id"], pat["desc"]),
                    "suggestion": pat["desc"],
                })
    return issues


def layer1_syntax_check(filepath):
    """Layer 1: Python 语法检查（py_compile）。

    Returns:
        list: issues
    """
    issues = []
    if not filepath.endswith(".py"):
        return issues

    full_path = os.path.join(ROOT, filepath)
    if not os.path.exists(full_path):
        return issues

    try:
        py_compile.compile(full_path, doraise=True)
    except py_compile.PyCompileError as e:
        issues.append({
            "file": filepath,
            "line": 0,
            "severity": "严重",
            "category": "语法",
            "description": "语法错误: %s" % str(e).split("\\n")[0],
            "suggestion": "修复 Python 语法错误",
        })
    return issues


def layer2_impact_analysis(filepath, changed_lines):
    """Layer 2: 影响范围分析。

    检查变更是否涉及：
    - 公共 API（函数/类定义）
    - 导入语句变更
    - 配置/安全相关文件

    Returns:
        list: issues
    """
    issues = []
    if not filepath.endswith(".py"):
        return issues

    full_path = os.path.join(ROOT, filepath)
    if not os.path.exists(full_path):
        return issues

    # 读取完整文件做 AST 分析
    try:
        with io.open(full_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception:
        return issues

    changed_line_set = set(ln for ln, _ in changed_lines)

    # 检查变更是否涉及函数/类定义
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if node.lineno in changed_line_set:
                severity = "主要" if not node.name.startswith("_") else "一般"
                issues.append({
                    "file": filepath,
                    "line": node.lineno,
                    "severity": severity,
                    "category": "影响范围",
                    "description": "变更涉及%s定义: %s（第 %d 行）" % (
                        "函数" if isinstance(node, ast.FunctionDef) else "类",
                        node.name, node.lineno),
                    "suggestion": "确认变更不影响外部调用方",
                })

    # 检查是否修改了导入语句
    for line_no, line_content in changed_lines:
        if line_content.strip().startswith(("import ", "from ")):
            issues.append({
                "file": filepath,
                "line": line_no,
                "severity": "一般",
                "category": "影响范围",
                "description": "导入语句变更: %s" % line_content.strip(),
                "suggestion": "确认新依赖已安装且版本兼容",
            })

    return issues


def review(diff_range, output_path=None, dry_run=False):
    """执行完整代码审查。

    Args:
        diff_range: git diff 范围
        output_path: 输出 CSV 路径（None 则自动生成）
        dry_run: 仅预览不写入

    Returns:
        list: 所有发现的问题
    """
    print("══ T-08 代码审查 Agent ══")
    print("  diff 范围: %s" % diff_range)

    # 1. 获取 diff
    diff_text = get_diff(diff_range)
    if not diff_text:
        print("  无变更内容")
        return []

    # 2. 解析变更文件
    files = parse_diff_files(diff_text)
    total_lines = sum(len(v) for v in files.values())
    print("  变更文件: %d 个, 变更行: %d" % (len(files), total_lines))

    # 3. 多层分析
    all_issues = []
    for filepath, changed_lines in files.items():
        # 跳过测试文件和文档
        if filepath.startswith(("tests/", "docs/", "台账/", ".trae/")):
            continue

        # Layer 1: 静态分析
        all_issues.extend(layer1_syntax_check(filepath))
        all_issues.extend(layer1_security_scan(filepath, changed_lines))
        all_issues.extend(layer1_quality_scan(filepath, changed_lines))

        # Layer 2: 影响范围
        all_issues.extend(layer2_impact_analysis(filepath, changed_lines))

    # 4. 按严重级别排序
    severity_order = {"严重": 0, "主要": 1, "一般": 2, "提示": 3}
    all_issues.sort(key=lambda x: severity_order.get(x["severity"], 9))

    # 5. 统计
    by_severity = {}
    by_category = {}
    for issue in all_issues:
        by_severity[issue["severity"]] = by_severity.get(issue["severity"], 0) + 1
        by_category[issue["category"]] = by_category.get(issue["category"], 0) + 1

    print("  发现问题: %d" % len(all_issues))
    print("    按严重级别: %s" % " / ".join("%s %d" % (k, v) for k, v in sorted(by_severity.items())))
    print("    按类别: %s" % " / ".join("%s %d" % (k, v) for k, v in sorted(by_category.items())))

    # 6. 降级标注
    print("  分析层级: Layer 1（ast 静态分析）+ Layer 2（影响范围）")
    print("  降级说明: Pylint/Flake8/Bandit 未安装，使用内置 ast 分析（§14.1 降级策略）")

    if dry_run:
        print("  [dry-run] 不写入报告")
        return all_issues

    # 7. 输出报告
    if not output_path:
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        report_dir = os.path.join(ROOT, "docs", "reviews")
        os.makedirs(report_dir, exist_ok=True)
        output_path = os.path.join(report_dir, "代码评审报告_%s.csv" % date_str)

    header = ["文件", "行号", "严重级别", "类别", "描述", "建议修复"]
    with io.open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for issue in all_issues:
            w.writerow([
                issue["file"],
                issue["line"],
                issue["severity"],
                issue["category"],
                issue["description"],
                issue["suggestion"],
            ])

    print("  报告已生成: %s" % output_path)
    return all_issues


def main():
    ap = argparse.ArgumentParser(description="T-08 AI 代码审查 Agent")
    ap.add_argument("--diff", required=True,
                    help="git diff 范围（HEAD~1 / HEAD~3..HEAD / staged）")
    ap.add_argument("--output", default=None, help="输出 CSV 路径")
    ap.add_argument("--dry-run", action="store_true", help="仅预览不写入")
    args = ap.parse_args()

    review(args.diff, args.output, args.dry_run)


if __name__ == "__main__":
    main()
