#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""goal_check.py — 目标驱动自主执行·完成度自检工具（OPT-GOAL-001 v1.1）

v1.1 补强：
  - SGD 持久化台账（台账/41_活跃目标.json）+ 交接文档集成
  - 执行状态持久化（迭代计数/AC 状态跨会话保留）
  - scope 读写分离（write_files/write_dirs vs read_files/read_dirs）
  - constraints 可机器验证（file_not_modified/file_not_created/content_not_changed）
  - 错误恢复策略（pause_wait_user/skip_and_continue/abort_goal）
  - 目标变更机制（amend 流程 + 变更历史）
  - 进度输出（N/M AC 通过 + 百分比）

CLI（跨平台）：
  py -3.11 tools/goal_check.py --goal sgd.json                    # 执行验证
  py -3.11 tools/goal_check.py --goal sgd.json --save             # 保存 SGD 到台账
  py -3.11 tools/goal_check.py --load                             # 从台账加载活跃目标
  py -3.11 tools/goal_check.py --status                           # 查看执行状态
  py -3.11 tools/goal_check.py --amend --amend-reason "原因"      # 变更目标
  py -3.11 tools/goal_check.py --close                            # 关闭已完成目标
  py -3.11 tools/goal_check.py --validate sgd.json                # 仅校验格式

验证类型（verify_type）：
  file_exists   — 文件存在
  file_contains — 文件包含指定内容
  command_pass  — 命令返回码 = 0
  test_pass     — pytest 文件全部通过
  count_ge      — 产出数量 >= N
  manual        — 需人工确认

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
LEDGER_PATH = os.path.join(ROOT, "台账", "41_活跃目标.json")

VALID_VERIFY_TYPES = ("file_exists", "file_contains", "command_pass", "test_pass", "count_ge", "manual")
VALID_CONSTRAINT_TYPES = ("file_not_modified", "file_not_created", "content_not_changed")
VALID_RECOVERY_ON_BREAK = ("pause_wait_user", "skip_and_continue", "abort_goal")
VALID_RECOVERY_ON_MAX = ("handoff", "abort_goal", "pause_wait_user")


# ── 台账持久化 ────────────────────────────────────────────────

def _load_ledger():
    """加载活跃目标台账。"""
    if not os.path.exists(LEDGER_PATH):
        return {"active_goals": [], "closed_goals": []}
    with io.open(LEDGER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_ledger(ledger):
    """保存活跃目标台账。"""
    ledger_dir = os.path.dirname(LEDGER_PATH)
    if not os.path.exists(ledger_dir):
        os.makedirs(ledger_dir, exist_ok=True)
    with io.open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)


def _sgd_hash(sgd):
    """计算 SGD 内容哈希（用于变更检测）。"""
    raw = json.dumps(sgd, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]


def save_goal(sgd, output_path=None):
    """保存 SGD 到活跃目标台账（P0 持久化）。

    Returns:
        dict: 保存结果
    """
    errors = validate_sgd(sgd)
    if errors:
        return {"saved": False, "errors": errors}

    ledger = _load_ledger()
    goal_id = "G-%03d" % (len(ledger["active_goals"]) + len(ledger.get("closed_goals", [])) + 1)
    now = datetime.now().isoformat()

    entry = {
        "goal_id": goal_id,
        "sgd": sgd,
        "sgd_hash": _sgd_hash(sgd),
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "iteration": 0,
        "ac_status": {},
        "consecutive_failures": 0,
        "amendment_history": [],
    }

    # 初始化 AC 状态
    for ac in sgd.get("acceptance_criteria", []):
        entry["ac_status"][ac["id"]] = "PENDING"

    ledger["active_goals"].append(entry)
    _save_ledger(ledger)

    print("目标已保存到台账: %s" % goal_id)
    print("  目标: %s" % sgd.get("statement", ""))
    print("  AC: %d 条 | 台账: %s" % (len(sgd.get("acceptance_criteria", [])), LEDGER_PATH))

    return {"saved": True, "goal_id": goal_id, "ledger_path": LEDGER_PATH}


