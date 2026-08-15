import os, sys, shutil, re, glob, datetime, subprocess
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.environ.get('SKILLS_DIR', os.path.join(ROOT, '.trae', 'skills'))
HANDOFF = os.path.join(ROOT, '交接文档.md')
TOOLS_DIR = os.path.join(ROOT, 'tools')
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
             'role-architecture','role-development','role-testing','role-deployment','role-governance']

def _run_script(script, *args):
    """跨平台运行 tools/ 下脚本：使用当前 Python 解释器（Windows/macOS/Linux 通用）。"""
    cmd = [sys.executable, os.path.join(TOOLS_DIR, script), *args]
    return subprocess.run(cmd, cwd=ROOT)

def run_package():
    r = _run_script('package_skills.py')
    return r.returncode

def run_version_check():
    """硬门禁：版本一致性校验，失败中止固化。"""
    r = _run_script('check_version_consistency.py')
    print('   ✓ 版本一致性校验执行完毕' if r.returncode == 0 else '   ✗ 版本一致性校验失败')
    return r.returncode


def run_closure_check():
    """硬门禁：闭环执行系统校验，失败中止固化。"""
    r = _run_script('check_skill_closure.py')
    print('   ✓ 闭环执行门禁执行完毕' if r.returncode == 0 else '   ✗ 闭环执行门禁失败')
    return r.returncode


def run_deploy():
    return _run_script('deploy_skills.py').returncode

def refresh_handoff(stamp, note):
    MARK = '## 1. 工作断点'
    with open(HANDOFF, encoding='utf-8') as f:
        c = f.read()
    n_roles = 0
    for r in ALL_ROLES:
        p = os.path.join(SKILLS_DIR, r, 'SKILL.md')
        if os.path.isfile(p):
            n_roles += 1
    # 仅刷新元数据行（固化时间/角色包数/固化备注），保留既有的已完成/进行中/待办/阻塞内容
    updated = re.sub(r'(\*\*最近固化时间\*\*：).*', lambda m: m.group(1) + stamp, c)
    updated = re.sub(r'(\*\*角色包数\*\*：).*', lambda m: m.group(1) + str(n_roles), updated)
    updated = re.sub(r'(\*\*固化备注\*\*：).*', lambda m: m.group(1) + (note if note else '—'), updated)
    if updated == c:
        # 若元数据行缺失，则按模板追加
        block = (f'\n\n{MARK}\n\n'
                 f'> 本区由 `tools/solidify.sh` 每次任务完成后自动覆写。\n'
                 f'> **新模型/新会话启动，第一步必须先读 `交接文档.md` 全文**，从本区定位上一模型已完成/待办，未读交接文档前禁止读其他项目文档。\n\n'
                 f'**最近固化时间**：{stamp}\n'
                 f'**角色包数**：{n_roles}\n'
                 f'**固化备注**：{note if note else "—"}\n\n'
                 f'### 已完成\n（无则写「无」）\n\n'
                 f'### 进行中\n（正在改动、未固化到磁盘的在途工作）\n\n'
                 f'### 待办\n（下一阶段动作）\n\n'
                 f'### 阻塞\n（如有风险/阻塞项）\n\n'
                 f'### 台账指针\n主台账 CSV 路径：待填　最近变更号：待填')
        updated = c.rstrip('\n') + block
    with open(HANDOFF, 'w', encoding='utf-8') as f:
        f.write(updated)
    print(f'   ✓ 交接文档断点区已刷新（固化后必须反映磁盘最新状态）')

def snapshot(ver):
    snap = os.path.join(ROOT, f'skills_backup_{ver}')
    if os.path.isdir(snap):
        print(f'   ⚠ 快照 {ver} 已存在（不覆盖）')
        return
    os.makedirs(snap)
    for r in ALL_ROLES:
        src = os.path.join(SKILLS_DIR, r)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(snap, r))
    for sub in ('references', 'shared'):
        src = os.path.join(SKILLS_DIR, sub)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(snap, sub))
    idx = os.path.join(SKILLS_DIR, 'SKILL_INDEX.md')
    if os.path.isfile(idx):
        shutil.copy(idx, os.path.join(snap, 'SKILL_INDEX.md'))
    print(f'   ✓ 快照已生成 → {snap}')

if __name__ == '__main__':
    # simple arg parsing: optional note, plus --dry-run / --json
    note = ''
    dry_run = False
    as_json = False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--dry-run':
            dry_run = True; i += 1
        elif a == '--json':
            as_json = True; i += 1
        else:
            # first non-flag is note
            if not note:
                note = a
            i += 1

    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    info = {'action': 'solidify', 'stamp': stamp, 'note': note, 'dry_run': dry_run}
    print('==============================================')
    print(' 育权台断点固化 (solidify v21, Python port)')
    print('==============================================')
    print('[1/5] 角色包清单')
    for r in ALL_ROLES:
        p = os.path.join(SKILLS_DIR, r, 'SKILL.md')
        if os.path.isfile(p):
            m = re.search(r'技能版本\*\*[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)', open(p, encoding='utf-8').read())
            print(f'   {r:<40} {m.group(1) if m else "v?"}')
    print('[1a/5] 版本一致性校验（硬门禁）')
    if run_version_check() != 0:
        print('❌ 版本一致性校验未通过，中止固化。请先统一各包元数据/页脚版本。')
        sys.exit(1)
    print('[1b/5] 闭环执行门禁校验（硬门禁）')
    if run_closure_check() != 0:
        print('❌ 闭环执行门禁未通过，中止固化。请先补齐“闭环执行系统”章节与关键门禁项。')
        sys.exit(1)
    print('[2/5] 刷新交接文档断点区')
    if not dry_run:
        refresh_handoff(stamp, note)
    else:
        print('   (dry-run) refresh_handoff skipped')
    print('[3/5] 快照')
    m = re.search(r'技能版本\*\*[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)',
                  open(os.path.join(SKILLS_DIR, 'dev-project-team-skill', 'SKILL.md'), encoding='utf-8').read())
    v = m.group(1) if m else 'v21.0.0'
    if not dry_run:
        snapshot(v)
    else:
        print(f'   (dry-run) snapshot {v} skipped')
    print('[4/5] 打包 dist')
    if not dry_run:
        if run_package() != 0:
            print('   ✗ package_skills.py 失败'); sys.exit(1)
        print('   ✓ package_skills.py 完成')
    else:
        print('   (dry-run) package_skills.py skipped')
    print('[5/5] 部署四目录')
    if not dry_run:
        if run_deploy() != 0:
            print('   ✗ deploy_skills.py 失败'); sys.exit(1)
        print('   ✓ deploy_skills.py 完成')
    else:
        print('   (dry-run) deploy_skills.py skipped')

    print('==============================================')
    print(' 固化完成。请执行: git add -A && git commit -m "<说明>"')
    print('==============================================')
    info['status'] = 'completed' if not dry_run else 'dry-run'
    if as_json:
        import json
        print(json.dumps(info, ensure_ascii=False))
