# EVAL-2026-09-01-001：dev-deploy-tools 独立化评估

> **评估日期**：2026-09-01
> **评估对象**：dev-deploy-tools（部署工具集，当前以 `role-deployment/domain/deploy-toolkit.md` 技能形态维护）
> **立项背景**：项目群规划 v3.0 Phase 3，评分 86/100，采用「先技能后评估」决策（评分中等偏高，先技能化运行，3个月后评估独立化）
> **评估结论**：❌ **不独立化**（0/3 判据满足），继续技能形态维护

---

## 一、评估三判据（定义于 deploy-toolkit.md §5）

### 判据 1：部署工具代码量 >2000 行且与本库发布流程解耦

| 指标 | 实测 | 判定 |
|------|------|------|
| 代码量 | 1963 行（solidify/publish_production/deploy_skills/mirror_push/package_skills/nightly_quality_gate 共 10 个文件） | 接近阈值但未超 |
| 解耦度 | 紧耦合：solidify→deploy_skills 调用、publish_production 独占全局库发布、mirror_push 绑定双推策略 | ❌ 未解耦 |

**结论**：❌ 不满足。工具集与技能库发布流程一体化，剥离成本高、收益低。

### 判据 2：≥3 个外部项目需要复用部署工具链

| 项目 | 实际引用 | 说明 |
|------|----------|------|
| dev-project-mgmt | 0 | 仅章程方法论层面提及「发布」 |
| dev-security-tools | 0 | 同上 |
| dev-test-tools | 0 | 同上 |

**实测**：0/3 项目有实际复用需求。

**结论**：❌ 不满足。外部项目均独立维护各自发布流程，无共享工具链需求。

### 判据 3：工具演进节奏与技能库发布节奏冲突

| 指标 | 实测 | 判定 |
|------|------|------|
| 近1月部署工具相关提交 | 37 次 | — |
| 近1月全库提交 | 400 次 | — |
| 占比 | 9.25% | 节奏温和 |

**结论**：❌ 不满足。演进节奏与技能库发布无冲突，无独立仓库诉求。

---

## 二、评估结论

**不独立化**。理由：
1. 三判据均未满足（0/3）
2. 技能形态运行正常：deploy-toolkit.md 提供脚本规范/检查清单/回滚演练方法论，工具实现在本库 tools/ 稳定演进
3. 剥离成本 > 收益：解耦需重构 solidify/publish_production 调用链，且无外部复用需求支撑

## 三、复评条件（满足任一即重新评估）

1. ≥3 个外部项目产生实际复用需求（引用计数 >0）
2. 部署工具代码量 >2000 行 且 与发布流程解耦方案可行
3. 工具演进节奏与技能库发布节奏出现实质冲突（如发布阻塞）

## 四、证据锚点

- 代码量统计：`wc -l tools/{solidify,publish_production,deploy_skills,mirror_push,package_skills,nightly_quality_gate}.{py,sh}` = 1963
- 外部引用：`grep -rl "solidify|publish_production|mirror_push|deploy_skills" dev-{project-mgmt,security-tools,test-tools}` = 0 命中
- 演进频率：`git log --oneline --since=2026-08-01` 统计

---

**评估人**：douglas + AI 助手（百炼 Qwen3.8-Max，S3 治理决策档）
**关联文档**：`docs/项目群整体规划方案_v3.0.md` Phase 4-1 · `role-deployment/domain/deploy-toolkit.md` §5
