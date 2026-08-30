#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仓库卫生门禁（lint_repo）：供 .githooks/pre-commit 调用的仓库结构校验。

检查项（返回 0=通过，1=发现 error 级问题）：
  ① 根目录非白名单散落文件/目录（白名单见下）；
  ② 文件名含乱码/非 UTF-8 码点（C0/C1 控制区、私有区、代理区、>0xFFFF），
     允许 CJK(0x4E00-0x9FFF) 文件名存在于 台账/ 与 docs/program-control-ledger/；
  ③ 仓库根级目录/文件命名非 kebab-case（正则 ^[a-z0-9]+(-[a-z0-9]+)*$），
     中文文档名在 台账/、docs/ 内豁免；.trae/skills/ 下 role-* 等已合规不重复检查；
  ④ 台账单一信息源：根目录不应再存在 program-management/（28-31 应已在 台账/）；
  ⑤ 提示性检查：31_文档配置管理.csv（在 台账/）是否登记仓库关键文档（仅 warning）。

设计：仅扫描仓库结构，不读取文件内容；跨平台 Python3；中文注释。
"""
import os, sys, re, argparse, logging

sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger('lint_repo')

# 根目录白名单（目录）
WHITELIST_DIRS = {
    '.git', '.trae', '.agents', '.claude', '.github', '.secrets', '.backup',
    '.githooks', '.vscode', 'docs', 'tools', 'scripts', 'security',
    'requirements', 'tests', '台账', '.trae-html-share-packages', '架构资产', 'env-architecture-plan',
    '项目模板',  # PMO 阶段模板目录（立项/需求/设计开发/测试/上线验收等阶段模板，并行会话生成，合法根级产物）
    '.codebuddy',  # IDE 项目数据目录（含计划/会话状态），非临时缓存，禁止删除
    '.workbuddy',  # WorkBuddy 本地会话/记忆数据目录（已 gitignore，保留本地磁盘，不入库）
    '.idea',       # JetBrains IDE 本地配置（已 gitignore，保留本地磁盘，不入库）
    '.venv',       # Python 虚拟环境（已 gitignore，保留本地磁盘，不入库）
    '.qoder',      # 工具本地配置目录（已 gitignore，保留本地磁盘，不入库）
    'references',  # 项目级引用文档（project-registry 等，非技能库 references）
}
# 根目录白名单（文件）
WHITELIST_FILES = {
    'AGENTS.md', 'opencode.json', 'README.md', '交接文档.md',
    'CHANGELOG.md', 'CONTRIBUTING.md',
    '.gitattributes', '.gitignore', '.agent-loop-enabled',
    'projects_registry.csv',  # nightly_quality_gate.py 硬编码依赖的 registry（登记测试命令等）
}
# 中文文档豁免命名检查的目录（以仓库根相对路径前缀匹配）
CJK_NAME_DIRS = {'台账', 'docs', 'docs/program-control-ledger'}
# 允许 CJK 文件名的目录（用于乱码检查豁免）
CJK_FILENAME_DIRS = {'台账', 'docs/program-control-ledger'}

KEBAB_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
CJK_RE = re.compile(r'[\u4e00-\u9fff]')


def find_repo_root():
    """解析仓库根目录：优先 git rev-parse，回退向上查找 .git。"""
    try:
        import subprocess
        out = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                             capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return os.path.abspath(out.stdout.strip())
    except Exception:
        pass
    cur = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    while True:
        if os.path.isdir(os.path.join(cur, '.git')):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _is_cjk_filename_ok(name, rel_dir):
    """中文文件名是否允许：仅 台账/ 与 docs/program-control-ledger/ 内允许 CJK。"""
    parts = rel_dir.split(os.sep)
    # rel_dir 为相对根的路径；命中豁免目录即允许
    if '台账' in parts:
        return True
    if parts[:2] == ['docs', 'program-control-ledger']:
        return True
    return False


def check_root_scatter(root):
    """① 根目录非白名单散落文件/目录。"""
    errors = []
    try:
        entries = sorted(os.listdir(root))
    except Exception as e:
        log.error(f'无法读取根目录: {e}')
        return ['无法读取根目录']
    ignore_dirs = {'dist', '_pkg_tmp', '_build_global', '.trae-html-share-packages'}
    for name in entries:
        full = os.path.join(root, name)
        if os.path.isdir(full):
            if name in WHITELIST_DIRS:
                continue
            if name.startswith('skills_backup_') or name in ignore_dirs:
                continue
            errors.append(f'根目录散落目录（非白名单）: {name}/')
        else:
            if name in WHITELIST_FILES:
                continue
            errors.append(f'根目录散落文件（非白名单）: {name}')
    return errors


def check_filename_mojibake(root):
    """② 文件名含乱码/非 UTF-8 码点（递归全仓扫描）。"""
    errors = []
    # 跳过的目录：gitignored 历史留档 / 缓存 / 临时产物（避免误报 mojibake）
    skip_dirs = {'.git', '.secrets', '.backup', '.trae-html-share-packages',
                 'dist', '_build_global', '_pkg_tmp', '__pycache__', '.vscode'}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == '.':
            rel_dir = ''
        all_names = list(dirnames) + list(filenames)
        for name in all_names:
            for ch in name:
                cp = ord(ch)
                bad = False
                if cp <= 0x1F or (0x7F <= cp <= 0x9F):        # C0/C1 控制区
                    bad = True
                elif 0xE000 <= cp <= 0xF8FF:                  # 私有使用区
                    bad = True
                elif 0xD800 <= cp <= 0xDFFF:                  # 代理区
                    bad = True
                elif cp > 0xFFFF:                             # 基本平面之外
                    bad = True
                if bad:
                    # CJK 文件名豁免（仅指定目录）
                    if CJK_RE.search(ch) and _is_cjk_filename_ok(name, rel_dir):
                        continue
                    errors.append(f'文件名含非法码点 U+{cp:04X}: {os.path.join(rel_dir, name)}')
                    break
    return errors


def check_root_kebab(root):
    """③ 根级目录/文件命名非 kebab-case（中文文档名在 台账/、docs/ 内豁免）。"""
    errors = []
    try:
        entries = sorted(os.listdir(root))
    except Exception:
        return []
    for name in entries:
        full = os.path.join(root, name)
        # 白名单目录与文件直接跳过
        if os.path.isdir(full) and name in WHITELIST_DIRS:
            continue
        if os.path.isfile(full) and name in WHITELIST_FILES:
            continue
        # gitignored 的 solidify/打包产物（dist/_pkg_tmp/skills_backup_* 等）豁免
        if os.path.isdir(full) and (name.startswith('skills_backup_') or name in {'dist', '_pkg_tmp', '_build_global', '.trae-html-share-packages'}):
            continue
        # 中文文档名豁免（出现在 台账/、docs/ 内的子项另行处理，根级一般无中文）
        if CJK_RE.search(name):
            continue
        if not KEBAB_RE.match(name):
            kind = '目录' if os.path.isdir(full) else '文件'
            errors.append(f'根级{kind}命名非 kebab-case: {name}')
    return errors


def check_program_mgmt(root):
    """④ program-management/ 不应再存在（台账单一信息源）。"""
    errors = []
    pm = os.path.join(root, 'program-management')
    if os.path.isdir(pm):
        errors.append('根目录仍存在 program-management/（28-31 应已在 台账/，违反台账单一信息源）')
    return errors


def check_skill_links(root):
    """⑥ 技能库 Markdown 引用可达性（复用 tools/check_skill_links.py，拦截 .// 残留与 __resources 断链）。"""
    import subprocess as sp
    errors = []
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_skill_links.py')
    if not os.path.isfile(script):
        errors.append('tools/check_skill_links.py 缺失（技能引用可达性门禁不可用）')
        return errors
    try:
        r = sp.run([sys.executable, script, '--quiet'], cwd=find_repo_root() or root,
                   capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            for line in (r.stdout or '').splitlines():
                line = line.strip()
                if line and ('✗' in line or '→' in line or '不可达' in line or '断链' in line):
                    errors.append(f'技能引用断链: {line}')
    except sp.TimeoutExpired:
        errors.append('check_skill_links.py 执行超时（技能引用可达性门禁）')
    except Exception as e:
        errors.append(f'check_skill_links.py 执行异常: {e}')
    return errors


def check_doc_config_csv(root):
    """⑤ 提示性检查：31 文档配置管理台账（项目群文档与配置管理）是否存在。"""
    warnings = []
    csv_path = os.path.join(root, '台账', '31_doc_config_mgmt.csv')
    if not os.path.isfile(csv_path):
        warnings.append('台账/31_doc_config_mgmt.csv 不存在（建议登记项目群文档与配置管理台账）')
    return warnings


def main():
    ap = argparse.ArgumentParser(description='仓库卫生门禁（结构校验）')
    ap.add_argument('--root', default=None, help='仓库根目录（默认自动探测）')
    args = ap.parse_args()

    root = os.path.abspath(args.root) if args.root else find_repo_root()
    log.info(f'仓库卫生门禁 (lint_repo) 根目录: {root}')

    all_errors = []
    all_errors += check_root_scatter(root)
    all_errors += check_filename_mojibake(root)
    all_errors += check_root_kebab(root)
    all_errors += check_program_mgmt(root)
    all_errors += check_skill_links(root)

    print('\n========== 仓库卫生门禁报告 ==========')
    if all_errors:
        print('发现 error 级问题:')
        for e in all_errors:
            print(f'  ❌ {e}')
    else:
        print('✅ 各项 error 级检查通过。')

    warnings = check_doc_config_csv(root)
    if warnings:
        print('\n提示性检查 (warning):')
        for w in warnings:
            print(f'  ⚠ {w}')

    print('======================================')
    if all_errors:
        log.error(f'❌ 门禁未通过：{len(all_errors)} 项 error。')
        return 1
    log.info('✅ 仓库卫生门禁通过。')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        log.error(f'执行异常: {e}')
        sys.exit(1)
