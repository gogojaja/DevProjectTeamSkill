# DevProjectTeamSkill · opencode 启用指南

> 面向 opencode CLI 的技能启用指南。**本指南为当前推荐启用方式**。
> 历史 TRAE 部署方式见 `legacy/TRAE部署与启用指南.md`（v8.0.0 留档，仅参考）。
> 技能库版本：v21.3.2 ｜ 最后更新：2026-08-07

---

## 1. 启用原理

opencode 通过 `skills.paths` 配置指向技能源码目录（本仓库 `.trae/skills/`，**唯一事实来源**）。
运行时 opencode 扫描该目录下的 `SKILL.md`，将 8 个角色包 + 1 个编排器注册为可加载技能。

采用「指向源目录」而非「复制到全局库」的方式，保证技能改动即时生效、单源无副本漂移。

## 2. 配置步骤

### 2.1 项目级（本仓库内，推荐）

仓库根 `opencode.json`：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": {
    "paths": [".trae/skills"]
  }
}
```

在仓库内启动 opencode 即自动加载。

### 2.2 全局级（任何目录可用）

编辑 `~/.config/opencode/opencode.jsonc`：

```jsonc
{
  "skills": {
    "paths": ["/Volumes/BR256G/DevProjectTeamSkill/.trae/skills"]
  }
}
```

> 注意：本仓库位于 USB 卷（`/Volumes/BR256G/...`），拔盘后全局配置失效；
> 如需脱离源码常驻，改用 `bash tools/deploy_skills.sh` 部署到 `~/.config/opencode/skills/`。

### 2.3 双平台注意事项

| 平台 | 全局配置路径 | 说明 |
|------|-------------|------|
| macOS/Linux | `~/.config/opencode/opencode.jsonc` | 可用 `"paths"` 指向源码目录；或 `deploy_skills.sh` 部署到 `~/.config/opencode/skills/` |
| Windows | `%USERPROFILE%\.config\opencode\opencode.jsonc` | `"paths"` 指向源码目录时，盘符/路径须改为 Windows 绝对路径（如 `D:\...\.trae\skills`） |

- `tools/deploy_skills.sh` 与 `.py` 均已平台自适应：Windows 自动部署到 `%USERPROFILE%\.config\opencode\skills`，macOS/Linux 自动部署到 `~/.config/opencode/skills`，无需手改脚本。
- **Windows 上推荐用部署方式**（`bash tools/deploy_skills.sh`）而非手写全局 `"paths"`，避免盘符/反斜杠转义差异导致反复修改配置文件。
- 源码变更后重跑 `solidify` 即自动重新部署，保证全局库与 `.trae/skills/` 一致。

### 2.4 验证

```sh
opencode                      # 进入会话后输入：
/skills                       # 应列出 8 个角色包 + 编排器
```

## 3. 已注册技能清单（v21.3.2）

| # | 技能 | 域 |
|---|------|-----|
| 0 | dev-project-team-skill | 编排器（全生命周期调度/阶段门禁/压缩/交接） |
| 1 | role-project-init | 项目启动（立项/章程/干系人/基线初始化） |
| 2 | role-requirements-analysis | 需求（收集/分析/SRS/变更/追溯） |
| 3 | role-architecture | 架构（策略/4+1/C4/数据安全/ADR/ATAM） |
| 4 | role-development | 开发（策略/编码/走查/单测/联调） |
| 5 | role-testing | 测试（策略/计划/用例/执行/缺陷/总结） |
| 6 | role-deployment | 投产（策略/计划/发布/回滚/交接） |
| 7 | role-governance | 总控保障（台账/评审/门禁/基线固化/审计/归档） |

## 4. 执行模式

- **标准**：软件项目全生命周期（启动→需求→架构→开发→测试→投产→归档）
- **阶段裁剪**：仅需部分阶段（启动阶段 `init_tailor` 产出 `00_阶段配置.csv`）
- **敏捷迭代**：1~2 周迭代循环，迭代轻量评审 + 发布级强门禁（`18_迭代配置.csv`）
- **角色组合加载**：单角色/多角色联合/双角色裁剪
- **技能维护**：编写/修改 SKILL.md 走 skill-authoring 五步流程

## 5. 常用触发词

```
全生命周期 / 启用角色 / 切换角色 / 阶段评审 / 门禁 / 基线固化 / 交接文档
敏捷迭代 / 用敏捷 / 快速上线
技能维护 / skill-authoring / 修改SKILL.md
```

## 6. 维护与固化

- 修改技能源码后执行：`bash tools/solidify.sh "<说明>"` + `git commit`
- 部署到目标目录：`bash tools/deploy_skills.sh --roles role-a,role-b`
- 详细规则见仓库根 `AGENTS.md` 与 `交接文档.md`
