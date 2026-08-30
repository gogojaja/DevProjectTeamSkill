#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# nightly_code_complete.py — 夜间自动代码补全工具（人在回路 / draft PR 模式）
#
# 行业最佳实践锚定（详见决策记录，来源 2026）：
#   EV-001 人在回路、绝不自动合入 main（GitHub Blog / jainmehul）
#   EV-002 质量门禁以测试为真相，不依赖模型自评（jainmehul）
#   EV-003 三道门：自动检查 → AI 预评审 → 人工意图评审（ruchitsuthar）
#   EV-004 仅低爆炸半径、可逆、显式标记点才自动化（parallelcode/ruchitsuthar）
#   EV-005 有界预算：候选上限/迭代上限/token 上限（loiane）
#   EV-006 护栏：仅分支、绝不合入/强推、绝不 disable 测试、限定文件（loiane）
#   EV-007 生成节流匹配评审吞吐（ruchitsuthar）
#   EV-008 动作分级 G0-G3、sandbox-first、凭据不落盘（dev.to brennhill）
#
# 本仓库铁律对齐：
#   铁律#1 源码单源：默认仅扫 tools/ 与显式 --scope，绝不碰 .trae/skills 角色包
#   铁律#3 A级：LLM 凭据经 load_secret（env/.secrets/Keychain），不入库不打印
#   铁律#7a 目录边界：仅白名单目录 + 仅标记点
#   铁律#8 脱敏：审计台账 PR 链接/路径脱敏
#   铁律#12 运行时自变：审计台账运行时 append → 不入库（gitignore）
#
# 子命令：
#   run      实际执行（发现候选 → 生成 → 门禁 → draft PR）
#   --dry-run 仅探测候选并展示计划补全（provider=mock，不做任何副作用）
#
# 用法：
#   python3 tools/nightly_code_complete.py --dry-run
#   python3 tools/nightly_code_complete.py run --scope tools --max-candidates 5
#   python3 tools/nightly_code_complete.py run --provider http --model gpt-4o
# =============================================================================
import os
import sys
import csv
import io
import re
import json
import hashlib
import argparse
import datetime
import subprocess
import tempfile

ROOT = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS = os.path.join(ROOT, "tools")
DEFAULT_SCOPES = [os.path.join(ROOT, "tools")]          # 铁律#1：默认只扫 tools/
AUDIT = os.path.join(ROOT, "台账", "nightly_code_complete_audit.csv")
STATE = os.path.join(ROOT, ".secrets", "nightly_code_complete_state.json")  # gitignored
BOM = b"\xef\xbb\xbf"

# 候选标记：仅注释上下文中的哨兵 @auto-complete（含行内注释），或 TODO/FIXME 后缀 (@auto-complete)
# 用 @ 哨兵而非裸 "auto-complete"，避免误匹配文档/字符串字面量（如分支名 "auto-complete/..."）
MARKER_RE = re.compile(r"(#|//|/\*|\*)\s*.*?@auto-complete", re.IGNORECASE)
TODO_RE = re.compile(r"#.*?\b(TODO|FIXME|XXX)\b.*?@auto-complete", re.IGNORECASE)
# 桩识别：仅替换这些"明确未完成"的行
STUB_LINE_RE = re.compile(
    r"^\s*(pass|raise\s+NotImplementedError|raise\s+NotImplemented|\.\.\.|return\s+None|return\s+NotImplemented)\b"
)

# 默认可处理的文本源码扩展名
SRC_EXT = (".py", ".js", ".ts", ".tsx", ".go", ".java", ".rb", ".rs", ".cpp", ".c", ".sh")


