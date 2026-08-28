#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交接文档 L1 核心摘要生成器
- 输入：完整交接文档 + 当前阶段/角色/任务上下文
- 输出：L1 核心摘要（结构化 Markdown，含实体索引）
- 模型：默认 qwen2.5-coder:7b (Ollama 本地)，fallback 纯规则摘要
- 触发：solidify.sh §2 刷新断点区前自动运行
- 保护：L1 摘要受 token_standard §7 交接必读预算保护（永不压缩、首部固定）
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
HANDOFF_DOC = ROOT / "交接文档.md"
SOLIDIFY_STATE = ROOT / ".solidify_state.json"  # 固化时的临时上下文


def read_handoff_doc() -> str:
    """读取完整交接文档"""
    if HANDOFF_DOC.exists():
        return HANDOFF_DOC.read_text(encoding="utf-8")
    return ""


def load_solidify_state() -> dict:
    """读取固化时的临时上下文（阶段/角色/任务/变更摘要）"""
    if SOLIDIFY_STATE.exists():
        try:
            return json.loads(SOLIDIFY_STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def extract_l1_by_rules(full_doc: str, state: dict) -> str:
    """纯规则摘要（fallback：无模型/模型失败时）——结构化输出 L1 必读核心"""
    l1_sections = {}
    
    # 辅助：按标题层级提取内容
    def find_section(doc: str, header_pattern: str, stop_at_headers: list) -> list:
        """提取某标题下的内容，直到遇到停止标题（不含标题行本身）"""
        lines = doc.split("\n")
        in_section = False
        collected = []
        for line in lines:
            # 检查是否进入目标区域（标题行本身不收集）
            if re.search(header_pattern, line):
                in_section = True
                continue
            # 检查是否遇到停止标题
            if in_section and any(re.search(stop, line) for stop in stop_at_headers):
                break
            if in_section:
                stripped = line.strip()
                if stripped:  # 跳过空行
                    collected.append(stripped)
        return collected
    
    # 1. 项目速览（匹配 🔴 L1 或 ## 0. 或 ### 0.）
    overview = find_section(full_doc, r"(?:##\s*0\.|###\s*0\.|🔴\s*L1)", [r"^##\s*\d", r"^###\s*\d", r"^---"])
    if overview:
        l1_sections["项目速览"] = overview
    
    # 2. 当前阶段/角色/任务边界
    stage_info = []
    for line in full_doc.split("\n"):
        stripped = line.strip()
        if re.search(r"(当前阶段|当前角色|当前任务)\s*[：:]", stripped):
            stage_info.append(stripped)
    if stage_info:
        l1_sections["当前阶段/角色/任务"] = stage_info
    
    # 3. 关键风险/阻塞（排除标题行本身）
    risk_lines = []
    for line in full_doc.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):  # 跳过标题行
            continue
        if any(kw in stripped for kw in ["关键风险", "关键阻塞", "风险/阻塞", "阻塞项", "阻塞：", "无阻塞", "无风险"]):
            if len(stripped) > 4:
                risk_lines.append(stripped)
    if not risk_lines:
        risk_lines = ["- **无阻塞项**"]
    l1_sections["关键风险/阻塞"] = risk_lines
    
    # 4. 下一步唯一动作
    action_lines = []
    for line in full_doc.split("\n"):
        stripped = line.strip()
        if re.search(r"下一步.*(?:唯一动作|动作|动作：)", stripped) or stripped.startswith("下一步"):
            if len(stripped) > 3:
                action_lines.append(stripped)
    l1_sections["下一步唯一动作"] = action_lines if action_lines else ["- 待定"]
    
    # 5. 铁律锚点
    iron_lines = []
    for line in full_doc.split("\n"):
        stripped = line.strip()
        if ("授权" in stripped and "备份" in stripped and "留痕" in stripped) or \
           ("#15" in stripped and ("执行合同" in stripped or "闸门" in stripped)) or \
           ("#11" in stripped and ("顺带" in stripped or "禁令" in stripped)):
            iron_lines.append(stripped)
    # 去重
    seen = set()
    dedup = []
    for l in iron_lines:
        if l not in seen:
            dedup.append(l)
            seen.add(l)
    l1_sections["铁律锚点"] = dedup if dedup else ["- **核心**：授权 → 备份 → 留痕"]
    
    # 6. 关键文件索引（精简版）
    file_lines = []
    in_index = False
    for line in full_doc.split("\n"):
        if "关键文件索引" in line or "文件索引" in line:
            in_index = True
            continue
        if in_index and line.strip().startswith("##"):
            break
        if in_index and line.strip().startswith("|") and "`" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                file_lines.append(f"- `{parts[0]}`：{parts[1]}")
    l1_sections["关键文件索引"] = file_lines[:5] if file_lines else ["- 见 L2 完整索引"]
    
    # 7. 固化上下文补充
    if state:
        extra = []
        if state.get("current_stage"):
            l1_sections.setdefault("当前阶段/角色/任务", []).append(f"- **当前阶段**：{state['current_stage']}")
        if state.get("current_role"):
            l1_sections.setdefault("当前阶段/角色/任务", []).append(f"- **当前角色**：{state['current_role']}")
        if state.get("current_task"):
            l1_sections.setdefault("当前阶段/角色/任务", []).append(f"- **当前任务**：{state['current_task']}")
        if state.get("changes_summary"):
            extra.append(f"- **本轮变更**：{state['changes_summary'][:200]}")
        if extra:
            l1_sections["固化上下文补充"] = extra
    
    # 组装输出（按固定顺序）
    order = [
        "项目速览",
        "当前阶段/角色/任务",
        "关键风险/阻塞",
        "下一步唯一动作",
        "铁律锚点",
        "关键文件索引",
        "固化上下文补充"
    ]
    
    out = []
    for sec in order:
        if sec in l1_sections and l1_sections[sec]:
            out.append(f"### {sec}")
            for line in l1_sections[sec]:
                if not line.startswith("-") and not line.startswith("#"):
                    out.append(f"- {line}")
                else:
                    out.append(line)
            out.append("")  # 空行分隔
    
    return "\n".join(out).strip() if out else "# L1 核心摘要（规则提取）\n\n> 无法提取关键信息，请检查交接文档格式"


