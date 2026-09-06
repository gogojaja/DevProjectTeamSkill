"""agent_runtime — 智能体运行时（Phase A 事件驱动中枢）

将现有孤立工具（agent_loop / memory_store / self_heal / quality_gate）
通过事件总线 + 决策引擎连接为自主控制环。

核心模块：
  - event_bus:          事件发布-订阅 + JSONL 持久化
  - decision_engine:    模式匹配决策 + 自动/手动执行
  - agent_loop_v2:      事件驱动主循环（兼容 v1 行为）
  - scheduled_tasks:    定时任务注册（对接 dev-task-scheduler）
  - session_init:       会话启动简报（Phase B 预留接口）

铁律遵循：
  - #3  A 级凭据禁止写入事件/决策台账
  - #8  敏感信息脱敏后入台账
  - #12 运行时产物（40/41/42 台账）gitignore，不入库
  - #15 Tier3 高辐射操作保留 HITL 确认
"""

__version__ = "1.0.0"
__all__ = [
    "event_bus",
    "decision_engine",
    "agent_loop_v2",
    "scheduled_tasks",
    "session_init",
]
