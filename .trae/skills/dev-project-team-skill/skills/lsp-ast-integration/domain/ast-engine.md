# AST 引擎：解析器/查询语言/模式匹配/符号表

> 编排器：`../SKILL.md`

---

## 1. 解析器架构

### 1.1 解析器选型
```python
class ParserRegistry:
    PARSERS = {
        # tree-sitter (推荐：快、增量、多语言)
        'typescript': {'library': 'tree-sitter-typescript', 'grammar': 'typescript'},
        'tsx': {'library': 'tree-sitter-typescript', 'grammar': 'tsx'},
        'javascript': {'library': 'tree-sitter-javascript', 'grammar': 'javascript'},
        'python': {'library': 'tree-sitter-python', 'grammar': 'python'},
        'go': {'library': 'tree-sitter-go', 'grammar': 'go'},
        'rust': {'library': 'tree-sitter-rust', 'grammar': 'rust'},
        'java': {'library': 'tree-sitter-java', 'grammar': 'java'},
        'csharp': {'library': 'tree-sitter-c-sharp', 'grammar': 'c_sharp'},
        'cpp': {'library': 'tree-sitter-cpp', 'grammar': 'cpp'},
        'c': {'library': 'tree-sitter-c', 'grammar': 'c'},
        'rust': {'library': 'tree-sitter-rust', 'grammar': 'rust'},
        'go': {'library': 'tree-sitter-go', 'grammar': 'go'},
        'java': {'library': 'tree-sitter-java', 'grammar': 'java'},
        'ruby': {'library': 'tree-sitter-ruby', 'grammar': 'ruby'},
        'php': {'library': 'tree-sitter-php', 'grammar': 'php'},
        'lua': {'library': 'tree-sitter-lua', 'grammar': 'lua'},
        'json': {'library': 'tree-sitter-json', 'grammar': 'json'},
        'yaml': {'library': 'tree-sitter-yaml', 'grammar': 'yaml'},
        'toml': {'library': 'tree-sitter-toml', 'grammar': 'toml'},
        'sql': {'library': 'tree-sitter-sql', 'grammar': 'sql'},
        'html': {'library': 'tree-sitter-html', 'grammar': 'html'},
        'css': {'library': 'tree-sitter-css', 'grammar': 'css'},
        'bash': {'library': 'tree-sitter-bash', 'grammar': 'bash'},
        'dockerfile': {'library': 'tree-sitter-dockerfile', 'grammar': 'dockerfile'},
        'graphql': {'library': 'tree-sitter-graphql', 'grammar': 'graphql'},
        'protobuf': {'library': 'tree-sitter-protobuf', 'grammar': 'protobuf'},
    }
    
    @classmethod
    def get_parser(cls, language: str) -> Parser:
        if language not in cls.PARSERS:
            raise ValueError(f"Unsupported language: {language}")
        config = cls.PARSERS[language]
        parser = Parser()
        parser.set_language(Language(config['library'], config['grammar']))
        return parser
```

---

## 2. AST 数据结构

### 2.1 节点结构
```python
@dataclass
class ASTNode:
    type: str                    # 节点类型: function_declaration, call_expression, ...
    start_byte: int              # 字节偏移
    end_byte: int                # 字节偏移
    start_point: Point           # (row, column) 0-based
    end_point: Point
    children: List['ASTNode']    # 子节点
    parent: Optional['ASTNode']  # 父节点
    text: str                    # 节点文本 (可选，懒加载)
    named: bool                  # 是否命名节点
    field_name: str              # 在父节点中的字段名
    
    def text(self) -> str:
        if self._text is None:
            self._text = self.source[self.start_byte:self.end_byte]
        return self._text
    
    def child_by_field(self, name: str) -> Optional['ASTNode']:
        for child in self.children:
            if child.field_name == name:
                return child
        return None
    
    def children_of_type(self, node_type: str) -> List['ASTNode']:
        return [c for c in self.children if c.type == node_type]
    
    def find_descendant(self, predicate: Callable[['ASTNode'], bool]) -> Optional['ASTNode']:
        if predicate(self): return self
        for child in self.children:
            result = child.find_descendant(predicate)
            if result: return result
        return None
```

### 2.2 位置信息
```python
@dataclass
class Point:
    row: int      # 0-based 行号
    column: int   # 0-based 列号 (UTF-8 字符)
    
    def to_lsp(self) -> Position:
        return {"line": self.row, "character": self.column}
    
    def to_utf16(self, source: str) -> int:
        """转换为 UTF-16 代码单元 (LSP 使用)"""
        lines = self.source.split('\n')
        line_text = lines[self.row]
        return len(line_text[:self.column].encode('utf-16-le')) // 2
```

---

## 3. 查询语言

### 3.1 Tree-sitter Query 语法
```python
class QueryEngine:
    def __init__(self, language: str):
        self.language = language
        self.queries: Dict[str, Query] = {}
    
    def query(self, ast: AST, pattern: str) -> List[QueryMatch]:
        """执行 tree-sitter query"""
        query = self._get_or_compile(ast.language, pattern)
        cursor = query.exec(ast.root_node)
        matches = []
        while cursor.next_match():
            match = cursor.match
            captures = {name: [node for _, node in capture] for name, capture in match.captures.items()}
            matches.append(QueryMatch(pattern=pattern, captures=captures))
        return matches
    
    def query_one(self, ast: AST, pattern: str) -> Optional[QueryMatch]:
        matches = self.query(ast, pattern)
        return matches[0] if matches else None
```

