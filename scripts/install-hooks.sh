#!/usr/bin/env bash
# ============================================================
# install-hooks.sh — Git 钩子一键分发（DevProjectTeamSkill）
# 钩子存放于仓库 .githooks/（随 clone 分发，Git 安全限制下 git 不会自动执行未安装钩子）
# 本脚本将 core.hooksPath 指向 .githooks/ 并赋可执行位，新 clone 只需执行一次：
#   bash scripts/install-hooks.sh
# 兼容 macOS / Linux / Windows(Git Bash)。
# ============================================================

set -e

# 仓库根（脚本位于 <root>/scripts/）
repo_root=$(cd "$(dirname "$0")/.." && pwd)
hooks_dir="$repo_root/.githooks"

if [ ! -d "$hooks_dir" ]; then
  echo "❌ .githooks/ 目录不存在: $hooks_dir" >&2
  exit 1
fi

echo "安装 Git 钩子…"

# 1. 设置 core.hooksPath（相对或绝对均可，Git 解析到 .githooks/）
git config core.hooksPath ".githooks"

# 2. 赋可执行位
chmod +x "$hooks_dir"/* 2>/dev/null || true

echo "✅ 钩子已安装: $(git config --get core.hooksPath)"
echo "   验证: git config --get core.hooksPath 应输出 .githooks"

# 3. 自检：列出钩子文件
echo "   钩子清单:"
ls -1 "$hooks_dir" | sed 's/^/     - /'

echo ""
echo "提示: 钩子失败时 git 会阻止提交。跳过钩子: git commit --no-verify（仅应急，不推荐）"
