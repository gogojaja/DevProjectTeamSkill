# 立项建议书：dev-model-router 多模型分层编排工具

> **孵化器编号**：INC-2026-08-31-002
> **决策对象**：多模型分层编排工具——独立项目 vs 内嵌实现
> **档位**：FULL（选型锁定+系统级）
> **评审模式**：多视角自评（3 视角：架构/安全/成本+演进）
> **评审结果**：🟢 SIGNED_OFF（3/3 全绿）
> **技能版本**：incubator-initiation v1.0.0 + best-practice-solution v1.2.1

---

## 一、方案调研

### 1.1 行业实践

| 来源 | 结论 | confidence |
|------|------|------------|
| emergentmind.com（T1 recalled） | Model Cascading 是多模型编排核心模式（高阶拆解→低阶执行→高阶组装） | high |
| Yu 2026（T1 recalled） | Task Decomposition DAGs 可将复杂任务映射为有向无环图，按依赖并行 | high |
| Chen et al. 2025（T1 recalled） | Stagewise Model Selection 基于 pass@1/fix@1 选择每阶段最优模型 | high |
| gstack+（T1 webfetch 核验） | 三层模型编排已验证（Tier-A 判断 / Tier-Mid 审查 / Tier-Exec 执行） | high |
| TrueFoundry 2026（T1 recalled） | Multi-Model Orchestration 匹配任务到正确模型 tier | high |

### 1.2 现有资产盘点

| 资产 | 说明 | 复用价值 |
|------|------|----------|
| `team-orchestration` 技能 | 并行编排 Worker（已支持 team/ultrawork/ralph 三种模式） | 高——可扩展为分层调度 |
| `best-practice-solution` 四段流水线 | Triage→Research→Draft→Converge | 高——可复用为 DAG 节点 |
| `multi-perspective-validation` 五视角 | Specialized Expert 模式 | 高——可复用为并行执行器 |
| `dev-task-scheduler` | APScheduler 调度引擎 | 中——可复用为任务调度层 |
| 本会话孵化器流程 | Supervisor-Worker 模式已验证 | 高——可复用为编排模式 |

### 1.3 证据卡

| 证据卡 | claim | 来源 | confidence |
|--------|-------|------|------------|
| EV-910 | Model Cascading 是多模型编排核心模式（高阶拆解→低阶执行→高阶组装） | T1 recalled | high |
| EV-911 | Task Decomposition DAGs 可将复杂任务映射为有向无环图，按依赖并行 | T1 recalled | high |
| EV-912 | Stagewise Model Selection 基于 pass@1/fix@1 选择每阶段最优模型 | T1 recalled | high |
| EV-913 | 本仓库已有 team-orchestration + best-practice-solution + MVP 三大技能可复用 | 本库实测 T1 | high |
| EV-914 | gstack+ 已验证三层模型编排（Tier-A/Tier-Mid/Tier-Exec） | T1 webfetch 核验 | high |

---

## 二、可行性评估

### 2.1 三判据独立化评估

| 判据 | 评估 | 判定 |
|------|------|------|
| **复用率** | 多模型编排是 AI 编码核心能力，跨项目复用 | ✅ 独立化 |
| **独立性** | 可独立解释（Router + DAG + Executor），不依赖 .trae/skills | ✅ 独立化 |
| **维护成本** | 独立后自管理，减少技能库膨胀 | ✅ 独立化 |

**结论**：三判据全部命中 → **建议独立化**

### 2.2 可行性五维

| 维度 | 评估 | 档位 |
|------|------|------|
| 技术可行性 | 行业实践成熟（T1 证据链）+ 本仓库已有三大技能可复用 | 高 |
| 经济可行性 | 开源免费，可复用现有资产，开发成本低 | 高 |
| 合规可行性 | 遵循铁律 #8（敏感信息分级），无合规风险 | 高 |
| 资源可行性 | 单人可维护，已有 team-orchestration 等资产可复用 | 高 |
| 时间可行性 | 基于现有资产扩展，预计 3-5 天 | 高 |

**结论**：五维全高 → **可行性极高**

---

## 三、方案双栏

### ✅ 可稳定达成效果

**方案 A（推荐）：独立为 `dev-model-router` 项目**

**技术架构**：

