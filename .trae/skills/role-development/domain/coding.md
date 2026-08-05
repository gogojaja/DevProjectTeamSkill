---
name: "development-coding-skill"
description: "Code development skill covering module implementation, coding standards, secure coding (OWASP ASVS), API implementation, database operations, and error handling. Invoke when writing code, implementing features, or doing secure coding."
---

# DevelopmentCodingSkill 代码开发技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **技能唯一标识**：DevelopmentCodingSkill
- **调用主体**：DevProjectTeamSkill（开发工程师子角色）
- **触发时机**：开发环境就绪后进入代码开发、编写代码、实现功能模块、安全编码
- **依赖工具**：ProjectMonitorSkill（变更审计）、development-testing-skill（下游单元测试环节）
- **参考标准**：ISO/IEC/IEEE 12207 · Clean Code · OWASP ASVS / Top 10 · ISO/IEC 25010
- **核心约束**：仅在开发工程师角色激活时加载执行逻辑；禁止超 500 行文件不拆分；外部输入必须验证；禁止硬编码配置；禁止循环依赖；禁止 sudo 权限操作；禁止编写架构设计文档、需求文档、部署运维脚本。

### 编码强制规则（编码铁律）

| 规则 | 要求 |
|------|------|
| 模块化 | 文件超 500 行自动模块化拆分 |
| 调试 | 内置 DEBUG 日志 |
| 自检 | 输出前语法自检 |
| 完整性 | 禁止残缺半成品 |
| 输入 | 外部输入必须验证 |
| 依赖 | 禁止循环依赖 |
| 配置 | 禁止硬编码配置（外部化） |
| 权限 | 禁止 sudo 权限操作 |

## 2. 统一入参标准

```json
{
  "action": "操作指令，可选值：develop_code",
  "dev_phase": "当前开发阶段，可选：development",
  "content": "对应操作内容：代码实现/功能描述",
  "module": "当前开发模块",
  "user_confirm": "用户指令：无/同意/拒绝/查错"
}
```

### action 指令清单

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `develop_code` | 代码开发（功能实现、编码规范、安全编码、文档注释） | 环境就绪后 | 环境已就绪 |

## 3. 流程

### 环节：代码开发（action = develop_code）

- **DoR**：开发环境就绪 ✅ 编码规范已定稿 ✅ 开发任务清单已确认 ✅ 架构设计文档已可用 ✅
- **执行内容**：功能模块实现、注释与文档、API 实现、数据库操作实现、安全编码实现、错误处理与日志，详见 `.//development_coding_details.md` §3。
- **DoD**：功能模块全部实现 ✅ 注释符合规范 ✅ API 符合接口契约 ✅ 数据库用参数化查询 ✅ ASVS 安全编码映射项全部实现 ✅ 错误处理和日志符合规范 ✅
- **规则**：按任务清单逐条完成不可跳过；每次提交是可编译完整代码；提交前过本地 Linter；安全编码逐条实现；发现架构问题记录反馈，不擅自修改架构。

## 4. 输出规范

1. **代码开发类**：源代码文件、代码注释、API 实现、安全编码实现；
2. **文档类**：模块头部注释、CHANGELOG 变更记录；
> 目录规范详见 `../../shared/references/directory_structure.md`
> 协作接口详见 `../../shared/references/api_contracts.md`

## 5. 边界

- 仅开发工程师角色激活时执行；禁止超 500 行不拆分；禁止硬编码配置/循环依赖/sudo 权限；外部输入必须验证；禁止编写架构设计文档、需求文档、部署运维脚本；架构问题只记录反馈，不擅自修改。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-02
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
