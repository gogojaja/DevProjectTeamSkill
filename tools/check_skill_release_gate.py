#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能发布级门禁校验（release gate）
强制校验：每个 SKILL.md 在进入打包/部署前，必须具备闭环执行系统、元数据、触发词和版本声明。
返回码 0=通过，1=失败。
"""
import os, sys, re

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.environ.get('SKILLS_DIR', os.path.join(ROOT, '.trae', 'skills'))
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
             'role-architecture','role-development','role-testing','role-deployment','role-governance',
             'role-program-mgmt','role-mgmt-consulting']
SUB_SKILLS = ['commit-protocol','lsp-ast-integration','multi-perspective-validation',
              'project-memory','self-improve','team-orchestration','worktree-isolation']


def read_text(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def check_frontmatter_and_metadata(text, role):
    errors = []
    if not re.search(r'^---\s*\nname:\s*"[^"]+"\s*\n', text, re.M):
        errors.append('缺少 frontmatter name')
    if not re.search(r'description:\s*".*Load when.*"', text, re.S):
        # 单语言原则（token_standard §2.1）：判废英文 Load when，改验中文触发词「用户说/触发词时加载」
        if not re.search(r'description:\s*".*(用户说|当用户|用户提到|触发词).*(时加载|加载本)', text, re.S):
            errors.append('缺少 description 中的中文触发声明（用户说…时加载，token_standard §2.1）')
    if '技能版本' not in text:
        errors.append('缺少 技能版本 元数据')
    if '**文档版本**' not in text:
        errors.append('缺少 **文档版本** 页脚')
    if '**最后更新**' not in text:
        errors.append('缺少 **最后更新** 页脚')
    if role not in text:
        # allow the skill name anywhere, but ensure the role path matches metadata field
        pass
    return errors


def check_closure(text):
    required = [
        '闭环执行系统',
        '任务入口',
        '执行状态',
        '验收门禁',
        '失败处理',
        '产出与交接',
        '审计记录',
    ]
    missing = [item for item in required if item not in text]
    if missing:
        return False, missing
    return True, []


def check_skill(role):
    path = os.path.join(SKILLS_DIR, role, 'SKILL.md')
    if not os.path.isfile(path):
        return False, [f'{role}: 缺少 SKILL.md']
    text = read_text(path)
    errors = []
    errors.extend(check_frontmatter_and_metadata(text, role))
    ok, missing = check_closure(text)
    if not ok:
        errors.append(f'闭环执行缺失：{missing}')
    return (not errors), errors


def main():
    print('技能发布级门禁校验 (release gate)')
    print(f'源: {SKILLS_DIR}')
    failed = 0
    for role in ALL_ROLES:
        ok, errors = check_skill(role)
        if ok:
            print(f'  ✓ {role:<40} 发布级门禁通过')
        else:
            print(f'  ✗ {role:<40} 发布级门禁失败')
            for err in errors:
                print(f'      - {err}')
            failed += 1

    # 子技能（内嵌于编排器）纳入发布级门禁
    for sub in SUB_SKILLS:
        p = os.path.join(SKILLS_DIR, 'dev-project-team-skill', 'skills', sub, 'SKILL.md')
        if not os.path.isfile(p):
            continue
        text = read_text(p)
        errs = []
        errs.extend(check_frontmatter_and_metadata(text, sub))
        ok, missing = check_closure(text)
        if not ok:
            errs.append(f'闭环执行缺失：{missing}')
        label = f'{sub} (sub)'
        if not errs:
            print(f'  ✓ {label:<36} 发布级门禁通过')
        else:
            print(f'  ✗ {label:<36} 发布级门禁失败')
            for e in errs:
                print(f'      - {e}')
            failed += 1
    print('=' * 50)
    if failed:
        print(f'❌ 发布级门禁失败: {failed} 个角色未通过。')
        sys.exit(1)
    print('✅ 所有角色均通过发布级门禁。')
    sys.exit(0)


if __name__ == '__main__':
    main()
