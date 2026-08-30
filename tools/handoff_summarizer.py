#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交接文档 L1 核心摘要生成器（v1.1.0）
- 输入：完整交接文档 + 当前阶段/角色/任务上下文
- 输出：L1 核心摘要（结构化 Markdown，含实体索引）
- 模型：默认 qwen2.5-coder:7b (Ollama 本地)，fallback 纯规则摘要
- 触发：solidify.sh §2 刷新断点区前自动运行
- 保护：L1 摘要受 token_standard §7 交接必读预算保护（永不压缩、首部固定）

v1.1.0（2026-08-29）修复摘要递归膨胀缺陷：
  ① extract_l1_zone 限定扫描范围为 L1 区（原全文扫描收集所有重复 L2 占位行导致 13756 字符膨胀）；
  ② 提取改按「### 子节切分」结构化取值，不再依赖脆弱正则匹配标题；
  ③ dedupe_lines 去重 + 各节限条数 + 3000 字符硬截断；
  ④ write_l1_to_handoff 前调 sanitize_duplicate_l2_blocks 清理历史累积的重复 L2 占位块；
  ⑤ 幂等保证：连续运行 MD5 一致不复发。
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).parent.parent)))
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


def extract_l1_zone(full_doc: str) -> str:
    """提取 L1 必读核心区域文本（锁定 🔴 L1 标记 ~ 首个 🟡 L2 标记之间）

    修复（2026-08-29）：原实现扫描全文收集关键行，当交接文档存在历史重复 L2 块时，
    会把所有重复「无阻塞项/下一步动作」收进摘要导致递归膨胀（13756 字符）。
    现强制限定扫描范围仅为 L1 区，杜绝污染源。
    """
    l1_start_marker = "## 🔴 L1 必读核心"
    l1_end_marker = "## 🟡 L2 标准上下文"
    start_idx = full_doc.find(l1_start_marker)
    end_idx = full_doc.find(l1_end_marker)
    if start_idx == -1 or end_idx == -1:
        # 找不到标准标记，退化为全文前 500 行（上限保护）
        return "\n".join(full_doc.split("\n")[:500])
    return full_doc[start_idx:end_idx]


def dedupe_lines(lines: list, limit: int = 5) -> list:
    """按原始顺序去重，最多保留 limit 条"""
    seen = set()
    out = []
    for ln in lines:
        key = ln.strip()
        if key not in seen:
            seen.add(key)
            out.append(ln)
        if len(out) >= limit:
            break
    return out


def extract_l1_by_rules(full_doc: str, state: dict) -> str:
    """纯规则摘要（fallback：无模型/模型失败时）——结构化输出 L1 必读核心"""
    l1_sections = {}
    # 限定扫描范围：仅 L1 区（修复全文扫描导致的递归膨胀）
    zone = extract_l1_zone(full_doc)

    # —— 按 ### 子节切分 L1 区（健壮：不依赖脆弱正则，各子节独立取值） ——
    def split_subsections(doc_zone: str) -> dict:
        """以 '### 标题' 切分 L1 区 → {标题: [内容行]}"""
        subs = {}
        cur_title = None
        for line in doc_zone.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("### "):
                cur_title = stripped[4:].strip()
                subs.setdefault(cur_title, [])
            elif stripped.startswith("#### "):
                # 四级子标题作为内容行保留
                if cur_title:
                    subs[cur_title].append("- **" + stripped[5:].strip() + "**")
            elif cur_title and not stripped.startswith("## "):
                subs[cur_title].append(stripped)
        return subs

    subs = split_subsections(zone)

    def sub(name: str, *aliases: str) -> list:
        for key in (name,) + aliases:
            if key in subs:
                return subs[key]
        return []

    # 1. 项目速览
    overview = sub("项目速览")
    if overview:
        l1_sections["项目速览"] = dedupe_lines(overview, 6)

    # 2. 当前阶段/角色/任务边界（兼容旧文档以散行存在的场景）
    stage_info = sub("当前阶段/角色/任务", "当前角色", "当前任务", "当前任务类型")
    if not stage_info:
        # 旧格式：散行「当前阶段：xx」在 L1 区任意位置
        for line in zone.split("\n"):
            stripped = line.strip()
            if re.search(r"(当前阶段|当前角色|当前任务|当前任务类型)\s*[：:]", stripped):
                stage_info.append(stripped)
    if stage_info:
        l1_sections["当前阶段/角色/任务"] = dedupe_lines(stage_info, 6)

    # 3. 关键风险/阻塞
    risk_lines = sub("关键风险/阻塞", "风险/阻塞")
    if risk_lines:
        risk_lines = [ln for ln in risk_lines if not ln.startswith("### ") and len(ln) > 4]
    if not risk_lines:
        risk_lines = ["- **无阻塞项**"]
    l1_sections["关键风险/阻塞"] = dedupe_lines(risk_lines, 3)

    # 4. 下一步唯一动作
    action_lines = sub("下一步唯一动作", "下一步动作")
    if action_lines:
        action_lines = [ln for ln in action_lines if len(ln) > 3]
    l1_sections["下一步唯一动作"] = dedupe_lines(action_lines, 3) if action_lines else ["- 待定"]

    # 5. 铁律锚点
    iron_lines = sub("铁律锚点")
    iron_lines = [ln for ln in iron_lines if not ln.startswith("### ")]
    if not iron_lines:
        iron_lines = ["- **核心**：授权 → 备份 → 留痕"]
    l1_sections["铁律锚点"] = dedupe_lines(iron_lines, 6)

    # 6. 关键文件索引（精简版）
    file_lines = sub("关键文件索引")
    file_lines = [ln for ln in file_lines if ln.startswith("|") and "`" in ln][:5]
    if not file_lines:
        file_lines = ["- 见 L2 完整索引"]
    l1_sections["关键文件索引"] = file_lines

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

    result = "\n".join(out).strip() if out else "# L1 核心摘要（规则提取）\n\n> 无法提取关键信息，请检查交接文档格式"

    # 硬截断：超过 3000 字符裁剪（token_standard §7 交接必读预算 2000 token 防护）
    if len(result) > 3000:
        result = result[:3000].rsplit("\n", 1)[0] + "\n- **（摘要超限，已裁剪）**"
    return result


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


