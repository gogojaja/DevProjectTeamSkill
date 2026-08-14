# multi_project_isolation.md — 多项目环境隔离最佳实践

> 跨项目并行开发环境隔离方案，涵盖 Git、语言运行时、数据库、配置文件、Docker 等多层次隔离。
> 适用于单机多项目开发场景，避免项目间互相干扰。
> 被 role-development / role-deployment / role-project-init / worktree-isolation 引用。

---

## 1. 隔离层次架构（4 层隔离）

```
┌─────────────────────────────────────────────────────────────┐
│  第 1 层：Git 仓库隔离（worktree）                            │
│  - 同仓库多分支并行                                          │
│  - PR/Issue 评审环境                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  第 2 层：语言运行时隔离（venv/conda）                        │
│  - Python venv, Node.js nvm, Java maven/gradle             │
│  - 依赖版本独立管理                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  第 3 层：服务与数据隔离（端口/数据库/缓存）                   │
│  - 不同端口（dev: 3000/8080, test: 4000/8081, prod: 8080）   │
│  - 数据库独立（不同端口/命名空间/实例）                       │
│  - 缓存隔离（Redis 独立实例）                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  第 4 层：配置与部署隔离（环境变量/Docker）                   │
│  - .env 文件隔离（dev/test/prod）                            │
│  - Docker Compose 多服务编排                                 │
│  - CI/CD 独立流水线                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  第 5 层：全局环境资产注册与冲突仲裁（跨项目横切）            │
│  - 每台服务器建立全局统一环境清单库（25_环境资源清单.csv）     │
│  - 端口/容器/数据库/大模型等独占资源统一注册、先注册先得       │
│  - 冲突升阶人工裁决 + change_audit 留痕                      │
│  - 本地工具/脚本缺省运行目标 = 本地轻量级大模型               │
└─────────────────────────────────────────────────────────────┘
```

> **第 5 层定位**：前三层解决「项目内部环境隔离」，第 5 层解决「多项目共享一台服务器的资源冲突」。4 层中**任何独占资源（端口/容器名/GPU/大模型容器/Docker 单一运行时）必须先注册后使用**，否则项目间必然互相干扰。

---

## 2. Git 仓库隔离（第 1 层）

### 2.1 Worktree 隔离（已有技能）

- **场景**：同仓库多分支并行开发、PR 评审
- **工具**：`git worktree`（已有 worktree-isolation 技能）
- **配置**：`~/.psm/worktrees/` 或自定义根目录

### 2.2 项目根目录命名规范

```
Workspace/
├── myproject-a/          # 项目 A
│   ├── .git/
│   ├── src/
│   ├── requirements.txt
│   └── .env.dev
├── myproject-b/          # 项目 B
│   ├── .git/
│   ├── src/
│   ├── package.json
│   └── .env.test
└── monorepo/             # 单体仓库（可选）
    ├── packages/
    │   ├── service-a/
    │   └── service-b/
    └── pnpm-workspace.yaml
```

**命名规则**：
- 项目名：小写+连字符（`my-project`）
- 避免缩写歧义（`api` → `api-service`）
- 单体仓库用 `monorepo` 前缀

### 2.3 分支命名规范

| 分支类型 | 命名模式 | 示例 |
|---------|---------|------|
| 主分支 | `main` / `master` | `main` |
| 开发分支 | `develop` | `develop` |
| 功能分支 | `feature/功能名` | `feature/user-auth` |
| 修复分支 | `fix/问题描述` | `fix/bug-123` |
| PR 评审 | `pr/编号-标题` | `pr/123-add-webhooks` |
| Hotfix | `hotfix/问题描述` | `hotfix/production-error` |

---

## 3. 语言运行时隔离（第 2 层）

### 3.1 Python venv 隔离

**项目级虚拟环境**：
```bash
# 每个项目独立 venv
myproject-a/
├── .venv/                # 独立 Python 环境
├── requirements.txt
└── src/

myproject-b/
├── .venv/                # 独立 Python 环境
├── requirements.txt
└── src/
```

**激活方式**：
```bash
# 项目 A
cd myproject-a
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 项目 B
cd myproject-b
source .venv/bin/activate
```

**环境变量注入**：
```bash
# .env.dev（项目级）
DATABASE_URL=postgresql://localhost:5432/myproject_a_dev
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev_secret_key

# .env.test（项目级）
DATABASE_URL=postgresql://localhost:5432/myproject_a_test
REDIS_URL=redis://localhost:6379/1
SECRET_KEY=test_secret_key
```

