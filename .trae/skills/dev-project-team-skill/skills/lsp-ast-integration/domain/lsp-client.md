# LSP 客戶端：啟動/能力/請求/響應/診斷/工作區

> 編排器：`../SKILL.md`

---

## 1. LSP 服務器管理

### 1.1 服務器啟動策略
```python
class LSPServerManager:
    def __init__(self):
        self.servers: Dict[str, LSPServer] = {}
        self.language_servers = {
            'typescript': {'command': ['typescript-language-server', '--stdio'], 'extensions': ['.ts', '.tsx']},
            'python': {'command': ['pyright-langserver', '--stdio'], 'extensions': ['.py']},
            'go': {'command': ['gopls'], 'extensions': ['.go']},
            'rust': {'command': ['rust-analyzer'], 'extensions': ['.rs']},
            'java': {'command': ['jdtls'], 'extensions': ['.java']},
            'csharp': {'command': ['csharp-ls'], 'extensions': ['.cs']},
            'cpp': {'command': ['clangd'], 'extensions': ['.cpp', '.cc', '.cxx', '.h', '.hpp']},
            'ruby': {'command': ['solargraph', 'stdio'], 'extensions': ['.rb']},
            'php': {'command': ['phpactor', 'language-server'], 'extensions': ['.php']},
            'kotlin': {'command': ['kotlin-language-server'], 'extensions': ['.kt', '.kts']},
            'swift': {'command': ['sourcekit-lsp'], 'extensions': ['.swift']},
            'lua': {'command': ['lua-language-server'], 'extensions': ['.lua']},
            'json': {'command': ['vscode-json-language-server', '--stdio'], 'extensions': ['.json']},
            'yaml': {'command': ['yaml-language-server', '--stdio'], 'extensions': ['.yaml', '.yml']},
        }
    
    def get_or_start(self, language: str, project_root: str) -> LSPServer:
        key = f"{language}:{project_root}"
        if key not in self.servers:
            config = self.language_servers.get(language)
            if not config:
                raise ValueError(f"No LSP server for language: {language}")
            self.servers[key] = LSPServer(config, project_root)
            self.servers[key].start()
        return self.servers[key]
```

### 1.2 服務器進程管理
```python
class LSPServer:
    def __init__(self, config: dict, project_root: str):
        self.config = config
        self.project_root = project_root
        self.process: subprocess.Popen = None
        self.request_id = 0
        self.pending_requests: Dict[int, asyncio.Future] = {}
        self.capabilities: ServerCapabilities = None
        self.initialized = False
    
    def start(self):
        self.process = subprocess.Popen(
            self.config['command'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.project_root,
            bufsize=0
        )
        # 啟動輸出讀取線程
        self._start_read_loop()
        # 發送 initialize 請求
        self.initialize()
    
    def initialize(self):
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "processId": os.getpid(),
                "rootUri": file_to_uri(self.project_root),
                "capabilities": self._get_client_capabilities(),
                "workspaceFolders": [{"uri": file_to_uri(self.project_root), "name": "workspace"}]
            }
        }
        future = self._send_request(req)
        result = future.result(timeout=30)
        self.capabilities = result.get('capabilities', {})
        self.initialized = True
        # 發送 initialized 通知
        self._send_notification("initialized", {})
```

---

## 2. LSP 協議實現

### 2.1 消息格式
```json
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "textDocument/definition",
  "params": {
    "textDocument": {"uri": "file:///project/src/main.ts"},
    "position": {"line": 10, "character": 5}
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": [
    {
      "uri": "file:///project/src/types/user.ts",
      "range": {
        "start": {"line": 5, "character": 0},
        "end": {"line": 5, "character": 10}
      }
    }
  ]
}

// Notification
{
  "jsonrpc": "2.0",
  "method": "textDocument/didChange",
  "params": {
    "textDocument": {"uri": "file:///project/src/main.ts", "version": 5},
    "contentChanges": [{"range": {...}, "text": "new code"}]
  }
}
```