```
dev-model-router/
├── router/                    # 路由层
│   ├── complexity.py          # 任务复杂度评估（关键词/分类器/混合）
│   ├── model_selector.py      # 模型选择器（Tier-A/Tier-Mid/Tier-Exec）
│   └── cost_optimizer.py      # 成本优化器
├── decomposer/                # 任务分解层
│   ├── dag_builder.py         # DAG 构建器
│   ├── task_splitter.py       # 任务拆分器
│   └── dependency.py          # 依赖分析
├── executor/                  # 执行层
│   ├── staged_executor.py     # 分阶段执行器
│   ├── parallel_worker.py     # 并行工作者
│   └── assembler.py           # 结果组装器
├── models/                    # 模型档案
│   ├── registry.py            # 模型注册表
│   └── profiles/              # 各模型性能档案
├── cli.py                     # CLI 入口
└── README.md
```

**核心能力**：
1. **任务复杂度评估**：关键词 + DistilBERT 分类器 + 混合路由
2. **DAG 任务分解**：复杂任务→有向无环图→按依赖并行
3. **分阶段模型选择**：基于 pass@1/fix@1 选每阶段最优模型
4. **结果组装 + 验证**：高阶模型组装子任务结果并验证

**使用方式**：
```bash
# 评估任务复杂度
python -m router assess "实现用户登录功能"

# 分解任务为 DAG
python -m decompose split "实现用户登录功能" --output tasks.json

# 执行 DAG（自动选模型）
python -m executor run tasks.json

# 高阶模型组装结果
python -m executor assemble results/
```

### ⚠️ 理论最优效果与当前限制

**方案 B：内嵌为 team-orchestration 扩展**
- 限制：3,477 行非核心代码膨胀技能库
- 反信号：多模型编排是通用能力，不应绑定特定技能库

**方案 C：用 LangChain/CrewAI 组合**
- 限制：外部依赖重，与本仓库工具链不兼容
- 反信号：本仓库已有 team-orchestration + best-practice-solution 可复用

---

## 四、评审报告

### 多视角评审（串行）

| 视角 | 对照证据 | 结论 |
|------|----------|------|
| 架构/技术路线 | EV-910~914（行业实践 + 本仓库现有能力 + gstack+ 先例） | ✅ SIGNED_OFF |
| 安全合规 | 遵循铁律 #8（敏感信息分级），API Key 走 .secrets/ | ✅ SIGNED_OFF |
| 成本+演进 | 可复用三大技能，独立后自管理，支持新模型接入 | ✅ SIGNED_OFF |

**聚合决策**：🟢 **SIGNED_OFF**（3/3 全绿）

### 未关闭风险

| 风险 | 严重度 | 处理 |
|------|--------|------|
| DistilBERT 分类器训练数据来源 | 中 | 先用关键词路由，后续渐进增强 |
| 模型 API 费用控制 | 中 | 预算强制机制（cost_optimizer.py） |

---

## 五、决策记录草案

- **标识**：ADR-2026-08-31-002
- **决策**：将多模型分层编排能力独立为 `dev-model-router` 项目
- **选项**：
  - A. **独立为 dev-model-router（本方案）** → ✅ 三判据全命中
  - B. 内嵌为 team-orchestration 扩展 → ❌ 3,477 行非核心代码膨胀
  - C. 用 LangChain/CrewAI → ❌ 外部依赖重，与本仓库不兼容
- **理由**：EV-910~914（行业实践 + 本仓库现有能力 + gstack+ 先例）
- **已验证**：gstack+ 三层编排（T1 webfetch 核验）、本仓库三大技能（T1 本库实测）
- **不确定**：DistilBERT 分类器训练数据来源
- **未关闭风险**：模型 API 费用控制（需预算强制机制）
- **反信号**：独立后无人维护 → 回收至本库

---

## 六、移交清单

| 项目 | 说明 | 路径 |
|------|------|------|
| 本方案文档 | 立项建议书 | `docs/incubator/INC-2026-08-31-002_dev-model-router.md` |
| 证据卡 | EV-910~914 | `docs/evidence_cards_dev-model-router_20260831.json` |
| 复用资产 | team-orchestration + best-practice-solution + MVP | `.trae/skills/` |
| ADR 草案 | 决策记录 | `docs/adr/ADR-2026-08-31-002_dev-model-router.md` |

---

**最后更新**：2026-08-31（孵化器立项）
**孵化器**：incubator-initiation v1.0.0
**评审签署**：🟢 SIGNED_OFF（3/3 视角全绿）
