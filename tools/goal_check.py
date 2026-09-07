#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""goal_check.py — 目标驱动自主执行·完成度自检工具（OPT-GOAL-001）

读取 SGD（结构化目标定义）JSON → 逐项验证验收标准 → 输出 CSV 报告。

CLI（跨平台）：
  py -3.11 tools/goal_check.py --goal sgd.json
  py -3.11 tools/goal_check.py --goal sgd.json --output report.csv
  py -3.11 tools/goal_check.py --validate sgd.json          # 仅校验 SGD 格式合法性

验证类型（verify_type）：
  file_exists   — 文件存在
  file_contains — 文件包含指定内容
  command_pass  — 命令返回码 = 0
  test_pass     — pytest 文件全部通过
  count_ge      — 产出数量 ≥ N
  manual        — 需人工确认（自动标记 FAIL + 备注）

依赖：无（标准库）
"""
import os
import sys
import io
import csv
import json
import glob
import argparse
import subprocess

# Windows 控制台 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VALID_VERIFY_TYPES = ("file_exists", "file_contains", "command_pass", "test_pass", "count_ge", "manual")


# ── SGD 格式校验 ──────────────────────────────────────────────

def validate_sgd(sgd):
    """校验 SGD JSON 格式合法性。

    Returns:
        list: 错误列表（空 = 合法）
    """
    errors = []

    # 必填字段
    if "statement" not in sgd:
        errors.append("缺少必填字段: statement")
    elif not isinstance(sgd["statement"], str) or len(sgd["statement"]) < 5:
        errors.append("statement 必须为 5~200 字符的字符串")

    if "acceptance_criteria" not in sgd:
        errors.append("缺少必填字段: acceptance_criteria")
    elif not isinstance(sgd["acceptance_criteria"], list):
        errors.append("acceptance_criteria 必须为数组")
    elif len(sgd["acceptance_criteria"]) < 1:
        errors.append("acceptance_criteria 至少 1 条")
    elif len(sgd["acceptance_criteria"]) > 20:
        errors.append("acceptance_criteria 最多 20 条")
    else:
        for i, ac in enumerate(sgd["acceptance_criteria"]):
            if not isinstance(ac, dict):
                errors.append("AC[%d] 必须为对象" % i)
                continue
            if "id" not in ac:
                errors.append("AC[%d] 缺少 id" % i)
            elif not isinstance(ac["id"], str) or not ac["id"].startswith("AC-"):
                errors.append("AC[%d] id 格式错误（需 AC-N）" % i)
            if "description" not in ac:
                errors.append("AC[%d] 缺少 description" % i)
            if "verify_type" not in ac:
                errors.append("AC[%d] 缺少 verify_type" % i)
            elif ac["verify_type"] not in VALID_VERIFY_TYPES:
                errors.append("AC[%d] verify_type 非法: %s（可选: %s）" % (i, ac["verify_type"], ", ".join(VALID_VERIFY_TYPES)))

    # 可选字段校验
    if "max_iterations" in sgd:
        mi = sgd["max_iterations"]
        if not isinstance(mi, int) or mi < 1 or mi > 50:
            errors.append("max_iterations 必须为 1~50 的整数")

    if "constraints" in sgd:
        if not isinstance(sgd["constraints"], list) or len(sgd["constraints"]) > 10:
            errors.append("constraints 必须为数组且最多 10 条")

    if "scope" in sgd:
        scope = sgd["scope"]
        if not isinstance(scope, dict):
            errors.append("scope 必须为对象")
        else:
            for key in ("files", "dirs"):
                if key in scope and not isinstance(scope[key], list):
                    errors.append("scope.%s 必须为数组" % key)

    return errors


# ── 验收标准验证 ──────────────────────────────────────────────

def verify_ac(ac, root):
    """验证单条验收标准。

    Returns:
        dict: {"status": "PASS"/"FAIL"/"MANUAL", "detail": "..."}
    """
    vtype = ac.get("verify_type", "")
    target = ac.get("verify_target", "")
    arg = ac.get("verify_arg", "")

    if vtype == "manual":
        return {"status": "MANUAL", "detail": "需人工确认: %s" % ac.get("description", "")}

    if vtype == "file_exists":
        path = os.path.join(root, target) if not os.path.isabs(target) else target
        if os.path.exists(path):
            return {"status": "PASS", "detail": "文件存在: %s" % target}
        return {"status": "FAIL", "detail": "文件不存在: %s" % target}

    if vtype == "file_contains":
        path = os.path.join(root, target) if not os.path.isabs(target) else target
        if not os.path.exists(path):
            return {"status": "FAIL", "detail": "文件不存在: %s" % target}
        try:
            with io.open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if arg in content:
                return {"status": "PASS", "detail": "文件包含 '%s'" % arg}
            return {"status": "FAIL", "detail": "文件不包含 '%s'" % arg}
        except Exception as e:
            return {"status": "FAIL", "detail": "读取失败: %s" % str(e)}

    if vtype == "command_pass":
        try:
            r = subprocess.run(
                target, shell=True, cwd=root,
                capture_output=True, timeout=30
            )
            if r.returncode == 0:
                return {"status": "PASS", "detail": "命令成功: %s" % target[:60]}
            return {"status": "FAIL", "detail": "命令失败(rc=%d): %s" % (r.returncode, target[:60])}
        except subprocess.TimeoutExpired:
            return {"status": "FAIL", "detail": "命令超时(30s): %s" % target[:60]}
        except Exception as e:
            return {"status": "FAIL", "detail": "命令异常: %s" % str(e)}

    if vtype == "test_pass":
        test_path = os.path.join(root, target) if not os.path.isabs(target) else target
        if not os.path.exists(test_path):
            return {"status": "FAIL", "detail": "测试文件不存在: %s" % target}
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
                cwd=root, capture_output=True, timeout=60
            )
            if r.returncode == 0:
                return {"status": "PASS", "detail": "测试全部通过: %s" % target}
            return {"status": "FAIL", "detail": "测试失败(rc=%d): %s" % (r.returncode, target)}
        except subprocess.TimeoutExpired:
            return {"status": "FAIL", "detail": "测试超时(60s): %s" % target}
        except Exception as e:
            return {"status": "FAIL", "detail": "测试异常: %s" % str(e)}

    if vtype == "count_ge":
        pattern = target
        try:
            threshold = int(arg) if arg else 1
        except ValueError:
            return {"status": "FAIL", "detail": "count_ge 阈值非整数: %s" % arg}
        matches = glob.glob(os.path.join(root, pattern))
        count = len(matches)
        if count >= threshold:
            return {"status": "PASS", "detail": "数量 %d >= %d (%s)" % (count, threshold, pattern)}
        return {"status": "FAIL", "detail": "数量 %d < %d (%s)" % (count, threshold, pattern)}

    return {"status": "FAIL", "detail": "未知 verify_type: %s" % vtype}


# ── 范围校验 ──────────────────────────────────────────────────

def check_scope(filepath, sgd):
    """检查文件路径是否在 SGD scope 范围内。

    Returns:
        bool: True = 在范围内
    """
    scope = sgd.get("scope")
    if not scope:
        return True  # 未指定 scope，不做限制

    filepath_norm = filepath.replace("\\", "/")

    # 检查 files glob
    for pattern in scope.get("files", []):
        if glob.fnmatch.fnmatch(filepath_norm, pattern):
            return True

    # 检查 dirs 前缀
    for d in scope.get("dirs", []):
        d_norm = d.replace("\\", "/").rstrip("/")
        if filepath_norm.startswith(d_norm + "/") or filepath_norm == d_norm:
            return True

    return False


# ── 主入口 ────────────────────────────────────────────────────

def goal_check(goal_path, output_path=None, validate_only=False):
    """完成度自检主入口。

    Args:
        goal_path: SGD JSON 文件路径
        output_path: 输出 CSV 路径
        validate_only: 仅校验格式

    Returns:
        dict: 检查结果摘要
    """
    if not os.path.exists(goal_path):
        print("错误: SGD 文件不存在: %s" % goal_path)
        sys.exit(1)

    with io.open(goal_path, "r", encoding="utf-8") as f:
        sgd = json.load(f)

    # 格式校验
    errors = validate_sgd(sgd)
    if errors:
        print("SGD 格式校验失败：")
        for e in errors:
            print("  ✗ %s" % e)
        return {"valid": False, "errors": errors}

    if validate_only:
        print("SGD 格式校验通过 ✓")
        print("  目标: %s" % sgd.get("statement", ""))
        print("  验收标准: %d 条" % len(sgd.get("acceptance_criteria", [])))
        return {"valid": True, "errors": []}

    # 逐项验证
    results = []
    pass_count = 0
    fail_count = 0
    manual_count = 0

    for ac in sgd.get("acceptance_criteria", []):
        result = verify_ac(ac, ROOT)
        row = {
            "id": ac.get("id", "?"),
            "description": ac.get("description", ""),
            "verify_type": ac.get("verify_type", ""),
            "status": result["status"],
            "detail": result["detail"],
        }
        results.append(row)
        if result["status"] == "PASS":
            pass_count += 1
        elif result["status"] == "FAIL":
            fail_count += 1
        else:
            manual_count += 1

    # 总体结论
    total = len(results)
    if fail_count == 0 and manual_count == 0:
        conclusion = "全部通过"
    elif fail_count == 0:
        conclusion = "待人工确认"
    else:
        conclusion = "未达标"

    # 输出
    if not output_path:
        os.makedirs(os.path.join(ROOT, "docs", "reviews"), exist_ok=True)
        output_path = os.path.join(ROOT, "docs", "reviews", "goal_check_report.csv")

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with io.open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "description", "verify_type", "status", "detail"])
        writer.writeheader()
        writer.writerows(results)

    # 控制台输出
    print("目标: %s" % sgd.get("statement", ""))
    print("验收标准: %d 条 | 通过: %d | 失败: %d | 待人工: %d" % (total, pass_count, fail_count, manual_count))
    print("结论: %s" % conclusion)
    print("报告: %s" % output_path)

    for r in results:
        mark = "✓" if r["status"] == "PASS" else ("✗" if r["status"] == "FAIL" else "?")
        print("  %s [%s] %s — %s" % (mark, r["id"], r["description"], r["detail"]))

    return {
        "valid": True, "total": total, "pass": pass_count,
        "fail": fail_count, "manual": manual_count,
        "conclusion": conclusion, "output_path": output_path,
    }


def main():
    ap = argparse.ArgumentParser(description="目标驱动自主执行·完成度自检工具（OPT-GOAL-001）")
    ap.add_argument("--goal", required=False, help="SGD JSON 文件路径")
    ap.add_argument("--validate", required=False, help="仅校验 SGD 格式合法性")
    ap.add_argument("--output", default=None, help="输出报告 CSV 路径")
    args = ap.parse_args()

    if args.validate:
        goal_check(args.validate, validate_only=True)
    elif args.goal:
        goal_check(args.goal, args.output)
    else:
        ap.error("必须指定 --goal 或 --validate")


if __name__ == "__main__":
    main()
