# 范围基准与追溯矩阵（Scope Baseline & RTM）

> 所属技能：`scope-tracking` v1.2.0 · 标准：`references/traceability_standard.md` §1-§4
> 权威工具：`tools/scope_tracker.py`（`init` / RTM schema）· 对齐 PMBOK 7th 范围管理 · IEEE 29148 · MoSCoW

## 1. 范围基准权威（强制）

- **范围基准 = 固化版需求基线（SRS + 追溯矩阵 RTM）派生**；「范围合规」以需求基线为**唯一**比对标准。
- 已实现内容与范围基准不符（该做未做 / 多做超范围 / 行为不符）→ 一律以范围基准为准，偏差记为**缺陷返工**；**禁止以已实现内容逆向修正范围基准/需求基线**。
- 范围基准调整**仅允许经合法变更审批**（来源限：范围调整 / 接口变化 / 合规新规 / 新诉求 / 缺陷澄清）；来源为「已实现内容」的调整请求一律驳回（见 `change-control.md`）。

## 2. 单一事实来源：需求-架构-代码追溯矩阵（RTM）

RTM 是范围跟踪的**单一事实来源**，路径 `台账/需求-架构-代码追溯矩阵.csv`，**连续维护、禁止事后突击补表**。标识符 `REQ-` / `AE-`（架构元素）/ `MOD-`（代码模块）/ `TC-`（测试用例）**唯一且不复用**。

**RTM 列 schema**（`scope_tracker.py` 权威定义）：

| 组 | 列 | 含义 |
|----|----|------|
| 基础（一致性门禁必需） | `REQ_ID` `REQ_TITLE` `AE_ID` `MOD_ID` `TC_ID` | 需求→架构→代码→测试的三方链接（多值逗号/分号分隔） |
| 扩展（范围跟踪） | `PRIORITY` | MoSCoW：`Must` / `Should` / `Could` / `Won't` |
| | `SCOPE_STATUS` | 见 §3 状态词表 |
| | `BASELINE_VER` | 该行需求所属范围基准版本（如 `v1.0.0`），审批通过后升级 |
| | `SOURCE` | 需求来源（范围调整/接口变化/合规新规/新诉求/缺陷澄清…） |
| | `VERIFY_METHOD` | 验证方式（关联 TC 或验证手段） |
| | `CHANGE_REFS` | 关联的变更编号（CR-<nnn>），审批回写追加 |

> 基础 5 列缺失时 `load_rtm` 抛错；`init` 会写入示例行并对已存在台账做 schema 对齐自检（无数据行则安全重写表头，含数据仅告警防丢失）。

## 3. SCOPE_STATUS 状态词表

| 类别 | 取值 | 语义 |
|------|------|------|
| 活动生命周期 | `Proposed` | 已提出，未纳入基线 |
| | `Baselined` | 已纳入范围基准 |
| | `InProgress` | 开发中 |
| | `Implemented` | 已实现（计入实现率） |
| | `Verified` | 已验证（计入实现率 + 验证率） |
| | `Closed` | 已关闭（计入实现率 + 验证率） |
| 范围外标记 | `Rejected` | 被否决 |
| | `Deferred` | 延期 |
| | `Out-of-Scope` | 明确范围外 |

- **实现率** = `SCOPE_STATUS ∈ {Implemented, Verified, Closed}` 的需求占比；**验证率** = `∈ {Verified, Closed}` 占比。
- **范围外不删除（强制）**：被否决/延期/明确范围外的需求**保留在 RTM 中以上述标记标注**，不物理删除——防止范围蔓延靠「重新争论已否决项」发生。

## 4. WBS 映射

`REQ-<nnn>` → `AE-<nnn>`（架构组件）→ `MOD-<nnn>`（代码模块）即构成可执行 WBS 映射（RTM 的 `REQ→AE→MOD` 链）。大型项目可另附 WBS 词典，但**映射事实以 RTM 为准**。

## 5. 初始化流程

```bash
python3 tools/scope_tracker.py init                # 建 RTM（含扩展列）+ 06/07 台账表头 + 示例行
python3 tools/scope_tracker.py init --reset-ledgers # 台账已存在但表头不符且无数据行时，安全重写表头
```

- 产物：`台账/需求-架构-代码追溯矩阵.csv`（RTM_COLS）、`台账/06_范围变更台账.csv`（CHANGE_COLS）、`台账/07_范围跟踪台账.csv`（TRACK_COLS）。
- DoD：RTM 表头符合 schema、示例行可被 `metrics` 解析、06/07 台账已建表头。

## 6. 最佳实践对齐

- **PMBOK 7th**：范围基准经批准后方可变更，范围绩效域以受控基线为锚。
- **IEEE 29148**：需求可追溯、可验证、有唯一标识，RTM 覆盖 REQ→设计→实现→测试双向链。
- **MoSCoW**：优先级驱动门禁严重度判定（Must 缩水=严重，Won't 实现=蔓延）。
- **NASA SWE-059 / ASPICE**：单一事实来源 + 连续维护，杜绝审计前突击补表。

---

**文档版本**：v1.2.0 **最后更新**：2026-09-08（从 scope-change.md §环节0 抽出并扩展 RTM schema/状态词表/WBS）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
