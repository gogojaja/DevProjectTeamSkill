#!/usr/bin/env python3
"""DevProjectTeamSkill MCP Server

将本技能库封装为 MCP (Model Context Protocol) 服务，暴露三类能力：
  - Tools:     可执行工具（solidify/deploy/check/cmdb/desensitize 等）
  - Resources: 可读知识文档（SKILL.md / references / SKILL_INDEX）
  - Prompts:   参数化角色路由模板（按角色包引导 AI 执行流程）

依赖：      uv run --python 3.10 --with "mcp[cli]" python3 tools/mcp_server.py
调试：      uv run --python 3.10 --with "mcp[cli]" mcp dev tools/mcp_server.py
"""

import os
import sys
import json
import subprocess
import importlib.util
from pathlib import Path

from mcp.server import MCPServer

mcp = MCPServer("dev-project-team-skill")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools"
SKILLS_DIR = PROJECT_ROOT / ".trae" / "skills"


# ─── Helpers ──────────────────────────────────────────────────────

def _run_tool(script_name: str, *args, cwd=None) -> dict:
    """运行 tools/ 下的 Python 脚本并返回结构化结果。"""
    script = TOOLS_DIR / script_name
    if not script.exists():
        return {"ok": False, "error": f"脚本不存在: {script}"}
    cmd = [sys.executable, str(script), *args]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=300,
        cwd=cwd or str(PROJECT_ROOT),
    )
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout[-8000:] if result.stdout else "",
        "stderr": result.stderr[-4000:] if result.stderr else "",
    }


# ─── MCP Tools: 可执行工具 ───────────────────────────────────────

@mcp.tool()
def solidify(description: str) -> dict:
    """一键基线固化：3 硬门禁 + 交接刷新 + 快照 + 打包 + 部署四目录。

    Args:
        description: 固化说明（写入交接文档断点区）
    """
    return _run_tool("solidify.py", description)


@mcp.tool()
def deploy_skills(roles: str = "") -> dict:
    """部署技能包到 .github/.claude/.agents 及 opencode 全局库。

    Args:
        roles: 逗号分隔的角色名（如 role-a,role-b），空=全部
    """
    args = []
    if roles:
        args = ["--roles", roles]
    return _run_tool("deploy_skills.py", *args)


@mcp.tool()
def package_skills(role: str = "") -> dict:
    """打包角色包到 dist/ 目录。

    Args:
        role: 单个角色包名（如 role-testing），空=全部
    """
    args = []
    if role:
        args = ["--role", role]
    return _run_tool("package_skills.py", *args)


@mcp.tool()
def check_traceability(matrix_path: str = "") -> dict:
    """需求-架构-代码三方一致性检查（孤儿/断链门禁）。

    Args:
        matrix_path: 追溯矩阵 CSV 路径，空=默认 需求-架构-代码追溯矩阵.csv
    """
    args = [matrix_path] if matrix_path else []
    return _run_tool("check_traceability.py", *args)


@mcp.tool()
def check_version_consistency() -> dict:
    """版本一致性硬门禁：校验 SKILL_INDEX/SKILL.md/CHANGELOG 版本号一致。"""
    return _run_tool("check_version_consistency.py")


@mcp.tool()
def check_skill_closure(skill_path: str = "") -> dict:
    """技能闭环执行能力检查：校验技能是否具备闭环执行系统章节。

    Args:
        skill_path: 技能目录路径，空=检查全部角色包
    """
    args = [skill_path] if skill_path else []
    return _run_tool("check_skill_closure.py", *args)


@mcp.tool()
def check_deprecation_cleanup() -> dict:
    """废弃清理门禁：检查废弃 ADR 资产是否有残留引用或运行态残留。"""
    return _run_tool("check_deprecation_cleanup.py")


@mcp.tool()
def cmdb(action: str, resource_type: str = "", resource_id: str = "",
         operator: str = "", port: int = 0, notes: str = "") -> dict:
    """CMDB 轻量级资源管理（注册/查询/释放/冲突检测）。

    Args:
        action: init | register | query | release | conflict | export
        resource_type: port | container | db | model | gpu
        resource_id: 资源标识（如 8080）
        operator: 操作者
        port: 端口号（resource_type=port 时使用）
        notes: 备注
    """
    args = [action]
    if resource_type:
        args += ["--type", resource_type]
    if resource_id:
        args += ["--id", resource_id]
    if operator:
        args += ["--operator", operator]
    if port:
        args += ["--port", str(port)]
    if notes:
        args += ["--notes", notes]
    return _run_tool("cmdb/cmdb-cli.py", *args)


@mcp.tool()
def desensitize(target: str, mode: str = "scan", output: str = "",
                dictionary: str = "") -> dict:
    """文档脱敏工具（A/B/C 三级敏感信息扫描与替换）。

    Args:
        target: 目标文件或目录路径
        mode: scan（仅扫描）| replace（脱敏替换）
        output: 输出文件路径（replace 模式）
        dictionary: 脱敏字典 CSV 路径（可选）
    """
    args = [target]
    if mode == "replace" and output:
        args += ["-o", output]
    if dictionary:
        args += ["--dictionary", dictionary]
    if mode == "scan":
        args.insert(0, "--scan")
    return _run_tool("desensitize/desensitize.py", *args)


