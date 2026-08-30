#!/usr/bin/env bash
# [M1 git 剥离薄封装代理] 转发到 dev-git-hub（AUTH-014）对应脚本，保持参数兼容。
HUB_SCRIPT="/Volumes/BR256G/dev-git-hub/tools/restore_github_push.sh"
if [ ! -f "$HUB_SCRIPT" ]; then
  echo "[error] dev-git-hub 工具缺失: $HUB_SCRIPT（请先初始化 dev-git-hub 项目）" >&2
  exit 1
fi
export PROJECT_ROOT="/Volumes/BR256G/DevProjectTeamSkill"
exec bash "$HUB_SCRIPT" "$@"
