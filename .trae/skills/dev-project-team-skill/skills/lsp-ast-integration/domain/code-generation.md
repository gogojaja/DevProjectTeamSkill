# 代碼生成：模板 / 上下文感知 / 類型感知 / 測試生成

> 編排器：`../SKILL.md`

---

## 1. 代碼生成架構

### 1.1 生成層次
| 層次 | 能力 | 依賴 | 典型應用 |
|------|------|------|----------|
| 模板生成 | 填充模板 | 模板引擎 | 樣板代碼、項目骨架、CRUD |
| 上下文感知 | 基於當前代碼 | AST 上下文 | 方法補全、類擴展、接口實現 |
| 類型感知 | 基於類型系統 | 符號表 + LSP | API 客戶端、DTO 映射、ORM 模型 |
| 語義感知 | 基於語義 | AST + 符號表 + LSP | 測試生成、遷移腳本、重構輔助 |

### 1.2 核心組件
```python
class CodeGenerator:
    def __init__(self, ast_engine: ASTEngine, lsp_client: LSPClient = None):
        self.ast_engine = ast_engine
        self.lsp = lsp_client
        self.templates: Dict[str, Template] = {}
        self.providers: Dict[str, GeneratorProvider] = {}
        self._register_default_templates()
    
    def generate(self, request: GenerationRequest) -> GenerationResult:
        # 1. 解析生成意圖
        intent = self._parse_intent(request)
        
        # 2. 收集上下文
        context = self._collect_context(intent)
        
        # 3. 選擇生成器
        generator = self.providers.get(intent.type)
        if not generator:
            return GenerationResult(success=False, errors=[f"Unknown generation type: {intent.type}"])
        
        # 4. 生成代碼
        code = generator.generate(context)
        
        # 5. 格式化
        formatted = self._format(code, intent.language)
        
        # 6. 校驗（可選 LSP 診斷）
        diagnostics = self._validate(formatted) if self.lsp else []
        
        return GenerationResult(
            success=not any(d.severity == 1 for d in diagnostics),
            code=formatted,
            diagnostics=diagnostics,
            insertion_point=context.insertion_point
        )
```

---

## 2. 模板引擎

### 2.1 模板 DSL
```python
@dataclass
class Template:
    name: str
    language: str
    pattern: str                    # 生成模式
    placeholders: List[str]         # 佔位符列表
    conditionals: List[Conditional] # 條件邏輯
    defaults: Dict[str, str]        # 默認值
    
    def render(self, context: Dict[str, Any]) -> str:
        """渲染模板"""
        result = self.pattern
        for placeholder in self.placeholders:
            value = context.get(placeholder) or self.defaults.get(placeholder, "")
            result = result.replace("{{" + placeholder + "}}", value)
        for cond in self.conditionals:
            result = cond.apply(result, context)
        return result
```

### 2.2 常用模板
```python
TEMPLATES = {
    "rest_api_resource": Template(
        name="rest_api_resource",
        language="python",
        pattern="""
class {Resource}Controller:
    def __init__(self, {resource}_service):
        self.{resource}_service = {resource}_service

    def list(self, request) -> Response:
        {{LIST_IMPL}}

    def get(self, request, {resource}_id) -> Response:
        {{GET_IMPL}}

    def create(self, request) -> Response:
        {{CREATE_IMPL}}

    def update(self, request, {resource}_id) -> Response:
        {{UPDATE_IMPL}}

    def delete(self, request, {resource}_id) -> Response:
        {{DELETE_IMPL}}
""",
        placeholders=["Resource", "resource", "LIST_IMPL", "GET_IMPL", "CREATE_IMPL", "UPDATE_IMPL", "DELETE_IMPL"],
        conditionals=[
            Conditional("if include_bulk", "bulk_pattern"),
            Conditional("if require_auth", "auth_decorator")
        ],
        defaults={"LIST_IMPL": "return self.{resource}_service.list_all()"}
    ),
    
    "repository": Template(
        name="repository",
        language="python",
        pattern="""
class {Entity}Repository:
    def __init__(self, session):
        self.session = session

    def find_by_id(self, {entity}_id) -> Optional[{Entity}]:
        return self.session.get({Entity}, {entity}_id)

    def save(self, {entity}: {Entity}) -> {Entity}:
        self.session.add({entity})
        self.session.commit()
        return {entity}

    def delete(self, {entity}: {Entity}) -> None:
        self.session.delete({entity})
        self.session.commit()
""",
        placeholders=["Entity", "entity"],
        conditionals=[],
        defaults={}
    ),
}
```

