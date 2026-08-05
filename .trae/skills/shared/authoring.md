---
name: "skill-authoring"
description: "技能创建/修改元技能（写入侧）：轻量五步流程（需求定义→SKILL.md 编写→结构校验→功能验证→打包发布）、三项结构校验、三触发功能验证、zip 打包。触发词：author_define、author_write、skill-authoring、新建技能、修改技能、技能编写。Load when the user creates or modifies a skill, writes SKILL.md, or packages a skill release."
---

# SkillAuthoringSkill 技能创建/修改元技能（shared/authoring.md）

> 版权声明详见 `./references/COPYRIGHT.md`　接口契约详见 `./references/api_contracts.md`

## 1. 基础元数据

- **技能唯一标识**：SkillAuthoringSkill
- **技能版本**：v1.0.3（源版本，随宿主 v21.0.0 内嵌 shared/）
- **定位**：技能创建/修改元技能（Meta-Skill），目标产物是 Skill 本身（SKILL.md）而非软件项目。
- **调用主体**：用户手动指令触发（如"新建一个技能"、"修改 xx 技能"）/ DevProjectTeamSkill 简化模式路由转发。
- **参考标准**（行业最佳实践）：OpenAI Function/Tool 描述规范（触发词+能力边界）· Anthropic Agent Skills 最佳实践 · prompt engineering 最佳实践（角色/步骤/规则/DoR/DoD 结构化）· 语义化版本规范 SemVer
- **核心约束**：
  1. 本技能只负责 Skill 文件的创建与修改，不执行软件项目业务任务；
  2. 校验铁律：结构校验不通过不得进入功能验证，功能验证不通过不得打包发布；
  3. 发布前须按 `./references/common_standards.md` 完成技能库快照，禁止无快照发布；
  4. 与 shared/evolution.md 边界：本技能负责产出新技能/新版本，evolution 负责诊断已有技能缺陷，不重叠。

## 2. 统一入参标准

```json
{
  "action": "操作指令，可选值：author_define / author_write / author_validate / author_test / author_pack",
  "skill_name": "目标技能名称（如 MyCustomSkill）",
  "content": "对应操作内容：需求描述/SKILL.md 草案/校验上下文/测试上下文/发布信息",
  "mode": "执行模式：full（五步全流程）/ validate_only（仅校验）/ pack_only（仅打包）"
}
```

### action 指令清单

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `author_define` | 需求定义（1 段 3-5 句描述明确做什么/何时触发/边界） | 新建技能 | 无 |
| `author_write` | SKILL.md 编写（frontmatter + 正文四部分） | 需求定义完成 | author_define 通过 |
| `author_validate` | 三项结构校验（frontmatter/内容完整性/无重复定义） | SKILL.md 编写完成 | author_write 通过 |
| `author_test` | 功能验证（正向/反向/边界三触发） | 结构校验通过 | author_validate 通过 |
| `author_pack` | 打包发布（独立 zip + 快照备份） | 功能验证通过 | author_test 通过 |

## 3. 五步流程

### Step 1 — 需求定义（author_define，~10min）

**处理规则**：
1. 输出 1 段需求描述（3-5 句话）：要做什么、何时触发、边界在哪；
2. 判定是新建独立技能还是修改既有技能，给出版本号建议（遵循 `./references/common_standards.md`）；
3. 涉及跨技能依赖时标注调用关系（参考 `./references/api_contracts.md`）；
4. 需求描述经用户确认后方可进入编写。

**输出**：技能需求描述（1 段）+ 版本建议 + 边界说明

### Step 2 — SKILL.md 编写（author_write，~20min）

**处理规则**：
1. frontmatter：`---` 包裹，含 `name` 与 `description` 两字段；description 精简（~250 字符），仅含触发词与能力边界；
2. 正文四部分必含：适用场景、核心模块、使用流程、输出规范；
3. 版本元数据按 `./references/common_standards.md` 格式（技能版本号/发布日/变更记录倒序）；
4. 跨技能引用使用相对路径 `./references/`；
5. 文件尾页脚按 common_standards（文档版本/最后更新/知识产权）。

**输出**：SKILL.md 完整文件

### Step 3 — 结构校验（author_validate，~5min）

| 校验项 | 检查内容 | 通过标准 |
|--------|---------|---------|
| frontmatter 格式 | `---` 包裹、含 name 和 description 字段 | 格式正确，字段无缺失 |
| 内容完整性 | 适用场景、核心模块、使用流程、输出规范四个部分 | 四部分均有内容 |
| 无重复定义 | 文件内无重复的章节或模块定义 | 无重复 |

校验失败 → 定位修复后重新校验，不得带病进入下一步。

**输出**：结构校验结果（通过/失败 + 失败项清单）

### Step 4 — 功能验证（author_test，~10min）

| 测试类型 | 方法 | 通过标准 |
|---------|------|---------|
| 正向触发 | 用与 description 匹配的提问测试 | 正确加载并响应 |
| 反向触发 | 用与技能无关的提问测试 | 不误触发 |
| 边界触发 | 用近似但不在范围内的提问测试 | 不误触发 |

**输出**：功能验证结果（三触发通过/失败）

### Step 5 — 打包发布（author_pack，~5min）

**处理规则**：
1. 每个技能单独 zip，命名 `dist/<skill-name>_v<版本号>.zip`；zip 内含 `SKILL.md` + 该技能引用的 `references/`（详见 `./references/cross_tool_standard.md`），确保独立解压后可放入任意工具 skills/ 目录直接使用；
2. 推荐直接执行 `tools/package_skills.sh` 一键打包（自动解析版本号与引用文档）；跨工具部署执行 `tools/deploy_skills.sh`（同步至 `.trae/skills/` `.github/skills/` `.claude/skills/` `.agents/skills/`）；
3. 发布前按 `./references/common_standards.md` 创建/更新 `skills_backup_v<版本号>/` 快照并做一致性比对；
4. 发布后登记变更记录与台账（涉及主技能体系的变更登记 CHG）；
5. 涉及既有技能修改时同步更新主技能路由表与 `./references/api_contracts.md`。

**输出**：zip 包（含 references）+ 快照 + 变更登记

## 4. 触发规则与安全铁律

### 4.1 触发场景

- 用户新建 SKILL.md（"帮我建个技能"）
- 用户修改既有技能（"修改 xx 技能的规则"）
- 用户要求五步简化流程迭代

### 4.2 安全铁律

1. **校验铁律**：结构校验不通过不得进入功能验证；功能验证不通过不得打包发布；
2. **快照铁律**：发布前按 common_standards 快照时机匹配执行——结构性重构/跨技能批量修改做全库快照，单技能修订（vX.Y.Z）备份该技能即可；禁止无快照发布；
3. **边界铁律**：本技能不执行软件项目业务任务；正式软件项目交付必须走 DevProjectTeamSkill 标准模式；
4. **权限铁律**：删除/移动技能文件等高危操作必须经 role-governance 审计。

### 4.3 禁用边界

- 正式软件项目交付（必须走 DevProjectTeamSkill 标准模式）
- 软件项目业务任务执行
- 跳过结构校验/功能验证直接打包

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
