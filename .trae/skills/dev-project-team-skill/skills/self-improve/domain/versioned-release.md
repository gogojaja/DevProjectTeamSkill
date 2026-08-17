# 版本化发布：版本记录 / solidify 固化 / 交接刷新

> 编排器：`../SKILL.md`

---

## 1. 版本化发布架构

### 1.1 发布流程
```mermaid
graph LR
  A[改动完成] --> B[验证通过]
  B --> C[版本号更新]
  C --> D[solidify 固化]
  D --> E[部署四目录]
  E --> F[交接刷新]
  F --> G[提交推送]
```

### 1.2 发布原则
- **版本一致**：元数据版本 == 页脚版本（check_version_consistency 硬门禁）；
- **原子提交**：一次发布一个 commit，可独立回退；
- **先固化后提交**：改动必须先 solidify（快照+打包+部署）再 git commit；
- **交接同步**：发布后必须刷新交接文档断点区，否则跨会话断点失效。

---

## 2. 版本号管理

### 2.1 版本规则
| 组件 | 规则 |
|------|------|
| 主版本 major | 破坏性变更 / 结构重组 |
| 次版本 minor | 新增能力 / 新增技能包 |
| 修订 patch | 修复 / 微调 / 文档 |
| 语义 | v21.3.3 = 第 21 期，第 3 次新增能力，第 3 次修订 |

### 2.2 版本更新位置（单源三处同步）
| 文件 | 位置 | 说明 |
|------|------|------|
| SKILL.md frontmatter | 无版本栏（description 不含版本） | 技能包版本在页脚 |
| SKILL.md 页脚 | `**文档版本**: vX.Y.Z` | 每技能包独立版本 |
| 编排器 SKILL.md | 技能版本 + 变更记录 + 页脚 | 升级主版本记录 |
| references 各标准 | 页脚 + 最后更新 | 标准独立版本 |
| SKILL_INDEX.md | 页脚版本 | 索引版本 |
| shared/references | 同步副本 | 禁止手工分叉 |

### 2.3 版本一致性校验
```bash
python3 tools/check_version_consistency.py
# 硬门禁：元数据版本 == 页脚版本；不通过则 solidify 中止
```

---

## 3. solidify 固化流程

### 3.1 执行命令
```bash
bash tools/solidify.sh "新增 X 能力（版本 v21.3.3）"
```

### 3.2 固化步骤（六步）
| 步骤 | 内容 | 产物 |
|------|------|------|
| 1 | 版本检查 | 各角色包版本清单 |
| 2 | 刷新交接断点区 | 交接文档元数据行更新 |
| 3 | 生成快照 | skills_backup_v<版本>/ |
| 4 | 打包 dist | 9 个角色包 zip |
| 5 | 部署四目录 | .trae/.agents/.claude + 全局库 |
| 6 | 完成 | 提示 commit |

### 3.3 固化后验证
```bash
git status                      # 确认改动文件清单
git diff --stat                 # 确认改动范围
python3 tools/check_version_consistency.py  # 二次确认
```

---

## 4. 部署四目录

### 4.1 目标目录
| 目录 | 平台 | 用途 |
|------|------|------|
| `.github/skills/` | 全平台 | GitHub Actions 集成 |
| `.claude/skills/` | 全平台 | Claude 集成 |
| `.agents/skills/` | 全平台 | 通用 Agent 集成 |
| `~/.config/opencode/skills` | macOS/Linux | opencode 全局 |
| `%USERPROFILE%\.config\opencode\skills` | Windows | opencode 全局 |

### 4.2 部署验证
```bash
# 验证目标目录存在新技能
ls .agents/skills/dev-project-team-skill/skills/<新技能>/
# 验证 references 副本同步
diff .trae/skills/references/<file> .trae/skills/shared/references/<file>
```

---

## 5. 交接刷新

### 5.1 交接文档断点区
| 栏位 | 内容 |
|------|------|
| 固化时间 | solidify 自动写入 |
| 角色包数 | 8 + 子技能数 |
| 版本 | 最新发布版本 |
| 已完成/待办 | 保留历史内容（solidify 只刷新元数据行，不清空） |

### 5.2 刷新规则
- **保留**：已完成清单、待办清单、决策记录；
- **更新**：固化时间、版本号、状态标记；
- **新增**：本次发布的技能/能力摘要。

---

## 6. 提交与推送

### 6.1 提交规范
```bash
git add -A
git commit -m "feat(<技能包>): <一句话摘要>"
```

### 6.2 提交类型
| 类型 | 场景 |
|------|------|
| feat | 新增技能包 / 新增能力 |
| fix | 修复缺陷 |
| chore | 打包/部署/文档调整 |
| docs | 文档更新 |

### 6.3 推送（双平台网络应对）
```bash
# macOS/Linux：SSH 直推，失败则 HTTPS + keychain
git remote set-url origin https://github.com/gogojaja/DevProjectTeamSkill.git
HOSTALIASES=/tmp/hosts_aliases git push origin main
git remote set-url origin git@github.com:gogojaja/DevProjectTeamSkill.git  # 还原

# Windows：HTTPS + PAT token 带凭据
git remote set-url origin "https://user:token@github.com/gogojaja/DevProjectTeamSkill.git"
git push origin main
git remote set-url origin "https://github.com/gogojaja/DevProjectTeamSkill.git"  # 还原
```

### 6.4 发布检查清单
- [ ] 版本一致性门禁通过
- [ ] 三触发词回归通过
- [ ] 打包 dist 成功
- [ ] 四目录部署成功
- [ ] 交接断点区刷新
- [ ] commit 完成
- [ ] push 成功（HEAD == origin/main）

---

## 7. 最佳实践

1. **一次一版**：每次发布只升一个版本，禁止跳版本；
2. **同步副本**：shared/references 改动后立即同步，禁止延后；
3. **先本地后远程**：先在本地全量验证再 push；
4. **发布记录**：SKILL_INDEX 页脚更新「最后更新」说明本次内容；
5. **回退预案**：发布前确认 git log 可回退点，异常时 git revert。

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-09