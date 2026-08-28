# P2 预压缩管道集成指南

> 版本：v1.0 | 日期：2026-08-28
> 对应方案：`docs/handoff_optimization_solution.md §5/§7.5`

---

## 1. 核心模块

**文件**：`tools/pre_compression.py`

| 类/函数 | 用途 | 调用时机 |
|---------|------|----------|
| `PreCompressionPipeline` | 统一管道入口 | 工具返回时 / 对话轮次结束 / 压缩前 |
| `trim_tool_output / trim_tool_output_smart` | 工具输出剪枝 | 每次工具调用返回时 |
| `desensitize_text` | 敏感数据脱敏 | 语义去重前置 |
| `semantic_deduplicate` | 语义去重 | 每轮对话结束 / 压缩前 |
| `align_boundary_backward / protect_tool_groups` | 边界对齐 | 压缩前 / 截断时 |

---

## 2. 集成点

### 2.1 工具调用返回时（剪枝）
```python
# 在工具执行器返回结果前调用
from tools.pre_compression import trim_tool_output_smart

def on_tool_result(output: str) -> str:
    return trim_tool_output_smart(output, max_chars=5000)
```

### 2.2 对话轮次结束 / 压缩前（完整管道）
```python
# 在上下文压缩前、或对话轮次结束时调用
from tools.pre_compression import PreCompressionPipeline

pipeline = PreCompressionPipeline(
    trim_output=True,
    desensitize=True,
    semantic_dedup=True,
    align_boundary=True,
    dedup_threshold=0.85
)

# 处理消息列表
messages = pipeline.process_messages(messages)
# 记得清理缓存
pipeline.clear_cache()
```

### 2.3 solidify 固化时（已接入）
`solidify.sh` Step 1e 已接入 `handoff_summarizer.py`，预压缩管道作为其内部依赖。

---

## 3. 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `trim_output` | `True` | 是否剪枝工具输出 |
| `desensitize` | `True` | 是否脱敏（A/B/C 级） |
| `semantic_dedup` | `True` | 是否语义去重 |
| `align_boundary` | `True` | 是否边界对齐 |
| `dedup_threshold` | `0.85` | 语义去重相似度阈值 |
| `max_output_chars` | `5000` | 单次工具输出最大字符数 |

---

## 4. Embedding 模型（CR-004）

| 项目 | 配置 |
|------|------|
| 模型 | `qwen2.5-coder:7b` (Ollama 本地) |
| 方式 | mean-pooling 最后一层隐藏状态 |
| 向量维度 | 3584 |
| 内存峰值 | ≤1.2 GB |
| CPU 占用 | <30% 单核 |
| 延迟 | <200 ms / 32 条批次 |
| 向量持久化 | **无**（仅内存、用后即丢） |
| Fallback | 无 Ollama 时使用哈希向量 |

> **关键**：Embedding 仅内存计算，**不落盘、不入库、用后即丢**（`_EMBEDDING_CACHE` 进程内字典，`clear_cache()` 清理）

---

## 5. 脱敏规则（内置 + 字典）

| 规则组 | 级别 | 示例 |
|--------|------|------|
| `a_secrets` | A | 密钥/Token/私钥（禁止入库） |
| `b_ipv4` | B | `192.168.1.1` → `xxx.xxx.xxx.xxx` |
| `b_email` | B | `test@example.com` → `t***@example.com` |
| `b_paths` | B | `/Users/john/...` → `~/...` |
| `b_phone_cn` | B | `13812345678` → `138****5678` |
| 字典关键字 | A/B/C | `desensitize_dictionary.csv` 5 个示例条目 |

> 字典：`tools/desensitize/desensitize_dictionary.csv`（5 个示例占位条目）

---

## 6. 语义去重参数

| 参数 | 值 | 说明 |
|------|------|------|
| `threshold` | `0.85` | 余弦相似度阈值，超过即视为重复 |
| 保留策略 | 信息密度优先 | 内容更长/更结构化者保留 |
| 省略提示 | 自动插入 | `[预压缩：语义去重省略 N 条重复消息]` |

---

## 7. 边界对齐规则

| 场景 | 处理 |
|------|------|
| `assistant` + `tool_calls` → 后续 `tool` | 整组作为一个单元保留 |
| 截断消息列表时 | 从后向前保留，遇到 `tool` 必保留其配对 `tool_call` |
| 语义去重可能破坏组 | 去重后再次 `align_boundary_backward` 修复 |

---

## 7. 测试验证

```bash
# 1. 单元测试
python3 tools/pre_compression.py --trim tools/pre_compression.py
python3 tools/pre_compression.py --dedup test_messages.json --threshold 0.85

# 2. 完整管道测试
python3 -c "
from tools.pre_compression import PreCompressionPipeline
p = PreCompressionPipeline()
msgs = [{'role':'user','content':'测试IP xxx.xxx.xxx.xxx'}]
result = p.process_messages(msgs)
print(result)
"

# 3. 集成测试（需 Ollama 运行 qwen2.5-coder:7b）
# 无 Ollama 时自动降级为哈希向量（功能完整，语义质量降级）
```

---

## 8. 性能指标（目标值）

| 指标 | 目标 | 验收方式 |
|------|------|----------|
| 摘要生成延迟 | <500 ms (P99) | `solidify.sh` 采集 |
| 语义去重延迟 | <200 ms / 32 条 | 管道内计时 |
| 预压缩管道吞吐 | >50 req/s | 封装层统计 |
| 内存峰值 | ≤1.5 GB | `solidify.sh` 采集 RSS |
| GPU/CPU 占用 | GPU<50% / CPU<30% | 固化时采集 |

---

## 9. 注意事项

1. **Ollama 依赖**：Embedding 需 `ollama serve` 运行且 `qwen2.5-coder:7b` 已拉取；无服务时自动降级哈希向量（功能完整、语义质量降级）
2. **缓存清理**：批次处理后务必调用 `pipeline.clear_cache()` 释放 Embedding 缓存
3. **脱敏字典**：当前仅 5 个示例条目，生产需扩充 `desensitize_dictionary.csv`
4. **零额外 LLM 调用**：剪枝/脱敏/去重/对齐均为本地计算，不产生额外 LLM 调用成本
5. **Fallback 机制**：Ollama 不可用时自动降级哈希向量，功能完整但语义质量降级

---

## 10. 后续扩展（P3+）

- [ ] 接入实际工具执行器（opencode/agent runtime）
- [ ] 接入上下文压缩器（compaction 前调用完整管道）
- [ ] 扩充脱敏字典（生产级关键字）
- [ ] Embedding 质量基准测试（对比哈希向量 vs 真实 Embedding）
- [ ] 配置文件化（`.pre_compression.yml`）

---