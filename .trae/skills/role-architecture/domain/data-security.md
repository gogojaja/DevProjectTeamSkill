---
name: "architecture-data-security-skill"
description: "Architecture data and security design sub-skill covering data architecture (ER model/data dictionary/storage strategy/data flow/lifecycle) and security architecture (STRIDE threat modeling/authentication & authorization/data security/audit chain/defense in depth), enforcing the seven design principles. Invoke after logical architecture design to produce data and security architecture."
---

# ArchitectureDataSecuritySkill 架构数据与安全设计技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能版本**：v21.0.0　**发布**：2026-08-04　**参考标准**：ISO/IEC/IEEE 42010 · ISO/IEC 25010（安全性）· OWASP ASVS / STRIDE · CIA · DAMA-DMBOK
- **定位**：架构「数据与安全」独立技能，负责数据架构与安全架构详细设计，落地七原则
- **调用主体**：架构设计师子角色；由 ArchitectureManagementSkill 路由分发；依赖逻辑设计（组件/接口）作为输入

## 2. 触发规则

- **触发时机**：逻辑设计（architecture-design-skill）评审通过后进入数据与安全设计阶段
- **DoR（准入）**：逻辑设计已评审通过；组件/接口/部署已提供；质量属性矩阵已确认（含安全性/可靠性优先级）

## 3. 流程（action=design_data_security）

```json
{
  "action": "design_data_security",
  "content": "逻辑设计方案（组件/接口/部署）引用",
  "quality_attributes": "安全性/可靠性优先的优先级列表",
  "user_confirm": "用户指令：无/同意/拒绝/查错"
}
```

- **3A 数据架构**：ER 模型；数据字典（字段/类型/约束/默认）；存储策略（选型/分库分表/读写分离/缓存）；数据流转（流向图/ETL）；生命周期（归档/销毁/保留/分级合规）；
- **3B 安全架构**：STRIDE 威胁建模（六类全覆盖）；认证授权（OAuth2/JWT/SAML、RBAC/ABAC）；数据安全（TLS/存储加密/脱敏/密钥管理）；审计链；纵深防御（网络/应用/数据多层、最小权限）。

详细表格见 `architecture-data-security-skill__resources/architecture_data_security_details.md`。

**DoD（完成）**：数据/安全架构五项完成；认证授权方案确定；数据安全三要素覆盖；审计链与纵深防御完成；七原则检查逐条 ✅。

## 4. 输出规范（CSV）

- 本地 CSV 结构化架构文档：数据架构设计、安全架构设计、数据字典、STRIDE 威胁模型

## 5. 边界

- 仅架构设计师角色激活时执行；依赖逻辑设计组件作为输入；禁止重复执行逻辑视图设计
- STRIDE 六类不得遗漏；数据安全须满足 ISO 25010 安全性质量特性与七原则「安全性」验收
- 遵循最小权限与纵深防御；七原则任一 ❌ 不得进入评审环节

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）