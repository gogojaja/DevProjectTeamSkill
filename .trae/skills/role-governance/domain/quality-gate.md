---
name: "project-quality-gate-skill"
description: "Project quality and gate management skill covering quality baseline, five-dimensional stage review, gate validation with per-stage special checks (requirements/architecture/dev/test/deployment traceability), and defect management. Invoke when performing stage reviews, gate checks, or managing quality defects."
---

# ProjectQualityGateSkill 项目质量与门禁管理技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能唯一标识**：ProjectQualityGateSkill
- **技能版本**：v21.0.0
- **版本发布日期**：2026-08-02
- **版本变更记录**：v1.0.0 由 project-monitor-skill v2.7.0 拆分而来（PMBOK 7th 质量管理 · ISO 9001 · ISO/IEC/IEEE 29119）
- **定位**：项目管控子技能，负责质量基准建立、五维阶段评审（stage_review）、阶段门禁校验（check_gate 含各阶段专项追溯矩阵完整性）与缺陷管理。
- **调用主体**：ProjectMonitorSkill（薄路由壳按 action 分发）
- **触发时机**：阶段产出物定稿后评审、阶段流转前门禁校验、缺陷发现与闭环、各阶段追溯矩阵完整性校验。
- **依赖工具**：project-scope-change-skill · project-governance-skill · project-progress-cost-skill
- **核心约束**：仅由 ProjectMonitorSkill 路由分发加载；评审结果必须以 CSV 输出；严重/主要缺陷未闭环禁止流转；最多 2 轮整改复核，仍存严重缺陷人工介入。

---

## 2. 统一入参标准

```json
{
  "action": "stage_review / check_gate",
  "current_stage": "需求分析/架构设计/开发编码/测试验收/部署运维/文档归档",
  "content": "对应操作内容",
  "user_confirm": "无/同意/拒绝/查错"
}
```

### action 指令清单

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `stage_review` | 标准化阶段评审（五维校验 + 范围跟踪） | 阶段产出物定稿后 | 产出物定稿 |
| `check_gate` | 阶段门禁校验（含各阶段专项） | 阶段流转前 | 评审通过 |

---

## 3. 质量与门禁原则

| 原则 | 要求 |
|------|------|
| 评审先行 | 产出物定稿后先评审后流转 |
| 门禁把关 | 门禁不通过禁止流转 |
| 缺陷闭环 | 严重/主要缺陷闭环后方可流转 |
| 追溯完整 | 各阶段追溯矩阵断链率 <=20% |
| 迭代刹车 | 最多 2 轮整改，仍存严重缺陷人工介入 |

---

## 4. 质量与门禁流程

> 各环节详细执行内容详见 `.//project_quality_gate_details.md` 对应章节。

### 环节 1：质量基准建立（Quality Baseline）

**执行内容**：缺陷分级标准、阶段验收标准、门禁指标写入「质量基准」CSV，详见 `.//project_quality_gate_details.md` §1。

**DoD**：质量基准写入完成 ✅

**规则**：缺陷三级（严重/主要/次要）判定标准明确。

### 环节 2：阶段评审（stage_review）

**DoR**：阶段产出物定稿 ✅ · 评审范围明确 ✅

**执行内容**：五维自动校验（范围合规/功能逻辑质量/工程规范/风险安全/范围跟踪）、`评审报告_<对象>_<版本>_{摘要|缺陷清单|逐原则|范围跟踪|角色权限}.csv` 5 文件输出、缺陷追加「质量缺陷台账」CSV，详见 `.//project_quality_gate_details.md` §2。

**DoD**：评审报告 CSV 生成 ✅ · 缺陷已登记 ✅ · 评审结论输出 ✅

**规则**：评审结果必须 CSV 输出（5 文件固定格式）；最多 2 轮整改复核，仍存严重/主要缺陷人工介入。

### 环节 3：门禁校验（check_gate）

**DoR**：本阶段评审通过 ✅ · 各阶段追溯矩阵可读取 ✅

**执行内容**：质量门禁强制校验（严重/主要缺陷闭环）、各阶段专项门禁细则（需求追溯矩阵/测试 RTM/投产 Go-Live 六维/架构 4+1+C4+ADR+七原则/开发 SonarQube 五维+SAST+SCA+审查+覆盖率），详见 `.//project_quality_gate_details.md` §3。

**DoD**：门禁校验完成 ✅ · 结果写入「门禁验收记录」CSV ✅ · 门禁结论（通过/驳回）✅

**规则**：各阶段专项断链率 >20% 驳回；任一专项不达标驳回；通过后固化物纳入产出物基准清单。

### 环节 4：缺陷管理（Defect Management）

**执行内容**：缺陷全生命周期（发现→登记→修复→复核→闭环）、缺陷分级、闭环要求，详见 `.//project_quality_gate_details.md` §4。

**DoD**：缺陷已登记 ✅ · 修复状态跟踪 ✅ · 闭环确认 ✅

**规则**：严重/主要缺陷必须闭环后方可流转；缺陷记录同步「质量缺陷台账」CSV。

---

## 5. 标准化输出结构

1. **评审类**：`评审报告_<对象>_<版本>_*.csv`（摘要/缺陷清单/逐原则评审详情/范围跟踪比对表/角色权限分布总览）；
2. **门禁类**：门禁结论、未通过风险清单、整改要求、产出物条目化比对表；
3. **缺陷类**：缺陷清单、闭环状态；
> 目录规范详见 `../../shared/references/directory_structure.md`

> 协作接口详见 `../../shared/references/api_contracts.md`

## 6. 技能版本管理规范

> 版本号规则、升级触发条件、升级评审机制统一见 `../../shared/references/common_standards.md`。
> 当前版本：v21.0.0。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-02
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）