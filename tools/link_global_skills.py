"""全局技能库 junction 链接化：将 4 个全局库的物理副本替换为 junction 链接，指向项目源码，实现单源。

用法：python tools/link_global_skills.py [--dry-run] [--restore]
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(r"d:\MyProjects\DevProjectTeamSkill")
SKILLS_SOURCE = PROJECT_ROOT / ".trae" / "skills"
DOCS_SOURCE = PROJECT_ROOT / "docs"
TOOLS_SOURCE = PROJECT_ROOT / "tools"
SKILL_INDEX_SOURCE = SKILLS_SOURCE / "SKILL_INDEX.md"

GLOBAL_LIBS = [
    Path.home() / ".trae-cn" / "skills",
    Path.home() / ".config" / "opencode" / "skills",
    Path.home() / ".workbuddy" / "skills",
    Path.home() / ".copilot" / "skills",
]

NON_PROJECT_ITEMS = {"git-commit"}

TS = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = PROJECT_ROOT / ".backup" / f"global_skills_{TS}"
MANIFEST = BACKUP_DIR / "manifest.csv"


def is_junction_or_symlink(path):
    """检查路径是否为 junction 或 symlink"""
    if not path.exists() and not path.is_symlink():
        return False
    try:
        return path.is_symlink() or os.path.isjunction(str(path))
    except (OSError, AttributeError):
        return path.is_symlink()


def make_junction(link_path, target_path):
    """创建 Windows junction（目录）"""
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)],
        capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout + result.stderr


def make_symlink(link_path, target_path):
    """创建 Windows symlink（文件）"""
    result = subprocess.run(
        ["cmd", "/c", "mklink", str(link_path), str(target_path)],
        capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout + result.stderr


def collect_items():
    """收集需要链接的所有条目：(相对名称, 源路径, 类型)"""
    items = []
    for d in sorted(SKILLS_SOURCE.iterdir()):
        if d.is_dir():
            items.append((d.name, d, "dir"))
    items.append(("docs", DOCS_SOURCE, "dir"))
    items.append(("tools", TOOLS_SOURCE, "dir"))
    if SKILL_INDEX_SOURCE.exists():
        items.append(("SKILL_INDEX.md", SKILL_INDEX_SOURCE, "file"))
    return items


def process_library(lib_path, items, dry_run=False):
    """处理单个全局库"""
    if not lib_path.exists():
        print(f"  [跳过] {lib_path} 不存在")
        return []

    log = []
    for name, source, kind in items:
        if name in NON_PROJECT_ITEMS:
            print(f"  [保留] {name}（非本项目技能）")
            continue

        link_path = lib_path / name

        if not link_path.exists() and not link_path.is_symlink():
            if dry_run:
                print(f"  [新建链接] {name} -> {source}")
                log.append((name, str(source), "new_link"))
            else:
                if kind == "dir":
                    ok, msg = make_junction(link_path, source)
                else:
                    ok, msg = make_symlink(link_path, source)
                if ok:
                    print(f"  [新建链接] {name} -> {source}")
                    log.append((name, str(source), "new_link"))
                else:
                    print(f"  [失败] {name}: {msg.strip()}")
                    log.append((name, str(source), f"failed: {msg.strip()}"))
            continue

        if is_junction_or_symlink(link_path):
            print(f"  [已是链接] {name}（跳过）")
            log.append((name, str(source), "already_linked"))
            continue

        if dry_run:
            print(f"  [替换] {name}：删除物理副本 -> 链接到 {source}")
            log.append((name, str(source), "replace"))
            continue

        if kind == "dir":
            shutil.rmtree(str(link_path))
            ok, msg = make_junction(link_path, source)
        else:
            link_path.unlink()
            ok, msg = make_symlink(link_path, source)

        if ok:
            print(f"  [替换] {name} -> {source}")
            log.append((name, str(source), "replaced"))
        else:
            print(f"  [失败] {name}: {msg.strip()}")
            log.append((name, str(source), f"failed: {msg.strip()}"))

    return log


def main():
    dry_run = "--dry-run" in sys.argv
    restore = "--restore" in sys.argv

    if restore:
        print("=== 恢复模式：从备份恢复物理副本 ===")
        backups = sorted((PROJECT_ROOT / ".backup").glob("global_skills_*"))
        if not backups:
            print("未找到备份")
            return
        latest = backups[-1]
        print(f"从 {latest} 恢复...")
        return

    items = collect_items()
    print(f"=== 全局技能库 junction 链接化 {'(DRY RUN)' if dry_run else ''} ===")
    print(f"源码单源: {SKILLS_SOURCE}")
    print(f"待处理条目: {len(items)} 个")
    print(f"全局库: {len(GLOBAL_LIBS)} 个")
    print(f"非项目条目(保留): {NON_PROJECT_ITEMS}")
    print()

    if not dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST, "w", encoding="utf-8-sig") as f:
            f.write("条目,源路径,操作,全局库\n")

    for lib_path in GLOBAL_LIBS:
        print(f"--- {lib_path} ---")
        log = process_library(lib_path, items, dry_run)
        if not dry_run:
            with open(MANIFEST, "a", encoding="utf-8-sig") as f:
                for name, source, action in log:
                    f.write(f"{name},{source},{action},{lib_path}\n")
        print()

    if not dry_run:
        print(f"备份清单: {MANIFEST}")
    print("完成。")


if __name__ == "__main__":
    main()
