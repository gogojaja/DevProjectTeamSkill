# 根因分析：5-Why / 鱼骨图 / 优先级排序

> 编排器：`../SKILL.md`

---

## 1. 根因分析架构

### 1.1 分析流程
```mermaid
graph LR
  A[偏差清单] --> B[5-Why 逐层问因]
  B --> C[鱼骨图分类]
  C --> D[根因确认]
  D --> E[可改进点提取]
  E --> F[优先级排序]
```

### 1.2 分析原则
- **追根到底**：至少问 5 层「为什么」，直到无可改进的系统性原因；
- **分类审视**：按人/流程/工具/标准/环境五大类检查，避免单一归因；
- **数据支撑**：每个「为什么」都要有依据，禁止臆测；
- **可改进性**：根因必须对应可改进点，否则继续深挖；
- **聚焦主因**：一个偏差通常有多因，找主因（80% 影响）优先。

---

## 2. 5-Why 分析

### 2.1 方法
```python
class FiveWhyAnalyzer:
    """5-Why 逐层问因"""
    
    def __init__(self):
        self.depth_limit = 5
    
    def analyze(self, deviation: Deviation) -> RootCause:
        """对偏差执行 5-Why"""
        causes = []
        current = deviation.description
        depth = 0
        
        while depth < self.depth_limit:
            question = f"为什么：{current}？"
            answer = self._ask(question)
            
            if not answer or self._is_systemic_root(answer):
                # 到达系统性根因
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
        """判断是否为系统性根因"""
        systemic_markers = ["标准缺失", "规范未定义", "流程未覆盖", "无检查点",
                            "约束冲突", "资源不足", "没有模板"]
        return any(m in answer for m in systemic_markers)
    
    def _check_improvable(self, root: str) -> bool:
        """检查根因是否可改进"""
        improvable_markers = ["补", "加", "更新", "重写", "优化", "新增", "调整"]
        return any(m in root for m in improvable_markers)
```

### 2.2 典型 5-Why 链
```
偏差：技能 A 触发词 X 下未加载
├─ 为什么①：description 没有触发词 X
│   └─ 为什么②：编写时按模板填但漏了
│       └─ 为什么③：结构校验只查 description 有无，不查触发词覆盖
│           └─ 为什么④：校验清单没有「触发词覆盖」项
│               └─ 为什么⑤：skill-authoring 五步第 3 步校验规则不完整  ← 系统根因
```
→ 可改进点：authoring.md 结构校验增加「触发词覆盖率」检查。

---

## 3. 鱼骨图分析

### 3.1 六大分类
| 分类 | 检查项 | 典型根因 |
|------|--------|----------|
| 人 (People) | 操作者技能、经验、疏忽 | 漏步骤、误操作、模板漏填 |
| 流程 (Process) | 步骤、检查点、门禁 | 跳步、无校验、绕过门禁 |
| 工具 (Tools) | 脚本、脚本逻辑、兼容 | 脚本 bug、路径硬编码、版本不符 |
| 标准 (Standards) | 规范、模板、约束 | 标准缺失、约束冲突、模板过期 |
| 环境 (Environment) | 平台、网络、依赖 | 平台差异、网络不稳、依赖缺失 |
| 数据 (Data) | 输入、格式、内容 | 数据错、格式不合规、内容过期 |

### 3.2 鱼骨分类实现
```python
class FishboneAnalyzer:
    """鱼骨图分类分析"""
    
    CATEGORIES = ["人", "流程", "工具", "标准", "环境", "数据"]
    
    KEYWORD_MAP = {
        "人": ["漏", "忘", "误", "手动", "疏忽", "操作"],
        "流程": ["跳", "绕", "缺步骤", "无检查", "门禁", "审批"],
        "工具": ["脚本", "路径", "硬编码", "兼容", "版本", "命令"],
        "标准": ["规范", "模板", "约束", "标准", "政策", "规定"],
        "环境": ["网络", "平台", "依赖", "权限", "系统", "容器"],
        "数据": ["格式", "内容", "CSV", "编码", "栏位", "栏位值"],
    }
    
    def classify(self, cause_text: str) -> List[str]:
        """将原因分类到鱼骨类别"""
        matched = []
        for category, keywords in self.KEYWORD_MAP.items():
            if any(k in cause_text for k in keywords):
                matched.append(category)
        return matched or ["其他"]
    
    def build_fishbone(self, causes: List[str]) -> FishboneDiagram:
        """构建鱼骨图数据"""
        diagram = FishboneDiagram()
        for cause in causes:
            categories = self.classify(cause)
            for cat in categories:
                diagram.add_bone(cat, cause)
        return diagram
```

