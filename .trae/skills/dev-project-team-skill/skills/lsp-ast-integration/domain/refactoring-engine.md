# 重構引擎：提取/內聯/移動/重命名/簽名變更

> 編排器：`../SKILL.md`

---

## 1. 重構操作類型

### 1.1 核心操作
| 操作 | 語義 | 適用場景 | 風險 |
|------|------|----------|------|
| `extract_method` | 提取方法 | 長函數、重複邏輯、單一職責 | 低 |
| `extract_class` | 提取類 | 神類、職責過重、內聚性差 | 中 |
| `extract_interface` | 提取接口 | 多實現、解耦、依賴倒置 | 低 |
| `inline_method` | 內聯方法 | 簡單委托、性能關鍵路徑 | 低 |
| `inline_variable` | 內聯變量 | 單次使用、簡化表達 | 低 |
| `move_method` | 移動方法 | 特性嫉妒、職責錯位 | 中 |
| `move_field` | 移動字段 | 數據與行為分離 | 中 |
| `rename` | 重命名 | 命名不清、統一術語 | 低 |
| `change_signature` | 變更簽名 | 參數增減/重排/類型變更 | 高 |
| `introduce_parameter` | 引入參數 | 硬編碼值參數化 | 低 |
| `remove_parameter` | 移除參數 | 死參數清理 | 低 |
| `encapsulate_field` | 封裝字段 | 直接訪問 → getter/setter | 低 |
| `replace_temp_with_query` | 臨時變量替換為查詢 | 複雜表達式簡化 | 低 |
| `replace_conditional_with_polymorphism` | 條件分支替換為多態 | 類型碼/條件分支過多 | 高 |
| `extract_superclass` | 提取超類 | 重複代碼、共同行為 | 中 |
| `extract_subclass` | 提取子類 | 部分實例特殊行為 | 中 |
| `form_template_method` | 形成模板方法 | 相似流程、差異步驟 | 中 |

---

## 2. 重構引擎架構

### 2.1 核心接口
```python
@dataclass
class RefactorOperation:
    type: str                           # 操作類型
    target: ASTNode                     # 目標節點
    params: Dict[str, Any]              # 參數
    preconditions: List[Precondition]   # 前置條件
    postconditions: List[Postcondition] # 後置條件

@dataclass
class RefactorResult:
    success: bool
    changes: List[FileChange]           # 文件變更
    preview: str                        # 預覽差異
    warnings: List[str]                 # 警告
    errors: List[str]                   # 錯誤

class RefactoringEngine:
    def __init__(self, ast_engine: ASTEngine, lsp_client: LSPClient = None):
        self.ast_engine = ast_engine
        self.lsp = lsp_client
        self.operations: Dict[str, RefactorOperationHandler] = {}
        self._register_operations()
    
    def refactor(self, operation: RefactorOperation) -> RefactorResult:
        handler = self.operations.get(operation.type)
        if not handler:
            return RefactorResult(success=False, errors=[f"Unknown operation: {operation.type}"])
        
        # 1. 驗證前置條件
        for pre in operation.preconditions:
            if not pre.check(operation):
                return RefactorResult(success=False, errors=[f"Precondition failed: {pre.description}"])
        
        # 2. 執行重構
        result = handler.execute(operation)
        
        # 3. 驗證後置條件
        for post in operation.postconditions:
            if not post.check(result):
                return RefactorResult(success=False, errors=[f"Postcondition failed: {post.description}"])
        
        return result
```

---

## 3. 核心重構操作實現

