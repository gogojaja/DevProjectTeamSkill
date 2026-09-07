---
name: "module-scaffold"
description: "Module scaffolding templates: generating compilable module skeletons with directory structure, interface stubs, configuration, and test placeholders for Python, TypeScript, and Go projects."
---

# 模块脚手架（Module Scaffold Templates）

> 本文件为 `impl-coach` 模块骨架生成环节的详细内容参考。

## 1. 脚手架生成流程

```
输入：模块名称 + 架构约束 + 技术栈
  │
  ├─ 1. 确定目录结构（按架构分层）
  ├─ 2. 生成接口定义文件（Protocol / Interface）
  ├─ 3. 生成实现桩文件（带 TODO 标记）
  ├─ 4. 生成 DTO / 数据模型文件
  ├─ 5. 生成测试桩文件
  └─ 6. 生成配置文件（如有需要）
  │
输出：可编译的最小模块骨架
```

## 2. Python 模块骨架（FastAPI / 分层架构）

### 2.1 标准目录结构

```
src/{module_name}/
├── __init__.py              # 包初始化，导出公共接口
├── interface.py             # 服务接口定义（Protocol）
├── service.py               # 业务逻辑实现
├── dto.py                   # 请求/响应数据传输对象
├── repository.py            # 数据访问接口
├── models.py                # 领域模型（可选，复杂业务时独立）
├── exceptions.py            # 模块专属异常定义
├── router.py                # API 路由（展示层入口）
└── tests/
    ├── __init__.py
    ├── conftest.py           # 测试 fixtures
    ├── test_service.py       # 业务逻辑测试
    ├── test_repository.py    # 数据访问测试（用 mock）
    └── test_router.py        # API 端点测试
```

### 2.2 骨架代码模板

**interface.py**（接口定义）：
```python
"""{module_name} 模块服务接口

架构约束：
- ADR-XXX: {架构决策描述}
- 依赖方向：本模块接口被 presentation 层依赖，本模块不依赖 presentation
"""
from typing import Protocol
from .dto import {Name}Request, {Name}Response


class {Name}Service(Protocol):
    """{模块名}服务接口"""

    async def create(self, request: {Name}Request) -> {Name}Response:
        """创建{实体名}"""
        ...

    async def get_by_id(self, id: str) -> {Name}Response | None:
        """按 ID 查询"""
        ...

    async def update(self, id: str, request: {Name}Request) -> {Name}Response:
        """更新{实体名}"""
        ...

    async def delete(self, id: str) -> None:
        """删除{实体名}"""
        ...
```

**service.py**（实现桩）：
```python
"""{module_name} 业务逻辑实现"""
from .interface import {Name}Service
from .dto import {Name}Request, {Name}Response
from .repository import {Name}Repository


class {Name}ServiceImpl:
    """{模块名}服务实现"""

    def __init__(self, repository: {Name}Repository):
        self._repository = repository

    async def create(self, request: {Name}Request) -> {Name}Response:
        # TODO: 实现业务逻辑
        raise NotImplementedError

    async def get_by_id(self, id: str) -> {Name}Response | None:
        # TODO: 实现业务逻辑
        raise NotImplementedError

    async def update(self, id: str, request: {Name}Request) -> {Name}Response:
        # TODO: 实现业务逻辑
        raise NotImplementedError

    async def delete(self, id: str) -> None:
        # TODO: 实现业务逻辑
        raise NotImplementedError
```

**dto.py**（数据传输对象）：
```python
"""{module_name} 数据传输对象"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class {Name}Request:
    """创建/更新请求"""
    # TODO: 根据需求定义字段
    name: str
    description: Optional[str] = None


@dataclass
class {Name}Response:
    """查询响应"""
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
```

**repository.py**（数据访问接口）：
```python
"""{module_name} 数据访问接口

架构约束：本接口定义在业务层，实现在数据层
"""
from typing import Protocol
from .dto import {Name}Response


class {Name}Repository(Protocol):
    """{模块名}仓储接口"""

    async def save(self, entity: {Name}Response) -> None: ...
    async def get_by_id(self, id: str) -> {Name}Response | None: ...
    async def delete(self, id: str) -> None: ...
```

