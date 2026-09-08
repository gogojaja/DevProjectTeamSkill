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
import csv
import subprocess
from datetime import datetime, timezone
from pathlib import Path

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
                    m = re.search(r"技能版本\**\s*[:：]\s*v(\d+\.\d+\.\d+)", line)
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


# ---------- 新增 Tools（v21.13.0 AI Agent 功能提升） ----------

@mcp.tool()
def skill_search(query: str, max_results: int = 10) -> str:
    """语义搜索技能文档（关键词匹配）。在 .trae/skills/ 下搜索包含 query 的技能内容。

    Args:
        query: 搜索关键词（支持中英文）
        max_results: 最大返回结果数（默认 10）
    """
    results = []
    query_lower = query.lower()
    for root_dir, dirs, files in os.walk(SKILLS_DIR):
        for fn in files:
            if fn.endswith(".md"):
                fp = os.path.join(root_dir, fn)
                try:
                    with open(fp, encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if query_lower in content.lower():
                        rel = os.path.relpath(fp, SKILLS_DIR)
                        # 提取匹配行上下文
                        lines = content.splitlines()
                        for i, line in enumerate(lines):
                            if query_lower in line.lower():
                                ctx = lines[max(0, i-1):i+2]
                                results.append(f"{rel}:{i+1}: {' | '.join(ctx)}")
                                if len(results) >= max_results:
                                    break
                except Exception:
                    pass
            if len(results) >= max_results:
                break
        if len(results) >= max_results:
            break
    return f"搜索 '{query}' 找到 {len(results)} 处匹配：\n" + "\n".join(results) if results else f"未找到包含 '{query}' 的技能文档"


@mcp.tool()
def skill_links() -> str:
    """技能引用可达性检查（包装 tools/check_skill_links.py）。检查技能文档间的引用是否可达。"""
    script = os.path.join(ROOT, "tools", "check_skill_links.py")
    if not os.path.isfile(script):
        return "check_skill_links.py 不存在，请检查 tools/ 目录"
    cmd = [sys.executable, script]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


@mcp.tool()
def audit_query(action: str = "recent", limit: int = 20) -> str:
    """审计台账查询（只读模式）。查询 13_安全审计台账 或 14_授权登记。

    Args:
        action: 查询类型（recent=最近记录 / auth=授权登记 / summary=摘要统计）
        limit: 返回记录数上限（默认 20）
    """
    ledger_dir = os.path.join(ROOT, "台账")
    if action == "recent":
        fp = os.path.join(ledger_dir, "13_安全审计台账.csv")
    elif action == "auth":
        fp = os.path.join(ledger_dir, "14_授权登记.csv")
    elif action == "summary":
        # 返回两个台账的行数统计
        audit_fp = os.path.join(ledger_dir, "13_安全审计台账.csv")
        auth_fp = os.path.join(ledger_dir, "14_授权登记.csv")
        audit_count = sum(1 for _ in open(audit_fp, encoding="utf-8-sig")) - 1 if os.path.isfile(audit_fp) else 0
        auth_count = sum(1 for _ in open(auth_fp, encoding="utf-8-sig")) - 1 if os.path.isfile(auth_fp) else 0
        return f"审计台账摘要：\n  安全审计记录：{audit_count} 条\n  授权登记记录：{auth_count} 条"
    else:
        return f"未知 action: {action}（可选 recent / auth / summary）"

    if not os.path.isfile(fp):
        return f"台账文件不存在：{fp}"
    with open(fp, encoding="utf-8-sig") as f:
        lines = f.readlines()
    header = lines[0].strip() if lines else ""
    data = lines[1:limit+1]
    return f"表头：{header}\n\n最近 {len(data)} 条记录：\n" + "".join(data)


@mcp.tool()
def scope_metrics(write: bool = False) -> str:
    """范围覆盖度指标与健康分（包装 tools/scope_tracker.py metrics）。

    Args:
        write: 是否写入 07_范围跟踪台账快照（默认 False 仅查询）
    """
    script = os.path.join(ROOT, "tools", "scope_tracker.py")
    if not os.path.isfile(script):
        return "scope_tracker.py 不存在，请检查 tools/ 目录"
    cmd = [sys.executable, script, "metrics"]
    if write:
        cmd.append("--write")
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


@mcp.tool()
def retro_harvest(stage: str, obj: str, good: str = "", improve: str = "", action: str = "", dry_run: bool = True) -> str:
    """复盘收割（包装 tools/retro_cli.py）。写 22_阶段复盘 + 提取行动项 + 登记经验库。

    Args:
        stage: 阶段名称（如 需求/架构/开发/测试/投产）
        obj: 复盘对象（如 技能库本体/某角色包）
        good: 做得好的方面（逗号分隔）
        improve: 需改进的方面（逗号分隔）
        action: 行动项（格式：描述;owner:xxx;deadline:yyyy-mm-dd）
        dry_run: 是否仅探测不写入（默认 True）
    """
    script = os.path.join(ROOT, "tools", "retro_cli.py")
    if not os.path.isfile(script):
        return "retro_cli.py 不存在，请检查 tools/ 目录"
    cmd = [sys.executable, script, "--stage", stage, "--object", obj]
    if good:
        cmd += ["--good", good]
    if improve:
        cmd += ["--improve", improve]
    if action:
        cmd += ["--action", action]
    if dry_run:
        return f"（安全默认）复盘 dry_run 模式。参数：stage={stage}, object={obj}, good={good}, improve={improve}"
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


@mcp.tool()
def review_execute(target: str, perspectives: str = "architect,security", dry_run: bool = True) -> str:
    """MPV 多视角评审执行（包装 tools/mpv_cli.py）。评审落盘 CSV + 脱敏扫描。

    Args:
        target: 评审对象（如 技能库本体/某角色包/某 ADR）
        perspectives: 评审视角（逗号分隔，默认 architect,security）
        report: 输出报告路径（默认 docs/reviews/评审报告_<对象>_<视角>.csv）
        dry_run: 是否仅探测不执行（默认 True）
    """
    script = os.path.join(ROOT, "tools", "mpv_cli.py")
    if not os.path.isfile(script):
        return "mpv_cli.py 不存在，请检查 tools/ 目录"
    cmd = [sys.executable, script, "--target", target, "--perspectives", perspectives]
    if dry_run:
        cmd.append("--dry-run")
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


@mcp.tool()
def nightly_gate(action: str = "list", target: str = "", dry_run: bool = True) -> str:
    """夜间质量门禁（包装 tools/nightly_quality_gate.py）。跨项目 registry 质量门禁。

    Args:
        action: 操作类型（list=列举项目 / run=执行门禁）
        target: 目标项目别名（action=run 时使用，空=全部项目）
        dry_run: 是否仅探测不执行（默认 True）
    """
    script = os.path.join(ROOT, "tools", "nightly_quality_gate.py")
    if not os.path.isfile(script):
        return "nightly_quality_gate.py 不存在，请检查 tools/ 目录"
    cmd = [sys.executable, script, action]
    if target:
        cmd += ["--target", target]
    if dry_run and action == "run":
        cmd.append("--dry-run")
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


@mcp.tool()
def skill_progress() -> str:
    """查询当前任务执行状态与进度。读取交接文档 L1 核心摘要，返回当前阶段/角色/任务/风险/下一步。"""
    handoff = os.path.join(ROOT, "交接文档.md")
    if not os.path.isfile(handoff):
        return "交接文档.md 不存在"
    with open(handoff, encoding="utf-8") as f:
        content = f.read()
    # 提取 L1 核心摘要区
    l1_match = re.search(r"## 🔴 L1 必读核心.*?### 项目速览(.*?)### 当前阶段/角色/任务(.*?)### 关键风险/阻塞(.*?)### 下一步唯一动作(.*?)(?=###|$)", content, re.DOTALL)
    if not l1_match:
        return "无法解析交接文档 L1 核心摘要区"
    project_info = l1_match.group(1).strip()
    stage_info = l1_match.group(2).strip()
    risk_info = l1_match.group(3).strip()
    next_action = l1_match.group(4).strip()
    return f"""📊 当前任务进度

【项目速览】
{project_info}

【当前阶段/角色/任务】
{stage_info}

【关键风险/阻塞】
{risk_info}

【下一步动作】
{next_action}"""


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


# ---------- 新增 Prompts（v21.13.0 AI Agent 功能提升） ----------

@mcp.prompt()
def architecture_design(project_name: str, domain: str = "通用") -> str:
    """引导架构设计全流程的提示词模板。

    Args:
        project_name: 项目名称
        domain: 业务领域（默认 通用）
    """
    return f"""你是架构设计师。请为项目『{project_name}』（领域：{domain}）执行架构设计全流程。

执行步骤（对齐 role-architecture 角色包）：
1. **架构策略分析**：业务上下文分析 → 质量属性量化 → 约束梳理 → ATAM 权衡 → 技术选型矩阵
2. **架构设计**：4+1 视图（逻辑/开发/进程/物理/场景）+ C4 模型（System/Container/Component）
3. **ADR 决策记录**：关键技术决策点用 MADR 格式记录（标题/状态/上下文/决策/后果）
4. **原型验证**：POC + 跨平台 + 性能基准
5. **ATAM 评审**：质量属性评估 + 反模式检查 + 七原则终审
6. **基线固化**：架构设计说明书 + 架构指南 + 归档

输出规范（CSV UTF-8 with BOM）：
- 架构策略分析报告.csv
- 技术选型评估矩阵.csv
- 质量属性需求矩阵.csv
- 架构风险登记册.csv

铁律：设计须评审通过后方可流转至开发阶段；禁止编写需求文档/测试用例/部署脚本。"""


@mcp.prompt()
def test_planning(phase: str = "测试", risk_level: str = "中") -> str:
    """引导测试计划编写的提示词模板。

    Args:
        phase: 当前阶段（默认 测试）
        risk_level: 风险等级（高/中/低，默认 中）
    """
    return f"""你是测试工程师。请为『{phase}』阶段编写测试计划（风险等级：{risk_level}）。

执行步骤（对齐 role-testing 角色包）：
1. **可测性分析**：需求可测性等级（A/B/C）+ 测试优先级
2. **风险评估**：风险矩阵（概率 × 影响）→ 测试优先级分配
3. **测试策略**：测试方法选型（手动/自动/混合）+ 测试类型定义（功能/SIT/API/非功能/安全）
4. **测试计划**：测试范围 + 测试环境 + 测试数据 + 进入/退出准则 + 工时估算
5. **用例设计**：等价类/边界值/决策表/状态迁移（按风险优先级）
6. **缺陷管理**：缺陷分级（P1~P4）+ 处理流程 + 度量指标

输出规范（CSV UTF-8 with BOM）：
- 测试追溯矩阵.csv（需求-用例-缺陷追溯）
- 缺陷清单.csv（P1~P4 分级）
- 测试总结报告.csv（执行统计 + 门禁结论）

铁律：测试计划须在测试执行前完成评审；缺陷须分级处理；门禁不通过不得流转。"""


@mcp.prompt()
def incubation_assess(candidate_name: str, candidate_type: str = "技能") -> str:
    """引导孵化评估的提示词模板。

    Args:
        candidate_name: 候选名称（技能/工具/项目名称）
        candidate_type: 候选类型（技能/工具/项目，默认 技能）
    """
    return f"""你是孵化器评审员。请对候选『{candidate_name}』（类型：{candidate_type}）执行孵化评估。

执行步骤（对齐 incubator-initiation 子技能）：
1. **方案调研**：现有方案/工具/技能分析 + 差距识别 + 改进机会
2. **可行性五维评估**：
   - 技术可行性（技术栈/依赖/复杂度）
   - 资源可行性（人力/时间/基础设施）
   - 商业可行性（价值/ROI/战略对齐）
   - 运维可行性（部署/监控/维护成本）
   - 风险可行性（技术债/合规/安全）
3. **独立性三判据**：
   - 复用率（≥3 项目使用 → 倾向独立）
   - 独立性（可独立运行/维护 → 倾向独立）
   - 维护成本（独立维护成本 ≤ 当前 → 倾向独立）
4. **孵化决策**：三选一（独立化/保留本库/暂缓）
5. **评审聚合**：3 视角评审（架构/安全/运维）
6. **移交清单**：六段式（背景/目标/范围/交付物/时间线/风险）

输出规范：
- 立项建议书（docs/incubator/INC-*.md）
- 评审报告（docs/reviews/评审报告_<候选>_<视角>.csv）

铁律：只评估不落地；落地交对应独立项目运营者执行。"""


@mcp.prompt()
def retrospective(stage: str, obj: str) -> str:
    """引导复盘收割的提示词模板。

    Args:
        stage: 阶段名称（如 需求/架构/开发/测试/投产）
        obj: 复盘对象（如 技能库本体/某角色包/某项目）
    """
    return f"""你是复盘引导师。请对『{stage}』阶段的『{obj}』执行复盘收割。

执行步骤（对齐 role-governance 复盘流程）：
1. **回顾目标**：本阶段原计划目标是什么？成功标准是什么？
2. **评估结果**：实际达成了什么？与目标的差距是多少？
3. **分析原因**：
   - 做得好的方面（继续保持）
   - 需改进的方面（根本原因分析）
   - 意外发现（正面/负面）
4. **总结经验**：
   - 可复用的经验（登记经验库）
   - 需避免的陷阱（登记教训库）
   - 需改进的流程（登记行动项）
5. **行动项**：
   - 具体行动（owner + deadline）
   - 优先级（P0/P1/P2）
   - 验收标准

输出规范（CSV UTF-8 with BOM）：
- 22_阶段复盘.csv（阶段/对象/做得好/需改进/行动项）
- 行动项台账（owner/deadline/status）

铁律：复盘须在阶段结束后 1 周内完成；行动项须有明确 owner 和 deadline；经验须登记经验库。"""


# ---------- 新增 Tools（v21.14.0 AI Agent PM 能力提升） ----------

def _run_mgmt_cli(args: list) -> str:
    """调用 dev-project-mgmt 代理并返回输出（截断 4000 字符）。"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from _project_mgmt_proxy import run_project_mgmt_cli
    result = run_project_mgmt_cli(args=args, capture=True)
    output = (result.stdout or "") + (result.stderr or "")
    return output[:4000] if output else f"(退出码 {result.returncode})"


@mcp.tool()
def raid_mgmt(action: str, raid_type: str = "", desc: str = "", raid_id: str = "",
              status: str = "", owner: str = "", dry_run: bool = True) -> str:
    """RAID 四维台账管理（风险/假设/问题/依赖）。

    委派本地权威工具 tools/raid_ops.py（risk-mgmt 技能单一信源，内化自
    dev-project-mgmt raid_manager），不再委派 dev-project-mgmt CLI。

    Args:
        action: 操作类型（list/add/update/close）
        raid_type: RAID 类型（risk/assumption/issue/dependency），action=add 时必填
        desc: 描述，action=add 时必填
        raid_id: RAID ID，action=update/close 时必填
        status: 新状态，action=update 时可选
        owner: 责任人，action=add/update 时可选
        dry_run: 是否仅探测不执行（默认 True）
    """
    script = os.path.join(ROOT, "tools", "raid_ops.py")
    if not os.path.isfile(script):
        return "raid_ops.py 不存在，请检查 tools/ 目录（risk-mgmt 技能权威工具）"
    if action == "list":
        cmd = [sys.executable, script, "list"]
        if raid_type:
            cmd += ["--type", raid_type]
    elif action == "add":
        if dry_run:
            return f"(dry-run) 将添加 RAID: type={raid_type}, desc={desc}"
        cmd = [sys.executable, script, "add", "--type", raid_type, "--desc", desc]
        if owner:
            cmd += ["--owner", owner]
    elif action in ("update", "close"):
        if dry_run and action == "update":
            return f"(dry-run) 将更新 {raid_id}: status={status}"
        cmd = [sys.executable, script, action, "--id", raid_id]
        if action == "update" and status:
            cmd += ["--status", status]
    else:
        return f"未知 action: {action}（可选 list/add/update/close）"
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


@mcp.tool()
def evm_analyze(action: str = "calc", milestone_id: str = "", milestone_name: str = "",
                planned_end: str = "", planned_value: float = 0.0) -> str:
    """EVM 挣值分析（PV/EV/AC/SPI/CPI）。

    委派本地权威工具 tools/evm_ops.py（schedule-cost 技能单一信源，内化自
    dev-project-mgmt evm_calculator，公式一致），不再委派 dev-project-mgmt CLI。

    Args:
        action: 操作类型（calc=计算指标 / status=查看状态 / add-milestone=添加里程碑）
        milestone_id: 里程碑 ID（action=add-milestone 时必填）
        milestone_name: 里程碑名称（action=add-milestone 时必填）
        planned_end: 计划结束日期（action=add-milestone 时可选）
        planned_value: 计划值 PV（action=add-milestone 时可选）
    """
    script = os.path.join(ROOT, "tools", "evm_ops.py")
    if not os.path.isfile(script):
        return "evm_ops.py 不存在，请检查 tools/ 目录（schedule-cost 技能权威工具）"
    if action == "calc":
        cmd = [sys.executable, script, "calc"]
        if milestone_id:
            cmd += ["--milestone", milestone_id]
    elif action == "status":
        cmd = [sys.executable, script, "status"]
    elif action == "add-milestone":
        cmd = [sys.executable, script, "add-milestone", "--id", milestone_id, "--name", milestone_name]
        if planned_end:
            cmd += ["--end", planned_end]
        if planned_value > 0:
            cmd += ["--value", str(planned_value)]
    else:
        return f"未知 action: {action}（可选 calc/status/add-milestone）"
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


@mcp.tool()
def progress_report(report_type: str = "weekly", project_name: str = "", phase: str = "") -> str:
    """进展报告生成（周报/阶段报）。包装 dev-project-mgmt CLI。

    Args:
        report_type: 报告类型（weekly=周报 / phase=阶段报告）
        project_name: 项目名称（可选，默认从目录名推导）
        phase: 阶段名称（report_type=phase 时可选）
    """
    args = ["report", report_type]
    if project_name:
        args += ["--name", project_name]
    if report_type == "phase" and phase:
        args += ["--phase", phase]
    return _run_mgmt_cli(args)


@mcp.tool()
def change_mgmt(action: str, title: str = "", desc: str = "", change_id: str = "",
                impact: str = "", priority: str = "", approver: str = "",
                dry_run: bool = True) -> str:
    """变更协调（登记/分析/审批/驳回）。包装 dev-project-mgmt CLI。

    Args:
        action: 操作类型（list/register/analyze/approve/reject）
        title: 变更标题（action=register 时必填）
        desc: 变更描述（action=register 时必填）
        change_id: 变更 ID（action=analyze/approve/reject 时必填）
        impact: 影响范围（action=register 时可选）
        priority: 优先级（action=register 时可选）
        approver: 审批人（action=approve/reject 时可选）
        dry_run: 是否仅探测不执行（默认 True）
    """
    args = ["change", action]
    if action == "list":
        pass
    elif action == "register":
        if dry_run:
            return f"(dry-run) 将登记变更: title={title}"
        args += ["--title", title, "--desc", desc]
        if impact:
            args += ["--impact", impact]
        if priority:
            args += ["--priority", priority]
    elif action in ("analyze", "approve", "reject"):
        if dry_run:
            return f"(dry-run) 将{action}变更: {change_id}"
        args += ["--id", change_id]
        if approver:
            args += ["--approver", approver]
    else:
        return f"未知 action: {action}（可选 list/register/analyze/approve/reject）"
    return _run_mgmt_cli(args)


@mcp.tool()
def program_status() -> str:
    """项目群整体视图（读 28/29/30 台账）。只读操作。"""
    ledger_dir = os.path.join(ROOT, "台账")
    if not os.path.isdir(ledger_dir):
        return "台账目录不存在"
    result = []
    # 28_项目群注册
    for fname, label in [
        ("28_program_registry.csv", "项目群注册"),
        ("29_dependency_matrix.csv", "依赖矩阵"),
        ("30_program_progress.csv", "项目群主进度"),
    ]:
        fpath = os.path.join(ledger_dir, fname)
        if os.path.isfile(fpath):
            try:
                with open(fpath, encoding="utf-8-sig") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                if len(rows) > 1:
                    result.append(f"【{label}】({len(rows)-1} 条)")
                    for row in rows[:3]:  # 仅显示前 3 行
                        result.append("  " + " | ".join(row[:6]))
                    if len(rows) > 3:
                        result.append(f"  ... 共 {len(rows)-1} 条")
                else:
                    result.append(f"【{label}】(空)")
            except Exception as e:
                result.append(f"【{label}】读取失败: {e}")
        else:
            result.append(f"【{label}】文件不存在")
    return "\n".join(result) if result else "无项目群数据"


@mcp.tool()
def program_dependency(source: str = "", target: str = "") -> str:
    """跨项目依赖查询（读 29_依赖矩阵）。只读操作。

    Args:
        source: 源项目名（可选，过滤条件）
        target: 目标项目名（可选，过滤条件）
    """
    fpath = os.path.join(ROOT, "台账", "29_dependency_matrix.csv")
    if not os.path.isfile(fpath):
        # 尝试中文文件名
        fpath = os.path.join(ROOT, "台账", "29_项目依赖矩阵.csv")
    if not os.path.isfile(fpath):
        return "依赖矩阵文件不存在"
    try:
        with open(fpath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        # 过滤
        if source:
            rows = [r for r in rows if source.lower() in r.get("源项目", "").lower()]
        if target:
            rows = [r for r in rows if target.lower() in r.get("目标项目", "").lower()]
        if not rows:
            return f"无匹配依赖记录（source={source}, target={target}）"
        result = [f"【依赖矩阵】({len(rows)} 条匹配)"]
        for r in rows[:10]:
            line = " | ".join(f"{k}={v}" for k, v in r.items() if v and k in
                              ("源项目", "目标项目", "依赖类型", "依赖强度", "状态", "传导风险"))
            result.append(f"  {line}")
        if len(rows) > 10:
            result.append(f"  ... 共 {len(rows)} 条")
        return "\n".join(result)
    except Exception as e:
        return f"读取失败: {e}"


# ---------- 新增 Tools（v21.15.0 PM 覆盖率提升） ----------

@mcp.tool()
def risk_scan(severity: str = "P1") -> str:
    """风险扫描：概率×影响分级扫描 RAID 台账高风险项。只读操作。

    委派本地权威工具 tools/raid_ops.py scan（risk-mgmt 技能单一信源，内化自
    dev-project-mgmt raid_manager + 原 MCP 内联 risk_scan 分级逻辑）。

    Args:
        severity: 过滤风险等级（P1=紧急/P2=高/P3=中/P4=低，默认仅 P1）
    """
    script = os.path.join(ROOT, "tools", "raid_ops.py")
    if not os.path.isfile(script):
        return "raid_ops.py 不存在，请检查 tools/ 目录（risk-mgmt 技能权威工具）"
    cmd = [sys.executable, script, "scan", "--severity", severity]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return (r.stdout + r.stderr)[:4000]


@mcp.tool()
def resource_conflict(resource: str = "") -> str:
    """资源冲突检测：扫描依赖矩阵中共享资源依赖 + 冲突预警。只读操作。

    Args:
        resource: 资源名称过滤（可选，模糊匹配）
    """
    fpath = os.path.join(ROOT, "台账", "29_dependency_matrix.csv")
    if not os.path.isfile(fpath):
        fpath = os.path.join(ROOT, "台账", "29_项目依赖矩阵.csv")
    if not os.path.isfile(fpath):
        return "依赖矩阵文件不存在"
    try:
        with open(fpath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return "依赖矩阵为空"
        # 提取共享资源（依赖对象列）
        resource_deps = {}  # resource -> list of rows
        for r in rows:
            dep_obj = r.get("依赖对象", r.get("dep_object", ""))
            intensity = r.get("依赖强度(硬/软)", r.get("依赖强度", ""))
            if not dep_obj:
                continue
            # 模糊匹配
            if resource and resource.lower() not in dep_obj.lower():
                continue
            key = dep_obj.strip()
            if key not in resource_deps:
                resource_deps[key] = []
            resource_deps[key].append(r)
        # 检测冲突：同一资源被 >=2 个源项目硬依赖
        conflicts = []
        for res, deps in resource_deps.items():
            sources = set()
            hard_count = 0
            for d in deps:
                src = d.get("源项目", d.get("source", ""))
                intensity = d.get("依赖强度(硬/软)", d.get("依赖强度", ""))
                if src:
                    sources.add(src)
                if "硬" in intensity:
                    hard_count += 1
            if len(sources) >= 2 or hard_count >= 2:
                conflicts.append({
                    "resource": res,
                    "sources": sources,
                    "dep_count": len(deps),
                    "hard_count": hard_count,
                })
        if not conflicts:
            filter_msg = f"（过滤: {resource}）" if resource else ""
            return f"无资源冲突{filter_msg}（共 {len(resource_deps)} 个资源依赖）"
        result = [f"【资源冲突】{len(conflicts)} 个冲突（共 {len(resource_deps)} 个资源）"]
        for c in conflicts[:10]:
            srcs = ", ".join(c["sources"])
            result.append(
                f"  ⚠ {c['resource']}  "
                f"源项目={srcs}  "
                f"依赖数={c['dep_count']}  "
                f"硬依赖={c['hard_count']}"
            )
        if len(conflicts) > 10:
            result.append(f"  ... 共 {len(conflicts)} 个冲突")
        result.append(f"\n缓解建议：错峰调度 / 增配资源 / 降级依赖（硬→软）")
        return "\n".join(result)
    except Exception as e:
        return f"资源冲突检测失败: {e}"


@mcp.tool()
def portfolio_summary() -> str:
    """组合治理摘要：全部项目群状态 + 收益兑现概览。只读操作。"""
    ledger_dir = os.path.join(ROOT, "台账")
    # 1. 读 28_项目群注册
    reg_path = os.path.join(ledger_dir, "28_program_registry.csv")
    if not os.path.isfile(reg_path):
        return "项目群注册文件不存在（28_program_registry.csv）"
    try:
        with open(reg_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            programs = list(reader)
        if not programs:
            return "项目群注册为空"
        result = [f"【组合治理摘要】{len(programs)} 个项目群"]
        for pg in programs:
            pg_id = pg.get("编号", "?")
            name = pg.get("名称", "?")
            status = pg.get("状态", "?")
            goal = pg.get("收益目标", pg.get("战略目标", ""))[:60]
            members = pg.get("成员项目清单", "")
            member_count = len([m for m in members.split(";") if m.strip()]) if members else 0
            tranche = pg.get("tranche划分", "")
            result.append(f"\n  [{pg_id}] {name}")
            result.append(f"    状态={status}  成员项目={member_count}个")
            result.append(f"    收益目标: {goal}")
            if tranche:
                result.append(f"    波次: {tranche[:60]}")
        # 2. 汇总 30_项目群主进度
        prog_path = os.path.join(ledger_dir, "30_program_progress.csv")
        if os.path.isfile(prog_path):
            with open(prog_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                progress_rows = list(reader)
            if progress_rows:
                # 统计 SPI
                spis = []
                for r in progress_rows:
                    spi_str = r.get("SPI", "")
                    try:
                        spis.append(float(spi_str))
                    except (ValueError, TypeError):
                        pass
                if spis:
                    avg_spi = sum(spis) / len(spis)
                    health = "✅ 健康" if avg_spi >= 1.0 else ("⚠️ 偏差" if avg_spi >= 0.8 else "❗ 严重滞后")
                    result.append(f"\n  【进度健康度】平均 SPI={avg_spi:.2f} {health}")
                    result.append(f"    里程碑总数: {len(progress_rows)}")
        return "\n".join(result)
    except Exception as e:
        return f"组合治理摘要读取失败: {e}"


# ---------- 新增 Prompts（v21.14.0 AI Agent PM 能力提升） ----------

@mcp.prompt()
def project_status_report(project_name: str = "", report_type: str = "weekly") -> str:
    """引导生成进展报告的提示词模板。

    Args:
        project_name: 项目名称（可选）
        report_type: 报告类型（weekly=周报 / phase=阶段报告）
    """
    return f"""你是项目经理。请为项目『{project_name or '当前项目'}』生成{report_type}。

执行步骤（对齐 role-project-mgmt 角色包）：
1. **数据采集**：
   - RAID 台账状态（调用 raid_mgmt list）
   - EVM 指标（调用 evm_analyze calc）
   - 变更状态（调用 change_mgmt list）
   - 进度跟踪（调用 program_status）
2. **报告生成**：
   - 调用 progress_report 生成{report_type}模板
   - 聚合 RAID/EVM/进度/变更数据
3. **报告内容**：
   - 本期完成事项
   - 进度/成本偏差分析（SPI/CPI）
   - 风险/问题状态
   - 下期计划
   - 需决策项

输出规范（CSV UTF-8 with BOM）：
- 评审报告_<项目>_<期>_进展.csv
- 仅回显首 5 行 + 行数

铁律：进展报告须聚合 RAID+EVM+进度数据；偏差超阈值须触发预警。"""


@mcp.prompt()
def risk_assessment(project_name: str = "") -> str:
    """引导 RAID 分析与风险预警的提示词模板。

    Args:
        project_name: 项目名称（可选）
    """
    return f"""你是风险管理师。请为项目『{project_name or '当前项目'}』执行 RAID 分析。

执行步骤（对齐 role-project-mgmt §3 + role-governance risk_scan）：
1. **RAID 台账查询**：
   - 调用 raid_mgmt(action="list") 获取全部条目
   - 按类型分类：风险/假设/问题/依赖
2. **风险评估**：
   - 概率 × 影响 = 风险等级（P1~P4）
   - P1 风险须立即升级
   - 临近到期项须预警
3. **应对策略**：
   - 风险：规避/转移/缓解/接受
   - 问题：根因分析 + 纠正措施
   - 依赖：缓解措施 + 替代方案
4. **输出报告**：
   - RAID 状态汇总（按类型/状态/优先级）
   - P1/P2 风险清单 + 应对策略
   - 升级建议

输出规范（CSV UTF-8 with BOM）：
- 12_风险问题台账.csv 更新
- 风险预警报告

铁律：P1 风险须立即升级；连续 2 次延期/超支停止 AI 自动调整，推送人工决策。"""


@mcp.prompt()
def program_review(tranche: str = "") -> str:
    """引导 Program Board 评审的提示词模板。

    Args:
        tranche: 当前波次（可选）
    """
    return f"""你是 Program Board 评审引导师。请执行项目群评审{f'（波次：{tranche}）' if tranche else ''}。

执行步骤（对齐 role-program-mgmt §8 Program Board 评审）：
1. **数据采集**：
   - 调用 program_status() 获取项目群整体视图
   - 调用 program_dependency() 获取依赖矩阵
   - 各项目 EVM 指标汇总
2. **四 Gate 评审**：
   - Gate 1：时间对齐（各项目里程碑是否对齐）
   - Gate 2：依赖无冲突（依赖矩阵是否有未决冲突）
   - Gate 3：标准一致（度量口径是否统一）
   - Gate 4：环境就绪（CMDB 关键资产状态）
3. **决策建议**：
   - 继续（proceed）：四 Gate 全通过
   - 转向（re-plan）：部分 Gate 未通过但可修复
   - 终止（close）：业务论证不再成立
4. **决策留痕**：
   - 评审纪要 + 决策记录
   - 禁止无记录口头决策

输出规范：
- 评审报告 CSV（四 Gate 通过状态 + 决策结论）
- 行动项（owner/deadline）

铁律：Program Board 决策必须人工确认；PM 提供机制不决策。"""


if __name__ == "__main__":
    # 默认 stdio；如需团队共享单端点，可改 mcp.run(transport="streamable-http")
    mcp.run()
