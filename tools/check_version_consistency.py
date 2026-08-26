#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版本一致性校验（check_version_consistency）
硬门禁：
1) 每个角色包 SKILL.md 元数据「技能版本」行 == 文档页脚「文档版本」行（必须一致）；
2) 每个维护产出的技能必须具备闭环执行系统与关键执行门禁（任务入口/执行状态/验收门禁/失败处理/产出交接/审计）。
3) 内嵌子技能（SUB_SKILLS）元数据==页脚，且 `domain/*.md` 头部版本行 == 该子技能 SKILL.md 版本（v21.7.5 扩展）。
软提示：变更记录最新一条是否含元数据版本号；10 包版本横向分布。
返回码 0=通过，1=硬门禁不一致/闭环门禁不通过（供 solidify 中止）。
"""
import os, sys, re

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.environ.get('SKILLS_DIR', os.path.join(ROOT, '.trae', 'skills'))
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
              'role-architecture','role-development','role-testing','role-deployment','role-governance',
              'role-program-mgmt','role-mgmt-consulting','role-project-mgmt']
SUB_SKILLS = ['best-practice-solution','commit-protocol','lsp-ast-integration','multi-perspective-validation',
              'project-memory','self-improve','team-orchestration','worktree-isolation',
              'customize-opencode']

VRE = re.compile(r'技能版本\*\*[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)')       # 元数据行
FRE = re.compile(r'\*\*文档版本\*\*[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)')   # 页脚
DVRE = re.compile(r'^>\s*归属：.*\s版本[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)', re.M)  # domain 头部版本行
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
    if re.search(r'(?m)^\s*#+\s*(?:\d+\.\s*)?闭环执行系统\s*$', content) is None:
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

    # 子技能与 domain 明细纳入版本一致性扫描（v21.7.5 扩展）
    for sub in SUB_SKILLS:
        sp = os.path.join(SKILLS_DIR, 'dev-project-team-skill', 'skills', sub, 'SKILL.md')
        if not os.path.isfile(sp):
            continue
        sc = open(sp, encoding='utf-8').read()
        ver = VRE.search(sc).group(1) if VRE.search(sc) else None
        foot = FRE.search(sc).group(1) if FRE.search(sc) else None
        label = f'{sub}.SKILL.md'
        if not (ver and foot and ver == foot):
            print(f'  ✗ {label:<36} 硬门禁: 元数据={ver} 页脚={foot} 不一致')
            hard += 1
        else:
            print(f'  ✓ {label:<36} {ver}')
        # domain/*.md 头部版本行必须与 SKILL.md 版本一致
        ddir = os.path.join(os.path.dirname(sp), 'domain')
        for root, _, files in os.walk(ddir):
            for fn in sorted(files):
                if not fn.endswith('.md'):
                    continue
                dp = os.path.join(root, fn)
                dc = open(dp, encoding='utf-8').read()
                dver = DVRE.search(dc).group(1) if DVRE.search(dc) else None
                dlabel = f'{sub}/domain/{fn if root == ddir else os.path.relpath(dp, root)}'
                if dver is None:
                    print(f'  ~ {dlabel:<54} 无版本行（跳过，软提示）')
                    soft += 1
                    continue
                if dver != ver:
                    print(f'  ✗ {dlabel:<54} 硬门禁: domain版本={dver} ≠ SKILL版本={ver}')
                    hard += 1
                else:
                    print(f'  ✓ {dlabel:<54} {dver}')

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