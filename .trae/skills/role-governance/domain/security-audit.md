---
name: "project-security-audit-skill"
description: "Project security audit skill covering high-risk operation pre-audit, audit trail (non-deletable operation logging), fault rollback, and security audit coordination. Invoke when auditing high-risk file operations, logging audit trails, or handling fault rollback."
---

# ProjectSecurityAuditSkill 项目安全审计技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能唯一标识**：ProjectSecurityAuditSkill
- **技能版本**：v21.0.0
- **版本发布日期**：2026-08-02
- **版本变更记录**：v1.0.0 由 project-monitor-skill v2.7.0 拆分而来（ITIL v4 变更控制 · ISO 27001 · OWASP ASVS）
- **定位**：项目管控子技能，负责高危操作前置审计、操作留痕（不可删除审计台账）、故障回滚优先逻辑与安全审计协同。
- **调用主体**：ProjectMonitorSkill（薄路由壳按 action 分发）
- **触发时机**：高危文件操作（修改入口脚本/目录、删除移动文件）、服务故障回滚、部署启停、核心架构文件变更。
- **依赖工具**：project-scope-change-skill · project-governance-skill
- **核心约束**：仅由 ProjectMonitorSkill 路由分发加载；高风险操作强制 `user_confirm=同意`（5 分钟无回复自动驳回）；全操作不可删除留痕；用户连续 2 次拒绝同一操作永久终止。

---

## 2. 统一入参标准

```json
{
  "action": "change_audit",
  "current_stage": "需求分析/架构设计/开发编码/测试验收/部署运维/文档归档",
  "content": "对应操作内容",
  "user_confirm": "无/同意/拒绝/查错"
}
```

### action 指令清单

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `change_audit` | 高危操作前置审计（操作影响评估表）+ 全操作留痕 | 高危文件操作、部署启停 | 操作已提出 |

> 故障回滚与审计留痕为 `change_audit` 协同子流程，由 ProjectMonitorSkill 按操作类型路由至本技能执行。

---

## 3. 安全审计原则

| 原则 | 要求 |
|------|------|
| 操作必审 | 高危操作前置审计，生成《操作影响评估表》 |
| 高风险强确认 | 高风险操作强制 `user_confirm=同意`（5 分钟自动驳回） |
| 留痕铁律 | 全操作不可删除留痕，唯一操作 ID 永久追溯 |
| 回滚优先 | 服务故障自动调取备份优先一键回滚 |
| 拒绝终止 | 用户连续 2 次拒绝同一操作永久终止 |
| **系统/项目外铁律** | 修改、删除**系统文件（%windir%\System32、hosts、注册表等）或项目外部文件（仓库之外路径）必须：①先获用户明确授权；②备份到项目内 `.backup/`（含时间戳）；③留痕至 `13_安全审计台账.csv`；否则禁止执行，经 `security_audit` 前置审计 |

---

## 4. 安全审计流程

> 各环节详细执行内容详见 `.//project_security_audit_details.md` 对应章节。

### 环节 1：高危操作前置审计（Pre-audit）

**DoR**：高危操作已提出 ✅ · 操作范围明确 ✅

**执行内容**：高危操作范围识别（入口脚本/文件操作/配置变更/发布操作）、《操作影响评估表》生成（操作 ID/受影响组件/风险等级/回滚方案）、审批规则执行，详见 `.//project_security_audit_details.md` §1。

**DoD**：《操作影响评估表》完成 ✅ · 风险等级已评估 ✅ · 高风险已审批（同意/驳回）✅

**规则**：高风险操作暂停等 `user_confirm=同意`；5 分钟无回复自动驳回；连续 2 次拒绝永久终止。

### 环节 2：操作留痕（Audit Trail）

**DoR**：操作已执行或回滚完成 ✅

**执行内容**：全操作留痕（修改/调整/启停/回滚追加「安全审计台账」CSV）、唯一操作 ID 生成（OP-YYYYMMDD-NNNN）、留痕不可删除，详见 `.//project_security_audit_details.md` §2。

**DoD**：操作已留痕 ✅ · 操作 ID 已生成 ✅ · 留痕内容完整 ✅

**规则**：所有操作必须留痕；留痕记录不可删除、不可篡改。

### 环节 3：故障回滚（Rollback）

**DoR**：服务故障已识别 ✅ · 备份可调取 ✅

**执行内容**：回滚优先逻辑（自动调取备份优先一键回滚，仅 `user_confirm=查错` 启动排查）、回滚步骤执行（读取备份→回滚→留痕→验证→根因分析），详见 `.//project_security_audit_details.md` §3。

**DoD**：一键回滚已执行 ✅ · 回滚操作已留痕 ✅ · 服务已恢复 ✅ · 根因已记录 ✅

**规则**：基础文件缺失/路径错误/语法报错类问题禁止判定为能力上限，必须完整根因修复。

### 环节 4：安全审计协同（Coordination）

**执行内容**：核心文件变更自动转发审计、安全审计结果纳入阶段门禁、归档时整合全部审计日志，详见 `.//project_security_audit_details.md` §4。

**DoD**：变更已审计 ✅ · 门禁已纳入 ✅ · 审计日志已归档 ✅

**规则**：高危文件操作自动转发本技能审计。

---

## 5. 标准化输出结构

1. **审计类**：《操作影响评估表》、「安全审计台账」CSV 记录（唯一操作 ID）；
2. **回滚类**：回滚方案、回滚验证报告、根因分析；
> 目录规范详见 `../../shared/references/directory_structure.md`

> 协作接口详见 `../../shared/references/api_contracts.md`

## 6. 技能版本管理规范

> 版本号规则、升级触发条件、升级评审机制统一见 `../../shared/references/common_standards.md`。
> 当前版本：v21.0.0。

---

**文档版本**：v21.3.0
**最后更新**：2026-08-07（新增系统/项目外文件修改删除铁律：授权+备份+留痕）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）