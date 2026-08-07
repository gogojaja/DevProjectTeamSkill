#!/usr/bin/env bash
# pre-commit 密钥扫描钩子（防误提交，R5）
# 部署: 复制到 .git/hooks/pre-commit 或执行 tools/install_secret_hooks.sh
# 依赖: rg (ripgrep) 或 grep -P; PowerShell 环境建议用 tools/secret_scan.ps1

set -u
files=$(git diff --cached --name-only --diff-filter=ACM)
if [ -z "$files" ]; then exit 0; fi

pattern='(ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY)'

for f in $files; do
  case "$f" in
    *.env|*.pem|*.key|*.p12|*.pfx|*.jks|*.keystore) continue ;;  # 已被 gitignore 排除, 防御性跳过
  esac
  if git show :"$f" 2>/dev/null | rg -P "$pattern" >/dev/null 2>&1; then
    echo "❌ 检测到疑似密钥: $f" >&2
    echo "   密钥禁止入库。请改用 .secrets/ + 凭据管理器/别名引用。" >&2
    exit 1
  fi
done
exit 0
