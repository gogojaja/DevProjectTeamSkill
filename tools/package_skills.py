#!/usr/bin/env python3
import os, sys, re, zipfile, shutil, glob
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.environ.get('SKILLS_DIR', os.path.join(ROOT, '.trae', 'skills'))
DIST = os.path.join(ROOT, 'dist')
HANDOFF = os.path.join(ROOT, '交接文档.md')
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
             'role-architecture','role-development','role-testing','role-deployment','role-governance',
             'role-program-mgmt','role-mgmt-consulting','role-project-mgmt',
             'role-operations','role-security']
# 独立可部署技能（非角色包）：随全量打包一并产出自包含 zip；三门禁校验器（check_*）已新增 STANDALONE_SKILLS 独立遍历分支（S1~S3），与 ALL_ROLES/SUB_SKILLS 语义隔离不污染
STANDALONE_SKILLS = ['scope-tracking', 'plan-creation', 'portfolio-mgmt', 'okr-strategy', 'resource-ops', 'stakeholder-comms', 'schedule-cost', 'risk-mgmt']

VRE = re.compile(r'技能版本\*\*[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)')

def get_version(path):
    try:
        with open(path, encoding='utf-8') as f:
            c = f.read()
        m = VRE.search(c)
        return m.group(1) if m else 'v21.0.0'
    except Exception:
        return 'v21.0.0'

def inject_bundled(src, dst):
    """按 skill.manifest.json 注入自包含工具/测试副本（B1 单一信源）。

    权威工具/测试留在仓库根 tools/·tests/；此处仅在打包产物内注入声明的副本，
    使 zip 脱离编排器即可 `python3 tools/scope_tracker.py ...` 独立运行。
    无 manifest 的既有角色包行为不变（零回归）。返回注入文件数。
    """
    import json
    mf = os.path.join(src, 'skill.manifest.json')
    if not os.path.isfile(mf):
        return 0
    try:
        with open(mf, encoding='utf-8') as f:
            m = json.load(f)
    except Exception as e:
        print(f'  ⚠ skill.manifest.json 解析失败，跳过注入: {e}')
        return 0
    bsrc = m.get('bundle_source', {}) or {}
    specs = [('bundle_tools', bsrc.get('tools', 'tools'), 'tools'),
             ('bundle_tests', bsrc.get('tests', 'tests'), 'tests')]
    n = 0
    for key, src_sub, dst_sub in specs:
        names = m.get(key, []) or []
        if not names:
            continue
        src_dir = os.path.join(ROOT, src_sub)
        dst_dir = os.path.join(dst, dst_sub)
        for name in names:
            s = os.path.join(src_dir, name)
            if not os.path.isfile(s):
                print(f'  ⚠ manifest 声明缺失（{key}）: {s}')
                continue
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy(s, os.path.join(dst_dir, name))
            n += 1
    if n:
        print(f'  ✓ 按 manifest 注入自包含副本: {n} 个（tools/+tests/）')
    return n


def pack_role(role):
    src = os.path.join(SKILLS_DIR, role)
    if not os.path.isfile(os.path.join(src, 'SKILL.md')):
        print(f'  ✗ {role} 缺少 SKILL.md，跳过')
        return False
    ver = get_version(os.path.join(src, 'SKILL.md'))
    tmp = os.path.join(ROOT, '_pkg_tmp', role)
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    try:
        os.makedirs(tmp)
    except OSError as e:
        print(f'  ✗ 创建临时目录失败: {e}')
        return False

    # 交接文档置包内第一项
    if os.path.isfile(HANDOFF):
        shutil.copy(HANDOFF, os.path.join(tmp, '00_交接文档.md'))
    else:
        print(f'  ⚠ 未找到交接文档 {HANDOFF}，包内不置 00_交接文档.md')

    # SKILL.md + domain
    shutil.copy(os.path.join(src, 'SKILL.md'), os.path.join(tmp, 'SKILL.md'))
    # 自包含声明清单（若存在）随包分发：保证独立可部署技能的契约可追溯/可再部署（与 deploy copytree 对齐）
    mf_src = os.path.join(src, 'skill.manifest.json')
    if os.path.isfile(mf_src):
        shutil.copy(mf_src, os.path.join(tmp, 'skill.manifest.json'))
    dom_src = os.path.join(src, 'domain')
    if os.path.isdir(dom_src):
        dst = os.path.join(tmp, 'domain')
        shutil.copytree(dom_src, dst, ignore=shutil.ignore_patterns('*.pyc'))

    # 包内 shared（若包自带）
    sh_src = os.path.join(src, 'shared')
    if os.path.isdir(sh_src):
        shutil.copytree(sh_src, os.path.join(tmp, 'shared'))

    # 内嵌上级库 shared/（../shared/ 指向 SKILLS_DIR/shared）
    lib_shared = os.path.join(SKILLS_DIR, 'shared')
    if os.path.isdir(lib_shared):
        dst = os.path.join(tmp, 'shared')
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(lib_shared):
            p = os.path.join(lib_shared, f)
            if os.path.isfile(p):
                shutil.copy(p, os.path.join(dst, f))
            elif os.path.isdir(p):
                shutil.copytree(p, os.path.join(dst, f), dirs_exist_ok=True)

    # 内嵌 references 副本
    ref_src = os.path.join(SKILLS_DIR, 'references')
    if os.path.isdir(ref_src):
        dst = os.path.join(tmp, 'references')
        shutil.copytree(ref_src, dst)

    # 按 skill.manifest.json 注入自包含工具/测试副本（无 manifest 的角色包不受影响）
    inject_bundled(src, tmp)

    out = os.path.join(DIST, f'{role}_{ver}.zip')
    try:
        os.makedirs(DIST, exist_ok=True)
    except OSError as e:
        print(f'  ✗ 创建 dist 目录失败: {e}')
        return False
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for root_dir, dirs, files in os.walk(tmp):
            for fn in files:
                full = os.path.join(root_dir, fn)
                rel = os.path.relpath(full, tmp)
                z.write(full, rel)
    n = len(zipfile.ZipFile(out).namelist())
    shutil.rmtree(tmp)
    print(f'  ✓ {out} ({n} files, 首项含 00_交接文档.md)')
    return True

def parse_roles(argv):
    """对齐 package_skills.sh：--role <name> 可多次；无参=全部角色包。"""
    roles = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--role':
            roles.append(argv[i+1]); i += 2
        elif a in ('-h', '--help'):
            print('用法: package_skills.py [--role <role-name>]...   # 无参=全部角色包 + 独立可部署技能（scope-tracking）')
            sys.exit(0)
        else:
            print(f'未知参数: {a}'); sys.exit(1)
    return roles or (ALL_ROLES + STANDALONE_SKILLS)

if __name__ == '__main__':
    roles = parse_roles(sys.argv[1:])
    print('角色包打包发布 (v21, Python port)')
    print(f'技能库源: {SKILLS_DIR}')
    for r in roles:
        pack_role(r)
    zips = glob.glob(os.path.join(DIST, '*.zip'))
    print(f'完成: {len(zips)} 个包已生成至 {DIST}')
    for z in zips:
        print('  ', os.path.basename(z), f'({os.path.getsize(z):,} bytes)')
