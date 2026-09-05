# 插件接口规范（Plugin Interface Specification）

> **定位**：定义 DevProjectTeamSkill 可选插件的发现、注册、调用与降级标准
> **核心原则**：核心功能独立运行，插件按需增强；无插件时核心功能完整可用
> **版本**：v1.0.0

---

## 一、架构分层

```
DevProjectTeamSkill (MCP Server)
├── 核心层（必须，独立运行）
│   ├── Skills: 10 个角色包 + 1 个编排器
│   ├── Core Tools: 固化/部署/检查/审计/CMDB/脱敏/去水印等
│   └── Resources: SKILL.md / references / SKILL_INDEX
│
├── 代理层（薄封装，插件缺失时友好降级）
│   ├── _hub_proxy.py      → dev-git-hub
│   ├── _scheduler_proxy.py → dev-task-scheduler
│   ├── _model_router_proxy.py → dev-model-router
│   └── （代理脚本仅转发，不复制实现）
│
└── 插件层（可选，安装后增强）
    ├── dev-git-hub        → Git 基建（推送/镜像/IP 探测）
    ├── dev-task-scheduler → 定时任务调度
    ├── dev-model-router   → 多模型分层编排
    ├── dev-project-mgmt   → 项目管理工具集
    ├── dev-security-tools → 安全审计工具集
    ├── dev-test-tools     → 测试工具集
    └── free-api-hub       → API 聚合服务
```

---

## 二、插件发现机制

### 2.1 定位优先级（三级动态解析）

所有插件统一按以下优先级定位，**无需硬编码绝对路径**：

| 优先级 | 方式 | 示例 |
|--------|------|------|
| **1. 环境变量** | `$<PLUGIN_NAME>_ROOT` | `DEV_GIT_HUB_ROOT=/path/to/dev-git-hub` |
| **2. 同级目录约定** | `<repo>/../<plugin-name>` | `../dev-git-hub` |
| **3. 配置文件** | `<repo>/.<plugin>_root` | `.hub_root` 内容为绝对路径 |

### 2.2 验证逻辑

定位到目录后，代理脚本验证插件有效性（检查特征子目录/文件）：

| 插件 | 验证条件 |
|------|----------|
| dev-git-hub | `<root>/tools/` 目录存在 |
| dev-task-scheduler | `<root>/scheduler/` 目录存在 |
| dev-model-router | `<root>/router/` 目录存在 |
| dev-project-mgmt | `<root>/tools/` 目录存在 |
| dev-security-tools | `<root>/tools/` 目录存在 |
| dev-test-tools | `<root>/tools/` 目录存在 |

---

## 三、插件注册表

**单一信源**：`references/plugin_registry.json`

