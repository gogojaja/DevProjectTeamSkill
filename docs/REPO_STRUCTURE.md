# REPO_STRUCTURE — 仓库目录树与目录职责

> 权威规则见根 `AGENTS.md`；本文件为目录结构视图与入库 / gitignored 划分说明。
> 编排器文档版本：v21.7.0。

## 顶层目录树

```
DevProjectTeamSkill/
├── .trae/
│   └── skills/                     # ★ 唯一事实来源（全部技能源码）
│       ├── SKILL_INDEX.md          # 10 包路由索引（#0 编排器 + #1~#9 角色包）
│       ├── references/             # 公共标准（token / csv / api 契约 / 环境 / 模型 / 铁律 / 咨询）
│       ├── shared/                 # 单源共享库（governance / evolution / authoring + references 副本）
│       ├── dev-project-team-skill/ # 编排器（薄壳：路由表 + 调度 / 压缩规则）
│       └── role-*/                 # 9 角色包（各含 SKILL.md + domain/ 流程 + *__resources/ 明细）
├── tools/                          # 打包 / 部署 / 固化 / 校验 / CMDB 脚本（.sh + .py 双实现）
│   └── cmdb/                       # 轻量级 CMDB CLI（注册 / 查询 / 释放 / 冲突检测，SQLite）
├── scripts/                        # 钩子安装等辅助脚本（install-hooks.sh）
├── security/                       # 安全示例与隔离配置（含 secrets-example/，可入库）
├── requirements/                   # 依赖声明
├── tests/                          # 测试
├── docs/                          # ★ 文档出口（指南 / 方案 / 台账标准）
│   ├── program-control-ledger/    # 项目群控制台账（已迁入，源 台账/ 之外出口）
│   ├── legacy/                     # 历史文档（双角色 / 精简工作流 / TRAE 启用指南）
│   ├── opencode启用指南.md         # opencode 当前推荐启用方式
│   ├── github_ip_records.csv       # GitHub 访问候选 IP 资源记录（动态刷新）
│   ├── capability-matrix-enhancement-v21.3.0.md
│   ├── data-governance-mode-v21.2.1.md
│   ├── 项目群协同.md
│   └── Token优化与CSV输出方案_v21.0.0.md
├── 台账/                           # ★ 受控台账库（入库，含 13/14/26/32/34 等 csv）
├── .trae-html-share-packages/      # 历史共享包留档（gitignored）
├── 交接文档.md                     # 跨会话断点（入库）
├── opencode.json                   # opencode 技能注册（入库）
├── AGENTS.md                       # 代理行为总规则（入库，权威）
├── README.md                       # 仓库门面（入库）
├── CHANGELOG.md                    # 版本演进史（入库）
├── CONTRIBUTING.md                 # 贡献指南（入库）
└── .gitignore / .gitattributes     # 忽略与行尾规则
```

## 各目录职责

| 路径 | 职责 | 是否入库 |
|------|------|----------|
| `.trae/skills/` | 技能源码唯一事实来源（角色包 / 标准 / 共享库） | ✅ 入库（规范副本） |
| `tools/` | 打包 / 部署 / 固化 / 校验 / CMDB 脚本（`.sh` + `.py` 双实现） | ✅ 入库 |
| `tools/cmdb/` | 多项目共享服务器资源管理（CMDB CLI，SQLite，审计日志，CSV 导出） | ✅ 入库 |
| `scripts/` | `install-hooks.sh` 等辅助脚本 | ✅ 入库 |
| `security/` | 安全示例与隔离配置；仅 `secrets-example/` 入库，真实密钥不入库 | ✅（示例）/ ❌（密钥） |
| `requirements/` | 依赖声明 | ✅ 入库 |
| `tests/` | 测试 | ✅ 入库 |
| `docs/` | 文档出口：启用指南 / 版本方案 / 控制台账（含 `program-control-ledger/`） | ✅ 入库 |
| `台账/` | 受控台账库：13_安全审计 / 14_授权登记 / 26_访问边界 / 32_镜像同步 / 34_客户登记 等 csv | ✅ 入库（受控） |
| `.trae-html-share-packages/` | 历史共享包留档 | ❌ gitignored |
| `.backup/` | 系统 / 外部文件操作前的强制备份（含时间戳） | ❌ gitignored |
| `dist/` `_build_global/` `_pkg_tmp/` | 打包 / 部署产物（可重新生成） | ❌ gitignored |
| `skills_backup_*/` `skills_legacy_*/` | 旧式手工备份目录（已被 git tag 取代） | ❌ gitignored |
| `.secrets/` `secrets/` `*.env` `*.pem` `*.key` 等 | 账号 / 密钥 / 凭据（A 级，禁止入库） | ❌ gitignored |
| `.github/skills/` `.claude/skills/` `.agents/skills/` | 部署目标（可由 deploy_skills 重新生成） | ❌ gitignored |
| `tools/cmdb/cmdb.db` | CMDB 本地运行时数据库（含本地操作留痕） | ❌ gitignored |
| `__pycache__/` `*.pyc` `.DS_Store` | 编译缓存 / 系统文件 | ❌ gitignored |
| `.agent-loop-enabled` | 自动化循环启用标记 | ❌ gitignored |

## 关键划分原则

- **唯一事实来源**：只有 `.trae/skills/` 入库为规范副本；部署目录（`.github/.claude/.agents/skills/`、全局库）可由 `tools/deploy_skills` 重新生成，不入库。
- **可重生成即忽略**：打包产物、备份、旧式备份目录、运行时数据库均 gitignored。
- **安全隔离**：密钥 / 凭据 / `.env` / `.secrets/` 一律 gitignored，真实值走凭据管理器或 `.secrets/`（不入库）。
- **受控台账入库**：`台账/` 是项目受控证据，入库；其中客户组织信息按 iron_rules §3 A/B 级脱敏（只存别名）。
- **文档出口统一**：对外文档集中于 `docs/`；`program-control-ledger` 已迁出根目录并入 `docs/program-control-ledger`。

---

**文档版本**：v21.7.0 ｜ **知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
