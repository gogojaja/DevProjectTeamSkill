# ADR-006：TRAE Schedule 与 APScheduler 双层架构

## 状态

Accepted（已采纳）

## 上下文

TRAE 平台内置了 Schedule 工具，支持基于 cron 表达式创建定时任务，由 TRAE Agent 执行。但 TRAE Schedule 有局限性：
- 依赖 TRAE 运行时，TRAE 不运行时任务不执行
- 任务状态管理和可靠性依赖 TRAE
- 缺乏幂等、重试、死信等企业级特性
- 可观测性有限

候选方案：
- 方案A：完全基于 TRAE Schedule
- 方案B：完全基于 APScheduler，独立运行
- 方案C：TRAE Schedule 作为用户入口，APScheduler 作为执行引擎（双层架构）

## 决策

**采用方案C：TRAE Schedule + APScheduler 双层架构。**

- **TRAE Schedule**：作为用户交互入口，负责任务的创建、管理、可视化
- **APScheduler**：作为核心执行引擎，负责任务的可靠调度、幂等校验、重试、死信等

## 理由

### 1. 优势互补

| 维度 | TRAE Schedule | APScheduler | 组合后 |
|------|--------------|-------------|--------|
| 用户体验 | ⭐⭐⭐⭐⭐ 原生集成 | ⭐⭐ 需 CLI | ⭐⭐⭐⭐⭐ |
| 调度可靠性 | ⭐⭐ 依赖 TRAE | ⭐⭐⭐⭐⭐ 成熟稳定 | ⭐⭐⭐⭐⭐ |
| 幂等重试 | ⭐ 无 | ⭐⭐⭐⭐⭐ 完善 | ⭐⭐⭐⭐⭐ |
| 可观测性 | ⭐⭐ 基础 | ⭐⭐⭐⭐ 丰富 | ⭐⭐⭐⭐⭐ |
| AI 能力 | ⭐⭐⭐⭐⭐ Agent 执行 | ⭐ 纯脚本 | ⭐⭐⭐⭐⭐ |
| 离线运行 | ⭐ 需 TRAE 运行 | ⭐⭐⭐⭐⭐ 独立进程 | ⭐⭐⭐⭐⭐ |

### 2. 用户体验好

- 用户通过熟悉的 TRAE Schedule 界面管理任务
- 不需要学习新的工具和命令
- TRAE 的 AI 能力可以辅助任务创建和故障排查

### 3. 可靠性有保障

- APScheduler 作为后台守护进程独立运行
- 即使 TRAE 不运行，任务也能正常执行
- 完善的幂等、重试、死信机制保障任务可靠执行

### 4. 平滑降级

- 如果 APScheduler 不可用，TRAE Schedule 仍能直接执行任务（降级模式）
- 如果 TRAE Schedule 不可用，仍可通过 CLI 管理 APScheduler 任务
- 双层互为备份，提高整体可靠性

## 架构关系

```
用户
  ↓
TRAE Schedule（用户入口）
  ↓ 创建/管理
APScheduler（执行引擎）← 独立守护进程
  ↓ 执行
任务脚本 / AI Agent
```

### 同步机制

1. TRAE Schedule 创建任务 → 同步注册到 APScheduler
2. APScheduler 执行状态 → 同步回 TRAE Schedule 展示
3. 双向同步，保持状态一致

### 降级模式

- APScheduler 不可用时，TRAE Schedule 自己执行任务（可靠性降低）
- TRAE Schedule 不可用时，APScheduler 继续后台执行，CLI 管理

## 后果

### 正面
- 用户体验好，与 TRAE 生态深度集成
- 可靠性高，APScheduler 独立运行保障任务执行
- 功能完善，幂等、重试、死信等企业级特性
- 双层互为备份，降级可用

### 负面
- 两套调度系统增加了复杂度
- 需要维护双向同步机制
- 状态一致性需要特别处理

### 缓解措施
- APScheduler 作为 Single Source of Truth，TRAE Schedule 只是视图层
- 同步操作幂等，重复同步不产生副作用
- 定期对账，确保状态一致

## 替代方案

| 方案 | 拒绝原因 |
|------|---------|
| 完全基于 TRAE Schedule | 可靠性不足，缺乏企业级特性，依赖 TRAE 运行 |
| 完全基于 APScheduler | 用户体验差，与 TRAE 生态脱节，缺乏 AI 能力 |

## 备注

- 同步方向：TRAE Schedule → APScheduler（主），APScheduler → TRAE Schedule（状态回传）
- 一致性模型：最终一致性，允许短暂延迟
- 冲突解决：以 APScheduler 状态为准
