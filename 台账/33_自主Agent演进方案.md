# 自主 Agent 运行时演进方案

- 文档编号：PG-LOCAL-001-PLAN-001
- 归属项目群：PG-LOCAL-001（本机多项目协同）
- 版本：v1.1.0
- 最后更新：2026-08-18
- 状态：评审通过（条件签署），P1 执行中
- 知识产权所有：段波（验证邮箱：duanbo.douglas@163.com）

---

## 一、目标与原则

### 目标
在 opencode 宿主之上，把现有「多角色 PMO 方法论 + 治理脚手架」升级为**能自主驱动生命周期、并行派工、自愈、自改进**的 Agent 运行时。当前仓库本体是「给 Agent 用的技能库」，缺的是运行时与执行自主性。

### 原则
1. 不破坏现有 9 角色技能，仅增量扩展；
2. 所有新增工具跨平台（`py`/`python3`），可审计，token A 级（铁律 #3）；
3. 危险操作保留人机确认（HITL）：force-push、hosts 改写默认受 `--force-with-lease`+备份+台账保护；
4. 每阶段独立可交付、可回退；收尾跑 `solidify` + 双推 + 刷新交接文档。

---

## 二、架构蓝图（四层）

```
┌─ 控制环运行时 (Control Loop) ── 中枢：事件/定时驱动、阶段门禁、调度
├─ 多 Agent 运行时 (Dispatch) ─── 派生并行角色 worker + 消息总线
├─ 记忆服务 (Memory) ──────────── 结构化持久记忆，替代手工交接文档
├─ 执行 Agency + 自愈 (Actions/Self-Heal) ─ 直接调工具、探测并修复异常
└─ 质量门 (Quality Gate) ──────── PR 级自动多视角评审 + 自改进闭环
```

宿主（opencode）提供 LLM 推理与 `Task` 子 Agent 原语；本方案在其上叠加「运行时层」。

---

## 三、核心模块设计

1. **`tools/agent_loop.py`（控制环）**：接收触发（git hook / 定时 / 手动）→ 加载对应角色技能 → 跑门禁（version/closure/release）→ 全过则调 `mirror_push` 双推 → 写 `台账/34_控制环执行记录.csv` → 防递归自提交记录（`AGENT_LOOP_ACTIVE` 环境变量）。支持 `--dry-run`（只跑门禁+记录、不双推不提交，安全验证）与 `--trigger hook`。钩子 `.githooks/post-commit` 由根目录 `.agent-loop-enabled` 开关激活，默认 HITL 不开。
2. **`tools/memory_store.py` + project_memory 实例化**：把 `交接文档.md` 升级为结构化记忆（SQLite/JSONL，UTF-8 BOM 导出），会话启动自动恢复上下文、决策、待办。
3. **`tools/dispatch.py`（多 Agent）**：封装 opencode `Task` 派生并行角色 worker（如 arch/dev/test），用 `台账/35_任务消息总线.csv` 做 handoff；team-orchestration 由剧本升级为运行时。
4. **`tools/self_heal.py`（自愈）**：监听 push 拒绝/分叉 → 自动 `fetch+rebase+force-sync(mirror)`；监听 GitHub flapping → 自动 `github_ip_refresh --write-hosts`（需提权）。
5. **`tools/quality_gate.py`（质量门）**：PR/提交触发 `multi-perspective-validation` 五视角并行，结论写入 `台账/36_质量门记录.csv`，不达标阻断合并。

---

## 四、实施计划（Phase 0–5）