### 3.2 常用查询模式库
```python
QUERY_LIBRARY = {
    # 函数/方法
    "function": """
        (function_declaration name: (identifier) @name
            parameters: (formal_parameters) @params
            return_type: (type_annotation)? @return_type
            body: (statement_block) @body) @function
    """,
    "method": """
        (method_definition name: (property_identifier) @name
            parameters: (formal_parameters) @params
            return_type: (type_annotation)? @return_type
            body: (statement_block) @body) @method
    """,
    "class": """
        (class_declaration name: (type_identifier) @name
            heritage: (class_heritage)? @heritage
            body: (class_body) @body) @class
    """,
    "interface": """
        (interface_declaration name: (type_identifier) @name
            extends: (extends_clause)? @extends
            body: (interface_body) @body) @interface
    """,
    # 调用
    "call": """
        (call_expression function: (identifier) @callee
            arguments: (arguments) @args) @call
    """,
    "member_call": """
        (call_expression function: (member_expression
            object: (_) @receiver
            property: (property_identifier) @method)
            arguments: (arguments) @args) @call
    """,
    # 导入/导出
    "import": """
        (import_statement
            source: (string) @source
            (import_clause
                (named_imports (import_specifier name: (identifier) @name) @spec)?
                (namespace_import (identifier) @namespace)?
                (default_import (identifier) @default)?
            )?) @import
    """,
    "export": """
        (export_statement
            declaration: (_) @decl
            (export_clause
                (export_specifier name: (identifier) @name) @spec)?) @export
    """,
    # 类型
    "type_annotation": """
        (type_annotation type: (_) @type) @annotation
    """,
    "type_reference": """
        (type_reference name: (type_identifier) @name
            type_arguments: (type_arguments)? @args) @ref
    """,
    # 变量/常量
    "variable": """
        (variable_declaration
            (variable_declarator name: (identifier) @name
                value: (_) @value
                type: (type_annotation)? @type) @decl) @variable
    """,
    "const": """
        (lexical_declaration
            (variable_declarator name: (identifier) @name
                value: (_) @value
                type: (type_annotation)? @type) @decl) @const
    """,
}

# TypeScript 特有
TS_QUERIES = {
    "type_alias": """
        (type_alias_declaration name: (type_identifier) @name
            type: (_) @type) @alias
    """,
    "enum": """
        (enum_declaration name: (identifier) @name
            body: (enum_body) @body) @enum
    """,
    "decorator": """
        (decorator expression: (call_expression
            function: (identifier) @name
            arguments: (arguments) @args) @dec) @decorator
    """,
}

# Python 特有
PY_QUERIES = {
    "function": """
        (function_definition name: (identifier) @name
            parameters: (parameters) @params
            return_type: (type)? @return_type
            body: (block) @body) @function
    """,
    "class": """
        (class_definition name: (identifier) @name
            superclasses: (argument_list)? @bases
            body: (block) @body) @class
    """,
    "import": """
        (import_statement
            (dotted_name) @module
            (import_from_statement)? @from) @import
    """,
    "decorator": """
        (decorator (identifier) @name (arguments)? @args) @decorator
    """,
}
```

---

## 4. 符号表与语义分析

### 4.1 符号表构建
```python
@dataclass
class Symbol:
    name: str
    kind: SymbolKind              # function, class, variable, constant, type, module, ...
    scope: Scope                  # 所在作用域
    definition: ASTNode           # 定义节点
    type: Optional[Type]          # 推导类型
    references: List[Reference]   # 引用位置
    documentation: str            # 文档字符串
    deprecated: bool
    deprecated_message: str

@dataclass
class Scope:
    parent: Optional['Scope']
    children: List['Scope']
    symbols: Dict[str, Symbol]
    scope_type: ScopeType         # global, module, class, function, block
    ast_node: ASTNode             # 对应的 AST 节点

class SymbolTableBuilder:
    def __init__(self, language: str):
        self.language = language
        self.global_scope = Scope(None, [], {}, ScopeType.GLOBAL, None)
        self.current_scope = self.global_scope
        self.errors: List[SemanticError] = []
    
    def build(self, ast: AST) -> Scope:
        self._visit(ast.root_node, self.global_scope)
        return self.global_scope
    
    def _visit(self, node: ASTNode, scope: Scope):
        handler = getattr(self, f"_visit_{node.type}", None)
        if handler:
            handler(node, scope)
        else:
            for child in node.children:
                self._visit(child, scope)
    
    def _visit_function_declaration(self, node: ASTNode, scope: Scope):
        name_node = node.child_by_field("name")
        name = name_node.text if name_node else "<anonymous>"
        
        # 创建函数符号
        func_scope = Scope(scope, [], {}, ScopeType.FUNCTION, node)
        self.current_scope = func_scope
        
        # 参数
        params_node = node.child_by_field("parameters")
        if params_node:
            for param in params_node.children_of_type("formal_parameter"):
                self._add_parameter(param, func_scope)
        
        # 返回类型
        return_type = node.child_by_field("return_type")
        
        # 处理函数体
        body = node.child_by_field("body")
        if body:
            for child in body.children:
                self._visit(child, func_scope)
        
        # 注册符号
        symbol = Symbol(
            name=name,
            kind=SymbolKind.FUNCTION,
            scope=scope,
            definition=node,
            references=[]
        )
        scope.symbols[name] = symbol
        
        self.current_scope = scope
    
    def _visit_variable_declaration(self, node: ASTNode, scope: Scope):
        for declarator in node.children_of_type("variable_declarator"):
            name_node = declarator.child_by_field("name")
            if name_node:
                name = name_node.text
                value = declarator.child_by_field("value")
                type_ann = declarator.child_by_field("type")
                
                symbol = Symbol(
                    name=name,
                    kind=SymbolKind.VARIABLE,
                    scope=scope,
                    definition=declarator,
                    type=self._resolve_type(type_ann) if type_ann else None
                )
                scope.symbols[name] = symbol
    
    def _visit_call_expression(self, node: ASTNode, scope: Scope):
        # 解析调用目标
        func_node = node.child_by_field("function")
        if func_node:
            self._resolve_reference(func_node, scope)
        
        # 参数
        args_node = node.child_by_field("arguments")
        if args_node:
            for arg in args_node.children:
                self._visit(arg, scope)
```

