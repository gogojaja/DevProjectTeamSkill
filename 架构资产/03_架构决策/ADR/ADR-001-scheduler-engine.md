# ADR-001：选择 APScheduler 作为核心调度引擎

## 状态

Accepted（已采纳）

## 上下文

定时任务系统需要一个可靠的调度引擎来支持 cron、interval、date 等多种触发器模式。候选方案包括：
- 方案A：Python APScheduler
- 方案B：系统 cron + 脚本
- 方案C：Celery Beat + Redis
- 方案D：Apache Airflow
- 方案E：自研调度器

本项目的约束条件：
1. Python 技术栈，与现有工具链一致
2. 跨平台支持（macOS / Linux / Windows）
3. 轻量、低资源消耗
4. 单机运行，不需要分布式调度
5. 零外部服务依赖

## 决策

**选择 APScheduler 3.x 作为核心调度引擎。**

## 理由

1. **Python 生态最成熟**：APScheduler 是 Python 生态中最成熟、最广泛使用的任务调度库，文档完善，社区活跃
2. **功能全面**：支持 cron / interval / date 三种触发器，支持 misfire 处理、并发控制、任务持久化
3. **跨平台好**：纯 Python 实现，macOS / Linux / Windows 三平台一致行为
4. **轻量零依赖**：核心库无外部依赖（除了可选的持久化后端），资源消耗低
5. **持久化支持**：支持 SQLite 等多种 JobStore，进程重启后任务状态可恢复
6. **可扩展性**：支持自定义触发器、自定义执行器、自定义 JobStore

## 后果

### 正面
- 开发效率高，无需从零实现调度逻辑
- 可靠性有保障，经过大量生产环境验证
- 功能丰富，可满足当前和未来一段时间的需求
- 社区支持好，问题可快速找到解决方案

### 负面
- 单进程架构，调度器故障影响所有任务
- 不支持分布式多节点调度（当前不需要）
- 需要学习 APScheduler 的 API 和配置
- 监控能力需自建

## 替代方案

| 方案 | 拒绝原因 |
|------|---------|
| 系统 cron | Windows 兼容性差，状态管理和监控需完全自建 |
| Celery Beat + Redis | 依赖 Redis，架构较重，对本项目过度设计 |
| Apache Airflow | 架构最重，资源消耗大，部署复杂，严重过度设计 |
| 自研调度器 | 开发成本高，可靠性无保障，重复造轮子 |

## 备注

- 版本：APScheduler 3.x
- 持久化后端：SQLite
- 执行器：ThreadPoolExecutor（默认 10 线程）