### 3.2 Node.js nvm 隔离

```bash
# 安装不同 Node 版本
nvm install 18
nvm use 18

# 项目 A（Node 18）
cd myproject-a
npm install
npm run dev

# 项目 B（Node 20）
nvm use 20
cd myproject-b
npm install
npm run dev
```

### 3.3 Java Maven/Gradle 隔离

**Maven**：
```xml
<!-- pom.xml -->
<properties>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <maven.compiler.source>17</maven.compiler.source>
    <maven.compiler.target>17</maven.compiler.target>
</properties>

<!-- 多环境配置 -->
profiles>
    <profile>
        <id>dev</id>
        <properties>
            <db.url>jdbc:postgresql://localhost:5432/myproject_a_dev</db.url>
        </properties>
    </profile>
    <profile>
        <id>prod</id>
        <properties>
            <db.url>jdbc:postgresql://prod-db:5432/myproject_a_prod</db.url>
        </properties>
    </profile>
</profiles>
```

**Gradle**：
```gradle
// build.gradle
def env = System.getProperty("env", "dev")
def dbUrl = env == "prod" ? "jdbc:postgresql://prod-db:5432/myproject_a_prod"
                      : "jdbc:postgresql://localhost:5432/myproject_a_${env}"

dependencies {
    runtimeOnly "org.postgresql:postgresql"
}

tasks.register("run") {
    doLast {
        exec {
            commandLine "java", "-jar", "build/libs/myproject-a.jar", env
        }
    }
}
```

---

## 4. 服务与数据隔离（第 3 层）

### 4.1 端口规划矩阵

| 服务类型 | dev 端口 | test 端口 | prod 端口 | 说明 |
|---------|---------|-----------|-----------|------|
| Web API | 3000 | 4000 | 8080 | 主服务 |
| Admin API | 3001 | 4001 | 8081 | 管理接口 |
| Database | 5432 | 5433 | 5432（集群） | PostgreSQL |
| Redis | 6379 | 6380 | 6379（集群） | 缓存 |
| Elasticsearch | 9200 | 9300 | 9200（集群） | 搜索 |
| RabbitMQ | 5672 | 5673 | 5672（集群） | 消息队列 |

**端口冲突检测脚本**：
```bash
#!/bin/bash
# check_ports.sh - 检查端口占用

PORTS=(3000 3001 4000 4001 5432 5433 6379 6380)
for port in "${PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $port is in use"
    else
        echo "✅ Port $port is free"
    fi
done
```

### 4.2 数据库隔离

**PostgreSQL 多实例**：
```bash
# 安装多个 PostgreSQL 实例
# dev 实例
pg_ctl -D /usr/local/var/postgres_dev start

# test 实例
pg_ctl -D /usr/local/var/postgres_test start

# 创建独立数据库
createdb -h localhost -p 5432 myproject_a_dev
createdb -h localhost -p 5433 myproject_a_test
```

**Docker 数据库**：
```yaml
# docker-compose.yml
version: '3.8'
services:
  db-dev:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: myproject_a_dev
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev123
    volumes:
      - pgdata-dev:/var/lib/postgresql/data

  db-test:
    image: postgres:15
    ports:
      - "5433:5432"
    environment:
      POSTGRES_DB: myproject_a_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test123
    volumes:
      - pgdata-test:/var/lib/postgresql/data

volumes:
  pgdata-dev:
  pgdata-test:
```

### 4.3 Redis 隔离

```bash
# 启动多个 Redis 实例
redis-server --port 6379 --daemonize yes --logfile redis-dev.log --dbfilename dump-dev.rdb
redis-server --port 6380 --daemonize yes --logfile redis-test.log --dbfilename dump-test.rdb
```

**Docker Redis**：
```yaml
services:
  redis-dev:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes

  redis-test:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    command: redis-server --appendonly yes
```

---

## 5. 配置与部署隔离（第 4 层）

### 5.1 环境变量隔离

**项目级 `.env` 文件结构**：
```
myproject-a/
├── .env.dev           # 开发环境
├── .env.test          # 测试环境
├── .env.staging       # 预发布环境
├── .env.prod          # 生产环境
├── .env.example       # 模板文件
└── .gitignore         # 忽略 .env*
```

