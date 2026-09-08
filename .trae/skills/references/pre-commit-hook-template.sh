#!/bin/sh
# Pre-commit hook: 涉密信息自动扫描（符合 iron_rules.md §3.2）
# 安装方式：cp references/pre-commit-hook-template.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# Windows: Copy-Item references/pre-commit-hook-template.sh .git/hooks/pre-commit

echo "🔒 pre-commit 涉密信息检查..."

# ============================================================
# 第一关：.gitignore 泄密文件屏蔽检查
# ============================================================
echo "[1/3] 检查 .gitignore 泄密文件屏蔽规则..."

# 检查脱敏工作目录是否被屏蔽
if git diff --cached --name-only | grep -q "脱敏工作"; then
  echo "❌ 检测到「脱敏工作」目录文件被暂存"
  echo "   请在 .gitignore 中添加：脱敏工作/"
  exit 1
fi

# 检查 .secrets 目录是否被屏蔽
if git diff --cached --name-only | grep -q "\.secrets"; then
  echo "❌ 检测到「.secrets」目录文件被暂存"
  echo "   请在 .gitignore 中添加：.secrets/"
  exit 1
fi

echo "  ✅ .gitignore 检查通过"

# ============================================================
# 第二关：gitleaks 敏感信息扫描
# ============================================================
echo "[2/3] gitleaks 扫描暂存区..."

# 查找 gitleaks 可执行文件
GITLEAKS=""
if command -v gitleaks >/dev/null 2>&1; then
  GITLEAKS="gitleaks"
elif [ -f "$LOCALAPPDATA/Microsoft/WinGet/Packages/Gitleaks.Gitleaks_Microsoft.Winget.Source_8wekyb3d8bbwe/gitleaks.exe" ]; then
  GITLEAKS="$LOCALAPPDATA/Microsoft/WinGet/Packages/Gitleaks.Gitleaks_Microsoft.Winget.Source_8wekyb3d8bbwe/gitleaks.exe"
elif [ -f "/c/Program Files/gitleaks/gitleaks.exe" ]; then
  GITLEAKS="/c/Program Files/gitleaks/gitleaks.exe"
fi

if [ -n "$GITLEAKS" ]; then
  "$GITLEAKS" protect --staged --verbose 2>&1
  if [ $? -ne 0 ]; then
    echo ""
    echo "❌ gitleaks 检测到敏感信息，提交已阻止"
    echo "   请脱敏后重新提交"
    echo "   如确认为误报，可用 git commit --no-verify 跳过（需授权）"
    exit 1
  fi
  echo "  ✅ gitleaks 扫描通过"
else
  echo "  ⚠️  gitleaks 未安装，跳过扫描"
  echo "     安装命令: winget install Gitleaks.Gitleaks"
fi

# ============================================================
# 第三关：反向映射表检测
# ============================================================
echo "[3/3] 检查反向映射表..."

# 检查暂存区是否包含映射表特征文件
MAPPING_FILES=$(git diff --cached --name-only | grep -iE "(mapping|dictionary|替换表|映射|desensitize_dictionary\.csv)$" | grep -v "\.example\." | grep -v "\.gitignore")

if [ -n "$MAPPING_FILES" ]; then
  echo "⚠️  检测到可能的映射表文件："
  echo "$MAPPING_FILES" | while read f; do echo "  - $f"; done
  echo ""
  echo "  如包含真实映射规则（原始词→替换值），禁止入库"
  echo "  请确认是否为示例文件，真实映射应存储在 .secrets/ 并加密"
  
  # 不自动阻断，但强烈警告
  echo "  ⚠️  如确认为真实映射表，请立即停止并移除"
fi

echo ""
echo "✅ pre-commit 检查全部通过"
