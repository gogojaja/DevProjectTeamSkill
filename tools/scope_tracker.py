#!/usr/bin/env python3
# =============================================================================
# scope_tracker.py — 项目范围跟踪与范围基准工具
#
# 依据：references/traceability_standard.md v1.2.0（§8.1 健康分精确模型 / §9 变更生命周期·基线冻结比对）
#       对齐 PMBOK 7th 范围管理 / 实施整体变更控制(CCB) / IEEE 29148 / ISO 21500 / ITIL v4 变更使能 / MoSCoW
# 版本：v1.2.0（2026-09-08 最佳实践升级：F1 UTF-8 输出防护 / F2 变更生命周期状态机
#       change-decide + 审批回写基线 / F3 门禁集成变更台账合规 / F4 基线冻结与真实
#       蔓延缩水比对 baseline freeze·diff / F6 需求易变性 KPI + report --json；向后兼容 v1.1.1）
# 版本：v1.1.1（2026-08-25 审计整改：gate 结论留痕/健康分门禁/fail-closed/蔓延补 MOD·TC 孤儿/快照去重口径）
#
# 子命令：
#   init    初始化《需求-架构-代码追溯矩阵》(扩展 RTM) 与 06/07 范围台账（含表头）
#   metrics 计算覆盖度指标 + 范围健康分 + 需求易变性 KPI（打印；可选 --write 写 07 快照）
#   gate    范围门禁：一致性 + 蔓延/缩水 + 变更台账合规 + 健康分，写 07_范围跟踪台账.csv，结论 exit
#   change  登记变更请求（五维影响），追加 06_范围变更台账.csv（状态=提出）
#   change-decide  推进变更生命周期（分析中/已批准/已驳回/已实施/已关闭）；批准时回写 RTM 基线版本+CHANGE_REFS
#   baseline  范围基准冻结(freeze)与差异比对(diff)：识别相对已批准基线的真实蔓延/缩水
#   report  范围状态综合报告（指标+变更+基线漂移+门禁预演）；--json 供 MCP/PMO 消费
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
import json
import argparse
import datetime

# Windows 控制台 UTF-8 输出（修复 GBK 下打印 ✓/⚠ 触发 UnicodeEncodeError 崩溃，v1.2.0）
# 与仓库内 req_quality.py / pmo_dashboard.py 等同类工具防护惯例一致。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

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
# 范围基准快照（F4）：freeze 全量写入该版本 REQ 集，diff 据此比对真实蔓延/缩水
DEFAULT_BASELINE = os.path.join(ROOT, '台账', '范围基准快照.csv')

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

# 范围基准快照（F4 真实蔓延/缩水比对锚点；append-only，每次 freeze 全量写入该版本 REQ 集）
BASELINE_COLS = ['BASELINE_VER', 'FROZEN_AT', 'REQ_ID', 'PRIORITY', 'SCOPE_STATUS',
                 'AE_ID', 'MOD_ID', 'TC_ID']

STATUS_IMPL = {'Implemented', 'Verified', 'Closed'}
STATUS_VER = {'Verified', 'Closed'}

# --- 变更生命周期状态机（F2，对齐 PMBOK 实施整体变更控制 / ITIL v4 变更使能）---
# 提出 → 分析中 → {已批准 | 已驳回} ；已批准 → 已实施 → 已关闭
CHANGE_STATUS_PROPOSED = '提出'
CHANGE_STATUS_ANALYZING = '分析中'
CHANGE_STATUS_APPROVED = '已批准'
CHANGE_STATUS_REJECTED = '已驳回'
CHANGE_STATUS_IMPLEMENTED = '已实施'
CHANGE_STATUS_CLOSED = '已关闭'
# 未决（尚未形成审批结论）状态：触及 Must/基线需求时构成范围门禁风险
CHANGE_OPEN_STATES = {CHANGE_STATUS_PROPOSED, CHANGE_STATUS_ANALYZING}
# 允许的 decide 目标状态
CHANGE_DECIDE_STATES = {CHANGE_STATUS_ANALYZING, CHANGE_STATUS_APPROVED,
                        CHANGE_STATUS_REJECTED, CHANGE_STATUS_IMPLEMENTED,
                        CHANGE_STATUS_CLOSED}
# 已判定（有决策结论）状态
CHANGE_DECIDED_STATES = {CHANGE_STATUS_APPROVED, CHANGE_STATUS_REJECTED,
                         CHANGE_STATUS_IMPLEMENTED, CHANGE_STATUS_CLOSED}

# 影响/严重度受控枚举（F2 参照完整性校验，非法值仅告警不阻断，容忍历史自由文本）
IMPACT_ENUM = {'高', '中', '低', ''}
SEVERITY_ENUM = {'轻微', '主要', '严重'}

# CR 超期未决阈值（天）：提出/分析中且 PROPOSED_AT 早于该阈值 → stale（F3/F6）
STALE_CR_DAYS = 14


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


