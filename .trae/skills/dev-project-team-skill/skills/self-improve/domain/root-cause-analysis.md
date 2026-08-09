# 根因分析：5-Why / 魚骨圖 / 優先級排序

> 編排器：`../SKILL.md`

---

## 1. 根因分析架構

### 1.1 分析流程
```mermaid
graph LR
  A[偏差清單] --> B[5-Why 逐層問因]
  B --> C[魚骨圖分類]
  C --> D[根因確認]
  D --> E[可改進點提取]
  E --> F[優先級排序]
```

### 1.2 分析原則
- **追根到底**：至少問 5 層「為什麼」，直到無可改進的系統性原因；
- **分類審視**：按人/流程/工具/標準/環境五大類檢查，避免單一歸因；
- **數據支撐**：每個「為什麼」都要有依據，禁止臆測；
- **可改進性**：根因必須對應可改進點，否則繼續深挖；
- **聚焦主因**：一個偏差通常有多因，找主因（80% 影響）優先。

---

## 2. 5-Why 分析

### 2.1 方法
```python
class FiveWhyAnalyzer:
    """5-Why 逐層問因"""
    
    def __init__(self):
        self.depth_limit = 5
    
    def analyze(self, deviation: Deviation) -> RootCause:
        """對偏差執行 5-Why"""
        causes = []
        current = deviation.description
        depth = 0
        
        while depth < self.depth_limit:
            question = f"為什麼：{current}？"
            answer = self._ask(question)
            
            if not answer or self._is_systemic_root(answer):
                # 到達系統性根因
                causes.append(Answer(level=depth, question=question, answer=answer, is_root=True))
                break
            
            causes.append(Answer(level=depth, question=question, answer=answer, is_root=False))
            current = answer
            depth += 1
        
        return RootCause(
            deviation=deviation,
            chain=causes,
            root= causes[-1].answer if causes else deviation.description,
            improvable= self._check_improvable(causes[-1].answer) if causes else False
        )
    
    def _is_systemic_root(self, answer: str) -> bool:
        """判斷是否為系統性根因"""
        systemic_markers = ["標準缺失", "規範未定義", "流程未覆蓋", "無檢查點",
                            "約束衝突", "資源不足", "沒有模板"]
        return any(m in answer for m in systemic_markers)
    
    def _check_improvable(self, root: str) -> bool:
        """檢查根因是否可改進"""
        improvable_markers = ["補", "加", "更新", "重寫", "優化", "新增", "調整"]
        return any(m in root for m in improvable_markers)
```

### 2.2 典型 5-Why 鏈
```
偏差：技能 A 觸發詞 X 下未加載
├─ 為什麼①：description 沒有觸發詞 X
│   └─ 為什麼②：編寫時按模板填但漏了
│       └─ 為什麼③：結構校驗只查 description 有無，不查觸發詞覆蓋
│           └─ 為什麼④：校驗清單沒有「觸發詞覆蓋」項
│               └─ 為什麼⑤：skill-authoring 五步第 3 步校驗規則不完整  ← 系統根因
```
→ 可改進點：authoring.md 結構校驗增加「觸發詞覆蓋率」檢查。

---

## 3. 魚骨圖分析

### 3.1 六大分類
| 分類 | 檢查項 | 典型根因 |
|------|--------|----------|
| 人 (People) | 操作者技能、經驗、疏忽 | 漏步驟、誤操作、模板漏填 |
| 流程 (Process) | 步驟、檢查點、門禁 | 跳步、無校驗、繞過門禁 |
| 工具 (Tools) | 腳本、腳本邏輯、兼容 | 腳本 bug、路徑硬編碼、版本不符 |
| 標準 (Standards) | 規範、模板、約束 | 標準缺失、約束衝突、模板過期 |
| 環境 (Environment) | 平台、網絡、依賴 | 平台差異、網絡不穩、依賴缺失 |
| 數據 (Data) | 輸入、格式、內容 | 數據錯、格式不合規、內容過期 |

### 3.2 魚骨分類實現
```python
class FishboneAnalyzer:
    """魚骨圖分類分析"""
    
    CATEGORIES = ["人", "流程", "工具", "標準", "環境", "數據"]
    
    KEYWORD_MAP = {
        "人": ["漏", "忘", "誤", "手動", "疏忽", "操作"],
        "流程": ["跳", "繞", "缺步驟", "無檢查", "門禁", "審批"],
        "工具": ["腳本", "路徑", "硬編碼", "兼容", "版本", "命令"],
        "標準": ["規範", "模板", "約束", "標準", "政策", "規定"],
        "環境": ["網絡", "平台", "依賴", "權限", "系統", "容器"],
        "數據": ["格式", "內容", "CSV", "編碼", "欄位", "欄位值"],
    }
    
    def classify(self, cause_text: str) -> List[str]:
        """將原因分類到魚骨類別"""
        matched = []
        for category, keywords in self.KEYWORD_MAP.items():
            if any(k in cause_text for k in keywords):
                matched.append(category)
        return matched or ["其他"]
    
    def build_fishbone(self, causes: List[str]) -> FishboneDiagram:
        """構建魚骨圖數據"""
        diagram = FishboneDiagram()
        for cause in causes:
            categories = self.classify(cause)
            for cat in categories:
                diagram.add_bone(cat, cause)
        return diagram
```

