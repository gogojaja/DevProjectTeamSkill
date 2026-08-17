# 提供商抽象：GitHub / Jira 实现

> 编排器：`../SKILL.md`　上位：PSM 协议 §2.4

---

## 1. 提供商介面

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class RefInfo:
    """统一引用信息"""
    repo: str                 # owner/repo
    ref_type: str             # issue | pull | feature
    ref_id: str               # number or name
    title: str
    body: str
    labels: List[str]
    url: str
    author: str
    head_branch: Optional[str] = None  # PR head branch
    base_branch: Optional[str] = None  # PR base branch

class Provider(ABC):
    @abstractmethod
    def resolve_ref(self, ref: str) -> RefInfo:
        """解析引用字符串为统一 RefInfo"""
        pass
    
    @abstractmethod
    def fetch_ref(self, ref_info: RefInfo) -> RefInfo:
        """获取完整引用信息（标题、描述、分支等）"""
        pass
    
    @abstractmethod
    def check_state(self, ref_info: RefInfo) -> str:
        """检查状态：open/closed/merged"""
        pass
    
    @abstractmethod
    def create_branch(self, ref_info: RefInfo, base: str) -> str:
        """创建工作分支，返回分支名"""
        pass
```

---

## 2. GitHub Provider 实现

### 2.1 CLI 依赖
- `gh` (GitHub CLI) v2.0+
- 认证：`gh auth login` 或 `GH_TOKEN` 环境变量

### 2.2 实现细节

```python
class GitHubProvider(Provider):
    def __init__(self, repo: str, gh_cli: str = "gh"):
        self.repo = repo
        self.gh = gh_cli
    
    def _run_gh(self, args: List[str]) -> dict:
        cmd = [self.gh] + args + ["--repo", self.repo, "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ProviderError(f"gh CLI failed: {result.stderr}")
        return json.loads(result.stdout)
    
    def resolve_ref(self, ref: str) -> RefInfo:
        # 支援格式: #123, owner/repo#123, URL
        # 返回基础 RefInfo (repo, ref_type, ref_id)
        pass
    
    def fetch_ref(self, ref_info: RefInfo) -> RefInfo:
        if ref_info.ref_type == "issue":
            data = self._run_gh(["issue", "view", ref_info.ref_id, 
                "--json", "number,title,body,labels,url,author"])
            ref_info.title = data["title"]
            ref_info.body = data["body"]
            ref_info.labels = [l["name"] for l in data["labels"]]
            ref_info.url = data["url"]
            ref_info.author = data["author"]["login"]
        elif ref_info.ref_type == "pull":
            data = self._run_gh(["pr", "view", ref_info.ref_id,
                "--json", "number,title,body,labels,url,author,headRefName,baseRefName,headRepository"])
            ref_info.title = data["title"]
            ref_info.body = data["body"]
            ref_info.labels = [l["name"] for l in data["labels"]]
            ref_info.url = data["url"]
            ref_info.author = data["author"]["login"]
            ref_info.head_branch = data["headRefName"]
            ref_info.base_branch = data["baseRefName"]
        return ref_info
    
    def check_state(self, ref_info: RefInfo) -> str:
        if ref_info.ref_type == "issue":
            data = self._run_gh(["issue", "view", ref_info.ref_id, "--json", "state"])
            return data["state"]  # OPEN/CLOSED
        elif ref_info.ref_type == "pull":
            data = self._run_gh(["pr", "view", ref_info.ref_id, "--json", "state,merged"])
            if data["merged"]:
                return "merged"
            return data["state"]  # OPEN/CLOSED/MERGED
        return "unknown"
    
    def create_branch(self, ref_info: RefInfo, base: str) -> str:
        if ref_info.ref_type == "issue":
            title_slug = re.sub(r'[^a-z0-9]+', '-', ref_info.title.lower())[:30]
            branch = f"fix/{ref_info.ref_id}-{title_slug}"
        elif ref_info.ref_type == "pull":
            branch = f"pr-{ref_info.ref_id}-review"
        else:
            branch = f"feature/{ref_info.ref_id}"
        
        # 获取 base 分支
        subprocess.run(["git", "fetch", "origin", base], check=True)
        subprocess.run(["git", "checkout", "-b", branch, f"origin/{base}"], check=True)
        return branch
```

### 2.3 PR 审查专用流程

```python
def prepare_pr_review(self, pr_number: int) -> tuple[str, str]:
    """为 PR 审查准备 worktree，返回 (worktree_path, branch_name)"""
    # 1. 获取 PR 信息
    data = self._run_gh(["pr", "view", str(pr_number),
        "--json", "number,title,headRefName,baseRefName,headRepository"])
    
    head_branch = data["headRefName"]
    base_branch = data["baseRefName"]
    
    # 2. fetch PR ref
    subprocess.run(["git", "fetch", "origin", f"pull/{pr_number}/head:pr-{pr_number}-review"], check=True)
    
    # 3. worktree 路径
    worktree_path = f"$HOME/.psm/worktrees/{self.repo.replace('/', '_')}/pr-{pr_number}"
    
    # 4. 创建 worktree
    subprocess.run(["git", "worktree", "add", worktree_path, f"pr-{pr_number}-review"], check=True)
    
    return worktree_path, f"pr-{pr_number}-review"
```

---

## 3. Jira Provider 实现

### 3.1 CLI 依赖
- `jira-cli` (ankitpokhrel/jira-cli)
- 安装：`brew install ankitpokhrel/jira-cli/jira-cli` (macOS)
- 认证：`jira init` 交互式配置

### 3.2 配置要求

专案别名需显式配置 `jira_project`：
```json
{
  "aliases": {
    "mywork": {
      "jira_project": "MYPROJ",
      "repo": "mycompany/my-project",
      "local": "~/Workspace/my-project",
      "default_base": "develop",
      "provider": "jira"
    }
  }
}
```

### 3.3 实现细节

```python
class JiraProvider(Provider):
    def __init__(self, repo: str, jira_project: str, jira_cli: str = "jira"):
        self.repo = repo
        self.jira_project = jira_project
        self.jira = jira_cli
    
    def _run_jira(self, args: List[str]) -> dict:
        cmd = [self.jira] + args + ["--output", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ProviderError(f"jira CLI failed: {result.stderr}")
        return json.loads(result.stdout)
    
    def resolve_ref(self, ref: str) -> RefInfo:
        # 支援: PROJ-123 (需配置 jira_project), alias#123
        if "-" in ref and ref.split("-")[0].isalpha():
            # PROJ-123 格式
            project_key = ref.split("-")[0]
            if project_key != self.jira_project:
                raise ProviderError(f"Jira project {project_key} not configured")
            ref_info = RefInfo(repo=self.repo, ref_type="issue", ref_id=ref)
        else:
            raise ProviderError("Jira ref must be PROJ-123 format")
        return ref_info
    
    def fetch_ref(self, ref_info: RefInfo) -> RefInfo:
        data = self._run_jira(["issue", "view", ref_info.ref_id,
            "--fields", "summary,description,labels,url,assignee,status"])
        ref_info.title = data["fields"]["summary"]
        ref_info.body = data["fields"]["description"] or ""
        ref_info.labels = [l["name"] for l in data["fields"]["labels"]]
        ref_info.url = f"https://jira.example.com/browse/{ref_info.ref_id}"
        ref_info.author = data["fields"]["assignee"]["displayName"] if data["fields"]["assignee"] else "unassigned"
        return ref_info
    
    def check_state(self, ref_info: RefInfo) -> str:
        data = self._run_jira(["issue", "view", ref_info.ref_id, "--fields", "status"])
        status = data["fields"]["status"]["name"]
        if status in ["Done", "Closed", "Resolved"]:
            return "closed"
        return "open"
    
    def create_branch(self, ref_info: RefInfo, base: str) -> str:
        title_slug = re.sub(r'[^a-z0-9]+', '-', ref_info.title.lower())[:30]
        branch = f"fix/{ref_info.ref_id}-{title_slug}"
        subprocess.run(["git", "fetch", "origin", base], check=True)
        subprocess.run(["git", "checkout", "-b", branch, f"origin/{base}"], check=True)
        return branch
```

### 3.4 Jira 限制

| 限制 | 说明 |
|------|------|
| 无 PR 概念 | 不支援 `psm review`，仅支援 `fix`/`feature` |
| 需显式配置 | `jira_project` 必须在 aliases 中配置 |
| CLI 独立认证 | `jira init` 独立于 gh 认证 |

---

## 4. 提供商工厂

```python
def get_provider(config: dict) -> Provider:
    provider = config.get("provider", "github")
    repo = config["repo"]
    
    if provider == "github":
        return GitHubProvider(repo)
    elif provider == "jira":
        jira_project = config.get("jira_project")
        if not jira_project:
            raise ConfigError("Jira provider requires jira_project in alias config")
        return JiraProvider(repo, jira_project)
    else:
        raise ConfigError(f"Unknown provider: {provider}")
```

---

## 5. 引用解析器

```python
def parse_ref(ref: str, default_project: str = None) -> tuple[Provider, RefInfo]:
    """统一入口：解析引用字符串 → (Provider, RefInfo)"""
    
    # 1. 如果有别名配置
    if "#" in ref and not ref.startswith("#"):
        alias, rest = ref.split("#", 1)
        project_config = load_project_config(alias)
        provider = get_provider(project_config)
        ref_info = provider.resolve_ref(f"{project_config.get('jira_project', '')}-{rest}" if project_config.get("provider") == "jira" else rest)
        ref_info.repo = project_config["repo"]
        return provider, ref_info
    
    # 2. 当前 repo 推断
    if ref.startswith("#"):
        repo = get_current_repo()
        provider = get_provider({"provider": "github", "repo": repo})
        ref_info = provider.resolve_ref(ref)
        ref_info.repo = repo
        return provider, ref_info
    
    # 3. 完整格式 owner/repo#num
    if "/" in ref and "#" in ref:
        repo_part, num_part = ref.split("#", 1)
        owner, repo_name = repo_part.split("/", 1)
        repo = f"{owner}/{repo_name}"
        provider = get_provider({"provider": "github", "repo": repo})
        ref_info = provider.resolve_ref(num_part)
        ref_info.repo = repo
        return provider, ref_info
    
    # 4. URL
    if ref.startswith("https://github.com/"):
        # 解析 URL
        pass
    
    raise ValueError(f"Unable to parse ref: {ref}")
```

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08