### 4.2 类型推导
```python
class TypeInference:
    def __init__(self, symbol_table: Scope):
        self.symbols = symbol_table
    
    def infer(self, node: ASTNode) -> Type:
        if node.type == "identifier":
            return self._infer_identifier(node)
        elif node.type == "call_expression":
            return self._infer_call(node)
        elif node.type == "binary_expression":
            return self._infer_binary(node)
        elif node.type == "member_expression":
            return self._infer_member(node)
        # ... 其他节点类型
        return Type.UNKNOWN
    
    def _infer_identifier(self, node: ASTNode) -> Type:
        symbol = self._lookup_symbol(node.text, node)
        if symbol and symbol.type:
            return symbol.type
        return Type.UNKNOWN
    
    def _infer_call(self, node: ASTNode) -> Type:
        callee = node.child_by_field("function")
        callee_type = self.infer(callee)
        if isinstance(callee_type, FunctionType):
            return callee_type.return_type
        return Type.UNKNOWN
```

---

## 5. 增量解析

### 5.1 增量更新
```python
class IncrementalParser:
    def __init__(self, language: str):
        self.parser = ParserRegistry.get_parser(language)
        self.tree: Optional[Tree] = None
        self.source: str = ""
    
    def parse(self, source: str, old_tree: Optional[Tree] = None) -> Tree:
        if old_tree and self.source:
            # 计算编辑差异
            edits = self._compute_edits(self.source, source)
            if edits:
                old_tree.edit(edits)
                self.tree = self.parser.parse(source, old_tree)
            else:
                self.tree = old_tree
        else:
            self.tree = self.parser.parse(bytes(source, 'utf-8'))
        
        self.source = source
        return self.tree
    
    def _compute_edits(self, old: str, new: str) -> List[Edit]:
        # 使用 difflib 或 Myers diff 算法计算最小编辑
        pass
```

---

## 6. 索引与缓存

### 6.1 符号索引
```python
class SymbolIndex:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.index: Dict[str, List[SymbolLocation]] = defaultdict(list)
        self.file_symbols: Dict[str, List[Symbol]] = {}
    
    def add_file(self, file_path: str, symbols: List[Symbol]):
        self.file_symbols[file_path] = symbols
        for sym in symbols:
            self.index[sym.name].append(SymbolLocation(
                symbol=sym,
                file=file_path,
                range=sym.definition.range
            ))
    
    def find(self, name: str, exact: bool = True) -> List[SymbolLocation]:
        if exact:
            return self.index.get(name, [])
        # 模糊匹配
        return [loc for name, locs in self.index.items() 
                if name.startswith(name) for loc in locs]
    
    def find_by_pattern(self, pattern: str) -> List[SymbolLocation]:
        import fnmatch
        return [loc for name, locs in self.index.items() 
                if fnmatch.fnmatch(name, pattern) for loc in locs]
```

---

## 7. 性能优化

### 7.1 并行解析
```python
class ParallelParser:
    def __init__(self, max_workers: int = None):
        self.executor = ThreadPoolExecutor(max_workers=max_workers or cpu_count())
    
    def parse_files(self, files: List[Tuple[str, str]]) -> Dict[str, Tree]:
        """files: [(file_path, source_code), ...]"""
        futures = {}
        for path, source in files:
            lang = detect_language(path)
            if lang:
                futures[self.executor.submit(self._parse_one, lang, source)] = path
        
        results = {}
        for future in as_completed(futures):
            path = futures[future]
            try:
                results[path] = future.result()
            except Exception as e:
                logging.error(f"Parse failed {path}: {e}")
        return results
```

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08