**`.env.example` 模板**：
```env
# Database
DATABASE_URL=postgresql://localhost:5432/myproject_a_dev
REDIS_URL=redis://localhost:6379/0

# Application
APP_ENV=dev
APP_PORT=3000
DEBUG=true

# Secrets
SECRET_KEY=your_secret_key_here
JWT_SECRET=your_jwt_secret_here
```

**`.gitignore` 配置**：
```gitignore
# 环境变量文件
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*.so
.Python

# Node.js
node_modules/
npm-debug.log

# IDE
.vscode/
.idea/
*.swp
```

### 5.2 Docker Compose 多项目隔离

**`docker-compose.yml`（项目 A）**：
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://db:5432/myproject_a_dev
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: myproject_a_dev
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev123

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**`docker-compose.test.yml`（项目 A 测试环境）**：
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "4000:3000"  # 映射到不同端口
    environment:
      - DATABASE_URL=postgresql://db:5432/myproject_a_test
      - REDIS_URL=redis:6379/1

  db:
    image: postgres:15
    ports:
      - "5433:5432"
    environment:
      POSTGRES_DB: myproject_a_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test123
```

**启动不同环境**：
```bash
# 开发环境
docker-compose up -d

# 测试环境
docker-compose -f docker-compose.test.yml up -d
```

### 5.3 CI/CD 独立流水线

**GitHub Actions 示例**：
```yaml
# .github/workflows/api-dev.yml
name: API - Dev

on:
  push:
    branches: [develop]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: myproject_a_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test123
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/myproject_a_test
          REDIS_URL: redis://localhost:6379/1
        run: pytest

# .github/workflows/api-prod.yml
name: API - Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: |
          # 部署脚本
          ./scripts/deploy.sh
```

---

## 6. 目录结构最佳实践

### 6.1 项目标准目录结构

```
myproject-a/
├── .github/              # GitHub Actions
│   ├── workflows/
│   │   ├── dev.yml
│   │   └── prod.yml
├── .git/
├── .vscode/              # VSCode 配置
│   ├── settings.json
│   └── launch.json
├── .env.example          # 环境变量模板
├── .gitignore
├── .prettierrc           # 代码格式化
├── Dockerfile
├── docker-compose.yml
├── LICENSE
├── README.md
├── pyproject.toml        # Python 项目配置
├── requirements.txt      # Python 依赖
├── src/                  # 源代码
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── models/
│   └── services/
├── tests/                # 测试代码
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api.py
│   └── test_models.py
├── .venv/                # Python 虚拟环境（.gitignore）
├── .env.dev              # 开发环境变量（.gitignore）
├── .env.test             # 测试环境变量（.gitignore）
├── .env.staging          # 预发布环境变量（.gitignore）
└── .env.prod             # 生产环境变量（.gitignore）
```

### 6.2 多项目目录布局

```
Workspace/
├── personal/             # 个人项目
│   ├── myproject-a/
│   └── myproject-b/
├── work/                 # 工作项目
│   ├── project-alpha/
│   └── project-beta/
├── monorepo/             # 单体仓库
│   ├── packages/
│   │   ├── service-a/
│   │   ├── service-b/
│   │   └── shared/
│   ├── pnpm-workspace.yaml
│   └── package.json
└── shared/               # 共享工具
    ├── scripts/
    └── templates/
```

---

## 7. 隔离验证清单

### 7.1 Git 隔离检查
- [ ] 每个项目独立 `.git` 目录
- [ ] 分支命名规范统一
- [ ] Worktree 已配置（同仓库多分支）
- [ ] PR 评审使用独立 worktree

### 7.2 语言运行时隔离检查
- [ ] 每个项目独立 venv/Node 版本
- [ ] `requirements.txt` / `package.json` 独立
- [ ] 依赖版本锁定文件存在

### 7.3 服务与数据隔离检查
- [ ] 端口分配无冲突
- [ ] 数据库独立（不同端口/实例）
- [ ] Redis 独立实例
- [ ] 缓存隔离（不同数据库索引）

### 7.4 配置与部署隔离检查
- [ ] `.env` 文件按环境隔离
- [ ] `.gitignore` 包含 `.env*`
- [ ] Docker Compose 多服务编排
- [ ] CI/CD 流水线独立

### 7.5 目录结构检查
- [ ] 项目根目录命名规范
- [ ] 目录结构统一
- [ ] 共享工具独立存放

---

## 8. 常见问题与解决方案

### 8.1 端口冲突
**问题**：启动服务时报端口占用
```bash
# 查找占用端口的进程
lsof -i :3000  # Linux/macOS
netstat -ano | findstr :3000  # Windows