| 阶段 | 目标 | 交付物 | 验收标准 | 涉及文件 |
|------|------|--------|----------|----------|
| **P0 基础** | 已具备 | 门禁/镜像/TLS 探测 | 三端一致、双推可用 | 已完成 |
| **P1 控制环 MVP** | 提交即自动门禁+双推 | `tools/agent_loop.py`、`.githooks/post-commit`、`.agent-loop-enabled` 开关、`台账/34_控制环执行记录.csv`、配套单测 | 一次 commit（启用后）自动跑通三道门禁+双推并留痕；`--dry-run` 可安全验证；门禁未过不双推；含 `tests/test_agent_loop.py` | `tools/agent_loop.py`、`.githooks/`、`tests/`、`台账/34_*` |
| **P2 记忆服务** | 跨会话上下文自动恢复 | `tools/memory_store.py`、`project_memory` 实例化 | 新会话自动载入决策/待办，无需手工读交接文档 | `tools/memory_store.py`、`台账/`、`role-project-init` 衔接 |
| **P3 自愈** | Git 分叉/flapping 自动修复 | `tools/self_heal.py`、控制环挂载 | 复现本次分叉场景可全自动恢复 | `tools/self_heal.py`、`台账/34_*` |
| **P4 多 Agent 运行时** | 并行派工真实化 | `tools/dispatch.py`、`台账/35_任务消息总线.csv` | 单需求自动派生并行角色 worker 并汇总结论 | `tools/dispatch.py`、`台账/35_*`、`team-orchestration` |
| **P5 质量门+自改进** | PR 自动评审+技能自演进 | `tools/quality_gate.py`、`self_improve` 闭环 | 坏 PR 自动阻断 + 技能补丁被提议 | `tools/quality_gate.py`、`台账/36_*`、`self-improve` |

每阶段收尾均跑 `solidify` + 双推 + 刷新交接文档。

---

## 五、与现有仓库契合（落地约束）

- 新增文件放 `tools/`（跨平台 `.py`，`py`/`python3` 双调）；台账放 `台账/`（UTF-8 BOM，禁 `.xlsx`）。
- 新技能在 `.trae/skills/` 单源，更新 `SKILL_INDEX.md` + `references/api_contracts.md`；版本号同步（version-consistency 门禁）。
- Token 一律 A 级（`load_secret` + `--write-hosts` 提权留痕 `13_安全审计台账.csv`/`14_授权登记.csv`）；hosts/系统文件改动走铁律 #7。
- 危险操作（force-push、hosts 改写）默认 HITL，仅控制环在 lease/备份保护下自动执行。
- 复用既有：`mirror_push.py`（双推）、`github_ip_refresh.py`（TLS 探测）、`load_secret.py`（凭据）、三道门禁脚本。

---

## 六、度量与里程碑

- **M1（P1 末）**：提交→门禁→双推 全自动，人工介入=0。
- **M2（P2 末）**：跨会话上下文恢复准确率抽检达标。
- **M3（P3 末）**：本次 Git 分叉类故障 MTTR ≈ 0（自动愈合）。
- **M4（P4 末）**：单需求并行角色派工可用。
- **M5（P5 末）**：PR 质量门自动阻断 + 自改进提案闭环。

---

## 七、风险与缓解

| 风险 | 缓解 |
|------|------|
| 宿主能力依赖（子 Agent 依赖 opencode `Task` 原语） | P4 先做可行性探针 |
| 自动执行误伤（force-push/hosts 改写） | `--force-with-lease` + 备份 + 台账留痕 |
| 令牌泄露 | 沿用 `load_secret`，禁止入仓，定期轮换 |
| 范围蔓延 | 每 Phase 独立可交付，先 P1 验证中枢再扩展 |

---

## 八、评审结论（五视角，2026-08-18）

决策：**条件签署（CHANGES_REQUESTED → 可接受风险），可进入 P1**；非阻塞改进项已纳入 v1.1.0 方案（见第九节）。

