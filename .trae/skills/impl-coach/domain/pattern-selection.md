---
name: "pattern-selection"
description: "Design pattern selection and idiomatic usage: matching GoF patterns, architectural patterns, and code idioms to specific implementation scenarios with rationale documentation."
---

# 设计模式选型与惯用法（Pattern Selection & Idioms）

> 本文件为 `impl-coach` 模式选型与实现评审环节的详细内容参考。

## 1. 模式选型决策树

### 1.1 按场景分类

```
场景判断
├── 需要创建对象？
│   ├── 对象创建逻辑复杂 → Factory Method
│   ├── 需要创建一系列相关对象 → Abstract Factory
│   ├── 需要精确控制创建过程（如池化） → Builder
│   └── 确保全局唯一实例 → Singleton（慎用，优先 DI）
│
├── 需要组织对象结构？
│   ├── 需要统一树形结构处理 → Composite
│   ├── 需要动态添加职责 → Decorator
│   └── 需要统一不同接口的调用 → Adapter
│
├── 需要管理对象行为？
│   ├── 算法在运行时切换 → Strategy
│   ├── 需要在操作前后附加行为 → Chain of Responsibility / Decorator
│   ├── 需要通知多个对象 → Observer
│   ├── 需要将复杂操作封装为简单接口 → Command
│   └── 需要控制对昂贵对象的访问 → Proxy
│
└── 需要管理状态？
    ├── 对象行为随状态改变 → State
    └── 需要保证状态转换一致性 → State + 状态机
```

### 1.2 架构级模式匹配

| 架构需求 | 推荐模式 | 适用条件 | 反模式警告 |
|---------|---------|---------|-----------|
| 分层解耦 | **依赖注入（DI）** | 所有层间依赖 | 手动 new 上层对象 |
| 事件驱动 | **发布-订阅 / Observer** | 异步通知、事件溯源 | 同步轮询状态 |
| 数据访问抽象 | **Repository** | 持久化层抽象 | Controller 直接写 SQL |
| 业务逻辑封装 | **Service Layer + Unit of Work** | 事务边界管理 | 业务逻辑散落在 Controller |
| 外部集成 | **Adapter / Anti-Corruption Layer** | 第三方 API 对接 | 直接耦合外部 SDK 类型 |
| 横切关注点 | **Decorator / Middleware** | 日志、认证、限流 | 每个方法手写日志 |
| 领域建模 | **Entity + Value Object** | 有业务含义的概念 | 全部用 dict/Map 表示 |
| 命令处理 | **Command + Handler** | CQRS / 复杂命令 | 一个函数做所有事 |

## 2. 模式选型记录模板

每次模式选型必须记录以下信息：

```markdown
### 模式选型记录

- **日期**：YYYY-MM-DD
- **模块**：模块名称
- **场景描述**：具体要实现的功能场景
- **候选模式**：
  1. 模式 A —— 优势 / 劣势
  2. 模式 B —— 优势 / 劣势
- **选定模式**：模式 X
- **选型理由**：为什么选 X 而不选 Y/Z
- **架构约束**：对应架构/ADR 的哪条约束
- **代码示例**：关键接口/类的骨架
```

## 3. 常用模式惯用法速查

### 3.1 Strategy（策略模式）

**适用场景**：同一操作有多种实现算法，需运行时切换。

```python
# 接口定义
class PricingStrategy(Protocol):
    def calculate(self, order: Order) -> Decimal: ...

# 具体策略
class RegularPricing:
    def calculate(self, order: Order) -> Decimal:
        return order.subtotal * Decimal("1.0")

class VipPricing:
    def calculate(self, order: Order) -> Decimal:
        return order.subtotal * Decimal("0.85")

# 上下文——通过注入使用策略
class OrderService:
    def __init__(self, pricing: PricingStrategy):
        self._pricing = pricing
```

**选型信号**：看到 `if/elif` 按类型分支处理不同逻辑时，考虑 Strategy。

### 3.2 Repository（仓储模式）

**适用场景**：隔离数据访问逻辑，提供集合式的领域对象访问。

```python
# 接口——定义在业务层
class OrderRepository(Protocol):
    async def get_by_id(self, order_id: str) -> Order | None: ...
    async def save(self, order: Order) -> None: ...
    async def find_by_customer(self, customer_id: str) -> list[Order]: ...

# 实现——定义在数据层
class PostgreSQLOrderRepository:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get_by_id(self, order_id: str) -> Order | None:
        row = await self._pool.fetchrow(
            "SELECT * FROM orders WHERE id = $1", order_id
        )
        return Order.from_row(row) if row else None
```

**选型信号**：架构要求数据层可替换（如测试时用内存实现）。

### 3.3 Observer / 发布-订阅

**适用场景**：一个事件需要触发多个独立处理逻辑。

```python
# 事件定义
@dataclass
class OrderCreatedEvent:
    order_id: str
    customer_id: str
    amount: Decimal
    timestamp: datetime

# 事件总线接口
class EventBus(Protocol):
    async def publish(self, event: Any) -> None: ...
    def subscribe(self, event_type: type, handler: Callable) -> None: ...

# 订阅者——各自独立处理
class InventoryHandler:
    async def on_order_created(self, event: OrderCreatedEvent) -> None:
        await self._reserve_stock(event.order_id, event.items)

class NotificationHandler:
    async def on_order_created(self, event: OrderCreatedEvent) -> None:
        await self._send_confirmation(event.customer_id, event.order_id)
```

**选型信号**：ADR 要求事件溯源、或架构图中有异步消息流。

### 3.4 Decorator / Middleware

**适用场景**：横切关注点（日志、认证、限流）需统一处理。

```python
# 中间件模式——FastAPI 示例
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration:.3f}s)")
    return response
```

**选型信号**：多个模块有相同的样板代码（如每个接口都手写日志和异常处理）。

## 4. 反模式检查清单

实现评审时检查以下反模式：

| 反模式 | 症状 | 修正方向 |
|--------|------|---------|
| **God Object** | 一个类/文件超 500 行、职责过多 | 拆分为多个单一职责类 |
| **Service Locator** | 运行时动态查找依赖 | 改为构造器注入 |
| **Anemic Domain** | 领域对象只有 getter/setter 无行为 | 将业务逻辑移入领域对象 |
| **Leaky Abstraction** | 抽象层暴露了底层实现细节 | 隐藏实现细节，接口只暴露业务语义 |
| **Golden Hammer** | 所有场景都用同一个模式 | 按场景选型，不预设模式 |
| **Premature Optimization** | 过早引入复杂模式"以防未来" | YAGNI——只在需求出现时引入 |
| **Copy-Paste Inheritance** | 通过复制代码而非继承/组合复用 | 提取公共逻辑为基类或工具类 |

---

**文档版本**：v1.0.0 **最后更新**：2026-09-07
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