---

## 3. 上下文感知生成

### 3.1 上下文收集
```python
class ContextCollector:
    def __init__(self, ast_engine: ASTEngine, lsp_client: LSPClient = None):
        self.ast_engine = ast_engine
        self.lsp = lsp_client
    
    def collect(self, file: str, cursor: Position = None) -> GenerationContext:
        """收集生成上下文"""
        ast = self.ast_engine.parse_file(file)
        context = GenerationContext(file=file, ast=ast)
        
        # 1. 當前作用域
        if cursor:
            context.scope = self._find_enclosing_scope(ast, cursor)
        
        # 2. 可見符號
        context.visible_symbols = self._collect_visible_symbols(ast, context.scope)
        
        # 3. 導入語句
        context.imports = self._collect_imports(ast)
        
        # 4. 命名衝突檢測
        context.used_names = self._collect_used_names(ast)
        
        # 5. 代碼風格
        context.style = self._detect_style(ast)
        
        return context
    
    def _find_enclosing_scope(self, ast, cursor) -> Scope:
        """找到光標所在的最內層作用域"""
        node = ast.root
        stack = []
        
        def walk(node):
            if self._contains(node, cursor):
                stack.append(node)
                for child in node.children:
                    walk(child)
        
        walk(ast.root)
        return stack[-1] if stack else ast.root_scope
    
    def _collect_visible_symbols(self, ast, scope) -> List[Symbol]:
        """收集作用域內可見符號"""
        symbols = []
        current = scope
        while current:
            symbols.extend(current.declarations)
            current = current.parent
        # 加上全局 + 導入
        symbols.extend(ast.global_symbols)
        return symbols
```

### 3.2 上下文感知生成
```python
class ContextAwareGenerator:
    def generate(self, context: GenerationContext, intent: GenerationIntent) -> str:
        """基於上下文生成"""
        if intent.type == "implement_method":
            return self._generate_method(context, intent)
        elif intent.type == "implement_interface":
            return self._generate_interface_impl(context, intent)
        elif intent.type == "create_class":
            return self._generate_class(context, intent)
        elif intent.type == "handle_error":
            return self._generate_error_handling(context, intent)
        return ""
    
    def _generate_method(self, context, intent) -> str:
        """生成方法實現"""
        signature = intent.signature
        return_type = signature.return_type
        
        # 基於返回類型推導默認實現
        default = self._default_for_type(return_type)
        
        # 使用可用符號
        available = [s for s in context.visible_symbols if self._is_usable(s, return_type)]
        
        return f"""def {signature.name}(self, {", ".join(signature.params)}):
    # TODO: 實現 {signature.name}
    {self._suggest_impl(available, return_type)}
    return {default}"""
    
    def _suggest_impl(self, symbols, return_type) -> str:
        """基於可見符號推導實現建議"""
        candidates = []
        for s in symbols:
            if s.type == return_type:
                candidates.append(f"return {s.name}")
        if candidates:
            return candidates[0]
        return f"# 提示: 可用的 {return_type} 符號: {', '.join(s.name for s in symbols[:5])}"
```

---

## 4. 類型感知生成

