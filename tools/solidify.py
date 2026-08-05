import os, sys, shutil, re, glob, datetime
sys.stdout.reconfigure(encoding='utf-8')

SKILLS_DIR = r'C:/Users/gogoj/.config/opencode/skills'
ROOT = r'D:\trae\DevProjectTeamSkill'
HANDOFF = os.path.join(ROOT, '交接文档.md')
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
             'role-architecture','role-development','role-testing','role-deployment','role-governance']

def run_package():
    os.system(f'py -3.11 "{os.path.join(ROOT, "tools", "package_skills.py")}" > "{os.path.join(ROOT, "_solidify_pkg.log")}" 2>&1')

def run_deploy():
    os.system(f'py -3.11 "{os.path.join(ROOT, "tools", "deploy_skills.py")}" > "{os.path.join(ROOT, "_solidify_deploy.log")}" 2>&1')

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
    note = sys.argv[1] if len(sys.argv) > 1 else ''
    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print('==============================================')
    print(' 育权台断点固化 (solidify v21, Python port)')
    print('==============================================')
    print('[1/5] 角色包清单')
    for r in ALL_ROLES:
        p = os.path.join(SKILLS_DIR, r, 'SKILL.md')
        if os.path.isfile(p):
            m = re.search(r'技能版本\*\*[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)', open(p, encoding='utf-8').read())
            print(f'   {r:<40} {m.group(1) if m else "v?"}')
    print('[2/5] 刷新交接文档断点区')
    refresh_handoff(stamp, note)
    print('[3/5] 快照')
    v = 'v21.0.0'
    snapshot(v)
    print('[4/5] 打包 dist')
    run_package()
    print('   ✓ package_skills.py 完成')
    print('[5/5] 部署四目录')
    run_deploy()
    print('   ✓ deploy_skills.py 完成')
    print('==============================================')
    print(' 固化完成。请执行: git add -A && git commit -m "<说明>"')
    print('==============================================')
