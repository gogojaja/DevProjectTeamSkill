# DevProjectTeamSkill 与 TwinForge 边界审计报告

> **审计日期**：2026-09-05
> **审计范围**：DevProjectTeamSkill 与 TwinForge 的工作边界、MCP 插件架构、可选插件机制
> **审计目标**：明确两个项目的职责边界，识别边界模糊问题，为 MCP 升级和可复用产品化提供整改方向
> **审计依据**：AGENTS.md、docs/孵化器模式与git剥离方案.md、docs/项目群整体规划方案_v3.0.md、docs/双机AI工作站架构方案-v1.1.md

---

## 一、项目定位对比

### 1.1 DevProjectTeamSkill 定位

| 维度 | 描述 |
|------|------|
| **产品定位** | 软件研发全生命周期多角色编排技能库 |
| **目标用户** | 任意 AI Agent、任意工具（opencode/TRAE/Claude Code/Cursor 等） |
| **部署方式** | 可复用产品，支持在任意机器上部署和使用 |
| **核心价值** | 10 个角色包 + 1 个编排器 + 工具集，提供标准化研发流程 |
| **MCP 升级** | 作为 MCP Server 暴露能力，支持工具/资源/提示词三类接口 |
| **插件架构** | 核心功能独立运行，关联工具和 skill 作为可选插件增强 |

### 1.2 TwinForge 定位

| 维度 | 描述 |
|------|------|
| **产品定位** | 双机 AI 开发工作站（Mac mini M2 + Dell OptiPlex 7010） |
| **目标用户** | 仅限本地用户（douglas 本人） |
| **部署方式** | 本地专用，绑定特定硬件配置 |
| **核心价值** | 本地 LLM 推理、MCP 服务管理、双机协作、涉密信息管理 |
| **公开程度** | 私有项目，对外不公开 |
| **特殊性质** | 包含本机环境配置、IP 地址、主机名等 B 级敏感信息 |

### 1.3 核心差异

| 对比维度 | DevProjectTeamSkill | TwinForge |
|----------|---------------------|-----------|
| **通用性** | 通用，可复用 | 专用，绑定本地硬件 |
| **公开性** | 可对外发布 | 私有，不公开 |
| **依赖关系** | 独立运行，插件可选 | 依赖本地三台机器 |
| **敏感信息** | 脱敏处理，无本机信息 | 包含本机 IP/主机名/路径 |
| **生命周期** | 长期维护，版本化 | 与硬件绑定，硬件更替则项目变化 |

---

## 二、边界问题审计

### 2.1 硬编码路径问题

**严重程度**：🔴 高

**问题描述**：DevProjectTeamSkill 中存在大量硬编码的本地路径，这些路径与 TwinForge 紧密绑定，导致无法在其他机器上直接部署。

**具体发现**：

