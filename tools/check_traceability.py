#!/usr/bin/env python3
# =============================================================================
# check_traceability.py — 需求-架构-代码 三方一致性门禁校验
#
# 行业最佳实践依据：
#   - NASA SWE-059 / ISO/IEC/IEEE 24765：需求↔架构↔设计↔代码↔测试 双向可追溯，禁止孤儿
#   - EN 62304 4-way traceability：需求↔设计、需求↔测试、风险↔设计、风险↔测试
#   - ASPICE：架构须证明每个需求分配到具体组件；定期「追溯健康自检」发现未覆盖/断链
#   - ArchUnit 思路：架构-实现一致性以自动化检查强制执行，杜绝代码漂移
#
# 本工具校验单一事实来源《需求-架构-代码追溯矩阵.csv》，检测：
#   1) 需求→架构覆盖（每个 REQ 至少映射 1 个 AE）
#   2) 需求→测试覆盖（每个 REQ 至少 1 个 TC）
#   3) 架构无孤儿（每个 AE 至少回溯 1 个 REQ）
#   4) 架构已落地（每个 AE 至少 1 个 MOD 实现）
#   5) 代码无孤儿（每个 MOD 至少归属 1 个 AE）
#   6) 测试回溯需求（每个 TC 至少回溯 1 个 REQ）
# 任一违规且超出 --max-violations 容忍度 → exit 1（门禁驳回）。
#
# 用法：
#   python3 tools/check_traceability.py [--matrix 台账/需求-架构-代码追溯矩阵.csv] [--max-violations 0] [--init]
#   --init  生成空模板（含表头与示例行）
# =============================================================================
import os
import sys
import csv
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MATRIX = os.path.join(ROOT, '台账', '需求-架构-代码追溯矩阵.csv')

EXPECTED_COLS = ['REQ_ID', 'REQ_TITLE', 'AE_ID', 'MOD_ID', 'TC_ID']


def split_ids(cell):
    if not cell:
        return []
    return [x.strip() for x in str(cell).replace(';', ',').split(',') if x.strip()]


def load_matrix(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        missing = [c for c in EXPECTED_COLS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError('追溯矩阵缺少列: %s（应为 %s）' % (','.join(missing), ','.join(EXPECTED_COLS)))
        rows = list(reader)
    return rows


def analyze(rows):
    req_to_aes, req_to_tcs = {}, {}
    ae_to_reqs, ae_to_mods = {}, {}
    mod_to_aes = {}
    tc_to_reqs = {}
    # _seen：从所有行（含空 REQ_ID 的孤儿行）收集，用于孤儿检测
    ae_seen, mod_seen, tc_seen = set(), set(), set()

    def add(map_, k, v):
        map_.setdefault(k, set()).add(v)

    for r in rows:
        reqs = split_ids(r.get('REQ_ID'))
        aes = split_ids(r.get('AE_ID'))
        mods = split_ids(r.get('MOD_ID'))
        tcs = split_ids(r.get('TC_ID'))
        ae_seen.update(aes)
        mod_seen.update(mods)
        tc_seen.update(tcs)
        for req in reqs:
            req_to_aes.setdefault(req, set()).update(aes)
            req_to_tcs.setdefault(req, set()).update(tcs)
            for ae in aes:
                add(ae_to_reqs, ae, req)
                for mod in mods:
                    add(ae_to_mods, ae, mod)
                    add(mod_to_aes, mod, ae)
            for tc in tcs:
                add(tc_to_reqs, tc, req)

    violations = []

    # 1) 需求→架构覆盖
    for req, aes in req_to_aes.items():
        if not aes:
            violations.append('需求 %s 未映射到任何架构元素(AE)' % req)
    # 2) 需求→测试覆盖
    for req, tcs in req_to_tcs.items():
        if not tcs:
            violations.append('需求 %s 未被任何测试用例(TC)验证' % req)
    # 3) 架构无孤儿（出现过但无回溯需求）
    for ae in ae_seen:
        if not ae_to_reqs.get(ae):
            violations.append('架构元素 %s 无回溯需求(孤儿架构)' % ae)
    # 4) 架构已落地(代码)：有需求的 AE 须有 MOD 实现
    for ae in ae_to_reqs:
        if not ae_to_mods.get(ae):
            violations.append('架构元素 %s 无代码模块(MOD)实现' % ae)
    # 5) 代码无孤儿
    for mod in mod_seen:
        if not mod_to_aes.get(mod):
            violations.append('代码模块 %s 无归属架构元素(孤儿代码)' % mod)
    # 6) 测试回溯需求
    for tc in tc_seen:
        if not tc_to_reqs.get(tc):
            violations.append('测试用例 %s 无回溯需求(孤儿测试)' % tc)

    return violations, {
        'req': len(req_to_aes), 'ae': len(ae_seen),
        'mod': len(mod_seen), 'tc': len(tc_seen),
    }


def init_template(path):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(EXPECTED_COLS)
        w.writerow(['REQ-001', '示例：用户可登录', 'AE-001', 'MOD-001', 'TC-001'])
    print('   ✓ 已生成追溯矩阵模板: %s' % path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--matrix', default=DEFAULT_MATRIX)
    ap.add_argument('--max-violations', type=int, default=0)
    ap.add_argument('--init', action='store_true', help='生成空模板并退出')
    args = ap.parse_args()

    if args.init:
        init_template(args.matrix)
        return 0

    if not os.path.isfile(args.matrix):
        print('   ✗ 未找到追溯矩阵: %s' % args.matrix, file=sys.stderr)
        print('   请先建立《需求-架构-代码追溯矩阵》(参见 references/traceability_standard.md)，', file=sys.stderr)
        print('   或运行: python3 tools/check_traceability.py --init', file=sys.stderr)
        return 1

    try:
        rows = load_matrix(args.matrix)
    except ValueError as e:
        print('   ✗ %s' % e, file=sys.stderr)
        return 1

    if not rows:
        print('   ✗ 追溯矩阵为空，请录入需求-架构-代码-测试映射。', file=sys.stderr)
        return 1

    violations, stats = analyze(rows)
    print('   追溯矩阵统计: 需求=%d 架构元素=%d 代码模块=%d 测试用例=%d'
          % (stats['req'], stats['ae'], stats['mod'], stats['tc']))

    if not violations:
        print('   ✓ 需求-架构-代码 三方一致性门禁通过（无孤儿/无断链）')
        return 0

    over = len(violations) - args.max_violations
    print('   ✗ 发现 %d 项追溯不一致（容忍度=%d）：' % (len(violations), args.max_violations), file=sys.stderr)
    for v in violations[:30]:
        print('     - ' + v, file=sys.stderr)
    if over > 0:
        print('   处置：补齐映射或清理孤儿，使每个需求可回溯到架构与测试、每个代码模块归属架构元素，再重跑本门禁。',
              file=sys.stderr)
        return 1
    print('   ⚠ 违规数在容忍度内，门禁通过（仍有 %d 项待清理）' % len(violations))
    return 0


if __name__ == '__main__':
    sys.exit(main())
