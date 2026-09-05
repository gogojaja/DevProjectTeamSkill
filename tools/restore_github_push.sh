#!/usr/bin/env bash
# [薄封装代理] 本文件仅转发到 dev-git-hub（AUTH-014 独立项目）对应脚本，不保留实现内容。
# 路径经三级动态解析（对齐 tools/_hub_proxy.py，2026-09-05 整改 R-4 去除硬编码卷路径）：
#   1. 环境变量 DEV_GIT_HUB_ROOT
#   2. 同级目录约定：<本仓库>/../dev-git-hub
#   3. 配置文件 <本仓库>/.hub_root（内容为 dev-git-hub 绝对路径）
# PROJECT_ROOT 动态推导为本仓库根目录（本脚本所在 tools/ 的上级）。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

HUB_ROOT=""
if [ -n "${DEV_GIT_HUB_ROOT:-}" ] && [ -d "$DEV_GIT_HUB_ROOT/tools" ]; then
  HUB_ROOT="$DEV_GIT_HUB_ROOT"
elif [ -d "$REPO_ROOT/../dev-git-hub/tools" ]; then
  HUB_ROOT="$(cd "$REPO_ROOT/../dev-git-hub" && pwd)"
elif [ -f "$REPO_ROOT/.hub_root" ]; then
  CANDIDATE="$(head -n1 "$REPO_ROOT/.hub_root" | tr -d '[:space:]')"
  if [ -n "$CANDIDATE" ] && [ -d "$CANDIDATE/tools" ]; then
    HUB_ROOT="$CANDIDATE"
  fi
fi

HUB_SCRIPT="$HUB_ROOT/tools/restore_github_push.sh"
if [ -z "$HUB_ROOT" ] || [ ! -f "$HUB_SCRIPT" ]; then
  echo "[error] dev-git-hub 工具缺失: tools/restore_github_push.sh" >&2
  echo "        请设置环境变量 DEV_GIT_HUB_ROOT 指向 dev-git-hub 根目录，" >&2
  echo "        或在仓库根创建 .hub_root 文件（内容为 dev-git-hub 绝对路径）" >&2
  exit 1
fi

export PROJECT_ROOT="$REPO_ROOT"
exec bash "$HUB_SCRIPT" "$@"
