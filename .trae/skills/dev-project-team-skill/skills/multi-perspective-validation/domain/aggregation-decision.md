# 聚合決策：規則/簽署/異議處理/風險接受/報告模板

> 編排器：`../SKILL.md`

---

## 1. 聚合決策引擎

### 1.1 決策矩陣

| 視角組合 | 全 PASS | 1 FAIL | 多 FAIL | 有 ERROR |
|----------|---------|--------|---------|----------|
| **決策** | SIGNED_OFF | CHANGES_REQUESTED | BLOCKED | BLOCKED_ERROR |
| **行動** | 允許合併/發布 | 要求修復後重驗 | 禁止合併，需重大重構 | 禁止，需修復工具/環境 |

### 1.2 決策算法
```python
def make_decision(perspective_results: Dict[str, PerspectiveResult]) -> Decision:
    """核心決策邏輯"""
    statuses = [r.status for r in perspective_results.values()]
    
    # 1. 任何 ERROR -> BLOCKED_ERROR
    if "ERROR" in statuses:
        return Decision(
            outcome="BLOCKED_ERROR",
            reason="Tool/environment failure in validation",
            requires_human=True
        )
    
    # 2. 統計 FAIL
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
        # 單一視角失敗，其餘通過 -> 條件通過
        failed = [name for name, r in perspective_results.items() if r.status == "FAIL"]
        return Decision(
            outcome="CHANGES_REQUESTED",
            reason=f"Single perspective failed: {failed[0]}",
            failed_perspectives=failed,
            confidence="medium"
        )
    elif fail_count <= 2:
        # 少數失敗
        failed = [name for name, r in perspective_results.items() if r.status == "FAIL"]
        return Decision(
            outcome="CHANGES_REQUESTED",
            reason=f"Multiple perspectives failed: {', '.join(failed)}",
            failed_perspectives=failed,
            confidence="medium"
        )
    else:
        # 多數失敗
        return Decision(
            outcome="BLOCKED",
            reason=f"Multiple critical failures: {fail_count}/{total} failed",
            confidence="high"
        )
```

### 1.3 嚴重性覆蓋規則
```python
SEVERITY_OVERRIDE = {
    "critical": "BLOCKED",      # 任何 critical FAIL -> 直接阻斷
    "high": "CHANGES_REQUESTED", # high FAIL -> 要求修復
    "medium": "CHANGES_REQUESTED", # medium -> 要求修復 (可配置)
    "low": "WARNING"             # low -> 僅警告
}

def apply_severity_override(decision: Decision, results: Dict) -> Decision:
    """按最高嚴重性覆蓋決策"""
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

## 2. 簽署協議

### 2.1 簽署格式
```markdown
# 多視角驗證簽署報告

**驗證 ID**: validation-20260808-001
**目標**: PR #1234 - UserService 重構
**決策**: ✅ SIGNED_OFF
**時間**: 2026-08-08T14:30:00Z

## 視角簽署
| 視角 | 狀態 | 簽署者 | 信心度 | 關鍵發現 |
|------|------|--------|--------|----------|
| 架構一致性 | ✅ PASS | Architect (Opus) | high | 接口契約完全一致 |
| 代碼質量 | ✅ PASS | CodeReviewer (Opus) | high | 複雜度均<15，覆蓋85% |
| 安全合規 | ✅ PASS | SecurityReviewer (Sonnet) | high | 0 high/critical 漏洞 |
| 測試完備性 | ⚠️ CHANGES_REQUESTED | TestEngineer (Sonnet) | medium | 缺少 E2E 測試 2 條 |
| 性能基準 | ✅ PASS | PerformanceEngineer (Sonnet) | high | P99 延遲 45ms < 200ms |

## 決策依據
- 單一視角 (測試) 發現非阻塞性問題
- 其餘 4 視角全部通過
- 缺失的 E2E 測試屬於已知風險，Issue #456 跟蹤
- 決策：SIGNED_OFF (條件：測試視角問題在下一迭代修復)

## 風險接受單 (如適用)
| 風險 | 影響 | 緩解措施 | 負責人 | 截止日期 |
|------|------|----------|--------|----------|
| 缺少 checkout 流程 E2E | 發布後可能發現集成問題 | 下一迭代優先補全 | TestEngineer | 2026-08-15 |

## 簽署
- Architect (Opus): ✅ PASS
- CodeReviewer (Opus): ✅ PASS  
- SecurityReviewer (Sonnet): ✅ PASS
- TestEngineer (Sonnet): ⚠️ CHANGES_REQUESTED
- PerformanceEngineer (Sonnet): ✅ PASS

**最終決策**: SIGNED_OFF
**簽署時間**: 2026-08-08T14:30:00Z
```

### 2.2 簽署數據結構
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
    model: str           # Opus/Sonnet/Haiku
    status: str          # PASS/FAIL/CHANGES_REQUESTED
    confidence: str      # high/medium/low
    signed_at: str
    notes: str
```

---

## 3. 異議處理機制

### 3.1 異議類型
| 類型 | 觸發條件 | 處理流程 |
|------|----------|----------|
| **技術異議** | 視角之間結論衝突 | 自動協商 → 專家仲裁 |
| **嚴重性分歧** | 同一問題嚴重性評級不同 | 證據交換 → 仲裁 |
| **範圍爭議** | 驗證範圍理解不一致 | 澄清範圍 → 重新驗證 |
| **工具誤報** | 認為工具產生假陽性 | 人工複核 → 標記/抑制 |

