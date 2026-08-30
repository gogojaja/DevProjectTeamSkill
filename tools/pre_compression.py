#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预压缩优化管道（零额外 LLM 调用）
- 工具输出剪枝 → 敏感数据脱敏 → 语义去重(Embedding复用) → 边界对齐保护
- 接入点：工具调用返回时、对话轮次结束时、压缩前
- 零额外 LLM 调用：剪枝/脱敏/去重均为本地规则/Embedding 计算
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).parent.parent)))
DESENSITIZE_SCRIPT = ROOT / "tools" / "desensitize" / "desensitize.py"
DESENSITIZE_DICT = ROOT / "tools" / "desensitize" / "desensitize_dictionary.csv"
OLLAMA_MODEL = "qwen2.5-coder:7b"  # 复用本地模型做 mean-pooling embedding

# 全局 Embedding 缓存（进程内，用后即丢）
_EMBEDDING_CACHE: Dict[str, List[float]] = {}


# =============================================================================
# 1. 工具输出剪枝
# =============================================================================

def trim_tool_output(output: str, max_lines: int = 50, keep_errors: bool = True) -> str:
    """
    剪枝工具输出：仅保留关键行/错误/结果摘要
    - 保留前 N 行（默认 10）+ 含错误/异常的行 + 最后 N 行（默认 10）
    - 丢弃冗长日志/进度条/重复行
    """
    if not output:
        return output
    
    lines = output.split("\n")
    if len(lines) <= max_lines:
        return output
    
    head_n = 10
    tail_n = 10
    error_pattern = re.compile(r"(error|exception|fail|traceback|critical|fatal|\[err\])", re.IGNORECASE)
    
    kept = []
    kept_set = set()
    
    # 头部
    for i, line in enumerate(lines[:head_n]):
        kept.append(f"[HEAD:{i}] {line}")
        kept_set.add(i)
    
    # 错误行
    if keep_errors:
        for i, line in enumerate(lines):
            if i in kept_set:
                continue
            if error_pattern.search(line):
                kept.append(f"[ERROR:{i}] {line}")
                kept_set.add(i)
    
    # 尾部
    for i in range(max(0, len(lines) - tail_n), len(lines)):
        if i not in kept_set:
            kept.append(f"[TAIL:{i}] {line}")
            kept_set.add(i)
    
    # 中间省略提示
    omitted = len(lines) - len(kept_set)
    if omitted > 0:
        kept.insert(head_n, f"... [省略 {omitted} 行中间内容] ...")
    
    return "\n".join(kept)


def trim_tool_output_smart(output: str, max_chars: int = 5000) -> str:
    """智能剪枝：按字符预算分配，优先保留结构化结果/错误"""
    if not output or len(output) <= max_chars:
        return output
    
    # 尝试按段落分割，保留关键段落
    paragraphs = re.split(r"\n\s*\n", output)
    if len(paragraphs) == 1:
        # 单大段，硬切
        return output[:max_chars] + "\n... [输出过长，已截断] ..."
    
    # 优先级：含错误 > 含结果关键词 > 短段落 > 长段落
    scored = []
    for i, p in enumerate(paragraphs):
        score = 0
        if re.search(r"(error|exception|fail|traceback)", p, re.IGNORECASE):
            score += 100
        if re.search(r"(result|output|success|完成|成功|结果)", p, re.IGNORECASE):
            score += 50
        if len(p) < 200:
            score += 10
        elif len(p) > 2000:
            score -= 20
        scored.append((score, i, p))
    
    scored.sort(reverse=True)
    
    kept = []
    total = 0
    for score, idx, p in scored:
        if total + len(p) + 2 <= max_chars:
            kept.append((idx, p))
            total += len(p) + 2
        else:
            break
    
    kept.sort(key=lambda x: x[0])  # 恢复原序
    result = "\n\n".join(p for _, p in kept)
    if total < len(output):
        result += f"\n\n... [省略 {len(paragraphs) - len(kept)} 段，原长 {len(output)} 字符] ..."
    return result


# =============================================================================
# 2. 敏感数据脱敏（前置）
# =============================================================================

