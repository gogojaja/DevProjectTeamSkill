#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SKILL.md 描述规范检查工具
检查 description 长度是否在 150~250 字符范围内
"""

import re
from pathlib import Path
from typing import List, Tuple, Dict

def extract_description(skill_md_path: Path) -> Tuple[str, str, int]:
    """提取 SKILL.md 中的 description
    
    Args:
        skill_md_path: SKILL.md 文件路径
        
    Returns:
        (description, status, length)
    """
    content = skill_md_path.read_text(encoding="utf-8")
    
    # 解析 frontmatter 中的 description 字段（单行引号形式），与 check_skill_descriptions.py 口径一致
    fm = re.search(r'^description:\s*"(.+)"\s*$', content, re.M)
    if not fm:
        fm = re.search(r"^description:\s*'(.+)'\s*$", content, re.M)
    description = fm.group(1).strip() if fm else ""

    # 保留中文标点（、。：（）等），仅归一化空白；不得过滤中文标点而低估长度
    description = re.sub(r"\s+", " ", description).strip()
    
    length = len(description)
    status = "PASS" if 150 <= length <= 250 else "FAIL"
    
    return description, status, length

def check_all_skills(skills_dir: Path) -> List[Dict]:
    """检查所有 SKILL.md 文件
    
    Args:
        skills_dir: 技能目录路径
        
    Returns:
        检查结果列表
    """
    results = []
    
    # 查找所有 SKILL.md 文件
    skill_files = list(skills_dir.glob("**/SKILL.md"))
    
    for skill_file in skill_files:
        package_name = skill_file.parent.name
        description, status, length = extract_description(skill_file)
        
        result = {
            "package": package_name,
            "file": str(skill_file.relative_to(skills_dir)),
            "description": description,
            "length": length,
            "status": status,
            "min_required": 150,
            "max_required": 250
        }
        
        results.append(result)
    
    return results

def main():
    """主函数"""
    import sys
    
    # 默认技能目录
    skills_dir = Path(__file__).parent.parent / ".trae" / "skills"
    
    if len(sys.argv) > 1:
        skills_dir = Path(sys.argv[1])
    
    if not skills_dir.exists():
        print(f"错误：技能目录不存在 {skills_dir}")
        return 1
    
    print(f"检查目录: {skills_dir}\n")
    print("=" * 80)
    
    results = check_all_skills(skills_dir)
    
    # 输出结果
    for result in results:
        status_symbol = "✓" if result["status"] == "PASS" else "✗"
        status_text = "通过" if result["status"] == "PASS" else "失败"
        
        print(f"{status_symbol} {result['package']}")
        print(f"  文件: {result['file']}")
        print(f"  长度: {result['length']} 字符 (要求: 150~250)")
        print(f"  状态: {status_text}")
        if result["status"] == "FAIL":
            print(f"  描述: {result['description']}")
        print()
    
    # 汇总
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = len(results) - passed
    
    print("=" * 80)
    print(f"汇总: {len(results)} 个角色包, {passed} 个通过, {failed} 个失败")
    
    if failed > 0:
        print("\n需要修复的角色包:")
        for result in results:
            if result["status"] == "FAIL":
                print(f"  - {result['package']}: {result['length']} 字符")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())