@mcp.tool()
def list_skills() -> dict:
    """列出所有角色包及其触发词（从 SKILL_INDEX.md 解析）。"""
    index = SKILLS_DIR / "SKILL_INDEX.md"
    if not index.exists():
        return {"ok": False, "error": "SKILL_INDEX.md 不存在"}
    lines = index.read_text(encoding="utf-8").splitlines()
    roles = []
    for line in lines:
        if line.startswith("| ") and "role-" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                roles.append({
                    "index": parts[1],
                    "package": parts[2],
                    "domain": parts[3],
                    "triggers": parts[4],
                    "path": parts[5],
                })
    return {"ok": True, "count": len(roles), "roles": roles}


# ─── MCP Resources: 知识文档 ─────────────────────────────────────

@mcp.resource("skill://index")
def skill_index() -> str:
    """SKILL_INDEX.md — 角色包索引清单（路由入口）。"""
    return (SKILLS_DIR / "SKILL_INDEX.md").read_text(encoding="utf-8")


@mcp.resource("skill://{role}/SKILL.md")
def skill_doc(role: str) -> str:
    """指定角色包的 SKILL.md 根文件。"""
    path = SKILLS_DIR / role / "SKILL.md"
    if not path.exists():
        return f"[错误] {role}/SKILL.md 不存在"
    return path.read_text(encoding="utf-8")


@mcp.resource("ref://{doc_name}")
def reference_doc(doc_name: str) -> str:
    """references/ 下的公共标准文档（iron_rules/token_standard/api_contracts 等）。"""
    if not doc_name.endswith(".md"):
        doc_name += ".md"
    path = SKILLS_DIR / "references" / doc_name
    if not path.exists():
        return f"[错误] references/{doc_name} 不存在"
    return path.read_text(encoding="utf-8")


@mcp.resource("skill://{role}/domain/{domain_name}")
def skill_domain(role: str, domain_name: str) -> str:
    """角色包子域明细文件（如 role-architecture/domain/strategy.md）。"""
    if not domain_name.endswith(".md"):
        domain_name += ".md"
    path = SKILLS_DIR / role / "domain" / domain_name
    if not path.exists():
        return f"[错误] {role}/domain/{domain_name} 不存在"
    return path.read_text(encoding="utf-8")


# ─── MCP Prompts: 角色路由模板 ───────────────────────────────────

@mcp.prompt()
def route_role(user_request: str) -> str:
    """根据用户请求自动路由到合适的角色包。

    Args:
        user_request: 用户的自然语言请求
    """
    return f"""你是 DevProjectTeamSkill 软件研发多角色编排器。

用户请求：{user_request}

请按以下步骤执行：
1. 读取 skill://index 获取角色包索引清单
2. 根据用户请求中的触发词匹配角色包（参考索引表中的触发词列）
3. 读取匹配角色包的 skill://<角色包名>/SKILL.md
4. 按 SKILL.md 中的流程执行用户请求
5. 如涉及多角色协同，按编排器路由表组合加载

触发词速查：
  - 启动/立项/章程/干系人/RACI → role-project-init
  - 需求/SRS/需求规格 → role-requirements-analysis
  - 架构/ADR/C4/数据架构 → role-architecture
  - 开发/编码/代码评审/单元测试 → role-development
  - 测试/用例/缺陷 → role-testing
  - 投产/部署/发布/回滚 → role-deployment
  - 台账/评审/门禁/基线固化/审计 → role-governance
  - 项目群/多项目/PMO → role-program-mgmt
  - 咨询/成熟度/PMO设计 → role-mgmt-consulting
"""


@mcp.prompt()
def stage_review(stage: str, deliverables: str) -> str:
    """阶段评审提示模板。

    Args:
        stage: 阶段名称（如 需求/架构/开发/测试）
        deliverables: 本阶段产出物清单（逗号分隔）
    """
    return f"""你是阶段评审员。请对以下阶段执行标准化评审。

阶段：{stage}
产出物：{deliverables}

评审流程：
1. 读取 ref://api_contracts 了解评审接口规范
2. 读取 ref://iron_rules 确认铁律约束
3. 按以下五维评审：
   - 范围完整性：产出物是否覆盖阶段全部范围项
   - 质量符合性：是否符合对应标准（IEEE 830 / ISO 25010 等）
   - 追溯一致性：需求-架构-代码追溯链是否完整（调用 check_traceability 工具）
   - 门禁通过性：阶段门禁是否全部放行（版本一致性/闭环/废弃清理/追溯）
   - 铁律合规性：授权/备份/留痕/脱敏是否合规
4. 评审结果输出为 CSV（UTF-8 with BOM），仅回显首 5 行 + 行数
"""


@mcp.prompt()
def skill_authoring(skill_name: str, action: str = "create") -> str:
    """技能编写/修改提示模板。

    Args:
        skill_name: 技能名称
        action: create（新建）| modify（修改）| verify（校验）
    """
    return f"""你是技能维护工程师。请执行技能{action}任务。

技能名称：{skill_name}
操作类型：{action}

执行流程（shared/authoring.md 六步）：
1. 定义：明确技能目标、触发条件、适用场景
2. 建模：设计闭环执行系统（任务入口/状态机/验收门禁/失败恢复/交接审计）
3. 编写：编写 SKILL.md（description 150~250 字符，含触发词与 Load when）
4. 校验：运行 check_skill_closure + check_skill_release_gate + check_version_consistency
5. 验证：在模拟场景中验证技能可被正确触发与执行
6. 打包发布：更新 SKILL_INDEX.md + api_contracts.md，执行 solidify 固化

铁律：
- 源码单源：只在 .trae/skills/ 操作，禁止手工复制 shared/references
- 闭环执行：必须具备「闭环执行系统」标题与模板
- 版本一致：SKILL_INDEX/SKILL.md/CHANGELOG 版本号必须一致
"""


# ─── 启动 ────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
