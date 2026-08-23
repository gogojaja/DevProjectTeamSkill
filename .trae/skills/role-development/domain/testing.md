---
name: "development-testing-skill"
description: "Unit testing skill covering TDD/BDD, test case design, coverage targets, Mock/Stub, automated execution, and regression testing. Invoke when writing unit tests, running unit tests, or validating code coverage."
---

# DevelopmentTestingSkill 单元测试技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **技能唯一标识**：DevelopmentTestingSkill
- **调用主体**：DevProjectTeamSkill（开发工程师子角色）
- **触发时机**：代码开发完成后编写/运行单元测试、覆盖率不达标时补充测试、bug 修复后回归
- **依赖工具**：ProjectMonitorSkill（门禁校验）、development-coding-skill（上游编码环节）、development-integration-skill（下游联调环节）
- **参考标准**：ISO/IEC/IEEE 12207（验证过程）· TDD / BDD · ISTQB · Clean Code
- **核心约束**：仅在开发工程师角色激活时加载执行逻辑；覆盖率不达标不进入下游环节；用例相互独立；外部依赖必须 Mock；每次 bug 修复同时编写回归用例。

### 测试原则

| 原则 | 要求 |
|------|------|
| 测试先行 | TDD/BDD，先写测试后写代码 |
| 覆盖率 | 行>=80%、分支>=70%、函数>=90%、关键路径100% |
| 用例独立 | 用例相互独立、可独立执行 |
| Mock 隔离 | 外部依赖必须 Mock（API/DB/MQ/FS/时间） |
| 回归闭环 | 每次 bug 修复同时编写回归用例 |
| 门禁关联 | 覆盖率不达标不进入下游环节 |

## 2. 统一入参标准

```json
{
  "action": "操作指令，可选值：run_unit_test",
  "dev_phase": "当前开发阶段，可选：testing",
  "content": "对应操作内容：测试脚本/测试目标",
  "module": "当前开发模块",
  "user_confirm": "用户指令：无/同意/拒绝/查错"
}
```

### action 指令清单

| action | 作用 | 触发场景 | 前置条件 |
|--------|------|----------|----------|
| `run_unit_test` | 单元测试（TDD/BDD、覆盖率、Mock、回归测试） | 代码开发完成后 | 代码已开发 |

## 3. 流程

### 环节：单元测试（action = run_unit_test）

- **DoR**：代码开发完成 ✅ 测试框架已配置（pytest/jest/junit）✅ 测试数据已准备 ✅
- **执行内容**：TDD 三阶段（Red/Green/Refactor）+ 用例设计方法（等价类/边界值/错误推测/路径覆盖/状态迁移）、覆盖率目标、Mock/Stub 配置、自动化执行、回归测试，详见 `development-testing-skill__resources/development_testing_details.md` §1-§5。
- **DoD**：用例覆盖全部功能点 ✅ 行覆盖率>=80%、分支>=70% ✅ 关键路径 100% ✅ 全部测试通过（0 失败）✅ Mock/Stub 完整 ✅ 回归测试通过 ✅
- **规则**：开发完成后立即编写测试，推荐 TDD；覆盖率不达标不进入联调/质量环节；用例相互独立；外部依赖必须 Mock；每次 bug 修复同时编写回归用例。

## 4. 输出规范

1. **测试类**：单元测试脚本、覆盖率报告、Mock 配置、回归测试报告；
2. **统计类**：覆盖率统计（行/分支/函数/关键路径）；
> 目录规范详见 `../../shared/references/directory_structure.md`
> 协作接口详见 `../../shared/references/api_contracts.md`

## 5. 边界

- 仅开发工程师角色激活时执行；覆盖率不达标不进入联调/质量环节；用例相互独立；外部依赖必须 Mock；每次 bug 修复同时编写回归用例；禁止跳过测试直接进入下游。

---

**文档版本**：v21.0.0
**最后更新**：2026-08-02
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