def generate_with_ollama(prompt: str, model: str = "qwen2.5-coder:7b", timeout: int = 30) -> str:
    """调用本地 Ollama 生成摘要"""
    try:
        # 使用 ollama CLI（需确保 ollama serve 运行中）
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT)
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"[warn] ollama run failed: {result.stderr}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print(f"[warn] ollama timeout ({timeout}s)", file=sys.stderr)
    except FileNotFoundError:
        print("[warn] ollama CLI not found", file=sys.stderr)
    except Exception as e:
        print(f"[warn] ollama error: {e}", file=sys.stderr)
    return ""


def build_prompt(full_doc: str, state: dict) -> str:
    """构建给模型的提示词"""
    stage = state.get("current_stage", "未知")
    role = state.get("current_role", "未知")
    task = state.get("current_task", "未知")
    changes = state.get("changes_summary", "无")
    
    return f"""请从以下完整交接文档中提取 L1 核心摘要（约 800 token），用于小模型/受限上下文必读。

**当前上下文**：
- 阶段：{stage}
- 角色：{role}
- 任务：{task}
- 本轮变更：{changes}

**提取要求**（仅输出 Markdown，不含解释）：
1. 项目速览（1 行）
2. 当前阶段/角色/任务边界
3. 关键风险/阻塞（无则写"无"）
4. 下一步唯一动作
5. 铁律锚点（授权/备份/留痕 + #15执行合同闸门 + #11顺带操作禁令）
6. 关键文件索引（精简版，≤5 项）

**完整交接文档**：
---
{full_doc[:15000]}
---
"""


def write_l1_to_handoff(l1_summary: str):
    """将 L1 摘要写入交接文档头部（替换现有 L1 区域）"""
    full_doc = read_handoff_doc()
    
    # 找到 L1 区域边界
    l1_start_marker = "## 🔴 L1 必读核心"
    l1_end_marker = "## 🟡 L2 标准上下文"
    
    start_idx = full_doc.find(l1_start_marker)
    end_idx = full_doc.find(l1_end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("[warn] L1/L2 分界标记未找到，跳过写入", file=sys.stderr)
        return False
    
    # 保留 L1 标记行，替换内容
    new_l1 = f"{l1_start_marker}（所有模型必读，~800 token）\n\n{l1_summary}\n\n"
    new_doc = full_doc[:start_idx] + new_l1 + full_doc[end_idx:]
    
    HANDOFF_DOC.write_text(new_doc, encoding="utf-8")
    print(f"[ok] L1 核心摘要已写入交接文档（{len(l1_summary)} 字符）")
    return True


def main():
    parser = argparse.ArgumentParser(description="交接文档 L1 核心摘要生成器")
    parser.add_argument("--model", default="qwen2.5-coder:7b", help="Ollama 模型名")
    parser.add_argument("--timeout", type=int, default=30, help="模型调用超时(秒)")
    parser.add_argument("--fallback-only", action="store_true", help="仅使用规则摘要，不调用模型")
    parser.add_argument("--dry-run", action="store_true", help="仅打印摘要，不写入文档")
    args = parser.parse_args()
    
    print("[info] 读取交接文档...")
    full_doc = read_handoff_doc()
    if not full_doc:
        print("[error] 交接文档为空或不存在", file=sys.stderr)
        sys.exit(1)
    
    state = load_solidify_state()
    print(f"[info] 固化上下文：{state}")
    
    # 优先尝试模型生成
    l1_summary = ""
    if not args.fallback_only:
        prompt = build_prompt(full_doc, state)
        print(f"[info] 调用 Ollama ({args.model})...")
        l1_summary = generate_with_ollama(prompt, args.model, args.timeout)
    
    # Fallback 规则摘要
    if not l1_summary:
        print("[info] 使用规则摘要...")
        l1_summary = extract_l1_by_rules(full_doc, state)
    
    print(f"[info] 生成摘要长度：{len(l1_summary)} 字符")
    
    if args.dry_run:
        print("\n=== L1 核心摘要（干跑） ===")
        print(l1_summary)
        return
    
    # 写入交接文档
    if write_l1_to_handoff(l1_summary):
        print("[ok] 完成")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()