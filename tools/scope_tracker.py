#!/usr/bin/env python3
# =============================================================================
# scope_tracker.py — 项目范围跟踪与范围基准工具
#
# 依据：references/traceability_standard.md v1.1.1
#       对齐 PMBOK 范围管理 / IEEE 29148 / ISO 21500 / MoSCoW / CCB
# 版本：v1.1.1（2026-08-25 审计整改：gate 结论留痕/健康分门禁/fail-closed/蔓延补 MOD·TC 孤儿/快照去重口径）
#
# 子命令：
#   init    初始化《需求-架构-代码追溯矩阵》(扩展 RTM) 与 06/07 范围台账（含表头）
#   metrics 计算覆盖度指标 + 范围健康分（打印；可选 --write 写 07 快照）
#   gate    范围门禁：一致性 + 蔓延/缩水检测 + 健康分，写 07_范围跟踪台账.csv，结论 exit
#   change  登记变更请求（五维影响），追加 06_范围变更台账.csv
#
# 复用：内部调用 tools/check_traceability.py 的 load_matrix / analyze 做一致性校验
# 用法：
#   python3 tools/scope_tracker.py init
#   python3 tools/scope_tracker.py metrics [--write]
#   python3 tools/scope_tracker.py gate [--max-violations 0] [--min-health 90]
#   python3 tools/scope_tracker.py change --req REQ-001 --title "..." --type 范围调整 \
#          --impact-scope 高 --severity 主要 --approver 用户 --baseline-from v1.0.0 --baseline-to v1.0.1
# =============================================================================
import os
import sys
import csv
import argparse
import datetime

# --- 项目根解析（修复部署副本场景 ROOT 错位）---
# 部署副本（如 ~/.workbuddy/skills/tools/）下，dirname(dirname(__file__)) 会指向
# 技能库目录而非真实项目，导致读写错误的 台账/。按以下优先级解析真实项目根：
#   1) --root 显式指定  2) 环境变量 PROJECT_ROOT / DPB_ROOT
#   3) 从当前工作目录向上寻找项目标记  4) 从脚本目录向上寻找
#   5) 兜底旧语义 dirname(dirname(__file__))
_PROJECT_MARKERS = ('台账', 'AGENTS.md', 'SKILL_INDEX.md', '交接文档.md', 'dev-project-team-skill')


def _looks_like_project_root(d):
    return any(os.path.exists(os.path.join(d, m)) for m in _PROJECT_MARKERS)


def find_project_root(explicit=None):
    cand = explicit or os.environ.get('PROJECT_ROOT') or os.environ.get('DPB_ROOT')
    if cand and os.path.isdir(cand):
        return os.path.abspath(cand)
    d = os.path.abspath(os.getcwd())
    while True:
        if _looks_like_project_root(d):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    d = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
    while True:
        if _looks_like_project_root(d):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ROOT = find_project_root()
DEFAULT_MATRIX = os.path.join(ROOT, '台账', '需求-架构-代码追溯矩阵.csv')
DEFAULT_CHANGE = os.path.join(ROOT, '台账', '06_范围变更台账.csv')
DEFAULT_TRACK = os.path.join(ROOT, '台账', '07_范围跟踪台账.csv')

# 原有一致性门禁要求的 5 列（向后兼容）
BASE_COLS = ['REQ_ID', 'REQ_TITLE', 'AE_ID', 'MOD_ID', 'TC_ID']
# 扩展 RTM 维度（范围跟踪）
EXT_COLS = ['PRIORITY', 'SCOPE_STATUS', 'BASELINE_VER', 'SOURCE', 'VERIFY_METHOD', 'CHANGE_REFS']
RTM_COLS = BASE_COLS + EXT_COLS

CHANGE_COLS = ['CHANGE_ID', 'REQ_IDS', 'TITLE', 'TYPE', 'SOURCE', 'IMPACT_SCOPE',
               'IMPACT_SCHEDULE', 'IMPACT_COST', 'IMPACT_QUALITY', 'IMPACT_SECURITY',
               'SEVERITY', 'STATUS', 'APPROVER', 'BASELINE_FROM', 'BASELINE_TO',
               'PROPOSED_AT', 'DECIDED_AT', 'NOTE']

