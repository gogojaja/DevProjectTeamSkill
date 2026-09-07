---
name: "architecture-to-code"
description: "Architecture-to-code translation: mapping C4 models, layer diagrams, and component boundaries to concrete code structures, directories, interfaces, and dependency rules."
---

# 架构到代码翻译（Architecture-to-Code Translation）

> 本文件为 `impl-coach` 架构解读与接口实现环节的详细内容参考。

## 1. C4 模型 → 代码映射

### 1.1 映射规则

| C4 层级 | 代码映射 | 产出物 |
|---------|---------|--------|
| **Context**（系统上下文） | 项目根目录、外部接口客户端/适配器 | 项目骨架、外部集成模块 |
| **Container**（容器） | 独立可部署单元 → 独立模块/包/服务 | 模块目录、Dockerfile、入口文件 |
| **Component**（组件） | 模块内的逻辑分组 → 包/命名空间 | 包目录、组件接口文件 |
| **Code**（代码） | 类/函数/接口实现 | 源代码文件 |

### 1.2 从 Container 到目录结构

**输入**：C4 Container 图（含容器名称、技术栈、职责描述）

**翻译步骤**：

1. **每个 Container → 一个顶层模块目录**
   ```
   # C4 Container 图示例
   Web App (React) → src/web/
   API Server (Python/FastAPI) → src/api/
   Database (PostgreSQL) → src/persistence/（或独立 migration/ 目录）
   Message Queue (Redis) → src/messaging/
   ```

2. **Container 间的依赖 → 模块间的 import 方向**
   - C4 图中 A → B 的依赖关系 = A 的代码 import B 的接口
   - 依赖方向必须与架构一致，反向依赖 = 架构违规

3. **Container 的技术栈 → 目录内的文件约定**
   ```
   Python Container → __init__.py + 子模块
   TypeScript Container → index.ts + 子模块
   Go Container → main.go + 包目录
   ```

### 1.3 从 Component 到包结构

**输入**：C4 Component 图（某容器内的组件划分）

**翻译步骤**：

1. **每个 Component → 一个包/目录**
   ```
   # 某 API Container 内的 Component
   AuthController → src/api/auth/
   UserService → src/api/users/
   OrderService → src/api/orders/
   NotificationService → src/api/notifications/
   ```

2. **Component 间的依赖 → 包间的 import 关系**
   - 同层组件可互相引用（需架构允许）
   - 下层组件不可引用上层（依赖倒置时需接口抽象）

3. **每个 Component 内部的标准文件结构**
   ```
   src/api/orders/
   ├── __init__.py          # 包初始化，导出公共接口
   ├── interface.py         # 接口定义（Protocol/ABC）
   ├── service.py           # 业务逻辑实现
   ├── dto.py               # 数据传输对象
   ├── repository.py        # 数据访问接口
   └── tests/
       ├── test_service.py
       └── test_repository.py
   ```

## 2. 分层架构 → 代码分层

### 2.1 经典三层映射

| 架构层 | 代码目录 | 职责 | 允许依赖 |
|--------|---------|------|---------|
| **Presentation**（展示层） | `controllers/` / `routes/` / `views/` | 接收请求、参数校验、调用 Service | Service 层接口 |
| **Business**（业务层） | `services/` / `usecases/` | 业务逻辑、事务管理、领域规则 | Repository 接口、Domain 模型 |
| **Data**（数据层） | `repositories/` / `dao/` / `persistence/` | 数据存取、ORM 映射、外部调用 | 无上层依赖 |

### 2.2 依赖方向强制规则

```
Presentation → Business → Data
     ↓            ↓
  Domain ←── Domain ←── Domain
```

- **向下依赖**：上层依赖下层的接口（面向接口编程）
- **Domain 居中**：领域模型被所有层引用，但不依赖任何层
- **禁止反向**：Data 层不可 import Service 层代码
- **跨层通信**：通过依赖注入，不通过直接实例化

### 2.3 接口契约翻译

**输入**：架构设计中的接口契约定义（API 规范、接口协议）

**翻译为代码**：

```python
# 架构契约：POST /api/v1/orders - 创建订单
# 翻译为接口定义

from typing import Protocol
from .dto import CreateOrderRequest, CreateOrderResponse

class OrderService(Protocol):
    """订单服务接口——源自架构契约"""
    async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse:
        """
        创建订单
        架构约束：幂等性由 request.idempotency_key 保证
        ADR-003：使用事件溯源模式记录订单状态变更
        """
        ...
```

**翻译检查清单**：

| 检查项 | 要求 |
|--------|------|
| 接口方法签名 | 与架构契约的输入/输出一致 |
| 异常定义 | 与架构错误码映射一致 |
| 约束注释 | ADR 编号和架构约束写在 docstring 中 |
| 版本标记 | 接口版本与 API 版本一致 |

## 3. 依赖方向验证

### 3.1 静态检查方法

```bash
# Python 示例：使用 import-linter 检查依赖方向
# .importlinter 配置
[importlinter]
root_packages = src

[importlinter:contract:layers]
name = Layer Architecture
type = layers
layers = src.presentation | src.business | src.data
containers = src
```

### 3.2 架构违规判定

| 违规类型 | 示例 | 严重级别 |
|---------|------|---------|
| 反向依赖 | Data 层 import Service 层 | **阻断** |
| 跨层穿透 | Controller 直接 import Repository | **警告** |
| 循环依赖 | A import B, B import A | **阻断** |
| 隐式依赖 | 通过全局变量/单例跨层通信 | **警告** |

---

**文档版本**：v1.0.0 **最后更新**：2026-09-07
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
