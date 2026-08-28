# 审计溯源增强方案（设计）

> 目标：让 DevProjectTeamSkill 在「执行关键操作」时，可被追溯定位到
> **哪台机器（主机标识）· 通过什么客户端工具 · 什么模型 · 什么时间**，
> 并契合行业治理级可观测性标准，同时不违反本仓库铁律 #8 脱敏要求。
> 决策：主机名经用户授权明文保留（AUTH-021）。

---

## 1. 行业最佳实践研究

### 1.1 治理级可观测性的四大支柱（Confident AI, 2026-07）
审计轨迹（audit trail）是合规证据的唯一机制：**不可变、受访问控制、按保留期留存**的
记录，说明「系统做了什么、谁改的、质量如何被监控」。四大支柱：
1. **不可变审计轨迹**（immutable audit trail）—— 防静默篡改、存活过保留期；
2. **访问控制**（access control）；
3. **数据驻留**（data residency）；
4. **持续质量证据**（continuous quality evidence）。
治理要求本质上是**记录留存要求**——审计应从第一天就按证据库设计，而非事后考古。

### 1.2 审计轨迹必须回答的五个问题（AgentTrust / LoginRadius, 2026）
企业级审计轨迹须能回答：
- **Who authorized?**（谁授权）
- **Who did what?**（谁做了什么）
- **When?**（何时）
- **What data / target?**（对象/数据）
- **What model / version?**（什么模型/版本）
→ 这正是本方案要补齐的「主机 + 工具 + 模型 + 时间」四维。

### 1.3 Trace-first 与 GenAI 语义约定（OpenTelemetry）
OpenTelemetry **GenAI 语义约定**（已从核心仓迁至 `semantic-conventions-genai`）定义了
AI 遥测的标准属性，本方案字段直接对齐：

| 本台账字段 | OTel GenAI 对应 | 含义 |
|---|---|---|
| `会话ID` | `session.id` / `gen_ai.conversation.id` | 一次 agent 运行的唯一关联 ID |
| `客户端工具` | `gen_ai.agent.name` / `gen_ai.workflow.name` | 发起操作的客户端/智能体 |
| `模型名称` | `gen_ai.request.model` / `gen_ai.response.model` | 执行操作的模型 |
| `主机标识` | `host.name`（OTel 资源语义） | 运行机器的主机名 |
| `操作时间` | span timestamp（`generatedAtTime`） | 操作发生时刻 |

最佳实践（groundcover, 2026）：**每次 agent 运行 = 一条 trace**，span 覆盖
规划→模型调用→工具调用；跨栈使用**统一遥测约定**（agent name / operation / model / tool / route），
使不同框架的遥测可读、可比对。本方案把这一原则下沉到「本地 CSV 台账」这一最轻量载体。

### 1.4 溯源数据模型（W3C PROV）
W3C PROV-DM 是溯源（provenance）国际标准，本方案操作记录可映射为：
- **Agent**（wasAssociatedWith）→ 执行操作的「模型 + 客户端工具」组合；
- **Activity** → 关键操作本身；
- **Entity** → 被修改的对象（文件/配置）；
- 关系：`wasAssociatedWith`（操作↔模型/工具）、`used`（操作↔对象）、`wasGeneratedBy`/`invalidatedAtTime`（对象版本演化）、`generatedAtTime`（操作时间）。
PROV 强调：**时间顺序完整性（chronological integrity）** 与 **跨组织可追溯（cross-organizational traceability）**——后者正对应本库多机（macOS `gogojajadeMac-mini` / Windows `douglas`）协作场景。

### 1.5 AI 治理标准映射
| 标准 | 与审计溯源的关联 |
|---|---|
| **NIST AI RMF** | Govern（治理文档/记录留存）、Measure（监控证据留存） |
| **ISO/IEC 42001** | 条款 7.5 记录、9.2 内部审核、10.2 不合格纠正——变更须可溯源 |
| **EU AI Act** | 高风险 AI 系统须留存运行日志 |
| **SOC 2** | 审计轨迹（audit trail）控制项 |
| **W3C PROV / OTel GenAI** | 溯源与遥测的语义层标准（见 1.3/1.4） |