# 杀死进程
kill -9 <PID>
```

### 8.2 虚拟环境混乱
**问题**：激活错误的 venv
```bash
# 确认当前 Python 路径
which python  # Linux/macOS
where python  # Windows

# 确认虚拟环境路径
which python  # 在项目目录下运行
```

### 8.3 数据库连接错误
**问题**：连接到错误的数据库名称
```bash
# 检查当前数据库
\l  # PostgreSQL

# 切换数据库
\c myproject_a_dev

# 查看连接信息
SHOW port;
SHOW database;
```

### 8.4 Docker 容器冲突
**问题**：容器名重复
```yaml
# docker-compose.yml
services:
  api:
    container_name: myproject-a-api-dev  # 添加容器名前缀
```

---

## 9. 工具推荐

| 工具 | 用途 | 适用场景 |
|-----|------|---------|
| `git worktree` | Git 多分支隔离 | 同仓库多分支 |
| `nvm` | Node.js 版本隔离 | Node.js 项目 |
| `poetry` | Python 依赖管理 | Python 项目 |
| `docker-compose` | 服务编排隔离 | 微服务项目 |
| `docker` | 容器隔离 | 环境一致性 |
| `pm2` | Node.js 进程管理 | 生产环境 |
| `gunicorn` | WSGI 服务器 | Python API |
| `nginx` | 反向代理 | 生产环境 |
| `portainer` | Docker 管理界面 | 可视化管理 |
| `redis-cli` | Redis 管理 | Redis 隔离 |

---

## 10. 全局环境资产注册与冲突仲裁（第 5 层，横切层）

> 适用：多项目共享一台服务器（本地开发机/测试机/内网服务器）时，**任何独占资源必须先注册后使用**。
> 配套台账：`台账/25_环境资源清单.csv`（跨项目共享，按主机登记）。
> 建立时机：**项目启动阶段**（role-project-init `register_env_asset`），每次申请/释放资源同步更新，冲突升阶 `change_audit` 留痕。

### 10.1 全局统一环境清单库（CMDB-lite）

为每台服务器建立**全局统一的环境清单库**，统一注册、统一管理，避免各项目各记各账导致隐性冲突：

```
25_环境资源清单.csv（每台服务器一张，跨项目共享）
主机, 资源类型, 资源标识, 环境, 端口, 容器名, 模型名, 占用项目, 注册日期, 状态, 优先级, 备注
dev-server, 端口,    3000,   dev,  3000,  -,       -,       project-a, 2026-08-13, 已占用, 高,   Web API
dev-server, 容器,    api-a,  dev,  -,     api-a,   -,       project-a, 2026-08-13, 已占用, 高,   compose 项目名
dev-server, 容器,    api-b,  dev,  -,     api-b,   -,       project-b, 2026-08-13, 已占用, 高,   compose 项目名
dev-server, 大模型,  ollama, dev,  11434, -,       qwen2.5:7b, project-a, 2026-08-13, 已占用, 高, 单驻留 OLLAMA_MAX_LOADED_MODELS=1
```

**字段约定**：
- `主机`：服务器标识（唯一）；
- `资源类型`：`端口 / 容器 / 数据库 / 大模型 / 缓存 / GPU / 域名 / Docker 运行时` 等；
- `资源标识`：端口号 / 容器名 / 数据库名 / 模型名 / 挂载路径；
- `环境`：`dev` / `test` / `prod`；
- `占用项目`：当前占用者（空 = 空闲）；
- `状态`：`空闲 / 已占用 / 冲突 / 仲裁中 / 已释放`；
- `优先级`：`高/中/低`（高 = 独占资源，中 = 共享资源，低 = 可替代资源）；
- 独占资源（大模型容器 / GPU / Docker 单一运行时 / 固定端口）状态必须显式登记。

### 10.2 独占资源与冲突仲裁规则

| 独占资源 | 单机约束 | 冲突场景 | 裁决 |
|----------|---------|---------|------|
| 大模型容器（Ollama 等） | 一台服务器同一时间仅驻留一个生成模型（`OLLAMA_MAX_LOADED_MODELS=1`） | 项目 B 需跑另一模型 | 先注册先得；排队释放后切换（模型加载按需切换，非同时驻留） |
| GPU | 一块 GPU 一次仅一个推理任务 | 多项目并发训练/推理 | 按优先级调度 + 显式时间窗，冲突升阶人工裁决 |
| Docker 单一运行时 | 一台服务器仅一个 Docker daemon（单实例） | 项目各自 `docker-compose` 容器名/端口冲突 | **容器名前缀 = 项目名**（`project-a-api`），端口注册后不得抢占 |
| 固定端口 | 端口一次仅一个监听 | 两个项目都用 3000 | 先注册先得；新项目改端口（3000→3002）并更新清单 |
| 数据库实例 | 数据库名/端口唯一 | 同名库冲突 | 库名带项目前缀（`project_a_dev`）+ 端口隔离 |
| 域名/子域 | 域名唯一 | 子域冲突 | 子域带项目前缀（`a.example.com`） |

**裁决流程（先注册先得 + 人工升阶）**：
1. **注册预检**：`register_env_asset` 申请资源时先查 `25_环境资源清单.csv`，命中「已占用」即判定冲突；
2. **自动裁决**：`空闲` → 直接占用并登记；可替换资源（如端口）→ 自动改资源标识重新申请；
3. **人工升阶**：独占资源（大模型容器 / GPU / Docker 运行时）冲突 → 自动升阶 `change_audit` 留痕（冲突描述/占用方/申请方/决策），由用户决策「等待释放 / 抢占（须授权）/ 换资源」；
4. **更新清单**：占用 / 释放 / 仲裁结果一律回写 `25_环境资源清单.csv`，状态与占用项目保持最新；
5. **启动门禁**：`check_ready` 校验项目所需资源全部登记且无「冲突」状态，未通过不放行进入需求阶段。

### 10.3 本地小工具/脚本的运行目标环境

开发的**本地小工具与脚本若依赖大模型**，运行目标环境**缺省为本地轻量级大模型**（本地 Ollama S0/S1 免费档，见 `model_selection.md` §7），规则：

- 工具运行目标 = 本地模型优先：`qwen3:4b` / `qwen2.5:7b` / `qwen2.5-coder:7b`（本地离线、免费、无网络依赖）；
- 单驻留约束：同一时间仅一个模型驻留，工具链切换模型按需加载（`OLLAMA_MAX_LOADED_MODELS=1`）；
- 若工具确需云端强模型（S2/S3 复杂分析），须在 `20_环境配置.csv` 登记模型引用别名，并经 `select_model` 决策留痕；
- 嵌入模型（`mxbai-embed-large`）仅用于检索/RAG，不计入生成路由池。

### 10.4 隔离验证清单（第 5 层）

- [ ] 每台服务器已建 `25_环境资源清单.csv`
- [ ] 本项目所需端口/容器/大模型资源已注册且无「冲突」
- [ ] Docker 容器名前缀含项目名
- [ ] 独占资源（大模型容器/GPU/Docker 运行时）冲突已裁决并留痕
- [ ] 本地工具依赖大模型时运行目标 = 本地轻量档（或已登记云端引用别名）

---

## 11. 固化流程

1. **项目初始化**：创建项目目录 → 配置 Git → 设置分支策略
2. **环境准备**：创建虚拟环境 → 配置 `.env` → 启动 Docker 服务
3. **服务隔离**：分配端口 → 配置数据库 → 隔离 Redis
4. **资源注册**：`register_env_asset` 登记端口/容器/大模型到 `25_环境资源清单.csv`（第 5 层）
5. **CI/CD 配置**：创建 GitHub Actions → 配置流水线
6. **文档编写**：README → 部署文档 → 环境配置说明
7. **基线固化**：执行 `solidify` → 提交 Git → 更新交接文档

---

## 12. 参考文档

- `worktree-isolation/SKILL.md` - Git worktree 隔离技能
- `environment_standard.md` - 环境配置抽取标准
- `directory_structure.md` - 目录结构规范
- `token_standard.md` - Token 标准与输出规范
- `model_selection.md` - 模型选型标准（§7 本地轻量模型档）
- `iron_rules.md` - 铁律卡（授权/备份/留痕）

---

**文档版本**：v1.1.0　**最后更新**：2026-08-14（新增第 5 层：全局环境资产注册与冲突仲裁 + 本地工具本地轻量模型运行目标）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
