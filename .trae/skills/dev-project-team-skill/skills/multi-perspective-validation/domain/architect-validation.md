# 架构验证：契约/模型/边界/决策追溯/ADR 一致性

> 编排器：`../SKILL.md`

---

## 1. 验证范畴

| 领域 | 检查点 | 严重性 | 自动化 |
|------|--------|--------|--------|
| 接口契约 | OpenAPI/Protobuf 与实现一致 | 高 | ✅ |
| 数据模型 | 实体/关系/约束完整 | 高 | ✅ |
| 服务边界 | 领域划分/职责单一/低耦合 | 中 | 半自动 |
| 依赖方向 | 无循环/分层正确/无反向依赖 | 高 | ✅ |
| ADR 一致性 | 实现符合架构决策记录 | 高 | 半自动 |
| 非功能需求 | 可扩展/可观测/可部署/安全 | 中 | 人工 |

---

## 2. 核心检查清单

### 2.1 接口契约一致性 (ARCH-001)
```python
def verify_contract_consistency(spec_path: str, impl_path: str) -> CheckResult:
    """OpenAPI/Protobuf 与实现一致性"""
    spec = parse_spec(spec_path)
    impl = extract_routes(impl_path)
    
    mismatches = []
    for endpoint in spec.endpoints:
        if endpoint not in impl:
            mismatches.append(f"Missing: {endpoint.method} {endpoint.path}")
        else:
            # 检查参数/响应/状态码
            diff = diff_schema(endpoint.schema, impl[endpoint].schema)
            if diff:
                mismatches.append(f"Schema diff {endpoint}: {diff}")
    
    return CheckResult(
        id="ARCH-001",
        status="PASS" if not mismatches else "FAIL",
        evidence=mismatches
    )
```

### 2.2 数据模型完整性 (ARCH-002)
```python
def verify_data_model(models_path: str) -> CheckResult:
    """实体/关系/约束/索引完整性"""
    issues = []
    for model in parse_models(models_path):
        # 必填字段
        if not model.has_field("id"): issues.append(f"{model.name}: missing id")
        if not model.has_field("created_at"): issues.append(f"{model.name}: missing created_at")
        if not model.has_field("updated_at"): issues.append(f"{model.name}: missing updated_at")
        
        # 关系完整性
        for rel in model.relationships:
            if not target_exists(rel.target): issues.append(f"Broken ref: {rel}")
        
        # 索引策略
        if not model.has_index("id"): issues.append(f"{model.name}: missing PK index")
    
    return CheckResult(id="ARCH-002", status="PASS" if not issues else "FAIL", evidence=issues)
```

### 2.3 服务边界与依赖方向 (ARCH-003/004)
```python
def verify_service_boundaries(arch_config: str) -> CheckResult:
    """领域划分/职责单一/依赖方向/无循环"""
    g = build_dependency_graph(arch_config)
    
    issues = []
    # 循环依赖
    cycles = find_cycles(g)
    for cycle in cycles:
        issues.append(f"Cycle: {' -> '.join(cycle)}")
    
    # 反向依赖 (presentation -> domain 等)
    for edge in g.edges:
        if violates_layering(edge):
            issues.append(f"Layer violation: {edge}")
    
    # 职责过重
    for node, out_deg in g.out_degree():
        if out_deg > 10:
            issues.append(f"God service: {node} ({out_deg} deps)")
    
    return CheckResult(id="ARCH-003/004", status="PASS" if not issues else "FAIL", evidence=issues)
```

### 2.4 ADR 一致性 (ARCH-005)
```python
def verify_adr_consistency(adr_dir: str, codebase: str) -> CheckResult:
    """实现符合架构决策"""
    issues = []
    for adr in parse_adrs(adr_dir):
        if adr.status != "accepted": continue
        
        # 提取决策规则
        rules = extract_rules(adr.content)
        for rule in rules:
            violations = find_violations(rule, codebase)
            if violations:
                issues.append(f"ADR-{adr.id} violation: {rule} -> {violations[:3]}")
    
    return CheckResult(id="ARCH-005", status="PASS" if not issues else "FAIL", evidence=issues)
```

---

## 3. 自动化工具链

| 工具 | 用途 | 集成方式 |
|------|------|----------|
| `spectral` | OpenAPI 规范验证 | CI pipeline |
| `sqlfluff` / `prisma validate` | Schema 验证 | pre-commit |
| `madge` / `depcruise` | 依赖图/循环检测 | CI gate |
| `archunit` (Java) / `import-linter` (Py) | 架构规则 | 测试套件 |
| 自定义 ADR parser | 决策追溯 | 专用脚本 |

---

## 4. 证据与报告格式

```json
{
  "perspective": "architect",
  "checks": [
    {"id": "ARCH-001", "name": "接口契约一致性", "status": "PASS", "evidence": [], "severity": "high"},
    {"id": "ARCH-002", "name": "数据模型完整性", "status": "FAIL", "evidence": ["User: missing updated_at"], "severity": "high"},
    {"id": "ARCH-003", "name": "服务边界", "status": "PASS", "evidence": [], "severity": "medium"},
    {"id": "ARCH-004", "name": "依赖方向", "status": "FAIL", "evidence": ["Cycle: auth -> user -> billing -> auth"], "severity": "high"},
    {"id": "ARCH-005", "name": "ADR 一致性", "status": "PASS", "evidence": [], "severity": "high"}
  ],
  "summary": "发现 2 项高严重性违规：依赖循环 + 缺少 updated_at",
  "confidence": "high",
  "tokens_used": 800
}
```

---

## 5. 门禁阈值

| 检查项 | 门禁 | 可配置 |
|--------|------|--------|
| 循环依赖 | 0 容忍 | 否 |
| 契约不一致 | 0 容忍 | 否 |
| 缺失必要字段 | 0 容忍 | 是 (legacy 例外) |
| ADR 违规 | 0 容忍 | 是 (标记例外) |
| God service (>10 deps) | 警告 | 是 |

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08