def _find_check_traceability():
    """定位共享工具 check_traceability.py（三方一致性校验）。

    兼容两种布局：
      1) 自包含技能部署：与本脚本同级目录（打包/部署时注入副本）；
      2) 仓库内单一信源：项目根 tools/（本脚本位于 .trae/skills/scope-tracking/tools/ 时上溯命中）。
    返回绝对路径或 None（未找到）。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [os.path.join(here, 'check_traceability.py'),
             os.path.join(ROOT, 'tools', 'check_traceability.py')]
    proot = os.environ.get('PROJECT_ROOT') or os.environ.get('DPB_ROOT')
    if proot:
        cands.append(os.path.join(proot, 'tools', 'check_traceability.py'))
    d = here
    for _ in range(8):  # 上溯查找 tools/check_traceability.py（部署副本场景）
        cands.append(os.path.join(d, 'tools', 'check_traceability.py'))
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    for c in cands:
        if os.path.isfile(c):
            return os.path.abspath(c)
    return None


def consistency_violations(matrix_path, fail_closed=False):
    """复用 check_traceability 的 analyze 计算孤儿/断链违规数。

    返回 (violations, ok)。fail_closed=True 时校验异常/模块缺失返回 (None, False)，
    供 gate 驳回（防门禁假绿）；False 时降级返回 ([], False)，不影响 metrics 指标。
    """
    try:
        import importlib.util
        ct_path = _find_check_traceability()
        if not ct_path:
            raise FileNotFoundError('未找到 check_traceability.py（已搜同级目录/项目根 tools/上溯）')
        spec = importlib.util.spec_from_file_location('check_traceability', ct_path)
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


def health_score(m, violations, creep, shrink, change_signals=None):
    """范围健康分（0~100，权威公式见 traceability_standard.md §8）。

    基准 100，逐项扣减：
      覆盖缺口  -0.2 × 未映射架构(AE)的需求占比%   -0.2 × 未被测试(TC)验证的需求占比%
      一致性    -2   × 违规数（断链/孤儿）
      蔓延      -1.5 × 项（gold-plating / 孤儿能力）
      缩水      -3   × 项（Must 缺实现/验证）
      变更信号  （change_signals 非空时，F3）：
                -4 × 未审批变更触及 Must/基线需求(open_unapproved_must)
                -2 × 相对冻结基线的净漂移(baseline_drift)
                -2 × 已判定 CR 缺审批人(missing_approver)
                -1 × 超期未决 CR(stale_cr)
    change_signals=None（默认）时与 v1.1.1 完全一致，保证向后兼容。
    """
    score = 100.0
    n = m['req_total'] or 1
    score -= (m['req_total'] - m['with_ae']) / n * 100 * 0.2
    score -= (m['req_total'] - m['with_tc']) / n * 100 * 0.2
    score -= len(violations) * 2
    score -= len(creep) * 1.5
    score -= len(shrink) * 3
    if change_signals:
        score -= change_signals.get('open_unapproved_must', 0) * 4
        score -= change_signals.get('baseline_drift', 0) * 2
        score -= change_signals.get('missing_approver', 0) * 2
        score -= change_signals.get('stale_cr', 0) * 1
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


# =============================================================================
# F2/F3/F4/F6 升级：变更生命周期状态机 · 变更台账合规 · 基线冻结与比对 · 易变性 KPI
# =============================================================================
_PRIO_RANK = {'Must': 3, 'Should': 2, 'Could': 1, "Won't": 0, 'Wont': 0}
ADVANCED_STATES = {'Baselined', 'InProgress', 'Implemented', 'Verified', 'Closed'}


def _prio_rank(p):
    return _PRIO_RANK.get((p or '').strip(), -1)


def _now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _parse_dt(s):
    s = (s or '').strip()
    if not s:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _req_index(rows):
    """RTM 展开为 req_id → {priority,status,ae,mod,tc}（多值 REQ_ID 行按单需求拆分）。"""
    idx = {}
    for r in rows:
        for req in split_ids(r.get('REQ_ID')):
            idx[req] = {
                'priority': (r.get('PRIORITY') or '').strip(),
                'status': (r.get('SCOPE_STATUS') or '').strip(),
                'ae': r.get('AE_ID', ''), 'mod': r.get('MOD_ID', ''), 'tc': r.get('TC_ID', ''),
            }
    return idx


def load_change_ledger(path=None):
    path = path or DEFAULT_CHANGE
    if not os.path.isfile(path):
        return []
    with open(path, encoding='utf-8-sig', newline='') as f:
        return [r for r in csv.DictReader(f)]


def _write_change_ledger(rows):
    ensure_header(DEFAULT_CHANGE, CHANGE_COLS)
    with open(DEFAULT_CHANGE, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CHANGE_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in CHANGE_COLS})


def _read_rtm_raw(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return (reader.fieldnames or []), list(reader)


def _write_rtm_raw(path, fields, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})


def update_change_status(cid, status, approver='', baseline_to='', note=''):
    """推进变更生命周期（F2）。返回 (ok, msg, cr)。"""
    changes = load_change_ledger()
    target = next((r for r in changes if (r.get('CHANGE_ID') or '').strip() == cid), None)
    if target is None:
        return False, '未找到变更请求 %s' % cid, None
    if status not in CHANGE_DECIDE_STATES:
        return False, '非法目标状态 %s（可选 %s）' % (status, '/'.join(sorted(CHANGE_DECIDE_STATES))), target
    if (target.get('STATUS') or '').strip() == CHANGE_STATUS_CLOSED:
        return False, '%s 已关闭，禁止再变更状态' % cid, target
    target['STATUS'] = status
    if status in CHANGE_DECIDED_STATES:
        target['DECIDED_AT'] = _now()
    if approver:
        target['APPROVER'] = approver
    if baseline_to:
        target['BASELINE_TO'] = baseline_to
    if note:
        old = (target.get('NOTE') or '').strip()
        target['NOTE'] = (old + ' | ' + note) if old else note
    _write_change_ledger(changes)
    return True, '已更新 %s → %s' % (cid, status), target


def apply_baseline_writeback(req_ids, baseline_to, change_id):
    """审批通过后回写 RTM：受影响 REQ 行升级 BASELINE_VER + 追加 CHANGE_REFS（F2，落实 scope-change §环节2）。"""
    if not os.path.isfile(DEFAULT_MATRIX):
        return 0
    req_set = set(split_ids(req_ids))
    if not req_set:
        return 0
    fields, rows = _read_rtm_raw(DEFAULT_MATRIX)
    if 'BASELINE_VER' not in fields or 'CHANGE_REFS' not in fields:
        return 0
    n = 0
    for r in rows:
        if set(split_ids(r.get('REQ_ID'))) & req_set:
            if baseline_to:
                r['BASELINE_VER'] = baseline_to
            refs = split_ids(r.get('CHANGE_REFS'))
            if change_id and change_id not in refs:
                refs.append(change_id)
                r['CHANGE_REFS'] = ','.join(refs)
            n += 1
    if n:
        _write_rtm_raw(DEFAULT_MATRIX, fields, rows)
    return n


def analyze_change_signals(rows, changes, baseline_drift=0):
    """变更台账合规信号（F3）：未审批触及 Must/基线、缺审批人、超期未决。"""
    protected = set()
    for r in rows:
        pr = (r.get('PRIORITY') or '').strip()
        st = (r.get('SCOPE_STATUS') or '').strip()
        bv = (r.get('BASELINE_VER') or '').strip()
        if pr == 'Must' or bv or st in ADVANCED_STATES:
            protected.update(split_ids(r.get('REQ_ID')))
    open_unapproved_must = missing_approver = stale_cr = open_cr = 0
    now = datetime.datetime.now()
    for c in changes:
        st = (c.get('STATUS') or '').strip()
        if st in CHANGE_OPEN_STATES:
            open_cr += 1
            if set(split_ids(c.get('REQ_IDS'))) & protected:
                open_unapproved_must += 1
            pd = _parse_dt(c.get('PROPOSED_AT'))
            if pd and (now - pd).days > STALE_CR_DAYS:
                stale_cr += 1
        elif st in {CHANGE_STATUS_APPROVED, CHANGE_STATUS_IMPLEMENTED, CHANGE_STATUS_CLOSED}:
            if not (c.get('APPROVER') or '').strip():
                missing_approver += 1
    return {'open_unapproved_must': open_unapproved_must, 'missing_approver': missing_approver,
            'stale_cr': stale_cr, 'baseline_drift': baseline_drift, 'open_cr': open_cr}


def volatility_metrics(rows, changes):
    """范围稳定性/需求易变性 KPI（F6，对齐 IEEE 需求易变性度量 + PMO 口径）。"""
    all_reqs = set(_req_index(rows).keys())
    changed_reqs = set()
    for c in changes:
        changed_reqs.update(split_ids(c.get('REQ_IDS')))
    now = datetime.datetime.now()
    ages, open_cr, approved, rejected = [], 0, 0, 0
    for c in changes:
        st = (c.get('STATUS') or '').strip()
        if st in CHANGE_OPEN_STATES:
            open_cr += 1
            pd = _parse_dt(c.get('PROPOSED_AT'))
            if pd:
                ages.append(max(0, (now - pd).days))
        elif st == CHANGE_STATUS_REJECTED:
            rejected += 1
        elif st in CHANGE_DECIDED_STATES:
            approved += 1
    inter = changed_reqs & all_reqs
    return {
        'req_total': len(all_reqs),
        'changed_reqs': len(inter),
        'req_volatility_pct': round(len(inter) / len(all_reqs) * 100, 1) if all_reqs else 0.0,
        'cr_total': len(changes), 'open_cr': open_cr, 'approved_cr': approved, 'rejected_cr': rejected,
        'avg_open_cr_age_days': round(sum(ages) / len(ages), 1) if ages else 0.0,
        'cr_per_req': round(len(changes) / len(all_reqs), 2) if all_reqs else 0.0,
    }


def _read_baseline_rows():
    if not os.path.isfile(DEFAULT_BASELINE):
        return []
    with open(DEFAULT_BASELINE, encoding='utf-8-sig', newline='') as f:
        return [r for r in csv.DictReader(f)]


def list_baselines():
    vers = []
    for r in _read_baseline_rows():
        v = (r.get('BASELINE_VER') or '').strip()
        if v and v not in vers:
            vers.append(v)
    return vers


def freeze_baseline(ver, rows, force=False):
    """冻结范围基准快照（F4）：全量写入该版本 REQ 集，作为后续 diff 的锚点。"""
    ver = (ver or '').strip()
    if not ver:
        return False, '基线版本不能为空'
    existing = _read_baseline_rows()
    if any((r.get('BASELINE_VER') or '').strip() == ver for r in existing) and not force:
        return False, '基线 %s 已冻结（如需覆盖加 --force）' % ver
    existing = [r for r in existing if (r.get('BASELINE_VER') or '').strip() != ver]
    now, added = _now(), 0
    for req, d in _req_index(rows).items():
        existing.append({'BASELINE_VER': ver, 'FROZEN_AT': now, 'REQ_ID': req,
                         'PRIORITY': d['priority'], 'SCOPE_STATUS': d['status'],
                         'AE_ID': d['ae'], 'MOD_ID': d['mod'], 'TC_ID': d['tc']})
        added += 1
    ensure_header(DEFAULT_BASELINE, BASELINE_COLS)
    with open(DEFAULT_BASELINE, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=BASELINE_COLS)
        w.writeheader()
        for r in existing:
            w.writerow({k: r.get(k, '') for k in BASELINE_COLS})
    return True, '已冻结范围基准 %s（%d 条需求）' % (ver, added)


def baseline_diff(rows, base_ver, changes=None):
    """当前 RTM 相对已冻结基线的真实蔓延/缩水（F4）：未经审批的净增/删除/降级即漂移。"""
    base_rows = [r for r in _read_baseline_rows() if (r.get('BASELINE_VER') or '').strip() == base_ver]
    if not base_rows:
        return {'ok': False, 'error': '未找到冻结基线 %s（请先 baseline freeze --ver %s）' % (base_ver, base_ver)}
    base = {(r.get('REQ_ID') or '').strip(): {'priority': (r.get('PRIORITY') or '').strip(),
                                              'status': (r.get('SCOPE_STATUS') or '').strip()} for r in base_rows}
    cur = {q: {'priority': d['priority'], 'status': d['status']} for q, d in _req_index(rows).items()}
    changes = load_change_ledger() if changes is None else changes
    approved = set()
    for c in changes:
        if (c.get('STATUS') or '').strip() in {CHANGE_STATUS_APPROVED, CHANGE_STATUS_IMPLEMENTED, CHANGE_STATUS_CLOSED}:
            approved.update(split_ids(c.get('REQ_IDS')))
    common = sorted(set(base) & set(cur))
    added = sorted(set(cur) - set(base))
    removed = sorted(set(base) - set(cur))
    status_changed = [(q, base[q]['status'], cur[q]['status']) for q in common if base[q]['status'] != cur[q]['status']]
    priority_changed = [(q, base[q]['priority'], cur[q]['priority']) for q in common if base[q]['priority'] != cur[q]['priority']]
    unapproved_added = [q for q in added if q not in approved]
    unapproved_removed = [q for q in removed if q not in approved]
    unapproved_prio_down = [(q, a, b) for (q, a, b) in priority_changed if q not in approved and _prio_rank(b) < _prio_rank(a)]
    drift = len(unapproved_added) + len(unapproved_removed) + len(unapproved_prio_down)
    return {'ok': True, 'base_ver': base_ver, 'added': added, 'removed': removed,
            'status_changed': status_changed, 'priority_changed': priority_changed,
            'unapproved_added': unapproved_added, 'unapproved_removed': unapproved_removed,
            'unapproved_prio_down': unapproved_prio_down, 'baseline_drift': drift}


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
    # F6：需求易变性 / 变更 KPI
    changes = load_change_ledger()
    vol = volatility_metrics(rows, changes)
    print('   ── 范围稳定性 KPI ──')
    print('   需求易变性=%s%% (%d/%d 条需求发生变更)  变更单=%d (未决%d/已批%d/已驳%d)'
          % (vol['req_volatility_pct'], vol['changed_reqs'], vol['req_total'],
             vol['cr_total'], vol['open_cr'], vol['approved_cr'], vol['rejected_cr']))
    print('   未决 CR 平均龄=%s 天  变更密度=%s CR/需求'
          % (vol['avg_open_cr_age_days'], vol['cr_per_req']))
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


def _gate_load_rows():
    """加载追溯矩阵，处理缺失/异常/为空三种前置失败路径（fail-closed）。

    返回 (rows, exit_code)；exit_code 非 None 时调用方应直接返回该码。
    """
    if not os.path.isfile(DEFAULT_MATRIX):
        print('   ✗ 未找到追溯矩阵，请先运行: python3 tools/scope_tracker.py init', file=sys.stderr)
        return None, 1
    try:
        rows = load_rtm(DEFAULT_MATRIX)
    except Exception as e:
        print('   ✗ 追溯矩阵异常（fail-closed）: %s' % e, file=sys.stderr)
        return None, 2
    if not rows:
        print('   ✗ 追溯矩阵为空', file=sys.stderr)
        return None, 1
    return rows, None


def _gate_resolve_drift(args, rows, changes):
    """F4：解析对比基线（未指定则取最新冻结基线）并计算真实漂移。

    返回 (against, drift, diff)。
    """
    against = getattr(args, 'against_baseline', None)
    if not against:
        frozen = list_baselines()
        against = Versorted(frozen) if frozen else None
    drift, diff = 0, None
    if against:
        diff = baseline_diff(rows, against, changes)
        if diff.get('ok'):
            drift = diff.get('baseline_drift', 0)
    return against, drift, diff


def _gate_print_compliance(change_signals, drift, against, diff):
    """打印变更合规（F3/F4）概览与未审批明细（蔓延/缩水/优先级降级）。"""
    print('   ── 变更合规（F3/F4）──')
    print('   未审批变更触及 Must/基线=%d  缺审批人=%d  超期未决 CR=%d  基线漂移=%d%s'
          % (change_signals['open_unapproved_must'], change_signals['missing_approver'],
             change_signals['stale_cr'], drift, ('（对比基线 %s）' % against) if against else '（无冻结基线）'))
    if not (diff and diff.get('ok')):
        return
    if diff['unapproved_added']:
        print('     ⚠ 未审批新增(蔓延): %s' % ','.join(diff['unapproved_added'][:20]))
    if diff['unapproved_removed']:
        print('     ⚠ 未审批删除(缩水): %s' % ','.join(diff['unapproved_removed'][:20]))
    if diff['unapproved_prio_down']:
        print('     ⚠ 未审批优先级降级: %s' % '; '.join('%s:%s→%s' % t for t in diff['unapproved_prio_down'][:20]))


def _gate_verdict(args, violations, creep, shrink, health, change_signals):
    """裁决门禁结论：返回「通过 / 警告 / 驳回」。"""
    allow_open = getattr(args, 'allow_open_changes', False)
    severe = (len(violations) > args.max_violations or len(shrink) > 0
              or health < args.min_health)  # v1.1.1：健康分门禁（标准 §8 ≥90）
    # F3：未审批变更触及 Must/基线 = 严重（scope-change §边界“超范围无审批禁止流转”）；--allow-open-changes 降为警告
    if change_signals['open_unapproved_must'] > 0 and not allow_open:
        severe = True
    warn = (len(creep) > 0 or (0 < len(violations) <= args.max_violations)
            or change_signals['stale_cr'] > 0 or change_signals['missing_approver'] > 0
            or (change_signals['open_unapproved_must'] > 0 and allow_open))
    return '通过' if not severe and not warn else ('驳回' if severe else '警告')


def cmd_gate(args):
    rows, err = _gate_load_rows()
    if err is not None:
        return err
    m = compute_metrics(rows)
    violations, ok = consistency_violations(DEFAULT_MATRIX, fail_closed=True)
    if not ok:
        # 一致性校验异常：fail-closed 驳回（防门禁假绿），exit 2
        _write_snapshot(m, [], [], [], 0.0, '一致性校验异常-fail-closed', '驳回')
        print('   范围门禁结论: 驳回（一致性校验异常，fail-closed，exit 2）', file=sys.stderr)
        return 2
    creep, shrink = detect_creep_shrink(rows)
    # F3：变更台账合规信号 + F4：相对已冻结基线的真实漂移
    changes = load_change_ledger()
    against, drift, diff = _gate_resolve_drift(args, rows, changes)
    change_signals = analyze_change_signals(rows, changes, baseline_drift=drift)
    health = health_score(m, violations, creep, shrink, change_signals)
    print_scorecard(m, violations, creep, shrink, health)
    _gate_print_compliance(change_signals, drift, against, diff)
    result = _gate_verdict(args, violations, creep, shrink, health, change_signals)
    detail = '违规%d/蔓延%d/缩水%d/健康%.1f/未审批%d/漂移%d' % (
        len(violations), len(creep), len(shrink), health,
        change_signals['open_unapproved_must'], drift)
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
    # F2：参照完整性校验（仅告警，不阻断登记）
    req_ids = split_ids(args.req)
    if os.path.isfile(DEFAULT_MATRIX):
        try:
            known = set(_req_index(load_rtm(DEFAULT_MATRIX)).keys())
            unknown = [q for q in req_ids if q not in known]
            if unknown:
                print('   ⚠ 变更引用了 RTM 中不存在的需求（请先录入或核对编号）: %s' % ','.join(unknown))
        except Exception:
            pass
    for label, val in (('范围', args.impact_scope), ('进度', args.impact_schedule),
                       ('成本', args.impact_cost), ('质量', args.impact_quality),
                       ('安全', args.impact_security)):
        if (val or '').strip() and val.strip() not in IMPACT_ENUM:
            print('   ⚠ %s影响值“%s”不在受控枚举{高/中/低}（仍登记，建议规范）' % (label, val))
    if (args.severity or '').strip() and args.severity.strip() not in SEVERITY_ENUM:
        print('   ⚠ 严重度“%s”不在受控枚举{轻微/主要/严重}' % args.severity)
    row = [cid, args.req, args.title, args.type, args.source,
           args.impact_scope, args.impact_schedule, args.impact_cost,
           args.impact_quality, args.impact_security,
           args.severity, CHANGE_STATUS_PROPOSED, args.approver, args.baseline_from,
           args.baseline_to, _now(), '', args.note]
    with open(DEFAULT_CHANGE, 'a', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerow(row)
    print('   ✓ 已登记变更请求 %s（状态=提出）→ %s' % (cid, DEFAULT_CHANGE))
    print('     下一步：python3 tools/scope_tracker.py change-decide --id %s --status 已批准 --approver <人> [--baseline-to v1.0.1] --writeback' % cid)
    return 0


def cmd_change_decide(args):
    """F2：推进变更生命周期；批准时可选回写 RTM 基线版本 + CHANGE_REFS。"""
    ok, msg, cr = update_change_status(args.id, args.status, approver=getattr(args, 'approver', ''),
                                       baseline_to=getattr(args, 'baseline_to', ''), note=getattr(args, 'note', ''))
    if not ok:
        print('   ✗ %s' % msg, file=sys.stderr)
        return 1
    print('   ✓ %s' % msg)
    # 批准/实施：回写 RTM（落实 scope-change §环节2 “审批通过升级基线版本 + 回写 CHANGE_REFS”）
    if args.status in {CHANGE_STATUS_APPROVED, CHANGE_STATUS_IMPLEMENTED} and getattr(args, 'writeback', False) and cr is not None:
        bto = (cr.get('BASELINE_TO') or '').strip() or getattr(args, 'baseline_to', '')
        n = apply_baseline_writeback(cr.get('REQ_IDS', ''), bto, cr.get('CHANGE_ID', ''))
        print('   ✓ 已回写 RTM：%d 行需求升级基线版本%s + 追加 CHANGE_REFS=%s'
              % (n, ('=%s' % bto) if bto else '(未指定版本)', cr.get('CHANGE_ID', '')))
        if n == 0:
            print('     ⚠ 无匹配需求行被回写（核对 REQ_IDS 是否存在于 RTM，或 RTM 缺 BASELINE_VER/CHANGE_REFS 列）')
    if args.status == CHANGE_STATUS_APPROVED and not (cr.get('APPROVER') or '').strip():
        print('   ⚠ 已批准但无审批人（重大变更强制 user_confirm=同意，请补 --approver）')
    return 0


def cmd_baseline(args):
    """F4：范围基准冻结(freeze) 与 差异比对(diff)。"""
    if args.action == 'freeze':
        if not os.path.isfile(DEFAULT_MATRIX):
            print('   ✗ 未找到追溯矩阵，请先 init', file=sys.stderr)
            return 1
        rows = load_rtm(DEFAULT_MATRIX)
        ver = args.ver
        if not ver:
            vers = [r.get('BASELINE_VER', '').strip() for r in rows if (r.get('BASELINE_VER') or '').strip()]
            ver = Versorted(vers) if vers else 'v1.0.0'
        ok, msg = freeze_baseline(ver, rows, force=getattr(args, 'force', False))
        print(('   ✓ ' if ok else '   ✗ ') + msg + (' → %s' % DEFAULT_BASELINE if ok else ''))
        return 0 if ok else 1
    if args.action == 'diff':
        if not os.path.isfile(DEFAULT_MATRIX):
            print('   ✗ 未找到追溯矩阵，请先 init', file=sys.stderr)
            return 1
        rows = load_rtm(DEFAULT_MATRIX)
        against = args.against
        if not against:
            frozen = list_baselines()
            against = Versorted(frozen) if frozen else None
        if not against:
            print('   ✗ 无冻结基线可比对，请先：baseline freeze --ver <版本>', file=sys.stderr)
            return 1
        d = baseline_diff(rows, against)
        if not d.get('ok'):
            print('   ✗ %s' % d.get('error'), file=sys.stderr)
            return 1
        print('   ── 基线差异比对（当前 vs %s）──' % against)
        print('   新增需求=%d  删除需求=%d  状态变更=%d  优先级变更=%d'
              % (len(d['added']), len(d['removed']), len(d['status_changed']), len(d['priority_changed'])))
        print('   未审批新增(真实蔓延)=%d  未审批删除(真实缩水)=%d  未审批降级=%d  → 基线漂移=%d'
              % (len(d['unapproved_added']), len(d['unapproved_removed']), len(d['unapproved_prio_down']), d['baseline_drift']))
        if d['unapproved_added']:
            print('     ⚠ 未审批新增: %s' % ','.join(d['unapproved_added'][:30]))
        if d['unapproved_removed']:
            print('     ⚠ 未审批删除: %s' % ','.join(d['unapproved_removed'][:30]))
        return 1 if d['baseline_drift'] > 0 and getattr(args, 'strict', False) else 0
    if args.action == 'list':
        vers = list_baselines()
        print('   已冻结基线: %s' % (', '.join(vers) if vers else '（无）'))
        return 0
    print('   ✗ 未知 baseline 动作: %s（freeze/diff/list）' % args.action, file=sys.stderr)
    return 1


def build_report(rows, m, violations, creep, shrink, health, changes, vol, diff, change_signals):
    """F6：结构化范围状态报告（供 --json / MCP / PMO 仪表盘消费）。"""
    return {
        'generated_at': _now(),
        'baseline_ver': Versorted([r.get('BASELINE_VER', '').strip() for r in rows if (r.get('BASELINE_VER') or '').strip()]) if any((r.get('BASELINE_VER') or '').strip() for r in rows) else None,
        'coverage': {'req_total': m['req_total'], 'req_ae_pct': m['cov_ae'], 'req_tc_pct': m['cov_tc'],
                     'impl_pct': m['impl_pct'], 'ver_pct': m['ver_pct']},
        'consistency': {'violations': len(violations), 'creep_items': len(creep), 'shrink_items': len(shrink)},
        'stability': vol,
        'change_compliance': change_signals,
        'baseline_diff': ({k: d[k] for k in ('base_ver', 'added', 'removed', 'unapproved_added',
                                             'unapproved_removed', 'unapproved_prio_down', 'baseline_drift')}
                          if diff and diff.get('ok') else None),
        'health_score': health,
        'status_dist': m['status_dist'], 'priority_dist': m['prio_dist'],
    }


def cmd_report(args):
    """F6：范围状态综合报告（指标+变更+基线漂移+门禁预演）；--json 供机器消费。"""
    if not os.path.isfile(DEFAULT_MATRIX):
        print('   ✗ 未找到追溯矩阵，请先 init', file=sys.stderr)
        return 1
    rows = load_rtm(DEFAULT_MATRIX)
    m = compute_metrics(rows)
    violations, _ = consistency_violations(DEFAULT_MATRIX)
    creep, shrink = detect_creep_shrink(rows)
    changes = load_change_ledger()
    against = getattr(args, 'against_baseline', None)
    if not against:
        frozen = list_baselines()
        against = Versorted(frozen) if frozen else None
    diff = baseline_diff(rows, against, changes) if against else None
    drift = diff.get('baseline_drift', 0) if (diff and diff.get('ok')) else 0
    change_signals = analyze_change_signals(rows, changes, baseline_drift=drift)
    health = health_score(m, violations, creep, shrink, change_signals)
    vol = volatility_metrics(rows, changes)
    report = build_report(rows, m, violations, creep, shrink, health, changes, vol, diff, change_signals)
    if getattr(args, 'json', False):
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print('══ 范围状态报告 (%s) ══' % report['generated_at'])
    print_scorecard(m, violations, creep, shrink, health)
    print('   ── 范围稳定性 KPI ──')
    print('   需求易变性=%s%%  变更单=%d(未决%d/已批%d/已驳%d)  未决CR均龄=%s天'
          % (vol['req_volatility_pct'], vol['cr_total'], vol['open_cr'], vol['approved_cr'],
             vol['rejected_cr'], vol['avg_open_cr_age_days']))
    print('   ── 变更合规 ──')
    print('   未审批触及Must/基线=%d  缺审批人=%d  超期未决=%d  基线漂移=%d'
          % (change_signals['open_unapproved_must'], change_signals['missing_approver'],
             change_signals['stale_cr'], drift))
    print('   范围健康分=%.1f（门禁预演：%s）' % (health, '驳回' if health < 90 or shrink or change_signals['open_unapproved_must'] else ('警告' if (creep or change_signals['stale_cr'] or change_signals['missing_approver']) else '通过')))
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
    p_g = sub.add_parser('gate', help='范围门禁（一致性+蔓延/缩水+变更合规+健康分）')
    p_g.add_argument('--max-violations', type=int, default=0)
    p_g.add_argument('--min-health', type=float, default=90, help='健康分门禁阈值（默认 90，低于则驳回）')
    p_g.add_argument('--against-baseline', default=None, help='指定对比的冻结基线版本（默认自动取最新）')
    p_g.add_argument('--allow-open-changes', action='store_true',
                     help='将“未审批变更触及 Must/基线”从驳回降为警告（迁移期用）')
    p_c = sub.add_parser('change', help='登记变更请求（状态=提出）')
    p_c.add_argument('--req', required=True, help='关联需求 ID（多值逗号分隔）')
    p_c.add_argument('--title', required=True, help='变更标题')
    p_c.add_argument('--type', default='范围调整', help='类型(范围调整/接口变化/合规新规/新诉求/缺陷澄清/其他)')
    p_c.add_argument('--source', default='用户诉求', help='变更来源')
    p_c.add_argument('--impact-scope', default='', help='范围影响(高/中/低)')
    p_c.add_argument('--impact-schedule', default='', help='进度影响(高/中/低)')
    p_c.add_argument('--impact-cost', default='', help='成本影响(高/中/低)')
    p_c.add_argument('--impact-quality', default='', help='质量影响(高/中/低)')
    p_c.add_argument('--impact-security', default='', help='安全影响(高/中/低)')
    p_c.add_argument('--severity', default='主要', help='严重度(轻微/主要/严重)')
    p_c.add_argument('--approver', default='', help='审批人')
    p_c.add_argument('--baseline-from', default='', help='基准版本(前)')
    p_c.add_argument('--baseline-to', default='', help='基准版本(后)')
    p_c.add_argument('--note', default='', help='备注')
    # F2：变更生命周期状态机
    p_cd = sub.add_parser('change-decide', help='推进变更生命周期（分析中/已批准/已驳回/已实施/已关闭）')
    p_cd.add_argument('--id', required=True, help='变更编号 CR-<nnn>')
    p_cd.add_argument('--status', required=True, help='目标状态(分析中/已批准/已驳回/已实施/已关闭)')
    p_cd.add_argument('--approver', default='', help='审批人（批准时强烈建议填写）')
    p_cd.add_argument('--baseline-to', default='', help='批准后的新基线版本（回写 RTM）')
    p_cd.add_argument('--writeback', action='store_true', help='批准/实施时回写 RTM（BASELINE_VER + CHANGE_REFS）')
    p_cd.add_argument('--note', default='', help='决策备注')
    # F4：基线冻结与差异比对
    p_b = sub.add_parser('baseline', help='范围基准冻结(freeze)/差异比对(diff)/列表(list)')
    p_b.add_argument('action', choices=['freeze', 'diff', 'list'], help='freeze=冻结当前RTM为基线; diff=当前vs基线; list=已冻结版本')
    p_b.add_argument('--ver', default='', help='freeze：基线版本（缺省取 RTM 最新 BASELINE_VER）')
    p_b.add_argument('--against', default='', help='diff：对比的基线版本（缺省取最新冻结）')
    p_b.add_argument('--force', action='store_true', help='freeze：覆盖已存在的同名基线')
    p_b.add_argument('--strict', action='store_true', help='diff：存在未审批漂移时 exit 1')
    # F6：综合报告
    p_r = sub.add_parser('report', help='范围状态综合报告（指标+变更+基线漂移+门禁预演）')
    p_r.add_argument('--json', action='store_true', help='以 JSON 输出（供 MCP/PMO 消费）')
    p_r.add_argument('--against-baseline', default=None, help='指定对比的冻结基线版本')

    args = ap.parse_args()
    if getattr(args, 'root', None):
        global ROOT, DEFAULT_MATRIX, DEFAULT_CHANGE, DEFAULT_TRACK, DEFAULT_BASELINE
        ROOT = find_project_root(args.root)
        DEFAULT_MATRIX = os.path.join(ROOT, '台账', '需求-架构-代码追溯矩阵.csv')
        DEFAULT_CHANGE = os.path.join(ROOT, '台账', '06_范围变更台账.csv')
        DEFAULT_TRACK = os.path.join(ROOT, '台账', '07_范围跟踪台账.csv')
        DEFAULT_BASELINE = os.path.join(ROOT, '台账', '范围基准快照.csv')
    if args.cmd == 'init':
        return cmd_init(args)
    if args.cmd == 'metrics':
        return cmd_metrics(args)
    if args.cmd == 'gate':
        return cmd_gate(args)
    if args.cmd == 'change':
        return cmd_change(args)
    if args.cmd == 'change-decide':
        return cmd_change_decide(args)
    if args.cmd == 'baseline':
        return cmd_baseline(args)
    if args.cmd == 'report':
        return cmd_report(args)
    ap.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
