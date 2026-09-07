---
name: "adr-to-code"
description: "ADR-to-code translation: converting Architecture Decision Records into concrete code structures, constraints, and implementation patterns with full traceability."
---

# ADR 落地指南（ADR-to-Code Translation）

> 本文件为 `impl-coach` ADR 落地环节的详细内容参考。

## 1. ADR → 代码翻译流程

### 1.1 翻译步骤

```
ADR 文档
  │
  ├─ 1. 提取决策：ADR 的 "Decision" 部分
  │     └→ 确定代码中需要体现的结构约束
  │
  ├─ 2. 提取约束：ADR 的 "Consequences" 部分
  │     └→ 确定代码中的强制规则和禁止项
  │
  ├─ 3. 提取上下文：ADR 的 "Context" 部分
  │     └→ 确定代码实现的前提条件
  │
  └─ 4. 生成映射：ADR 编号 → 代码位置 → 实现方式
        └→ 形成追溯表
```

### 1.2 翻译模板

对每条 ADR，填写以下映射表：

| ADR 字段 | 翻译目标 | 代码体现 |
|---------|---------|---------|
| **Decision**（决策） | 代码结构/模式选择 | 接口定义、类结构、目录组织 |
| **Consequences**（后果） | 代码约束/规则 | 注释、断言、Linter 规则 |
| **Context**（上下文） | 实现前提 | 配置项、环境要求 |
| **Status**（状态） | 实现状态 | 追溯表标记 |

## 2. 常见 ADR 类型与代码映射

### 2.1 技术选型类 ADR

**示例 ADR-001**：
> **决策**：API 框架选用 FastAPI，不使用 Flask。
> **理由**：原生异步支持、自动 OpenAPI 文档、类型安全。

**代码映射**：

```python
# 1. 项目依赖锁定（pyproject.toml / requirements.txt）
# fastapi>=0.100.0,<1.0.0
# uvicorn[standard]>=0.23.0

# 2. 应用入口结构
from fastapi import FastAPI
from .routers import orders, users, health

app = FastAPI(
    title="OrderService",
    version="1.0.0",  # 与架构基线版本一致
)

# 3. 路由注册——每个路由文件对应架构 Component
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
```

**追溯记录**：
```csv
ADR编号,决策摘要,代码位置,实现方式,状态
ADR-001,API框架选用FastAPI,src/api/main.py,FastAPI app 实例 + 路由注册,已实现
ADR-001,API框架选用FastAPI,pyproject.toml,fastapi 依赖锁定,已实现
```

### 2.2 架构风格类 ADR

**示例 ADR-002**：
> **决策**：采用分层架构，严格三层隔离（Presentation / Business / Data），通过依赖注入解耦。

**代码映射**：

```python
# 1. 目录结构——强制三层分离
# src/
# ├── presentation/    # 展示层：路由、请求/响应模型
# ├── business/        # 业务层：服务接口与实现、领域模型
# └── data/            # 数据层：仓储实现、ORM 模型

# 2. 依赖注入——使用 Depends 实现解耦
from fastapi import Depends
from ..business.service import OrderService
from ..data.repository import PostgreSQLOrderRepository

# 数据层实例化（在组装点/Composition Root 统一配置）
def get_order_repository() -> OrderRepository:
    return PostgreSQLOrderRepository(pool=db_pool)

def get_order_service(
    repo: OrderRepository = Depends(get_order_repository)
) -> OrderService:
    return OrderService(repository=repo)

# 展示层——只依赖业务层接口
@router.post("/orders")
async def create_order(
    request: CreateOrderRequest,
    service: OrderService = Depends(get_order_service),
):
    return await service.create_order(request)
```

**追溯记录**：
```csv
ADR编号,决策摘要,代码位置,实现方式,状态
ADR-002,分层架构+依赖注入,src/presentation/,Router 通过 Depends 注入 Service,已实现
ADR-002,分层架构+依赖注入,src/business/,Service 依赖 Repository 接口,已实现
ADR-002,分层架构+依赖注入,src/data/,Repository 实现数据存取,已实现
```

### 2.3 安全策略类 ADR

**示例 ADR-005**：
> **决策**：所有 API 端点使用 JWT Bearer Token 认证，Token 有效期 30 分钟。

**代码映射**：

```python
# 1. 认证中间件——统一在应用层处理
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    token = credentials.credentials
    payload = decode_jwt(token)  # 解码 + 过期验证
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return User(id=payload["sub"], role=payload["role"])

# 2. 端点使用——声明式认证
@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    user: User = Depends(get_current_user),  # ADR-005 认证要求
    service: OrderService = Depends(get_order_service),
):
    return await service.get_order(order_id, user_id=user.id)
```

## 3. ADR 追溯矩阵

### 3.1 矩阵模板

| ADR 编号 | 决策摘要 | 影响模块 | 代码位置 | 实现状态 | 验证方式 |
|---------|---------|---------|---------|---------|---------|
| ADR-001 | API 框架 FastAPI | api | `src/api/` | ✅ 已实现 | 启动验证 |
| ADR-002 | 分层架构 | 全部 | `src/*/` | ✅ 已实现 | import-linter |
| ADR-003 | 事件溯源 | orders | `src/api/orders/events.py` | 🔲 未实现 | 测试覆盖 |
| ADR-005 | JWT 认证 | api | `src/api/auth/` | ✅ 已实现 | 集成测试 |

### 3.2 追溯检查规则

1. **每条 ADR 至少有一个代码位置映射**——无映射 = 未落地
2. **代码中的架构约束注释必须引用 ADR 编号**——如 `# ADR-003: 使用事件溯源`
3. **实现状态必须与 ADR Status 一致**——ADR 已批准 = 代码必须实现
4. **验证方式必须可执行**——不能仅写"人工检查"，需有自动化手段

## 4. 实现评审检查清单

对已实现的代码进行 ADR 合规评审：

- [ ] 每条已批准的 ADR 都有对应的代码实现
- [ ] 代码中的关键决策处有 ADR 编号注释
- [ ] 代码结构符合 ADR 描述的架构约束
- [ ] 无 ADR 已明确禁止的实现方式
- [ ] 追溯矩阵已更新到最新状态
- [ ] 实现方式与 ADR 描述一致（非仅形式上满足）

---

**文档版本**：v1.0.0 **最后更新**：2026-09-07
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
