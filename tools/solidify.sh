#!/usr/bin/env bash
# =============================================================================
# solidify.sh — 育权台结成果「断点固化」一键脚本（v21.7.2）
# 依据: references/token_standard.md §2 / 方案 v21.0.1 §2.3-2.4
#
# 变更:
#   v21.7.2: 修 Windows/Git Bash 三项缺陷：
#            ① 技能版本解析改走 Python——LANG 为空(C locale)时 grep 按字节处理多字节字符，
#              字符类 [：:] 中全角冒号(3字节 EF BC 9A)被拆散致组合正则必然失配，
#              MAIN_VER 静默兜底 v21.0.0 而污染快照目录名；现改为解析失败即中止，不再兜底。
#            ② zip 缺失时回退 package_skills.py（Git for Windows 不带 zip.exe，
#              原致 [4/6] 中止并经 set -e + pipefail 连带跳过 [5/6] 部署）。
#            ③ 9 处 python3 硬编码统一为探测所得 $PY（兼容仅有 python 的环境）。
#   v21.7.1: 新增第 4 硬门禁「废弃清理门禁」（ADR 废弃后强制移除资产，见 check_deprecation_cleanup.py）
#   v21.7.0: 新增 3 个硬门禁（版本一致性/闭环执行/发布级），与 solidify.py 功能对齐
#   v21.0.0: 交接文档改名 + 断点区刷新 + 角色包粒度快照 + v21 打包部署
#   v20: 初代版本
#
# 用法:
#   bash tools/solidify.sh
#   bash tools/solidify.sh "描述本次改动"   # 可选，写入断点
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${SKILLS_DIR:-$ROOT/.trae/skills}"
HANDOFF="$ROOT/交接文档.md"
STAMP="$(date '+%Y-%m-%d %H:%M:%S')"
CUSTOM_NOTE="${1:-}"

# ---- Python 解释器探测（Git for Windows 常只有 python，无 python3）----
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "✗ 未找到 python3/python：无法解析技能版本、执行门禁与打包" >&2; exit 1
fi

# 读取 SKILL.md 的「技能版本」字段；失败输出空串，由调用方处置。
# 不用 bash grep：纯中文字面量可匹配（字节序列整体比对），但含多字节字符的字符类
# [：:] 在 C locale 下被拆成独立字节、只能匹配 1 字节，故组合正则全部失配。
# 正则内中文以 \uXXXX 转义书写，避免依赖命令行参数的编码环境。
read_skill_version() {
  "$PY" -c 'import re, sys
try:
    t = open(sys.argv[1], encoding="utf-8").read()
except OSError:
    print(""); sys.exit(0)
m = re.search("\u6280\u80fd\u7248\u672c\\*\\*[\uff1a:]\\s*(v[0-9]+\\.[0-9]+\\.[0-9]+)", t)
print(m.group(1) if m else "")' "$1"
}

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
  role-program-mgmt role-mgmt-consulting role-project-mgmt
  role-operations role-security
)
SKILL_COUNT=0
for r in "${ALL_ROLES[@]}"; do
  if [[ -d "$SKILLS_DIR/$r" ]]; then
    ver="$(read_skill_version "$SKILLS_DIR/$r/SKILL.md")"
    [[ -z "$ver" ]] && ver="v?"
    printf "   %-40s %s\n" "$r" "$ver"
    SKILL_COUNT=$((SKILL_COUNT+1))
  fi
done
echo "   共 ${SKILL_COUNT} 个角色包"

# ---- 1a. 硬门禁：版本一致性校验 ----
echo ""
echo "[1a/6] 版本一致性校验（硬门禁）"
if "$PY" "$ROOT/tools/check_version_consistency.py" 2>&1; then
  echo "   ✓ 版本一致性校验通过"
else
  echo "   ✗ 版本一致性校验未通过，中止固化。请先统一各包元数据/页脚版本。" >&2
  exit 1
fi

# ---- 1b. 硬门禁：闭环执行系统校验 ----
echo ""
echo "[1b/6] 闭环执行门禁校验（硬门禁）"
if "$PY" "$ROOT/tools/check_skill_closure.py" 2>&1; then
  echo "   ✓ 闭环执行门禁通过"
else
  echo "   ✗ 闭环执行门禁未通过，中止固化。请先补齐「闭环执行系统」章节与关键门禁项。" >&2
  exit 1
fi

# ---- 1c. 硬门禁：发布级门禁校验 ----
echo ""
echo "[1c/6] 发布级门禁校验（硬门禁）"
if "$PY" "$ROOT/tools/check_skill_release_gate.py" 2>&1; then
  echo "   ✓ 发布级门禁通过"
else
  echo "   ✗ 发布级门禁未通过，中止固化。请先补齐 frontmatter、metadata 与闭环执行结构。" >&2
  exit 1
fi

# ---- 1d. 硬门禁：废弃清理门禁校验 ----
echo ""
echo "[1d/6] 废弃清理门禁校验（硬门禁）"
if "$PY" "$ROOT/tools/check_deprecation_cleanup.py" 2>&1; then
  echo "   ✓ 废弃清理门禁通过"
else
  echo "   ✗ 废弃清理门禁未通过，中止固化。请先彻底移除废弃资产残留（引用/端口/进程/LaunchAgent）。" >&2
  exit 1
fi

# ---- 1e. 生成 L1 交接核心摘要（token_standard §7 / handoff-struct） ----
echo ""
echo "[1e/6] 生成 L1 交接核心摘要 (handoff_summarizer.py)"
if "$PY" "$ROOT/tools/handoff_summarizer.py" --fallback-only 2>&1; then
  echo "   ✓ L1 核心摘要已生成/更新"