TRACK_COLS = ['SNAPSHOT_ID', 'BASELINE_VER', 'SNAPSHOT_AT', 'REQ_TOTAL', 'REQ_IMPL',
              'REQ_VERIFIED', 'AE_TOTAL', 'MOD_TOTAL', 'TC_TOTAL', 'ORPHAN_COUNT',
              'CREEP_ITEMS', 'SHRINK_ITEMS', 'COVERAGE_REQ_AE_PCT', 'COVERAGE_REQ_TC_PCT',
              'HEALTH_SCORE', 'GATE_RESULT', 'DETAIL']

STATUS_IMPL = {'Implemented', 'Verified', 'Closed'}
STATUS_VER = {'Verified', 'Closed'}


def split_ids(cell):
    if not cell:
        return []
    return [x.strip() for x in str(cell).replace(';', ',').split(',') if x.strip()]


def load_rtm(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        missing = [c for c in BASE_COLS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError('追溯矩阵缺少基础列: %s（应为 %s）' % (','.join(missing), ','.join(BASE_COLS)))
        return list(reader)


def consistency_violations(matrix_path, fail_closed=False):
    """复用 check_traceability 的 analyze 计算孤儿/断链违规数。

    返回 (violations, ok)。fail_closed=True 时校验异常返回 (None, False)，
    供 gate 驳回（防门禁假绿）；False 时降级返回 ([], False)，不影响 metrics 指标。
    """
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'check_traceability', os.path.join(os.path.dirname(__file__), 'check_traceability.py'))
        ct = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ct)
        rows = ct.load_matrix(matrix_path)
        violations, _ = ct.analyze(rows)
        return violations, True
    except Exception as e:
        if fail_closed:
            print('   ✗ 一致性校验模块异常（门禁 fail-closed）: %s' % e, file=sys.stderr)
            return None, False
        print('   ⚠ 一致性校验模块不可用: %s' % e, file=sys.stderr)
        return [], False


def compute_metrics(rows):
    req_rows = [r for r in rows if split_ids(r.get('REQ_ID'))]
    n = len(req_rows)
    with_ae = with_tc = impl = ver = 0
    status_dist, prio_dist = {}, {}
    for r in req_rows:
        reqs = split_ids(r.get('REQ_ID'))
        aes = split_ids(r.get('AE_ID'))
        tcs = split_ids(r.get('TC_ID'))
        st = (r.get('SCOPE_STATUS') or '').strip()
        pr = (r.get('PRIORITY') or '').strip()
        if aes:
            with_ae += 1
        if tcs:
            with_tc += 1
        if st in STATUS_IMPL:
            impl += 1
        if st in STATUS_VER:
            ver += 1
        status_dist[st or '未填'] = status_dist.get(st or '未填', 0) + 1
        prio_dist[pr or '未填'] = prio_dist.get(pr or '未填', 0) + 1
    cov_ae = round(with_ae / n * 100, 1) if n else 0.0
    cov_tc = round(with_tc / n * 100, 1) if n else 0.0
    impl_pct = round(impl / n * 100, 1) if n else 0.0
    ver_pct = round(ver / n * 100, 1) if n else 0.0
    return {
        'req_total': n, 'with_ae': with_ae, 'with_tc': with_tc,
        'impl': impl, 'ver': ver,
        'cov_ae': cov_ae, 'cov_tc': cov_tc, 'impl_pct': impl_pct, 'ver_pct': ver_pct,
        'status_dist': status_dist, 'prio_dist': prio_dist,
    }