### 3.1 提取方法
```python
class ExtractMethodHandler:
    def execute(self, op: RefactorOperation) -> RefactorResult:
        target = op.target
        params = op.params
        
        # 1. 分析目標區域
        start_line = params['start_line']
        end_line = params['end_line']
        method_name = params['method_name']
        new_params = params.get('parameters', [])
        return_type = params.get('return_type')
        
        # 2. 分析數據流
        data_flow = self._analyze_data_flow(target, start_line, end_line)
        
        # 3. 確定參數
        inputs = data_flow.inputs  # 外部變量讀取
        outputs = data_flow.outputs  # 外部變量寫入
        returned = data_flow.returned  # 返回值
        
        # 4. 生成新方法
        new_method = self._generate_method(
            name=params['method_name'],
            params=self._deduce_parameters(inputs),
            body=target.text,
            return_type=self._deduce_return_type(returned)
        )
        
        # 4. 生成調用代碼
        call_code = self._generate_call(params['method_name'], inputs)
        
        # 5. 生成變更
        changes = [
            FileChange(
                file=target.file,
                range=Range(start_line, 1, end_line, 1),
                new_text=call_code
            ),
            FileChange(
                file=target.file,
                range=Range(target.end_line + 1, 1, target.end_line + 1, 1),
                new_text=f"\n{new_method}\n"
            )
        ]
        
        return RefactorResult(success=True, changes=changes, preview=generate_diff(changes))

    def _analyze_data_flow(self, node: ASTNode, start: int, end: int) -> DataFlow:
        """分析區域內的讀寫變量"""
        inputs = set()
        outputs = set()
        returned = None
        
        def visit(node):
            nonlocal returned
            if node.type == "identifier":
                # 讀取變量
                if self._is_external_read(node):
                    self.inputs.add(node.text)
            elif node.type == "assignment_expression":
                # 寫入變量
                left = node.child_by_field("left")
                if left and self._is_external_write(left):
                    self.outputs.add(left.text)
            elif node.type == "return_statement":
                returned = node.child_by_field("value")
            
            for child in node.children:
                child.visit(visit)
        
        target.visit(visit)
        return DataFlow(inputs=self.inputs, outputs=self.outputs, returned=returned)
    
    def _generate_method(self, name, params, body, return_type):
        param_str = ", ".join(f"{p.name}: {p.type}" for p in params)
        return f"""async {name}({param_str}): {return_type} {{
{self._indent(body, 4)}
}}"""
```

### 3.2 提取類
```python
class ExtractClassHandler:
    def execute(self, op: RefactorOperation) -> RefactorResult:
        target = op.target  # 源類
        params = op.params
        
        class_name = params['class_name']
        methods = params['methods']  # 要移動的方法名列表
        fields = params.get('fields', [])  # 要移動的字段
        
        # 1. 驗證：方法/字段是否存在
        source_class = self._find_class(target)
        methods_to_move = [m for m in source_class.methods if m.name in params['methods']]
        fields_to_move = [f for f in source_class.fields if f.name in params['fields']]
        
        # 2. 分析依賴
        deps = self._analyze_dependencies(methods_to_move, fields_to_move, target)
        
        # 3. 生成新類
        new_class = self._generate_class(
            name=params['class_name'],
            methods=methods_to_move,
            fields=fields_to_move,
            imports=self._collect_imports(methods_to_move)
        )
        
        # 4. 在源類中委托
        delegation = self._generate_delegation(params['class_name'], methods_to_move)
        
        changes = [
            FileChange(
                file=target.file,
                range=Range(target.end_line + 1, 1, target.end_line + 1, 1),
                new_text=f"\n{new_class}\n"
            ),
            FileChange(
                file=target.file,
                range=Range(target.start_line, 1, target.end_line, 1),
                new_text=self._inject_delegation(target.text, delegation)
            )
        ]
        
        return RefactorResult(success=True, changes=changes, preview=generate_diff(changes))
```

### 3.3 重命名
```python
class RenameHandler:
    def execute(self, op: RefactorOperation) -> RefactorResult:
        target = op.target
        new_name = op.params['new_name']
        
        # 1. 使用 LSP 獲取所有引用
        refs = self.lsp.find_references(target.file, target.line, target.col)
        
        # 2. 按文件分組
        by_file = defaultdict(list)
        for ref in refs:
            by_file[ref.uri].append(ref)
        
        # 3. 生成變更
        changes = []
        for uri, refs in by_file.items():
            file_path = uri_to_file(uri)
            source = read_file(file_path)
            
            # 按位置排序（從後往前替換，避免位置偏移）
            sorted_refs = sorted(refs, key=lambda r: (r.range.start.line, r.range.start.character), reverse=True)
            
            new_text = source
            for ref in sorted_refs:
                start = offset_from_position(source, ref.range.start)
                end = offset_from_position(source, ref.range.end)
                new_text = new_text[:start] + op.params['new_name'] + new_text[end:]
            
            changes.append(FileChange(file=file_path, new_text=new_text))
        
        return RefactorResult(success=True, changes=changes, preview=generate_diff(changes))
```