### 2.2 核心請求方法
```python
class LSPClient:
    def __init__(self, server: LSPServer):
        self.server = server
    
    def _request(self, method: str, params: dict, timeout: float = 10) -> Any:
        req_id = self.server._next_id()
        future = self.server._create_future()
        msg = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        self.server._send(msg)
        return asyncio.wait_for(future, timeout=timeout)
    
    # 核心導航
    def goto_definition(self, uri: str, line: int, char: int) -> List[Location]:
        return self._request("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": self._char_to_utf16(uri, line, char)}
        })
    
    def goto_declaration(self, uri: str, line: int, char: int) -> List[Location]:
        return self._request("textDocument/declaration", {...})
    
    def goto_type_definition(self, uri: str, line: int, char: int) -> List[Location]:
        return self._request("textDocument/typeDefinition", {...})
    
    def goto_implementation(self, uri: str, line: int, char: int) -> List[Location]:
        return self._request("textDocument/implementation", {...})
    
    def find_references(self, uri: str, line: int, char: int, include_decl: bool = True) -> List[Location]:
        return self._request("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": char},
            "context": {"includeDeclaration": True}
        })
    
    def hover(self, uri: str, line: int, char: int) -> Hover:
        return self._request("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": char}
        })
    
    def signature_help(self, uri: str, line: int, char: int) -> SignatureHelp:
        return self._request("textDocument/signatureHelp", {...})
    
    def completion(self, uri: str, line: int, char: int, trigger: str = None) -> CompletionList:
        return self._request("textDocument/completion", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": char},
            "context": {"triggerKind": 1, "triggerCharacter": trigger} if trigger else {}
        })
    
    def rename(self, uri: str, line: int, char: int, new_name: str) -> WorkspaceEdit:
        return self._request("textDocument/rename", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": char},
            "newName": new_name
        })
    
    def prepare_rename(self, uri: str, line: int, char: int) -> Range:
        return self._request("textDocument/prepareRename", {...})
    
    def document_symbols(self, uri: str) -> List[DocumentSymbol]:
        return self._request("textDocument/documentSymbol", {"textDocument": {"uri": uri}})
    
    def workspace_symbols(self, query: str) -> List[SymbolInformation]:
        return self._request("workspace/symbol", {"query": query})
    
    def code_action(self, uri: str, range: Range, diagnostics: List[Diagnostic]) -> List[CodeAction]:
        return self._request("textDocument/codeAction", {
            "textDocument": {"uri": uri},
            "range": range,
            "context": {"diagnostics": diagnostics}
        })
    
    def formatting(self, uri: str, options: FormattingOptions) -> List[TextEdit]:
        return self._request("textDocument/formatting", {
            "textDocument": {"uri": uri},
            "options": options
        })
    
    def on_type_formatting(self, uri: str, line: int, char: int, ch: str) -> List[TextEdit]:
        return self._request("textDocument/onTypeFormatting", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": char},
            "ch": ch,
            "options": {...}
        })
```

---

## 3. 診斷與文檔同步

### 3.1 文檔同步
```python
class DocumentSyncManager:
    def __init__(self, client: LSPClient):
        self.client = client
        self.documents: Dict[str, DocumentState] = {}
    
    def did_open(self, uri: str, language_id: str, version: int, text: str):
        self.documents[uri] = DocumentState(uri, language_id, version, text)
        self.client._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": version,
                "text": text
            }
        })
    
    def did_change(self, uri: str, version: int, changes: List[TextDocumentContentChangeEvent]):
        state = self.documents.get(uri)
        if state:
            state.version = version
            state.apply_changes(changes)
        self.client._send_notification("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": version},
            "contentChanges": changes
        })
    
    def did_close(self, uri: str):
        if uri in self.documents:
            del self.documents[uri]
        self.client._send_notification("textDocument/didClose", {"textDocument": {"uri": uri}})
    
    def did_save(self, uri: str, text: str = None):
        params = {"textDocument": {"uri": uri}}
        if text:
            params["text"] = text
        self.client._send_notification("textDocument/didSave", params)
```

