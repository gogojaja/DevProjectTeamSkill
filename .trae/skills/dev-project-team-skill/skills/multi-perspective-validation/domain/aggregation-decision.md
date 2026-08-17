# 聚合决策：规则/签署/异议处理/风险接受/报告模板

> 编排器：`../SKILL.md`

---

## 1. 聚合决策引擎

### 1.1 决策矩阵

| 视角组合 | 全 PASS | 1 FAIL | 多 FAIL | 有 ERROR |
|----------|---------|--------|---------|----------|
| **决策** | SIGNED_OFF | CHANGES_REQUESTED | BLOCKED | BLOCKED_ERROR |
| **行动** | 允许合并/发布 | 要求修复后重验 | 禁止合并，需重大重构 | 禁止，需修复工具/环境 |

### 1.2 决策算法
```python
def make_decision(perspective_results: Dict[str, PerspectiveResult]) -> Decision:
    """核心决策逻辑"""
    statuses = [r.status for r in perspective_results.values()]
    
    # 1. 任何 ERROR -> BLOCKED_ERROR
    if "ERROR" in statuses:
        return Decision(
            outcome="BLOCKED_ERROR",
            reason="Tool/environment failure in validation",
            requires_human=True
        )
    
    # 2. 统计 FAIL
    fail_count = statuses.count("FAIL")
    pass_count = statuses.count("PASS")
    total = len(statuses)
    
    if fail_count == 0:
        # 全 PASS
        return Decision(
            outcome="SIGNED_OFF",
            reason="All perspectives passed",
            confidence="high"
        )
    elif fail_count == 1 and pass_count >= 3:
        # 单一视角失败，其余通过 -> 条件通过
        failed = [name for name, r in perspective_results.items() if r.status == "FAIL"]
        return Decision(
            outcome="CHANGES_REQUESTED",
            reason=f"Single perspective failed: {failed[0]}",
            failed_perspectives=failed,
            confidence="medium"
        )
    elif fail_count <= 2:
        # 少数失败
        failed = [name for name, r in perspective_results.items() if r.status == "FAIL"]
        return Decision(
            outcome="CHANGES_REQUESTED",
            reason=f"Multiple perspectives failed: {', '.join(failed)}",
            failed_perspectives=failed,
            confidence="medium"
        )
    else:
        # 多数失败
        return Decision(
            outcome="BLOCKED",
            reason=f"Multiple critical failures: {fail_count}/{total} failed",
            confidence="high"
        )
```

### 1.3 严重性覆盖规则
```python
SEVERITY_OVERRIDE = {
    "critical": "BLOCKED",      # 任何 critical FAIL -> 直接阻断
    "high": "CHANGES_REQUESTED", # high FAIL -> 要求修复
    "medium": "CHANGES_REQUESTED", # medium -> 要求修复 (可配置)
    "low": "WARNING"             # low -> 仅警告
}

def apply_severity_override(decision: Decision, results: Dict) -> Decision:
    """按最高严重性覆盖决策"""
    max_severity = max(
        (max((c.severity for c in r.checks), default="low") for r in results.values()),
        default="low"
    )
    
    override = SEVERITY_OVERRIDE.get(max_severity)
    if override and decision_priority(override) > decision_priority(decision.outcome):
        return Decision(
            outcome=override,
            reason=f"Severity override: {max_severity} failure",
            confidence="high"
        )
    return decision
```

---

## 2. 签署协议

