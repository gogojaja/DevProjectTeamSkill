# 架構驗證：契約/模型/邊界/決策追溯/ADR 一致性

> 編排器：`../SKILL.md`

---

## 1. 驗證範疇

| 領域 | 檢查點 | 嚴重性 | 自動化 |
|------|--------|--------|--------|
| 接口契約 | OpenAPI/Protobuf 與實現一致 | 高 | ✅ |
| 數據模型 | 實體/關係/約束完整 | 高 | ✅ |
| 服務邊界 | 領域劃分/職責單一/低耦合 | 中 | 半自動 |
| 依賴方向 | 無循環/分層正確/無反向依賴 | 高 | ✅ |
| ADR 一致性 | 實現符合架構決策記錄 | 高 | 半自動 |
| 非功能需求 | 可擴展/可觀測/可部署/安全 | 中 | 人工 |

---

## 2. 核心檢查清單

### 2.1 接口契約一致性 (ARCH-001)
```python
def verify_contract_consistency(spec_path: str, impl_path: str) -> CheckResult:
    """OpenAPI/Protobuf 與實現一致性"""
    spec = parse_spec(spec_path)
    impl = extract_routes(impl_path)
    
    mismatches = []
    for endpoint in spec.endpoints:
        if endpoint not in impl:
            mismatches.append(f"Missing: {endpoint.method} {endpoint.path}")
        else:
            # 檢查參數/響應/狀態碼
            diff = diff_schema(endpoint.schema, impl[endpoint].schema)
            if diff:
                mismatches.append(f"Schema diff {endpoint}: {diff}")
    
    return CheckResult(
        id="ARCH-001",
        status="PASS" if not mismatches else "FAIL",
        evidence=mismatches
    )
```

### 2.2 數據模型完整性 (ARCH-002)
```python
def verify_data_model(models_path: str) -> CheckResult:
    """實體/關係/約束/索引完整性"""
    issues = []
    for model in parse_models(models_path):
        # 必填字段
        if not model.has_field("id"): issues.append(f"{model.name}: missing id")
        if not model.has_field("created_at"): issues.append(f"{model.name}: missing created_at")
        if not model.has_field("updated_at"): issues.append(f"{model.name}: missing updated_at")
        
        # 關係完整性
        for rel in model.relationships:
            if not target_exists(rel.target): issues.append(f"Broken ref: {rel}")
        
        # 索引策略
        if not model.has_index("id"): issues.append(f"{model.name}: missing PK index")
    
    return CheckResult(id="ARCH-002", status="PASS" if not issues else "FAIL", evidence=issues)
```

### 2.3 服務邊界與依賴方向 (ARCH-003/004)
```python
def verify_service_boundaries(arch_config: str) -> CheckResult:
    """領域劃分/職責單一/依賴方向/無循環"""
    g = build_dependency_graph(arch_config)
    
    issues = []
    # 循環依賴
    cycles = find_cycles(g)
    for cycle in cycles:
        issues.append(f"Cycle: {' -> '.join(cycle)}")
    
    # 反向依賴 (presentation -> domain 等)
    for edge in g.edges:
        if violates_layering(edge):
            issues.append(f"Layer violation: {edge}")
    
    # 職責過重
    for node, out_deg in g.out_degree():
        if out_deg > 10:
            issues.append(f"God service: {node} ({out_deg} deps)")
    
    return CheckResult(id="ARCH-003/004", status="PASS" if not issues else "FAIL", evidence=issues)
```

### 2.4 ADR 一致性 (ARCH-005)
```python
def verify_adr_consistency(adr_dir: str, codebase: str) -> CheckResult:
    """實現符合架構決策"""
    issues = []
    for adr in parse_adrs(adr_dir):
        if adr.status != "accepted": continue
        
        # 提取決策規則
        rules = extract_rules(adr.content)
        for rule in rules:
            violations = find_violations(rule, codebase)
            if violations:
                issues.append(f"ADR-{adr.id} violation: {rule} -> {violations[:3]}")
    
    return CheckResult(id="ARCH-005", status="PASS" if not issues else "FAIL", evidence=issues)
```

---

## 3. 自動化工具鏈

| 工具 | 用途 | 集成方式 |
|------|------|----------|
| `spectral` | OpenAPI 規範驗證 | CI pipeline |
| `sqlfluff` / `prisma validate` | Schema 驗證 | pre-commit |
| `madge` / `depcruise` | 依賴圖/循環檢測 | CI gate |
| `archunit` (Java) / `import-linter` (Py) | 架構規則 | 測試套件 |
| 自定義 ADR parser | 決策追溯 | 專用腳本 |

---

## 4. 證據與報告格式

```json
{
  "perspective": "architect",
  "checks": [
    {"id": "ARCH-001", "name": "接口契約一致性", "status": "PASS", "evidence": [], "severity": "high"},
    {"id": "ARCH-002", "name": "數據模型完整性", "status": "FAIL", "evidence": ["User: missing updated_at"], "severity": "high"},
    {"id": "ARCH-003", "name": "服務邊界", "status": "PASS", "evidence": [], "severity": "medium"},
    {"id": "ARCH-004", "name": "依賴方向", "status": "FAIL", "evidence": ["Cycle: auth -> user -> billing -> auth"], "severity": "high"},
    {"id": "ARCH-005", "name": "ADR 一致性", "status": "PASS", "evidence": [], "severity": "high"}
  ],
  "summary": "發現 2 項高嚴重性違規：依賴循環 + 缺少 updated_at",
  "confidence": "high",
  "tokens_used": 800
}
```

---

## 5. 門禁閾值

| 檢查項 | 門禁 | 可配置 |
|--------|------|--------|
| 循環依賴 | 0 容忍 | 否 |
| 契約不一致 | 0 容忍 | 否 |
| 缺失必要字段 | 0 容忍 | 是 (legacy 例外) |
| ADR 違規 | 0 容忍 | 是 (標記例外) |
| God service (>10 deps) | 警告 | 是 |

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08