---
name: "development-strategy-skill"
description: "Development strategy and environment skill covering technical stack confirmation, branching strategy (Trunk-Based/Git Flow), coding standards, task breakdown (WBS), and environment preparation. Invoke when entering development phase, planning development strategy, or setting up development environments."
---

# DevelopmentStrategySkill 开发策略与环境技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **技能唯一标识**：DevelopmentStrategySkill
- **调用主体**：DevProjectTeamSkill（开发工程师子角色）
- **触发时机**：架构基线固化后进入开发阶段、制定开发策略、准备开发环境
- **依赖工具**：ProjectMonitorSkill（变更审计）、development-coding-skill（下游编码环节）
- **参考标准**：ISO/IEC/IEEE 12207 · Trunk-Based Development / Git Flow · OWASP ASVS / Top 10 · Clean Code
- **核心约束**：仅在开发工程师角色激活时加载执行逻辑；策略分析是开发第一步；编码规范在环境准备前定稿；分支策略确定后不可随意变更；禁止编写架构设计文档、需求文档、部署运维脚本。

## 2. 统一入参标准

```json
{
  "action": "操作指令，可选值：analyze_strategy / prepare_env",
  "dev_phase": "当前开发阶段，可选：strategy/env",
  "content": "对应操作内容：开发策略/环境配置",
  "module": "当前开发模块",
  "user_confirm": "用户指令：无/同意/拒绝/查错"
}
```

### action 指令清单

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `analyze_strategy` | 开发策略分析（技术栈确认、分支策略、编码规范、任务拆解、ASVS 映射） | 架构基线固化后、开发阶段第一步 | 架构基线已固化 |
| `prepare_env` | 开发环境准备（环境搭建、依赖管理、工具链、CI/CD、安全工具） | 开发策略确认后 | 策略已确认 |

### 流程约束（七原则入口）

| 原则 | 策略分析验收 | 环境准备验收 |
|------|--------------|--------------|
| 编码规范 | 编码规范文档制定 | Linter/Formatter 配置 |
| 测试先行 | 测试策略制定 | 测试框架配置 |
| 安全编码 | ASVS 映射清单 | 安全工具配置 |
| 代码审查 | 审查规范制定 | PR 模板配置 |
| 持续集成 | CI/CD 策略制定 | CI/CD 流水线配置 |
| 质量门禁 | 质量指标定义 | 扫描器配置 |
| 文档同步 | 文档模板制定 | 文档工具配置 |

## 3. 流程

### 环节 1：开发策略分析（action = analyze_strategy）

- **DoR**：架构基线已固化 ✅ 架构设计说明书已评审（含开发指南）✅ 架构追溯矩阵已建立 ✅ 进度基准与开发窗口已明确 ✅
- **执行内容**：技术栈确认、分支策略（Trunk-Based/Git Flow 决策树）、编码规范、任务拆解（WBS）、计划排期、OWASP ASVS 安全编码映射（V1-V14），详见 `.//development_strategy_details.md` §1。
- **DoD**：开发策略分析报告 ✅ 分支策略已选定 ✅ 编码规范文档完成 ✅ 开发任务清单 CSV（WBS）✅ 开发计划已排期 ✅ ASVS 安全编码映射清单完成 ✅
- **规则**：策略分析是开发第一步；技术栈版本与架构基线一致，变更走变更流程；分支策略确定后不可随意变更；编码规范在环境准备前定稿作为审查依据；策略变更需 `change_audit`。

### 环节 2：开发环境准备（action = prepare_env）

- **DoR**：开发策略已确认 ✅ 编码规范已定稿 ✅ 技术栈版本已确认 ✅
- **执行内容**：环境搭建（本地/容器/远程）、依赖管理、工具链配置、CI/CD 流水线、数据库/中间件本地实例、安全工具配置，详见 `.//development_strategy_details.md` §2。
- **环境配置抽取**：dev 环境配置项统一写入 `台账/20_环境配置.csv`（`../shared/references/environment_standard.md`），密钥只存别名不存明文；供测试/部署引用与检查。
- **DoD**：环境搭建完成 ✅ 依赖版本锁定文件生成 ✅ 工具链（Linter/Formatter/Git Hooks）完成 ✅ CI/CD 流水线完成 ✅ 数据库/中间件本地实例就绪 ✅ 安全工具配置完成 ✅ 环境配置已写入 `20_环境配置.csv` ✅
- **规则**：开发环境与生产环境结构一致（配置外部化）；依赖版本锁定禁止 floating；CI/CD 在代码开发前配置完成；Git Hooks 配提交前检查；安全工具在首次提交前配置完成。

## 4. 输出规范

1. **策略分析类**：开发策略分析报告、分支策略规范文档、编码规范文档、开发任务清单 CSV、安全编码检查清单；
2. **环境配置类**：环境搭建指南、依赖清单、工具链配置文档、CI/CD 配置文档；
> 目录规范详见 `../../shared/references/directory_structure.md`
> 协作接口详见 `../../shared/references/api_contracts.md`

## 5. 边界

- 仅开发工程师角色激活时执行；禁止编写架构设计文档、需求文档、部署运维脚本；分支策略/技术栈变更走 `change_audit` 与影响评估；禁止跨阶段执行后续环节。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-02
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