### 3.4 變更簽名
```python
class ChangeSignatureHandler:
    def execute(self, op: RefactorOperation) -> RefactorResult:
        target = op.target
        params = op.params
        
        # 1. 解析當前簽名
        current_sig = self._parse_signature(target)
        
        # 2. 構建新簽名
        new_params = params.get('parameters', [])
        new_return = params.get('return_type')
        
        # 3. 找到所有調用點
        callers = self._find_callers(target)
        
        # 4. 生成調用點變更
        changes = []
        for caller in callers:
            call_site = self._find_call_site(caller, target.name)
            if call_site:
                new_call = self._generate_new_call(call_site, params)
                changes.append(FileChange(
                    file=caller.file,
                    range=call_site.range,
                    new_text=new_call
                ))
        
        # 4. 更新定義
        new_sig = self._generate_signature(target.name, new_params, params.get('return_type'))
        changes.append(FileChange(
            file=target.file,
            range=target.signature_range,
            new_text=new_sig
        ))
        
        return RefactorResult(success=True, changes=changes, preview=generate_diff(changes))
```

---

## 4. 安全性保證

### 4.1 前置條件檢查
```python
class PreconditionChecker:
    def check_extract_method(self, op: RefactorOperation) -> List[str]:
        errors = []
        target = op.target
        
        # 1. 目標必須是語句序列
        if not self._is_statement_sequence(target):
            errors.append("Target must be a sequence of statements")
        
        # 2. 不能包含 return/break/continue (除非在循環/函數內)
        if self._contains_control_flow(target):
            errors.append("Cannot extract code with return/break/continue")
        
        # 3. 不能有未處理的副作用
        if self._has_unhandled_side_effects(target):
            errors.append("Contains unhandled side effects (I/O, mutations)")
        
        return errors
    
    def check_rename(self, op: RefactorOperation) -> List[str]:
        errors = []
        new_name = op.params['new_name']
        
        # 1. 名稱合法性
        if not is_valid_identifier(new_name):
            errors.append(f"Invalid identifier: {new_name}")
        
        # 2. 不衝突
        if self._has_conflict(op.target, new_name):
            errors.append(f"Name conflict: {new_name} already exists in scope")
        
        # 3. 不破壞導出/導入
        if self._breaks_exports(op.target, new_name):
            errors.append("Rename would break exports/imports")
        
        return errors
```

### 4.2 後置條件驗證
```python
class PostconditionChecker:
    def verify(self, result: RefactorResult) -> List[str]:
        errors = []
        
        # 1. 語法正確性
        for change in result.changes:
            if not self._is_syntactically_valid(change):
                errors.append(f"Syntax error in {change.file}")
        
        # 2. 類型正確性 (如果有 LSP)
        if self.lsp:
            diags = self.lsp.get_diagnostics_for_file(change.file)
            if any(d.severity == 1 for d in diags):  # error
                errors.append(f"Type errors introduced in {change.file}")
        
        # 3. 測試通過 (如果有測試)
        if self.test_runner:
            if not self._run_affected_tests(result.changes):
                errors.append("Tests failed after refactoring")
        
        return errors
```

---

## 5. 預覽與交互

### 5.1 差異生成
```python
def generate_diff(changes: List[FileChange]) -> str:
    """生成統一差異格式"""
    diffs = []
    for change in changes:
        old = read_file(change.file) if not change.is_new else ""
        new = change.new_text
        
        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{change.file}",
            tofile=f"b/{change.file}",
            lineterm=""
        )
        diffs.append("\n".join(diff))
    return "\n".join(diffs)
```

### 5.2 交互式確認
```python
class InteractiveRefactoring:
    def confirm(self, result: RefactorResult) -> bool:
        print(result.preview)
        response = input("Apply these changes? [y/n/d] ").lower()
        if response == 'y':
            return True
        elif response == 'd':
            # 顯示詳細差異
            self._show_detailed_diff(result.changes)
            return self.confirm(result)
        return False
    
    def apply(self, result: RefactorResult):
        for change in result.changes:
            if change.is_new:
                write_file(change.file, change.new_text)
            else:
                # 安全寫入：原子替換
                atomic_write(change.file, change.new_text)
```

---

## 5. 撤銷支持

```python
class UndoManager:
    def __init__(self):
        self.history: List[RefactorSnapshot] = []
    
    def snapshot(self, changes: List[FileChange]) -> RefactorSnapshot:
        snapshot = RefactorSnapshot(
            timestamp=time.time(),
            changes=changes,
            backups={}
        )
        for change in changes:
            if not change.is_new:
                snapshot.backups[change.file] = read_file(change.file)
        self.history.append(snapshot)
        return snapshot
    
    def undo(self) -> bool:
        if not self.history:
            return False
        snapshot = self.history.pop()
        for file, content in snapshot.backups.items():
            atomic_write(file, content)
        # 刪除新建文件
        for change in snapshot.changes:
            if change.is_new and os.path.exists(change.file):
                os.remove(change.file)
        return True
```

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08