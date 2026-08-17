# UltraQA 多轮验证循环

> 编排器：`../SKILL.md`　上位：编排器 §5 调度规则

---

## 1. QA 循环参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_cycles` | 5 | 最大验证轮次 |
| `same_error_threshold` | 3 | 同一错误重复次数达标 → 停止循环 |
| `validator_quorum` | 3/3 | 三视角全通才算通过 |
| `timeout_per_cycle` | 15min | 单轮超时保护 |
| `regression_suite` | full | 每轮跑全量回归 |

---

## 2. 五轮验证流程

```mermaid
graph TD
    A[Cycle 1: 基线建立] --> B[Cycle 2: 修复验证]
    B --> C[Cycle 3: 安全/性能]
    C --> D[Cycle 4: 多视角评审]
    D --> E[Cycle 5: 签署回归]
    E -->|全通| F[QA签署]
    B -->|同错误≥3| G[停止→RCA]
    C -->|同错误≥3| G
    D -->|分歧| H[协商/仲裁]
```

### 2.1 Cycle 1: 基线建立
- 编译构建
- 静态分析
- 单元测试
- 集成测试
- 产出：基线测试报告 + 失败清单

### 2.2 Cycle 2: 修复验证
- 针对 Cycle 1 失败项修复
- 重跑失败测试
- 检查是否引入新失败
- 产出：修复验证报告

### 2.3 Cycle 3: 安全/性能
- 安全扫描
- 性能基准
- 依赖漏洞检查
- 产出：安全/性能报告

### 2.4 Cycle 4: 多视角评审
| 验证器 | 档位 | 聚焦 | 产出 |
|--------|------|------|------|
| Architect | S2(强模型) | 功能完整性、架构一致性 | PASS/FAIL + 证据 |
| SecurityReviewer | S2(强模型) | 威胁建模、漏洞、数据流 | PASS/FAIL + CVE 清单 |
| CodeReviewer | S2/S1 | 代码质量、测试覆盖、风格 | PASS/FAIL + 难点标注 |

**决策规则**：三视角全 PASS → 进入 Cycle 5；任一 FAIL → 进入 fix 循环 → 回 Cycle 1

### 2.5 Cycle 5: 签署回归
- 全量回归测试
- 建构产物验证
- 部署烟测
- 三视角签署 → QA 签署报告

---

## 3. 验证器清单

### 3.1 Architect (功能完整性)
```yaml
checks:
  - 需求覆盖率: 100% (每个需求点有对应测试)
  - 接口契约一致性: OpenAPI/Swagger 与实现一致
  - 数据模型完整性: 无孤儿实体、外键完整
  - 边界条件: 空值、极值、并发、权限
evidence: "需求追溯矩阵 + 测试覆盖率报告"
```

### 3.2 SecurityReviewer (安全)
```yaml
checks:
  - 静态扫描: bandit/semgrep 0 high/critical
  - 依赖漏洞: npm audit / cargo audit 0 high
  - 输入验证: 所有入口点有验证/清洗
  - 认证授权: RBAC/ABAC 正确、无越权
  - 敏感数据: 无明文密钥、PII 加密
  - 威胁建模: STRIDE 覆盖核心流程
evidence: "扫描报告 + 威胁模型文档"
```

### 3.3 CodeReviewer (质量)
```yaml
checks:
  - 风格一致性: lint 0 error
  - 复杂度: 圈复杂度 < 15、函数 < 50 行
  - 测试覆盖率: 行覆盖 ≥ 80%、分支 ≥ 70%
  - 文档: 公共 API 有 docstring
  - 重复代码: < 3% (sonarqube)
evidence: "lint/report + coverage.xml + 代码审查清单"
```

---

## 4. 签署协议

### 4.1 签署格式
```markdown
# UltraQA 签署报告

Pipeline: ultraqa-20260808-001
Cycle: 5/5
Timestamp: 2026-08-08T14:30:00Z

## 验证器签署
| 验证器 | 状态 | 信心度 | 风险范围 | 未测项 |
|--------|------|--------|----------|--------|
| Architect | ✅ PASS | high | narrow | E2E 跨服务 |
| SecurityReviewer | ✅ PASS | high | narrow | 渗透测试 |
| CodeReviewer | ✅ PASS | medium | moderate | 性能基准 |

## 总体结论
- 状态: ✅ SIGNED-OFF
- 信心度: high
- 风险: moderate (仅文档/性能基准待补)
- 部署建议: 可发布，建议 1 周内补齐未测项

## 签署人
- Architect: S2 (强模型)
- SecurityReviewer: S2 (强模型)  
- CodeReviewer: S1/S2
```

### 4.2 分歧处理
- 任一验证器 FAIL → 自动进入 fix 循环
- 三视角意见分歧（如 2 PASS 1 FAIL）：
  1. 自动协商：失败方给具体证据，其他方反驳
  2. 轮次 ≤ 2 → 仍分歧 → Architect (S2/强模型) 仲裁
  3. 仲裁结果为最终决策

---

## 5. 停止条件

| 条件 | 动作 |
|------|------|
| 所有验证器 PASS | 产出签署报告 → 完成 |
| 同一错误重复 ≥ 3 轮 | 停止 → 生成 RCA → 请求人工 |
| 单轮超时 > 15min | 熔断 → 标记超时任务 → 继续下一轮 |
| 连续 2 轮无进展 (失败数不减) | 升级 → 请求人工介入 |

---

## 6. CSV 报表规范

每轮结束产出 `台账/ultraqa_cycle{N}_{timestamp}.csv` (UTF-8 BOM)：

```csv
cycle,validator,check,status,evidence,confidence,scope-risk,not-tested
1,Architect,需求覆盖率,PASS,"追溯矩阵 42/42",high,narrow,
1,SecurityReviewer,静态扫描,FAIL,"bandit 2 high",high,narrow,渗透测试
1,CodeReviewer,测试覆盖率,PASS,"行85% 分支72%",high,narrow,
2,SecurityReviewer,静态扫描修复,PASS,"bandit 0 high",high,narrow,
...
5,Architect,最终签署,PASS,"全功能验证",high,narrow,E2E跨服务
5,SecurityReviewer,最终签署,PASS,"0 high/critical",high,narrow,渗透测试
5,CodeReviewer,最终签署,PASS,"lint 0 err cov 85%",medium,moderate,性能基准
```

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08