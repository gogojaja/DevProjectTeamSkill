#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_production.py 重构回归测试
==================================

背景：tools/publish_production.py 的 main() 原为 159 行、圈复杂度 47，parse_args()
嵌套深度 11（DEEP-CMP-001/002/003 SEVERE 级技术债）。已按发布阶段拆分为
_resolve_version / _print_banner / _print_global_targets / _run_release_gates /
_build_version_dir / _record_rollback_pointer / _create_version_link /
_remove_current / _switch_current / _deploy_global / _check_global_skills /
_verify_consumers / _register_clients / _print_archive_info，parse_args 改为
选项分发表驱动；hashlib 由 __main__ 块内提升到顶层导入。

本测试提供两层保障：
  1. 行为契约测试：参数解析、版本规范化、门禁短路、dry-run、真实发布的软链
     原子切换 / 回滚指针 / 全局库部署 / 消费端验证等关键可观察行为。
  2. 重构等价性测试：取出 git HEAD 版本与工作区版本，在**互不影响的两份同构
     沙箱**上执行同一场景，逐字节比对 stdout / 退出码 / 产物目录树，证明拆分
     未改变行为。HEAD 与工作区一致（重构已提交）时自动跳过。

安全性：所有真实发布场景均在 tmp_path 沙箱内进行，并把 GLOBAL_SKILLS / HOME_DIR /
TARGET_ROOT 重定向到沙箱，绝不触碰用户真实全局技能库。