```json
{
  "plugins": [
    {
      "name": "dev-git-hub",
      "env_var": "DEV_GIT_HUB_ROOT",
      "auth": "AUTH-014",
      "category": "infrastructure",
      "required": false,
      "tools": ["mirror_push", "github_push", "github_ip_refresh"],
      "fallback": "使用 git push origin 兜底（仅本地提交）",
      "description": "Git 基建（LAN 中枢 + WAN 灾备 + 真实 IP 推送）"
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 插件项目名 |
| `env_var` | string | ✅ | 环境变量名 |
| `auth` | string | — | 授权编号（对应 `台账/14_授权登记.csv`） |
| `category` | string | ✅ | 分类：`infrastructure` / `tool` / `service` |
| `required` | bool | ✅ | 是否必需（当前全部 `false`） |
| `tools` | string[] | ✅ | 提供的工具列表 |
| `fallback` | string | — | 插件缺失时的替代方案 |
| `description` | string | ✅ | 一句话说明 |

---

## 四、代理脚本规范

### 4.1 薄封装代理模板

```python
#!/usr/bin/env python3
"""
[薄封装代理] 转发到 <plugin-name> 对应脚本。
路径经 tools/_<plugin>_proxy.py 动态解析，跨机器可移植。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _<plugin>_proxy import run_<plugin>_cli

if __name__ == "__main__":
    sys.exit(run_<plugin>_cli())
```

### 4.2 降级处理规范

插件缺失时，代理脚本**必须**输出以下信息：

```
[error] <plugin-name> 工具缺失: tools/<script_name>
        安装方式：
          1. 将 <plugin-name> 项目 clone 到本仓库同级目录（../<plugin-name>）
          2. 或设置环境变量 <ENV_VAR> 指向项目根目录
          3. 或创建配置文件 .<plugin>_root 写入绝对路径
        替代方案：<fallback>
```

### 4.3 代理脚本清单

| 代理脚本 | 目标插件 | 转发脚本 |
|----------|----------|----------|
| `tools/mirror_push.py` | dev-git-hub | `tools/mirror_push.py` |
| `tools/github_push.py` | dev-git-hub | `tools/github_push.py` |
| `tools/github_ip_refresh.py` | dev-git-hub | `tools/github_ip_refresh.py` |
| `tools/scheduler_proxy.py` | dev-task-scheduler | `scheduler/cli.py` |
| `tools/model_router_proxy.py` | dev-model-router | `cli.py` |

---

## 五、核心工具 vs 插件工具

### 5.1 核心工具（无插件依赖，独立运行）

| 工具 | 说明 |
|------|------|
| `tools/solidify.py` | 一键固化（门禁+快照+打包+部署） |
| `tools/package_skills.py` | 打包角色包 |
| `tools/deploy_skills.py` | 部署技能到目标目录 |
| `tools/publish_production.py` | 生产发布 |
| `tools/check_*.py` | 各类门禁检查 |
| `tools/audit.py` | 审计台账写入 |
| `tools/desensitize/` | 文档脱敏 |
| `tools/remove_watermark/` | 去水印 |
| `tools/cmdb/` | CMDB 资源管理 |
| `tools/mcp_server/` | MCP Server |
| `tools/estimate_cost.py` | 成本估算 |
| `tools/cost_monitor.py` | 成本监控 |

### 5.2 插件工具（需安装对应插件）

| 工具 | 依赖插件 | 插件缺失时行为 |
|------|----------|---------------|
| `tools/mirror_push.py` | dev-git-hub | 报错 + 安装指引 |
| `tools/github_push.py` | dev-git-hub | 报错 + 安装指引 |
| `tools/github_ip_refresh.py` | dev-git-hub | 报错 + 安装指引 |
| `tools/scheduler_proxy.py` | dev-task-scheduler | 报错 + 安装指引 |
| `tools/model_router_proxy.py` | dev-model-router | 报错 + 安装指引 |

---

## 六、新插件接入流程

### 6.1 新增插件步骤

1. **创建独立项目**（独立仓库，不嵌套本仓库）
2. **实现工具**（在插件项目 `tools/` 目录下）
3. **在本仓库创建代理脚本**：
   - `tools/_<plugin>_proxy.py`（路径解析模块）
   - `tools/<tool>_proxy.py`（薄封装代理）
4. **注册插件**：更新 `references/plugin_registry.json`
5. **更新文档**：
   - `.env.example` 添加环境变量
   - `references/project-registry.md` 添加登记条目
   - `SKILL_INDEX.md` 标注插件依赖（如适用）

### 6.2 插件独立性要求

- ✅ 插件可独立运行和测试（不依赖本仓库代码）
- ✅ 本仓库无插件时核心功能完整可用
- ✅ 代理脚本仅转发，不复制插件实现
- ✅ 路径全部动态解析，无硬编码

---

## 七、与现有机制的衔接

| 机制 | 衔接方式 |
|------|----------|
| **铁律 #7/#7a**（授权/边界） | 插件路径经 `register_auth` 授权登记 |
| **铁律 #8**（敏感信息） | 插件路径不含 B 级敏感信息（环境变量/相对路径） |
| **孵化器模式** | 新插件经孵化器评估后独立化 |
| **bootstrap_remotes.py** | 初始化时引导配置插件路径 |
| **publish_production** | 发布时不包含插件实现 |

---

**文档版本**：v1.0.0
**知识产权所有**：段波
**最后更新**：2026-09-05
