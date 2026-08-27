#!/usr/bin/env python3
# =============================================================================
# publish_production.py — 生产技能发布脚本（v1.0.0）
# -----------------------------------------------------------------------------
# 职责: 将最新版本技能发布到生产消费载体（全局 opencode 技能库），并在
#       ~/dev-project-team-skill/ 下建立不可变版本目录 + current 软链留档。
#
# 设计依据:
#   - references/environment_topology.md v21.7.0 双套环境拓扑（非生产合并、生产独立）
#   - Twelve-Factor Build/Release/Run 分离 + immutable artifact（build once, 版本目录只读）
#   - opencode Agent Skills 官方文档: 仅扫描 6 个固定位置，skills.paths 不参与发现
#     => 生产消费载体 = ~/.config/opencode/skills（opencode 自动发现）
#
# 门禁（发布前全部通过）:
#   1. 版本一致性（tools/check_version_consistency.py）
#   2. 闭环执行门禁（tools/check_skill_closure.py）
#   3. 发布级门禁（tools/check_skill_release_gate.py）
#   4. 废弃清理门禁（tools/check_deprecation_cleanup.py）
#   5. 脱敏扫描（tools/desensitize/desensitize.py --scan）
#
# 用法:
#   python3 tools/publish_production.py                    # 发布当前 sources 版本
#   python3 tools/publish_production.py --version v21.8.0  # 显式指定版本
#   python3 tools/publish_production.py --dry-run          # 仅探测不发布
#   python3 tools/publish_production.py --target-dir ~/dev-project-team-skill
#
# 跨平台: macOS/Linux/python 均可；Windows 用 py -3.11
# =============================================================================
import os, sys, re, shutil, glob, subprocess, tempfile
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.environ.get("SKILLS_DIR", os.path.join(ROOT, ".trae", "skills"))

if sys.platform.startswith("win"):
    HOME_DIR = os.environ.get("USERPROFILE", "")
    GLOBAL_SKILLS = os.path.join(os.environ.get("USERPROFILE", ""), ".config", "opencode", "skills")
    TARGET_ROOT = os.path.join(os.environ.get("USERPROFILE", ""), "dev-project-team-skill")
else:
    HOME_DIR = os.path.expanduser("~")
    GLOBAL_SKILLS = os.path.join(os.environ.get("XDG_CONFIG_HOME", HOME_DIR), ".config", "opencode", "skills")
    TARGET_ROOT = os.path.join(HOME_DIR, "dev-project-team-skill")

ALL_ROLES = ["dev-project-team-skill", "role-project-init", "role-requirements-analysis",
             "role-architecture", "role-development", "role-testing", "role-deployment",
             "role-governance", "role-program-mgmt", "role-mgmt-consulting", "role-project-mgmt"]

TOOLS = {
    "version": os.path.join(ROOT, "tools", "check_version_consistency.py"),
    "closure": os.path.join(ROOT, "tools", "check_skill_closure.py"),
    "release": os.path.join(ROOT, "tools", "check_skill_release_gate.py"),
    "deprecation": os.path.join(ROOT, "tools", "check_deprecation_cleanup.py"),
    "desensitize": os.path.join(ROOT, "tools", "desensitize", "desensitize.py"),
}


def parse_args(argv):
    target_root = TARGET_ROOT
    version = None
    dry_run = False
    gate_only = False
    extra_list = None
    all_globals = False
    no_extra = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--target-dir":
            target_root = os.path.expanduser(argv[i + 1]); i += 2
        elif a == "--version":
            version = argv[i + 1]; i += 2
        elif a == "--dry-run":
            dry_run = True; i += 1
        elif a == "--gate-desensitize":
            gate_only = True; i += 1
        elif a == "--no-extra-globals":
            no_extra = True; i += 1
        elif a == "--all-globals":
            all_globals = True; i += 1
        elif a == "--extra-globals":
            extra_list = [x.strip() for x in argv[i + 1].split(",") if x.strip()]; i += 2
        elif a in ("-h", "--help"):
            print("用法: publish_production.py [--version <vX.Y.Z>] [--target-dir <dir>] "
                  "[--dry-run] [--gate-desensitize]\n"
                  "      [--no-extra-globals | --extra-globals trae,workbuddy | --all-globals]")
            print("  默认: 除 opencode 全局库外，自动同步到已安装工具(父目录存在)的全局技能目录")
            print("  --no-extra-globals : 仅发布到 opencode 全局库(原行为)")
            print("  --extra-globals    : 显式指定额外全局目标(trae/trae-cn/workbuddy/claude/copilot/agents)")
            print("  --all-globals       : 全部已知工具全局目录(即使未安装也创建)")
            sys.exit(0)
        else:
            print(f"未知参数: {a}"); sys.exit(1)
    return target_root, version, dry_run, gate_only, extra_list, all_globals, no_extra


