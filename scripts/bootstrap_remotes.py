#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bootstrap_remotes.py — 迁移初始化引导（跨平台，Windows 主推）
新机器 clone 本仓库后执行，完成以下初始化：
  1. 安装 Git 钩子
  2. 定位/引导创建 dev-git-hub（推送工具单一信源）
  3. 配置 git remotes（origin=GitHub, mirror=Gitee）
  4. 引导配置凭据（.secrets/）
  5. 验证代理链路

用法：
  python tools/bootstrap_remotes.py         # Windows
  python3 scripts/bootstrap_remotes.py      # macOS/Linux
"""
import os
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(cmd, check=False, **kw):
    """运行命令，返回 CompletedProcess。"""
    return subprocess.run(cmd, capture_output=True, text=True, shell=False, **kw)


def git(*args, cwd=None):
    """执行 git 命令，返回 stdout.strip()。"""
    r = run(["git"] + list(args), cwd=cwd or str(REPO_ROOT))
    return r.stdout.strip() if r.returncode == 0 else ""


def prompt(msg, default=""):
    """交互式输入。"""
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"{msg}{suffix}: ").strip()
    except EOFError:
        val = ""
    return val or default


def main():
    print("=" * 42)
    print("  DevProjectTeamSkill 迁移初始化")
    print("=" * 42)

    hub_root = REPO_ROOT.parent / "dev-git-hub"

    # ---- 1. 安装 Git 钩子 ----
    print("\n[1/5] 安装 Git 钩子...")
    hook_script = REPO_ROOT / "scripts" / "install-hooks.sh"
    if hook_script.exists():
        if sys.platform == "win32":
            r = run(["git", "config", "core.hooksPath", ".githooks"])
            print("  [OK] core.hooksPath = .githooks" if r.returncode == 0 else "  [WARN] 设置失败")
        else:
            r = run(["bash", str(hook_script)])
            if r.returncode == 0:
                print("  [OK] 钩子已安装")
            else:
                print("  [WARN] install-hooks.sh 执行失败，手动运行")
    else:
        print("  [WARN] install-hooks.sh 不存在，跳过")

    # 赋可执行位（非 Windows）
    hooks_dir = REPO_ROOT / ".githooks"
    if hooks_dir.is_dir() and sys.platform != "win32":
        for f in hooks_dir.iterdir():
            f.chmod(0o755)

    # ---- 2. 定位/引导创建 dev-git-hub ----
    print("\n[2/5] 检查 dev-git-hub（推送工具单一信源）...")
    if (hub_root / "tools").is_dir():
        print(f"  [OK] dev-git-hub 已存在: {hub_root}")
    else:
        print(f"  [WARN] dev-git-hub 未找到: {hub_root}")
        print("  dev-git-hub 是 GitHub/Gitee 推送工具的独立项目（单一信源）。")
        print("  本仓库经薄封装代理调用其推送工具，不内嵌实现。")
        print()
        print("  请选择初始化方式：")
        print("    a) clone dev-git-hub 到同级目录（推荐）")
        print("    b) 指定 dev-git-hub 在其他位置")
        print("    c) 暂时跳过（推送不可用，本地提交不受影响）")
        choice = prompt("\n  选择 (a/b/c)", "c")
        if choice == "a":
            hub_url = prompt("  dev-git-hub 远端 URL")
            if hub_url:
                r = run(["git", "clone", hub_url, str(hub_root)])
                print("  [OK] dev-git-hub 已 clone" if r.returncode == 0
                      else f"  [FAIL] {r.stderr.strip()}")
        elif choice == "b":
            hub_path = prompt("  dev-git-hub 绝对路径")
            if hub_path:
                cfg = REPO_ROOT / ".hub_root"
                cfg.write_text(hub_path, encoding="utf-8")
                print(f"  [OK] 已写入 .hub_root: {hub_path}")
        else:
            print("  [SKIP] 跳过 dev-git-hub 初始化")

    # ---- 3. 配置 git remotes ----
    print("\n[3/5] 检查 git remotes...")
    origin_url = git("remote", "get-url", "origin")
    mirror_url = git("remote", "get-url", "mirror")

    if not origin_url:
        gh_url = prompt("  GitHub 远端 URL (origin，留空跳过)")
        if gh_url:
            git("remote", "add", "origin", gh_url)
            print(f"  [OK] origin 已配置: {gh_url}")
    else:
        print(f"  [OK] origin 已存在: {origin_url}")

    if not mirror_url:
        ge_url = prompt("  Gitee 远端 URL (mirror，留空跳过)")
        if ge_url:
            git("remote", "add", "mirror", ge_url)
            print(f"  [OK] mirror 已配置: {ge_url}")
    else:
        print(f"  [OK] mirror 已存在: {mirror_url}")

    # ---- 4. 引导配置凭据 ----
    print("\n[4/5] 检查推送凭据...")
    secrets_dir = REPO_ROOT / ".secrets"
    secrets_dir.mkdir(exist_ok=True)

    gitee_token_file = secrets_dir / "gitee_token"
    if not gitee_token_file.exists():
        print("  [WARN] Gitee token 未配置（.secrets/gitee_token）")
        print("    Gitee 设置 → 私人令牌 → 生成新令牌（勾选 projects 读写权限）")
        ge_token = prompt("  输入 Gitee token（留空跳过）")
        if ge_token:
            gitee_token_file.write_text(ge_token, encoding="utf-8")
            print("  [OK] Gitee token 已写入 .secrets/gitee_token")
    else:
        print("  [OK] Gitee token 已配置")

    gitee_user_file = secrets_dir / "gitee_user"
    if not gitee_user_file.exists():
        ge_user = prompt("  Gitee 用户名", "gogojaja")
        gitee_user_file.write_text(ge_user, encoding="utf-8")
        print(f"  [OK] Gitee 用户名已写入: {ge_user}")
    else:
        print("  [OK] Gitee 用户名已配置")

    print()
    print("  GitHub 凭据：推送工具自动从 origin 远端 URL 解析 token，")
    print("  请通过 git remote set-url origin 'https://<user>:<token>@github.com/...' 临时配置，")
    print("  或系统钥匙串/macOS Keychain 提供。")

    # ---- 5. 验证代理链路 ----
    print("\n[5/5] 验证代理链路...")
    tools_dir = REPO_ROOT / "tools"
    sys.path.insert(0, str(tools_dir))
    try:
        from _hub_proxy import find_hub_root, PROJECT_ROOT
        hub = find_hub_root()
        if hub:
            print(f"  [OK] dev-git-hub 已定位: {hub}")
            print(f"  [OK] PROJECT_ROOT: {PROJECT_ROOT}")
        else:
            print("  [WARN] dev-git-hub 未定位，推送功能不可用（本地提交不受影响）")
            print("    解决: export DEV_GIT_HUB_ROOT=/path/to/dev-git-hub")
            print("    或: echo /path/to/dev-git-hub > .hub_root")
    except Exception as e:
        print(f"  [WARN] Python 代理验证失败: {e}")

    print()
    print("=" * 42)
    print("  初始化完成")
    print("=" * 42)
    print()
    print("  后续操作：")
    print("    - 推送: python tools/mirror_push.py")
    print("    - 固化: python tools/solidify.py '说明'")
    print("    - 安装钩子: bash scripts/install-hooks.sh（已完成则跳过）")
    print()
    print("  注意：.secrets/ 已被 .gitignore 忽略，凭据不会入库")


if __name__ == "__main__":
    main()