### 2.1 签署格式
```markdown
# 多视角验证签署报告

**验证 ID**: validation-20260808-001
**目标**: PR #1234 - UserService 重构
**决策**: ✅ SIGNED_OFF
**时间**: 2026-08-08T14:30:00Z

## 视角签署
| 视角 | 状态 | 签署者 | 信心度 | 关键发现 |
|------|------|--------|--------|----------|
| 架构一致性 | ✅ PASS | Architect (S2/强模型) | high | 接口契约完全一致 |
| 代码质量 | ✅ PASS | CodeReviewer (S1/S2) | high | 复杂度均<15，覆盖85% |
| 安全合规 | ✅ PASS | SecurityReviewer (S2/强模型) | high | 0 high/critical 漏洞 |
| 测试完备性 | ⚠️ CHANGES_REQUESTED | TestEngineer (S1) | medium | 缺少 E2E 测试 2 条 |
| 性能基准 | ✅ PASS | PerformanceEngineer (S1/S2) | high | P99 延迟 45ms < 200ms |

## 决策依据
- 单一视角 (测试) 发现非阻塞性问题
- 其余 4 视角全部通过
- 缺失的 E2E 测试属于已知风险，Issue #456 跟踪
- 决策：SIGNED_OFF (条件：测试视角问题在下一迭代修复)

## 风险接受单 (如适用)
| 风险 | 影响 | 缓解措施 | 负责人 | 截止日期 |
|------|------|----------|--------|----------|
| 缺少 checkout 流程 E2E | 发布后可能发现集成问题 | 下一迭代优先补全 | TestEngineer | 2026-08-15 |

## 签署
- Architect (S2/强模型): ✅ PASS
- CodeReviewer (S1/S2): ✅ PASS  
- SecurityReviewer (S2/强模型): ✅ PASS
- TestEngineer (S1): ⚠️ CHANGES_REQUESTED
- PerformanceEngineer (S1/S2): ✅ PASS

**最终决策**: SIGNED_OFF
**签署时间**: 2026-08-08T14:30:00Z
```

### 2.2 签署数据结构
```python
@dataclass
class SignedReport:
    validation_id: str
    target: ValidationTarget
    decision: Decision
    perspectives: Dict[str, PerspectiveResult]
    risk_acceptances: List[RiskAcceptance]
    signatures: Dict[str, Signature]  # perspective -> signature
    timestamp: str
    
@dataclass
class Signature:
    perspective: str
    model: str           # s0/s1/s2/s3（model_selection 档位）
    status: str          # PASS/FAIL/CHANGES_REQUESTED
    confidence: str      # high/medium/low
    signed_at: str
    notes: str
```

---

## 3. 异议处理机制

### 3.1 异议类型
| 类型 | 触发条件 | 处理流程 |
|------|----------|----------|
| **技术异议** | 视角之间结论冲突 | 自动协商 → 专家仲裁 |
| **严重性分歧** | 同一问题严重性评级不同 | 证据交换 → 仲裁 |
| **范围争议** | 验证范围理解不一致 | 澄清范围 → 重新验证 |
| **工具误报** | 认为工具产生假阳性 | 人工复核 → 标记/抑制 |

### 3.2 自动协商流程
```python
def resolve_disagreement(perspectives: Dict[str, PerspectiveResult]) -> Resolution:
    """自动协商：证据交换 + 加权投票"""
    
    # 1. 识别冲突
    conflicts = detect_conflicts(perspectives)
    if not conflicts:
        return Resolution(status="no_conflict")
    
    # 2. 证据交换轮次 (最多 2 轮)
    for round_num in range(2):
        for conflict in conflicts:
            # 各方提交额外证据
            evidence = collect_additional_evidence(conflict, perspectives)
            
            # 重新评估
            reassessed = reevaluate_with_evidence(conflict, evidence)
            
            if reassessed.consensus:
                return Resolution(status="resolved", consensus=reassessed)
    
    # 3. 专家仲裁 (Architect S2/强模型 仲裁)
    return arbitration(conflicts, perspectives)
```

### 3.3 仲裁规则
```python
def arbitration(conflicts, perspectives) -> Resolution:
    """Architect (S2/强模型) 仲裁，基于证据权重"""
    
    for conflict in conflicts:
        # 收集双方证据
        evidence_a = collect_evidence(conflict.perspective_a)
        evidence_b = collect_evidence(conflict.perspective_b)
        
        # 权重评分
        score_a = weigh_evidence(evidence_a, conflict.topic)
        score_b = weigh_evidence(evidence_b, conflict.topic)
        
        # 仲裁决策
        if score_a > score_b * 1.5:
            winner = conflict.perspective_a
        elif score_b > score_a * 1.5:
            winner = conflict.perspective_b
        else:
            # 平局 -> 保守决策 (更严格)
            winner = "stricter"
        
        return Resolution(
            status="arbitrated",
            winner=winner,
            reasoning=f"Evidence weight: {score_a:.2f} vs {score_b:.2f}"
        )
```

---

## 4. 风险接受机制

