#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DevProjectTeamSkill MCP 服务（官方 mcp[cli] SDK / FastMCP）。

将技能库的程序化能力暴露为 MCP tools / resources / prompts，使任意 MCP 客户端
（opencode / Claude Code / Cursor / Trae 等）可统一调用，避免各工具各自复制或同步。

版本治理（单源 + 发布即更新，铁律#1）：
- 技能库版本号动态读取自 .trae/skills/dev-project-team-skill/SKILL.md（唯一事实来源），
  不硬编码；每次读取 skill://version 即得当前最新。
- publish_production.py 发布时额外生成 tools/mcp_server/manifest.json + VERSION，
  供非 MCP 探测拿到已发布版本；client 指向同一 server 即共享同版本，杜绝多工具反复同步。

安全约束（铁律#3/#8/#12）：
- 不接收/不打印 A 级凭据；副作用工具（solidify/publish）经 MCP 默认 dry_run 或禁用正式发布。
- estimate_cost 的 --append 仍写本地 gitignored 台账（铁律#12）。
"""
import os
import re
import sys
import json
import subprocess
from datetime import datetime, timezone

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.stderr.write("缺少依赖 mcp，请先安装：pip install \"mcp[cli]\"（见 tools/mcp_server/requirements.txt）\n")
    raise

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 仓库根
SKILLS_DIR = os.path.join(ROOT, ".trae", "skills")
ORCH = os.path.join(SKILLS_DIR, "dev-project-team-skill", "SKILL.md")

mcp = FastMCP("DevProjectTeamSkill")


def _read_version():
    if os.path.isfile(ORCH):
        with open(ORCH, encoding="utf-8") as f:
            for line in f:
                m = re.search(r"v(\d+\.\d+\.\d+)", line)
                if m:
                    return "v" + m.group(1)
    return "unknown"


# ---------- Tools（包装现有 CLI，零逻辑复制） ----------

@mcp.tool()
def skill_list() -> str:
    """列出全部角色包与子技能及其技能版本（从 .trae/skills 单源读取）。"""
    rows = []
    for name in sorted(os.listdir(SKILLS_DIR)):
        p = os.path.join(SKILLS_DIR, name)
        if not os.path.isdir(p):
            continue
        ver = "?"
        skill = os.path.join(p, "SKILL.md")
        if os.path.isfile(skill):
            with open(skill, encoding="utf-8") as f:
                for line in f:
                    m = re.search(r"技能版本[”：:]\s*v(\d+\.\d+\.\d+)", line)
                    if m:
                        ver = "v" + m.group(1)
                        break
        rows.append(f"{name}\t{ver}")
    return "\n".join(rows) if rows else "（.trae/skills 缺失）"


@mcp.tool()
def skill_load(role: str) -> str:
    """读取并返回指定角色/子技能的 SKILL.md 全文（如 role-architecture / dev-project-team-skill / best-practice-solution）。"""
    candidates = [
        os.path.join(SKILLS_DIR, role, "SKILL.md"),
        os.path.join(SKILLS_DIR, "dev-project-team-skill", "skills", role, "SKILL.md"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return open(c, encoding="utf-8").read()
    return f"未找到角色 {role} 的 SKILL.md（候选: {candidates}）"


@mcp.tool()
def run_gate(skill: str = "dev-project-team-skill", gate: str = "closure") -> str:
    """运行技能质量门禁：gate ∈ closure|version|release|links。返回门禁输出。"""
    scripts = {
        "closure": "check_skill_closure.py",
        "version": "check_version_consistency.py",
        "release": "check_skill_release_gate.py",
        "links": "check_skill_links.py",
    }
    if gate not in scripts:
        return f"未知 gate: {gate}（可选 {list(scripts)}）"
    cmd = [sys.executable, os.path.join(ROOT, "tools", scripts[gate]), skill]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


@mcp.tool()
def estimate_cost(model: str, in_tok: int, out_tok: int, batch: bool = False, append: bool = False) -> str:
    """估算大模型调用成本并可选写入台账（包装 tools/estimate_cost.py）。model 为 catalog §2 中模型名。"""
    cmd = [sys.executable, os.path.join(ROOT, "tools", "estimate_cost.py"),
           "--model", model, "--in-tok", str(in_tok), "--out-tok", str(out_tok)]
    if batch:
        cmd.append("--batch")
    if append:
        cmd.append("--append")
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


@mcp.tool()
def solidify(note: str, dry_run: bool = True) -> str:
    """固化（部署项目级三目录 + 刷新交接）。默认 dry_run=True 仅探测，避免经 MCP 误触发发布副作用。"""
    if dry_run:
        return "（安全默认）经 MCP 的 solidify 仅允许 dry_run 探测；正式固化请在本地终端执行：bash tools/solidify.sh \"<说明>\""
    cmd = ["bash", os.path.join(ROOT, "tools", "solidify.sh"), note]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


@mcp.tool()
def publish_production(dry_run: bool = True) -> str:
    """生产发布（全局库 + 多工具全局生效 + 生成 MCP 版本清单）。默认 dry_run=True 仅探测；正式发布请在本地终端执行。"""
    cmd = [sys.executable, os.path.join(ROOT, "tools", "publish_production.py")] + (["--dry-run"] if dry_run else [])
    if dry_run:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        return (r.stdout + r.stderr)[:4000]
    return "（安全默认）经 MCP 的正式发布被禁用；请在本地终端执行：python3 tools/publish_production.py"


@mcp.tool()
def mirror_push() -> str:
    """双推 GitHub + Gitee 镜像，返回推送结果（包装 tools/mirror_push.py）。"""
    cmd = [sys.executable, os.path.join(ROOT, "tools", "mirror_push.py")]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


# ---------- Resources（只读知识，URI 暴露） ----------

@mcp.resource("skill://index")
def skill_index() -> str:
    """技能总索引 SKILL_INDEX.md。"""
    p = os.path.join(SKILLS_DIR, "SKILL_INDEX.md")
    return open(p, encoding="utf-8").read() if os.path.isfile(p) else "缺失"


@mcp.resource("skill://role/{name}/SKILL")
def role_skill(name: str) -> str:
    """读取指定角色的 SKILL.md 内容（如 role-architecture）。"""
    return skill_load(name)


@mcp.resource("skill://references/{file}")
def reference_file(file: str) -> str:
    """读取 references 下某知识文档（如 dev_platform_catalog.md / iron_rules.md / api_contracts.md）。"""
    p = os.path.join(SKILLS_DIR, "references", file)
    return open(p, encoding="utf-8").read() if os.path.isfile(p) else f"缺失: {file}"


@mcp.resource("skill://version")
def skill_version() -> str:
    """当前技能库版本（动态读取自编排器 SKILL.md，发布即更新）。"""
    return _read_version()


# ---------- Prompts（角色调用模板） ----------

@mcp.prompt()
def invoke_role(role: str, task: str) -> str:
    """生成调用某角色处理任务的提示词模板。"""
    return (f"请加载角色 {role}（见 .trae/skills/{role}/SKILL.md），执行任务：{task}。"
            f"先读其 domain/ 流程，再按编排器『闭环执行系统』推进，阶段流转前过对应门禁。")


@mcp.prompt()
def phase_gate(phase: str) -> str:
    """生成阶段评审提示词模板（phase ∈ 启动/需求/架构/开发/测试/投产）。"""
    return (f"请对『{phase}』阶段做五维评审与门禁：台账 / 评审 / 变更审计 / EVM / 风险 / 安全审计；"
            f"门禁不通过不得流转至下一阶段。")


if __name__ == "__main__":
    # 默认 stdio；如需团队共享单端点，可改 mcp.run(transport="streamable-http")
    mcp.run()