def detect_creep_shrink(rows):
    """启发式：gold-plating(蔓延) 与 scope-shrink(缩水)。"""
    creep, shrink = [], []
    req_rows = [r for r in rows if split_ids(r.get('REQ_ID'))]
    for r in req_rows:
        reqs = split_ids(r.get('REQ_ID'))
        st = (r.get('SCOPE_STATUS') or '').strip()
        pr = (r.get('PRIORITY') or '').strip()
        aes = split_ids(r.get('AE_ID'))
        tcs = split_ids(r.get('TC_ID'))
        mods = split_ids(r.get('MOD_ID'))
        # 缩水：Must 且已进入基线/开发/实现/验证/关闭，却缺 MOD 或 TC
        if pr == 'Must' and st in {'Baselined', 'InProgress', 'Implemented', 'Verified', 'Closed'}:
            if not mods:
                shrink.append('%s 缺实现(MOD)' % ','.join(reqs))
            if not tcs:
                shrink.append('%s 缺验证(TC)' % ','.join(reqs))
        # 蔓延：Won't 却已实现/验证
        if pr == "Won't" and st in STATUS_IMPL:
            creep.append('%s Won\'t 却已%s' % (','.join(reqs), st))
    # 蔓延：AE/MOD/TC 未关联到任何有 REQ 的行（悬空新增能力）
    ae_seen, mod_seen, tc_seen = set(), set(), set()
    ae_to_req, mod_to_ae, tc_to_req = {}, {}, {}
    for r in rows:
        for ae in split_ids(r.get('AE_ID')):
            ae_seen.add(ae); ae_to_req.setdefault(ae, set()).update(split_ids(r.get('REQ_ID')))
        for mod in split_ids(r.get('MOD_ID')):
            mod_seen.add(mod)
        for tc in split_ids(r.get('TC_ID')):
            tc_seen.add(tc); tc_to_req.setdefault(tc, set()).update(split_ids(r.get('REQ_ID')))
    for ae in ae_seen:
        if not ae_to_req.get(ae):
            creep.append('%s 孤儿架构(无回溯需求)' % ae)
    # MOD/TC 孤儿（悬空新增能力 = 蔓延，v1.1.1 审计整改补全）
    mod_to_ae = {}
    for r in rows:
        for mod in split_ids(r.get('MOD_ID')):
            mod_to_ae.setdefault(mod, set()).update(split_ids(r.get('AE_ID')))
    for mod in mod_seen:
        if not mod_to_ae.get(mod):
            creep.append('%s 孤儿代码(无归属架构)' % mod)
    for tc in tc_seen:
        if not tc_to_req.get(tc):
            creep.append('%s 孤儿测试(无回溯需求)' % tc)
    return creep, shrink


def health_score(m, violations, creep, shrink):
    score = 100.0
    n = m['req_total'] or 1
    score -= (m['req_total'] - m['with_ae']) / n * 100 * 0.2
    score -= (m['req_total'] - m['with_tc']) / n * 100 * 0.2
    score -= len(violations) * 2
    score -= len(creep) * 1.5
    score -= len(shrink) * 3
    return max(0.0, round(score, 1))


def print_scorecard(m, violations, creep, shrink, health):
    print('   ── 范围健康分卡 ──')
    print('   需求总数=%d  需求→架构覆盖=%d (%s%%)  需求→测试覆盖=%d (%s%%)'
          % (m['req_total'], m['with_ae'], m['cov_ae'], m['with_tc'], m['cov_tc']))
    print('   实现率=%s%%  验证率=%s%%' % (m['impl_pct'], m['ver_pct']))
    print('   一致性违规=%d  蔓延项=%d  缩水项=%d' % (len(violations), len(creep), len(shrink)))
    print('   状态分布=%s' % m['status_dist'])
    print('   优先级分布=%s' % m['prio_dist'])
    print('   范围健康分=%.1f' % health)


def ensure_header(path, cols):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    if not os.path.isfile(path):
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            csv.writer(f).writerow(cols)
        print('   ✓ 已初始化台账(表头): %s' % path)


def reconcile_ledger_header(path, cols, force):
    """若台账已存在且表头与预期 schema 不一致：无数据行时安全重写表头；含数据则仅告警，防丢失。"""
    if not os.path.isfile(path):
        return
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    header = rows[0] if rows else []
    if [c.strip() for c in header] == [c.strip() for c in cols]:
        return  # 已一致
    data_rows = [r for r in rows[1:] if any(str(c).strip() for c in r)]
    if not data_rows:
        # 仅表头（无数据）：安全重写
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            csv.writer(f).writerow(cols)
        print('   ✓ 已按 scope_tracker schema 重写表头(无数据,安全): %s' % path)
    elif force:
        print('   ⚠ 含 %d 行数据，拒绝强制重写以防丢失（请先备份）: %s' % (len(data_rows), path))
    else:
        print('   ⚠ 台账表头与 scope_tracker 预期 schema 不一致(含 %d 行数据,未改写): %s' % (len(data_rows), path))
        print('     预期 %d 列: %s' % (len(cols), ','.join(cols)))
        print('     实际 %d 列: %s' % (len(header), ','.join(h.strip() for h in header)))


