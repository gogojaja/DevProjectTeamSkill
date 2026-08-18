#!/usr/bin/env python3
# =============================================================================
# check_deprecation_cleanup.py — 废弃清理门禁校验（solidify 第 4 硬门禁）
#
# 规则（DevProjectTeamSkill §2.2-7 / AGENTS.md 铁律 #9）：
#   ADR 状态 = 废弃 后：
#     1) 任何后续会话启动必须先做「废弃资产完整性检查」（全库 grep + 端口/进程/LaunchAgent 三查）；
#     2) 基线固化阶段强制移除废弃资产，存在残留则中止固化（未通过不得固化）。
#
# 判定：
#   扫描架构资产 ADR（状态=废弃），对每个废弃资产做：
#     - 全库 grep：仓库内仍引用该资产名/标识；
#     - 端口三查：声明端口仍在监听 / 进程仍在运行 / LaunchAgent 仍加载；
#   任一残留 → exit 1（中止固化）；无废弃 ADR 或清理干净 → exit 0。
#
# 说明：当前仓库尚无 ADR 基础设施时，本门禁默认通过（前向兼容），
#      一旦存在 status=废弃 的 ADR 即自动生效。
# =============================================================================
import os, re, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXCLUDE_DIRS = {'.git', 'dist', 'skills_backup', 'node_modules', '__pycache__',
               '.github', '.claude', '.agents', 'build', '.venv', 'venv', 'skills_backup_v21.6.0'}
TEXT_EXT = {'.md', '.txt', '.py', '.sh', '.json', '.yaml', '.yml', '.toml',
            '.csv', '.js', '.ts', '.go', '.java', '.rb', '.rs', '.cfg', '.ini'}

STATUS_RE = re.compile(r'^\s*(状态|status)\s*[:：]\s*(.+?)\s*$', re.I)
ASSET_RE = re.compile(r'^\s*(资产|asset|资产名|asset[_ ]?name)\s*[:：]\s*(.+?)\s*$', re.I)
PORTS_RE = re.compile(r'^\s*(端口|port|ports)\s*[:：]\s*(.+?)\s*$', re.I)
PROC_RE = re.compile(r'^\s*(进程|process|process[_ ]?name|服务名|service)\s*[:：]\s*(.+?)\s*$', re.I)
LAUNCH_RE = re.compile(r'^\s*(launchagent|launchd|启动项|plist)\s*[:：]\s*(.+?)\s*$', re.I)

DEPRECATED_VALUES = {'废弃', 'deprecated', '弃用', 'obsolete', 'retired', 'archived'}


def find_adr_files():
    candidates = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        top = rel.split(os.sep)[0] if rel != '.' else ''
        if top in EXCLUDE_DIRS or top.startswith('skills_backup'):
            dirnames[:] = []
            continue
        for fn in filenames:
            low = fn.lower()
            if 'adr' in low and fn.endswith('.md'):
                candidates.append(os.path.join(dirpath, fn))
            elif low == 'adr' or low == 'adrs':
                for f in filenames:
                    if f.endswith('.md'):
                        candidates.append(os.path.join(dirpath, f))
    # 去重
    return list(dict.fromkeys(candidates))