### 4.1 類型推導
```python
class TypeAwareGenerator:
    def __init__(self, lsp_client: LSPClient):
        self.lsp = lsp_client
    
    def infer_type(self, file: str, line: int, col: int) -> TypeInfo:
        """推導變量/表達式類型"""
        hover = self.lsp.hover(file, line, col)
        if not hover:
            return TypeInfo(name="unknown", kind="any")
        
        # 解析 hover 內容中的類型標記
        return self._parse_type_from_hover(hover)
    
    def generate_api_client(self, spec: OpenAPISpec) -> str:
        """基於 OpenAPI 生成 API 客戶端"""
        lines = ["class ApiClient:", "    def __init__(self, base_url):", "        self.base_url = base_url"]
        
        for path, methods in spec.paths.items():
            class_name = self._path_to_class(path)
            lines.append(f"\n    class {class_name}:")
            lines.append(f"        def __init__(self, client):")
            lines.append(f"            self._client = client")
            
            for method, detail in methods.items():
                lines.extend(self._generate_endpoint(method, path, detail, class_name))
        
        return "\n".join(lines)
    
    def _generate_endpoint(self, method, path, detail, class_name) -> List[str]:
        """生成端點方法"""
        params = []
        for p in detail.get("parameters", []):
            params.append(f"{p['name']}: {self._type_to_annotation(p['schema']['type'])}")
        
        lines = [
            f"        def {self._method_name(method, path)}(self, {', '.join(params)}) -> Any:",
            f"            \"\"\"{detail.get('summary', '')}\"\"\"",
            f"            url = f\"{self._path_with_query(path)}\"",
        ]
        
        # 請求體
        if "requestBody" in detail:
            lines.append(f"            data = {self._body_serialize(detail['requestBody'])}")
        
        # 發送請求
        lines.extend([
            f"            response = self._client.request({method!r}, url, data=data)",
            "            response.raise_for_status()",
            "            return response.json()",
        ])
        return lines
```

### 4.2 DTO / 模型生成
```python
class ModelGenerator:
    def generate_dto(self, schema: Dict) -> str:
        """從 JSON Schema 生成 DTO"""
        name = schema["title"]
        fields = []
        
        for prop, details in schema.get("properties", {}).items():
            field_type = self._map_type(details.get("type", "any"))
            default = self._map_default(details)
            required = "=" if prop not in schema.get("required", []) else ""
            
            if default is not None:
                fields.append(f"    {prop}{required}{default}")
            else:
                fields.append(f"    {prop}: {field_type}{required}...")
        
        return f"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class {name}:
{chr(10).join(fields)}
"""
    
    def _map_type(self, json_type: str) -> str:
        mapping = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "List[Any]",
            "object": "Dict[str, Any]",
            "null": "Optional[Any]"
        }
        return mapping.get(json_type, "Any")
```

---

## 5. 測試生成

