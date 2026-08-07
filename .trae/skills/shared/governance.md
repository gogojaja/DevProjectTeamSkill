# governance.md — 总控保障（台账/评审/门禁/固化/审计）（单源共享）

> 源：原 project-monitor-skill + project-governance-skill。被 role-governance 引用。
> 全体系唯一台账读写中枢；所有评审/变更/门禁/基线/归档/交接统一经此执行。

## 1. action 指令

| action | 作用 | 触发 |
|--------|------|------|
| `create_baseline` | 台账基线初始化 | 项目启动阶段 |
| `stage_review` | 五维阶段评审（输出 CSV） | 各阶段门禁前 |
| `check_gate` | 门禁校验 | 阶段结束 |
| `change_audit` | 变更审计（五维影响评估） | 范围/内容变更 |
| `register_change` | 变更登记 | 审计通过后 |
| `risk_scan` | 风险扫描 | 定期/阶段切换 |
| `progress_update` | 里程碑/EVM 更新 | 周期 |
| `security_audit` | 高危操作预审计 + 审计链 | 高危文件操作 |
| `solidify_baseline` | 基线固化 + 快照 | 阶段门禁通过 |
| `release_gate` | 发布级门禁（含自动化质量阈值） | 迭代配置 发布点=Y |
| `iteration_review` | 迭代末轻量评审 + 回顾 | 每迭代末 |
| `handover_export` | 交接/归档导出 | 项目收尾 |

## 2. 门禁分级（标准 + 敏捷迭代）

| 级别 | 时机 | 内容 | 固化 |
|------|------|------|------|
| 阶段级（标准模式） | 每阶段末 | `stage_review` 五维 + `check_gate` | `solidify_baseline` |
| 迭代级（敏捷模式） | 每迭代末 | `iteration_review`（变更审计+缺陷门禁+台账更新+回顾） | 不固化基线 |
| **发布级（任何模式不可裁剪）** | 敏捷 `发布点=Y` | 完整 `stage_review` + `check_gate` + 自动化质量阈值 + 全套产出 | `solidify_baseline` |

**发布级 check_gate 自动化质量阈值（P1-1）**：自动化测试通过率 ≥95%；关键路径用例全绿（阻断级 0 遗留）；SAST/SCAN 无高危；安全审计（高危操作）通过。

**门禁防绕过机制（P2-4）**：`release_gate` 由 role-governance 独立执行；`18_迭代配置.csv` 无 `发布点=Y` 记录时禁止进入投产（role-deployment），杜绝无门禁发布。

**迭代回顾（P0-2）**：`iteration_review` 末输出 `02_迭代回顾.csv`（做得好/需改进/行动项），作下迭代改进输入（PDCA 闭环）。

## 2a. 台账与评审输出

- 主台账 CSV（UTF-8 with BOM）按 `../shared/references/directory_structure.md` 布局；禁止新 .xlsx；
- `stage_review` 输出 CSV：`评审报告_<对象>_<版本>_<数据|缺陷|逐原则|范围|角色>.csv`，仅回显首 5 行 + 行数；
- 评审五维：范围/进度/质量/风险/安全；门禁逐阶段特殊检查按各角色包约定。

## 3. 铁律

评审/变更/门禁/固化/归档禁止子角色自主处理，一律经总控包；高危文件操作先 `security_audit`；审计链非删除；固化前 `交接文档.md` 断点区必须刷新（solidify.sh）。

---

**文档版本**：v21.2.1　**最后更新**：2026-08-06（新增门禁分级/发布级阈值/防绕过/迭代回顾）
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）