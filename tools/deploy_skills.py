import os, sys, shutil, glob
sys.stdout.reconfigure(encoding='utf-8')

SKILLS_DIR = os.environ.get('SKILLS_DIR', r'D:\trae\DevProjectTeamSkill\.trae\skills')
ROOT = r'D:\trae\DevProjectTeamSkill'
GLOBAL_SKILLS = r'C:/Users/gogoj/.config/opencode/skills'
DEFAULT_TARGETS = [os.path.join(ROOT, t) for t in
                   ('.github/skills', '.claude/skills', '.agents/skills')] + [GLOBAL_SKILLS]
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
             'role-architecture','role-development','role-testing','role-deployment','role-governance']

def parse_args(argv):
    targets = []
    roles = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--target':
            targets.append(argv[i+1]); i += 2
        elif a == '--roles':
            roles += [x for x in argv[i+1].split(',') if x]; i += 2
        elif a in ('-h', '--help'):
            print('用法: package_skills.py [--target <dir>]... [--roles <role,role,...>]')
            sys.exit(0)
        else:
            print(f'未知参数: {a}'); sys.exit(1)
    return targets or DEFAULT_TARGETS, roles or ALL_ROLES

def check_names(roles):
    fail = 0
    for r in roles:
        p = os.path.join(SKILLS_DIR, r, 'SKILL.md')
        if not os.path.isfile(p):
            print(f'  ✗ {r} 缺少 SKILL.md'); fail = 1; continue
        with open(p, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('name:'):
                    name = line.split(':', 1)[1].strip().strip('"').strip()
                    break
        if name != r:
            print(f'  ✗ {r} frontmatter name({name}) 与目录名不一致'); fail = 1
    if fail:
        print('frontmatter 校验未通过，中止部署')
        sys.exit(1)
    print('  ✓ frontmatter name 校验通过')

def deploy_target(target, roles):
    print(f'部署 → {target} ({",".join(roles)})')
    if os.path.exists(target):
        shutil.rmtree(target)
    os.makedirs(target)
    for r in roles:
        src = os.path.join(SKILLS_DIR, r)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(target, r),
                            ignore=shutil.ignore_patterns('*.pyc'))
        else:
            print(f'  ✗ 技能库无角色包 {r}')
    ref = os.path.join(SKILLS_DIR, 'references')
    if os.path.isdir(ref):
        shutil.copytree(ref, os.path.join(target, 'references'))
    # 同步 shared/ 单源（角色包 ../shared/ 引用目标解析依赖此目录）
    shared = os.path.join(SKILLS_DIR, 'shared')
    if os.path.isdir(shared):
        shutil.copytree(shared, os.path.join(target, 'shared'))
    idx = os.path.join(SKILLS_DIR, 'SKILL_INDEX.md')
    if os.path.isfile(idx):
        shutil.copy(idx, os.path.join(target, 'SKILL_INDEX.md'))
    ok = all(os.path.isfile(os.path.join(target, r, 'SKILL.md')) for r in roles)
    if ok:
        print(f'  ✓ 部署完成（{len(roles)} 包 + references + SKILL_INDEX.md）')
    else:
        print('  ✗ 部署校验失败')
        sys.exit(1)

if __name__ == '__main__':
    targets, roles = parse_args(sys.argv[1:])
    print('技能库部署 (v21, Python port, --roles 按需部署)')
    print(f'源库: {SKILLS_DIR}')
    print(f'待部署角色包: {",".join(roles)}')
    check_names(roles)
    for t in targets:
        deploy_target(t, roles)
    print('全部完成。注入型工具请只放入本次任务所需角色包。')
