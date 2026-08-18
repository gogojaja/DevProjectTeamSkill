#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理被 .gitignore 忽略的散落产物（cleanup_workspace）

这些项删除不影响版本库、可经对应 tools/ 重新生成：
  - skills_backup_*/          经 tools/solidify 重新生成
  - skills_legacy_*/          历史遗留快照
  - *.zip                     经 tools/package_skills 重新生成
  - dist/                     经 tools/package_skills 重新生成
  - _build_global/            临时构建产物
  - _pkg_tmp/                 打包临时目录
  - _solidify_*.log           固化日志
  - SkillEvolutionSkill/      历史方案目录
  - skill-evolution-plan/     历史方案目录
  - requirements-analysis-skill-modification-plan*/  历史方案目录

安全约束：
  - 仅删除「确实被 git 忽略」的项（git check-ignore 校验），避免误删已跟踪文件；
  - git 不可用时回退到 .gitignore 解析 + 目标模式匹配，结果保守（只删明确目标）。

参数：
  --dry-run   只打印将要删除的清单，不实际删除
  --archive   删除前先把待删项复制到 .backup/<timestamp>/ 归档
返回码 0=完成（或无待删项），1=执行异常。
"""
import os, sys, shutil, glob, argparse, logging, subprocess, datetime

sys.stdout.reconfigure(encoding='utf-8')

# 待清理目标（相对仓库根目录的模式）
TARGET_DIR_GLOBS = [
    'skills_backup_*', 'skills_legacy_*', 'dist', '_build_global',
    '_pkg_tmp', 'SkillEvolutionSkill', 'skill-evolution-plan',
    'requirements-analysis-skill-modification-plan*',
]
TARGET_FILE_GLOBS = ['*.zip', '_solidify_*.log']

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger('cleanup_workspace')


def find_repo_root():
    """解析仓库根目录：优先 git rev-parse，回退向上查找 .git。"""
    try:
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


def is_git_ignored(root, path):
    """用 git check-ignore 校验 path 是否确实被忽略；git 不可用时回退 .gitignore 解析。"""
    rel = os.path.relpath(path, root)
    try:
        r = subprocess.run(['git', 'check-ignore', '-q', rel],
                           cwd=root, capture_output=True)
        if r.returncode == 0:
            return True
        if r.returncode == 1:
            return False
    except Exception:
        pass
    # 回退：逐项用 .gitignore 模式匹配（保守：仅在忽略清单中才算忽略）
    return _fallback_ignored(root, rel)


def _fallback_ignored(root, rel):
    """无 git 时的保守回退：仅当 rel 命中 .gitignore 中「目录/文件」忽略模式才视为忽略。
    这里复用本脚本已知目标（它们本就在 .gitignore 中），避免依赖完整 ignore 解析。"""
    base = os.path.basename(rel)
    parent = os.path.dirname(rel)
    for g in TARGET_DIR_GLOBS:
        if parent == '' and glob.fnmatch.fnmatch(base, g):
            return True
    for g in TARGET_FILE_GLOBS:
        if glob.fnmatch.fnmatch(base, g):
            return True
    return False


def collect_targets(root):
    """展开目标模式，返回 (存在的路径列表)。"""
    found = []
    for g in TARGET_DIR_GLOBS:
        # 目录类：先按 glob，再补精确目录
        for p in glob.glob(os.path.join(root, g)):
            if os.path.isdir(p):
                found.append(p)
        exact = os.path.join(root, g)
        if os.path.isdir(exact) and exact not in found:
            found.append(exact)
    for g in TARGET_FILE_GLOBS:
        for p in glob.glob(os.path.join(root, g)):
            if os.path.isfile(p):
                found.append(p)
    # 去重并保留相对顺序
    seen, uniq = set(), []
    for p in found:
        rp = os.path.relpath(p, root)
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    return uniq


def archive_targets(root, targets):
    """删除前将待删项复制到 .backup/<timestamp>/ 归档。"""
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(root, '.backup', stamp)
    os.makedirs(backup_dir, exist_ok=True)
    for p in targets:
        rel = os.path.relpath(p, root)
        dst = os.path.join(backup_dir, rel)
        try:
            if os.path.isdir(p):
                shutil.copytree(p, dst)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(p, dst)
            log.info(f'  归档: {rel} -> .backup/{stamp}/{rel}')
        except Exception as e:
            log.warning(f'  归档失败 {rel}: {e}')
    return backup_dir


def remove_targets(targets):
    for p in targets:
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
        except Exception as e:
            log.warning(f'  删除失败 {p}: {e}')


def main():
    ap = argparse.ArgumentParser(description='清理被 .gitignore 忽略的散落产物')
    ap.add_argument('--dry-run', action='store_true', help='只打印将要删除的清单，不实际删除')
    ap.add_argument('--archive', action='store_true', help='删除前先归档到 .backup/<timestamp>/')
    args = ap.parse_args()

    root = find_repo_root()
    log.info(f'仓库根目录: {root}')

    candidates = collect_targets(root)
    # 仅保留确实被 git 忽略的项
    to_delete = []
    for p in candidates:
        rel = os.path.relpath(p, root)
        if is_git_ignored(root, p):
            to_delete.append((p, rel))
        else:
            log.warning(f'  跳过（非 git 忽略，已跟踪或不在忽略清单）: {rel}')

    if not to_delete:
        log.info('✅ 无待清理的散落产物。')
        return 0

    print('\n========== 清理清单 ==========')
    for p, rel in to_delete:
        kind = '目录' if os.path.isdir(p) else '文件'
        print(f'  [{kind}] {rel}')

    if args.dry_run:
        print('\n(dry-run) 未执行删除。')
        return 0

    if args.archive:
        backup_dir = archive_targets(root, [p for p, _ in to_delete])
        print(f'\n已归档至: {os.path.relpath(backup_dir, root)}')

    remove_targets([p for p, _ in to_delete])

    n_dir = sum(1 for p, _ in to_delete if os.path.isdir(p))
    n_file = len(to_delete) - n_dir
    print('\n========== 清理统计 ==========')
    print(f'  已删除目录: {n_dir} 个')
    print(f'  已删除文件: {n_file} 个')
    print(f'  合计: {len(to_delete)} 项')
    log.info('✅ 清理完成。')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        log.error(f'执行异常: {e}')
        sys.exit(1)