def parse_adr(path):
    """返回 (status, asset, ports, procs, launches) 或 None。"""
    try:
        with open(path, encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except OSError:
        return None
    status = asset = None
    ports, procs, launches = [], [], []
    for ln in lines:
        m = STATUS_RE.match(ln)
        if m and status is None:
            status = m.group(2).strip()
        m = ASSET_RE.match(ln)
        if m and asset is None:
            asset = m.group(2).strip()
        m = PORTS_RE.match(ln)
        if m:
            ports += [p.strip() for p in re.split(r'[,;，；\s]+', m.group(2)) if p.strip()]
        m = PROC_RE.match(ln)
        if m:
            procs += [p.strip() for p in re.split(r'[,;，；\s]+', m.group(2)) if p.strip()]
        m = LAUNCH_RE.match(ln)
        if m:
            launches += [l.strip() for l in re.split(r'[,;，；\s]+', m.group(2)) if l.strip()]
    if status is None:
        return None
    if status.strip().lower() not in DEPRECATED_VALUES:
        return None
    return (status, asset, ports, procs, launches)


def repo_grep(asset):
    if not asset:
        return []
    hits = []
    pat = re.compile(re.escape(asset), re.I)
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        top = rel.split(os.sep)[0] if rel != '.' else ''
        if top in EXCLUDE_DIRS or top.startswith('skills_backup'):
            dirnames[:] = []
            continue
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, encoding='utf-8', errors='ignore') as f:
                    for i, ln in enumerate(f, 1):
                        if pat.search(ln):
                            hits.append('%s:%d: %s' % (os.path.relpath(fp, ROOT), i, ln.strip()[:120]))
                            if len(hits) >= 20:
                                return hits
            except OSError:
                continue
    return hits


def port_listening(port):
    try:
        r = subprocess.run(['lsof', '-nP', '-iTCP:%s' % port, '-sTCP:LISTEN'],
                           capture_output=True, text=True, timeout=10)
        return r.returncode == 0 and bool(r.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        # 非 macOS / lsof 缺失 → 退回 netstat
        try:
            r = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=10)
            return (':%s ' % port) in r.stdout
        except (OSError, subprocess.SubprocessError):
            return False


def process_running(name):
    try:
        r = subprocess.run(['pgrep', '-f', name], capture_output=True, text=True, timeout=10)
        return r.returncode == 0 and bool(r.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def launchagent_loaded(ident):
    try:
        r = subprocess.run(['launchctl', 'list'], capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and ident in r.stdout:
            return True
    except (OSError, subprocess.SubprocessError):
        pass
    # 检查 ~/Library/LaunchAgents 是否存在 plist
    p = os.path.expanduser('~/Library/LaunchAgents/%s.plist' % ident)
    if os.path.exists(p):
        return True
    return False


def main():
    adrs = find_adr_files()
    deprecated = []
    for p in adrs:
        info = parse_adr(p)
        if info:
            deprecated.append((p, info))

    if not deprecated:
        print('   ✓ 未发现 status=废弃 的 ADR，废弃清理门禁通过（前向兼容）')
        return 0

    print('   ⚠ 检测到 %d 个废弃 ADR，执行「废弃资产完整性检查」：' % len(deprecated))
    residuals = []
    for p, (status, asset, ports, procs, launches) in deprecated:
        print('     - %s (资产=%s)' % (os.path.relpath(p, ROOT), asset or '未声明'))

        # 全库 grep
        if asset:
            hits = repo_grep(asset)
            # 排除 ADR 自身声明
            hits = [h for h in hits if os.path.relpath(p, ROOT) not in h]
            if hits:
                residuals.append('[%s] 全库仍引用废弃资产「%s」：' % (os.path.relpath(p, ROOT), asset))
                residuals += ['       ' + h for h in hits[:5]]

        # 端口三查
        for port in ports:
            if port_listening(port):
                residuals.append('[%s] 端口 %s 仍在监听（应已释放）' % (os.path.relpath(p, ROOT), port))
        for name in procs:
            if process_running(name):
                residuals.append('[%s] 进程「%s」仍在运行（应已停止）' % (os.path.relpath(p, ROOT), name))
        for ident in launches:
            if launchagent_loaded(ident):
                residuals.append('[%s] LaunchAgent「%s」仍加载（应已卸载）' % (os.path.relpath(p, ROOT), ident))

    if residuals:
        print('   ✗ 废弃清理门禁未通过，中止固化。请先彻底移除以下废弃资产残留：', file=sys.stderr)
        for line in residuals:
            print('     ' + line, file=sys.stderr)
        print('   处置：移除仓库引用 → 停止进程/释放端口/卸载 LaunchAgent → 重新 solidify。', file=sys.stderr)
        return 1

    print('   ✓ 废弃资产完整性检查通过（引用/端口/进程/LaunchAgent 均无残留）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
