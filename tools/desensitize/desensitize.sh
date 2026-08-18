#!/usr/bin/env bash
# desensitize.sh — 文档脱敏工具 bash 封装（v1.0.0）
# 用法: bash tools/desensitize/desensitize.sh --scan <目标>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 查找 Python
PY=""
if command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
elif command -v py >/dev/null 2>&1; then
  PY="py -3"
fi

if [ -z "$PY" ]; then
  echo "❌ 未找到 Python 解释器，请先安装 Python 3.10+" >&2
  exit 1
fi

exec $PY "$SCRIPT_DIR/desensitize.py" "$@"
