#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mirror_push.py — 国内镜像同步（地缘风险对冲）双推工具

策略：每次提交同时推送 origin(GitHub) + mirror(Gitee) 等多个 remote。
单目标失败不阻断另一个；每次同步追加 台账/32_镜像同步记录.csv 留痕。

安全约定（铁律 #3 A 级）：
- 国内/境外 token 只经环境变量或 .secrets/ 提供，脚本从 GITEE_TOKEN/GITEE_USER 等读取，
  经 `git -c url.<auth>@.insteadOf=...` 注入，绝不打印、不写入仓库、不硬编码。
- 凭据获取跨平台走 `load_secret.load()`：环境变量 > .secrets/<name> 文件 > macOS Keychain；
  Windows 用 .secrets 文件或环境变量，macOS 额外支持系统钥匙串。
- 远程 URL 入台账前一律脱敏（掩去 user:token）。

用法（跨平台）：
  py -3.11 tools/mirror_push.py                # Windows
  python3 tools/mirror_push.py                 # macOS / Linux
  py -3.11 tools/mirror_push.py origin mirror  # 指定 remote 列表
  py -3.11 tools/mirror_push.py --verify       # 仅校验各 remote 与本地 HEAD 是否一致
  # 凭据三种提供方式（任选，脚本自动装载，无需手动 export）：
  #   a) 环境变量： $env:GITEE_TOKEN="xxx"; $env:GITEE_USER="gogojaja"   (Windows)
  #                export GITEE_TOKEN="xxx"; export GITEE_USER="gogojaja" (macOS)
  #   b) 文件：     .secrets/gitee_token 与 .secrets/gitee_user（gitignore，不入库）
  #   c) macOS：    security add-generic-password -s gitee_token -a <user> -w <token>