---

## 4. 根因确认

### 4.1 验证规则
| 规则 | 说明 |
|------|------|
| 复现性 | 根因可复现偏差现象（验证因果） |
| 可控性 | 根因在技能库/流程可控范围内 |
| 唯一性 | 排除掉不可能因素后留下的（归谬法） |
| 可改进 | 对根因的改进能消除偏差 |

### 4.2 确认方法
```python
class RootCauseValidator:
    """根因验证"""
    
    def validate(self, root_cause: RootCause) -> ValidationResult:
        """验证根因有效性"""
        checks = []
        
        # 1. 复现性验证
        if self._can_reproduce(root_cause):
            checks.append(Check(name="复现性", passed=True, note="可复现"))
        else:
            checks.append(Check(name="复现性", passed=False, note="无法复现，需更多数据"))
        
        # 2. 可控性验证
        controllable = any(m in root_cause.root for m in ["标准", "流程", "工具", "技能", "脚本", "模板"])
        checks.append(Check(name="可控性", passed=controllable, 
                           note="可控" if controllable else "超出技能库范围"))
        
        # 3. 可改进性
        checks.append(Check(name="可改进性", passed=root_cause.improvable,
                           note="可改进" if root_cause.improvable else "需重新分析"))
        
        return ValidationResult(
            valid=all(c.passed for c in checks),
            checks=checks
        )
```

---

## 5. 可改进点提取与优先级

### 5.1 可改进点模型
```python
@dataclass
class ImprovementPoint:
    id: str                  # IMP-001
    root_cause: str          # 对应根因
    target: str              # 改进目标（技能/流程/工具/标准）
    proposal: str            # 改进方向
    expected_benefit: str    # 预期收益
    cost: str                # 成本（低/中/高）
    risk: str                # 风险（低/中/高）
    priority: str            # P0/P1/P2/P3
    
    def score(self) -> float:
        """优先级得分：收益 / 成本"""
        benefit_score = {"高": 3, "中": 2, "低": 1}.get(self.expected_benefit, 1)
        cost_score = {"低": 1, "中": 2, "高": 3}.get(self.cost, 2)
        return benefit_score / cost_score
```

### 5.2 优先级矩阵
| 收益 \ 成本 | 低成本 | 中成本 | 高成本 |
|------------|--------|--------|--------|
| 高收益 | **P0 立即做** | P1 近期做 | P2 规划做 |
| 中收益 | P1 近期做 | P2 规划做 | P3 缓议 |
| 低收益 | P2 规划做 | P3 缓议 | P3 不做 |

### 5.3 排序实现
```python
def prioritize(points: List[ImprovementPoint]) -> List[ImprovementPoint]:
    """按得分排序并赋优先级"""
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

## 6. 分析输出

### 6.1 根因分析报告
```markdown
## 根因分析报告
- **偏差**：DEV-001 技能 A 触发词 X 下未加载
- **5-Why 链**：
  1. description 没有触发词 X
  2. 编写时按模板填但漏了
  3. 结构校验只查 description 有无
  4. 校验清单没有触发词覆盖项
  5. **authoring.md 第 3 步校验规则不完整** ← 系统根因
- **鱼骨分类**：标准（校验规则缺失）
- **可改进点**：IMP-001 补 authoring.md 结构校验触发词覆盖率
- **优先级**：P1（中收益低成本）
```

### 6.2 可改进点清单
```csv
id,root_cause,target,proposal,expected_benefit,cost,risk,priority
IMP-001,authoring.md校验规则不完整,标准,结构校验补触发词覆盖率检查,中,低,低,P1
IMP-002,脚本路径硬编码,工具,deploy路径改自定位,高,中,低,P0
```

---

## 7. 最佳实践

1. **5 层够用**：多数根因 3~5 层可达系统级，勿无限深挖；
2. **一次一因**：一次分析聚焦单一偏差，避免混杂多因；
3. **先验证再行动**：根因未验证不进入提案阶段；
4. **可改进才提**：无法改进的根因（如外部限制）标注「接受」而非硬改；
5. **沉淀模式**：常见偏差的根因模式沉淀到 `lesson-harvesting.md`，避免重复分析。

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-09