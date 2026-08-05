---
name: "project-scope-change-skill"
description: "Project scope and change management skill covering scope gate validation, deliverable itemized comparison, scope tracking, change audit with five-dimensional impact assessment, and change registration. Invoke when checking scope compliance, auditing changes, or handling scope changes."
---

# ProjectScopeChangeSkill 项目范围与变更管理技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `change_audit` | 范围/架构/核心文件变更审计（五维影响评估） | 变更、范围调整 | 变更已提出 |

- **调用主体**：ProjectMonitorSkill（薄路由壳按 action 分发）；范围门禁校验、产出物条目化比对、范围跟踪检查为 `check_gate`/`stage_review` 协同子步骤，由 project-quality-gate-skill 门禁流程触发本技能。
- **参考标准**：PMBOK 7th（范围管理）· ITIL v4（变更使能）· ISO 21500
- **依赖工具**：project-quality-gate-skill（门禁协同）、project-security-audit-skill（核心文件变更安全审计）

## 2. 流程

### 环节 1：范围门禁校验（Scope Gate）
产出物匹配「范围基准」核查、超范围内容拦截、产出物条目化比对（上一阶段基准 vs 下一阶段准入，✅/❌/⚠️）、范围跟踪检查（缩水/蔓延/内容变更判定）。
**DoD**：范围核查完成 · 产出物比对表生成 · 范围跟踪比对表生成 · 结果写入 `台账/07_范围跟踪台账.csv`。
**规则**：流转前必须范围核查；超范围内容无审批拦截；严重（缩水）/主要（蔓延）缺陷记录并限期整改。

### 环节 2：变更审计（change_audit）
**DoR**：变更已提出 · 影响范围可评估。
**执行内容**：五维影响评估（范围/进度/成本/质量/安全）、《变更影响评估表》生成、重大变更审批、记录追加 `台账/06_范围变更台账.csv`。
**DoD**：评估表完成 · 五维风险已评估 · 重大变更已审批 · 变更台账已追加。
**规则**：重大变更强制 `user_confirm=同意`；核心架构文件变更自动转发安全审计；同一需求连续 3 次无审批变更触发范围冻结预警。

## 3. 输出规范

1. **门禁类**：产出物条目化比对表（✅/❌/⚠️）、范围跟踪比对表；
2. **变更类**：《变更影响评估表》、「范围变更台账」记录。
> 目录规范详见 `../../shared/references/directory_structure.md`，协作接口详见 `../../shared/references/api_contracts.md`

## 4. 边界

- 仅由 ProjectMonitorSkill 路由分发加载；
- 超范围内容无审批禁止流转；
- 重大变更强制 `user_confirm=同意`；
- 同一需求连续 3 次无审批变更 → 冻结范围。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）