### 1.6 LLM 审计轨迹学术框架（arXiv:2601.20727, 2026）
提出：① 生命周期事件框架（事件类型 + 必备元数据 + 治理理由）；② 参考架构
（轻量发射器 + **只追加审计存储 append-only** + 审计者接口）；③ 开源实现。
关键特征：**全面覆盖、时间顺序完整、不可变（immutability）、防篡改（tamper-evident）、跨组织可追溯**。
其中「配置驱动的自适应（prompts / 检索索引 / 工具 schema / 安全策略）应作为**带版本的资产**，其变更可归因到 actor 与时间」——与本库「技能即资产、单源 `.trae/skills/`」理念一致。

---

## 2. 现状缺口（对照四维）

当前 `台账/13_安全审计台账.csv` 字段：
`操作ID, 操作类型, 对象, 风险等级, 授权人, 是否备份, 备份路径, 留痕时间, 结果`

| 需求维度 | 现状 | 问题 |
|---|---|---|
| 主机标识 | ❌ 无字段；`授权人` 偶有 `douglas\<user>` 但不记录主机名 | 无法定位机器；且铁律 #8 为合规刻意脱敏留空 |
| 客户端工具 | ❌ 无字段；仅文本偶提（「Continue.dev 已接入」） | 无法结构化定位客户端 |
| 模型名称 | ❌ 无字段；`40_大模型成本台账` 仅计费任务记模型 | 无法定位执行模型 |
| 操作时间 | ⚠️ 有「留痕时间」但不规范：格式混乱（`20260827233121` vs `2026-08-28 07:33:18`）、无时区、是写入时间非操作时间 | 不可靠解析 |

---

## 3. 设计方案

### 3.1 概念模型（PROV + OTel 映射）
```
[模型+客户端工具] --(wasAssociatedWith)--> [关键操作 Activity]
        |                                        |
   gen_ai.request.model / gen_ai.agent.name   操作时间(generatedAtTime) / 会话ID(session.id)
        |                                        |
        +--(used)--> [对象 Entity] <--(wasGeneratedBy / invalidatedAtTime)-- [新版本]
```
每行审计 = 一个 Activity 实例，承载上述全部溯源属性。

### 3.2 增强后台账 Schema

**`台账/13_安全审计台账.csv`（新表头，向后兼容）：**
```
操作ID, 会话ID, 主机标识, 客户端工具, 模型名称, 操作时间,
操作类型, 对象, 风险等级, 授权人, 授权ID, 是否备份, 备份路径, 留痕时间, 结果
```
- `操作ID`：主键，格式 `OP-AUDIT-0NN` / `AUD-YYYYMMDD-NN`（沿用现有）。
- `会话ID`：一次 agent 运行 UUID（OTel `session.id`），聚合同次多操作。
- `主机标识`：机器主机名（**用户授权明文**，AUTH-021），多机经 CMDB `host` 注册表关联。
- `客户端工具`：发起客户端（opencode / Trae CN / Qoder / VS Code+Continue …）。
- `模型名称`：活跃模型（如 `ark-coding/deepseek-v4-flash`）。
- `操作时间`：**ISO8601+TZ**（`2026-08-28T07:33:18+08:00`），取操作发生时刻。
- 其余沿用旧字段；`对象` 路径仍按铁律 #8 脱敏（`<repo>` 占位 / 相对路径）。

**`台账/14_授权登记.csv`（仅增 `主机标识` 列，授权同样按机器归属）：**
```
授权ID, 主机标识, 授权对象, 对象类型, 路径, 权限, 授权人, 授权时间, 有效期至, 状态, 备注
```