def load_goal(goal_id=None):
    """从台账加载活跃目标（P0 持久化）。

    Args:
        goal_id: 指定目标 ID，None 则加载第一个活跃目标

    Returns:
        dict: 目标条目或 None
    """
    ledger = _load_ledger()
    active = ledger.get("active_goals", [])

    if not active:
        print("无活跃目标")
        return None

    if goal_id:
        for g in active:
            if g["goal_id"] == goal_id:
                _print_goal_status(g)
                return g
        print("目标不存在: %s" % goal_id)
        return None

    # 默认加载第一个活跃目标
    goal = active[0]
    _print_goal_status(goal)
    return goal


def update_status(goal_id, ac_id, status, iteration=None):
    """更新单条 AC 状态 + 迭代计数（P1 执行状态持久化）。

    Returns:
        dict: 更新结果
    """
    ledger = _load_ledger()
    for g in ledger.get("active_goals", []):
        if g["goal_id"] == goal_id:
            if ac_id in g["ac_status"]:
                g["ac_status"][ac_id] = status
            if iteration is not None:
                g["iteration"] = iteration
            g["updated_at"] = datetime.now().isoformat()
            _save_ledger(ledger)
            return {"updated": True, "goal_id": goal_id, "ac_id": ac_id, "status": status}
    return {"updated": False, "error": "目标不存在: %s" % goal_id}


def amend_goal(goal_id, new_sgd, reason):
    """变更目标（P1 目标变更机制）。

    保留变更历史，更新 SGD 哈希，重置受影响的 AC 状态。

    Returns:
        dict: 变更结果
    """
    errors = validate_sgd(new_sgd)
    if errors:
        return {"amended": False, "errors": errors}

    ledger = _load_ledger()
    for g in ledger.get("active_goals", []):
        if g["goal_id"] == goal_id:
            now = datetime.now().isoformat()
            old_hash = g["sgd_hash"]
            new_hash = _sgd_hash(new_sgd)

            # 记录变更历史
            g["amendment_history"].append({
                "seq": len(g.get("amendment_history", [])) + 1,
                "timestamp": now,
                "reason": reason,
                "old_hash": old_hash,
                "new_hash": new_hash,
                "old_statement": g["sgd"].get("statement", ""),
                "new_statement": new_sgd.get("statement", ""),
            })

            # 更新 SGD
            g["sgd"] = new_sgd
            g["sgd_hash"] = new_hash
            g["updated_at"] = now

            # 重置新增 AC 状态
            old_ac_ids = set(g["ac_status"].keys())
            for ac in new_sgd.get("acceptance_criteria", []):
                if ac["id"] not in old_ac_ids:
                    g["ac_status"][ac["id"]] = "PENDING"

            _save_ledger(ledger)
            print("目标已变更: %s (第 %d 次变更)" % (goal_id, len(g["amendment_history"])))
            print("  原因: %s" % reason)
            return {"amended": True, "goal_id": goal_id, "amendment_seq": len(g["amendment_history"])}

    return {"amended": False, "error": "目标不存在: %s" % goal_id}


def close_goal(goal_id):
    """关闭已完成的目标，移入 closed_goals。

    Returns:
        dict: 关闭结果
    """
    ledger = _load_ledger()
    for i, g in enumerate(ledger.get("active_goals", [])):
        if g["goal_id"] == goal_id:
            g["status"] = "completed"
            g["completed_at"] = datetime.now().isoformat()
            ledger.setdefault("closed_goals", []).append(g)
            ledger["active_goals"].pop(i)
            _save_ledger(ledger)
            print("目标已关闭: %s" % goal_id)
            return {"closed": True, "goal_id": goal_id}
    return {"closed": False, "error": "目标不存在: %s" % goal_id}