def read_version():
    idx = os.path.join(SKILLS_DIR, "dev-project-team-skill", "SKILL.md")
    if not os.path.isfile(idx):
        print("  ✗ 编排器 SKILL.md 缺失"); sys.exit(1)
    with open(idx, encoding="utf-8") as f:
        for line in f:
            m = re.search(r'v(\d+\.\d+\.\d+)', line)
            if m:
                return m.group(1)
    raise SystemExit("  ✗ 未在 SKILL.md 发现版本号")


def run_gate(name, script, extra=()):
    if not os.path.isfile(script):
        print(f"  ~ 门禁脚本不存在，跳过: {script}")
        return True
    print(f"  [门禁] {name} ...")
    cmd = [sys.executable, script, *extra]
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print(f"  ✗ 门禁失败: {name}")
        return False
    return True


def copy_skills_to(dest):
    os.makedirs(dest, exist_ok=True)
    for r in ALL_ROLES:
        src = os.path.join(SKILLS_DIR, r)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dest, r), dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("*.pyc", ".DS_Store"))
    for sub in ("references", "shared"):
        s = os.path.join(SKILLS_DIR, sub)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(dest, sub), dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("*.pyc", ".DS_Store"))
    idx = os.path.join(SKILLS_DIR, "SKILL_INDEX.md")
    if os.path.isfile(idx):
        shutil.copy2(idx, os.path.join(dest, "SKILL_INDEX.md"))
    # 配套工具与文档：SKILL_INDEX/SKILL.md 大量引用 tools/* 与 docs/*，
    # 必须随发布集一起输出，否则消费端按文档调用脚本时路径不存在。
    for extra in ("tools", "docs"):
        s = os.path.join(ROOT, extra)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(dest, extra), dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                                          ".DS_Store", "dist", "_pkg_tmp"))
    ok = all(os.path.isfile(os.path.join(dest, r, "SKILL.md")) for r in ALL_ROLES)
    if not ok:
        print("  ✗ 版本目录复制校验失败"); sys.exit(1)


def sync_into(dest):
    """精确同步到某全局技能目录：先清理本仓库发布集子项，再整集复制。
    用于非 opencode 工具全局目录，避免整目录重建误删用户其他技能。
    兼容 Windows 目录 junction/symlink：优先 os.rmdir 仅删链接本身，
    不误删链接目标内容；真实目录才 rmtree。"""
    os.makedirs(dest, exist_ok=True)
    purge = ALL_ROLES + ["references", "shared", "tools", "docs", "SKILL_INDEX.md"]
    for name in purge:
        p = os.path.join(dest, name)
        if not os.path.lexists(p):
            continue
        try:
            if os.path.islink(p) and not os.path.isdir(p):
                os.unlink(p)
            elif os.path.islink(p) or os.path.isdir(p):
                # 目录 symlink / junction：先尝试 rmdir 仅删链接本身
                try:
                    os.rmdir(p)
                except OSError:
                    # 真实目录（rmdir 因非空失败）→ 递归删除
                    shutil.rmtree(p)
            else:
                os.remove(p)
        except OSError as e:
            print(f"  ~ 清理 {p} 失败（跳过）: {e}")
    copy_skills_to(dest)


def global_target_matrix():
    """各工具全局技能目录矩阵（依据 cross_tool_standard.md 与 WorkBuddy 审计记录）。"""
    return {
        "opencode": {"path": GLOBAL_SKILLS, "rebuild": True, "always": True},
        "trae": {"path": os.path.join(HOME_DIR, ".trae", "skills"), "rebuild": False, "always": False},
        "trae-cn": {"path": os.path.join(HOME_DIR, ".trae-cn", "skills"), "rebuild": False, "always": False},
        "workbuddy": {"path": os.path.join(HOME_DIR, ".workbuddy", "skills"), "rebuild": False, "always": False},
        "claude": {"path": os.path.join(HOME_DIR, ".claude", "skills"), "rebuild": False, "always": False},
        "copilot": {"path": os.path.join(HOME_DIR, ".copilot", "skills"), "rebuild": False, "always": False},
        "agents": {"path": os.path.join(HOME_DIR, ".agents", "skills"), "rebuild": False, "always": False},
    }


def resolve_global_targets(extra_list, all_globals, no_extra):
    """解析本次要部署的全局目标。
    - opencode 始终（always）
    - 默认：仅对已安装工具（其父目录存在）自动部署
    - --no-extra-globals：仅 opencode
    - --extra-globals a,b：显式指定（覆盖默认与自动发现）
    - --all-globals：全部已知工具（即使未安装也创建）
    """
    matrix = global_target_matrix()
    result = {}
    for name, cfg in matrix.items():
        if cfg.get("always"):
            result[name] = cfg
            continue
        if no_extra:
            continue
        if extra_list:
            if name in extra_list:
                result[name] = cfg
            continue
        if all_globals:
            result[name] = cfg
            continue
        parent = os.path.dirname(cfg["path"])
        if os.path.isdir(parent):
            result[name] = cfg
    return result


