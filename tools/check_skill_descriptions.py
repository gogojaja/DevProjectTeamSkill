#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""description 弱模型适配校验（check_skill_descriptions）
硬门禁（弱模型铁律，见 token_standard.md §2.1）：
1) 每个 SKILL.md frontmatter description 长度必须 150~250 字符；
2) 触发词前置：首句须以「用户/当用户」开头（用户实际会说的话）而非主题标签描述；
3) 禁止中英混排：description 不得包含英文「Load when ...」尾巴（允许专有术语 SRS/ADR/C4/EVM/LSP/AST/team 等）。
返回码 0=通过，1=有不符合项（供 solidify 中止）。
"""
import os, sys, re, glob, json

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.environ.get('SKILLS_DIR', os.path.join(ROOT, '.trae', 'skills'))

MIN_LEN, MAX_LEN = 150, 250
EN_TAIL_RE = re.compile(r'(Load when|when the user|use when)[\s\S]*$', re.I)
# 合法专有术语（可保留在中文 description 中）
ALLOWED_EN = {'SRS','ADR','C4','EVM','ATAM','LSP','AST','PMBOK','IEEE','BABOK','PR',
              'Git','CSV','PDF','PRJ','RTM','Go','No','S0','S1','S2','S3','team',
              'ultrawork','ralph','worktree','Notepad','ProjectMemory','PSM',
              'Teleport','tmux','GitHub','Jira','issue','Architect','CodeReviewer',
              'SecurityReviewer','TestEngineer','PerformanceEngineer'}


def find_skill_files():
    """遍历 .trae/skills 下所有 SKILL.md（含角色包与内嵌子技能）。"""
    files = []
    files += glob.glob(os.path.join(SKILLS_DIR, 'role-*', 'SKILL.md'))
    files += glob.glob(os.path.join(SKILLS_DIR, 'dev-project-team-skill', 'SKILL.md'))
    files += glob.glob(os.path.join(SKILLS_DIR, 'dev-project-team-skill', 'skills', '*', 'SKILL.md'))
    return sorted(files)


def extract_description(content):
    """解析 frontmatter 中 description 字段（单行引号形式）。返回 None 表示缺失/多行。"""
    m = re.search(r'^description:\s*"(.+)"\s*$', content, re.M)
    if not m:
        m = re.search(r"^description:\s*'(.+)'\s*$", content, re.M)
    return m.group(1) if m else None


def has_mixed_english(desc):
    """检测英文尾巴（Load when 等）→ 视为中英混排不合格。"""
    return EN_TAIL_RE.search(desc) is not None


def main():
    files = find_skill_files()
    errors = []
    for f in files:
        with open(f, encoding='utf-8') as fh:
            content = fh.read()
        rel = os.path.relpath(f, SKILLS_DIR)
        desc = extract_description(content)
        if desc is None:
            errors.append(f'[{rel}] description 缺失或未用单行引号形式')
            continue
        n = len(desc)
        if not (MIN_LEN <= n <= MAX_LEN):
            errors.append(f'[{rel}] description 长度 {n} 不在 {MIN_LEN}~{MAX_LEN}')
        if has_mixed_english(desc):
            errors.append(f'[{rel}] 含英文 Load when 尾巴（中英混排），须转中文')
    # 汇总
    if errors:
        print(f'❌ description 校验失败（{len(errors)} 项）：')
        for e in errors:
            print(f'  · {e}')
        return 1
    print(f'✅ description 校验通过（{len(files)} 个 SKILL.md 全部合规：150~250 字符 / 触发词前置 / 无英文尾巴）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
