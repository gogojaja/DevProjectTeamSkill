#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能闭环执行门禁校验（check_skill_closure）
强制校验：每个维护产出的 SKILL.md 必须具备《闭环执行系统》章节，以及
任务入口、执行状态、验收门禁、失败处理、产出与交接、审计记录等关键要素。
返回码 0=通过，1=失败。
"""
import os, sys, re

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.environ.get('SKILLS_DIR', os.path.join(ROOT, '.trae', 'skills'))
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
             'role-architecture','role-development','role-testing','role-deployment','role-governance',
             'role-program-mgmt','role-mgmt-consulting','role-project-mgmt']
SUB_SKILLS = ['best-practice-solution','commit-protocol','incubator-initiation','lsp-ast-integration','model-selection','multi-perspective-validation',
              'project-memory','self-improve','team-orchestration','worktree-isolation',
              'customize-opencode']

REQUIRED_KEYS = [
    '任务入口',
    '执行状态',
    '验收门禁',
    '失败处理',
    '产出与交接',
    '审计记录',
]


def check_closure(content):
    if re.search(r'(?m)^\s*#+\s*(?:\d+\.\s*)?闭环执行系统\s*$', content) is None:
        return False, '缺少 "闭环执行系统" 标题'
    for key in REQUIRED_KEYS:
        if key not in content:
            return False, f'缺少关键章节: {key}'
    if '统一引用 `../shared/closure_execution_template.md`' not in content and 'closure_execution_template.md' not in content:
        # 允许模板引用缺失时保留最小门禁，但在维护模式中建议强制引用模板
        pass
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
    for sub in SUB_SKILLS:
        path = os.path.join(SKILLS_DIR, 'dev-project-team-skill', 'skills', sub, 'SKILL.md')
        label = f'{sub} (sub)'
        if not os.path.isfile(path):
            print(f'  ~ {label:<36} 未安装（跳过）')
            continue
        with open(path, encoding='utf-8') as fh:
            content = fh.read()
        ok, reason = check_closure(content)
        if ok:
            print(f'  ✓ {label:<36} 闭环执行门禁通过')
        else:
            print(f'  ✗ {label:<36} {reason}')
            failed += 1

    print('=' * 50)
    if failed:
        print(f'❌ 闭环门禁失败: {failed} 个角色未满足维护标准。')
        sys.exit(1)

    print('✅ 所有角色均满足闭环执行门禁。')
    sys.exit(0)


if __name__ == '__main__':
    main()