**exceptions.py**（异常定义）：
```python
"""{module_name} 模块异常"""


class {Name}NotFoundError(Exception):
    """{实体名}不存在"""
    def __init__(self, id: str):
        self.id = id
        super().__init__(f"{Name} not found: {id}")


class {Name}ValidationError(Exception):
    """{实体名}校验失败"""
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Validation error on {field}: {message}")
```

**router.py**（API 路由）：
```python
"""{module_name} API 路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from .interface import {Name}Service
from .dto import {Name}Request, {Name}Response

router = APIRouter()


@router.post("/", response_model={Name}Response, status_code=status.HTTP_201_CREATED)
async def create(
    request: {Name}Request,
    service: {Name}Service = Depends(),  # 通过 DI 注入
):
    return await service.create(request)


@router.get("/{id}", response_model={Name}Response)
async def get_by_id(
    id: str,
    service: {Name}Service = Depends(),
):
    result = await service.get_by_id(id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"{Name} not found")
    return result
```

**tests/conftest.py**（测试 fixtures）：
```python
"""测试公共 fixtures"""
import pytest
from unittest.mock import AsyncMock
from ..service import {Name}ServiceImpl
from ..repository import {Name}Repository


@pytest.fixture
def mock_repository() -> AsyncMock:
    """模拟仓储——测试时替代真实数据库"""
    return AsyncMock(spec={Name}Repository)


@pytest.fixture
def service(mock_repository) -> {Name}ServiceImpl:
    """被测服务——注入模拟仓储"""
    return {Name}ServiceImpl(repository=mock_repository)
```

## 3. TypeScript 模块骨架（Express / NestJS 风格）

### 3.1 标准目录结构

```
src/{module-name}/
├── index.ts                 # 模块入口，导出公共接口
├── {name}.interface.ts      # 接口/类型定义
├── {name}.service.ts        # 业务逻辑实现
├── {name}.dto.ts            # DTO 定义
├── {name}.repository.ts     # 数据访问接口
├── {name}.controller.ts     # 路由控制器
├── {name}.exceptions.ts     # 异常定义
└── __tests__/
    ├── {name}.service.spec.ts
    └── {name}.controller.spec.ts
```

### 3.2 骨架代码模板

**{name}.interface.ts**：
```typescript
// {module-name} 模块接口定义
// 架构约束：ADR-XXX

export interface I{Name}Service {
  create(request: Create{Name}Dto): Promise<{Name}Response>;
  getById(id: string): Promise<{Name}Response | null>;
  update(id: string, request: Update{Name}Dto): Promise<{Name}Response>;
  delete(id: string): Promise<void>;
}

export interface I{Name}Repository {
  save(entity: {Name}Response): Promise<void>;
  getById(id: string): Promise<{Name}Response | null>;
  delete(id: string): Promise<void>;
}
```

## 4. 脚手架质量检查

生成的骨架必须通过以下检查：

| 检查项 | 要求 |
|--------|------|
| 可编译 | 骨架代码无语法错误，可被编译器/解释器接受 |
| 依赖方向 | import 方向符合架构分层约束 |
| 接口完整 | 所有 CRUD / 业务方法都有接口定义 |
| 测试可运行 | 测试文件可被发现（即使全部 skip/TODO） |
| 注释引用 | 关键接口注释引用了 ADR 编号 |
| 命名一致 | 文件名、类名、方法名与架构文档术语一致 |

## 5. 脚手架生成命令参考

```bash
# Python 项目——创建新模块
mkdir -p src/{module}/tests
touch src/{module}/__init__.py
touch src/{module}/interface.py
touch src/{module}/service.py
touch src/{module}/dto.py
touch src/{module}/repository.py
touch src/{module}/exceptions.py
touch src/{module}/router.py
touch src/{module}/tests/__init__.py
touch src/{module}/tests/conftest.py
touch src/{module}/tests/test_service.py

# TypeScript 项目——创建新模块
mkdir -p src/{module}/__tests__
touch src/{module}/index.ts
touch src/{module}/{name}.interface.ts
touch src/{module}/{name}.service.ts
touch src/{module}/{name}.dto.ts
touch src/{module}/{name}.repository.ts
touch src/{module}/{name}.controller.ts
touch src/{module}/{name}.exceptions.ts
touch src/{module}/__tests__/{name}.service.spec.ts
```

---

**文档版本**：v1.0.0 **最后更新**：2026-09-07
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
