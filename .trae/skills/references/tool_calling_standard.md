# tool_calling_standard.md — 工具外部调用规范（单源共享）

> 适用：本仓库 `tools/*.py` 全部工具 + 今后经本技能开发的技能/项目中的工具。
> 目标：所有工具均具备被其他项目直接调用的能力，通过 `PROJECT_ROOT` 环境变量注入目标项目根目录。

## 1. 铁律：PROJECT_ROOT 优先解析

所有工具的仓库根目录解析必须遵循以下优先级：

```python
# 优先级 1：环境变量 PROJECT_ROOT（外部调用方注入）
# 优先级 2：__file__ 相对计算（本仓库内调用时的兜底）
ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

或使用 pathlib：

```python
ROOT = Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent)))
```

### 1.1 禁止的模式

| 禁止 | 原因 | 正确 |
|------|------|------|
| `ROOT = "/hardcoded/path"` | 硬编码绝对路径，迁移即失效 | `os.environ.get("PROJECT_ROOT", ...)` |
| `ROOT = os.path.join('.trae', 'skills')` | CWD 依赖，从其他目录调用失效 | `os.path.join(REPO_ROOT, '.trae', 'skills')` |
| `git rev-parse --show-toplevel` 独占 | 不支持外部项目注入 | PROJECT_ROOT 优先 → git rev-parse → `__file__` 兜底 |
| `os.getcwd()` 独占 | CWD 依赖 | PROJECT_ROOT 优先 → getcwd → `__file__` 兜底 |

### 1.2 find_repo_root() 标准实现

工具若有独立的 `find_repo_root()` 函数，须遵循：

```python
def find_repo_root():
    """PROJECT_ROOT 环境变量优先 → git rev-parse → __file__ 回退。"""
    env_root = os.environ.get("PROJECT_ROOT")
    if env_root and os.path.isdir(env_root):
        return os.path.abspath(env_root)
    try:
        import subprocess
        out = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                             capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return os.path.abspath(out.stdout.strip())
    except Exception:
        pass
    cur = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return cur
```

## 2. CLI 接口要求

### 2.1 必须有 CLI 入口

```python
if __name__ == "__main__":
    main()
```

### 2.2 必须支持 --help

使用 `argparse` 或等效库，`python tools/<name>.py --help` 须输出用法说明。

### 2.3 无副作用运行

- `--dry-run` 或 `--verify` 模式：仅探测不执行副作用操作
- 无参数时：默认安全行为（只读/列表），不执行写操作

## 3. 外部调用方式

### 3.1 其他项目调用本仓库工具

```bash
# 方式 A：环境变量注入（推荐）
PROJECT_ROOT=/path/to/target/project python3 /path/to/DevProjectTeamSkill/tools/lint_repo.py

# 方式 B：在目标项目目录中调用（依赖 CWD 兜底）
cd /path/to/target/project
python3 /path/to/DevProjectTeamSkill/tools/check_traceability.py
```

### 3.2 今后经本技能开发的工具

新工具开发时**必须**遵循本规范：

1. ROOT 解析：`os.environ.get("PROJECT_ROOT", __file__兜底)`
2. 内部路径：`os.path.join(ROOT, "台账", "xxx.csv")`（不硬编码）
3. CLI 入口：`if __name__ == "__main__": main()`
4. `--help` 支持
5. 无副作用运行模式

## 4. 工具分类

| 类别 | 说明 | PROJECT_ROOT 注入效果 |
|------|------|----------------------|
| 通用工具 | 不引用 `.trae/skills` 或 `台账/`，如 `excel_to_csv.py` | 可直接调用，PROJECT_ROOT 无实际影响 |
| 技能库工具 | 引用 `.trae/skills` 结构，如 `check_skill_links.py` | 注入后扫描目标项目的 `.trae/skills/` |
| 台账工具 | 引用 `台账/` 目录，如 `audit.py` | 注入后读写目标项目的 `台账/` |
| 代理工具 | 薄封装代理转发到 dev-git-hub，如 `mirror_push.py` | 注入后转发时注入 PROJECT_ROOT 给目标脚本 |

## 5. 审计与门禁

- 新增/修改工具时，须自检 ROOT 解析是否符合 §1 铁律
- `lint_repo.py` 可扫描工具文件中的硬编码路径模式（未来增强）
- 违反本规范的工具不得通过 `solidify` 固化门禁（未来纳入）

---

**文档版本**：v1.0.0　**最后更新**：2026-08-31（建立工具外部调用规范，全部 47 个工具已支持 PROJECT_ROOT 注入）