### 5.1 基於 AST 生成單元測試
```python
class TestGenerator:
    def __init__(self, ast_engine: ASTEngine, framework: str = "pytest"):
        self.ast_engine = ast_engine
        self.framework = framework
    
    def generate_for_function(self, file: str, func_name: str) -> str:
        """為函數生成單元測試"""
        ast = self.ast_engine.parse_file(file)
        func = self._find_function(ast, func_name)
        
        # 1. 分析函數簽名
        params = func.signature.params
        return_type = func.signature.return_type
        
        # 2. 生成測試用例
        cases = []
        cases.extend(self._generate_normal_cases(func))
        cases.extend(self._generate_edge_cases(func))
        cases.extend(self._generate_error_cases(func))
        
        # 3. 生成測試函數
        test_lines = [
            "import pytest",
            f"from {self._module_of(file)} import {func_name}",
            "",
        ]
        
        for i, case in enumerate(cases):
            test_lines.extend([
                f"def test_{func_name}_{case.name}():",
                *[f"    {line}" for line in case.body],
                "",
            ])
        
        return "\n".join(test_lines)
    
    def _generate_normal_cases(self, func) -> List[TestCase]:
        """正常路徑測試"""
        # 基於參數類型生成典型值
        cases = []
        params = func.signature.params
        for i in range(min(3, max(1, len(params)))):
            values = []
            for p in params:
                values.append(self._sample_value(p.type))
            cases.append(TestCase(
                name=f"normal_{i}",
                body=[f"result = {func.name}({', '.join(values)})", f"assert result is not None"]
            ))
        return cases
    
    def _generate_edge_cases(self, func) -> List[TestCase]:
        """邊界值測試"""
        cases = []
        params = func.signature.params
        edge_values = {"int": ["0", "-1", "maxint"], "str": ["\"\"", "\" \"", "\"\\n\""], "list": ["[]"], "float": ["0.0", "-0.0", "inf"]}
        
        for p in params:
            base_type = p.type.strip("Optional")
            for val in edge_values.get(base_type, []):
                args = ["None" if p.name == p.name else val for p in params]
                cases.append(TestCase(
                    name=f"edge_{p.name}_{val.replace('\\\"','q').replace('\\n','n')}",
                    body=[f"result = {func.name}({', '.join(args)})", "assert result is not None"]
                ))
        return cases
    
    def _generate_error_cases(self, func) -> List[TestCase]:
        """異常測試"""
        cases = []
        params = func.signature.params
        for p in params:
            cases.append(TestCase(
                name=f"error_{p.name}_none",
                body=[f"with pytest.raises(TypeError):", f"    {func.name}(None)"]
            ))
        return cases
```

### 5.2 測試覆蓋率分析
```python
class CoverageAnalyzer:
    def analyze(self, file: str, coverage_data: Dict) -> CoverageReport:
        """分析測試覆蓋率並識別未覆蓋分支"""
        ast = self.ast_engine.parse_file(file)
        
        # 1. 找出所有條件節點
        conditionals = self._find_conditionals(ast)
        
        # 2. 與覆蓋數據對比
        uncovered = []
        for cond in conditionals:
            key = f"{cond.file}:{cond.line}"
            if key not in coverage_data:
                uncovered.append(cond)
            else:
                data = coverage_data[key]
                if data["branch_count"] != data["covered_count"]:
                    uncovered.append(cond)
        
        # 3. 生成補充測試建議
        suggestions = [self._suggest_test(cond) for cond in uncovered]
        
        return CoverageReport(total=len(conditionals), uncovered=len(uncovered), suggestions=suggestions)
```

---

## 6. 生成質量保證

### 6.1 生成代碼校驗
```python
class GenerationValidator:
    def __init__(self, lsp_client: LSPClient = None):
        self.lsp = lsp_client
    
    def validate(self, code: str, language: str, context: GenerationContext) -> ValidationResult:
        """驗證生成代碼質量"""
        errors = []
        warnings = []
        
        # 1. 語法校驗
        if not self._is_syntactically_valid(code, language):
            errors.append("Generated code has syntax errors")
        
        # 2. 命名衝突
        conflicts = self._check_name_conflicts(code, context.used_names)
        warnings.extend(conflicts)
        
        # 3. 類型正確性
        if self.lsp:
            diags = self.lsp.get_diagnostics_for_code(code, language)
            errors.extend([d for d in diags if d.severity == 1])
            warnings.extend([d for d in diags if d.severity == 2])
        
        # 4. 安全檢查
        security = self._check_security(code, language)
        warnings.extend(security)
        
        return ValidationResult(
            valid=not errors,
            errors=errors,
            warnings=warnings,
            suggestions=self._make_suggestions(code, context)
        )
    
    def _check_security(self, code, language) -> List[str]:
        """安全檢查：SQL 注入、命令注入、路徑遍歷"""
        warnings = []
        
        if "eval(" in code or "exec(" in code:
            warnings.append("Potential code execution - use with caution")
        
        if "subprocess" in code and "shell=True" in code:
            warnings.append("Shell injection risk detected")
        
        if "raw_input" in code or "input(" in code and "sql" in code:
            warnings.append("Potential injection vector")
        
        return warnings
```

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08