---

## 4. 根因確認

### 4.1 驗證規則
| 規則 | 說明 |
|------|------|
| 復現性 | 根因可復現偏差現象（驗證因果） |
| 可控性 | 根因在技能庫/流程可控範圍內 |
| 唯一性 | 排除掉不可能因素後留下的（歸謬法） |
| 可改進 | 對根因的改進能消除偏差 |

### 4.2 確認方法
```python
class RootCauseValidator:
    """根因驗證"""
    
    def validate(self, root_cause: RootCause) -> ValidationResult:
        """驗證根因有效性"""
        checks = []
        
        # 1. 復現性驗證
        if self._can_reproduce(root_cause):
            checks.append(Check(name="復現性", passed=True, note="可復現"))
        else:
            checks.append(Check(name="復現性", passed=False, note="無法復現，需更多數據"))
        
        # 2. 可控性驗證
        controllable = any(m in root_cause.root for m in ["標準", "流程", "工具", "技能", "腳本", "模板"])
        checks.append(Check(name="可控性", passed=controllable, 
                           note="可控" if controllable else "超出技能庫範圍"))
        
        # 3. 可改進性
        checks.append(Check(name="可改進性", passed=root_cause.improvable,
                           note="可改進" if root_cause.improvable else "需重新分析"))
        
        return ValidationResult(
            valid=all(c.passed for c in checks),
            checks=checks
        )
```

---

## 5. 可改進點提取與優先級

### 5.1 可改進點模型
```python
@dataclass
class ImprovementPoint:
    id: str                  # IMP-001
    root_cause: str          # 對應根因
    target: str              # 改進目標（技能/流程/工具/標準）
    proposal: str            # 改進方向
    expected_benefit: str    # 預期收益
    cost: str                # 成本（低/中/高）
    risk: str                # 風險（低/中/高）
    priority: str            # P0/P1/P2/P3
    
    def score(self) -> float:
        """優先級得分：收益 / 成本"""
        benefit_score = {"高": 3, "中": 2, "低": 1}.get(self.expected_benefit, 1)
        cost_score = {"低": 1, "中": 2, "高": 3}.get(self.cost, 2)
        return benefit_score / cost_score
```

### 5.2 優先級矩陣
| 收益 \ 成本 | 低成本 | 中成本 | 高成本 |
|------------|--------|--------|--------|
| 高收益 | **P0 立即做** | P1 近期做 | P2 規劃做 |
| 中收益 | P1 近期做 | P2 規劃做 | P3 緩議 |
| 低收益 | P2 規劃做 | P3 緩議 | P3 不做 |

### 5.3 排序實現
```python
def prioritize(points: List[ImprovementPoint]) -> List[ImprovementPoint]:
    """按得分排序並賦優先級"""
    for p in points:
        score = p.score()
        if score >= 2.0 and p.expected_benefit == "高":
            p.priority = "P0"
        elif score >= 1.0:
            p.priority = "P1"
        elif score >= 0.5:
            p.priority = "P2"
        else:
            p.priority = "P3"
    
    rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return sorted(points, key=lambda p: rank[p.priority])
```

---

## 6. 分析輸出

### 6.1 根因分析報告
```markdown
## 根因分析報告
- **偏差**：DEV-001 技能 A 觸發詞 X 下未加載
- **5-Why 鏈**：
  1. description 沒有觸發詞 X
  2. 編寫時按模板填但漏了
  3. 結構校驗只查 description 有無
  4. 校驗清單沒有觸發詞覆蓋項
  5. **authoring.md 第 3 步校驗規則不完整** ← 系統根因
- **魚骨分類**：標準（校驗規則缺失）
- **可改進點**：IMP-001 補 authoring.md 結構校驗觸發詞覆蓋率
- **優先級**：P1（中收益低成本）
```

### 6.2 可改進點清單
```csv
id,root_cause,target,proposal,expected_benefit,cost,risk,priority
IMP-001,authoring.md校驗規則不完整,標準,結構校驗補觸發詞覆蓋率檢查,中,低,低,P1
IMP-002,腳本路徑硬編碼,工具,deploy路徑改自定位,高,中,低,P0
```

---

## 7. 最佳實踐

1. **5 層夠用**：多數根因 3~5 層可達系統級，勿無限深挖；
2. **一次一因**：一次分析聚焦單一偏差，避免混雜多因；
3. **先驗證再行動**：根因未驗證不進入提案階段；
4. **可改進才提**：無法改進的根因（如外部限制）標註「接受」而非硬改；
5. **沉澱模式**：常見偏差的根因模式沉澱到 `lesson-harvesting.md`，避免重複分析。

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-09