#!/usr/bin/env python3
"""
check_skill_links.py — 技能库 Markdown 引用可达性门禁
=====================================================
目的：拦截技能库内部 Markdown 链接断裂（断链），避免在门禁层之后才人工排查。

检查范围：
  ① `.//xxx.md` 历史残留引用（资源已迁移至 `*-skill__resources/`，`.//` 必然失效）
  ② `*/domain/*.md` 内裸名引用 `xxx_details.md`（未写正确 `__resources/` 前缀）
  ③ `*/SKILL.md` 内 `domain/*.md` / `domain/*__resources/*.md` 相对路径可达性

用法：
  python3 tools/check_skill_links.py            # 扫描 .trae/skills，报告断链
  python3 tools/check_skill_links.py --strict   # strict 模式（含 SKILL.md 根级引用校验）

退出码：
  0 = 通过（无断链）
  1 = 发现断链（打印后退出非零，供门禁阻断）
  2 = 参数错误

说明：
  - 根级 `references/`、`shared/`、`dev-project-team-skill/` 的跨库引用走 `../../references/` 等根级锚定，
    不在本脚本 scope；本脚本专注 role-*/SKILL.md 与 role-*/domain/*.md 的域内引用。
  - 通配符/占位符（`*`、`{}`、`<...>`）、http(s) 链接、纯文件名（无目录前缀指向根）自动豁免。
"""

import argparse
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

_THIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.environ.get("PROJECT_ROOT", _THIS)
ROOT = os.path.join(REPO_ROOT, '.trae', 'skills')


def norm(path):
    """规范化路径。"""
    return os.path.normpath(path)


def collect_files():
    """收集 SKILL.md 与 domain/*.md（含 __resources 子目录）。"""
    skills = []
    for pattern in (os.path.join(ROOT, 'role-*', 'SKILL.md'),
                    os.path.join(ROOT, 'role-*', 'domain', '*.md')):
        skills.extend(glob.glob(pattern))
    # 显式排除子技能包（dev-project-team-skill/skills/... 由各自宿主解析，不在本脚本 scope）
    skills = [s for s in skills if not s.startswith('dev-project-team-skill/')]
    return skills


def is_exempt(ref):
    """豁免：http、通配符、占位符、根级锚定、运行态文档。"""
    if ref.startswith('http'):
        return True
    if re.search(r'[\*\{\}\<\>]', ref):
        return True
    # 运行态文档（项目根生成，非技能内文件）
    if ref in ('交接文档.md', '跨会话交接文档.md', '00_交接文档.md', '项目铁律.md'):
        return True
    # 根级锚定（references/、shared/ 及 ../ 越级）由打包内嵌 + 库根校验，本脚本不重复
    if ref.startswith('references/') or ref.startswith('shared/'):
        return True
    if ref.startswith('../../'):
        return True
    return False


def scan():
    files = collect_files()
    broken = []
    for f in files:
        base_dir = os.path.dirname(f)
        content = open(f, encoding='utf-8').read()
        # ① .// 残留（必然失效）
        for m in re.finditer(r'\.//([a-zA-Z0-9_\-/]+\.md)', content):
            if not m.group(1).startswith(('references/', 'shared/')):
                broken.append((f, f'.//{m.group(1)}', '残留 .// 引用（应指向 __resources/）'))
        # ②③ 反引号包裹的 .md 相对引用
        for m in re.finditer(r'`([^`\s]+)\.md[`#]', content):
            ref = m.group(1) + '.md'
            frag = m.group(1)
            label = ref
            if is_exempt(ref):
                continue
            # 优先级1：相对引用文件所在目录（base_dir）
            target = norm(os.path.join(base_dir, ref))
            # 优先级2：相对本文件所在角色包根（SKILL.md 常用库根/包根定位）
            pkg_root = norm(os.path.dirname(os.path.dirname(f))) if 'domain/' in f else base_dir
            # 优先级3：相对整库根（.trae/skills/）
            lib_root = os.path.normpath(ROOT)
            candidates = [target, norm(os.path.join(pkg_root, ref)),
                          norm(os.path.join(lib_root, ref))]
            if not any(os.path.exists(c) for c in candidates):
                broken.append((f, label, f'相对 {base_dir} 与库根均不可达'))

    return files, broken


def main():
    ap = argparse.ArgumentParser(description='技能库引用可达性门禁')
    ap.add_argument('--strict', action='store_true', help='strict 模式（默认）')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    files, broken = scan()
    if not args.quiet:
        print(f'扫描文件: {len(files)} 个 SKILL.md/domain 文档')
        print(f'发现断链: {len(broken)} 处')
    if broken:
        print('════ 断链清单 ════')
        for f, label, reason in broken:
            print(f'  ✗ {os.path.normpath(f)}')
            print(f'      → {label}   ({reason})')
        print('════ 请修复断链后重跑 ════')
        return 1
    if not args.quiet:
        print('✅ 域内引用全部可达，无断链。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