def desensitize_text(text: str, dict_path: Optional[Path] = None) -> str:
    """
    调用 desensitize.py 对文本脱敏（A/B/C 级全覆盖）
    - 仅脱敏后文本进入 embedding
    - 向量仅内存计算、不落盘、用后即丢
    """
    if not text:
        return text
    
    dict_path = dict_path or DESENSITIZE_DICT
    if not dict_path.exists():
        return text  # 字典不存在则跳过
    
    try:
        import tempfile
        # 创建临时目录作为输出目录
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = os.path.join(tmpdir, "input.txt")
            out_dir = os.path.join(tmpdir, "out")
            os.makedirs(out_dir, exist_ok=True)
            
            # 写入输入文件
            with open(in_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            cmd = [
                sys.executable, str(DESENSITIZE_SCRIPT),
                in_path, "-o", out_dir,
                "--dictionary", str(dict_path),
                "--level", "C"  # A+B+C 全级别
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # 输出文件直接在 out_dir 下，同名
                out_file = os.path.join(out_dir, "input.txt")
                if os.path.exists(out_file):
                    with open(out_file, encoding="utf-8") as f:
                        return f.read()
                # 备选：查找任何文件
                for root, dirs, files in os.walk(out_dir):
                    for f in files:
                        out_file = os.path.join(root, f)
                        with open(out_file, encoding="utf-8") as f:
                            return f.read()
            else:
                print(f"[warn] desensitize failed: {result.stderr}", file=sys.stderr)
                return text
                
    except Exception as e:
        print(f"[warn] desensitize exception: {e}", file=sys.stderr)
        return text
    
    return text


# =============================================================================
# 3. 语义去重（复用 qwen2.5-coder:7b mean-pooling Embedding）
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """获取文本的 Embedding 向量（mean-pooling qwen2.5-coder:7b 最后一层隐藏状态）"""
    global _EMBEDDING_CACHE
    
    # 缓存键：文本哈希
    cache_key = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    if cache_key in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[cache_key]
    
    # 截断过长文本（模型上下文限制）
    max_chars = 8000
    if len(text) > max_chars:
        text = text[:max_chars]
    
    try:
        # 通过 Ollama 获取隐藏状态（需 Ollama 支持 embeddings API）
        # 这里使用 ollama embeddings API（Ollama 0.1.47+ 支持）
        import json
        result = subprocess.run(
            ["ollama", "embeddings", "--model", OLLAMA_MODEL, "--prompt", text],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            embedding = data.get("embedding", [])
            if embedding:
                _EMBEDDING_CACHE[cache_key] = embedding
                return embedding
        
        # Fallback：使用简单的 TF-IDF 风格哈希向量（无模型依赖）
        print(f"[warn] ollama embeddings failed, using fallback hash vector", file=sys.stderr)
        
    except Exception as e:
        print(f"[warn] embedding failed: {e}", file=sys.stderr)
    
    # Fallback：基于词频的简单向量（3584 维稀疏向量模拟）
    words = re.findall(r"\w+", text.lower())
    vec = [0.0] * 3584
    for w in words:
        h = hash(w) % 3584
        vec[h] += 1.0
    # 归一化
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    _EMBEDDING_CACHE[cache_key] = vec
    return vec


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """余弦相似度"""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_deduplicate(messages: List[Dict], threshold: float = 0.85) -> List[Dict]:
    """
    语义去重：计算消息 Embedding 相似度，仅保留最信息密集版本
    - messages: [{"role": "...", "content": "..."}, ...]
    - threshold: 相似度阈值（默认 0.85），超过即视为重复
    - 返回去重后的消息列表（保留首次出现的最密集版本）
    """
    if len(messages) <= 1:
        return messages
    
    # 计算每条消息的 Embedding
    embeddings = []
    for msg in messages:
        content = msg.get("content", "")
        if not content:
            embeddings.append(None)
        else:
            emb = get_embedding(content)
            embeddings.append(emb)
    
    # 去重：保留第一个，后续与前面所有比较
    kept = []
    kept_embeddings = []
    
    for i, (msg, emb) in enumerate(zip(messages, embeddings)):
        if emb is None:
            kept.append(msg)
            kept_embeddings.append(emb)
            continue
        
        is_duplicate = False
        for j, kept_emb in enumerate(kept_embeddings):
            if kept_emb is None:
                continue
            sim = cosine_similarity(emb, kept_emb)
            if sim >= threshold:
                # 重复：判断哪个更信息密集（内容更长/更结构化者保留）
                if len(msg.get("content", "")) > len(kept[j].get("content", "")):
                    # 当前更密集，替换
                    kept[j] = msg
                    kept_embeddings[j] = emb
                is_duplicate = True
                break
        
        if not is_duplicate:
            kept.append(msg)
            kept_embeddings.append(emb)
    
    omitted = len(messages) - len(kept)
    if omitted > 0:
        # 在适当位置插入省略提示
        kept.append({
            "role": "system",
            "content": f"[预压缩：语义去重省略 {omitted} 条重复消息，阈值={threshold}]"
        })
    
    return kept


# =============================================================================
# 4. 边界对齐保护
# =============================================================================

def align_boundary_backward(messages: List[Dict]) -> List[Dict]:
    """
    边界对齐：识别 tool_call/tool_result 组，保持组完整不拆分
    参考 Hermes `_align_boundary_backward` 逻辑
    """
    if not messages:
        return messages
    
    result = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg.get("role", "")
        
        if role == "assistant" and "tool_calls" in msg and msg["tool_calls"]:
            # 发现 tool_call 组开始
            group = [msg]
            i += 1
            # 收集后续所有 tool_result
            while i < len(messages) and messages[i].get("role") == "tool":
                group.append(messages[i])
                i += 1
            # 整组作为一个单元保留
            result.extend(group)
        else:
            result.append(msg)
            i += 1
    
    return result


def protect_tool_groups(messages: List[Dict], max_keep: int) -> List[Dict]:
    """
    在截断消息列表时保护 tool_call/tool_result 组完整性
    - 从后向前保留，遇到 tool_result 则必须保留其配对的 tool_call
    """
    if len(messages) <= max_keep:
        return messages
    
    # 从后向前扫描，标记必须保留的索引
    must_keep = set()
    i = len(messages) - 1
    kept_count = 0
    
    while i >= 0 and kept_count < max_keep:
        msg = messages[i]
        role = msg.get("role", "")
        
        if role == "tool":
            # tool_result：必须保留，且找到对应的 tool_call
            must_keep.add(i)
            kept_count += 1
            # 向前找 tool_call
            j = i - 1
            while j >= 0:
                if messages[j].get("role") == "assistant" and "tool_calls" in messages[j]:
                    must_keep.add(j)
                    kept_count += 1
                    break
                j -= 1
        else:
            must_keep.add(i)
            kept_count += 1
        i -= 1
    
    # 按原序输出
    return [msg for idx, msg in enumerate(messages) if idx in must_keep]


# =============================================================================
# 5. 统一入口
# =============================================================================

class PreCompressionPipeline:
    """预压缩管道统一入口"""
    
    def __init__(
        self,
        trim_output: bool = True,
        desensitize: bool = True,
        semantic_dedup: bool = True,
        align_boundary: bool = True,
        dedup_threshold: float = 0.85,
        max_output_chars: int = 5000
    ):
        self.trim_output = trim_output
        self.desensitize = desensitize
        self.semantic_dedup = semantic_dedup
        self.align_boundary = align_boundary
        self.dedup_threshold = dedup_threshold
        self.max_output_chars = max_output_chars
    
    def process_tool_output(self, output: str) -> str:
        """处理单次工具输出（剪枝）"""
        if self.trim_output:
            output = trim_tool_output_smart(output, self.max_output_chars)
        return output
    
    def process_messages(
        self,
        messages: List[Dict],
        dedup: bool = None,
        align: bool = None
    ) -> List[Dict]:
        """处理消息列表（对话轮次结束/压缩前）"""
        # 1. 边界对齐（保护 tool 组）
        if align or self.align_boundary:
            messages = align_boundary_backward(messages)
        
        # 2. 语义去重
        if (dedup if dedup is not None else self.semantic_dedup):
            # 先脱敏
            if self.desensitize:
                for msg in messages:
                    if msg.get("content"):
                        msg["content"] = desensitize_text(msg["content"])
            messages = semantic_deduplicate(messages, self.dedup_threshold)
        
        # 2.5 再次边界对齐（去重可能破坏组，重新对齐）
        if align or self.align_boundary:
            messages = align_boundary_backward(messages)
        
        return messages
    
    def clear_cache(self):
        """清理 Embedding 缓存（用后即丢）"""
        global _EMBEDDING_CACHE
        _EMBEDDING_CACHE.clear()


# =============================================================================
# CLI 入口（用于测试/调试）
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="预压缩管道 CLI")
    parser.add_argument("--trim", help="剪枝文本文件", type=Path)
    parser.add_argument("--desensitize", help="脱敏文本文件", type=Path)
    parser.add_argument("--dedup", help="语义去重 JSON 消息文件", type=Path)
    parser.add_argument("--threshold", type=float, default=0.85, help="去重相似度阈值")
    parser.add_argument("--output", "-o", type=Path, help="输出文件")
    args = parser.parse_args()
    
    pipeline = PreCompressionPipeline()
    
    if args.trim:
        text = args.trim.read_text(encoding="utf-8")
        result = pipeline.process_tool_output(text)
        out = result
    elif args.desensitize:
        text = args.desensitize.read_text(encoding="utf-8")
        out = desensitize_text(text)
    elif args.dedup:
        msgs = json.loads(args.dedup.read_text(encoding="utf-8"))
        pipeline = PreCompressionPipeline(dedup_threshold=args.threshold)
        out = json.dumps(pipeline.process_messages(msgs), ensure_ascii=False, indent=2)
    else:
        parser.print_help()
        return
    
    if args.output:
        args.output.write_text(out, encoding="utf-8")
        print(f"[ok] 写入 {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()