| 文件 | 硬编码路径 | 问题说明 |
|------|-----------|----------|
| `references/project-registry.md` | `/Volumes/BR256G/dev-git-hub` | macOS 绝对路径，其他机器不存在 |
| `references/project-registry.md` | `/Volumes/BR256G/dev-task-scheduler` | 同上 |
| `references/project-registry.md` | `/Volumes/BR256G/dev-model-router` | 同上 |
| `references/project-registry.md` | `/Volumes/BR256G/dev-project-mgmt` | 同上 |
| `references/project-registry.md` | `/Volumes/BR256G/dev-security-tools` | 同上 |
| `references/project-registry.md` | `/Volumes/BR256G/dev-test-tools` | 同上 |
| `references/project-registry.md` | `/Volumes/BR256G/free-api-hub` | 同上 |
| AGENTS.md | `/Volumes/BR256G/dev-git-hub` | 多处引用绝对路径 |
| docs/*.md | `/Volumes/BR256G/` | 文档中大量引用 |

**影响**：
- 新机器 clone 后需要手动修改路径配置
- 无法直接作为产品发布（包含私有路径）
- 违反 B 级敏感信息处理规则（绝对路径应脱敏）

**整改建议**：
- 使用环境变量（如 `DEV_GIT_HUB_ROOT`）替代硬编码路径
- 提供 `.env.example` 模板，用户自行配置
- `bootstrap_remotes.py` 已实现部分动态解析，但未覆盖所有引用点

---

### 2.2 TwinForge 私有配置混入问题

**严重程度**：🟡 中

**问题描述**：DevProjectTeamSkill 包含大量 TwinForge 的具体实施细节，这些信息属于私有项目配置，不应出现在通用产品中。

**具体发现**：

| 位置 | 私有配置内容 | 问题说明 |
|------|-------------|----------|
| `docs/双机AI工作站架构方案-v1.1.md` | Mac mini M2 16GB 硬件规格 | 绑定特定硬件 |
| `docs/双机AI工作站架构方案-v1.1.md` | Dell OptiPlex 7010 硬件规格 | 绑定特定硬件 |
| `docs/双机AI工作站架构方案-v1.1.md` | Tailscale 组网配置 | 私有网络配置 |
| `docs/双机AI工作站架构方案-v1.1.md` | `xxx.xxx.xxx.xxx` IP 地址 | B 级敏感信息（已脱敏） |
| `docs/双机AI工作站架构方案-v1.1.md` | Ollama 端口 11434 配置 | 本地服务配置 |
| `docs/双机AI工作站架构方案-v1.1.md` | SMB 共享目录配置 | 本地文件共享配置 |
| `台账/28_program_registry.csv` | TwinForge 成员登记 | 私有项目纳入项目群 |

**影响**：
- 产品发布时会泄露本地环境信息
- 文档臃肿，包含大量与通用产品无关的内容
- 新用户可能误解这些配置为必需配置

**整改建议**：
- 将 TwinForge 相关文档移至 TwinForge 项目目录
- DevProjectTeamSkill 仅保留引用链接，不内嵌实现细节
- 项目群注册表中 TwinForge 条目标记为「私有/可选」

---

### 2.3 MCP 插件架构问题

**严重程度**：🟡 中

**问题描述**：MCP Server 实现中存在硬编码逻辑，可选插件机制不完善。

**具体发现**：

| 问题 | 位置 | 说明 |
|------|------|------|
| **代理脚本硬编码** | `tools/mirror_push.py` 等 | 薄封装代理直接调用 dev-git-hub，无插件发现机制 |
| **依赖检测缺失** | `tools/mcp_server.py` | 未检测可选插件是否可用，调用失败时无友好错误 |
| **配置未外部化** | `opencode.json` | MCP 配置硬编码，未提供模板化配置 |
| **插件注册缺失** | `tools/mcp_server/` | 无插件注册表，无法动态发现和加载插件 |

**影响**：
- 无插件时功能降级不明确
- 新机器部署需要手动配置插件路径
- 无法实现「核心独立运行，插件按需增强」的设计目标

**整改建议**：
- 实现插件发现机制（环境变量 + 配置文件 + 自动检测）
- 代理脚本增加插件可用性检查和降级处理
- 提供 MCP 配置模板（`mcp-config.example.json`）
- 定义插件接口规范（`references/plugin_interface.md`）

---

### 2.4 工具独立性问题

**严重程度**：🟡 中

**问题描述**：部分工具与 TwinForge 环境强耦合，无法独立运行。

**具体发现**：

| 工具 | 耦合点 | 独立性评估 |
|------|--------|-----------|
| `tools/mirror_push.py` | 依赖 dev-git-hub 的 `mirror_push.py` | ⚠️ 需要插件 |
| `tools/github_push.py` | 依赖 dev-git-hub 的 `github_push.py` | ⚠️ 需要插件 |
| `tools/github_ip_refresh.py` | 依赖 dev-git-hub 的实现 | ⚠️ 需要插件 |
| `tools/scheduler_proxy.py` | 依赖 dev-task-scheduler | ⚠️ 需要插件 |
| `tools/model_router_proxy.py` | 依赖 dev-model-router | ⚠️ 需要插件 |
| `tools/desensitize/desensitize.py` | 独立实现 | ✅ 可独立运行 |
| `tools/cmdb/cmdb-cli.py` | 独立实现 | ✅ 可独立运行 |
| `tools/audit.py` | 独立实现 | ✅ 可独立运行 |

**影响**：
- 部分功能在无插件环境下不可用
- 用户可能误以为这些功能是核心功能
- 错误提示不友好，用户不知道需要安装插件

**整改建议**：
- 明确区分核心工具和插件工具
- 核心工具在 `tools/` 目录，插件工具在 `tools/plugins/` 或通过代理调用
- 工具执行前检查依赖，给出友好提示
- 在 SKILL_INDEX.md 中标注哪些功能需要插件

---

### 2.5 文档边界模糊

**严重程度**：🟢 低

**问题描述**：文档中混合了通用产品说明和 TwinForge 私有实施细节。

**具体发现**：

| 文档 | 问题 |
|------|------|
| `docs/双机AI工作站架构方案-v1.1.md` | 完整的 TwinForge 方案，应归属 TwinForge |
| `docs/项目群整体规划方案_v3.0.md` | 包含 TwinForge 作为成员项目 |
| `docs/项目群边界审核报告_20260905.md` | 包含 TwinForge 边界审核 |
| AGENTS.md | 包含 TwinForge 的独立关联项目说明 |

**整改建议**：
- TwinForge 相关文档移至 TwinForge 项目
- DevProjectTeamSkill 仅保留「项目注册表」中的引用条目
- 文档中使用相对链接引用 TwinForge 文档（如果需要）

---

## 三、MCP 插件架构评估

### 3.1 当前架构

```
DevProjectTeamSkill (MCP Server)
├── 核心能力（独立运行）
│   ├── Skills: 10 个角色包 + 1 个编排器
│   ├── Tools: 固化/部署/检查/审计等
│   └── Resources: SKILL.md / references / SKILL_INDEX
│
└── 可选插件（增强能力）
    ├── dev-git-hub: git 基建（通过薄代理调用）
    ├── dev-task-scheduler: 定时任务（通过薄代理调用）
    ├── dev-model-router: 模型路由（通过薄代理调用）
    ├── dev-project-mgmt: 项目管理工具
    ├── dev-security-tools: 安全审计工具
    └── dev-test-tools: 测试工具集
```

### 3.2 目标架构

```
DevProjectTeamSkill (MCP Server) - 可复用产品
├── 核心层（必须，独立运行）
│   ├── Skills: 10 个角色包 + 1 个编排器
│   ├── Core Tools: 固化/部署/检查/审计/CMDB/脱敏等
│   └── Resources: SKILL.md / references / SKILL_INDEX
│
├── 插件接口层（规范定义）
│   ├── Plugin Registry: 插件注册表
│   ├── Plugin Discovery: 插件发现机制
│   └── Plugin Loader: 插件加载器
│
└── 可选插件层（按需安装）
    ├── [插件] dev-git-hub: git 基建
    ├── [插件] dev-task-scheduler: 定时任务
    ├── [插件] dev-model-router: 模型路由
    ├── [插件] dev-project-mgmt: 项目管理
    ├── [插件] dev-security-tools: 安全审计
    ├── [插件] dev-test-tools: 测试工具
    └── [插件] TwinForge Adapter: 双机工作站适配器（私有）
```

### 3.3 架构差距分析

| 维度 | 当前状态 | 目标状态 | 差距 |
|------|----------|----------|------|
| **插件发现** | 硬编码路径 | 环境变量 + 配置文件 + 自动检测 | 需实现 |
| **插件注册** | 无注册表 | `plugin_registry.json` | 需新建 |
| **插件接口** | 无规范 | `references/plugin_interface.md` | 需定义 |
| **降级处理** | 调用失败报错 | 友好提示 + 功能降级 | 需优化 |
| **配置模板** | 无 | `mcp-config.example.json` | 需提供 |
| **文档说明** | 混合 | 核心/插件分离 | 需整理 |

---

## 四、可选插件机制评估

### 4.1 当前插件调用方式

| 插件 | 调用方式 | 是否有降级处理 |
|------|----------|---------------|
| dev-git-hub | `tools/mirror_push.py` 薄代理 | ❌ 无 |
| dev-task-scheduler | `tools/scheduler_proxy.py` | ❌ 无 |
| dev-model-router | `tools/model_router_proxy.py` | ❌ 无 |
| dev-project-mgmt | 直接调用 | ❌ 无 |
| dev-security-tools | 直接调用 | ❌ 无 |
| dev-test-tools | 直接调用 | ❌ 无 |

### 4.2 目标插件机制

```python
# 插件发现机制示例
def discover_plugin(plugin_name: str) -> Optional[Path]:
    """发现插件路径，优先级：环境变量 > 配置文件 > 默认位置"""
    # 1. 环境变量
    env_var = f"{plugin_name.upper()}_ROOT"
    if env_var in os.environ:
        return Path(os.environ[env_var])
    
    # 2. 配置文件
    config = load_plugin_config()
    if plugin_name in config:
        return Path(config[plugin_name])
    
    # 3. 默认位置（同级目录）
    default_path = Path(f"../{plugin_name}")
    if default_path.exists():
        return default_path
    
    return None

# 插件调用包装
def call_plugin_tool(plugin_name: str, tool_name: str, *args) -> dict:
    """调用插件工具，带降级处理"""
    plugin_path = discover_plugin(plugin_name)
    if plugin_path is None:
        return {
            "error": f"插件 {plugin_name} 未安装",
            "hint": f"请安装 {plugin_name} 或配置 {plugin_name.upper()}_ROOT 环境变量",
            "fallback": get_fallback_action(plugin_name, tool_name)
        }
    # ... 调用插件工具
```

### 4.3 插件接口规范（建议）

```markdown
# 插件接口规范

## 必需接口
- `README.md`: 插件说明
- `PLUGIN.json`: 插件元数据（名称/版本/依赖/接口）
- `tools/`: 工具目录
- `references/`: 参考文档

## 可选接口
- `SKILL.md`: 技能定义（如果插件提供技能）
- `tests/`: 测试用例
- `docs/`: 文档

## PLUGIN.json 示例
{
  "name": "dev-git-hub",
  "version": "1.0.0",
  "description": "Git 基建工具集",
  "tools": ["mirror_push", "github_push", "github_ip_refresh"],
  "skills": [],
  "dependencies": [],
  "entry_points": {
    "mirror_push": "tools/mirror_push.py",
    "github_push": "tools/github_push.py"
  }
}
```

---

## 五、待办事项清单

### 5.1 高优先级（阻塞产品化）

| 编号 | 任务 | 影响范围 | 预估工作量 | 状态 |
|------|------|----------|-----------|------|
| **TODO-001** | 移除 `references/project-registry.md` 中的硬编码路径，改用环境变量 | 全局 | 2 小时 | 待执行 |
| **TODO-002** | 移除 AGENTS.md 中的硬编码路径，改用环境变量说明 | 全局 | 1 小时 | 待执行 |
| **TODO-003** | 创建 `.env.example` 模板，列出所有可配置的环境变量 | 配置 | 1 小时 | 待执行 |
| **TODO-004** | 实现插件发现机制（`tools/plugin_discovery.py`） | 核心 | 4 小时 | 待执行 |
| **TODO-005** | 创建插件注册表（`references/plugin_registry.json`） | 配置 | 2 小时 | 待执行 |
| **TODO-006** | 定义插件接口规范（`references/plugin_interface.md`） | 文档 | 3 小时 | 待执行 |

### 5.2 中优先级（影响用户体验）

| 编号 | 任务 | 影响范围 | 预估工作量 | 状态 |
|------|------|----------|-----------|------|
| **TODO-007** | 为薄代理脚本添加插件可用性检查和降级处理 | 工具 | 4 小时 | 待执行 |
| **TODO-008** | 创建 MCP 配置模板（`mcp-config.example.json`） | 配置 | 1 小时 | 待执行 |
| **TODO-009** | 在 SKILL_INDEX.md 中标注哪些功能需要插件 | 文档 | 1 小时 | 待执行 |
| **TODO-010** | 将 TwinForge 相关文档移至 TwinForge 项目目录 | 文档 | 2 小时 | 待执行 |
| **TODO-011** | 更新文档中的 TwinForge 引用为相对链接 | 文档 | 1 小时 | 待执行 |

### 5.3 低优先级（优化改进）

| 编号 | 任务 | 影响范围 | 预估工作量 | 状态 |
|------|------|----------|-----------|------|
| **TODO-012** | 实现插件加载器（`tools/plugin_loader.py`） | 核心 | 4 小时 | 待执行 |
| **TODO-013** | 创建插件开发指南（`docs/plugin_development_guide.md`） | 文档 | 3 小时 | 待执行 |
| **TODO-014** | 为每个插件创建 `PLUGIN.json` 元数据文件 | 插件 | 2 小时 | 待执行 |
| **TODO-015** | 实现插件版本兼容性检查 | 核心 | 2 小时 | 待执行 |
| **TODO-016** | 创建 TwinForge 适配器插件（私有） | 插件 | 4 小时 | 待执行 |

### 5.4 长期规划

| 编号 | 任务 | 影响范围 | 预估工作量 | 状态 |
|------|------|----------|-----------|------|
| **TODO-017** | 实现插件市场/仓库机制 | 架构 | 8 小时 | 规划中 |
| **TODO-018** | 支持插件热加载/卸载 | 核心 | 4 小时 | 规划中 |
| **TODO-019** | 实现插件依赖解析和冲突检测 | 核心 | 4 小时 | 规划中 |
| **TODO-020** | 创建插件测试框架 | 测试 | 4 小时 | 规划中 |

---

## 六、整改路线图

### Phase 1：路径外部化（1-2 天）

**目标**：移除所有硬编码路径，实现配置外部化

**任务**：
- [ ] TODO-001: 移除 project-registry.md 硬编码路径
- [ ] TODO-002: 移除 AGENTS.md 硬编码路径
- [ ] TODO-003: 创建 .env.example 模板
- [ ] 更新 bootstrap_remotes.py 支持所有路径配置

**验收标准**：
- 新机器 clone 后只需配置 `.env` 即可运行核心功能
- 无硬编码的本地路径

### Phase 2：插件机制实现（3-5 天）

**目标**：实现插件发现、注册、加载机制

**任务**：
- [ ] TODO-004: 实现插件发现机制
- [ ] TODO-005: 创建插件注册表
- [ ] TODO-006: 定义插件接口规范
- [ ] TODO-007: 为薄代理添加降级处理

**验收标准**：
- 核心功能无插件时可独立运行
- 插件可用时自动增强功能
- 插件不可用时给出友好提示

### Phase 3：文档整理（2-3 天）

**目标**：分离通用文档和私有文档

**任务**：
- [ ] TODO-009: 标注插件依赖
- [ ] TODO-010: 移动 TwinForge 文档
- [ ] TODO-011: 更新文档引用
- [ ] TODO-013: 创建插件开发指南

**验收标准**：
- 文档清晰区分核心功能和插件功能
- TwinForge 私有信息不混入通用产品

### Phase 4：产品化发布（1 周）

**目标**：准备产品级发布

**任务**：
- [ ] TODO-008: 创建 MCP 配置模板
- [ ] TODO-014: 创建插件元数据
- [ ] TODO-015: 实现版本兼容性检查
- [ ] 创建产品 README 和安装指南

**验收标准**：
- 新用户可按文档在任意机器上部署
- MCP Server 可被任意 MCP 客户端调用
- 插件可按需安装和配置

---

## 七、风险评估

### 7.1 整改风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 路径外部化导致现有功能失效 | 中 | 高 | 充分测试，保留兼容性 |
| 插件机制引入新的复杂度 | 中 | 中 | 简单实现，渐进增强 |
| 文档整理遗漏重要信息 | 低 | 中 | 完整性检查，版本控制 |
| TwinForge 功能受影响 | 低 | 高 | 创建适配器插件 |

### 7.2 不整改的风险

| 风险 | 概率 | 影响 | 后果 |
|------|------|------|------|
| 无法作为产品发布 | 高 | 高 | 项目价值无法发挥 |
| 新机器部署困难 | 高 | 中 | 用户体验差 |
| 私有信息泄露 | 中 | 高 | 安全风险 |
| 维护成本增加 | 高 | 中 | 每次修改需同步多处 |

---

## 八、结论与建议

### 8.1 核心结论

1. **边界存在但不清晰**：DevProjectTeamSkill 和 TwinForge 有明确的定位差异，但实现层面存在大量边界模糊
2. **硬编码是主要问题**：大量本地路径硬编码导致无法直接产品化
3. **插件机制缺失**：虽然有薄代理调用，但缺乏规范的插件发现和降级机制
4. **文档混合**：通用文档和私有文档未分离

### 8.2 整改建议

1. **立即执行**：路径外部化（TODO-001~003），这是产品化的前提
2. **短期执行**：插件机制实现（TODO-004~007），实现「核心独立，插件可选」
3. **中期执行**：文档整理（TODO-008~013），提升用户体验
4. **长期规划**：插件市场和热加载（TODO-017~020），提升产品竞争力

### 8.3 预期效果

整改完成后：
- DevProjectTeamSkill 可作为**独立产品**在任意机器上部署
- 核心功能**无需任何插件**即可正常运行
- 插件**按需安装**，安装后功能增强
- TwinForge 作为**私有插件**存在，不影响产品发布
- 新用户**5 分钟内**可完成基础部署

---

**审计人**：AI Agent（PMO 辅助）
**审核人**：待定
**知识产权所有**：段波
**文档版本**：v1.0.0
**最后更新**：2026-09-05
