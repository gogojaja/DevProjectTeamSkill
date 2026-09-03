#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步项目群所有项目进展到 30_program_progress.csv
流程：
1. 对本地存在的项目执行 git pull 更新到最新版本
2. 读取各项目的台账文件
3. 汇总生成 30_program_progress.csv
"""

import os
import subprocess
import csv
import sys
from datetime import datetime
from pathlib import Path

# 项目群成员项目（本地存在的）
PROJECTS = [
    "DevProjectTeamSkill",
    "TwinForge",
    "dev-git-hub",
    "dev-task-scheduler",
    "dev-model-router",
    "dev-project-mgmt",
    "dev-security-tools",
    "dev-test-tools",
    "bank-it-pm-complete",
    "lark-training-ppt-generator",
    "Project-management",
    "free-api-hub",
    "ex-post-supervision",
]

BASE_DIR = Path(r"D:\Myprojects")
TARGET_CSV = BASE_DIR / "DevProjectTeamSkill" / "台账" / "30_program_progress.csv"


def run_git_pull(project_dir: Path) -> tuple[bool, str]:
    """执行 git pull，返回 (成功与否, 输出信息)"""
    try:
        # 检查是否是 git 仓库
        git_dir = project_dir / ".git"
        if not git_dir.exists():
            return False, f"非 git 仓库: {project_dir}"
        
        # 获取当前分支
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        branch = result.stdout.strip() or "main"
        
        # 执行 git pull
        result = subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return True, result.stdout.strip() or "已是最新"
        else:
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "超时"
    except Exception as e:
        return False, str(e)


def read_project_ledger(project_dir: Path, project_name: str) -> list[dict]:
    """读取项目的台账文件，提取里程碑进展信息"""
    ledger_dir = project_dir / "台账"
    if not ledger_dir.exists():
        return []
    
    milestones = []
    
    # 优先查找进度相关的台账文件
    progress_files = [
        "30_program_progress.csv",  # 项目群主进度（如果项目自己也维护）
        "18_迭代配置.csv",          # 迭代配置
        "19_迭代回顾.csv",          # 迭代回顾
        "00_阶段配置.csv",          # 阶段配置
        "06_范围变更台账.csv",      # 范围变更
        "22_阶段复盘.csv",          # 阶段复盘
    ]
    
    for fname in progress_files:
        fpath = ledger_dir / fname
        if fpath.exists():
            try:
                with open(fpath, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # 尝试提取里程碑信息
                        milestone = extract_milestone(row, fname, project_name)
                        if milestone:
                            milestones.append(milestone)
            except Exception as e:
                print(f"  读取 {fname} 失败: {e}")
    
    return milestones


def extract_milestone(row: dict, source_file: str, project_name: str) -> dict | None:
    """从台账行提取里程碑信息"""
    # 不同文件的字段映射
    if source_file == "30_program_progress.csv":
        return {
            "项目": project_name,
            "里程碑": row.get("里程碑", ""),
            "计划日期": row.get("计划日期", ""),
            "实际日期": row.get("实际日期", ""),
            "偏差(天)": row.get("偏差(天)", ""),
            "SPI": row.get("SPI", ""),
            "关键路径标记": row.get("关键路径标记", ""),
            "状态": row.get("状态", ""),
            "责任方": row.get("责任方", ""),
            "更新记录": row.get("更新记录", ""),
            "更新日期": row.get("更新日期", datetime.now().strftime("%Y-%m-%d")),
        }
    
    elif source_file == "18_迭代配置.csv":
        # 迭代配置：迭代编号、开始日期、结束日期、目标、状态
        iteration = row.get("迭代编号") or row.get("迭代") or ""
        if iteration:
            return {
                "项目": project_name,
                "里程碑": f"迭代 {iteration}",
                "计划日期": row.get("开始日期", ""),
                "实际日期": row.get("实际开始日期", row.get("开始日期", "")),
                "偏差(天)": "",
                "SPI": "",
                "关键路径标记": "否",
                "状态": row.get("状态", "进行中"),
                "责任方": row.get("负责人", ""),
                "更新记录": f"迭代目标: {row.get('目标', '')}",
                "更新日期": datetime.now().strftime("%Y-%m-%d"),
            }
    
    elif source_file == "19_迭代回顾.csv":
        iteration = row.get("迭代") or row.get("迭代编号") or ""
        if iteration:
            return {
                "项目": project_name,
                "里程碑": f"迭代 {iteration} 复盘",
                "计划日期": row.get("计划日期", ""),
                "实际日期": row.get("实际日期", row.get("复盘日期", "")),
                "偏差(天)": "",
                "SPI": "",
                "关键路径标记": "否",
                "状态": "已完成",
                "责任方": row.get("主持人", ""),
                "更新记录": f"复盘结论: {row.get('结论', row.get('改进项', ''))[:100]}",
                "更新日期": datetime.now().strftime("%Y-%m-%d"),
            }
    
    elif source_file == "00_阶段配置.csv":
        phase = row.get("阶段") or row.get("阶段名称") or ""
        if phase:
            return {
                "项目": project_name,
                "里程碑": f"阶段 {phase}",
                "计划日期": row.get("计划开始", row.get("开始日期", "")),
                "实际日期": row.get("实际开始", row.get("开始日期", "")),
                "偏差(天)": "",
                "SPI": "",
                "关键路径标记": "否",
                "状态": row.get("状态", "进行中"),
                "责任方": row.get("负责人", ""),
                "更新记录": f"阶段目标: {row.get('目标', '')[:100]}",
                "更新日期": datetime.now().strftime("%Y-%m-%d"),
            }
    
    elif source_file == "22_阶段复盘.csv":
        phase = row.get("阶段") or ""
        if phase:
            return {
                "项目": project_name,
                "里程碑": f"阶段 {phase} 复盘",
                "计划日期": row.get("计划日期", ""),
                "实际日期": row.get("复盘日期", row.get("实际日期", "")),
                "偏差(天)": "",
                "SPI": "",
                "关键路径标记": "否",
                "状态": "已完成",
                "责任方": row.get("主持人", ""),
                "更新记录": f"复盘结论: {row.get('结论', row.get('行动项', ''))[:100]}",
                "更新日期": datetime.now().strftime("%Y-%m-%d"),
            }
    
    return None


def main():
    print("=" * 60)
    print("项目群进展同步开始")
    print("=" * 60)
    
    all_milestones = []
    
    # 1. 逐个项目执行 git pull 并读取台账
    for project_name in PROJECTS:
        project_dir = BASE_DIR / project_name
        print(f"\n[{project_name}]")
        
        if not project_dir.exists():
            print(f"  目录不存在，跳过")
            continue
        
        # Git pull
        print(f"  执行 git pull...")
        success, msg = run_git_pull(project_dir)
        if success:
            print(f"  [OK] {msg}")
        else:
            print(f"  [FAIL] {msg}")
        
        # 读取台账
        print(f"  读取台账...")
        milestones = read_project_ledger(project_dir, project_name)
        print(f"  提取到 {len(milestones)} 条里程碑记录")
        all_milestones.extend(milestones)
    
    # 2. 去重（按 项目+里程碑+计划日期）
    seen = set()
    unique_milestones = []
    for m in all_milestones:
        key = (m["项目"], m["里程碑"], m["计划日期"])
        if key not in seen:
            seen.add(key)
            unique_milestones.append(m)
    
    print(f"\n去重后共 {len(unique_milestones)} 条记录")
    
    # 3. 按项目、计划日期排序
    unique_milestones.sort(key=lambda x: (x["项目"], x["计划日期"] or "9999-12-31"))
    
    # 4. 写入目标 CSV
    fieldnames = ["项目", "里程碑", "计划日期", "实际日期", "偏差(天)", "SPI", "关键路径标记", "状态", "责任方", "更新记录", "更新日期"]
    
    # 备份原文件
    if TARGET_CSV.exists():
        backup_path = TARGET_CSV.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d%H%M%S')}.csv")
        TARGET_CSV.rename(backup_path)
        print(f"\n原文件已备份到: {backup_path}")
    
    with open(TARGET_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_milestones)
    
    print(f"\n[OK] 已写入 {TARGET_CSV} ({len(unique_milestones)} 条记录)")
    
    # 5. 显示前几行预览
    print("\n预览（前 10 行）:")
    with open(TARGET_CSV, 'r', encoding='utf-8-sig') as f:
        for i, line in enumerate(f):
            if i < 11:
                print(line.rstrip())
            else:
                break
    
    print("\n" + "=" * 60)
    print("同步完成")
    print("=" * 60)


if __name__ == "__main__":
    main()