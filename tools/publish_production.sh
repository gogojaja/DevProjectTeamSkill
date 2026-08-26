#!/usr/bin/env bash
# =============================================================================
# publish_production.sh — 生产技能发布脚本（v1.0.0）
# -----------------------------------------------------------------------------
# 职责: 将最新版本技能发布到生产消费载体（全局 opencode 技能库），并在
#       ~/dev-project-team-skill/ 下建立不可变版本目录 + current 软链留档。
#
# 设计依据:
#   - references/environment_topology.md v21.7.0 双套环境拓扑
#   - Twelve-Factor Build/Release/Run 分离 + immutable artifact
#   - opencode Agent Skills 官方文档: 生产消费载体 = ~/.config/opencode/skills
#
# 门禁: 版本一致性 + 闭环执行 + 发布级 + 废弃清理 + 脱敏扫描
# 用法:
#   bash tools/publish_production.sh                    # 发布当前 sources 版本
#   bash tools/publish_production.sh --version v21.8.0  # 显式版本
#   bash tools/publish_production.sh --dry-run          # 仅探测
# 跨平台: macOS/Linux 用本脚本；Windows 用 publish_production.py（py -3.11）
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${SKILLS_DIR:-$ROOT/.trae/skills}"

# ---- 路径 ----
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    HOME_DIR="${USERPROFILE:-$HOME}"
    ;;
  *)
    HOME_DIR="$HOME"
    ;;
esac
GLOBAL_SKILLS="${XDG_CONFIG_HOME:-$HOME_DIR/.config}/opencode/skills"
TARGET_ROOT="${TARGET_ROOT:-$HOME_DIR/dev-project-team-skill}"

ALL_ROLES=(dev-project-team-skill role-project-init role-requirements-analysis
           role-architecture role-development role-testing role-deployment
           role-governance role-program-mgmt role-mgmt-consulting role-project-mgmt)

VERSION=""
DRY_RUN=0

usage() {
  echo "用法: $0 [--version <vX.Y.Z>] [--target-root <dir>] [--dry-run]"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    --target-root) TARGET_ROOT="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  VERSION="$(grep -m1 -oE 'v[0-9]+\.[0-9]+\.[0-9]+' "$SKILLS_DIR/dev-project-team-skill/SKILL.md" | head -1)"
  VERSION="${VERSION#v}"   # 去掉 v 前缀，目录统一为 v<VERSION>
fi
if [[ -z "$VERSION" ]]; then
  echo "✗ 未在 SKILL.md 发现版本号"; exit 1
fi

echo "=============================================================="
echo " 生产技能发布 (publish_production v1.0.0)  目标版本: $VERSION"
echo "=============================================================="
echo "源库: $SKILLS_DIR"
echo "留档根: $TARGET_ROOT"
echo "生产消费载体: $GLOBAL_SKILLS"

run_gate() {
  local name="$1" script="$2"
  if [[ ! -f "$script" ]]; then
    echo "  ~ 门禁脚本不存在，跳过: $script"; return 0
  fi
  echo "  [门禁] $name ..."
  if ! python3 "$script" ; then
    echo "  ✗ 门禁失败: $name"; return 1
  fi
  return 0
}

# 1. 门禁
run_gate "版本一致性" "$ROOT/tools/check_version_consistency.py" || exit 1
run_gate "闭环执行"   "$ROOT/tools/check_skill_closure.py"       || exit 1
run_gate "发布级"     "$ROOT/tools/check_skill_release_gate.py"  || exit 1
run_gate "废弃清理"   "$ROOT/tools/check_deprecation_cleanup.py" || exit 1

# 2. 脱敏扫描
if ! python3 "$ROOT/tools/publish_production.py" --gate-desensitize; then
  echo "  ✗ 脱敏门禁未通过，发布中止。"; exit 1
fi

# 3. 版本目录（不可变留档）
VER_DIR="$TARGET_ROOT/v${VERSION}"
echo "  构建版本目录: $VER_DIR ..."
if [[ -d "$VER_DIR" ]]; then
  echo "  ~ 该版本目录已存在，跳过重建（保留不可变留档）"
else
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  (dry-run) 将创建 $VER_DIR"
  else
    mkdir -p "$VER_DIR"
    for r in "${ALL_ROLES[@]}"; do
      [[ -d "$SKILLS_DIR/$r" ]] && cp -R "$SKILLS_DIR/$r" "$VER_DIR/"
    done
    for sub in references shared; do
      [[ -d "$SKILLS_DIR/$sub" ]] && cp -R "$SKILLS_DIR/$sub" "$VER_DIR/"
    done
    for extra in tools docs; do
      [[ -d "$ROOT/$extra" ]] && cp -R "$ROOT/$extra" "$VER_DIR/"
    done
    [[ -f "$SKILLS_DIR/SKILL_INDEX.md" ]] && cp "$SKILLS_DIR/SKILL_INDEX.md" "$VER_DIR/"
    echo "  ✓ 版本目录已构建"
  fi
fi

# 4. current 软链（原子切换）
CURRENT="$TARGET_ROOT/current"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  (dry-run) 将设置 current -> v$VERSION"
else
  # macOS `mv -f` 覆盖符号链接会跟随目标而非替换链接，改用 ln -sfn 原子替换
  ln -sfn "v$VERSION" "$CURRENT"
  echo "  ✓ current -> $(readlink "$CURRENT")"
fi

# 5. 发布到全局库（生产消费载体）
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  (dry-run) 将部署到全局库 $GLOBAL_SKILLS"
else
  rm -rf "$GLOBAL_SKILLS"
  mkdir -p "$GLOBAL_SKILLS"
  for r in "${ALL_ROLES[@]}"; do
    [[ -d "$SKILLS_DIR/$r" ]] && cp -R "$SKILLS_DIR/$r" "$GLOBAL_SKILLS/"
  done
  for sub in references shared; do
    [[ -d "$SKILLS_DIR/$sub" ]] && cp -R "$SKILLS_DIR/$sub" "$GLOBAL_SKILLS/"
  done
  for extra in tools docs; do
    [[ -d "$ROOT/$extra" ]] && cp -R "$ROOT/$extra" "$GLOBAL_SKILLS/"
  done
  [[ -f "$SKILLS_DIR/SKILL_INDEX.md" ]] && cp "$SKILLS_DIR/SKILL_INDEX.md" "$GLOBAL_SKILLS/"
  echo "  ✓ 已发布到全局库 $GLOBAL_SKILLS"
fi

echo "  发布完成。"