### 3.2 診斷處理
```python
class DiagnosticsManager:
    def __init__(self, client: LSPClient):
        self.client = client
        self.diagnostics: Dict[str, List[Diagnostic]] = {}
        self.client._register_notification("textDocument/publishDiagnostics", self._on_diagnostics)
    
    def _on_diagnostics(self, params: PublishDiagnosticsParams):
        self.diagnostics[params.uri] = params.diagnostics
        # 觸發回調/事件
        self._emit("diagnostics_changed", params.uri, params.diagnostics)
    
    def get_diagnostics(self, uri: str = None) -> Dict[str, List[Diagnostic]]:
        if uri:
            return {uri: self.diagnostics.get(uri, [])}
        return self.diagnostics
    
    def get_diagnostics_for_file(self, file_path: str) -> List[Diagnostic]:
        uri = file_to_uri(file_path)
        return self.diagnostics.get(uri, [])
    
    def get_severity_count(self, uri: str = None) -> Dict[str, int]:
        counts = {"error": 0, "warning": 0, "info": 0, "hint": 0}
        for diag in self.diagnostics.get(uri, []) if uri else [d for ds in self.diagnostics.values() for d in ds]:
            severity_map = {1: "error", 2: "warning", 3: "info", 4: "hint"}
            counts[severity_map.get(diag.severity, "info")] += 1
        return counts
```

---

## 4. 工作區管理

### 4.1 工作區文件夾
```python
class WorkspaceManager:
    def __init__(self, client: LSPClient):
        self.client = client
        self.folders: List[WorkspaceFolder] = []
    
    def add_folder(self, uri: str, name: str = None):
        folder = WorkspaceFolder(uri=uri, name=name or os.path.basename(uri))
        self.folders.append(folder)
        self.client._send_notification("workspace/didChangeWorkspaceFolders", {
            "event": {"added": [folder.to_dict()], "removed": []}
        })
    
    def remove_folder(self, uri: str):
        folder = next((f for f in self.folders if f.uri == uri), None)
        if folder:
            self.folders.remove(folder)
            self.client._send_notification("workspace/didChangeWorkspaceFolders", {
                "event": {"added": [], "removed": [folder.to_dict()]}
            })
```

### 4.2 配置變更
```python
class ConfigurationManager:
    def __init__(self, client: LSPClient):
        self.client = client
        self.settings: Dict[str, Any] = {}
    
    def get_configuration(self, items: List[ConfigurationItem]) -> List[Any]:
        future = self.client._send_request("workspace/configuration", {"items": items})
        return future.result()
    
    def did_change_configuration(self, settings: Dict[str, Any]):
        self.settings.update(settings)
        self.client._send_notification("workspace/didChangeConfiguration", {"settings": settings})
```

---

## 5. 代碼動作與重構支持

### 5.1 代碼動作
```python
class CodeActionProvider:
    def __init__(self, client: LSPClient):
        self.client = client
    
    def get_code_actions(self, uri: str, range: Range, diagnostics: List[Diagnostic], 
                         only: List[str] = None, trigger_kind: int = 1) -> List[CodeAction]:
        params = {
            "textDocument": {"uri": uri},
            "range": range,
            "context": {"diagnostics": diagnostics, "triggerKind": trigger_kind}
        }
        if only:
            params["context"]["only"] = only
        return self.client._request("textDocument/codeAction", params)
    
    def resolve_code_action(self, action: CodeAction) -> CodeAction:
        if action.command:
            return action
        return self.client._request("codeAction/resolve", {"action": action})
    
    def apply_code_action(self, action: CodeAction) -> WorkspaceEdit:
        if action.edit:
            return self.client.apply_workspace_edit(action.edit)
        if action.command:
            return self.execute_command(action.command)
        return None
```

---

## 5. 工具函數

```python
def file_to_uri(path: str) -> str:
    path = os.path.abspath(path)
    if sys.platform == "win32":
        return f"file:///{path.replace(os.sep, '/')}"
    return f"file://{path}"

def uri_to_file(uri: str) -> str:
    if uri.startswith("file://"):
        path = uri[7:]
        if sys.platform == "win32" and path.startswith("/"):
            path = path[1:]
        return path
    return uri

def position_to_lsp(line: int, char: int) -> Position:
    return {"line": line, "character": char}

def range_to_lsp(start_line, start_char, end_line, end_char) -> Range:
    return {"start": {"line": start_line, "character": start_char},
            "end": {"line": end_line, "character": end_char}}
```

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08