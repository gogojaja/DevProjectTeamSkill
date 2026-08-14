# CMDB CLI - 轻量级资源管理工具

## 概述

CMDB CLI 是 DevProjectTeamSkill 技能库配套的轻量级资源管理工具，用于管理多项目共享服务器上的资源冲突（端口、容器、大模型、GPU、数据库、域名等）。

## 功能

- **主机注册**：记录服务器信息（主机名、IP、环境）
- **资源注册**：注册资源（端口、容器、模型、GPU、数据库、域名）并关联到项目
- **资源释放**：释放占用的资源
- **冲突检测**：自动检测资源冲突（同一资源被多个项目占用）
- **查询**：按主机、类型、项目、状态查询资源
- **导出**：导出资源为 CSV 格式
- **审计日志**：所有操作留痕

## 快速开始

### 1. 初始化数据库

```bash
python tools/cmdb/cmdb-cli.py init
```

### 2. 注册主机

```bash
python tools/cmdb/cmdb-cli.py register --host dev-server-01 --type port --identifier 8000 --project backend-api --name "Backend API Server"
```

### 3. 注册其他资源

```bash
# 注册容器
python tools/cmdb/cmdb-cli.py register --host dev-server-01 --type container --identifier mysql-01 --project backend-api --name "MySQL Database"

# 注册大模型
python tools/cmdb/cmdb-cli.py register --host dev-server-01 --type model --identifier llama3-8b --project ai-team --name "Llama3 8B Model"

# 注册 GPU
python tools/cmdb/cmdb-cli.py register --host dev-server-01 --type gpu --identifier gpu-01 --project ai-team --name "NVIDIA A100"
```

### 4. 查询资源

```bash
# 查询所有资源
python tools/cmdb/cmdb-cli.py query

# 查询特定主机的资源
python tools/cmdb/cmdb-cli.py query --host dev-server-01

# 查询特定项目的资源
python tools/cmdb/cmdb-cli.py query --project backend-api

# 查询特定类型的资源
python tools/cmdb/cmdb-cli.py query --type port

# 查询特定状态的资源
python tools/cmdb/cmdb-cli.py query --status occupied
```

### 5. 列出所有主机

```bash
python tools/cmdb/cmdb-cli.py list-hosts
```

### 6. 导出资源为 CSV

```bash
# 导出到文件
python tools/cmdb/cmdb-cli.py export --project backend-api --output backend-api-resources.csv

# 导出到 stdout
python tools/cmdb/cmdb-cli.py export --project backend-api --output -
```

### 7. 释放资源

```bash
# 按资源 ID 释放
python tools/cmdb/cmdb-cli.py release --resource-id 1 --project backend-api

# 按类型和标识释放
python tools/cmdb/cmdb-cli.py release --type port --identifier 8000 --project backend-api
```

## 命令参考

### init

初始化数据库。

```bash
python tools/cmdb/cmdb-cli.py init
```

### register

注册资源。

```bash
python tools/cmdb/cmdb-cli.py register \
  --host <hostname> \
  --type <type> \
  --identifier <identifier> \
  --project <project> \
  [--name <name>] \
  [--priority <high|medium|low>] \
  [--notes <notes>] \
  [--force] \
  [--operator <operator>]
```

**参数**：
- `--host`：主机名（必需）
- `--type`：资源类型（必需）- `port`/`container`/`model`/`gpu`/`database`/`domain`
- `--identifier`：资源标识（必需）- 端口号/容器名/模型名等
- `--project`：占用项目（必需）
- `--name`：资源名称（可选）
- `--priority`：优先级（可选）- `high`/`medium`/`low`（默认：`medium`）
- `--notes`：备注（可选）
- `--force`：强制覆盖已存在的资源（可选）
- `--operator`：操作人（可选，默认：环境变量 `USER`）

### release

释放资源。

```bash
python tools/cmdb/cmdb-cli.py release \
  [--resource-id <id>] \
  [--type <type>] \
  [--identifier <identifier>] \
  --project <project> \
  [--force] \
  [--operator <operator>]
```

**参数**：
- `--resource-id`：资源 ID（可选，优先级高于 `--type` + `--identifier`）
- `--type`：资源类型（可选）
- `--identifier`：资源标识（可选）
- `--project`：释放项目（必需）
- `--force`：强制释放（可选）
- `--operator`：操作人（可选）

### query

查询资源。

```bash
python tools/cmdb/cmdb-cli.py query \
  [--host <hostname>] \
  [--type <type>] \
  [--project <project>] \
  [--status <free|occupied|conflict>]
```

