#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP Server（tools/mcp_server/skills_mcp_server.py）stdio 端到端探针。

模拟 MCP 客户端完成一轮完整握手与调用：
  initialize → initialized → tools/list → tools/call(skill_list)
  → tools/call(run_gate) → resources/read(skill://version) → prompts/get(invoke_role)

v21.24.1 补强：
  1. 新增 tools/call(run_gate) 断言——它是唯一走 subprocess 的工具，此前零覆盖，
     致 GBK/UTF-8 解码缺陷（r.stdout 为 None、门禁输出全丢）长期潜伏无人发现。
  2. 工具/prompts 断言由「硬编码集合相等」改为「核心子集包含 + 总数阈值」，
     避免每次能力扩张都误红（原断言停在 7 工具/2 prompts，实际已 24/9）。
  3. 新增 pytest 入口 test_mcp_stdio_end_to_end()——原为 def main() 脚本形式，
     pytest 不收集，等于长期无人运行的失效门禁。

用法：python tools/tests/test_mcp_server_stdio.py   或   pytest tools/tests/test_mcp_server_stdio.py
退出码：0=全部通过；1=存在失败项。
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER = os.path.join(ROOT, "tools", "mcp_server", "skills_mcp_server.py")
# 核心能力子集（缺失即红）+ 总数阈值（能力扩张不误红）
CORE_TOOLS = {"skill_list", "skill_load", "run_gate", "estimate_cost",
              "solidify", "publish_production", "mirror_push"}
MIN_TOOLS = 24
CORE_PROMPTS = {"invoke_role", "phase_gate"}
MIN_PROMPTS = 9

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
        check(f"tools/list 含核心 {len(CORE_TOOLS)} 工具且总数≥{MIN_TOOLS}",
              CORE_TOOLS.issubset(tools) and len(tools) >= MIN_TOOLS,
              f"总数={len(tools)}，缺失核心={sorted(CORE_TOOLS - tools)}")

        # 4. tools/call skill_list
        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "skill_list", "arguments": {}}})
        content = recv(3).get("result", {}).get("content", [])
        text = "".join(c.get("text", "") for c in content)
        n_roles = text.count("role-")
        check("tools/call skill_list", n_roles >= 10, f"角色包数={n_roles}，首行={text.splitlines()[0] if text else '空'}")

        # 4a. tools/call run_gate —— subprocess 输出完整性回归防护（v21.24.1）
        # 缺陷史：text=True 未指定 encoding 时，Windows 中文系统按 locale(GBK) 解码子进程的
        # UTF-8 输出，解码异常发生在 subprocess 的 _readerthread 线程内 → buffer 未 append
        # → communicate() 返回 None → r.stdout is None，门禁输出全丢而 tool 返回空串
        # （旧写法 r.stdout + r.stderr 则直接抛 TypeError: NoneType + str）。
        # 三项断言：输出足够长、含中文特征词、无 U+FFFD 替换字符。
        # 一旦 encoding="utf-8" 被移除或 reader 线程再次崩溃，本项立即变红。
        send({"jsonrpc": "2.0", "id": 10, "method": "tools/call",
              "params": {"name": "run_gate",
                         "arguments": {"gate": "closure", "skill": "dev-project-team-skill"}}})
        gtext = "".join(c.get("text", "") for c in recv(10).get("result", {}).get("content", []))
        # 注：Python 3.11 不允许 f-string 表达式内出现反斜杠（3.12+ 才放开），
        # 故 U+FFFD 判定先提取为局部变量，不在 f-string 内写 '\ufffd' 字面量。
        has_cjk = "闭环" in gtext
        has_repl = "\ufffd" in gtext
        check("tools/call run_gate 门禁输出未丢失",
              len(gtext) > 500 and has_cjk and not has_repl,
              f"字数={len(gtext)}，含'闭环'={has_cjk}，含替换符={has_repl}，"
              f"首行={gtext.splitlines()[0][:60] if gtext else '空'}")

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
        check(f"prompts/list 含核心 {len(CORE_PROMPTS)} 模板且总数≥{MIN_PROMPTS}",
              CORE_PROMPTS.issubset(prompts) and len(prompts) >= MIN_PROMPTS,
              f"总数={len(prompts)}，缺失核心={sorted(CORE_PROMPTS - prompts)}")
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


def test_mcp_stdio_end_to_end() -> None:
    """pytest 入口：包装 main()，使本探针纳入 pytest 收集。

    原文件仅有 def main() + __main__ 守卫，pytest 不收集任何项，
    导致这个唯一的 subprocess 路径端到端门禁长期无人运行而静默失效。
    """
    rc = main()
    failed = [name for name, ok, _ in results if not ok]
    assert rc == 0, f"stdio 端到端探针失败项：{failed}"


if __name__ == "__main__":
    sys.exit(main())
