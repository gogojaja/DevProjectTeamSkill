---
name: "architecture-strategy-skill"
description: "Architecture strategy analysis sub-skill performing deep analysis of business context and architecture requirements across configurable dimensions (business/technical/functional/quality/cost/time constraints), outputting strategy analysis report with ATAM assessment and technology selection recommendation. Invoke when performing architecture strategy analysis."
---

# ArchitectureStrategySkill 架构策略分析技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **版本**：v21.0.0　**发布**：2026-08-04　**基准**：TOGAF 10 ADM · ISO/IEC/IEEE 42010 · ADD 3.0 · 12-Factor · C4
- **定位**：架构「策略与评估」独立技能，输出《架构策略分析报告》（ATAM 权衡 + 技术选型矩阵 + 风险评估）
- **调用**：架构设计师子角色；ArchitectureDesignSkill 路由分发，仅架构设计师激活时执行

## 2. 触发规则

需求基线固化后进入架构设计、编写策略、质量属性量化、技术选型时触发。

## 3. 流程（action=analyze_strategy）

业务分析 → 质量属性量化 → 约束梳理（业务/技术/功能/质量/成本/时间）→ ATAM 权衡 → 技术选型矩阵 → 风险登记。铁律：策略分析须在设计前完成并评审通过后交 design。

## 4. 输出规范（CSV）

- `架构资产/架构策略分析报告.csv`　`架构资产/技术选型评估矩阵.csv`
- `质量属性需求矩阵.csv`　`架构资产/架构风险登记册.csv`

## 5. 边界

禁止编写具体架构图纸（交 design）；仅架构域，输出经评审后流转。

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
