#!/usr/bin/env bash
# =============================================================================
# solidify.sh — 育权台结成果「断点固化」一键脚本（v21.0.0）
# 依据: references/token_standard.md §2 / 方案 v21.0.1 §2.3-2.4
#
# 变更（v20 -> v21）:
#   - 交接文档改名: 跨会话交接文档.md → 交接文档.md（P2-2，禁止双源并存）
#   - 固化时强制刷新 交接文档.md 断点区；若文件缺失则用模板创建
#   - 快照改用角色包粒度；打包/部署调用 v21 脚本
#
# 用法:
#   bash tools/solidify.sh
#   bash tools/solidify.sh "描述本次改动"   # 可选，写入断点
# =============================================================================
set -euo pipefail

SKILLS_DIR="${SKILLS_DIR:-C:/Users/gogoj/.config/opencode/skills}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HANDOFF="$ROOT/交接文档.md"
STAMP="$(date '+%Y-%m-%d %H:%M:%S')"
CUSTOM_NOTE="${1:-}"

echo "=============================================="
echo " 育权台断点固化 (solidify v21)"
echo "=============================================="

# ---- 0. 交接文档改名迁移：若旧文件存在而新文件缺失，改名；禁止双源 ----
OLD_HANDOFF="$ROOT/跨会话交接文档.md"
if [[ -f "$OLD_HANDOFF" ]]; then
  if [[ -f "$HANDOFF" ]]; then
    echo "[0/6] ⚠ 交接文档.md 与 跨会话交接文档.md 并存（双源），请手动合并后删除旧文件" >&2
  else
    mv "$OLD_HANDOFF" "$HANDOFF"
    echo "[0/6] 跨会话交接文档.md → 交接文档.md 改名迁移完成"
  fi
fi

# ---- 1. 扫描当前角色包清单 ----
echo ""
echo "[1/6] 当前角色包清单与版本:"
ALL_ROLES=(
  dev-project-team-skill role-project-init role-requirements-analysis
  role-architecture role-development role-testing role-deployment role-governance
)
SKILL_COUNT=0
for r in "${ALL_ROLES[@]}"; do
  if [[ -d "$SKILLS_DIR/$r" ]]; then
    ver="$(grep -oE "技能版本\*\*[：:]\s*v[0-9]+\.[0-9]+\.[0-9]+" "$SKILLS_DIR/$r/SKILL.md" 2>/dev/null | grep -oE "v[0-9]+\.[0-9]+\.[0-9]+" | head -1 || echo "v?")"
    printf "   %-40s %s\n" "$r" "$ver"
    SKILL_COUNT=$((SKILL_COUNT+1))
  fi
done
echo "   共 ${SKILL_COUNT} 个角色包"

# ---- 2. 交接文档断点区强制刷新（缺失则模板创建） ----
echo ""
echo "[2/6] 强制刷新交接文档断点区"

# 若交接文档不存在，用模板创建
if [[ ! -f "$HANDOFF" ]]; then
  cat > "$HANDOFF" <<'EOF'
# 交接文档

## 0. 速览
（项目目标 + 当前阶段 + 下一步唯一动作）

## 1. 工作断点
（已完成 / 进行中 / 待办 / 阻塞，各 ≤5 条）

## 2. 关键文件索引
（文件路径 + 一句话用途，≤10 条）

## 3. 台账指针
（主台账 CSV 目录路径 + 最近变更号）

## 4. 约定与铁律
（本库强制规则超链接）

---

EOF
  echo "   ✓ 交接文档不存在，已用模板创建"
fi

python3 - "$HANDOFF" "$STAMP" "$SKILL_COUNT" "$CUSTOM_NOTE" <<'PYEOF'
import sys
p, stamp, n, note = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
MARK_HEAD = "## 1. 工作断点"
BLOCK = f"""## 1. 工作断点

> 本区由 `tools/solidify.sh` 每次任务完成后自动覆写。
> **新模型/新会话启动，第一步必须先读 `交接文档.md` 全文**，从本区定位上一模型已完成/待办，未读交接文档前禁止读其他项目文档。

**最近固化时间**：{stamp}
**角色包数**：{n}
**固化备注**：{note if note else '—'}

### 已完成
（无则写「无」）

### 进行中
（正在改动、未固化到磁盘的在途工作）

### 待办
（下一阶段动作）

### 阻塞
（如有风险/阻塞项）

### 台账指针
主台账 CSV 路径：待填　最近变更号：待填
"""
with open(p, encoding='utf-8') as f:
    c = f.read()
i = c.find(MARK_HEAD)
if i != -1:
    j = c.find("\n## ", i + len(MARK_HEAD))
    after = c[j:] if j != -1 else ""
    block = c[:i] + BLOCK.rstrip("\n") + "\n" + after
else:
    block = c.rstrip("\n") + "\n\n---\n\n" + BLOCK
with open(p, 'w', encoding='utf-8') as f:
    f.write(block)
PYEOF
echo "   ✅ 交接文档断点区已刷新（固化后必须反映磁盘最新状态）"

# ---- 3. 快照（角色包粒度） ----
MAIN_VER="$(grep -oE "技能版本\*\*[：:]\s*v[0-9]+\.[0-9]+\.[0-9]+" "$SKILLS_DIR/dev-project-team-skill/SKILL.md" 2>/dev/null | grep -oE "v[0-9]+\.[0-9]+\.[0-9]+" | head -1 || echo "v21.0.0")"
SNAP_DIR="$ROOT/skills_backup_${MAIN_VER}"
echo ""
echo "[3/6] 生成快照 → ${SNAP_DIR}"
if [[ -d "$SNAP_DIR" ]]; then
  echo "   ⚠ 快照 $MAIN_VER 已存在（不覆盖）。如需本次改动单独快照，请手动指定版本。"
else
  mkdir -p "$SNAP_DIR"
  for r in "${ALL_ROLES[@]}"; do
    [[ -d "$SKILLS_DIR/$r" ]] && cp -R "$SKILLS_DIR/$r" "$SNAP_DIR/$r"
  done
  [[ -d "$SKILLS_DIR/references" ]] && cp -R "$SKILLS_DIR/references" "$SNAP_DIR/references"
  [[ -f "$SKILLS_DIR/SKILL_INDEX.md" ]] && cp "$SKILLS_DIR/SKILL_INDEX.md" "$SNAP_DIR/SKILL_INDEX.md"
  echo "   ✓ ${SKILL_COUNT} 角色包 + references + SKILL_INDEX 快照已生成"
fi

# ---- 4. 打包 ----
echo ""
echo "[4/6] 打包 dist (package_skills.sh v21)"
bash "$ROOT/tools/package_skills.sh" --handoff "$HANDOFF" 2>&1 | tail -3

# ---- 5. 部署 ----
echo ""
echo "[5/6] 全量部署四目录 (deploy_skills.sh v21)"
bash "$ROOT/tools/deploy_skills.sh" 2>&1 | tail -6

echo ""
echo "=============================================================="
echo " 固化完成。请执行: git add -A && git commit -m \"<说明>\""
echo "翻转: bash tools/solidify.sh \"<下次改动说明>\""
echo "=============================================================="