# Team Pipeline 团队流水线详细协议

> 编排器：`../SKILL.md`　上位：编排器 §5 调度规则

---

## 1. 五阶段定义

| 阶段 | 代号 | 核心角色 | 产出 | 门禁 |
|------|------|----------|------|------|
| 1 | plan | Analyst(S3) + Planner(S3) | 任务分解 DAG + 验收标准 | 依赖图无环 + 覆盖率 100% |
| 2 | prd | Architect(S3) | 技术设计/接口契约/数据模型 | 契约评审通过 + 无循环依赖 |
| 3 | exec | Executor(S0~S2) | 代码/测试/文档 | lint/typecheck/test 全绿 |
| 4 | verify | Architect + SecurityReviewer + CodeReviewer(并行) | QA 签署报告 | 三视角全通过 |
| 5 | fix | Executor(按根因分派) | 修复补丁 + 回归测试 | 同一错误 ≤3 轮 |

---

## 2. 阶段转换协议

```yaml
transition:
  plan->prd:
    require: [dag_validated, acceptance_defined]
    artifact: ".senate/plans/team-dag.json"
  prd->exec:
    require: [contract_reviewed, no_cycles]
    artifact: ".senate/specs/team-prd.md"
  exec->verify:
    require: [all_green, coverage>=80%]
    artifact: "build/test reports"
  verify->fix:
    trigger: any_failed
    max_cycles: 3
  fix->verify:
    require: [patch_applied, regression_passed]
    artifact: "fix patches + test results"
```

---

## 3. 角色映射表

| 阶段 | 主角色 | 档位 | 备选 | 并行度 |
|------|--------|------|------|--------|
| plan | Analyst + Planner | S3(强模型) | - | 2 |
| prd | Architect | S3(强模型) | S2 | 1 |
| exec | Executor | S0~S2(免费→平衡) | - | ≤6 |
| verify | Architect + SecRev + CodeRev | S2/S3 | - | 3 |
| fix | Executor(按根因) | S0~S2 | - | ≤2 |

**模型路由规则**（档位见 `../../../../references/model_selection.md` §3-4）：
- 简单/模板化任务 → S0（免费/低价，快、省）
- 标准实现/调试 → S1（低价/平衡）
- 架构/安全/深度审查 → S2/S3（强模型，S3 高危禁止降档）

---

## 4. 产出模板

### 3.1 任务分解 DAG (`.senate/plans/team-dag.json`)
```json
{
  "version": "1.0",
  "nodes": [
    {"id": "T1", "name": "API设计", "role": "architect", "deps": []},
    {"id": "T2", "name": "前端页面", "role": "executor", "deps": ["T1"]},
    {"id": "T3", "name": "后端服务", "role": "executor", "deps": ["T1"]},
    {"id": "T4", "name": "集成测试", "role": "test-engineer", "deps": ["T2","T3"]}
  ],
  "edges": [["T1","T2"],["T1","T3"],["T2","T4"],["T3","T4"]]
}
```

### 3.2 验收标准清单
```markdown
# 任务 T2 验收标准
- [ ] 页面渲染无报错
- [ ] API 调用成功率 100%
- [ ] 响应时间 < 200ms
- [ ] 单测覆盖率 ≥ 85%
```

### 3.3 QA 签署报告
```markdown
# Team Pipeline QA Sign-off
Phase: verify
Validators:
  - Architect: PASS (功能完整性)
  - SecurityReviewer: PASS (0 high/critical)
  - CodeReviewer: PASS (风格/复杂度/测试)
Confidence: high
Scope-risk: moderate
Not-tested: E2E 跨服务流程
```

---

## 4. 异常处理

| 异常 | 处理策略 |
|------|----------|
| DAG 有环 | plan 阶段强制阻断，要求 Planner 重写 |
| 接口契约变更 | prd 阶段回滚，Architect 重新评审 |
| exec 阶段并行冲突 | MVCC 检测冲突 → 自动重试 2 次 → 仍冲突升级人工 |
| verify 三视角分歧 | 多数决；平局 → Architect 裁决 |
| fix 超过 3 轮 | 标记根本问题，生成 RCA 报告，请求人工介入 |

---

## 5. 并行度控制

```python
MAX_PARALLEL = {
    "plan": 2,
    "prd": 1,
    "exec": 6,
    "verify": 3,
    "fix": 2
}

# 工作窃取队列：空闲 Worker 从全局就绪队列偷取任务
# 就绪条件：所有上游依赖完成 + 资源可用
```

---

**文档版本**：v1.0.0　**最后更新**：2026-08-08