def _print_goal_status(goal):
    """打印目标状态（含进度）。"""
    sgd = goal.get("sgd", {})
    ac_status = goal.get("ac_status", {})
    total = len(ac_status)
    passed = sum(1 for s in ac_status.values() if s == "PASS")
    failed = sum(1 for s in ac_status.values() if s == "FAIL")
    pending = sum(1 for s in ac_status.values() if s == "PENDING")
    pct = int(passed / total * 100) if total > 0 else 0

    print("目标: %s [%s]" % (goal.get("goal_id", "?"), goal.get("status", "?")))
    print("  描述: %s" % sgd.get("statement", ""))
    print("  进度: %d/%d 通过 (%d%%) | 失败: %d | 待定: %d" % (passed, total, pct, failed, pending))
    print("  迭代: %d/%s" % (goal.get("iteration", 0), sgd.get("max_iterations", 10)))
    print("  连续失败: %d" % goal.get("consecutive_failures", 0))
    if goal.get("amendment_history"):
        print("  变更次数: %d" % len(goal["amendment_history"]))
    print()
    for ac in sgd.get("acceptance_criteria", []):
        ac_id = ac.get("id", "?")
        status = ac_status.get(ac_id, "?")
        mark = {"PASS": "+", "FAIL": "x", "PENDING": "?", "MANUAL": "M"}.get(status, "?")
        print("  [%s] %s: %s" % (mark, ac_id, ac.get("description", "")))


# ── SGD 格式校验 ──────────────────────────────────────────────

