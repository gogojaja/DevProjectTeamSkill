#!/usr/bin/env bash
# =============================================================================
# deploy_skills.sh — 角色包按需部署脚本（v21.0.0）
# 依据: references/token_standard.md §1.3 / 方案 v21.0.1 §2.3
#
# 变更（v20 -> v21）:
#   - 新增 --roles <role-a,role-b,...> 按需部署指定角色包（注入型工具防全量注入）
#   - 不带 --roles 默认全量部署 10 个角色包
#   - 部署时同步 SKILL_INDEX.md + references/
#   - 注入型工具（TRAE 等递归读目录）推荐 --roles 只放需要的包
#
# 用法:
#   bash tools/deploy_skills.sh --target .agents/skills --roles role-testing
#   bash tools/deploy_skills.sh                         # 全量到默认目标（.github/.claude/.agents + 全局库）
# 说明: 源库固定为 .trae/skills（唯一事实来源），永不写入 .trae/skills。
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${SKILLS_DIR:-$ROOT/.trae/skills}"
# 全局 opencode 技能库：平台自适应（macOS/Linux -> ~/.config/opencode/skills；Windows -> %USERPROFILE%/.config/...）
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    GLOBAL_SKILLS="${USERPROFILE:-$HOME/.config}/.config/opencode/skills" ;;
  *)
    GLOBAL_SKILLS="${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills" ;;
esac

DEFAULT_TARGETS=(
  "$ROOT/.github/skills"
  "$ROOT/.claude/skills"
  "$ROOT/.agents/skills"
  "$GLOBAL_SKILLS"
)

usage() {
  echo "用法: $0 [--target <dir>]... [--roles <role,role,...>]" >&2
  echo "  --target  部署目标目录（可多次），缺省为 4 个默认目录" >&2
  echo "  --roles   只部署指定角色包（逗号分隔），缺省全量 10 包" >&2
  echo "  示例: bash $0 --target .trae/skills --roles role-testing,role-deployment" >&2
  exit 1
}

TARGETS=()
ROLES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      [[ $# -ge 2 ]] || usage
      TARGETS+=("$2"); shift 2 ;;
    --roles)
      [[ $# -ge 2 ]] || usage
      IFS=',' read -ra R <<< "$2"
      ROLES+=("${R[@]}"); shift 2 ;;
    -h|--help) usage ;;
    *) echo "未知参数: $1" >&2; usage ;;
  esac
done
[[ ${#TARGETS[@]} -eq 0 ]] && TARGETS=("${DEFAULT_TARGETS[@]}")

[[ -d "$SKILLS_DIR" ]] || { echo "错误: 技能库目录不存在: $SKILLS_DIR" >&2; exit 1; }

ALL_ROLES=(
  dev-project-team-skill
  role-project-init
  role-requirements-analysis
  role-architecture
  role-development
  role-testing
  role-deployment
  role-governance
  role-program-mgmt
  role-mgmt-consulting
)

if [[ ${#ROLES[@]} -eq 0 ]]; then
  ROLES=("${ALL_ROLES[@]}")
fi

# frontmatter name 与目录名一致性校验（只校验待部署角色）
check_names() {
  local fail=0 name
  for r in "${ROLES[@]}"; do
    [[ -f "$SKILLS_DIR/$r/SKILL.md" ]] || { echo "  ✗ $r 缺少 SKILL.md" >&2; fail=1; continue; }
    name="$(sed -n 's/^name: *"\(.*\)"$/\1/p; s/^name: *\(.*\)$/\1/p' "$SKILLS_DIR/$r/SKILL.md" | head -1 | tr -d '[:space:]')"
    if [[ "$name" != "$r" ]]; then
      echo "  ✗ $r frontmatter name($name) 与目录名不一致" >&2; fail=1
    fi
  done
  [[ $fail -eq 0 ]] || { echo "frontmatter 校验未通过，中止部署" >&2; exit 1; }
  echo "  ✓ frontmatter name 校验通过"
}

deploy_target() {
  local target="$1"
  echo "部署 → $target (${ROLES[*]})"
  rm -rf "$target"
  mkdir -p "$target"

  local r
  for r in "${ROLES[@]}"; do
    if [[ -d "$SKILLS_DIR/$r" ]]; then
      mkdir -p "$target/$r"
      # 复制包内全部内容（含 domain/ shared/ references/）
      while IFS= read -r f; do
        rel="${f#"$SKILLS_DIR/$r"/}"
        mkdir -p "$target/$r/$(dirname "$rel")"
        cp "$f" "$target/$r/$rel"
      done < <(find "$SKILLS_DIR/$r" -type f ! -name "*.pyc" 2>/dev/null)
    else
      echo "  ✗ 技能库无角色包 $r" >&2
    fi
  done

  # 同步 references/
  if [[ -d "$SKILLS_DIR/references" ]]; then
    mkdir -p "$target/references"
    while IFS= read -r f; do
      base="$(basename "$f")"
      cp "$f" "$target/references/$base"
    done < <(find "$SKILLS_DIR/references" -type f 2>/dev/null)
  fi

  # 同步 shared/ 单源（角色包 ../shared/ 引用目标解析依赖此目录）
  if [[ -d "$SKILLS_DIR/shared" ]]; then
    mkdir -p "$target/shared"
    while IFS= read -r f; do
      base="$(basename "$f")"
      cp "$f" "$target/shared/$base"
    done < <(find "$SKILLS_DIR/shared" -type f 2>/dev/null)
    if [[ -d "$SKILLS_DIR/shared/references" ]]; then
      mkdir -p "$target/shared/references"
      while IFS= read -r f; do
        base="$(basename "$f")"
        cp "$f" "$target/shared/references/$base"
      done < <(find "$SKILLS_DIR/shared/references" -type f 2>/dev/null)
    fi
  fi

  # 同步 SKILL_INDEX.md
  if [[ -f "$SKILLS_DIR/SKILL_INDEX.md" ]]; then
    cp "$SKILLS_DIR/SKILL_INDEX.md" "$target/SKILL_INDEX.md"
  fi

  # 部署校验
  local ok=1
  for r in "${ROLES[@]}"; do
    [[ -f "$target/$r/SKILL.md" ]] || { echo "  ✗ 缺失: $target/$r/SKILL.md" >&2; ok=0; }
  done
  [[ $ok -eq 1 ]] && echo "  ✓ 部署完成（${#ROLES[@]} 包 + references + SKILL_INDEX.md）" || { echo "  ✗ 部署校验失败" >&2; exit 1; }
}

echo "技能库部署 (v21, --roles 按需部署)"
echo "源库: $SKILLS_DIR"
echo "待部署角色包: ${ROLES[*]}"
check_names
for t in "${TARGETS[@]}"; do
  deploy_target "$t"
done
echo "全部完成。注入型工具请只放入本次任务所需角色包。"