运行：python -m pytest tests/test_publish_production_refactor.py -q
"""

import ast
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_REL = "tools/publish_production.py"
SCRIPT = REPO_ROOT / SCRIPT_REL

ALL_ROLES = ["dev-project-team-skill", "role-project-init", "role-requirements-analysis",
             "role-architecture", "role-development", "role-testing", "role-deployment",
             "role-governance", "role-program-mgmt", "role-mgmt-consulting", "role-project-mgmt",
             "role-operations", "role-security"]

FIX_VERSION = "21.30.0"

# manifest.json 的 released_at 为 UTC 时间戳，两次运行必然不同，比对前归一化
_TS_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00")


# ---------------------------------------------------------------- 载入工具

def _head_source():
    """取出 git HEAD 版本的脚本源码；不可用时跳过等价对比。"""
    r = subprocess.run(["git", "show", f"HEAD:{SCRIPT_REL}"], cwd=str(REPO_ROOT),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not r.stdout.strip():
        pytest.skip("git HEAD 版本不可用，跳过重构等价对比")
    return r.stdout


def _work_source():
    """读取工作区（重构后）源码。"""
    return SCRIPT.read_text(encoding="utf-8")


def _load_module(src, name, sandbox_root):
    """在指定 PROJECT_ROOT / SKILLS_DIR 下把源码执行为独立模块。

    模块级常量 ROOT / SKILLS_DIR 在 exec 时从环境读取，故先设环境再 exec，
    即可让两份版本各自绑定到自己的沙箱，互不干扰。
    """
    saved = {k: os.environ.get(k) for k in ("PROJECT_ROOT", "SKILLS_DIR")}
    os.environ["PROJECT_ROOT"] = str(sandbox_root)
    os.environ["SKILLS_DIR"] = str(Path(sandbox_root) / ".trae" / "skills")
    try:
        mod = types.ModuleType(name)
        mod.__file__ = str(SCRIPT)
        exec(compile(src, str(SCRIPT), "exec"), mod.__dict__)  # nosec: 测试装载，src 读自本地被测脚本(SCRIPT)非外部输入
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    # HEAD 版本把 import hashlib 放在 __main__ 块内，以导入方式加载时缺失；
    # 为让 dir_hash 分支可被执行，两份版本统一补齐，保证对比公平。
    if not hasattr(mod, "hashlib"):
        mod.hashlib = hashlib
    return mod


def _make_sandbox(base: Path) -> Path:
    """构造最小可发布沙箱，返回沙箱根。

    含 13 个角色包 SKILL.md（copy_skills_to 的强校验要求）、SKILL_INDEX.md、
    references/shared 子库、独立 HOME（含 .config/opencode 父目录）与留档根。
    repo/tools 刻意留空：run_gate 对不存在的门禁脚本返回 True（跳过），使沙箱内
    发布主链路可完整走通，且不依赖真实门禁工具状态。
    """
    repo = base / "repo"
    skills = repo / ".trae" / "skills"
    for role in ALL_ROLES:
        d = skills / role
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            f"# {role}\n\nversion: v{FIX_VERSION}\n\n角色包内容占位。\n", encoding="utf-8")
    (skills / "SKILL_INDEX.md").write_text("# 技能索引\n\n- dev-project-team-skill\n",
                                           encoding="utf-8")
    for sub in ("references", "shared"):
        (skills / sub).mkdir(parents=True, exist_ok=True)
        (skills / sub / "note.md").write_text(f"{sub} 共享资产\n", encoding="utf-8")
    (repo / "tools").mkdir(parents=True, exist_ok=True)
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "readme.md").write_text("docs\n", encoding="utf-8")

    (base / "home" / ".config" / "opencode").mkdir(parents=True, exist_ok=True)
    (base / "archive").mkdir(parents=True, exist_ok=True)
    return base


def _redirect_to_sandbox(mod, base: Path):
    """把模块的用户级全局路径重定向到沙箱，避免污染真实全局技能库。"""
    mod.HOME_DIR = str(base / "home")
    mod.GLOBAL_SKILLS = str(base / "home" / ".config" / "opencode" / "skills")
    mod.TARGET_ROOT = str(base / "archive")
    return mod


def _build(tmp_path, tag, argv=None):
    """沙箱 + 模块装载 + 重定向，一步到位。"""
    _make_sandbox(tmp_path)
    return _redirect_to_sandbox(_load_module(_work_source(), tag, tmp_path / "repo"), tmp_path)


def _snapshot(root: Path) -> dict:
    """快照目录树：相对路径 → 内容（时间戳归一化）/ 链接标记。"""
    out = {}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            out[rel] = f"<link:{os.path.basename(os.readlink(str(p)))}>"
        elif p.is_dir():
            out[rel] = "<dir>"
        else:
            try:
                out[rel] = _TS_PATTERN.sub("<TS>", p.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, OSError):
                out[rel] = f"<bin:{p.stat().st_size}>"
    return out


def _run_main(mod, argv):
    """捕获 stdout 调用 mod.main()，返回 (stdout, SystemExit code 或 None)。"""
    buf = io.StringIO()
    code = None
    saved_argv = sys.argv
    sys.argv = ["publish_production.py", *argv]
    try:
        with redirect_stdout(buf):
            try:
                mod.main()
            except SystemExit as e:      # 脚本以 sys.exit 表达失败语义，需捕获比对
                code = 0 if e.code is None else e.code
    finally:
        sys.argv = saved_argv
    return buf.getvalue(), code


def _capture(fn, *args):
    """捕获无参/带参函数的 stdout。"""
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args)
    return buf.getvalue()


def _wipe(sandbox: Path):
    """清空沙箱：先摘除 current 链接（junction/symlink 用 rmdir 仅删链接本身，
    不递归删目标），再整树删除。"""
    archive = sandbox / "archive"
    if archive.exists():
        for p in list(archive.iterdir()):
            if p.name == "current" or p.name.startswith(".current.tmp."):
                if os.path.lexists(str(p)):
                    try:
                        os.rmdir(str(p))
                    except OSError:
                        try:
                            os.remove(str(p))
                        except OSError:
                            pass
    shutil.rmtree(str(sandbox), ignore_errors=True)


def _run_both(base: Path, argv):
    """在**同一路径**的沙箱上先后执行 HEAD 版本与工作区版本，返回可比对结果。

    必须复用同一路径：dir_hash() 把文件绝对路径也纳入哈希，两份不同路径的
    沙箱会产生伪差异，无法判定行为是否等价。
    """
    src_head, src_work = _head_source(), _work_source()
    if src_head == src_work:
        pytest.skip("HEAD 与工作区一致（重构已提交），无需等价对比")

    sandbox = base / "sb"
    results = []
    for tag, src in (("head", src_head), ("work", src_work)):
        _wipe(sandbox)
        _make_sandbox(sandbox)
        mod = _redirect_to_sandbox(_load_module(src, f"pp_{tag}", sandbox / "repo"), sandbox)
        out, code = _run_main(mod, argv)
        tree = {}
        tree.update(_snapshot(sandbox / "archive"))
        tree.update({"home/" + k: v for k, v in _snapshot(sandbox / "home").items()})
        tree.update({"repo/" + k: v for k, v in _snapshot(sandbox / "repo").items()})
        results.append((out, code, tree))
    _wipe(sandbox)
    return results[0], results[1]


# ================================================================ 行为契约

class TestParseArgs:
    """parse_args 改为分发表驱动后的解析契约。"""

    def test_no_args_defaults(self, tmp_path):
        m = _build(tmp_path, "pp_args")
        r = m.parse_args([])
        assert r[0] == m.TARGET_ROOT
        assert r[1] is None and r[4] is None
        assert r[2] is False and r[3] is False
        assert r[5] is False and r[6] is False and r[7] is False and r[8] is False

    def test_value_options(self, tmp_path):
        m = _build(tmp_path, "pp_args2")
        r = m.parse_args(["--version", "v21.30.0", "--target-dir", str(tmp_path / "x")])
        assert r[1] == "v21.30.0"
        assert r[0] == str(tmp_path / "x")

    def test_flag_options(self, tmp_path):
        m = _build(tmp_path, "pp_args3")
        r = m.parse_args(["--dry-run", "--verify", "--register-clients",
                          "--all-globals", "--no-extra-globals"])
        assert r[2] and r[7] and r[8] and r[5] and r[6]

    def test_gate_desensitize_flag(self, tmp_path):
        assert _build(tmp_path, "pp_args4").parse_args(["--gate-desensitize"])[3] is True

    def test_extra_globals_split_and_strip(self, tmp_path):
        m = _build(tmp_path, "pp_args5")
        assert m.parse_args(["--extra-globals", "trae, workbuddy ,"])[4] == ["trae", "workbuddy"]

    def test_target_dir_expanduser(self, tmp_path):
        m = _build(tmp_path, "pp_args6")
        assert m.parse_args(["--target-dir", "~/x"])[0] == os.path.expanduser("~/x")

    def test_unknown_arg_exits_1(self, tmp_path, capsys):
        m = _build(tmp_path, "pp_args7")
        with pytest.raises(SystemExit) as e:
            m.parse_args(["--nope"])
        assert e.value.code == 1
        assert "未知参数: --nope" in capsys.readouterr().out

    def test_help_exits_0_and_lists_all_flags(self, tmp_path, capsys):
        m = _build(tmp_path, "pp_args8")
        with pytest.raises(SystemExit) as e:
            m.parse_args(["--help"])
        assert e.value.code == 0
        out = capsys.readouterr().out
        for flag in ("--dry-run", "--gate-desensitize", "--verify", "--register-clients",
                     "--no-extra-globals", "--extra-globals", "--all-globals"):
            assert flag in out


class TestVersionResolve:
    """版本号解析与规范化（防 vv 双前缀）。"""

    def test_explicit_version_strips_v_prefix(self, tmp_path):
        assert _build(tmp_path, "pp_v1")._resolve_version("v21.30.0") == FIX_VERSION

    def test_explicit_version_without_prefix_unchanged(self, tmp_path):
        assert _build(tmp_path, "pp_v2")._resolve_version(FIX_VERSION) == FIX_VERSION

    def test_none_reads_from_skill_md(self, tmp_path):
        assert _build(tmp_path, "pp_v3")._resolve_version(None) == FIX_VERSION

    def test_missing_skill_md_exits_1(self, tmp_path, capsys):
        m = _build(tmp_path, "pp_v4")
        os.remove(str(tmp_path / "repo" / ".trae" / "skills"
                      / "dev-project-team-skill" / "SKILL.md"))
        with pytest.raises(SystemExit) as e:
            m._resolve_version(None)
        assert e.value.code == 1
        assert "SKILL.md 缺失" in capsys.readouterr().out


class TestGateOnly:
    """--gate-desensitize 短路路径：不建目录、不切软链、不部署。"""

    def test_gate_only_exits_0_without_side_effects(self, tmp_path):
        m = _build(tmp_path, "pp_gate")
        _, code = _run_main(m, ["--gate-desensitize"])
        assert code == 0
        assert not (tmp_path / "archive" / "current").exists()
        assert not (tmp_path / "archive" / f"v{FIX_VERSION}").exists()

    def test_gate_failure_exits_1(self, tmp_path):
        m = _build(tmp_path, "pp_gate2")
        m.run_desensitize_gate = lambda *a, **k: False
        _, code = _run_main(m, ["--gate-desensitize"])
        assert code == 1


class TestDryRun:
    """dry-run：只探测不落盘。"""

    def test_dry_run_creates_nothing(self, tmp_path):
        m = _build(tmp_path, "pp_dry")
        out, code = _run_main(m, ["--dry-run", "--no-extra-globals"])
        assert code is None
        assert not (tmp_path / "archive" / f"v{FIX_VERSION}").exists()
        assert not (tmp_path / "archive" / "current").exists()
        assert not (tmp_path / "home" / ".config" / "opencode" / "skills").exists()
        assert not (tmp_path / "repo" / "tools" / "mcp_server" / "manifest.json").exists()
        assert "(dry-run) 将创建" in out
        assert "(dry-run) 将设置 current ->" in out
        assert "发布完成。" in out

    def test_version_resolved_before_gate_only(self, tmp_path):
        """版本解析须先于 gate_only 判定（solidify.sh 依赖此顺序）。"""
        m = _build(tmp_path, "pp_order")
        calls = []
        m._resolve_version = lambda v: (calls.append("resolve"), FIX_VERSION)[1]
        m.run_desensitize_gate = lambda *a, **k: (calls.append("gate"), True)[1]
        _run_main(m, ["--gate-desensitize"])
        assert calls == ["resolve", "gate"]


class TestRealPublish:
    """真实发布：版本目录、软链原子切换、回滚指针、全局库部署、manifest。"""

    def test_creates_immutable_version_dir(self, tmp_path):
        m = _build(tmp_path, "pp_pub")
        out, code = _run_main(m, ["--no-extra-globals"])
        assert code is None
        ver = tmp_path / "archive" / f"v{FIX_VERSION}"
        assert ver.is_dir() and (ver / "SKILL_INDEX.md").is_file()
        for role in ALL_ROLES:
            assert (ver / role / "SKILL.md").is_file()
        assert "发布完成。" in out

    def test_current_points_to_version(self, tmp_path):
        m = _build(tmp_path, "pp_pub2")
        _run_main(m, ["--no-extra-globals"])
        cur = tmp_path / "archive" / "current"
        assert cur.exists()
        assert os.path.basename(os.path.realpath(str(cur))) == f"v{FIX_VERSION}"

    def test_deploys_to_global_skills_with_rebuild(self, tmp_path):
        m = _build(tmp_path, "pp_pub3")
        out, _ = _run_main(m, ["--no-extra-globals"])
        g = tmp_path / "home" / ".config" / "opencode" / "skills"
        assert (g / "SKILL_INDEX.md").is_file()
        assert (g / "role-development" / "SKILL.md").is_file()
        assert "已发布到 opencode 全局库" in out

    def test_writes_mcp_manifest_and_version(self, tmp_path):
        m = _build(tmp_path, "pp_pub4")
        _run_main(m, ["--no-extra-globals"])
        srv = tmp_path / "repo" / "tools" / "mcp_server"
        man = json.loads((srv / "manifest.json").read_text(encoding="utf-8"))
        assert man["released_version"] == f"v{FIX_VERSION}"
        assert man["skill_source_version"] == f"v{FIX_VERSION}"
        snippet = man["client_config_snippet"]["mcpServers"]["dev-project-team-skill"]
        assert snippet["args"][0].replace("\\", "/").endswith(
            "tools/mcp_server/skills_mcp_server.py")
        assert (srv / "VERSION").read_text(encoding="utf-8") == f"v{FIX_VERSION}\n"

    def test_existing_version_dir_not_rebuilt(self, tmp_path):
        """不可变留档：版本目录已存在时跳过重建，原有文件不被触碰。"""
        m = _build(tmp_path, "pp_pub5")
        ver = tmp_path / "archive" / f"v{FIX_VERSION}"
        ver.mkdir(parents=True)
        (ver / "SENTINEL.md").write_text("do-not-touch\n", encoding="utf-8")
        out, _ = _run_main(m, ["--no-extra-globals"])
        assert "该版本目录已存在，跳过重建" in out
        assert (ver / "SENTINEL.md").read_text(encoding="utf-8") == "do-not-touch\n"

    def test_rollback_pointer_written_on_republish(self, tmp_path):
        """二次发布须写回滚指针，并把 current 切到新版本。

        指针内容跟平台链接形态相关：symlink 记版本名，Windows 无符号链接权限时
        回退为 junction（os.path.islink 为 False）则记 "unknown"——两者均为原行为，
        此处只断言平台无关的不变量：指针已落盘 + current 已指向新版本。
        """
        m1 = _build(tmp_path, "pp_pub6")
        _run_main(m1, ["--no-extra-globals"])
        (tmp_path / "archive" / "v21.29.0").mkdir(parents=True)
        cur = tmp_path / "archive" / "current"
        _unlink_path(cur)
        _make_link("v21.29.0", cur, tmp_path / "archive")

        m2 = _redirect_to_sandbox(_load_module(_work_source(), "pp_pub7", tmp_path / "repo"),
                                  tmp_path)
        out, _ = _run_main(m2, ["--no-extra-globals"])
        rb = tmp_path / "repo" / ".backup" / "last_production_version.txt"
        assert rb.is_file()
        assert rb.read_text(encoding="utf-8") in ("v21.29.0", "unknown")
        assert "回滚指针已记录" in out
        assert os.path.basename(os.path.realpath(str(cur))) == f"v{FIX_VERSION}"

    def test_rollback_pointer_skipped_when_dry_run(self, tmp_path):
        m = _build(tmp_path, "pp_rb_dry")
        (tmp_path / "archive" / "v21.29.0").mkdir(parents=True)
        cur = tmp_path / "archive" / "current"
        cur.mkdir(parents=True)
        (cur / "marker.txt").write_text("real-dir\n", encoding="utf-8")
        _run_main(m, ["--dry-run", "--no-extra-globals"])
        assert not (tmp_path / "repo" / ".backup" / "last_production_version.txt").exists()
        assert (cur / "marker.txt").is_file()

    def test_rollback_pointer_records_unknown_for_real_dir(self, tmp_path):
        """current 为实体目录（非链接）时记 "unknown"，保持原行为。"""
        m = _build(tmp_path, "pp_rb_dir")
        cur = tmp_path / "archive" / "current"
        cur.mkdir(parents=True)
        _capture(m._record_rollback_pointer, str(cur), False)
        rb = tmp_path / "repo" / ".backup" / "last_production_version.txt"
        assert rb.read_text(encoding="utf-8") == "unknown"

    def test_rollback_pointer_noop_when_current_absent(self, tmp_path):
        m = _build(tmp_path, "pp_rb_none")
        _capture(m._record_rollback_pointer, str(tmp_path / "archive" / "current"), False)
        assert not (tmp_path / "repo" / ".backup" / "last_production_version.txt").exists()

    def test_rollback_pointer_records_symlink_target(self, tmp_path):
        """current 为真 symlink 时记其指向的版本名（平台不支持建链则跳过）。"""
        m = _build(tmp_path, "pp_rb_link")
        (tmp_path / "archive" / "v21.29.0").mkdir(parents=True)
        cur = tmp_path / "archive" / "current"
        try:
            os.symlink("v21.29.0", str(cur), target_is_directory=True)
        except OSError:
            pytest.skip("当前平台/权限不支持符号链接")
        _capture(m._record_rollback_pointer, str(cur), False)
        rb = tmp_path / "repo" / ".backup" / "last_production_version.txt"
        assert rb.read_text(encoding="utf-8") == "v21.29.0"

    def test_gate_failure_aborts_before_publish(self, tmp_path):
        m = _build(tmp_path, "pp_abort")
        m.run_gate = lambda *a, **k: False
        out, code = _run_main(m, ["--no-extra-globals"])
        assert code == 1
        assert "发布中止：门禁未通过。" in out
        assert not (tmp_path / "archive" / f"v{FIX_VERSION}").exists()

    def test_desensitize_gate_failure_aborts(self, tmp_path):
        m = _build(tmp_path, "pp_abort2")
        m.run_desensitize_gate = lambda *a, **k: False
        _, code = _run_main(m, ["--no-extra-globals"])
        assert code == 1
        assert not (tmp_path / "archive" / f"v{FIX_VERSION}").exists()


def _unlink_path(p: Path):
    """删链接本身（symlink/junction）或空目录，不递归删目标内容。"""
    if not os.path.lexists(str(p)):
        return
    try:
        os.rmdir(str(p))
    except OSError:
        os.remove(str(p))


def _make_link(target_name, link_path: Path, base: Path):
    """跨平台建链：优先 symlink，Windows 无权限时回退目录 junction。"""
    try:
        os.symlink(target_name, str(link_path), target_is_directory=True)
    except OSError:
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link_path),
                        str(base / target_name)], check=True, capture_output=True)


class TestVerifyAndRegister:
    """消费端验证与 MCP 客户端注册的输出契约。"""

    def test_verify_all_pass(self, tmp_path):
        m = _build(tmp_path, "pp_ver1")
        _run_main(m, ["--no-extra-globals"])
        g = tmp_path / "home" / ".config" / "opencode" / "skills"
        for role in ALL_ROLES[1:]:
            (g / role).mkdir(parents=True, exist_ok=True)
        out = _capture(m._verify_consumers)
        assert "SKILL_INDEX.md 存在于全局库" in out
        assert "消费端验证通过" in out

    def test_verify_reports_missing_index(self, tmp_path):
        m = _build(tmp_path, "pp_ver2")
        _run_main(m, ["--no-extra-globals"])
        os.remove(str(tmp_path / "home" / ".config" / "opencode" / "skills" / "SKILL_INDEX.md"))
        out = _capture(m._verify_consumers)
        assert "SKILL_INDEX.md 缺失于全局库" in out
        assert "消费端验证存在告警" in out

    def test_verify_reports_insufficient_roles(self, tmp_path):
        m = _build(tmp_path, "pp_ver3")
        g = tmp_path / "home" / ".config" / "opencode" / "skills"
        g.mkdir(parents=True)
        (g / "SKILL_INDEX.md").write_text("idx\n", encoding="utf-8")
        out = _capture(m._verify_consumers)
        assert "角色包目录数不足" in out
        assert "消费端验证存在告警" in out

    def test_verify_warns_when_global_missing_but_still_passes(self, tmp_path):
        """全局库不存在时仅告警，结论仍为通过（保持原行为，勿误判为失败）。"""
        m = _build(tmp_path, "pp_ver4")
        out = _capture(m._verify_consumers)
        assert "全局库不存在" in out
        assert "消费端验证通过" in out

    def test_register_clients_skips_when_script_absent(self, tmp_path):
        m = _build(tmp_path, "pp_reg")
        assert "register_mcp_client.py 不存在，跳过" in _capture(m._register_clients, False)


class TestGlobalTargets:
    """全局目标解析矩阵。"""

    def test_no_extra_only_opencode(self, tmp_path):
        m = _build(tmp_path, "pp_tgt1")
        assert list(m.resolve_global_targets(None, False, True)) == ["opencode"]

    def test_all_globals_includes_seven(self, tmp_path):
        t = _build(tmp_path, "pp_tgt2").resolve_global_targets(None, True, False)
        assert len(t) == 7 and t["opencode"]["rebuild"] is True

    def test_extra_list_selects(self, tmp_path):
        t = _build(tmp_path, "pp_tgt3").resolve_global_targets(["trae", "claude"], False, False)
        assert set(t) == {"opencode", "trae", "claude"}

    def test_auto_discovery_by_parent_dir(self, tmp_path):
        m = _build(tmp_path, "pp_tgt4")
        (tmp_path / "home" / ".trae").mkdir(parents=True)
        assert "trae" in m.resolve_global_targets(None, False, False)
        assert "workbuddy" not in m.resolve_global_targets(None, False, False)


# ================================================================ 重构等价性

@pytest.mark.parametrize("argv", [
    ["--dry-run", "--no-extra-globals"],
    ["--dry-run", "--all-globals"],
    ["--dry-run", "--extra-globals", "trae,workbuddy"],
    ["--dry-run", "--no-extra-globals", "--verify", "--register-clients"],
    ["--dry-run", "--no-extra-globals", "--version", "v21.30.0"],
    ["--dry-run", "--no-extra-globals", "--version", "21.30.0"],
    ["--no-extra-globals"],
    ["--all-globals"],
    ["--no-extra-globals", "--verify"],
    ["--gate-desensitize"],
    ["--help"],
    ["--bogus-flag"],
])
def test_head_vs_work_equivalence(tmp_path, argv):
    """HEAD 版本与重构版本在同构沙箱上的 stdout / 退出码 / 产物树须完全一致。"""
    (h_out, h_code, h_tree), (w_out, w_code, w_tree) = _run_both(tmp_path, argv)
    assert h_code == w_code, f"退出码不一致: head={h_code} work={w_code}"
    assert h_out == w_out, "stdout 不一致:\n" + _first_diff(h_out, w_out)
    assert h_tree == w_tree, "产物目录树不一致:\n" + "\n".join(
        f"  {k}: head={h_tree.get(k)!r} work={w_tree.get(k)!r}"
        for k in sorted(set(h_tree) | set(w_tree)) if h_tree.get(k) != w_tree.get(k))


def _first_diff(a, b):
    la, lb = a.splitlines(), b.splitlines()
    for i, (x, y) in enumerate(zip(la, lb)):
        if x != y:
            return f"  L{i}: head={x!r}\n  L{i}: work={y!r}"
    return f"  行数不同: head={len(la)} work={len(lb)}"


# ================================================================ 结构指标

def test_main_and_parse_args_below_threshold():
    """重构后 main / parse_args 须降到阈值内（防债务回弹）。"""
    tree = ast.parse(_work_source())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ("main", "parse_args"):
            length = node.end_lineno - node.lineno + 1
            cc = 1 + sum(isinstance(x, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                                        ast.BoolOp, ast.IfExp, ast.comprehension))
                         for x in ast.walk(node))
            assert length <= 80, f"{node.name} 长度 {length} 超阈值 80"
            assert cc <= 15, f"{node.name} 圈复杂度 {cc} 超阈值 15"


def test_hashlib_imported_at_top():
    """hashlib 须在模块顶层导入：原置于 __main__ 块内，模块被导入时 dir_hash 抛 NameError。"""
    src = _work_source()
    tree = ast.parse(src)
    top_names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_names.update(a.name for a in node.names)
    assert "hashlib" in top_names


def test_no_shell_true():
    """安全基线：不得引入 shell=True。"""
    assert "shell=True" not in _work_source()
