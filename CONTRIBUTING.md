# CONTRIBUTING — DevProjectTeamSkill 贡献指南

> 本仓库是**技能库本体**，贡献即「维护技能库本身」（编写 / 结构 / 打包 / 部署），不是执行软件项目业务。
> 所有规则以根 `AGENTS.md` 为权威来源，本文为其贡献者视图摘要。

## ① 目录约定

- **源码单源**：所有角色包、标准、共享库的唯一事实来源是 `.trae/skills/`；`tools/deploy_skills.py` / `solidify.py` 均以它为源。
- **禁止手工复制**：共享内容只存 `shared/`（含 `governance` / `evolution` / `authoring` 与 `references` 副本）；角色包以 `../shared/...` 相对引用复用，**禁止手工复制 `shared/references` 进角色包**（打包时自动内嵌）。
- **产物归位**：技能维护产出落 `.trae/skills/<包名>/`；打包 / 临时物归 `dist/`、`backup/tmp_migrations/`、`_pkg_tmp/`；不得把维护产物误放仓库根或其他目录。

## ② 命名规范

- 全仓目录与文件名使用 **kebab-case**（短横线小写），如 `role-project-init/`、`skill_maintenance_sop.md` 例外仅限既有约定。
- 文件以 **UTF-8** 编码写入；**禁止 GBK / 乱码文件名**，避免跨平台（Windows / macOS）乱码。
- **允许中文文档名**的特殊区域：
  - `台账/` 受控台账库（如 `13_安全审计台账.csv`、`34_客户登记.csv` 等）；
  - `docs/program-control-ledger/` 历史控制台账出口（如 `01_总纲.md`）。
  - 其余位置统一用英文 / kebab-case 文件名。

## ③ 文件管理铁律摘要

- **改技能三同步**：新增 / 修改技能必须同步 `SKILL_INDEX.md` + `references/api_contracts.md`；技能 `description` 150~250 字符，格式「做什么。<触发词>。Load when...」。
- **改动后固化**：任务完成执行 `tools/solidify.sh "<说明>"`（快照→刷新交接断点区→打包→部署），再 `git commit`；禁止把未固化成果留在上下文跨模型传递。
- **敏感信息三级**：A 级禁止入库（密钥 / 凭据 / Token 只存别名，真实值走 `.secrets/` + 凭据管理器）；B 级脱敏入库（主机名 / IP / 用户名 / 绝对路径，提交公共仓库前必须脱敏，IP 默认 `xxx.xxx.xxx.xxx`）；C 级正常入库。提交前自问属于哪级。
- **系统 / 项目外文件操作**：修改、删除系统文件（hosts / 注册表 / System32 等）或仓库外文件，必须：①先获用户明确授权；②操作前强制备份到项目内 `.backup/`（含时间戳）；③留痕 `台账/13_安全审计台账.csv`，并经 `security_audit` 前置审计。无授权 / 未备份一律禁止执行。
- **目录访问边界**：本项目可写范围 = 仓库目录（`台账/26_访问边界.csv`）；目录外访问须经 `register_auth` 授权（`台账/14_授权登记.csv`，未填有效期默认仅本次对话有效）。

## ④ 版本管理

- 使用 **git tag** 管理版本：`git tag vX.Y.Z` 对应各角色包 / 编排器版本号（如 v21.12.0）。
- **不再使用** `skills_backup_*` / `skills_legacy_*` 等手工备份目录（已被 gitignored，且可由 `tools/deploy_skills` 重新生成）。
- 版本号规则：主版本大重构、次版本新增角色包 / 能力、修订版本修正 / 增强；与 `SKILL_INDEX.md` 末尾「文档版本」保持一致。

## ⑤ 提交前自动门禁

- **环境门禁钩子**：`scripts/install-hooks.sh` 一键安装（设置 `core.hooksPath .githooks`，git 钩子不随 clone 分发，新 clone 须执行一次）。
- **`.githooks/pre-commit`**：提交前自动检查 A 级密钥 / B 级脱敏 / `.env` 与 `.secrets` 禁提交 / 大文件 >4K；失败阻断提交（`git commit --no-verify` 仅应急，不推荐）。
- **控制环 `post-commit` 钩子**：提交后触发固化 / 校验联动（如 `tools/check_version_consistency.py`、`tools/check_skill_closure.py` 等），保证版本与闭环一致性。
- 提交前建议本地跑 `python tools/check_version_consistency.py` 与 `python tools/check_skill_release_gate.py` 预检。

## 贡献流程速览

1. 在 `.trae/skills/` 源修改技能 → 同步 `SKILL_INDEX.md` + `references/api_contracts.md` + `description`；
2. `python tools/check_skill_closure.py` / `check_version_consistency.py` 校验通过；
3. `bash tools/solidify.sh "说明"` 固化部署；
4. 刷新 `交接文档.md` 断点区；
5. `git add` 目标文件 → `git commit`（门禁通过后）；
6. 需要版本发布时 `git tag vX.Y.Z`。

---

**文档版本**：v21.12.0 ｜ **知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
