#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP Server（tools/mcp_server/skills_mcp_server.py）stdio 端到端探针。

模拟 MCP 客户端完成一轮完整握手与调用：
  initialize → initialized → tools/list → tools/call(skill_list)
  → resources/read(skill://version) → prompts/get(invoke_role)

用法：.venv/bin/python tools/tests/test_mcp_server_stdio.py
退出码：0=全部通过；1=存在失败项。
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER = os.path.join(ROOT, "tools", "mcp_server", "skills_mcp_server.py")
EXPECTED_TOOLS = {"skill_list", "skill_load", "run_gate", "estimate_cost",
                  "solidify", "publish_production", "mirror_push"}
EXPECTED_PROMPTS = {"invoke_role", "phase_gate"}

results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  | {detail}" if detail else ""))


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, SERVER], cwd=ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8",
    )

    def send(msg: dict) -> None:
        proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        proc.stdin.flush()

    def recv(want_id: int) -> dict:
        while True:
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError(f"stdout 已关闭（等待 id={want_id}）stderr: {proc.stderr.read()[:2000]}")
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == want_id:
                return msg

    try:
        # 1. initialize
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "probe", "version": "0.0.1"}}})
        resp = recv(1)
        info = resp.get("result", {}).get("serverInfo", {})
        check("initialize", info.get("name") == "DevProjectTeamSkill", f"serverInfo={info}")

        # 2. initialized 通知
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        # 3. tools/list
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = {t["name"] for t in recv(2).get("result", {}).get("tools", [])}
        check("tools/list 共 7 工具", tools == EXPECTED_TOOLS, f"实际={sorted(tools)}")

        # 4. tools/call skill_list
        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "skill_list", "arguments": {}}})
        content = recv(3).get("result", {}).get("content", [])
        text = "".join(c.get("text", "") for c in content)
        n_roles = text.count("role-")
        check("tools/call skill_list", n_roles >= 10, f"角色包数={n_roles}，首行={text.splitlines()[0] if text else '空'}")

        # 5. resources/read skill://version
        send({"jsonrpc": "2.0", "id": 4, "method": "resources/read",
              "params": {"uri": "skill://version"}})
        ver = "".join(c.get("text", "") for c in recv(4).get("result", {}).get("contents", []))
        check("resources/read skill://version", ver.startswith("v21."), f"版本={ver}")

        # 6. resources/list（静态）+ resources/templates/list（模板）
        send({"jsonrpc": "2.0", "id": 5, "method": "resources/list"})
        uris = {r["uri"] for r in recv(5).get("result", {}).get("resources", [])}
        check("resources/list 静态资源", {"skill://index", "skill://version"}.issubset(uris), f"实际={sorted(uris)}")
        send({"jsonrpc": "2.0", "id": 8, "method": "resources/templates/list"})
        t_uris = {r["uriTemplate"] for r in recv(8).get("result", {}).get("resourceTemplates", [])}
        check("resources/templates/list 模板", {"skill://role/{name}/SKILL", "skill://references/{file}"}.issubset(t_uris), f"实际={sorted(t_uris)}")

        # 6a. 模板资源实读：skill://references/iron_rules.md
        send({"jsonrpc": "2.0", "id": 9, "method": "resources/read",
              "params": {"uri": "skill://references/iron_rules.md"}})
        rtext = "".join(c.get("text", "") for c in recv(9).get("result", {}).get("contents", []))
        check("resources/read 模板实读 references", len(rtext) > 200, f"字数={len(rtext)}，首行={rtext.splitlines()[0][:60] if rtext else '空'}")

        # 7. prompts/get invoke_role
        send({"jsonrpc": "2.0", "id": 6, "method": "prompts/get",
              "params": {"name": "invoke_role",
                         "arguments": {"role": "role-testing", "task": "冒烟测试"}}})
        msgs = recv(6).get("result", {}).get("messages", [])
        ptext = "".join(m.get("content", {}).get("text", "") for m in msgs)
        check("prompts/get invoke_role", "role-testing" in ptext and "冒烟测试" in ptext, ptext[:80])

        # 8. prompts/list
        send({"jsonrpc": "2.0", "id": 7, "method": "prompts/list"})
        prompts = {p["name"] for p in recv(7).get("result", {}).get("prompts", [])}
        check("prompts/list 共 2 模板", prompts == EXPECTED_PROMPTS, f"实际={sorted(prompts)}")
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        proc.terminate()
        proc.wait(timeout=10)

    failed = [r for r in results if not r[1]]
    print(f"\n合计 {len(results)} 项，通过 {len(results) - len(failed)}，失败 {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