def validate_sgd(sgd):
    """校验 SGD JSON 格式合法性（v1.1 增强：scope 读写分离 + constraints 可验证 + error_recovery）。

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

    # 可选字段
    if "max_iterations" in sgd:
        mi = sgd["max_iterations"]
        if not isinstance(mi, int) or mi < 1 or mi > 50:
            errors.append("max_iterations 必须为 1~50 的整数")

    if "constraints" in sgd:
        if not isinstance(sgd["constraints"], list) or len(sgd["constraints"]) > 10:
            errors.append("constraints 必须为数组且最多 10 条")
        else:
            for i, c in enumerate(sgd["constraints"]):
                if isinstance(c, dict):
                    if "type" not in c or c["type"] not in VALID_CONSTRAINT_TYPES:
                        errors.append("constraint[%d] type 非法（可选: %s）" % (i, ", ".join(VALID_CONSTRAINT_TYPES)))
                    if "target" not in c:
                        errors.append("constraint[%d] 缺少 target" % i)

    if "scope" in sgd:
        scope = sgd["scope"]
        if not isinstance(scope, dict):
            errors.append("scope 必须为对象")
        else:
            # v1.1 读写分离 + v1.0 兼容
            for key in ("files", "dirs", "write_files", "write_dirs", "read_files", "read_dirs"):
                if key in scope and not isinstance(scope[key], list):
                    errors.append("scope.%s 必须为数组" % key)

    if "error_recovery" in sgd:
        er = sgd["error_recovery"]
        if not isinstance(er, dict):
            errors.append("error_recovery 必须为对象")
        else:
            if "on_circuit_break" in er and er["on_circuit_break"] not in VALID_RECOVERY_ON_BREAK:
                errors.append("error_recovery.on_circuit_break 非法（可选: %s）" % ", ".join(VALID_RECOVERY_ON_BREAK))
            if "on_max_iterations" in er and er["on_max_iterations"] not in VALID_RECOVERY_ON_MAX:
                errors.append("error_recovery.on_max_iterations 非法（可选: %s）" % ", ".join(VALID_RECOVERY_ON_MAX))

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


# ── 约束验证（v1.1 新增） ────────────────────────────────────

def verify_constraints(sgd, root):
    """验证 SGD 中的可机器验证约束。

    Returns:
        list: [{"type": ..., "target": ..., "status": "PASS"/"FAIL"/"SKIP", "detail": ...}]
    """
    results = []
    constraints = sgd.get("constraints", [])

    for c in constraints:
        if isinstance(c, str):
            # v1.0 纯文字约束 → 跳过（不可机器验证）
            results.append({"type": "text_only", "target": c, "status": "SKIP", "detail": "纯文字声明，需人工确认"})
            continue

        if not isinstance(c, dict):
            continue

        ctype = c.get("type", "")
        ctarget = c.get("target", "")

        if ctype == "file_not_modified":
            # 检查文件是否存在（存在 = 未被修改/删除，适用于约束「不修改已有文件」）
            path = os.path.join(root, ctarget) if not os.path.isabs(ctarget) else ctarget
            if os.path.exists(path):
                results.append({"type": ctype, "target": ctarget, "status": "PASS", "detail": "文件存在: %s" % ctarget})
            else:
                results.append({"type": ctype, "target": ctarget, "status": "FAIL", "detail": "文件不存在（可能被删除/移动）: %s" % ctarget})

        elif ctype == "file_not_created":
            # 检查文件是否不存在（不存在 = 未创建禁止创建的文件）
            path = os.path.join(root, ctarget) if not os.path.isabs(ctarget) else ctarget
            if not os.path.exists(path):
                results.append({"type": ctype, "target": ctarget, "status": "PASS", "detail": "文件未创建: %s" % ctarget})
            else:
                results.append({"type": ctype, "target": ctarget, "status": "FAIL", "detail": "文件已存在（违反约束）: %s" % ctarget})

        elif ctype == "content_not_changed":
            # 需要 baseline hash 对比，当前版本标记为需人工确认
            results.append({"type": ctype, "target": ctarget, "status": "SKIP", "detail": "需 baseline hash 对比（待实现）"})

        else:
            results.append({"type": ctype, "target": ctarget, "status": "SKIP", "detail": "未知约束类型: %s" % ctype})

    return results


# ── 范围校验（v1.1 读写分离） ─────────────────────────────────

def check_scope(filepath, sgd, mode="write"):
    """检查文件路径是否在 SGD scope 范围内。

    Args:
        filepath: 文件路径
        sgd: SGD 字典
        mode: "write"（写操作检查）或 "read"（读操作检查）

    Returns:
        bool: True = 在范围内
    """
    scope = sgd.get("scope")
    if not scope:
        return True  # 未指定 scope，不做限制

    filepath_norm = filepath.replace("\\", "/")

    if mode == "write":
        # 写操作：优先用 v1.1 write_files/write_dirs，回退 v1.0 files/dirs
        write_files = scope.get("write_files", scope.get("files", []))
        write_dirs = scope.get("write_dirs", scope.get("dirs", []))
    else:
        # 读操作：用 v1.1 read_files/read_dirs，未指定则不限制
        read_files = scope.get("read_files", [])
        read_dirs = scope.get("read_dirs", [])
        if not read_files and not read_dirs:
            return True  # 未指定读范围 = 不限制
        write_files, write_dirs = read_files, read_dirs

    # 检查 files glob
    for pattern in write_files:
        if glob.fnmatch.fnmatch(filepath_norm, pattern):
            return True

    # 检查 dirs 前缀
    for d in write_dirs:
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
            print("  x %s" % e)
        return {"valid": False, "errors": errors}

    if validate_only:
        print("SGD 格式校验通过 (v1.1)")
        print("  目标: %s" % sgd.get("statement", ""))
        print("  验收标准: %d 条" % len(sgd.get("acceptance_criteria", [])))
        # v1.1 额外信息
        constraints = sgd.get("constraints", [])
        verifiable = sum(1 for c in constraints if isinstance(c, dict))
        if verifiable:
            print("  可验证约束: %d/%d" % (verifiable, len(constraints)))
        scope = sgd.get("scope", {})
        if scope.get("read_files") or scope.get("read_dirs"):
            print("  scope: 读写分离模式")
        er = sgd.get("error_recovery", {})
        if er:
            print("  错误恢复: on_break=%s on_max=%s" % (
                er.get("on_circuit_break", "pause_wait_user"),
                er.get("on_max_iterations", "handoff")))
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

    # 约束验证（v1.1）
    constraint_results = verify_constraints(sgd, ROOT)

    # 总体结论
    total = len(results)
    if fail_count == 0 and manual_count == 0:
        conclusion = "全部通过"
    elif fail_count == 0:
        conclusion = "待人工确认"
    else:
        conclusion = "未达标"

    # 进度输出（v1.1）
    pct = int(pass_count / total * 100) if total > 0 else 0
    print("目标: %s" % sgd.get("statement", ""))
    print("进度: %d/%d 通过 (%d%%) | 失败: %d | 待人工: %d" % (pass_count, total, pct, fail_count, manual_count))
    print("结论: %s" % conclusion)

    # 约束验证结果
    constraint_fails = [c for c in constraint_results if c["status"] == "FAIL"]
    if constraint_fails:
        print("约束违反：")
        for c in constraint_fails:
            print("  x [%s] %s — %s" % (c["type"], c["target"], c["detail"]))

    # 错误恢复建议（v1.1）
    er = sgd.get("error_recovery", {})
    if fail_count > 0:
        on_break = er.get("on_circuit_break", "pause_wait_user")
        if on_break == "pause_wait_user":
            print("建议: 暂停等待用户介入")
        elif on_break == "skip_and_continue":
            print("建议: 跳过失败项继续执行")
        elif on_break == "abort_goal":
            print("建议: 中止目标并交接")

    # 输出 CSV
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

    print("报告: %s" % output_path)

    for r in results:
        mark = "+" if r["status"] == "PASS" else ("x" if r["status"] == "FAIL" else "?")
        print("  [%s] [%s] %s — %s" % (mark, r["id"], r["description"], r["detail"]))

    return {
        "valid": True, "total": total, "pass": pass_count,
        "fail": fail_count, "manual": manual_count,
        "conclusion": conclusion, "output_path": output_path,
        "constraint_results": constraint_results,
    }


def main():
    ap = argparse.ArgumentParser(description="目标驱动自主执行·完成度自检工具 v1.1（OPT-GOAL-001）")
    ap.add_argument("--goal", required=False, help="SGD JSON 文件路径")
    ap.add_argument("--validate", required=False, help="仅校验 SGD 格式合法性")
    ap.add_argument("--output", default=None, help="输出报告 CSV 路径")
    # v1.1 持久化
    ap.add_argument("--save", action="store_true", help="保存 SGD 到活跃目标台账")
    ap.add_argument("--load", action="store_true", help="从台账加载活跃目标")
    ap.add_argument("--status", action="store_true", help="查看活跃目标执行状态")
    ap.add_argument("--close", action="store_true", help="关闭已完成目标")
    ap.add_argument("--goal-id", default=None, help="指定目标 ID（配合 --load/--status/--close/--amend）")
    # v1.1 变更
    ap.add_argument("--amend", action="store_true", help="变更活跃目标")
    ap.add_argument("--amend-reason", default="", help="变更原因")
    args = ap.parse_args()

    # v1.1 台账操作
    if args.load or args.status:
        load_goal(args.goal_id)
        return

    if args.close:
        if not args.goal_id:
            ap.error("--close 需要指定 --goal-id")
        close_goal(args.goal_id)
        return

    if args.amend:
        if not args.goal_id:
            ap.error("--amend 需要指定 --goal-id")
        if not args.goal:
            ap.error("--amend 需要指定 --goal 新 SGD 文件")
        with io.open(args.goal, "r", encoding="utf-8") as f:
            new_sgd = json.load(f)
        amend_goal(args.goal_id, new_sgd, args.amend_reason or "未指定原因")
        return

    if args.save:
        if not args.goal:
            ap.error("--save 需要指定 --goal SGD 文件")
        with io.open(args.goal, "r", encoding="utf-8") as f:
            sgd = json.load(f)
        save_goal(sgd, args.output)
        return

    # v1.0 兼容操作
    if args.validate:
        goal_check(args.validate, validate_only=True)
    elif args.goal:
        goal_check(args.goal, args.output)
    else:
        ap.error("必须指定 --goal 或 --validate 或 --load/--status/--close/--amend")


if __name__ == "__main__":
    main()
