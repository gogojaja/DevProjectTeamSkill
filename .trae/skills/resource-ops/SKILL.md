---
name: "resource-ops"
description: "用户提到资源管理/容量规划/技能矩阵/资源分配/负载均衡/利用率/人员调配/资源过载/资源闲置/单点故障时加载本资源运营管理技能：负责跨项目人力资源容量登记（可用工时/利用率）、资源分配与调拨、负载均衡检查（过载>85%/健康50~85%/闲置<50%）、技能矩阵管理（熟练度1~5）、单点故障检测（某技能仅1人掌握）。可脱离编排器独立部署运行。用户说资源容量/技能矩阵/负载均衡/资源分配/单点故障时加载。"
---

# resource-ops 资源运营管理技能

> 版权：`../shared/references/COPYRIGHT.md` Token：`../shared/references/token_standard.md`
> 权威工具：`tools/resource_ops.py`（capacity/allocate/balance/skill/singlespot）
> 对齐：PMI Resource Management · Theory of Constraints · Skills Matrix

## 1. 元数据

- **技能版本**：v1.0.0 **发布日期**：2026-09-08
- **变更记录**：
  - v1.0.0：首个**合规独立可部署**版本——从编排器内嵌子技能提升为 `.trae/skills/` 顶层自包含技能；补 YAML frontmatter、三段版本号、闭环执行系统、`skill.manifest.json`（打包期注入 `resource_ops.py`+`test_resource_ops.py`）；注册 SKILL_INDEX 条目 26 + STANDALONE_SKILLS。原 5 action 能力、资源容量模型、技能矩阵、单点故障检测全部保留；负载均衡阈值按工具实现对齐（过载>85%/健康≥50%/闲置<50%）。
- **参考标准**：PMI Resource Management · Theory of Constraints（TOC）· Skills Matrix
- **定位**：跨项目人力资源的容量规划、技能管理与负载均衡。

## 2. 触发规则

用户表达「资源管理 / 容量规划 / 技能矩阵 / 资源分配 / 负载均衡 / 利用率 / 人员调配 / 资源过载 / 资源闲置 / 单点故障」时加载本技能。

| 环节 | action | 功能 | 台账 | CLI |
|------|--------|------|------|-----|
| 容量登记 | capacity_register | 团队/个人可用工时登记 | 48_资源容量.csv | `capacity` |
| 资源分配 | allocate | 跨项目分配与调拨跟踪 | 48_资源容量.csv | `allocate` |
| 负载均衡 | load_balance | 过载/健康/闲置检查 | 48_资源容量.csv | `balance` |
| 技能矩阵 | skill_matrix | 成员技能 + 熟练度 1~5 | 49_技能矩阵.csv | `skill` |
| 单点检测 | singlespot_risk | 某技能仅 1 人掌握预警 | 49_技能矩阵.csv | `singlespot` |

**边界**：资源冲突检测→`resource_conflict` MCP（仅检测冲突）；资源运营管理→本技能（容量+技能+负载）；CMDB 环境资源→`tools/cmdb/`（IT 基础设施，非人力资源）。

## 3. 资源容量与技能模型（单一信源）

```
可用工时 = 工作日 × 8h × 利用率系数（0.8，扣除会议/培训/休假）
已分配   = 项目A分配 + 项目B分配 + ...
利用率   = 已分配 / 可用工时 × 100%
```

**负载均衡阈值**（与 `resource_ops.py` cmd_allocate/cmd_balance 一致）：利用率 **>85% = 过载**（预警，`balance` 退出码 1）；**50%~85% = 健康**；**<50% = 闲置**（建议增加分配或释放）。

**技能熟练度 1~5**：1=入门 / 2=基础 / 3=熟练 / 4=专家 / 5=权威。**单点故障**：某技能熟练度 ≥3 者仅 1 人 → 预警（`singlespot` 退出码 1）。

## 4. 工具调用（CLI）

权威工具 `tools/resource_ops.py`（Python3，零第三方依赖）：

```bash
python3 tools/resource_ops.py capacity --name "张三" --role "后端开发" --available 160
python3 tools/resource_ops.py allocate --name "张三" --project "项目A" --hours 80
python3 tools/resource_ops.py balance
python3 tools/resource_ops.py skill --name "张三" --skills "Python:4,Java:3,SQL:3"
python3 tools/resource_ops.py singlespot
```

**台账产物**（UTF-8 with BOM）：`48_资源容量.csv`（编号/成员/角色/可用工时/已分配/利用率%/项目分配/登记日期）· `49_技能矩阵.csv`（编号/成员/技能清单/熟练度/登记日期/单点风险）。

**退出码**：`0`=成功/无过载无单点；`1`=参数非法（成员不存在/技能格式错误）或检出过载/单点故障。

## 5. 核心原则

1. **容量先登记后分配**：无容量记录不得分配（allocate 找不到成员则拒绝）。
2. **利用率量化**：分配即重算利用率，过载（>85%）必预警。
3. **技能可视**：技能矩阵记录熟练度，支撑调配决策。
4. **单点必除**：关键技能仅 1 人掌握须预警并培养备份。
5. **人力资源边界**：仅管人力容量/技能，环境资源归 CMDB。

