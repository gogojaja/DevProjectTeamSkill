#!/usr/bin/env python3
import os, sys, shutil, glob
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.environ.get('SKILLS_DIR', os.path.join(ROOT, '.trae', 'skills'))
# 全局 opencode 技能库：平台自适应（Windows -> %USERPROFILE%/.config/...；macOS/Linux -> ~/.config/...）
if sys.platform.startswith('win'):
    GLOBAL_SKILLS = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), '.config', 'opencode', 'skills')
else:
    GLOBAL_SKILLS = os.path.join(os.environ.get('HOME', ''), '.config', 'opencode', 'skills')
DEFAULT_TARGETS = [os.path.join(ROOT, t) for t in
                   ('.github/skills', '.claude/skills', '.agents/skills')] + [GLOBAL_SKILLS]
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
             'role-architecture','role-development','role-testing','role-deployment','role-governance',
             'role-program-mgmt','role-mgmt-consulting']

def parse_args(argv):
    targets = []
    roles = []
    dry_run = False
    as_json = False
    skip_global = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--target':
            targets.append(argv[i+1]); i += 2
        elif a == '--roles':
            roles += [x for x in argv[i+1].split(',') if x]; i += 2
        elif a == '--skip-global':
            skip_global = True; i += 1
        elif a == '--dry-run':
            dry_run = True; i += 1
        elif a == '--json':
            as_json = True; i += 1
        elif a in ('-h', '--help'):
            print('用法: deploy_skills.py [--target <dir>]... [--roles <role,role,...>] [--skip-global] [--dry-run] [--json]')
            sys.exit(0)
        else:
            print(f'未知参数: {a}'); sys.exit(1)
    if not targets:
        if skip_global:
            targets = [os.path.join(ROOT, t) for t in ('.github/skills', '.claude/skills', '.agents/skills')]
        else:
            targets = DEFAULT_TARGETS
    return targets, roles, dry_run, as_json

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
    try:
        if os.path.exists(target):
            shutil.rmtree(target)
        os.makedirs(target)
    except OSError as e:
        print(f'  ✗ 创建部署目录失败: {e}')
        sys.exit(1)
    for r in roles:
        src = os.path.join(SKILLS_DIR, r)
        if os.path.isdir(src):
            try:
                shutil.copytree(src, os.path.join(target, r),
                                ignore=shutil.ignore_patterns('*.pyc'))
            except OSError as e:
                print(f'  ✗ 复制 {r} 失败: {e}')
        else:
            print(f'  ✗ 技能库无角色包 {r}')
    ref = os.path.join(SKILLS_DIR, 'references')
    if os.path.isdir(ref):
        try:
            shutil.copytree(ref, os.path.join(target, 'references'))
        except OSError as e:
            print(f'  ✗ 复制 references 失败: {e}')
    # 同步 shared/ 单源（角色包 ../shared/ 引用目标解析依赖此目录）
    shared = os.path.join(SKILLS_DIR, 'shared')
    if os.path.isdir(shared):
        try:
            shutil.copytree(shared, os.path.join(target, 'shared'))
        except OSError as e:
            print(f'  ✗ 复制 shared 失败: {e}')
    idx = os.path.join(SKILLS_DIR, 'SKILL_INDEX.md')
    if os.path.isfile(idx):
        shutil.copy(idx, os.path.join(target, 'SKILL_INDEX.md'))
    # 配套工具与文档：SKILL_INDEX/SKILL.md 引用 tools/* 与 docs/*，随部署集一起输出
    for extra in ('tools', 'docs'):
        s = os.path.join(ROOT, extra)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(target, extra),
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc',
                                                          '.DS_Store', 'dist', '_pkg_tmp'))
    ok = all(os.path.isfile(os.path.join(target, r, 'SKILL.md')) for r in roles)
    if ok:
        print(f'  ✓ 部署完成（{len(roles)} 包 + references + SKILL_INDEX.md）')
    else:
        print('  ✗ 部署校验失败')
        sys.exit(1)

if __name__ == '__main__':
    targets, roles, dry_run, as_json = parse_args(sys.argv[1:])
    info = {
        'action': 'deploy_skills',
        'source': SKILLS_DIR,
        'targets': targets,
        'roles': roles,
        'dry_run': dry_run
    }
    if not dry_run:
        print('技能库部署 (v21, Python port, --roles 按需部署)')
        print(f'源库: {SKILLS_DIR}')
        print(f'待部署角色包: {",".join(roles)}')
        check_names(roles)
        for t in targets:
            deploy_target(t, roles)
        print('全部完成。注入型工具请只放入本次任务所需角色包。')
        info['status'] = 'completed'
    else:
        # dry-run: do not perform file system changes, only report
        info['status'] = 'dry-run'
        info['message'] = f'Would deploy {len(roles)} roles to {len(targets)} targets.'
        print(info['message'])

    if as_json:
        import json
        print(json.dumps(info, ensure_ascii=False))