def cmd_init(args):
    ensure_header(DEFAULT_MATRIX, RTM_COLS)
    with open(DEFAULT_MATRIX, encoding='utf-8-sig', newline='') as f:
        has = bool(list(csv.reader(f))[1:] if os.path.getsize(DEFAULT_MATRIX) > 3 else [])
    if not has:
        with open(DEFAULT_MATRIX, 'a', encoding='utf-8-sig', newline='') as f:
            csv.writer(f).writerow(
                ['REQ-001', '示例需求', 'AE-001', 'MOD-001', 'TC-001',
                 'Must', 'Proposed', 'v1.0.0', '示例来源', 'TC-001', ''])
        print('   ✓ 已写入 RTM 示例行')
    ensure_header(DEFAULT_CHANGE, CHANGE_COLS)
    ensure_header(DEFAULT_TRACK, TRACK_COLS)
    # schema 对齐自检：已存在但表头不符时安全重写（仅表头）或告警（含数据）
    reconcile_ledger_header(DEFAULT_MATRIX, RTM_COLS, args.reset_ledgers)
    reconcile_ledger_header(DEFAULT_CHANGE, CHANGE_COLS, args.reset_ledgers)
    reconcile_ledger_header(DEFAULT_TRACK, TRACK_COLS, args.reset_ledgers)
    print('   ✓ 范围跟踪机制初始化完成（RTM + 06/07 台账）')
    return 0


def cmd_metrics(args):
    if not os.path.isfile(DEFAULT_MATRIX):
        print('   ✗ 未找到追溯矩阵，请先运行: python3 tools/scope_tracker.py init', file=sys.stderr)
        return 1
    rows = load_rtm(DEFAULT_MATRIX)
    if not rows:
        print('   ✗ 追溯矩阵为空', file=sys.stderr)
        return 1
    m = compute_metrics(rows)
    violations, _ = consistency_violations(DEFAULT_MATRIX)
    creep, shrink = detect_creep_shrink(rows)
    health = health_score(m, violations, creep, shrink)
    print_scorecard(m, violations, creep, shrink, health)
    if args.write:
        ensure_header(DEFAULT_TRACK, TRACK_COLS)
        _write_snapshot(m, violations, creep, shrink, health, '指标快照')
        print('   ✓ 已写范围快照到 %s' % DEFAULT_TRACK)
    return 0


