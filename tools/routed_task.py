#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 路由任务接口（供云端 Agent 调用本地模型）

通过 _model_router_proxy 定位 dev-model-router，使用 RoutedExecutor
将代码任务路由到本地 14B 模型或云端模型。

设计目标：
- 云端 Agent（如当前会话中的 AI）需要做代码修复/走查/测试生成时，
  通过本模块将实际代码生成下发到本地 14B 模型（零成本）
- 复杂任务自动路由到云端高阶模型
- 返回结果 + 成本信息

Usage (Python):
    from tools.routed_task import route_code_task

    result = route_code_task(
        task_type="review",
        source_code="def foo(): pass",
        file_path="scripts/example.py",
    )
    print(result["issues"])

Usage (CLI):
    python tools/routed_task.py review scripts/example.py < scripts/example.py
    python tools/routed_task.py test_gen scripts/example.py < scripts/example.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def _get_routed_executor(
    ollama_host: Optional[str] = None,
    ollama_port: Optional[int] = None,
    local_model: str = "qwen2.5-coder:14b",
):
    """创建 RoutedExecutor 实例（通过 _model_router_proxy 定位 dev-model-router）。"""
    ollama_host = ollama_host or os.environ.get("OLLAMA_HOST", "localhost")
    ollama_port = ollama_port or int(os.environ.get("OLLAMA_PORT", "11434"))
    # 导入代理模块定位 dev-model-router
    try:
        from ._model_router_proxy import find_model_router_root
    except ImportError:
        # 回退：直接路径查找
        def find_model_router_root():
            from pathlib import Path
            env_root = os.environ.get("DEV_MODEL_ROUTER_ROOT")
            if env_root:
                p = Path(env_root)
                if p.is_dir():
                    return p
            # 同级目录约定
            sibling = Path(__file__).resolve().parent.parent.parent / "dev-model-router"
            if sibling.is_dir():
                return sibling
            return None

    router_root = find_model_router_root()
    if router_root is None:
        raise RuntimeError(
            "dev-model-router 未找到。请设置 DEV_MODEL_ROUTER_ROOT 环境变量，"
            "或将 dev-model-router 放在 DevProjectTeamSkill 同级目录。"
        )

    # 确保 dev-model-router 在 Python 路径中
    router_str = str(router_root)
    if router_str not in sys.path:
        sys.path.insert(0, router_str)

    from executor.ollama_client import OllamaClient
    from executor.routed_executor import RoutedExecutor
    from executor.cloud_client import CloudClient
    from pathlib import Path

    ollama = OllamaClient(host=ollama_host, port=ollama_port)
    cloud = CloudClient()

    return RoutedExecutor(
        ollama_client=ollama,
        cloud_client=cloud if cloud.is_configured else None,
        local_model=local_model,
        cost_storage_path=Path(os.path.expanduser("~/nightly_reports/router_costs.json")),
        daily_budget=float(os.environ.get("DAILY_BUDGET_LIMIT", "5.0")),
        router_mode=os.environ.get("ROUTER_MODE", "keyword"),
    )


def route_code_task(
    task_type: str,
    source_code: str,
    file_path: str,
    extra_context: str = "",
    ollama_host: Optional[str] = None,
    ollama_port: Optional[int] = None,
) -> Dict[str, Any]:
    """
    路由代码任务到本地/云端模型。

    Args:
        task_type: 任务类型 ("review" | "completion" | "test_gen")
        source_code: 源代码内容
        file_path: 文件路径
        extra_context: 额外上下文（如安全扫描结果）
        ollama_host: Ollama 主机地址
        ollama_port: Ollama 端口

    Returns:
        Dict 包含：
        - task_type: 任务类型
        - file_path: 文件路径
        - route: 实际路由 ("local" | "cloud")
        - result: 任务结果（根据 task_type 不同结构不同）
        - cost: 成本信息
    """
    executor = _get_routed_executor(ollama_host, ollama_port)

    if task_type == "review":
        result = executor.review_code(source_code, file_path, extra_context=extra_context)
        return {
            "task_type": "review",
            "file_path": file_path,
            "issues": [
                {
                    "line": i.line,
                    "severity": i.severity,
                    "category": i.category,
                    "description": i.description,
                    "suggestion": i.suggestion,
                }
                for i in result.issues
            ],
            "issue_count": result.issue_count,
            "blocking_count": result.blocking_count,
            "error": result.error,
            "duration_s": result.duration_s,
            **_extract_stats(executor),
        }

    elif task_type == "completion":
        result = executor.suggest_completion(source_code, file_path)
        return {
            "task_type": "completion",
            "file_path": file_path,
            "completion_code": result.completion_code,
            "explanation": result.explanation,
            "confidence": result.confidence,
            "error": result.error,
            "duration_s": result.duration_s,
            **_extract_stats(executor),
        }

    elif task_type == "test_gen":
        result = executor.generate_tests(source_code, file_path)
        return {
            "task_type": "test_gen",
            "file_path": file_path,
            "test_code": result.test_code,
            "test_targets": result.test_targets,
            "test_count": result.test_count,
            "error": result.error,
            "duration_s": result.duration_s,
            **_extract_stats(executor),
        }

    else:
        return {
            "task_type": task_type,
            "file_path": file_path,
            "error": f"Unknown task_type: {task_type}",
        }


def _extract_stats(executor) -> Dict[str, Any]:
    """从执行器提取路由统计。"""
    try:
        stats = executor.get_routing_stats()
        return {
            "routing": {
                "total": stats.total_tasks,
                "local": stats.routed_local,
                "cloud": stats.routed_cloud,
                "degraded": stats.degraded_to_local,
                "total_cost": stats.total_cost,
            },
        }
    except AttributeError:
        return {"routing": {"total": 0}}


# ── CLI 入口 ──

def main():
    """CLI 入口：python tools/routed_task.py <task_type> <file_path> [< source_file]"""
    if len(sys.argv) < 3:
        print("Usage: python routed_task.py <task_type> <file_path>", file=sys.stderr)
        print("  task_type: review | completion | test_gen", file=sys.stderr)
        print("  从 stdin 读取源代码（或从 file_path 读取）", file=sys.stderr)
        sys.exit(1)

    task_type = sys.argv[1]
    file_path = sys.argv[2]

    # 从文件读取源代码
    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
    else:
        # 从 stdin 读取
        source_code = sys.stdin.read()

    ollama_host = os.environ.get("OLLAMA_HOST", "localhost").replace("http://", "").replace("https://", "")
    if ":" in ollama_host:
        host, port_str = ollama_host.rsplit(":", 1)
        ollama_port = int(port_str)
    else:
        host = ollama_host
        ollama_port = int(os.environ.get("OLLAMA_PORT", "11434"))

    result = route_code_task(
        task_type=task_type,
        source_code=source_code,
        file_path=file_path,
        ollama_host=host,
        ollama_port=ollama_port,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