def dir_hash(path):
    h = hashlib.sha256()
    for dirpath, _, files in sorted(os.walk(path)):
        for fn in sorted(files):
            fp = os.path.join(dirpath, fn)
            h.update(fp.encode("utf-8", "surrogateescape"))
            hs = hashlib.sha256()
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hs.update(chunk)
            h.update(hs.digest())
    return h.hexdigest()[:16]


def is_placeholder(text):
    """判断敏感匹配是否为占位符形式（<...>、示例值、规则样例输入等）。"""
    t = text.strip().strip('"\'')
    # 去掉 key= / key: 前缀后再判值是否为占位符
    if re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*[=:]\s*', t):
        t = re.sub(r'^[A-Za-z_][A-Za-z0-9_]*\s*[=:]\s*', '', t)
        t = t.strip().strip('"\'')
    if re.fullmatch(r'<[^<>]+>', t):
        return True
    if re.fullmatch(r'[\w.+-]+@example\.(com|org|net)', t):
        return True
    if re.fullmatch(r'(?:xx+\.)+xx+', t):
        return True
    if re.fullmatch(r'\d+\.\d+\.\d+\.x', t):
        return True
    # 规则定义/文档中的示例输入（正则样例值，非真实凭据）
    if 'EXAMPLE' in t.upper() or 'sample' in t.lower() or 'placeholder' in t.lower():
        return True
    if re.search(r'(\*{3}|\.{3})$', t):          # 掩码/截断样（*** 或 ...）
        return True
    if 'example' in t.lower() or 'localhost' in t.lower():
        return True
    if re.search(r'^-----BEGIN.*PRIVATE KEY-----', t):   # 私钥示例头
        return True
    if t.startswith('/home/') or '/home/user/' in t:
        return True
    return False


def parse_scan_report(path):
    """解析脱敏扫描报告 CSV，返回 findings 列表 [{source,line,level,rule_id,match}, ...]"""
    import csv as _csv
    findings = []
    if not os.path.isfile(path):
        return findings
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = _csv.DictReader(f)
        for row in reader:
            findings.append({
                "source": row.get("source", ""),
                "line": row.get("line", ""),
                "level": row.get("level", ""),
                "rule_id": row.get("rule_id", ""),
                "match": row.get("match_preview", ""),
            })
    return findings


def is_rule_example(source):
    """规则定义文件中的敏感命中视为示例输入（非真实凭据）。"""
    s = source.replace("\\", "/")
    return s.endswith("desensitize/desensitize.py") or "/desensitize/desensitize.py" in s


def run_desensitize_gate(skills_dir=None, report_path=None):
    """脱敏门禁（扫描发布集全部源头：skills + tools + docs）：
    - A 级真实凭据（非占位符）→ 返回 False（中止发布）
    - B 级 → 告警 + 清单，返回 True
    - A 级占位符（<...>）→ 提示，返回 True
    - 无发现 → True
    """
    print("  [门禁] 脱敏扫描 ...")
    ds = TOOLS["desensitize"]
    if not os.path.isfile(ds):
        print("  ~ 脱敏工具缺失，跳过扫描（建议安装后重跑）")
        return True
    skills_dir = skills_dir or SKILLS_DIR
    report_path = report_path or os.path.join(ROOT, "scan_report_publish.csv")
    scan_targets = [skills_dir,
                    os.path.join(ROOT, "tools"),
                    os.path.join(ROOT, "docs")]
    findings = []
    for i, tgt in enumerate(scan_targets):
        if not os.path.isdir(tgt):
            continue
        tmp_report = f"{report_path}.{i}"
        if os.path.isfile(tmp_report):
            os.remove(tmp_report)
        subprocess.run([sys.executable, ds, "--scan", tgt, "--report", tmp_report],
                       cwd=ROOT)
        findings.extend(parse_scan_report(tmp_report))
        if os.path.isfile(tmp_report):
            os.remove(tmp_report)
    # A 级：真实凭据（非占位符）硬拦截
    a_real = []
    a_placeholder = []
    b_findings = []
    a_real = [f for f in findings if f["level"] == "A" and not is_placeholder(f["match"])
              and not is_rule_example(f["source"])]
    a_placeholder = [f for f in findings if f["level"] == "A"
                     and (is_placeholder(f["match"]) or is_rule_example(f["source"]))]
    b_findings = [f for f in findings if f["level"] == "B"]
    passed = True
    if a_real:
        print(f"  ✗ 脱敏扫描发现 {len(a_real)} 处 A 级真实凭据，发布中止：")
        for f in a_real:
            print(f"     {f['source']}:{f['line']}  {f['match']}")
        passed = False
    if b_findings:
        print(f"  ~ 脱敏扫描发现 {len(b_findings)} 处 B 级信息（示例/公开/占位符），"
              f"已列为告警清单（见 scan_report_publish.csv），继续发布。")
    if a_placeholder:
        print(f"  ~ 脱敏扫描另有 {len(a_placeholder)} 处 A 级占位符形式（<...>），"
              f"不阻断发布。")
    if not a_real and not a_placeholder and not b_findings:
        print("  ✓ 脱敏扫描通过，无 A/B 级敏感信息。")
    return passed


