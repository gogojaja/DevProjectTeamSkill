---
name: "architecture-design-skill"
description: "Architecture logical design sub-skill producing the 4+1 view model and C4 model with component, interface, and deployment design, enforcing the seven design principles mapped to ISO/IEC 25010. Invoke after architecture strategy analysis to produce the logical architecture design."
---

# ArchitectureDesignSkill 架构逻辑设计技能

> 版权声明详见 `../../shared/references/COPYRIGHT.md`

## 1. 基础元数据

- **技能版本**：v21.0.0　**发布**：2026-08-04　**参考标准**：4+1 视图（Kruchten）· C4（Brown）· ADD 3.0 · ISO/IEC/IEEE 42010 · ISO/IEC 25010 · 12-Factor
- **定位**：架构「逻辑设计」独立技能，负责 4+1 视图、C4 模型、组件、接口、部署设计与七原则落地检查
- **调用主体**：架构设计师子角色；由 ArchitectureManagementSkill 路由分发

## 2. 触发规则

- **触发时机**：架构策略分析评审通过后进入逻辑设计阶段
- **DoR（准入）**：策略分析已评审通过；质量属性需求矩阵已确认；技术选型已确定；需求基线（SRS+追溯矩阵）就绪

## 3. 流程（action=design_architecture）

```json
{
  "action": "design_architecture",
  "content": "架构方案/策略分析报告引用",
  "quality_attributes": "质量属性优先级列表",
  "target_platforms": "目标平台列表（如：Linux/Windows/Docker/K8s）",
  "user_confirm": "用户指令：无/同意/拒绝/查错"
}
```

执行（六项）：
1. **4+1 视图**：逻辑/进程/开发/物理视图 + 场景（+1）贯穿验证；
2. **C4 分层**：Context / Container / Component / Code；
3. **组件设计**：职责、接口、依赖、生命周期、通信（禁循环依赖）；
4. **接口设计**：API 契约（REST/RPC/gRPC）、版本管理、错误码、认证授权、限流熔断；
5. **部署设计**：物理视图、部署拓扑、平台抽象、容器化、配置外部化；
6. **七原则落地检查**：逐条验证。

详细表格见 `architecture-design-skill__resources/architecture_design_details.md`。

**DoD（完成）**：4+1 五视图齐全（场景贯穿）；C4 四层完整；组件/接口/部署文档完成；七原则合规检查逐条 ✅。

## 4. 输出规范（CSV）

- 本地 CSV 结构化架构文档：4+1 视图、C4 模型、组件/接口/部署设计、七原则合规检查表
- 设计输出作为 data-security-skill 的输入

## 5. 边界

- 仅架构设计师角色激活时执行；必须基于已评审的策略分析
- 禁止跨入数据/安全架构设计（由 data-security 子技能承载）
- 接口设计须先于开发编码完成（作为开发契约）；七原则任一 ❌ 不得进入下一环节

---

**文档版本**：v21.0.0　**最后更新**：2026-08-04
**知识产权所有**：段波（验证邮箱：duanbo.douglas@163.com）
