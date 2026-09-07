# OPT-REVIEW-002 实施计划

> **关联方案**：OPT-REVIEW-002 评审能力全面优化方案
> **评审结论**：4.15/5.0 Go（2026-09-07 五维评审通过）
> **编制日期**：2026-09-07

---

## Phase 1：文档评审 + 代码审查（12.5h）

| 序号 | 交付物 | 工时 | 依赖 | 状态 |
|:---:|---|:---:|---|:---:|
| 1.1 | T-01 xlsx_dump | 0.5h | 无 | DONE |
| 1.2 | T-03 review_report_gen | 1.0h | 无 | DONE |
| 1.3 | T-06 xlsx_verify | 1.0h | T-01 | DONE |
| 1.4 | T-08 code_review_agent | 4.0h | git + 静态分析 | DONE |
| 1.5 | S-01 xlsx-requirement-review | 3.0h | T-01/T-03 | DONE |
| 1.6 | S-04 code-review-agent | 3.0h | T-08 | DONE |

**验收标准**：
- T-01：导出 xlsx 全工作表内容，UTF-8 编码正确
- T-03：输入缺陷 JSON 输出 2 份标准 CSV
- T-06：修复后 xlsx 逐条验证，标记已修复/未修复
- T-08：评审最近 3 次 commit，输出结构化报告
- S-01：端到端评审 xlsx，缺陷清单完整
- S-04：代码审查技能触发 + 报告生成

---

## Phase 2：安全 + 需求质量 + 修复闭环（14.5h）

| 序号 | 交付物 | 工时 | 依赖 | 状态 |
|:---:|---|:---:|---|:---:|
| 2.1 | T-09 dep_vuln_scan | 3.0h | pip-audit/OSV | TODO |
| 2.2 | T-11 req_quality | 3.0h | 无 | TODO |
| 2.3 | T-04 defect_ledger_sync | 1.5h | 无 | TODO |
| 2.4 | T-05 xlsx_cell_fix | 1.5h | openpyxl | TODO |
| 2.5 | S-02 xlsx-auto-fix | 2.0h | T-05/T-06 | TODO |
| 2.6 | S-05 security-scan-suite | 2.0h | T-09 | TODO |
| 2.7 | S-06 review-recheck | 1.5h | T-06 | TODO |

---

## Phase 3：架构 + 投产 + 度量（13.5h）

| 序号 | 交付物 | 工时 | 依赖 | 状态 |
|:---:|---|:---:|---|:---:|
| 3.1 | T-02 xlsx_diff | 1.0h | T-01 | TODO |
| 3.2 | T-07 docx_structure_extract | 1.5h | python-docx | TODO |
| 3.3 | T-10 arch_compliance | 3.0h | ADR 目录 | TODO |
| 3.4 | T-12 env_compare | 2.0h | 无 | TODO |
| 3.5 | T-13 review_metrics | 2.0h | 评审报告+台账 | TODO |
| 3.6 | S-03 docx-requirement-review | 4.0h | T-07 | TODO |

---

## 里程碑

| 里程碑 | 内容 | 预计完成 |
|:---:|------|:---:|
| M1 | Phase 1 完成：文档评审自动化 + AI 代码审查 | 本会话 |
| M2 | Phase 2 完成：安全扫描 + 需求质量 + 修复闭环 | +2 人天 |
| M3 | Phase 3 完成：架构合规 + 环境比对 + 效能度量 | +2 人天 |
