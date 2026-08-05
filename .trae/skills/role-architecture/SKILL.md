---
name: "role-architecture"
description: "架构设计角色包：架构策略分析、4+1 视图与 C4 逻辑设计、数据与安全架构、ADR 决策、ATAM 评审及基线固化。触发词：架构策略、架构设计、4+1视图、C4模型、数据架构、安全架构、ADR、架构评审、ATAM。Load when the user requests architecture strategy, 4+1/C4 design, data/security architecture, or ATAM review."
---

# role-architecture 架构设计角色包

> 版权：`../shared/references/COPYRIGHT.md`　Token：`../shared/references/token_standard.md`　总控：`../shared/governance.md`

## 1. 元数据

- **技能版本**：v21.0.0　**发布日期**：2026-08-04
- **变更记录**：v21.0.0 由 architecture-management-skill + 4 子技能重组为角色包
- **参考标准**：ISO/IEC/IEEE 42010 · ISO/IEC 25010 · TOGAF · ATAM · C4 Model

## 2. 触发规则

用户表达「架构策略/架构设计/4+1视图/C4/数据架构/安全架构/写 ADR/原型验证/架构评审/架构变更」时加载本包。先 Read 路由表，命中后只读对应 `domain/*.md`。

## 3. 流程（路由到 domain/）

| 环节 | action | 明细 |
|------|--------|------|
| 策略分析 | analyze_strategy | `domain/strategy.md` |
| 逻辑设计 | design_architecture | `domain/design.md`（4+1 / C4 / 组件 / 接口 / 部署） |
| 数据与安全 | design_data_security | `domain/data-security.md` |
| 决策记录 | record_decisions | `domain/review.md`（ADR） |
| 原型验证 | validate_prototype | `domain/review.md` |
| 架构评审 | review_architecture | `domain/review.md`（ATAM） |
| 变更分析 | change_analysis | `domain/review.md` |
| 基线固化 | solidify_baseline | `../shared/governance.md` |

## 4. 设计原则（映射 ISO/IEC 25010）

模块化/内聚/松耦合/抽象/信息隐藏/单点控制，映射质量属性（性能/可用性/安全/可维护性/可扩展性）。评估与反模式检查见 domain 明细。

## 5. 输出规范与边界

- 架构视图 / ADR / ATAM 报告按 token_standard §3 输出 CSV；
- 评审经 `../shared/governance.md`；
- 边界：仅架构域；开发/测试等路由到对应角色包。

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）