"""
import os
import sys
import re
import csv
import io
import datetime
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "台账", "32_镜像同步记录.csv")
BOM = b"\xef\xbb\xbf"
DEFAULT_REMOTES = ["origin", "mirror"]

# remote -> (user_env, token_env)
TOKEN_ENV = {
    "mirror": ("GITEE_USER", "GITEE_TOKEN"),
    "gitee": ("GITEE_USER", "GITEE_TOKEN"),
    "gitcode": ("GITCODE_USER", "GITCODE_TOKEN"),
    "origin": ("GITHUB_USER", "GITHUB_TOKEN"),
    "github": ("GITHUB_USER", "GITHUB_TOKEN"),
}


def _run(cmd, extra_env=None):
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)


def _branch():
    r = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    b = r.stdout.strip()
    return b or "main"


def _head():
    return _run(["git", "rev-parse", "HEAD"]).stdout.strip()


def _mask(url):
    """脱敏：掩去 user:token。"""
    return re.sub(r"://[^/@]+@", "://***@", url) if url else ""


def _remote_exists(remote):
    r = _run(["git", "remote", "get-url", remote])
    return r.returncode == 0 and r.stdout.strip() != ""


def _push_one(remote, branch):
    """推送单个 remote；token 经 insteadOf 注入，不持久化。返回 (ok, msg, elapsed_sec)。"""
    user_var, token_var = TOKEN_ENV.get(remote, (remote.upper() + "_USER", remote.upper() + "_TOKEN"))
    token = os.environ.get(token_var)
    user = os.environ.get(user_var)

    extra_args = []
    if token:
        url = _run(["git", "remote", "get-url", remote]).stdout.strip()
        if "://" in url:
            proto, rest = url.split("://", 1)
            host = rest.split("/", 1)[0]
            auth = ("%s:" % user if user else "") + token + "@"
            instead = "%s://%s%s/" % (proto, auth, host)
            orig = "%s://%s/" % (proto, host)
            extra_args = ["-c", "url.%s.insteadOf=%s" % (instead, orig)]

    cmd = ["git", *extra_args, "push", remote, branch]
    start = datetime.datetime.now()
    res = _run(cmd)
    elapsed = (datetime.datetime.now() - start).total_seconds()
    ok = res.returncode == 0
    out = (res.stdout + res.stderr).strip()
    for s in (token, user):  # 铁律 #3 A 级：输出中抹除凭据，绝不回显/落盘
        if s:
            out = out.replace(s, "***")
    last = out.splitlines()[-1] if out else ""
    return ok, (last if last else ("成功" if ok else "失败")), elapsed


def _next_seq():
    if not os.path.exists(LEDGER):
        return 1
    with io.open(LEDGER, "r", encoding="utf-8-sig") as f:
        lines = [l for l in f.read().splitlines() if l.strip()]
    # 数据行数（去掉表头）
    return max(0, len(lines) - 1) + 1


def _append_ledger(rows):
    header = ["同步编号", "同步时间", "源commit", "目标remote", "远程URL(脱敏)", "状态", "耗时秒", "说明"]
    new = not os.path.exists(LEDGER)
    with io.open(LEDGER, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        for row in rows:
            w.writerow(row)


def _verify(remotes, branch):
    head = _head()
    print("本地 HEAD: %s" % head[:12])
    all_ok = True
    for remote in remotes:
        if not _remote_exists(remote):
            print("  [%s] 跳过(未配置)" % remote)
            continue
        _run(["git", "fetch", remote, branch])
        r = _run(["git", "rev-parse", "%s/%s" % (remote, branch)])
        rh = r.stdout.strip()
        same = rh == head
        all_ok = all_ok and same
        print("  [%s] remote=%s -> %s" % (remote, rh[:12] if rh else "?", "一致" if same else "不一致(待推送)"))
    return 0 if all_ok else 1


def _ensure_secrets():
    """跨平台自动装载凭据到环境变量（env > .secrets 文件 > macOS Keychain）。"""
    try:
        import load_secret as ls
    except Exception:
        return
    for n in ("gitee_token", "github_token"):
        try:
            u, t = ls.load(n)
        except Exception:
            continue
        if not t:
            continue
        key = n.upper()  # GITEE_TOKEN / GITHUB_TOKEN
        os.environ.setdefault(key, t)
        if u:
            os.environ.setdefault(key.replace("TOKEN", "USER"), u)


def main():
    _ensure_secrets()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    remotes = args if args else DEFAULT_REMOTES
    verify = "--verify" in sys.argv[1:]

    if verify:
        return _verify(remotes, _branch())

    branch = _branch()
    head = _head()
    now = datetime.datetime.now()
    seq = _next_seq()
    rows = []
    all_ok = True

    for remote in remotes:
        if not _remote_exists(remote):
            sid = "SYNC-%s-%03d" % (now.strftime("%Y%m%d"), seq)
            seq += 1
            rows.append([sid, now.strftime("%Y-%m-%d %H:%M:%S"), head[:12], remote, "",
                         "跳过(未配置)", "0.0", "remote 未配置，待用户在 Gitee 建仓后 git remote add mirror"])
            print("[跳过] %s：remote 未配置" % remote)
            continue
        url = _run(["git", "remote", "get-url", remote]).stdout.strip()
        ok, msg, elapsed = _push_one(remote, branch)
        status = "成功" if ok else "失败"
        all_ok = all_ok and ok
        sid = "SYNC-%s-%03d" % (now.strftime("%Y%m%d"), seq)
        seq += 1
        rows.append([sid, now.strftime("%Y-%m-%d %H:%M:%S"), head[:12], remote, _mask(url),
                     status, "%.1f" % elapsed, msg])
        print("[%s] %s：%s (%.1fs)" % (status, remote, msg, elapsed))
        if not ok:
            print("  详情：%s" % msg)

    _append_ledger(rows)
    print("\n台账已更新：%s" % LEDGER)
    print("本地 HEAD=%s  全部成功=%s" % (head[:12], all_ok))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    sys.exit(main())
