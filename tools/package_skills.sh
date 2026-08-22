#!/usr/bin/env bash
# =============================================================================
# package_skills.sh — 角色包粒度打包发布脚本（v21.0.0）
# 依据: references/token_standard.md §1 / 方案 v21.0.1 §1.2 / §2.3
#
# 变更（v20 -> v21）:
#   - 按「角色包」粒度打包（8 个包），不再 39 个技能各打一包
#   - 源码单源: 包内 SKILL.md 经 ../shared/ 相对引用共享能力；打包时自动内嵌
#     shared/ 副本 + references 副本，输出包自包含可独立解压使用
#   - 包内第一项 = 00_交接文档.md（技能库打包取技能库根交接文档）
#   - 子技能统一为 .md（不再 .md 化规避注入，P0-1）
#
# 用法:
#   bash tools/package_skills.sh                # 打包全部 10 个角色包
#   bash tools/package_skills.sh --role role-testing   # 只打包指定角色包
#   bash tools/package_skills.sh --handoff 交接文档.md  # 指定交接文档来源
# =============================================================================
set -euo pipefail

# ---- 路径 ----
# SKILLS_DIR 可用环境变量覆盖（默认为仓库源码 .trae/skills，唯一事实来源）
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${SKILLS_DIR:-$ROOT/.trae/skills}"
DIST="$ROOT/dist"
HANDOFF="$ROOT/交接文档.md"

# ---- 参数解析 ----
ROLES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role) [[ $# -ge 2 ]] || { echo "--role 需要参数" >&2; exit 1; }; ROLES+=("$2"); shift 2 ;;
    --handoff) [[ $# -ge 2 ]] || { echo "--handoff 需要参数" >&2; exit 1; }; HANDOFF="$2"; shift 2 ;;
    -h|--help) echo "用法: $0 [--role <role-name>]... [--handoff <file>]"; exit 0 ;;
    *) echo "未知参数: $1" >&2; exit 1 ;;
  esac
done

# 全部角色包（8 个）
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

# 待处理角色
if [[ ${#ROLES[@]} -eq 0 ]]; then
  ROLES=("${ALL_ROLES[@]}")
fi

mkdir -p "$DIST"

[[ -d "$SKILLS_DIR" ]] || { echo "错误: 技能库目录不存在: $SKILLS_DIR" >&2; exit 1; }

get_version() {
  local file="$1"
  grep -oE "技能版本\*\*[：:]\s*v[0-9]+\.[0-9]+\.[0-9]+" "$file" | grep -oE "v[0-9]+\.[0-9]+\.[0-9]+" | head -1 || echo "v21.0.0"
}

pack_role() {
  local role="$1"
  local src="$SKILLS_DIR/$role"
  local ver
  ver="$(get_version "$src/SKILL.md")"

  [[ -f "$src/SKILL.md" ]] || { echo "  ✗ $role 缺少 SKILL.md，跳过" >&2; return 1; }

  local tmp out
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/$role"

  # 交接文档置包内第一项
  if [[ -f "$HANDOFF" ]]; then
    cp "$HANDOFF" "$tmp/00_交接文档.md"
  else
    echo "  ⚠ 未找到交接文档 $HANDOFF，包内不置 00_交接文档.md" >&2
  fi

  # 复制 SKILL.md + 包内非共享内容（domain/ 等，排除 shared/ 由下方内嵌）
  cp "$src/SKILL.md" "$tmp/$role/"
  if [[ -d "$src/domain" ]]; then
    mkdir -p "$tmp/$role/domain"
    while IFS= read -r f; do
      rel="${f#"$src"/}"
      mkdir -p "$tmp/$role/$(dirname "$rel")"
      cp "$f" "$tmp/$role/$rel"
    done < <(find "$src/domain" -type f ! -name "*.pyc" 2>/dev/null)
  fi

  # 源码单源内嵌 shared/: SKILL.md/domain 引用 ../shared/... 的文件都复制进来
  if [[ -d "$src/shared" ]]; then
    mkdir -p "$tmp/$role/shared"
    while IFS= read -r f; do
      rel="${f#"$src"/}"
      mkdir -p "$tmp/$role/$(dirname "$rel")"
      cp "$f" "$tmp/$role/$rel"
    done < <(find "$src/shared" -type f 2>/dev/null)
  fi
  # 若引用上级库 shared/（../shared/ 指向 SKILLS_DIR/shared），也内嵌
  if [[ -d "$SKILLS_DIR/shared" ]]; then
    mkdir -p "$tmp/$role/shared"
    while IFS= read -r f; do
      base="$(basename "$f")"
      cp "$f" "$tmp/$role/shared/$base"
    done < <(find "$SKILLS_DIR/shared" -type f 2>/dev/null)
  fi

  # 内嵌 references 副本（引用 references/ 的）
  if [[ -d "$SKILLS_DIR/references" ]]; then
    mkdir -p "$tmp/$role/references"
    while IFS= read -r f; do
      base="$(basename "$f")"
      cp "$f" "$tmp/$role/references/$base"
    done < <(find "$SKILLS_DIR/references" -type f 2>/dev/null)
  fi

  out="$DIST/${role}_${ver}.zip"
  (cd "$tmp" && zip -qr "$out" .)
  rm -rf "$tmp"

  local n_files
  n_files="$(unzip -l "$out" | tail -1 | awk '{print $2}' 2>/dev/null || echo "?")"
  echo "  ✓ $out (${n_files} files, 首项含 00_交接文档.md)"
}

echo "角色包打包发布 (v21)"
echo "技能库源: $SKILLS_DIR"
for r in "${ROLES[@]}"; do
  pack_role "$r"
done
echo "完成: $(ls "$DIST"/*.zip 2>/dev/null | wc -l | tr -d ' ') 个包已生成至 dist/"