### 3.3 脱敏策略（铁律 #8 对齐）
| 字段 | 敏感级 | 处理 |
|---|---|---|
| 主机标识 | B 级（本应脱敏） | **用户授权明文保留**（AUTH-021）→ 例外 |
| 客户端工具 | 非敏感 | 明文 |
| 模型名称 | 非敏感（公开模型名） | 明文 |
| 操作时间 | 非敏感 | 明文 ISO8601+TZ |
| 对象路径 | B 级 | 维持脱敏（`<repo>` / 相对路径） |

### 3.4 自动埋点助手 `tools/audit.py`
统一写入入口，避免手工漏填：
- 自动抓取 `socket.gethostname()` → 主机标识；
- 自动生成 `操作时间` = `datetime.now().astimezone().isoformat()`（含 +08:00）；
- 支持 `--kind op|auth`、`--tool`、`--model`、`--session-id`、`--target`（可选算 SHA256 前后哈希）、`--op-id` 自动递增；
- 模型默认值：未传时读取 `opencode.json` 的 `model` 字段，再降级 `未知`；
- 输出到对应台账（UTF-8、LF、`lineterminator="\n"`）。

---

## 4. 方案评审

### 4.1 优点
1. **标准对齐**：字段命名/语义直接映射 OTel GenAI + W3C PROV，未来可无缝对接 SIEM / Langfuse 等平台。
2. **精准定位**：补齐用户要求的「机器 + 工具 + 模型 + 时间」四维，异常时可一键收敛。
3. **低成本落地**：本地 CSV 台账，无外部依赖，契合本库离线、单源特性。
4. **向后兼容**：旧行回填（已知行填实、未知填 `未知`、时间解析为标准格式），不破坏历史。

### 4.2 风险缺口与缓解
| 缺口 | 风险 | 缓解 |
|---|---|---|
| **CSV 可变性** | 行业最佳实践强调 append-only / WORM / 防篡改（arXiv, Confident AI）；CSV 可被静默改写 | ① git 历史即 append-only + 提交签名；② 后续引入**哈希链**（每行含前一行哈希）作 tamper-evident（见 4.3） |
| **埋点靠纪律** | 助手存在但关键操作须主动调用才记录 | ① 在 opencode 技能关键操作 SOP 引用 `tools/audit.py`；② pre-commit 钩子提示未留痕的关键外部改动 |
| **主机名明文 vs 铁律 #8** | 公开仓库暴露基础设施主机名 | AUTH-021 显式授权 + 范围限定；若仓库转公开可改用 `host-<hash>` 别名 + 本地 `.secrets` 映射 |
| **时区一致性** | 多机/多时区导致排序错乱 | 强制 `+08:00`（本机环境）；字段为 ISO8601 含偏移，天然可排序 |
| **会话ID 空白** | 未传则跨操作无法聚合 | 缺省生成 per-invocation UUID，保证可关联 |

### 4.3 可选增强（本方案不阻塞，列入路线图）
- **哈希链防篡改**：每行追加 `前序哈希`，形成 tamper-evident 链。
- **对象前后哈希**：`对象哈希(前→后)` 列，直接验证变更内容完整性。
- **SIEM / 外部导出**：台账按 OTel 语义序列化后推送至 Langfuse / SIEM（多机集中溯源）。
- **模型/工具自动探测**：从运行环境（如 opencode 注入的环境变量）自动取客户端与模型，减少手工参数。

---

## 5. 合规映射小结
本方案以 **W3C PROV（溯源模型）+ OpenTelemetry GenAI（遥测语义）+ NIST AI RMF / ISO 42001（治理记录）**
为基准，在不引入外部依赖、不违反铁律 #8（经授权例外）前提下，补齐关键操作审计的
「主机 + 客户端工具 + 模型 + 时间 + 会话」五维溯源能力，满足用户「异常时定位到
具体机器/工具/模型/时间」的核心诉求，并为后续防篡改与集中溯源预留接口。