### 3.2 自動協商流程
```python
def resolve_disagreement(perspectives: Dict[str, PerspectiveResult]) -> Resolution:
    """自動協商：證據交換 + 加權投票"""
    
    # 1. 識別衝突
    conflicts = detect_conflicts(perspectives)
    if not conflicts:
        return Resolution(status="no_conflict")
    
    # 2. 證據交換輪次 (最多 2 輪)
    for round_num in range(2):
        for conflict in conflicts:
            # 各方提交額外證據
            evidence = collect_additional_evidence(conflict, perspectives)
            
            # 重新評估
            reassessed = reevaluate_with_evidence(conflict, evidence)
            
            if reassessed.consensus:
                return Resolution(status="resolved", consensus=reassessed)
    
    # 3. 專家仲裁 (Architect Opus 仲裁)
    return arbitration(conflicts, perspectives)
```

### 3.3 仲裁規則
```python
def arbitration(conflicts, perspectives) -> Resolution:
    """Architect (Opus) 仲裁，基於證據權重"""
    
    for conflict in conflicts:
        # 收集雙方證據
        evidence_a = collect_evidence(conflict.perspective_a)
        evidence_b = collect_evidence(conflict.perspective_b)
        
        # 權重評分
        score_a = weigh_evidence(evidence_a, conflict.topic)
        score_b = weigh_evidence(evidence_b, conflict.topic)
        
        # 仲裁決策
        if score_a > score_b * 1.5:
            winner = conflict.perspective_a
        elif score_b > score_a * 1.5:
            winner = conflict.perspective_b
        else:
            # 平局 -> 保守決策 (更嚴格)
            winner = "stricter"
        
        return Resolution(
            status="arbitrated",
            winner=winner,
            reasoning=f"Evidence weight: {score_a:.2f} vs {score_b:.2f}"
        )
```

---

## 4. 風險接受機制

### 4.1 風險接受單模板
```markdown
# 風險接受單 (Risk Acceptance Form)

**RA-ID**: RA-20260808-001
**關聯驗證**: validation-20260808-001
**風險描述**: 缺少 checkout 流程 E2E 測試
**風險等級**: Medium
**潛在影響**: 發布後可能發現支付/庫存集成問題，導致訂單失敗
**發現視角**: TestEngineer
**發現檢查項**: TE-005 (E2E 覆蓋)

## 風險分析
| 維度 | 評估 |
|------|------|
| 發生概率 | Medium (支付集成近期有變更) |
| 影響範圍 | 訂單模塊 (核心業務) |
| 檢測難度 | Low (用戶下單即可發現) |
| 修復成本 | Low (補全 E2E 約 2 人日) |

## 緩解措施
1. **發布前**：在 Staging 環境手動執行 checkout 全流程測試
2. **發布後**：啟用增強監控 (訂單成功率/支付回調成功率/庫存扣減成功率)
3. **回滾預案**: 準備熱修復分支，30 分鐘內可回滾
4. **跟蹤**: Issue #456 跟蹤 E2E 補全，預計 2026-08-15 完成

## 批准
- **提交人**: TestEngineer (Sonnet)
- **審批人**: Architect (Opus) ✅
- **業務負責人**: Product Owner ✅
- **批准時間**: 2026-08-08T14:30:00Z
- **有效期**: 至 2026-08-15 (E2E 補全截止)

## 簽署
- Architect (Opus): ✅ 批准
- Product Owner: ✅ 批准
```

### 4.2 風險接受數據結構
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

## 5. 報告模板

### 5.1 完整驗證報告 (Markdown)
```markdown
# 多視角驗證報告

## 元數據
- **驗證 ID**: {validation_id}
- **目標**: {target_description}
- **觸發**: {trigger_reason}
- **基線**: {baseline_ref}
- **時間**: {timestamp}

## 決策摘要
- **最終決策**: {SIGNED_OFF | CHANGES_REQUESTED | BLOCKED | BLOCKED_ERROR}
- **決策理由**: {decision_reason}
- **信心度**: {confidence}

## 視角詳情
{perspective_details_table}

## 聚合分析
- **通過視角**: {pass_count}/{total}
- **失敗視角**: {fail_list}
- **最高嚴重性**: {max_severity}
- **異議處理**: {disagreement_summary}

## 風險接受
{risk_acceptance_list}

## 簽署
{signatures}

## 附件
- 完整檢查清單 (CSV)
- 詳細日誌鏈接
- 基線對比報告
```

### 5.2 CSV 導出
```csv
validation_id,target,decision,perspective,check_id,check_name,status,severity,evidence,confidence
val-001,PR#1234,SIGNED_OFF,architect,ARCH-001,接口契約,PASS,high,,high
val-001,PR#1234,SIGNED_OFF,architect,ARCH-002,數據模型,FAIL,high,"User: missing updated_at",high
val-001,PR#1234,SIGNED_OFF,security,SEC-002,依賴漏洞,FAIL,high,"CVE-2024-1234 lodash@4.17.20",high
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

### 6.2 門禁規則
```yaml
# 驗證失敗阻斷合併
branch_protection:
  required_status_checks:
    - "Multi-Perspective Validation"
  required_reviews: 1
  dismiss_stale_reviews: true
```

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08