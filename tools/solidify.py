#!/usr/bin/env python3
import os, sys, shutil, re, glob, datetime, subprocess
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.environ.get('SKILLS_DIR', os.path.join(ROOT, '.trae', 'skills'))
HANDOFF = os.path.join(ROOT, '交接文档.md')
TOOLS_DIR = os.path.join(ROOT, 'tools')
ALL_ROLES = ['dev-project-team-skill','role-project-init','role-requirements-analysis',
             'role-architecture','role-development','role-testing','role-deployment','role-governance',
             'role-program-mgmt','role-mgmt-consulting','role-project-mgmt']

def _run_script(script, *args):
    """跨平台运行 tools/ 下脚本：使用当前 Python 解释器（Windows/macOS/Linux 通用）。"""
    try:
        cmd = [sys.executable, os.path.join(TOOLS_DIR, script), *args]
        return subprocess.run(cmd, cwd=ROOT)
    except FileNotFoundError:
        print(f'   ✗ 脚本不存在: {script}')
        return subprocess.CompletedProcess(cmd, returncode=1)
    except OSError as e:
        print(f'   ✗ 执行 {script} 失败: {e}')
        return subprocess.CompletedProcess(cmd, returncode=1)

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


def run_release_gate():
    """发布级门禁：检查 frontmatter/metadata/闭环结构，失败中止固化与发布。"""
    r = _run_script('check_skill_release_gate.py')
    print('   ✓ 发布级门禁执行完毕' if r.returncode == 0 else '   ✗ 发布级门禁失败')
    return r.returncode


def run_deprecation_cleanup():
    """第 4 硬门禁：废弃清理门禁，ADR 废弃后必须移除资产，失败中止固化。"""
    r = _run_script('check_deprecation_cleanup.py')
    print('   ✓ 废弃清理门禁执行完毕' if r.returncode == 0 else '   ✗ 废弃清理门禁失败')
    return r.returncode


def run_mcp_server_check():
    """第 5 硬门禁：MCP Server 门禁，检查语法/工具计数/脚本可达性/依赖声明。"""
    r = _run_script('check_mcp_server.py')
    print('   ✓ MCP Server 门禁校验通过' if r.returncode == 0 else '   ✗ MCP Server 门禁失败')
    return r.returncode


def run_plugin_chain_check():
    """第 6 软门禁：插件链路检查，检查代理脚本/注册表/环境变量模板。不阻断固化。"""
    r = _run_script('check_plugin_chain.py')
    if r.returncode == 0:
        print('   ✓ 插件链路检查通过（软门禁，不阻断）')
    else:
        print('   ⚠ 插件链路检查有告警（软门禁，不阻断固化）')
    return r.returncode


def run_deploy():
    # 开发固化仅部署项目级三目录；全局库（生产消费载体）由 publish_production 独占
    return _run_script('deploy_skills.py', '--skip-global').returncode

def refresh_handoff(stamp, note):
    MARK = '## 1. 工作断点'
    try:
        with open(HANDOFF, encoding='utf-8') as f:
            c = f.read()
    except FileNotFoundError:
        print(f'   ✗ 交接文档不存在: {HANDOFF}')
        return
    except OSError as e:
        print(f'   ✗ 读取交接文档失败: {e}')
        return
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
    try:
        with open(HANDOFF, 'w', encoding='utf-8') as f:
            f.write(updated)
        print(f'   ✓ 交接文档断点区已刷新（固化后必须反映磁盘最新状态）')
    except OSError as e:
        print(f'   ✗ 写入交接文档失败: {e}')

def snapshot(ver):
    snap = os.path.join(ROOT, f'skills_backup_{ver}')
    if os.path.isdir(snap):
        print(f'   ⚠ 快照 {ver} 已存在（不覆盖）')
        return
    try:
        os.makedirs(snap)
    except OSError as e:
        print(f'   ✗ 创建快照目录失败: {e}')
        return
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
    # 配套工具与文档（SKILL_INDEX/SKILL.md 引用 tools/* 与 docs/*）
    for extra in ('tools', 'docs'):
        src = os.path.join(ROOT, extra)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(snap, extra),
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc',
                                                          '.DS_Store', 'dist', '_pkg_tmp'))
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
    print('[1a/6] 版本一致性校验（硬门禁）')
    if run_version_check() != 0:
        print('❌ 版本一致性校验未通过，中止固化。请先统一各包元数据/页脚版本。')
        sys.exit(1)
    print('[1b/6] 闭环执行门禁校验（硬门禁）')
    if run_closure_check() != 0:
        print('❌ 闭环执行门禁未通过，中止固化。请先补齐“闭环执行系统”章节与关键门禁项。')
        sys.exit(1)
    print('[1c/6] 发布级门禁校验（硬门禁）')
    if run_release_gate() != 0:
        print('❌ 发布级门禁未通过，中止固化。请先补齐 frontmatter、metadata 与闭环执行结构。')
        sys.exit(1)
    print('[1d/6] 废弃清理门禁校验（硬门禁）')
    if run_deprecation_cleanup() != 0:
        print('❌ 废弃清理门禁未通过，中止固化。请先彻底移除废弃资产残留（引用/端口/进程/LaunchAgent）。')
        sys.exit(1)
    print('[1e/6] MCP Server 门禁校验（硬门禁）')
    if run_mcp_server_check() != 0:
        print('❌ MCP Server 门禁未通过，中止固化。请检查 tools/mcp_server/ 目录完整性。')
        sys.exit(1)
    print('[1f/6] 插件链路检查（软门禁，不阻断）')
    run_plugin_chain_check()
    print('[2/6] 刷新交接文档断点区')
    if not dry_run:
        refresh_handoff(stamp, note)
    else:
        print('   (dry-run) refresh_handoff skipped')
    print('[3/6] 快照')
    m = re.search(r'技能版本\*\*[：:]\s*(v[0-9]+\.[0-9]+\.[0-9]+)',
                  open(os.path.join(SKILLS_DIR, 'dev-project-team-skill', 'SKILL.md'), encoding='utf-8').read())
    v = m.group(1) if m else 'v21.0.0'
    if not dry_run:
        snapshot(v)
    else:
        print(f'   (dry-run) snapshot {v} skipped')
    print('[4/6] 打包 dist')
    if not dry_run:
        if run_package() != 0:
            print('   ✗ package_skills.py 失败'); sys.exit(1)
        print('   ✓ package_skills.py 完成')
    else:
        print('   (dry-run) package_skills.py skipped')
    print('[5/6] 部署项目级三目录 (全局库由 publish_production 独占)')
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
