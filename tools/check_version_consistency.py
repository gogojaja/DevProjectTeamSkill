#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版本一致性校验（check_version_consistency）
硬门禁：每个角色包 SKILL.md 元数据「技能版本」行 == 文档页脚「文档版本」行（必须一致）。
软提示：变更记录最新一条是否含元数据版本号；8 包版本横向分布。
返回码 0=通过，1=硬门禁不一致（供 solidify 中止）。
"""
import os, sys, re

sys.stdout.reconfigure(encoding='utf-8')

SKILLS_DIR = os.environ.get('SKILLS_DIR', r'D:\trae\DevProjectTeamSkill\.trae\skills')
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
             'role-architecture','role-development','role-testing','role-deployment','role-governance']

VRE = re.compile(r'技能版本\*\*[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)')       # 元数据行
FRE = re.compile(r'\*\*文档版本\*\*[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)')   # 页脚
CRE = re.compile(r'^\s*[-*]\s*v([0-9]+\.[0-9]+\.[0-9]+)')                 # 变更记录条目

def check_role(role):
    p = os.path.join(SKILLS_DIR, role, 'SKILL.md')
    if not os.path.isfile(p):
        return None
    c = open(p, encoding='utf-8').read()
    ver = (VRE.search(c).group(1) if VRE.search(c) else None)
    foot = (FRE.search(c).group(1) if FRE.search(c) else None)
    chg = None
    for line in c.splitlines():
        m = CRE.match(line)
        if m:
            chg = 'v' + m.group(1)
            break
    return (ver, foot, chg)

def main():
    print('版本一致性校验 (version consistency check)')
    print(f'源: {SKILLS_DIR}')
    hard = 0
    soft = 0
    versions = {}
    for r in ALL_ROLES:
        got = check_role(r)
        if got is None:
            print(f'  ✗ {r:<40} 缺少 SKILL.md')
            hard += 1
            continue
        ver, foot, chg = got
        versions[r] = ver
        # 硬门禁：元数据 == 页脚
        if not (ver and foot and ver == foot):
            print(f'  ✗ {r:<40} 硬门禁: 元数据={ver} 页脚={foot} 不一致')
            hard += 1
        else:
            # 软提示：变更记录最新条应含元数据版本
            if chg and chg != ver:
                print(f'  ~ {r:<40} 软提示: 变更记录最新={chg} ≠ 元数据={ver}')
                soft += 1
            else:
                print(f'  ✓ {r:<40} {ver}')
    uniq = sorted(set(v for v in versions.values() if v))
    if len(uniq) > 1:
        print(f'  · 跨包版本分布: {uniq}（各包独立演进，允许差异）')
    print('=' * 50)
    if hard:
        print(f'❌ 硬门禁失败: {hard} 项元数据/页脚版本不一致。请统一后重试。')
        sys.exit(1)
    print(f'✅ 硬门禁通过（{soft} 项软提示可人工确认）。')
    sys.exit(0)

if __name__ == '__main__':
    main()