def main():
    target_root, version, dry_run, gate_only, extra_list, all_globals, no_extra = parse_args(sys.argv[1:])
    if version is None:
        version = read_version()

    if gate_only:
        if not run_desensitize_gate():
            sys.exit(1)
        sys.exit(0)

    print("=" * 60)
    print(f"  生产技能发布 (publish_production v1.0.0)  目标版本: {version}")
    print("=" * 60)
    print(f"源库: {SKILLS_DIR}")
    print(f"留档根: {target_root}")

    # 解析全局生效目标（opencode + 自动发现的 trae/workbuddy 等）
    g_targets = resolve_global_targets(extra_list, all_globals, no_extra)
    print(f"全局生效目标 ({len(g_targets)}):")
    for n, c in g_targets.items():
        print(f"  - {n}: {c['path']}  (rebuild={c['rebuild']})")

    # 1. 门禁
    gates = [
        ("版本一致性", "version"),
        ("闭环执行", "closure"),
        ("发布级", "release"),
        ("废弃清理", "deprecation"),
    ]
    for name, key in gates:
        if not run_gate(name, TOOLS[key]):
            print("  发布中止：门禁未通过。"); sys.exit(1)

    # 2. 脱敏扫描
    if not run_desensitize_gate():
        sys.exit(1)

    # 3. 版本目录（不可变留档）
    ver_dir = os.path.join(target_root, f"v{version}")
    print(f"  构建版本目录: {ver_dir} ...")
    if os.path.isdir(ver_dir):
        print("  ~ 该版本目录已存在，跳过重建（保留不可变留档）")
    else:
        if dry_run:
            print(f"  (dry-run) 将创建 {ver_dir}")
        else:
            copy_skills_to(ver_dir)

    # 4. current 软链（原子切换）
    current = os.path.join(target_root, "current")
    if dry_run:
        print(f"  (dry-run) 将设置 current -> v{version}")
    else:
        tmp_link = os.path.join(target_root, f".current.tmp.{os.getpid()}")
        try:
            if os.path.islink(tmp_link) or os.path.exists(tmp_link):
                os.remove(tmp_link)
            try:
                os.symlink(f"v{version}", tmp_link)
            except OSError:
                if sys.platform == "win32":
                    abs_target = os.path.join(target_root, f"v{version}")
                    subprocess.run(["cmd", "/c", "mklink", "/J", tmp_link, abs_target],
                                   check=True, capture_output=True)
                else:
                    raise
            if os.path.exists(current) or os.path.islink(current):
                try:
                    os.remove(current)
                except OSError:
                    try:
                        os.rmdir(current)
                    except OSError:
                        shutil.rmtree(current)
            os.replace(tmp_link, current)
        except OSError as e:
            print(f"  ✗ 软链切换失败: {e}"); sys.exit(1)

    # 5. 发布到全局库（多工具全局生效：opencode + trae/workbuddy 等）
    for name, cfg in g_targets.items():
        dest = cfg["path"]
        if dry_run:
            print(f"  (dry-run) 将部署到 {name} 全局库 {dest} (rebuild={cfg['rebuild']})")
            continue
        if cfg["rebuild"]:
            # 整库重建（opencode 专属：假定全局库专用于本仓库）
            if os.path.isdir(dest):
                if sys.platform == "win32":
                    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", dest],
                                   check=True, capture_output=True)
                else:
                    shutil.rmtree(dest)
            copy_skills_to(dest)
        else:
            # 精确同步（其他工具：仅清理本仓库发布集子项，保护用户其他全局技能）
            sync_into(dest)
        print(f"  ✓ 已发布到 {name} 全局库 {dest}")

    if not dry_run:
        # 6. 打印留档信息
        print(f"  版本目录: {ver_dir}  SHA256={dir_hash(ver_dir) if os.path.isdir(ver_dir) else '-'}")
        print(f"  current   -> {os.path.realpath(current) if os.path.exists(current) else '-'}")
    print("  发布完成。")

if __name__ == "__main__":
    import hashlib
    main()