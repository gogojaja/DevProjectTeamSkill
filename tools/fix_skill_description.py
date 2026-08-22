#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SKILL.md 描述修复工具
自动修复不符合长度规范的 description
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List

# 默认描述模板，用于补充长度不够的描述
DEFAULT_EXTENSIONS = {
    "architecture": "，遵循ISO/IEC/IEEE 42010标准，支持4+1视图与C4模型。",
    "development": "，遵循编码规范与安全最佳实践。",
    "governance": "，支持五维评审与门禁管理。",
    "deployment": "，支持分阶段发布与回滚预案。",
    "testing": "，支持测试策略制定与缺陷管理。",
    "requirements": "，支持IEEE 830 SRS编写。",
    "deployment": "，支持分阶段发布与回滚预案。",
    "testing": "，支持测试策略制定与缺陷管理。",
    "deployment": "，支持分阶段发布与回滚预案。",
    "testing": "，支持测试策略制定与缺陷管理。",
}

def extract_frontmatter(content: str) -> tuple:
    """提取 YAML frontmatter 和内容
    
    Returns:
        (frontmatter_dict, rest_content)
    """
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if frontmatter_match:
        try:
            frontmatter = yaml.safe_load(frontmatter_match.group(1))
            rest_content = frontmatter_match.group(2)
            return frontmatter, rest_content
        except yaml.YAMLError:
            pass
    
    return {}, content

def fix_description_length(description: str, package_name: str) -> str:
    """修复描述长度
    
    Args:
        description: 原描述
        package_name: 包名
        
    Returns:
        修复后的描述
    """
    # 移除多余空格
    description = re.sub(r'\s+', ' ', description).strip()
    length = len(description)
    
    # 长度已经在范围内，不需要修复
    if 150 <= length <= 250:
        return description
    
    # 长度不足，添加扩展
    if length < 150:
        extension = DEFAULT_EXTENSIONS.get(package_name, "，支持全生命周期管理。")
        return description + extension
    
    # 长度超限，需要截断
    if length > 250:
        # 尝试保留主要内容
        truncated = description[:247] + "..."
        return truncated
    
    return description

def fix_skill_description(skill_md_path: Path) -> bool:
    """修复单个 SKILL.md 的 description
    
    Args:
        skill_md_path: SKILL.md 文件路径
        
    Returns:
        是否修复成功
    """
    try:
        content = skill_md_path.read_text(encoding="utf-8")
        frontmatter, rest_content = extract_frontmatter(content)
        
        if "description" not in frontmatter:
            print(f"警告：{skill_md_path} 中没有找到 description 字段")
            return False
        
        old_description = frontmatter["description"]
        package_name = skill_md_path.parent.name
        new_description = fix_description_length(old_description, package_name)
        
        if old_description == new_description:
            print(f"跳过：{skill_md_path}（描述长度已符合要求）")
            return False
        
        # 更新 frontmatter
        frontmatter["description"] = new_description
        
        # 重建文件内容
        new_frontmatter = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
        new_content = f"---\n{new_frontmatter}---\n{rest_content}"
        
        skill_md_path.write_text(new_content, encoding="utf-8")
        
        print(f"修复：{skill_md_path}")
        print(f"  旧长度：{len(old_description)} -> 新长度：{len(new_description)}")
        print(f"  新描述：{new_description}")
        
        return True
        
    except Exception as e:
        print(f"错误：修复 {skill_md_path} 时出错：{e}")
        return False

def main():
    """主函数"""
    import sys
    
    skills_dir = Path(__file__).parent.parent / ".trae" / "skills"
    
    if len(sys.argv) > 1:
        skills_dir = Path(sys.argv[1])
    
    if not skills_dir.exists():
        print(f"错误：技能目录不存在 {skills_dir}")
        return 1
    
    print(f"修复目录: {skills_dir}\n")
    print("=" * 80)
    
    # 查找所有 SKILL.md 文件
    skill_files = list(skills_dir.glob("**/SKILL.md"))
    
    fixed_count = 0
    for skill_file in skill_files:
        if fix_skill_description(skill_file):
            fixed_count += 1
        print()
    
    print("=" * 80)
    print(f"修复完成：共修复 {fixed_count} 个文件")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())