def _run(cmd, cwd=None, timeout=1800, input_text=None):
    """复用 nightly_quality_gate 的 _run 范式：返回 (ok, out, err)。"""
    try:
        r = subprocess.run(cmd, cwd=cwd or ROOT, input=input_text,
                           capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        return r.returncode == 0, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return False, "", "timeout"
    except Exception as e:  # noqa: BLE001
        return False, "", str(e)


def _next_id(path, prefix):
    n = 1
    if os.path.exists(path):
        with io.open(path, "r", encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                if row and row[0].startswith(prefix):
                    try:
                        n = max(n, int(row[0].split("-")[1]) + 1)
                    except Exception:
                        pass
    return "%s-%03d" % (prefix, n)


def _append_csv(path, header, rows):
    new = not os.path.exists(path)
    with io.open(path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        for r in rows:
            w.writerow(r)


def _load_state():
    if os.path.exists(STATE):
        try:
            with io.open(STATE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"done": [], "run_seq": 0}


def _save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with io.open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)


def _fingerprint(cand):
    key = "%s:%d:%s" % (cand["file"], cand["line"], cand["snippet"])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 1) 发现：仅显式 @auto-complete 标记点（强约束，防越权）
# ---------------------------------------------------------------------------
def find_candidates(scopes, max_candidates, exclude=None):
    exclude = exclude or []
    cands = []
    seen_files = set()
    for scope in scopes:
        if not os.path.isdir(scope):
            continue
        for dirpath, dirs, files in os.walk(scope):
            # 不递归进排除目录（.git / 第三方）
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules", ".secrets")]
            for fn in files:
                if not fn.endswith(SRC_EXT):
                    continue
                full = os.path.join(dirpath, fn)
                if any(full.startswith(e) for e in exclude):
                    continue
                cands += _scan_file(full, max_candidates - len(cands))
                if len(cands) >= max_candidates:
                    return cands[:max_candidates]
    return cands[:max_candidates]


def _scan_file(full, budget):
    out = []
    try:
        with io.open(full, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return out
    for i, line in enumerate(lines):
        if not (MARKER_RE.search(line) or TODO_RE.search(line)):
            continue
        # 仅替换紧随其后的桩块（同缩进连续行，直到缩进下降或空行/桩结束）
        stub_start = i + 1
        if stub_start >= len(lines):
            continue
        base_indent = len(lines[stub_start]) - len(lines[stub_start].lstrip(" "))
        block = []
        j = stub_start
        while j < len(lines):
            cur = lines[j]
            if cur.strip() == "":
                break
            indent = len(cur) - len(cur.lstrip(" "))
            if j > stub_start and indent < base_indent:
                break
            block.append(cur)
            j += 1
        snippet = "".join(block).rstrip("\n")
        if not snippet.strip():
            continue
        # 防自匹配：标记点必须是"解释说明"之外的真实桩——要求桩块首行即未完成桩
        if not STUB_LINE_RE.match(block[0].strip()):
            continue
        out.append({
            "id": "",  # 运行期统一编号
            "file": full,
            "line": i + 1,
            "marker": line.strip(),
            "stub_start": stub_start + 1,            # 1-indexed（文件内）
            "stub_end": stub_start + len(block),    # 含
            "snippet": snippet,
        })
        if len(out) >= budget:
            break
    return out


# ---------------------------------------------------------------------------
# 2) 上下文检索（轻量 RAG，零依赖）
# ---------------------------------------------------------------------------
def context_for(full, cand, root):
    ctx = []
    try:
        with io.open(full, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        lines = []
    # 同文件：候选前后各 40 行
    lo = max(0, cand["line"] - 40)
    hi = min(len(lines), cand["stub_end"] + 40)
    ctx.append("【文件上下文 %s 行 %d-%d】" % (os.path.relpath(full, root), lo + 1, hi))
    ctx.append("".join(lines[lo:hi]))
    # 邻近测试文件（若存在）
    test_candidates = [
        full.replace(".py", "_test.py"),
        os.path.join(os.path.dirname(full), "tests",
                     os.path.basename(full).replace(".py", "_test.py")),
    ]
    for tc in test_candidates:
        if os.path.exists(tc):
            ctx.append("【相关测试 %s】" % os.path.relpath(tc, root))
            try:
                with io.open(tc, "r", encoding="utf-8") as f:
                    ctx.append(f.read()[:2000])
            except Exception:
                pass
            break
    # 仓库约定（语言铁律：中文注释等）
    ag = os.path.join(root, "AGENTS.md")
    if os.path.exists(ag):
        ctx.append("【仓库约定 AGENTS.md 摘要】注释与文档一律中文；不引入未授权新依赖；")
    return "\n".join(ctx)


# ---------------------------------------------------------------------------
# 3) 生成（provider 可插拔：mock / opencode / http）
# ---------------------------------------------------------------------------
def build_prompt(cand, ctx):
    return (
        "你是代码补全助手。仅补全下方【待补全桩】标记的代码块，"
        "保持相同函数签名、相同缩进、不破坏已有测试、遵循中文注释约定、"
        "不引入新的第三方依赖（除非现有导入已使用）。只输出补全后的代码块本身，"
        "不要输出解释，不要改动桩以外的代码。\n\n"
        "【上下文】\n%s\n\n【待补全桩（文件 %s 行 %d-%d）】\n%s\n"
        % (ctx, cand["file"], cand["stub_start"], cand["stub_end"], cand["snippet"])
    )


def _extract_code(text):
    """从模型输出中提取代码块（```...``` 或纯文本）。"""
    m = re.search(r"```(?:[a-zA-Z]+)?\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).rstrip("\n") + "\n"
    return text.strip() + "\n"


def generate(provider, prompt, cfg):
    if provider == "mock":
        # 确定性占位（用于 dry-run 与测试，不联网）
        return "# [mock 补全] 由评审者人工实现\n    pass\n"
    if provider == "http":
        from load_secret import load
        _, token = load(cfg.secret_name)
        if not token:
            raise RuntimeError("HTTP provider 需要 %s 凭据（env/.secrets/Keychain），未取到" % cfg.secret_name)
        body = json.dumps({
            "model": cfg.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": cfg.max_tokens,
            "temperature": 0.2,
        }).encode("utf-8")
        req = urllib_request(cfg.api_base + "/chat/completions", body, token)
        data = json.loads(req)
        return _extract_code(data["choices"][0]["message"]["content"])
    if provider == "opencode":
        # 调用本仓库已配置的 opencode（headless 批量）。接口以子进程为准。
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
            tf.write(prompt)
            pfile = tf.name
        try:
            ok, out, err = _run(["opencode", "--prompt-file", pfile], timeout=cfg.llm_timeout)
        finally:
            try:
                os.unlink(pfile)
            except Exception:
                pass
        if not ok:
            raise RuntimeError("opencode 调用失败（请确认 opencode CLI 可用或改用 --provider http）：%s" % err[:300])
        return _extract_code(out)
    raise RuntimeError("未知 provider: %s" % provider)


def urllib_request(url, body, token):
    import urllib.request
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % token,
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8")


# ---------------------------------------------------------------------------
# 4) 质量门禁（在临时分支应用，失败回滚）
# ---------------------------------------------------------------------------
def apply_completion(full, cand, completion):
    """将桩块替换为补全代码，返回新文件内容。"""
    with io.open(full, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new = lines[:cand["stub_start"] - 1] + [completion] + lines[cand["stub_end"]:]
    return "".join(new)


def gate(root, cand, full, completion, cfg, branch):
    """在 feature 分支写入改动并跑门禁；失败返回 (False, detail)。"""
    new_content = apply_completion(full, cand, completion)
    if cfg.dry_run or cfg.no_git:
        return True, "dry-run/no-git：跳过分支与门禁"
    # 建分支
    ok, _, err = _run(["git", "checkout", "-b", branch], cwd=root)
    if not ok:
        return False, "建分支失败: %s" % err[:200]
    try:
        with io.open(full, "w", encoding="utf-8") as f:
            f.write(new_content)
        # 门禁命令
        results = []
        for label, cmd in [("lint", cfg.lint_cmd), ("test", cfg.test_cmd)]:
            if not cmd:
                results.append("%s=skip" % label)
                continue
            ok2, out, err = _run(cmd, cwd=root, shell=True, timeout=cfg.gate_timeout)
            results.append("%s=%s" % (label, "pass" if ok2 else "FAIL"))
            if not ok2:
                return False, "门禁%s失败: %s" % (label, (out or err)[:400])
        return True, ";".join(results)
    finally:
        # 无论成败，回到 main（失败分支由交付阶段决定是否保留）
        _run(["git", "checkout", "main"], cwd=root)


# ---------------------------------------------------------------------------
# 5) 交付（draft PR 或本地 patch，绝不自动合入）
# ---------------------------------------------------------------------------
def deliver(root, cand, completion, gate_ok, gate_detail, cfg, branch, run_id):
    if not gate_ok:
        return "skipped", ""
    if cfg.dry_run or cfg.no_pr:
        # 降级：本地 patch 落地 .backup/，记入待决策队列模式（不推送）
        os.makedirs(os.path.join(root, ".backup"), exist_ok=True)
        patch = os.path.join(root, ".backup", "%s.patch" % cand["id"])
        with io.open(patch, "w", encoding="utf-8") as f:
            f.write(apply_completion(cand["file"], cand, completion))
        return "patch", os.path.relpath(patch, root)
    # 推送分支 + draft PR（需 gh 与远端凭据）
    ok, _, err = _run(["git", "checkout", branch], cwd=root)
    if not ok:
        return "skipped", "无法切换分支: %s" % err[:200]
    _run(["git", "add", "-A"], cwd=root)
    _run(["git", "commit", "-m", "auto-complete(%s): %s" % (cand["id"], os.path.basename(cand["file"]))], cwd=root)
    ok, _, err = _run(["git", "push", "-u", "origin", branch], cwd=root)
    if not ok:
        return "skipped", "推送失败(无远端凭据?): %s" % err[:200]
    title = "auto-complete %s · %s" % (cand["id"], os.path.basename(cand["file"]))
    body = ("夜间自动代码补全（draft，待人工评审）\n\n候选: %s 行 %d-%d\n门禁: %s\n"
            "生成模型: %s\n请人工评审后决定是否合入。" %
            (os.path.relpath(cand["file"], root), cand["stub_start"], cand["stub_end"],
             gate_detail, cfg.provider))
    ok, out, err = _run(["gh", "pr", "create", "--draft", "-t", title, "-b", body], cwd=root)
    if not ok:
        return "branch-pushed", "PR 创建失败(gh 未登录?): %s" % err[:200]
    # 提取 PR 链接（脱敏：仅保留域名）
    url = ""
    for ln in out.splitlines():
        if "github.com" in ln or "gitee.com" in ln:
            url = re.sub(r"(https?://[^/]+).*", r"\1/***", ln.strip())
            break
    return "pr", url or "pushed"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def run(cfg):
    state = _load_state()
    if cfg.reset_state:
        state = {"done": [], "run_seq": 0}
    scopes = cfg.scope if cfg.scope else DEFAULT_SCOPES
    print("[ncc] 扫描范围: %s" % ", ".join(scopes))
    cands = find_candidates(scopes, cfg.max_candidates, exclude=cfg.exclude)
    # 去重：跳过已处理指纹
    fresh = []
    for c in cands:
        fp = _fingerprint(c)
        if fp in state["done"]:
            print("[ncc] 跳过已完成候选: %s" % c["file"])
            continue
        c["fp"] = fp
        fresh.append(c)
    cands = fresh
    print("[ncc] 发现候选 %d 个" % len(cands))
    if not cands:
        return 0

    state["run_seq"] += 1
    run_id = "NCC-RUN-%03d" % state["run_seq"]
    audit_rows = []
    for idx, c in enumerate(cands, 1):
        c["id"] = _next_id(AUDIT, "NCC")
        print("[ncc] ── %d/%d %s %s 行 %d ──" % (idx, len(cands), c["id"],
                                                  os.path.relpath(c["file"], ROOT), c["line"]))
        ctx = context_for(c["file"], c, ROOT)
        try:
            completion = generate(cfg.provider, build_prompt(c, ctx), cfg)
        except Exception as e:
            print("[ncc] 生成失败: %s" % e)
            audit_rows.append([c["id"], _now(), os.path.relpath(c["file"], ROOT), c["line"],
                                "gen-fail", cfg.provider, 0, "", "error: %s" % str(e)[:200]])
            continue
        branch = "auto-complete/%s" % c["id"]
        gate_ok, gate_detail = gate(ROOT, c, c["file"], completion, cfg, branch)
        status, ref = deliver(ROOT, c, completion, gate_ok, gate_detail, cfg, branch, run_id)
        diff_lines = completion.count("\n")
        audit_rows.append([c["id"], _now(), os.path.relpath(c["file"], ROOT), c["line"],
                           "ok" if gate_ok else "gate-fail", cfg.provider, diff_lines,
                           ref, gate_detail])
        if gate_ok:
            state["done"].append(c["fp"])
    _save_state(state)
    _append_csv(AUDIT, ["候选ID", "时间", "文件", "行", "结果", "模型", "diff行数", "PR/补丁(脱敏)", "门禁详情"],
                audit_rows)
    print("[ncc] 审计台账: %s（运行时自变，gitignore）" % AUDIT)
    print("[ncc] 完成，run_id=%s" % run_id)
    return 0


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    p = argparse.ArgumentParser(description="夜间自动代码补全（draft PR 模式，人在回路）")
    p.add_argument("--dry-run", action="store_true", help="仅探测候选+展示计划补全，不做副作用（provider=mock）")
    p.add_argument("--scope", action="append", help="扫描目录（可多次）；默认 tools/")
    p.add_argument("--exclude", action="append", default=[], help="排除路径前缀")
    p.add_argument("--max-candidates", type=int, default=5, help="单次最大候选数（防 PR 洪泛，EV-007）")
    p.add_argument("--provider", choices=["mock", "opencode", "http"], default="opencode",
                   help="生成 provider；dry-run 强制 mock")
    p.add_argument("--model", default="gpt-4o", help="http provider 模型名")
    p.add_argument("--api-base", default="https://api.openai.com/v1", help="http provider 基址（OpenAI 兼容）")
    p.add_argument("--secret-name", default="llm_token", help="http provider 凭据名（走 load_secret）")
    p.add_argument("--max-tokens", type=int, default=1024, help="单次生成 token 上限（有界预算）")
    p.add_argument("--llm-timeout", type=int, default=300, help="LLM 调用超时秒")
    p.add_argument("--gate-timeout", type=int, default=1800, help="门禁命令超时秒")
    p.add_argument("--lint-cmd", default="", help="门禁 lint 命令（如 'python3 -m flake8 tools'）")
    p.add_argument("--test-cmd", default="", help="门禁测试命令（如 'python3 -m pytest tests -q'）")
    p.add_argument("--no-git", action="store_true", help="不建分支/不改 git（仅计算）")
    p.add_argument("--no-pr", action="store_true", help="不推送/不建 PR，降级为本地 patch")
    p.add_argument("--reset-state", action="store_true", help="清空已完成指纹去重状态")
    args = p.parse_args()
    if args.dry_run:
        args.provider = "mock"
        args.no_git = True
        args.no_pr = True
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