### 4.1 风险接受单模板
```markdown
# 风险接受单 (Risk Acceptance Form)

**RA-ID**: RA-20260808-001
**关联验证**: validation-20260808-001
**风险描述**: 缺少 checkout 流程 E2E 测试
**风险等级**: Medium
**潜在影响**: 发布后可能发现支付/库存集成问题，导致订单失败
**发现视角**: TestEngineer
**发现检查项**: TE-005 (E2E 覆盖)

## 风险分析
| 维度 | 评估 |
|------|------|
| 发生概率 | Medium (支付集成近期有变更) |
| 影响范围 | 订单模块 (核心业务) |
| 检测难度 | Low (用户下单即可发现) |
| 修复成本 | Low (补全 E2E 约 2 人日) |

## 缓解措施
1. **发布前**：在 Staging 环境手动执行 checkout 全流程测试
2. **发布后**：启用增强监控 (订单成功率/支付回调成功率/库存扣减成功率)
3. **回滚预案**: 准备热修复分支，30 分钟内可回滚
4. **跟踪**: Issue #456 跟踪 E2E 补全，预计 2026-08-15 完成

## 批准
- **提交人**: TestEngineer (S1)
- **审批人**: Architect (S2/强模型) ✅
- **业务负责人**: Product Owner ✅
- **批准时间**: 2026-08-08T14:30:00Z
- **有效期**: 至 2026-08-15 (E2E 补全截止)

## 签署
- Architect (S2/强模型): ✅ 批准
- Product Owner: ✅ 批准
```

### 4.2 风险接受数据结构
```python
@dataclass
class RiskAcceptance:
    ra_id: str
    validation_id: str
    risk_description: str
    risk_level: str           # Critical/High/Medium/Low
    probability: str          # High/Medium/Low
    impact: str               # Critical/High/Medium/Low
    detecting_perspective: str
    check_id: str
    mitigation: List[str]
    rollback_plan: str
    tracking_issue: str
    deadline: str
    approvers: List[str]
    approved_at: str
    expires_at: str
```

---

## 5. 报告模板

### 5.1 完整验证报告 (Markdown)
```markdown
# 多视角验证报告

## 元数据
- **验证 ID**: {validation_id}
- **目标**: {target_description}
- **触发**: {trigger_reason}
- **基线**: {baseline_ref}
- **时间**: {timestamp}

## 决策摘要
- **最终决策**: {SIGNED_OFF | CHANGES_REQUESTED | BLOCKED | BLOCKED_ERROR}
- **决策理由**: {decision_reason}
- **信心度**: {confidence}

## 视角详情
{perspective_details_table}

## 聚合分析
- **通过视角**: {pass_count}/{total}
- **失败视角**: {fail_list}
- **最高严重性**: {max_severity}
- **异议处理**: {disagreement_summary}

## 风险接受
{risk_acceptance_list}

## 签署
{signatures}

## 附件
- 完整检查清单 (CSV)
- 详细日志链接
- 基线对比报告
```

### 5.2 CSV 导出
```csv
validation_id,target,decision,perspective,check_id,check_name,status,severity,evidence,confidence
val-001,PR#1234,SIGNED_OFF,architect,ARCH-001,接口契约,PASS,high,,high
val-001,PR#1234,SIGNED_OFF,architect,ARCH-002,数据模型,FAIL,high,"User: missing updated_at",high
val-001,PR#1234,SIGNED_OFF,security,SEC-002,依赖漏洞,FAIL,high,"CVE-2024-1234 lodash@4.17.20",high
```

---

## 6. CI/CD 集成

### 6.1 GitHub Actions / GitLab CI
```yaml
# .github/workflows/validate.yml
name: Multi-Perspective Validation
on: [pull_request, push]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run multi-perspective validation
        run: |
          python -m multi_perspective_validation \
            --target ${{ github.event.pull_request.head.sha }} \
            --baseline ${{ github.event.pull_request.base.sha }} \
            --output validation-report.md
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: validation-report
          path: validation-report.md
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('validation-report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            })
```

### 6.2 门禁规则
```yaml
# 验证失败阻断合并
branch_protection:
  required_status_checks:
    - "Multi-Perspective Validation"
  required_reviews: 1
  dismiss_stale_reviews: true
```

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08