def _write_snapshot(m, violations, creep, shrink, health, detail, gate_result='指标快照'):
    baseline_ver = '—'
    rows = load_rtm(DEFAULT_MATRIX)
    vers = [r.get('BASELINE_VER', '').strip() for r in rows if (r.get('BASELINE_VER') or '').strip()]
    if vers:
        baseline_ver = Versorted(vers)
    # 元素总数 = 去重计数（v1.1.1 审计整改，原为"含该列的行数"口径误导）
    ae_uniq, mod_uniq, tc_uniq = set(), set(), set()
    for r in rows:
        ae_uniq.update(split_ids(r.get('AE_ID')))
        mod_uniq.update(split_ids(r.get('MOD_ID')))
        tc_uniq.update(split_ids(r.get('TC_ID')))
    sid = 'SN-%s' % datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    row = [sid, baseline_ver, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
           m['req_total'], m['impl'], m['ver'],
           len(ae_uniq), len(mod_uniq), len(tc_uniq),
           len(violations), len(creep), len(shrink),
           m['cov_ae'], m['cov_tc'], health,
           gate_result, detail]
    with open(DEFAULT_TRACK, 'a', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerow(row)


def Versorted(vers):
    try:
        return sorted(vers, key=lambda v: [int(x) for x in v.lstrip('v').split('.')])[-1]
    except Exception:
        return sorted(vers)[-1]


def cmd_gate(args):
    if not os.path.isfile(DEFAULT_MATRIX):
        print('   ✗ 未找到追溯矩阵，请先运行: python3 tools/scope_tracker.py init', file=sys.stderr)
        return 1
    try:
        rows = load_rtm(DEFAULT_MATRIX)
    except Exception as e:
        print('   ✗ 追溯矩阵异常（fail-closed）: %s' % e, file=sys.stderr)
        return 2
    if not rows:
        print('   ✗ 追溯矩阵为空', file=sys.stderr)
        return 1
    m = compute_metrics(rows)
    violations, ok = consistency_violations(DEFAULT_MATRIX, fail_closed=True)
    if not ok:
        # 一致性校验异常：fail-closed 驳回（防门禁假绿），exit 2
        _write_snapshot(m, [], [], [], 0.0, '一致性校验异常-fail-closed', '驳回')
        print('   范围门禁结论: 驳回（一致性校验异常，fail-closed，exit 2）', file=sys.stderr)
        return 2
    creep, shrink = detect_creep_shrink(rows)
    health = health_score(m, violations, creep, shrink)
    print_scorecard(m, violations, creep, shrink, health)

    severe = (len(violations) > args.max_violations or len(shrink) > 0
              or health < args.min_health)  # v1.1.1：健康分门禁（标准 §8 ≥90）
    warn = len(creep) > 0 or (0 < len(violations) <= args.max_violations)
    result = '通过' if not severe and not warn else ('驳回' if severe else '警告')
    detail = '违规%d/蔓延%d/缩水%d/健康%.1f' % (len(violations), len(creep), len(shrink), health)
    ensure_header(DEFAULT_TRACK, TRACK_COLS)
    _write_snapshot(m, violations, creep, shrink, health, detail, result)  # v1.1.1：门禁结论留痕
    print('   范围门禁结论: %s（写 %s）' % (result, DEFAULT_TRACK))
    return 1 if result == '驳回' else 0


def cmd_change(args):
    ensure_header(DEFAULT_CHANGE, CHANGE_COLS)
    existing = []
    with open(DEFAULT_CHANGE, encoding='utf-8-sig', newline='') as f:
        existing = [r for r in csv.DictReader(f)]
    n = len(existing) + 1
    cid = 'CR-%03d' % n
    row = [cid, args.req, args.title, args.type, args.source,
           args.impact_scope, args.impact_schedule, args.impact_cost,
           args.impact_quality, args.impact_security,
           args.severity, '提出', args.approver, args.baseline_from,
           args.baseline_to, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
           '', args.note]
    with open(DEFAULT_CHANGE, 'a', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerow(row)
    print('   ✓ 已登记变更请求 %s → %s' % (cid, DEFAULT_CHANGE))
    return 0


def main():
    ap = argparse.ArgumentParser(description='项目范围跟踪与范围基准工具')
    ap.add_argument('--root', default=None,
                    help='显式指定项目根目录（含 台账/ 的目录）；默认自动探测（CWD/脚本目录向上查找项目标记）')
    sub = ap.add_subparsers(dest='cmd')

    p_init = sub.add_parser('init', help='初始化 RTM 与 06/07 范围台账')
    p_init.add_argument('--reset-ledgers', action='store_true',
                        help='若 06/07/RTM 已存在但表头不一致且无数据行，安全重写表头')
    p_m = sub.add_parser('metrics', help='计算覆盖度指标与健康分')
    p_m.add_argument('--write', action='store_true', help='同时写 07 范围跟踪台账快照')
    p_g = sub.add_parser('gate', help='范围门禁（一致性+蔓延/缩水+健康分）')
    p_g.add_argument('--max-violations', type=int, default=0)
    p_g.add_argument('--min-health', type=float, default=90, help='健康分门禁阈值（默认 90，低于则驳回）')
    p_c = sub.add_parser('change', help='登记变更请求')
    p_c.add_argument('--req', required=True, help='关联需求 ID（多值逗号分隔）')
    p_c.add_argument('--title', required=True, help='变更标题')
    p_c.add_argument('--type', default='范围调整', help='类型(范围调整/接口变化/合规新规/新诉求/缺陷澄清/其他)')
    p_c.add_argument('--source', default='用户诉求', help='变更来源')
    p_c.add_argument('--impact-scope', default='', help='范围影响')
    p_c.add_argument('--impact-schedule', default='', help='进度影响')
    p_c.add_argument('--impact-cost', default='', help='成本影响')
    p_c.add_argument('--impact-quality', default='', help='质量影响')
    p_c.add_argument('--impact-security', default='', help='安全影响')
    p_c.add_argument('--severity', default='主要', help='严重度(轻微/主要/严重)')
    p_c.add_argument('--approver', default='', help='审批人')
    p_c.add_argument('--baseline-from', default='', help='基准版本(前)')
    p_c.add_argument('--baseline-to', default='', help='基准版本(后)')
    p_c.add_argument('--note', default='', help='备注')

    args = ap.parse_args()
    if getattr(args, 'root', None):
        global ROOT, DEFAULT_MATRIX, DEFAULT_CHANGE, DEFAULT_TRACK
        ROOT = find_project_root(args.root)
        DEFAULT_MATRIX = os.path.join(ROOT, '台账', '需求-架构-代码追溯矩阵.csv')
        DEFAULT_CHANGE = os.path.join(ROOT, '台账', '06_范围变更台账.csv')
        DEFAULT_TRACK = os.path.join(ROOT, '台账', '07_范围跟踪台账.csv')
    if args.cmd == 'init':
        return cmd_init(args)
    if args.cmd == 'metrics':
        return cmd_metrics(args)
    if args.cmd == 'gate':
        return cmd_gate(args)
    if args.cmd == 'change':
        return cmd_change(args)
    ap.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
