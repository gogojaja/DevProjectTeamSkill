#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能闭环执行门禁校验（check_skill_closure）
强制校验：每个维护产出的 SKILL.md 必须具备《闭环执行系统》章节，以及
任务入口、执行状态、验收门禁、失败处理、产出与交接、审计记录等关键要素。
返回码 0=通过，1=失败。
"""
import os, sys, re

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.environ.get('SKILLS_DIR', os.path.join(ROOT, '.trae', 'skills'))
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
             'role-architecture','role-development','role-testing','role-deployment','role-governance']

REQUIRED_KEYS = [
    '任务入口',
    '执行状态',
    '验收门禁',
    '失败处理',
    '产出与交接',
    '审计记录',
]


def check_closure(content):
    if re.search(r'(?m)^(#+\s*)?闭环执行系统\s*$', content) is None:
        return False, '缺少 "闭环执行系统" 标题'
    for key in REQUIRED_KEYS:
        if key not in content:
            return False, f'缺少关键章节: {key}'
    return True, 'ok'


def main():
    print('技能闭环执行门禁校验 (skill closure check)')
    print(f'源: {SKILLS_DIR}')
    failed = 0
    for role in ALL_ROLES:
        path = os.path.join(SKILLS_DIR, role, 'SKILL.md')
        if not os.path.isfile(path):
            print(f'  ✗ {role:<40} 缺少 SKILL.md')
            failed += 1
            continue
        with open(path, encoding='utf-8') as fh:
            content = fh.read()
        ok, reason = check_closure(content)
        if ok:
            print(f'  ✓ {role:<40} 闭环执行门禁通过')
        else:
            print(f'  ✗ {role:<40} {reason}')
            failed += 1

    print('=' * 50)
    if failed:
        print(f'❌ 闭环门禁失败: {failed} 个角色未满足维护标准。')
        sys.exit(1)

    print('✅ 所有角色均满足闭环执行门禁。')
    sys.exit(0)


if __name__ == '__main__':
    main()
