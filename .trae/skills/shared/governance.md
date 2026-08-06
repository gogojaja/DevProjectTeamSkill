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
| `handover_export` | 交接/归档导出 | 项目收尾 |

## 2. 台账与评审输出

- 主台账 CSV（UTF-8 with BOM）按 `../shared/references/directory_structure.md` 布局；禁止新 .xlsx；
- `stage_review` 输出 CSV：`评审报告_<对象>_<版本>_<数据|缺陷|逐原则|范围|角色>.csv`，仅回显首 5 行 + 行数；
- 评审五维：范围/进度/质量/风险/安全；门禁逐阶段特殊检查按各角色包约定。

## 3. 铁律

评审/变更/门禁/固化/归档禁止子角色自主处理，一律经总控包；高危文件操作先 `security_audit`；审计链非删除；固化前 `交接文档.md` 断点区必须刷新（solidify.sh）。

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）