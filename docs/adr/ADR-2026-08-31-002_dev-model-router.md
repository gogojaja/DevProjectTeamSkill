# ADR-2026-08-31-002：多模型分层编排工具独立化

> **状态**：待架构角色正式编号
> **决策者**：孵化器（incubator-initiation v1.0.0）
> **日期**：2026-08-31
> **关联**：INC-2026-08-31-002

---

## 背景

AI 编码领域最前沿的架构模式是多模型分层协作：高阶模型拆解任务→低阶模型执行子任务→高阶模型组装调试。本仓库已有 team-orchestration + best-practice-solution + multi-perspective-validation 三大技能可复用，需要评估：独立项目 vs 内嵌实现。

## 决策

将多模型分层编排能力独立为 `dev-model-router` 项目，本仓库保留薄封装代理。

## 选项

| 选项 | 描述 | 结论 |
|------|------|------|
| A. **独立为 dev-model-router** | Router + DAG + Executor 三层架构 | ✅ 三判据全命中 |
| B. 内嵌为 team-orchestration 扩展 | 扩展现有技能 | ❌ 3,477 行非核心代码膨胀 |
| C. 用 LangChain/CrewAI | 外部框架组合 | ❌ 外部依赖重，与本仓库不兼容 |

## 理由

1. **三判据全命中**：
   - 复用率：多模型编排是 AI 编码核心能力，跨项目复用
   - 独立性：Router + DAG + Executor 三层可独立解释
   - 维护成本：独立后自管理，减少技能库膨胀

2. **可行性五维全高**：
   - 技术：行业实践成熟（T1 证据链）+ 本仓库已有三大技能可复用
   - 经济：开源免费，可复用现有资产
   - 合规：遵循铁律 #8（敏感信息分级）
   - 资源：单人可维护
   - 时间：基于现有资产扩展，预计 3-5 天

3. **行业实践验证**：
   - Model Cascading（emergentmind.com 2026）
   - Task Decomposition DAGs（Yu 2026）
   - Stagewise Model Selection（Chen et al. 2025）
   - gstack+ 三层编排（T1 webfetch 核验）

## 已验证

| 证据 | 来源 | access_date |
|------|------|-------------|
| gstack+ 三层编排 | webfetch T1 | 2026-08-31 |
| 本仓库三大技能 | 本库 T1 | 2026-08-31 |
| Model Cascading 模式 | recalled T1 | 2026-08-31 |

## 不确定

| 项目 | 说明 |
|------|------|
| DistilBERT 分类器训练数据来源 | 先用关键词路由，后续渐进增强 |

## 未关闭风险

| 风险 | 严重度 | 处理 |
|------|--------|------|
| DistilBERT 分类器训练数据 | 中 | 先用关键词路由，后续渐进增强 |
| 模型 API 费用控制 | 中 | 预算强制机制（cost_optimizer.py） |

## 反信号

- 独立后无人维护 → 回收至本库
- 独立后调用率下降 → 保留本库薄封装即可

## 实施步骤

1. 创建 `dev-model-router` 独立仓库
2. 实现 Router 层（复杂度评估 + 模型选择）
3. 实现 Decomposer 层（DAG 构建 + 任务拆分）
4. 实现 Executor 层（分阶段执行 + 结果组装）
5. 本仓库保留薄封装代理
6. 更新 project-registry.md 登记

---

**最后更新**：2026-08-31（初始草案）
**孵化器**：incubator-initiation v1.0.0
**评审**：🟢 SIGNED_OFF（3/3 视角全绿）