## 6. 输出规范

- 所有台账 CSV（UTF-8 with BOM，禁止 .xlsx）；技能清单/熟练度以 JSON 存储；输出回显关键行 + 计数。
- 边界仅人力资源运营域；不承接环境资源管理（归 CMDB）、不承接资源冲突检测（归 resource_conflict MCP）。

## 7. 独立部署与镜像同步

本技能为**自包含可独立部署技能**：权威工具保留在仓库根 `tools/resource_ops.py`（单一信源），`skill.manifest.json` 声明打包/部署期注入 `resource_ops.py`+`test_resource_ops.py` 副本。`package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 按 manifest 注入后，产物含 `SKILL.md + skill.manifest.json + tools/ + tests/`，脱离编排器即可 `python3 tools/resource_ops.py ...` 运行。

**分发清单（STANDALONE_SKILLS）**：已登记为 `package_skills.py`/`deploy_skills.py`/`deploy_skills.sh` 的 `STANDALONE_SKILLS`（独立于 11 个 `ALL_ROLES`），全量同步（无参）自动纳入；按需 `--role resource-ops` 单独分发。**镜像目标**：`.github/skills/` · `.claude/skills/` · `.agents/skills/` · 全局 opencode 库。

> **同步命令**：改动后运行 `python3 tools/package_skills.py` + `python3 tools/deploy_skills.py`。

---

## 闭环执行系统

### 1. 任务入口
- 输入：用户要求管理资源容量、技能矩阵、负载均衡、单点故障检测；
- 前置：需确认团队成员清单、项目清单、可用工时基准；
- 不适用：环境资源管理（归 CMDB）、资源冲突检测（归 resource_conflict MCP）。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 | 处理方式 |
|------|---------|---------|---------|
| 待启动 | 资源管理需求明确 | 确认成员与项目清单 | 读取现有台账 |
| 执行中 | 容量登记/分配/技能录入中 | 产出形成 | 按 action 执行 |
| 校验中 | 负载均衡/单点检测完成 | 过载/单点处理 | 预警 + 调配建议 |
| 阻塞 | 成员未登记容量即分配 | 补容量登记 | 暂停并记录阻塞 |
| 完成 | 台账更新 | 归档 | 通知相关方 |
| 回退 | 检出过载/单点故障 | 调配或培养备份 | 预警并限期整改 |

### 3. 执行动作层
- 步骤 1：`capacity` 资源容量登记（成员/角色/可用工时）；
- 步骤 2：`allocate` 资源分配（累加已分配 + 重算利用率 + 状态判定）；
- 步骤 3：`balance` 负载均衡检查（过载>85%/健康/闲置<50%）；
- 步骤 4：`skill` 技能矩阵录入（"Python:4,Java:3" 解析为 JSON）；
- 步骤 5：`singlespot` 单点故障检测（熟练度≥3 仅 1 人 → 预警）；
- 输入输出约束：先登记容量后分配；技能格式 `名:级别`；台账 UTF-8 BOM；退出码 0/1。

### 4. 验收门禁
- 必须产出物：资源容量表（48）、技能矩阵（49）、负载均衡报告、单点检测报告；
- 通过条件：利用率计算正确、过载已预警、单点风险已标识；
- 失败条件：资源数据不完整、过载未预警、成员未登记即分配；
- 审核对象：role-project-mgmt（资源调配）+ role-program-mgmt（跨项目资源）。

### 5. 失败处理
- 失败类型：成员未登记容量、技能格式错误、检出过载（>85%）、检出单点故障；
- 恢复策略：补容量登记后重分配；修正技能格式；过载则调配或释放；单点则培养备份；
- 是否需要人工确认：过载调配与单点故障处置须人工确认。

### 6. 产出与交接
- 产出物列表：48_资源容量.csv、49_技能矩阵.csv、负载均衡报告、单点检测报告；
- 交接对象：role-project-mgmt（项目资源调配）、role-program-mgmt（跨项目资源平衡）、MCP resource_capacity/resource_conflict；
- 下一步动作：健康 → 维持；过载 → 调配；单点 → 培养备份。

### 7. 审计记录
- 执行时间：capacity/allocate/skill/singlespot 时间点（台账登记日期）；
- 关键参数：可用工时、已分配、利用率%、技能熟练度、项目分配明细；
- 关键决策：负载状态判定（过载/健康/闲置）、单点故障预警；
- 结果证据：48/49 台账 CSV、负载均衡报告、单点检测报告。

---

**文档版本**：v1.0.0 **最后更新**：2026-09-08（从编排器内嵌子技能提升为顶层独立可部署技能；补 frontmatter/三段版本/闭环执行系统/skill.manifest.json；注册 SKILL_INDEX 条目26 + STANDALONE_SKILLS；负载阈值按 resource_ops.py 实现对齐 过载>85%/健康≥50%/闲置<50%）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