**参数**：
- `--host`：主机名（可选）
- `--type`：资源类型（可选）
- `--project`：占用项目（可选）
- `--status`：状态（可选）- `free`/`occupied`/`conflict`

### list-hosts

列出所有主机。

```bash
python tools/cmdb/cmdb-cli.py list-hosts
```

### export

导出资源为 CSV。

```bash
python tools/cmdb/cmdb-cli.py export \
  [--host <hostname>] \
  [--type <type>] \
  [--project <project>] \
  [--output <file>]
```

**参数**：
- `--host`：主机名（可选）
- `--type`：资源类型（可选）
- `--project`：占用项目（可选）
- `--output`：输出文件（可选，默认：`-` 即 stdout）

### version

显示版本信息。

```bash
python tools/cmdb/cmdb-cli.py version
```

## 数据库结构

### 主机表（hosts）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| hostname | TEXT | 主机名（唯一） |
| ip | TEXT | IP 地址（可选） |
| environment | TEXT | 环境（默认：`dev`） |
| registered_by | TEXT | 注册人 |
| registered_at | TEXT | 注册时间 |
| notes | TEXT | 备注 |

### 资源表（resources）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| host_id | INTEGER | 外键：hosts.id |
| resource_type | TEXT | 资源类型 |
| resource_identifier | TEXT | 资源标识 |
| resource_name | TEXT | 资源名称（可选） |
| occupied_by | TEXT | 占用项目（空=空闲） |
| status | TEXT | 状态（`free`/`occupied`/`conflict`） |
| priority | TEXT | 优先级（`high`/`medium`/`low`） |
| registered_at | TEXT | 注册时间 |
| released_at | TEXT | 释放时间 |
| notes | TEXT | 备注 |

### 审计表（audits）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| action | TEXT | 操作类型 |
| resource_id | INTEGER | 外键：resources.id |
| operator | TEXT | 操作人 |
| timestamp | TEXT | 操作时间 |
| notes | TEXT | 备注 |

## 集成到技能库

### 1. 在 `role-project-init` 中调用 CMDB

在 `register_env_asset` action 中调用 `cmdb-cli.py`：

```python
# 示例
import subprocess

def register_env_asset(project, host, resource_type, identifier, priority="medium"):
    cmd = [
        "python", "tools/cmdb/cmdb-cli.py",
        "register",
        "--host", host,
        "--type", resource_type,
        "--identifier", identifier,
        "--project", project,
        "--priority", priority,
        "--operator", current_user
    ]
    subprocess.run(cmd, check=True)
```

### 2. 在 `multi_project_isolation.md` 中补充说明

在 `multi_project_isolation.md` 的第 5 层「全局环境资产注册与冲突仲裁」中补充 CMDB 使用说明。

### 3. 固化部署

```bash
bash tools/solidify.sh "feat(cmdb): 添加轻量级资源管理工具 CMDB CLI v1.0.0"
```

## 使用场景

### 场景 1：多项目共享同一台服务器

假设有 3 个项目共享同一台服务器 `dev-server-01`：

```bash
# 项目 A 注册端口
python tools/cmdb/cmdb-cli.py register --host dev-server-01 --type port --identifier 8000 --project project-a --name "Project A API"

# 项目 B 注册端口
python tools/cmdb/cmdb-cli.py register --host dev-server-01 --type port --identifier 8001 --project project-b --name "Project B API"

# 项目 C 尝试注册端口 8000（冲突）
python tools/cmdb/cmdb-cli.py register --host dev-server-01 --type port --identifier 8000 --project project-c
# 输出：❌ 资源标识冲突：UNIQUE constraint failed: resources.resource_identifier
```

### 场景 2：资源释放与审计

```bash
# 项目 A 完成开发，释放端口
python tools/cmdb/cmdb-cli.py release --type port --identifier 8000 --project project-a

# 查询审计日志
cat tools/cmdb/cmdb_audit.log
```

## 版本信息

- **版本**：v1.0.0
- **数据库**：SQLite
- **Python 版本**：3.6+
- **许可协议**：MIT

## 故障排查

### 问题：数据库不存在

**错误**：`❌ 数据库不存在，请先运行: cmdb-cli init`

**解决**：运行 `python tools/cmdb/cmdb-cli.py init` 初始化数据库。

### 问题：资源已存在

**错误**：`⚠️  资源已存在: port=8000`

**解决**：使用 `--force` 强制覆盖，或先释放资源。

### 问题：权限不足

**错误**：`❌ 权限不足`

**解决**：确保 Python 脚本有写入权限。

## 许可协议

MIT License

## 作者

DevProjectTeamSkill Team