else
  echo "   ⚠ L1 摘要生成失败（fallback 规则摘要已尝试），继续固化..." >&2
fi

# ---- 1f. 硬门禁：评审产物落盘校验（评审报告CSV/证据卡入库/评审模式申明/无 /tmp 挂链） ----
echo ""
echo "[1f/6] 评审产物落盘校验（硬门禁）"
if "$PY" "$ROOT/tools/check_review_artifacts.py" 2>&1; then
  echo "   ✓ 评审产物门禁通过"
else
  echo "   ✗ 评审产物门禁未通过，中止固化。请先补齐评审报告 CSV（docs/reviews/）、证据卡入库（docs/evidence_cards_*.json，禁 /tmp）与评审模式申明。" >&2
  exit 1
fi

# ---- 1g. 复盘闭环检查（未关闭行动项提示） ----
echo ""
echo "[1g/6] 复盘闭环检查（未关闭行动项提示）"
if "$PY" "$ROOT/tools/check_retro_closure.py" 2>&1; then
  echo "   ✓ 复盘行动项闭环检查通过"
else
  echo "   ⚠ 存在未关闭复盘行动项，建议处理后固化（非阻断）"
fi

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

"$PY" - "$HANDOFF" "$STAMP" "$SKILL_COUNT" "$CUSTOM_NOTE" <<'PYEOF'
import sys, re
p, stamp, n, note = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(p, encoding='utf-8') as f:
    c = f.read()
# 只刷新元数据行（固化时间/角色包数/固化备注），保留既有的已完成/进行中/待办/阻塞内容
updated = re.sub(r'(\*\*最近固化时间\*\*：).*', lambda m: m.group(1) + stamp, c)
updated = re.sub(r'(\*\*角色包数\*\*：).*', lambda m: m.group(1) + str(n), updated)
updated = re.sub(r'(\*\*固化备注\*\*：).*', lambda m: m.group(1) + (note if note else '—'), updated)
if updated == c:
    # 元数据行缺失时按模板追加完整断点区
    BLOCK = f"""
## 1. 工作断点

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
    updated = c.rstrip('\n') + BLOCK
with open(p, 'w', encoding='utf-8') as f:
    f.write(updated)
PYEOF
echo "   ✅ 交接文档断点区已刷新（固化后必须反映磁盘最新状态）"

# ---- 3. 快照（角色包粒度） ----
MAIN_VER="$(read_skill_version "$SKILLS_DIR/dev-project-team-skill/SKILL.md")"
if [[ -z "$MAIN_VER" ]]; then
  echo "   ✗ 无法解析主编排器技能版本：$SKILLS_DIR/dev-project-team-skill/SKILL.md" >&2
  echo "     拒绝兜底为固定版本号——静默的错误版本名会污染快照目录（v21.7.2 前的历史缺陷）。" >&2
  exit 1
fi
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
  # 配套工具与文档（SKILL_INDEX/SKILL.md 引用 tools/* 与 docs/*）
  for extra in tools docs; do
    [[ -d "$ROOT/$extra" ]] && cp -R "$ROOT/$extra" "$SNAP_DIR/$extra"
  done
  [[ -f "$SKILLS_DIR/SKILL_INDEX.md" ]] && cp "$SKILLS_DIR/SKILL_INDEX.md" "$SNAP_DIR/SKILL_INDEX.md"
  echo "   ✓ ${SKILL_COUNT} 角色包 + references + SKILL_INDEX 快照已生成"

# ---- 3a. 生成 MCP 版本清单（publish_production --dry-run）----
echo ""
echo "[3a/6] 生成 MCP 版本清单 → ${SNAP_DIR}/mcp_version_manifest.json"
if "$PY" "$ROOT/tools/publish_production.py" --dry-run 2>/dev/null; then
  # publish_production.py --dry-run 会在 tools/mcp_server/ 生成 manifest.json + VERSION
  MCP_MANIFEST="${ROOT}/tools/mcp_server/manifest.json"
  if [[ -f "$MCP_MANIFEST" ]]; then
    cp "$MCP_MANIFEST" "$SNAP_DIR/mcp_version_manifest.json"
    echo "   ✓ MCP 版本清单已写入快照目录"
  else
    echo "   ⚠ MCP 版本清单未生成（publish_production.py --dry-run 未输出），跳过"
  fi
else
  echo "   ⚠ publish_production.py --dry-run 执行失败，跳过 MCP 清单生成"
fi
fi

# ---- 4. 打包 ----
echo ""
if command -v zip >/dev/null 2>&1; then
  echo "[4/6] 打包 dist (package_skills.sh v21)"
  bash "$ROOT/tools/package_skills.sh" --handoff "$HANDOFF" 2>&1 | tail -3
else
  # Git for Windows 不带 zip.exe：package_skills.sh 会在打包步骤 command not found，
  # 再经 set -e + pipefail 连带跳过 [5/6] 部署。回退功能等价的 Python port（zipfile 模块）。
  # 注意 package_skills.py 不接受 --handoff（未知参数即 exit 1），其内部自行写入 00_交接文档.md。
  echo "[4/6] 打包 dist (未检测到 zip，回退 package_skills.py)"
  "$PY" "$ROOT/tools/package_skills.py" 2>&1 | tail -3
fi

# ---- 5. 部署 ----
echo ""
echo "[5/6] 部署项目级三目录 (deploy_skills.sh --skip-global；全局库由 publish_production 独占)"
bash "$ROOT/tools/deploy_skills.sh" --skip-global 2>&1 | tail -6

echo ""
echo "=============================================================="
echo " 固化完成。请执行: git add -A && git commit -m \"<说明>\""
echo "翻转: bash tools/solidify.sh \"<下次改动说明>\""
echo "=============================================================="