def sanitize_duplicate_l2_blocks(full_doc: str) -> str:
    """合并历史累积的重复 L2 标准上下文块（一次性污染修复）

    修复（2026-08-29）：HEAD 交接文档曾堆积 16 个内容完全相同的 `## 🟡 L2 标准上下文`
    占位块（均为 '无阻塞项/下一步唯一动作/铁律锚点/见 L2 完整索引' 模板），仅最后一个块
    含真实工作断点。此处扫描全部分界，仅保留「含真实内容」的那个 L2 块，其余删除，
    并从源头杜绝 extract_l1_zone 的扫描污染（L1 区之后即为唯一 L2）。
    """
    l1_marker = "## 🔴 L1 必读核心"
    l2_marker = "## 🟡 L2 标准上下文"
    l3_marker = "## 🟢 L3 完整归档"

    # 依次定位各分界（首次出现即按文档顺序）
    l1_idx = full_doc.find(l1_marker)
    if l1_idx == -1:
        return full_doc

    # 收集所有 L2 标记位置
    positions = []
    search_from = l1_idx
    while True:
        pos = full_doc.find(l2_marker, search_from)
        if pos == -1:
            break
        positions.append(pos)
        search_from = pos + len(l2_marker)

    if len(positions) <= 1:
        return full_doc  # 无重复，无需清理

    # L3 位置（用于给最后一段圈边界）
    l3_idx = full_doc.find(l3_marker, positions[-1])
    tail_bound = l3_idx if l3_idx != -1 else len(full_doc)

    # 判断每段是否含真实内容：段内若有「详细工作断点/进行中工作/待办事项/完整关键文件索引/台账指针」即为真实块
    real_sections = ["详细工作断点", "进行中工作", "待办事项", "完整关键文件索引", "台账指针", "约定与铁律（完整版）"]

    def classify(start_pos, end_pos):
        seg = full_doc[start_pos:end_pos]
        hits = [kw for kw in real_sections if kw in seg]
        # 模板占位块特征：含 "见 L2 完整索引" 且无真实 section 关键词
        if hits:
            return ("real", hits)
        if "见 L2 完整索引" in seg and not any(kw in seg for kw in ["### 1. 详细工作断点"]):
            return ("placeholder", hits)
        return ("real", hits)   # 保守：无法判断时视为真实保留

    # 逐段圈定 [positions[i], positions[i+1])
    segs = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else tail_bound
        kind, hits = classify(pos, end)
        segs.append((pos, end, kind, hits))

    # 保留策略：所有 real 段保留；占位段全部删除；若占位段是最后一个且不含真实内容则同样删除
    placeholders = [s for s in segs if s[2] == "placeholder"]
    to_delete = [s for s in placeholders]
    if not to_delete:
        return full_doc

    # 重建：保留首部至第一个 L2 之前，然后拼接第一个 real 段 + 占位段之间的 real 段 + 尾部
    first_l2 = positions[0]
    head = full_doc[:first_l2]
    kept_segs = [s for s in segs if s[2] == "real"]
    # 保持原有顺序：kept_segs 已按位置排序
    middle = "".join(full_doc[s[0]:s[1]] for s in kept_segs)
    tail = full_doc[tail_bound:]
    rebuilt = head + middle + tail
    removed = len(to_delete)
    print(f"[info] sanitize_duplicate_l2_blocks：清理 {removed} 个重复 L2 占位块，保留 {len(kept_segs)} 个真实块")
    return rebuilt


def write_l1_to_handoff(l1_summary: str):
    """将 L1 摘要写入交接文档头部（替换现有 L1 区域，先清理重复 L2 块）"""
    full_doc = read_handoff_doc()

    # 先清理历史累积的重复 L2 占位块（污染源）
    full_doc = sanitize_duplicate_l2_blocks(full_doc)

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