| 视角 | 结论 | 关键发现 |
|------|------|----------|
| Architect | ✅ PASS | 四层架构清晰、边界明确、复用既有 tools 无接口冲突 |
| CodeReviewer | ✅ PASS | 分阶段可交付、验收清晰；建议每 Phase 的 tool 配单元测试 |
| SecurityReviewer | ✅ PASS | 令牌 A 级（load_secret/不入仓/轮换）、hosts 走铁律 #7、URL 脱敏均合规 |
| TestEngineer | ⚠️ CHANGES_REQUESTED | 每 Phase 有验收标准，但缺自动化验收脚本（P1 端到端触发、P3 分叉复现） |
| PerformanceEngineer | ✅ PASS | 门禁秒级、SQLite/JSONL 轻量；P4 需定并发上限与 token 预算 |

> 详细 check 级记录见 `台账/37_方案评审记录.csv`。

---

## 九、评审采纳与方案完善（v1.1.0）

针对第八节非阻塞项，方案完善如下，并在 P1 起落地：

1. **宿主依赖可行性探针（ARCH-002）**：P4 前先做 opencode `Task` 子 Agent 可行性探针（最小派生 worker→回传），验证宿主能力再扩 P4，降风险。
2. **每 Phase 工具配单元测试（CR-002 / TE-002）**：P1 起每个新增 `tools/*.py` 配套 `tests/test_*.py`，至少覆盖门禁编排、双推失败降级、台账写入与防递归自提交；P3 固化「制造分叉→自动 fetch+rebase+force-sync」复现测试。
3. **消息总线脱敏规范（SEC-003）**：P4 的 `台账/35_任务消息总线.csv` 明确禁止承载 A 级信息，上下文 handoff 仅传引用/脱敏摘要，token/凭据一律不落总线。
4. **并发与 token 预算（PERF-002）**：P4 定义并行 worker 上限（建议 ≤4）与单轮 token 预算（≤12000），避免宿主限流与成本失控。

P1 本次交付已落实项 2 的测试骨架（`tests/test_agent_loop.py`）与 hook 安全开关（`.agent-loop-enabled`）。

---

## 十、实施进度（截至 2026-08-18）

| 阶段 | 状态 | 交付物 | 备注 |
|------|------|--------|------|
| **P0 基础** | ✅ 已完成（前序） | 门禁 / 镜像 / TLS 探测 | 三端一致、双推可用 |
| **P1 控制环 MVP** | ✅ 已完成 | `tools/agent_loop.py` + `.githooks/post-commit` + `台账/34_控制环执行记录.csv` + 单测 | 三道门禁全过自动双推；hook 默认关闭（HITL），建 `.agent-loop-enabled` 即激活 |
| **P2 记忆服务** | ✅ 已完成 | `tools/memory_store.py` + `台账/38_项目记忆.jsonl` + 单测 | 跨会话决策/待办/风险结构化记忆，UTF-8 BOM 导出 |
| **P3 自愈** | ✅ 已完成 | `tools/self_heal.py` + 单测 | 分叉自动 fetch+rebase+`--force-with-lease`（强制前备份）+ GitHub 探测修复 |
| **P4 多 Agent 运行时** | ✅ 脚手架完成 | `tools/dispatch.py` + `台账/35_任务消息总线.csv` + 单测 | 任务登记/状态流转/派工指令；真实 worker 派工依赖宿主 `Task` 原语（ARCH-002 可行性已验证可行） |
| **P5 质量门 + 自改进** | ✅ 脚手架完成 | `tools/quality_gate.py` + `台账/36_质量门记录.csv` + 单测 | Architect/CodeReviewer 由既有 check 脚本代理；Security/Test/Performance 标记「待宿主 LLM」（host seam） |

**收尾状态**：
- 全部新增 `tools/*.py` 配 `tests/test_*.py`，单测全过；version/closure/release 三道门禁全绿。
- 提交已双推至 Gitee（mirror）；GitHub（origin）因访问 flapping 偶发滞后，恢复后由 `mirror_push`/`self_heal` 补齐。
- 待办：①轮换已在对话明文暴露的 Gitee token（A 级）；②清理工作树中前序遗留的未提交改动（含 `role-mgmt-consulting` 等）；③激活控制环自动双推（建 `.agent-loop-enabled`）。
