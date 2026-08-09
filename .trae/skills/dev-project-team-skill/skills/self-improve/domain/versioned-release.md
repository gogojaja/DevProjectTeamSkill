# 版本化發布：版本記錄 / solidify 固化 / 交接刷新

> 編排器：`../SKILL.md`

---

## 1. 版本化發布架構

### 1.1 發布流程
```mermaid
graph LR
  A[改動完成] --> B[驗證通過]
  B --> C[版本號更新]
  C --> D[solidify 固化]
  D --> E[部署四目錄]
  E --> F[交接刷新]
  F --> G[提交推送]
```

### 1.2 發布原則
- **版本一致**：元數據版本 == 頁腳版本（check_version_consistency 硬門禁）；
- **原子提交**：一次發布一個 commit，可獨立回退；
- **先固化後提交**：改動必須先 solidify（快照+打包+部署）再 git commit；
- **交接同步**：發布後必須刷新交接文檔斷點區，否則跨會話斷點失效。

---

## 2. 版本號管理

### 2.1 版本規則
| 組件 | 規則 |
|------|------|
| 主版本 major | 破壞性變更 / 結構重組 |
| 次版本 minor | 新增能力 / 新增技能包 |
| 修訂 patch | 修復 / 微調 / 文檔 |
| 語義 | v21.3.3 = 第 21 期，第 3 次新增能力，第 3 次修訂 |

### 2.2 版本更新位置（單源三處同步）
| 文件 | 位置 | 說明 |
|------|------|------|
| SKILL.md frontmatter | 無版本欄（description 不含版本） | 技能包版本在頁腳 |
| SKILL.md 頁腳 | `**文檔版本**: vX.Y.Z` | 每技能包獨立版本 |
| 編排器 SKILL.md | 技能版本 + 變更記錄 + 頁腳 | 升級主版本記錄 |
| references 各標準 | 頁腳 + 最後更新 | 標準獨立版本 |
| SKILL_INDEX.md | 頁腳版本 | 索引版本 |
| shared/references | 同步副本 | 禁止手工分叉 |

### 2.3 版本一致性校驗
```bash
python3 tools/check_version_consistency.py
# 硬門禁：元數據版本 == 頁腳版本；不通過則 solidify 中止
```

---

## 3. solidify 固化流程

### 3.1 執行命令
```bash
bash tools/solidify.sh "新增 X 能力（版本 v21.3.3）"
```

### 3.2 固化步驟（六步）
| 步驟 | 內容 | 產物 |
|------|------|------|
| 1 | 版本檢查 | 各角色包版本清單 |
| 2 | 刷新交接斷點區 | 交接文檔元數據行更新 |
| 3 | 生成快照 | skills_backup_v<版本>/ |
| 4 | 打包 dist | 9 個角色包 zip |
| 5 | 部署四目錄 | .trae/.agents/.claude + 全局庫 |
| 6 | 完成 | 提示 commit |

### 3.3 固化後驗證
```bash
git status                      # 確認改動文件清單
git diff --stat                 # 確認改動範圍
python3 tools/check_version_consistency.py  # 二次確認
```

---

## 4. 部署四目錄

### 4.1 目標目錄
| 目錄 | 平台 | 用途 |
|------|------|------|
| `.github/skills/` | 全平台 | GitHub Actions 集成 |
| `.claude/skills/` | 全平台 | Claude 集成 |
| `.agents/skills/` | 全平台 | 通用 Agent 集成 |
| `~/.config/opencode/skills` | macOS/Linux | opencode 全局 |
| `%USERPROFILE%\.config\opencode\skills` | Windows | opencode 全局 |

### 4.2 部署驗證
```bash
# 驗證目標目錄存在新技能
ls .agents/skills/dev-project-team-skill/skills/<新技能>/
# 驗證 references 副本同步
diff .trae/skills/references/<file> .trae/skills/shared/references/<file>
```

---

## 5. 交接刷新

### 5.1 交接文檔斷點區
| 欄位 | 內容 |
|------|------|
| 固化時間 | solidify 自動寫入 |
| 角色包數 | 8 + 子技能數 |
| 版本 | 最新發布版本 |
| 已完成/待辦 | 保留歷史內容（solidify 只刷新元數據行，不清空） |

### 5.2 刷新規則
- **保留**：已完成清單、待辦清單、決策記錄；
- **更新**：固化時間、版本號、狀態標記；
- **新增**：本次發布的技能/能力摘要。

---

## 6. 提交與推送

### 6.1 提交規範
```bash
git add -A
git commit -m "feat(<技能包>): <一句話摘要>"
```

### 6.2 提交類型
| 類型 | 場景 |
|------|------|
| feat | 新增技能包 / 新增能力 |
| fix | 修復缺陷 |
| chore | 打包/部署/文檔調整 |
| docs | 文檔更新 |

### 6.3 推送（雙平台網絡應對）
```bash
# macOS/Linux：SSH 直推，失敗則 HTTPS + keychain
git remote set-url origin https://github.com/gogojaja/DevProjectTeamSkill.git
HOSTALIASES=/tmp/hosts_aliases git push origin main
git remote set-url origin git@github.com:gogojaja/DevProjectTeamSkill.git  # 還原

# Windows：HTTPS + PAT token 帶憑據
git remote set-url origin "https://user:token@github.com/gogojaja/DevProjectTeamSkill.git"
git push origin main
git remote set-url origin "https://github.com/gogojaja/DevProjectTeamSkill.git"  # 還原
```

### 6.4 發布檢查清單
- [ ] 版本一致性門禁通過
- [ ] 三觸發詞回歸通過
- [ ] 打包 dist 成功
- [ ] 四目錄部署成功
- [ ] 交接斷點區刷新
- [ ] commit 完成
- [ ] push 成功（HEAD == origin/main）

---

## 7. 最佳實踐

1. **一次一版**：每次發布只升一個版本，禁止跳版本；
2. **同步副本**：shared/references 改動後立即同步，禁止延後；
3. **先本地後遠程**：先在本地全量驗證再 push；
4. **發布記錄**：SKILL_INDEX 頁腳更新「最後更新」說明本次內容；
5. **回退預案**：發布前確認 git log 可回退點，異常時 git revert。

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-09