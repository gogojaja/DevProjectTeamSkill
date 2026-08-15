#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版本一致性校验（check_version_consistency）
硬门禁：
1) 每个角色包 SKILL.md 元数据「技能版本」行 == 文档页脚「文档版本」行（必须一致）；
2) 每个维护产出的技能必须具备闭环执行系统与关键执行门禁（任务入口/执行状态/验收门禁/失败处理/产出交接/审计）。
软提示：变更记录最新一条是否含元数据版本号；8 包版本横向分布。
返回码 0=通过，1=硬门禁不一致/闭环门禁不通过（供 solidify 中止）。
"""
import os, sys, re

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.environ.get('SKILLS_DIR', os.path.join(ROOT, '.trae', 'skills'))
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
             'role-architecture','role-development','role-testing','role-deployment','role-governance']

VRE = re.compile(r'技能版本\*\*[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)')       # 元数据行
FRE = re.compile(r'\*\*文档版本\*\*[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)')   # 页脚
CRE = re.compile(r'^\s*[-*]\s*v([0-9]+\.[0-9]+\.[0-9]+)')                 # 变更记录条目
CLOSURE_REQUIRED = [
    '任务入口',
    '执行状态',
    '验收门禁',
    '失败处理',
    '产出与交接',
    '审计记录',
]


def check_closure_section(content):
    """校验技能是否具备闭环执行系统的关键章节与门禁。"""
    if re.search(r'(?m)^(#+\s*)?闭环执行系统\s*$', content) is None:
        return False
    for key in CLOSURE_REQUIRED:
        if key not in content:
            return False
    return True

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
        p = os.path.join(SKILLS_DIR, r, 'SKILL.md')
        content = open(p, encoding='utf-8').read()

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

        # 闭环执行能力门禁：必须具备标准章节和关键要素
        if not check_closure_section(content):
            print(f'  ✗ {r:<40} 闭环执行门禁未通过：缺少 "闭环执行系统" 或关键要素（任务入口/执行状态/验收门禁/失败处理/产出与交接/审计记录）')
            hard += 1
        else:
            print(f'  ✓ {r:<40} 闭环执行门禁通过')

        # 轻量契约校验：检查 SKILL.md 正文（跳过 frontmatter）前 1200 字是否包含任务契约要点
        # （正文前部为元数据+变更记录，触发规则/任务入口区通常在 400~900 字处）
        body = content.split('---', 2)[2] if content.startswith('---') else content
        head = body[:1200]
        required_keys = ['目标', '触发', '不适用', '输入', '输出', '回退', '失败']
        if not any(k in head for k in required_keys):
            print(f'  ✗ {r:<40} 任务契约要点缺失（正文前1200字未包含目标/触发/输入/输出/回退等关键词）')
            hard += 1
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