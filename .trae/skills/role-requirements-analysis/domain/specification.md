---
name: "requirements-specification-skill"
description: "Requirements specification sub-skill writing IEEE 830 standard requirement specifications (SRS) as a CSV document set with 10 Sheets mapping to IEEE Std 830-1998 sections, applying the REQ-<dimension>-<module>-<sequence> numbering rule, and running an eight-characteristic quality validation with gate conditions. Invoke when writing or validating the SRS document."
---

# RequirementsSpecificationSkill 需求规格化（SRS 编写）技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 触发规则

- **定位/调用**：需求工程「规格化」阶段技能；由 requirements-analysis-skill 路由分发，DevProjectTeamSkill 需求分析师子角色主动调用（仅调用时临时加载，不常驻上下文）
- **触发时机**：需求编写环节、SRS 质量校验
- **存储介质**：`SRS_v<版本号>/`、`SRS质量校验报告.csv`
- **参考标准**：IEEE Std 830-1998、ISO/IEC/IEEE 29148:2018
- **入参**：`{"action": "document_requirements", "stage": "需求收集/需求分析/需求编写/需求评审", "content": "分析结果/SRS文档章节", "project_context": "项目名称/范围边界/相关方/约束条件", "dimensions": "已选维度代码，决定 SRS Sheet 覆盖范围", "user_confirm": "无/同意/拒绝"}`

| action | 作用 | 触发场景 |
|--------|------|----------|
| `document_requirements` | 编写 IEEE 830 标准化 SRS 文档 | 需求编写环节 |

## 2. 流程（document_requirements）

**SRS 结构**：10 Sheet 映射 IEEE 830 章节 → 需求编号规则 `REQ-<维度>-<模块>-<序号>` → 八项质量特性校验。详见 `.//requirements_specification_details.md`。

**SRS Sheet 结构**：1-引言 / 2-总体描述 / 3-外部接口需求 / 4-功能需求 / 5-性能需求 / 6-设计约束 / 7-质量属性 / 8-其他需求 / 9-附录 / 10-追溯矩阵。

**质量校验**：正确性/无歧义性/完整性/一致性/可验证性/可追踪性/可修改性七项校验 + 性能指标量化标准，逐项检查后输出校验报告与总通过率。

## 3. 输出规范

- `SRS_v<版本号>/`（10 章 10 个 CSV）；`SRS质量校验报告.csv`（质量校验项 + 总通过率）

**质量门禁（向评审环节流转前）**：① SRS 质量校验全部通过；② 追溯矩阵 100% 填充无断链；③ 需求编号规则一致无重复。

## 4. 边界（刹车规则）

- 质量校验 3 项以上 ❌ → 暂停返回分析环节补充
- 需新增需求 → 转变更审计，禁止直接写入
- 追溯矩阵出现未填项或编号重复 → 暂停编写，修正后继续

---

> 目录规范详见 `../../shared/references/directory_structure.md`
> 协作接口详见 `../../shared/references/api_contracts.md`

**文档版本**：v21.0.0 | **最后更新**：2026-08-02 | **知识产权所有**：段波（duanbo.douglas@163.com）