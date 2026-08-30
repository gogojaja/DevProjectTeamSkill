#!/usr/bin/env bash
# ============================================================
# bootstrap_remotes.sh — 迁移初始化引导（macOS/Linux）
# 新机器 clone 本仓库后执行，完成以下初始化：
#   1. 安装 Git 钩子
#   2. 定位/引导创建 dev-git-hub（推送工具单一信源）
#   3. 配置 git remotes（origin=GitHub, mirror=Gitee）
#   4. 引导配置凭据（.secrets/）
#   5. 验证代理链路
# 用法：bash scripts/bootstrap_remotes.sh
# ============================================================

set -e

repo_root=$(cd "$(dirname "$0")/.." && pwd)
hub_root="${repo_root}/../dev-git-hub"

echo "=========================================="
echo "  DevProjectTeamSkill 迁移初始化"
echo "=========================================="

# ---- 1. 安装 Git 钩子 ----
echo ""
echo "[1/5] 安装 Git 钩子..."
if [ -f "$repo_root/scripts/install-hooks.sh" ]; then
  bash "$repo_root/scripts/install-hooks.sh"
else
  echo "  ⚠ install-hooks.sh 不存在，跳过"
fi

# ---- 2. 定位/引导创建 dev-git-hub ----
echo ""
echo "[2/5] 检查 dev-git-hub（推送工具单一信源）..."
if [ -d "$hub_root/tools" ]; then
  echo "  ✅ dev-git-hub 已存在: $hub_root"
else
  echo "  ⚠ dev-git-hub 未找到: $hub_root"
  echo "  dev-git-hub 是 GitHub/Gitee 推送工具的独立项目（单一信源）。"
  echo "  本仓库经薄封装代理调用其推送工具，不内嵌实现。"
  echo ""
  echo "  请选择初始化方式："
  echo "    a) clone dev-git-hub 到同级目录（推荐）："
  echo "       git clone <dev-git-hub 远端 URL> \"$hub_root\""
  echo "    b) 指定 dev-git-hub 在其他位置："
  echo "       echo '/path/to/dev-git-hub' > \"$repo_root/.hub_root\""
  echo "       或设置环境变量: export DEV_GIT_HUB_ROOT=/path/to/dev-git-hub"
  echo "    c) 暂时跳过（推送功能不可用，本地提交不受影响）"
  echo ""
  read -p "  是否现在初始化 dev-git-hub？(a/b/c): " choice
  case "$choice" in
    a|A)
      read -p "  dev-git-hub 远端 URL: " hub_url
      git clone "$hub_url" "$hub_root" && echo "  ✅ dev-git-hub 已 clone"
      ;;
    b|B)
      read -p "  dev-git-hub 绝对路径: " hub_path
      echo "$hub_path" > "$repo_root/.hub_root"
      echo "  ✅ 已写入 .hub_root: $hub_path"
      ;;
    c|C)
      echo "  ⏭ 跳过 dev-git-hub 初始化（推送功能不可用，本地提交不受影响）"
      ;;
    *)
      echo "  ⏭ 无效选择，跳过"
      ;;
  esac
fi

# ---- 3. 配置 git remotes ----
echo ""
echo "[3/5] 检查 git remotes..."
origin_url=$(git -C "$repo_root" remote get-url origin 2>/dev/null || echo "")
mirror_url=$(git -C "$repo_root" remote get-url mirror 2>/dev/null || echo "")

if [ -z "$origin_url" ]; then
  read -p "  GitHub 远端 URL (origin，留空跳过): " gh_url
  if [ -n "$gh_url" ]; then
    git -C "$repo_root" remote add origin "$gh_url"
    echo "  ✅ origin 已配置: $gh_url"
  fi
else
  echo "  ✅ origin 已存在: $origin_url"
fi

if [ -z "$mirror_url" ]; then
  read -p "  Gitee 远端 URL (mirror，留空跳过): " ge_url
  if [ -n "$ge_url" ]; then
    git -C "$repo_root" remote add mirror "$ge_url"
    echo "  ✅ mirror 已配置: $ge_url"
  fi
else
  echo "  ✅ mirror 已存在: $mirror_url"
fi

# ---- 4. 引导配置凭据 ----
echo ""
echo "[4/5] 检查推送凭据..."
secrets_dir="$repo_root/.secrets"
mkdir -p "$secrets_dir" 2>/dev/null || true

if [ ! -f "$secrets_dir/gitee_token" ]; then
  echo "  ⚠ Gitee token 未配置（.secrets/gitee_token）"
  echo "    Gitee 设置 → 私人令牌 → 生成新令牌（勾选 projects 读写权限）"
  read -p "  输入 Gitee token（留空跳过）: " ge_token
  if [ -n "$ge_token" ]; then
    echo -n "$ge_token" > "$secrets_dir/gitee_token"
    echo "  ✅ Gitee token 已写入 .secrets/gitee_token"
  fi
else
  echo "  ✅ Gitee token 已配置"
fi

if [ ! -f "$secrets_dir/gitee_user" ]; then
  read -p "  Gitee 用户名 (gogojaja): " ge_user
  ge_user="${ge_user:-gogojaja}"
  echo -n "$ge_user" > "$secrets_dir/gitee_user"
  echo "  ✅ Gitee 用户名已写入: $ge_user"
else
  echo "  ✅ Gitee 用户名已配置"
fi

echo ""
echo "  GitHub 凭据：推送工具自动从 origin 远端 URL 解析 token，"
echo "  请通过 git remote set-url origin 'https://<user>:<token>@github.com/...' 临时配置，"
echo "  或系统钥匙串/macOS Keychain 提供。"

# ---- 5. 验证代理链路 ----
echo ""
echo "[5/5] 验证代理链路..."
python3 -c "
import sys, os
sys.path.insert(0, os.path.join('$repo_root', 'tools'))
from _hub_proxy import find_hub_root, PROJECT_ROOT
hub = find_hub_root()
if hub:
  print('  ✅ dev-git-hub 已定位: %s' % hub)
  print('  ✅ PROJECT_ROOT: %s' % PROJECT_ROOT)
else:
  print('  ⚠ dev-git-hub 未定位，推送功能不可用（本地提交不受影响）')
  print('    解决: export DEV_GIT_HUB_ROOT=/path/to/dev-git-hub')
" 2>/dev/null || echo "  ⚠ Python 代理验证失败，请检查 Python 环境"

echo ""
echo "=========================================="
echo "  初始化完成"
echo "=========================================="
echo ""
echo "  后续操作："
echo "    - 推送: python3 tools/mirror_push.py"
echo "    - 固化: bash tools/solidify.sh '说明'"
echo "    - 安装钩子: bash scripts/install-hooks.sh（已完成则跳过）"
echo ""
echo "  注意：.secrets/ 已被 .gitignore 忽略，凭据不会入库"
