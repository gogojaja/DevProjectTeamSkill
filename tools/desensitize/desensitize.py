#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
desensitize.py — 文档脱敏小工具（v1.0.0）
依据: .trae/skills/references/iron_rules.md §3 敏感信息三级处理

功能：
  1. 扫描模式（--scan）：检测文件/目录中的敏感信息，输出报告，不修改原文件
  2. 脱敏模式（默认）：自动替换敏感信息，可选择原地替换或输出到新目录
  3. 支持 A/B/C 三级敏感信息分级，规则可扩展
  4. 生成脱敏报告 CSV（位置/类型/级别/原值摘要/替换值）
  5. 支持 --dry-run 预览、--include/--exclude 文件过滤

用法:
  python tools/desensitize/desensitize.py --scan <文件或目录>
  python tools/desensitize/desensitize.py <文件或目录> -o <输出目录>
  python tools/desensitize/desensitize.py --in-place <文件>
  python tools/desensitize/desensitize.py --rules custom_rules.json <目标>
  python tools/desensitize/desensitize.py --dictionary desensitize_dictionary.csv <目标>
"""

import os
import sys
import re
import json
import csv
import datetime
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# =============================================================================
# 默认脱敏规则集（对齐 iron_rules.md §3 A/B/C 三级）
# =============================================================================

DEFAULT_RULES = {
    # ── A 级：禁止入库（密钥/凭据/Token/私钥），发现即告警，默认用 *** 替换 ──
    "a_secrets": {
        "level": "A",
        "description": "密钥/凭据/Token（A 级，禁止入库）",
        "enabled": True,
        "patterns": [
            {
                "name": "github_pat_classic",
                "regex": r'ghp_[A-Za-z0-9]{36}',
                "replacement": "ghp_***",
                "example": "ghp_abcdefghijklmnopqrstuvwxyz0123456789"
            },
            {
                "name": "github_pat_fine_grained",
                "regex": r'github_pat_[A-Za-z0-9_]{82}',
                "replacement": "github_pat_***",
                "example": "github_pat_1234567890abcdefghij..."
            },
            {
                "name": "aws_access_key",
                "regex": r'AKIA[0-9A-Z]{16}',
                "replacement": "AKIA***",
                "example": "AKIAIOSFODNN7EXAMPLE"
            },
            {
                "name": "sk_api_key",
                "regex": r'sk-[A-Za-z0-9]{20,}',
                "replacement": "sk-***",
                "example": "sk-abc123def456..."
            },
            {
                "name": "private_key_header",
                "regex": r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----',
                "replacement": "-----BEGIN PRIVATE KEY-----\n***\n-----END PRIVATE KEY-----",
                "example": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
            },
            {
                "name": "gitee_token",
                "regex": r'gitee_[A-Za-z0-9]{30,}',
                "replacement": "gitee_***",
                "example": "gitee_abc123def456..."
            },
            {
                "name": "bearer_token",
                "regex": r'(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*',
                "replacement": r'\1***',
                "example": "Authorization: Bearer eyJhbGciOi..."
            },
            {
                "name": "password_inline",
                "regex": r'(?i)(password\s*[=:]\s*)[^\s"\'}{]+',
                "replacement": r'\1***',
                "example": "password=mySecret123"
            },
        ]
    },

    # ── B 级：脱敏入库（IP/主机名/用户名/绝对路径/邮箱） ──
    "b_ipv4": {
        "level": "B",
        "description": "IPv4 地址（B 级，默认完全脱敏）",
        "enabled": True,
        "patterns": [
            {
                "name": "ipv4_full",
                "regex": r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
                "replacement": "xxx.xxx.xxx.xxx",
                "example": "192.168.1.100 → xxx.xxx.xxx.xxx"
            }
        ],
        # 豁免：已脱敏标记 / 回环地址 / 组播 / 保留段 / 示例 IP
        "exempt_patterns": [
            r'^xxx\.',
            r'^127\.',
            r'^0\.0\.0\.0$',
            r'^255\.',
            r'^224\.',
            r'\.x$',
        ]
    },

    "b_paths": {
        "level": "B",
        "description": "绝对路径（B 级，脱敏用户名/盘符）",
        "enabled": True,
        "patterns": [
            {
                "name": "windows_user_path",
                "regex": r'[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+\\',
                "replacement": r'%USERPROFILE%\\',
                "example": "C:\\Users\\john\\... → %USERPROFILE%\\..."
            },
            {
                "name": "macos_user_path",
                "regex": r'/Users/[A-Za-z0-9_.-]+/',
                "replacement": "~/",
                "example": "/Users/john/... → ~/..."
            },
            {
                "name": "linux_home_path",
                "regex": r'/home/[A-Za-z0-9_.-]+/',
                "replacement": "~/",
                "example": "/home/john/... → ~/..."
            },
            {
                "name": "windows_drive_path",
                "regex": r'[A-Za-z]:\\(?:Users|Program Files|ProgramData|Windows|temp|tmp)\\',
                "replacement": r'%SYSTEMDRIVE%\\...\\',
                "example": "D:\\trae\\... → %SYSTEMDRIVE%\\...\\"
            },
        ],
        "exempt_patterns": [
            r'%[A-Z_]+%',  # 已用环境变量占位
            r'^~/',         # 已用 ~/ 占位
        ]
    },

    "b_email": {
        "level": "B",
        "description": "邮箱地址（B 级，脱敏用户名）",
        "enabled": True,
        "patterns": [
            {
                "name": "email_mask",
                "regex": r'\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b',
                "replacement": r'\1***@\2',
                "example": "john.doe@example.com → j***@example.com"
            }
        ]
    },

    "b_phone_cn": {
        "level": "B",
        "description": "中国大陆手机号（B 级，中间 4 位脱敏）",
        "enabled": True,
        "patterns": [
            {
                "name": "cn_mobile",
                "regex": r'\b1([3-9]\d)(\d{4})(\d{4})\b',
                "replacement": r'1\1****\3',
                "example": "13812345678 → 138****5678"
            }
        ]
    },
}

# 默认支持的文本文件扩展名
DEFAULT_EXTENSIONS = {
    '.md', '.txt', '.csv', '.json', '.yaml', '.yml', '.xml',
    '.py', '.sh', '.ps1', '.bat', '.js', '.ts', '.tsx', '.jsx',
    '.html', '.css', '.env', '.conf', '.cfg', '.ini', '.toml',
    '.log', '.rst', '.adoc',
}

# 默认排除目录
DEFAULT_EXCLUDE_DIRS = {
    '.git', '.svn', '.hg', 'node_modules', '__pycache__',
    '.venv', 'venv', 'dist', 'build', '.secrets',
}


# =============================================================================
# 核心脱敏引擎
# =============================================================================

class Desensitizer:
    """文档脱敏引擎"""

    def __init__(self, rules=None, extensions=None, exclude_dirs=None):
        self.rules = rules or DEFAULT_RULES
        self.extensions = extensions or DEFAULT_EXTENSIONS
        self.exclude_dirs = exclude_dirs or DEFAULT_EXCLUDE_DIRS
        self._compiled = {}
        self._exempt_compiled = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """预编译所有正则表达式"""
        for rule_id, rule in self.rules.items():
            if not rule.get("enabled", True):
                continue
            self._compiled[rule_id] = []
            for p in rule["patterns"]:
                try:
                    self._compiled[rule_id].append({
                        "name": p["name"],
                        "regex": re.compile(p["regex"], re.MULTILINE),
                        "replacement": p["replacement"],
                    })
                except re.error as e:
                    print(f"  ⚠ 规则 {p['name']} 正则编译失败: {e}", file=sys.stderr)

            # 编译豁免模式
            if "exempt_patterns" in rule:
                self._exempt_compiled[rule_id] = []
                for ep in rule["exempt_patterns"]:
                    try:
                        self._exempt_compiled[rule_id].append(re.compile(ep))
                    except re.error:
                        pass

    def _is_exempt_match(self, rule_id, matched_text):
        """检查单个匹配文本是否匹配豁免规则（对匹配文本本身检查，而非整行）"""
        if rule_id not in self._exempt_compiled:
            return False
        for ep in self._exempt_compiled[rule_id]:
            if ep.search(matched_text):
                return True
        return False

    def scan_text(self, text, source_label="inline"):
        """
        扫描文本中的敏感信息，返回发现列表。
        返回: [{"rule": "...", "pattern": "...", "level": "...", "match": "...", "line": N, "col": N}, ...]
        """
        findings = []
        lines = text.split('\n')

        for rule_id, compiled_list in self._compiled.items():
            rule = self.rules[rule_id]
            level = rule.get("level", "?")
            for cp in compiled_list:
                for line_num, line in enumerate(lines, 1):
                    for m in cp["regex"].finditer(line):
                        matched_text = m.group(0)
                        # 检查匹配内容是否豁免
                        if self._is_exempt_match(rule_id, matched_text):
                            continue
                        findings.append({
                            "rule_id": rule_id,
                            "rule_desc": rule.get("description", rule_id),
                            "pattern_name": cp["name"],
                            "level": level,
                            "match": matched_text,
                            "replacement": cp["replacement"],
                            "line": line_num,
                            "column": m.start() + 1,
                            "source": source_label,
                        })
        # 按行号排序
        findings.sort(key=lambda x: (x["line"], x["column"]))
        return findings

    def desensitize_text(self, text):
        """
        对文本执行脱敏，返回 (脱敏后文本, 替换统计)。
        注意：按规则优先级依次替换，A 级先于 B 级；豁免的匹配项不替换。
        """
        result = text
        stats = {}

        # 先 A 级后 B 级（按 level 排序：A > B > C）
        sorted_rules = sorted(
            self._compiled.keys(),
            key=lambda rid: {"A": 0, "B": 1, "C": 2}.get(self.rules[rid].get("level", "?"), 9)
        )

        for rule_id in sorted_rules:
            rule = self.rules[rule_id]
            level = rule.get("level", "?")
            for cp in self._compiled[rule_id]:
                count = [0]  # 用 list 实现闭包内修改
                replacement = cp["replacement"]

                def _make_replacer(rid, repl, cnt_ref):
                    """创建带豁免检查的替换函数"""
                    def _replacer(m):
                        matched = m.group(0)
                        if self._is_exempt_match(rid, matched):
                            return matched  # 豁免，原样返回
                        cnt_ref[0] += 1
                        # 处理反向引用（\1, \2 等）
                        return m.expand(repl)
                    return _replacer

                replacer = _make_replacer(rule_id, replacement, count)
                result = cp["regex"].sub(replacer, result)
                if count[0] > 0:
                    key = f"{level}/{cp['name']}"
                    stats[key] = stats.get(key, 0) + count[0]

        return result, stats

    def should_process_file(self, filepath):
        """判断是否应该处理该文件"""
        fp = Path(filepath)
        # 检查扩展名
        if fp.suffix.lower() not in self.extensions:
            return False
        # 检查排除目录
        parts = set(fp.parts)
        if parts & self.exclude_dirs:
            return False
        # 跳过二进制（简单启发式）
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                f.read(1024)
            return True
        except (UnicodeDecodeError, PermissionError):
            return False

    def collect_files(self, target):
        """收集目标路径下所有待处理文件"""
        target = Path(target)
        files = []
        if target.is_file():
            if self.should_process_file(target):
                files.append(target)
        elif target.is_dir():
            for root, dirs, filenames in os.walk(target):
                # 实时移除排除目录
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                for fn in filenames:
                    fp = Path(root) / fn
                    if self.should_process_file(fp):
                        files.append(fp)
        return files


# =============================================================================
# 报告生成
# =============================================================================

def write_report(findings, stats, report_path):
    """生成脱敏/扫描报告 CSV（UTF-8 with BOM）"""
    fieldnames = [
        "source", "line", "column", "level",
        "rule_id", "rule_desc", "pattern_name",
        "match_preview", "replacement"
    ]
    with open(report_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in findings:
            writer.writerow({
                "source": item["source"],
                "line": item["line"],
                "column": item["column"],
                "level": item["level"],
                "rule_id": item["rule_id"],
                "rule_desc": item["rule_desc"],
                "pattern_name": item["pattern_name"],
                "match_preview": _preview(item["match"], 60),
                "replacement": _preview(item["replacement"], 60),
            })
        # 追加汇总行
        if stats:
            writer.writerow({})
            writer.writerow({"source": "=== 汇总 ===", "line": "", "column": ""})
            for key, count in sorted(stats.items()):
                writer.writerow({
                    "source": key,
                    "line": count,
                    "column": "",
                    "level": key.split('/')[0] if '/' in key else "",
                    "rule_id": "",
                    "rule_desc": "",
                    "pattern_name": "",
                    "match_preview": "",
                    "replacement": "",
                })


def _preview(text, max_len=60):
    """生成匹配内容预览（避免泄露完整敏感信息）"""
    text = text.replace('\n', '\\n').replace('\r', '')
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


# =============================================================================
# 自定义规则加载
# =============================================================================

def load_custom_rules(path):
    """从 JSON 文件加载自定义规则，与默认规则合并（覆盖同名规则）"""
    with open(path, 'r', encoding='utf-8') as f:
        custom = json.load(f)

    merged = json.loads(json.dumps(DEFAULT_RULES))  # 深拷贝默认

    for rule_id, rule_data in custom.items():
        if rule_id in merged:
            # 合并：更新 enabled / patterns / exempt_patterns
            if "enabled" in rule_data:
                merged[rule_id]["enabled"] = rule_data["enabled"]
            if "patterns" in rule_data:
                merged[rule_id]["patterns"] = rule_data["patterns"]
            if "exempt_patterns" in rule_data:
                merged[rule_id]["exempt_patterns"] = rule_data["exempt_patterns"]
        else:
            # 新增规则
            merged[rule_id] = rule_data

    return merged


def add_keyword_rules(rules, keywords, level="B", replacement="***"):
    """
    从关键词列表生成自定义规则并加入规则集。
    所有关键词使用直接子串匹配（兼容中英文混合场景）。
    """
    if not keywords:
        return rules

    patterns = []
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        escaped = re.escape(kw)
        # 直接子串匹配，不依赖词边界（兼容中英混合场景）
        regex = escaped

        patterns.append({
            "name": f"keyword_{kw}",
            "regex": regex,
            "replacement": replacement,
            "example": f"{kw} → {replacement}"
        })

    if patterns:
        rules["custom_keywords"] = {
            "level": level,
            "description": f"用户自定义关键词（{level} 级，命令行 --keywords 指定）",
            "enabled": True,
            "patterns": patterns
        }

    return rules


def load_dictionary_rules(rules, csv_path):
    """
    从脱敏字典 CSV（UTF-8 with BOM）读取关键字集并入规则集。
    CSV 列：keyword, level, replacement, type, description
      - keyword：要脱敏的关键字（直接子串匹配，兼容中文）
      - level：A/B/C（默认 B）
      - replacement：替换文本（默认 ***）
    - 以 # 开头的行视为注释跳过；空行跳过。
    返回更新后的规则集（新增 dictionary_keywords 规则组）。
    """
    if not os.path.isfile(csv_path):
        print(f"  ⚠ 脱敏字典文件不存在: {csv_path}", file=sys.stderr)
        return rules

    # 按 A→B→C 分三组，便于 --level 过滤
    by_level = {"A": [], "B": [], "C": []}
    loaded = 0
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for raw in reader:
            if not raw:
                continue
            row = [c.strip() for c in raw]
            if not row[0] or row[0].startswith('#'):
                continue
            if row[0].lower() == 'keyword' or (len(row) > 1 and row[1].lower() == 'level'):
                continue  # 跳过表头
            level = (row[1].upper() if len(row) > 1 and row[1].upper() in ("A", "B", "C") else "B")
            replacement = (row[2] if len(row) > 2 and row[2] else "***")
            _type = (row[3] if len(row) > 3 else "other")
            by_level[level].append({
                "name": f"dict_{_type}_{row[0]}",
                "regex": re.escape(row[0]),
                "replacement": replacement,
                "example": f"{row[0]} → {replacement}",
            })
            loaded += 1

    if loaded:
        for lvl, patterns_l in by_level.items():
            if patterns_l:
                rules[f"dictionary_{lvl}"] = {
                    "level": lvl,
                    "description": f"脱敏字典关键字（{lvl} 级，来自 --dictionary）",
                    "enabled": True,
                    "patterns": patterns_l,
                }
        print(f" 已加载脱敏字典 {loaded} 个关键字（{csv_path}）")

    return rules


# =============================================================================
# CLI 主入口
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="文档脱敏工具 — 按 A/B/C 三级扫描和替换敏感信息（对齐 iron_rules.md §3）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描单个文件（不修改）
  python desensitize.py --scan document.md

  # 扫描整个目录并生成报告
  python desensitize.py --scan ./docs --report scan_report.csv

  # 脱敏文件到输出目录
  python desensitize.py ./src -o ./output_desensitized

  # 原地脱敏（危险，建议先备份）
  python desensitize.py --in-place config.yaml

  # 使用自定义规则
  python desensitize.py --rules my_rules.json --scan ./src

  # 使用脱敏字典（关键字集 CSV）
  python desensitize.py --dictionary desensitize_dictionary.csv ./src -o ./src_safe

  # 脱敏字典 + 命令行临时关键词 组合使用
  python desensitize.py --dictionary desensitize_dictionary.csv --keywords "内部代号,张三" ./doc.md

  # 仅启用 A 级检测
  python desensitize.py --scan --level A ./secrets
"""
    )
    parser.add_argument("target", nargs="?", help="目标文件或目录")
    parser.add_argument("--scan", action="store_true", help="仅扫描，不修改文件（安全模式）")
    parser.add_argument("--in-place", action="store_true", help="原地替换文件（危险，请先备份）")
    parser.add_argument("-o", "--output", help="输出目录（脱敏模式下使用，不指定则在同目录生成 .desensitized 副本）")
    parser.add_argument("--report", help="报告输出路径（CSV），默认自动生成")
    parser.add_argument("--rules", help="自定义规则 JSON 文件路径（与默认规则合并）")
    parser.add_argument("--dictionary", help="脱敏字典 CSV 路径（keyword,level,replacement,type,description；UTF-8 with BOM；# 开头为注释）")
    parser.add_argument("--level", choices=["A", "B", "C"], help="仅处理指定级别及以上（A=仅A级，B=A+B，C=全部）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式：显示将替换的内容，但不写入文件")
    parser.add_argument("--include-ext", help="额外包含的扩展名，逗号分隔（如 .env,.cfg）")
    parser.add_argument("--exclude-dir", help="额外排除的目录，逗号分隔")
    parser.add_argument("--keywords", help="自定义敏感关键词，逗号分隔（如：内部项目名,机密代号,张三）")
    parser.add_argument("--keyword-level", choices=["A", "B", "C"], default="B",
                        help="自定义关键词的敏感级别（默认 B 级）")
    parser.add_argument("--keyword-replacement", default="***",
                        help="自定义关键词的替换文本（默认 ***）")
    parser.add_argument("--list-rules", action="store_true", help="列出所有当前启用的规则后退出")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出统计结果")

    args = parser.parse_args()

    # 列出规则
    if args.list_rules:
        _print_rules()
        return 0

    if not args.target:
        parser.error("请指定目标文件或目录（或使用 --list-rules 查看规则）")

    # 构建规则集
    rules = DEFAULT_RULES
    if args.rules:
        if not os.path.isfile(args.rules):
            print(f"❌ 自定义规则文件不存在: {args.rules}", file=sys.stderr)
            return 1
        rules = load_custom_rules(args.rules)

    # 脱敏字典（关键字集，UTF-8 with BOM CSV）
    if args.dictionary:
        rules = load_dictionary_rules(rules, args.dictionary)

    # 命令行自定义关键词
    if args.keywords:
        kw_list = [kw.strip() for kw in args.keywords.split(',') if kw.strip()]
        if kw_list:
            rules = add_keyword_rules(rules, kw_list,
                                       level=args.keyword_level,
                                       replacement=args.keyword_replacement)
            print(f" 已加载 {len(kw_list)} 个自定义关键词（{args.keyword_level} 级）")

    # 按级别过滤
    if args.level:
        level_order = {"A": ["A"], "B": ["A", "B"], "C": ["A", "B", "C"]}
        allowed = set(level_order[args.level])
        rules = {
            rid: r for rid, r in rules.items()
            if r.get("level", "?") in allowed
        }

    # 扩展名和排除目录
    extensions = set(DEFAULT_EXTENSIONS)
    if args.include_ext:
        for ext in args.include_ext.split(','):
            ext = ext.strip()
            if ext and not ext.startswith('.'):
                ext = '.' + ext
            extensions.add(ext)

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    if args.exclude_dir:
        for d in args.exclude_dir.split(','):
            d = d.strip()
            if d:
                exclude_dirs.add(d)

    # 初始化引擎
    engine = Desensitizer(rules=rules, extensions=extensions, exclude_dirs=exclude_dirs)

    # 收集文件
    target_path = Path(args.target)
    if not target_path.exists():
        print(f"❌ 目标不存在: {args.target}", file=sys.stderr)
        return 1

    files = engine.collect_files(target_path)
    if not files:
        print("⚠ 未找到可处理的文件")
        return 0

    mode = "扫描" if args.scan else "脱敏"
    print(f"==============================================")
    print(f" 文档脱敏工具 (desensitize v1.0.0)")
    print(f" 模式: {mode} | 目标: {target_path} | 文件数: {len(files)}")
    print(f"==============================================")

    all_findings = []
    all_stats = {}
    processed = 0

    for fp in files:
        rel_path = str(fp.relative_to(target_path) if target_path.is_dir() else fp.name)

        try:
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  ⚠ 跳过 {rel_path}: 读取失败 ({e})", file=sys.stderr)
            continue

        # 扫描模式
        if args.scan:
            findings = engine.scan_text(content, source_label=rel_path)
            if findings:
                all_findings.extend(findings)
                print(f"  📄 {rel_path} — 发现 {len(findings)} 处敏感信息")
                # 按级别汇总
                level_counts = {}
                for f_item in findings:
                    lvl = f_item["level"]
                    level_counts[lvl] = level_counts.get(lvl, 0) + 1
                for lvl, cnt in sorted(level_counts.items()):
                    print(f"       {lvl} 级: {cnt} 处")
            processed += 1
            continue

        # 脱敏模式
        new_content, stats = engine.desensitize_text(content)

        if stats:
            for k, v in stats.items():
                all_stats[k] = all_stats.get(k, 0) + v

            # 生成扫描发现用于报告
            findings = engine.scan_text(content, source_label=rel_path)
            all_findings.extend(findings)

            if args.dry_run:
                print(f"  📄 {rel_path} — 将替换 {sum(stats.values())} 处")
            else:
                # 确定输出路径
                if args.in_place:
                    out_path = fp
                elif args.output:
                    out_dir = Path(args.output)
                    if target_path.is_dir():
                        out_path = out_dir / fp.relative_to(target_path)
                    else:
                        out_path = out_dir / fp.name
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    # 默认：同目录 .desensitized 后缀
                    out_path = fp.with_suffix(fp.suffix + '.desensitized')

                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"  ✅ {rel_path} → {out_path.name if not args.output else out_path} ({sum(stats.values())} 处替换)")

            processed += 1
        else:
            if not args.scan:
                print(f"  ✓ {rel_path} — 无敏感信息")
            processed += 1

    # 生成报告
    report_path = args.report
    if not report_path:
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = "scan" if args.scan else "desensitize"
        report_path = f"{prefix}_report_{ts}.csv"

    if all_findings or all_stats:
        write_report(all_findings, all_stats, report_path)
        print(f"\n📊 报告已生成: {report_path}")

    # 汇总
    total_findings = len(all_findings)
    total_replacements = sum(all_stats.values()) if all_stats else 0

    print(f"\n──────────────────────────────────────────────")
    print(f" 处理文件: {processed} / {len(files)}")
    if args.scan:
        print(f" 发现敏感信息: {total_findings} 处")
        # 按级别统计
        level_counts = {}
        for f in all_findings:
            lvl = f["level"]
            level_counts[lvl] = level_counts.get(lvl, 0) + 1
        for lvl in ["A", "B", "C"]:
            if lvl in level_counts:
                print(f"    {lvl} 级: {level_counts[lvl]} 处")
    else:
        print(f" 总替换数: {total_replacements} 处")

    if args.json:
        import json as _json
        result = {
            "mode": "scan" if args.scan else "desensitize",
            "target": str(target_path),
            "files_total": len(files),
            "files_processed": processed,
            "findings_count": total_findings,
            "replacements_count": total_replacements,
            "report": report_path,
            "stats": all_stats,
            "dry_run": args.dry_run,
        }
        print("\n" + _json.dumps(result, ensure_ascii=False, indent=2))

    # 退出码：A 级发现 → 1（告警），B 级及以下 → 0
    a_count = sum(1 for f in all_findings if f["level"] == "A")
    if a_count > 0 and args.scan:
        return 1  # 发现 A 级敏感信息，非零退出码
    return 0


def _print_rules():
    """打印所有启用的规则"""
    print("当前脱敏规则集：")
    print(f"{'规则 ID':<25} {'级别':<6} {'状态':<6} 描述")
    print("-" * 80)
    for rid, rule in DEFAULT_RULES.items():
        enabled = "启用" if rule.get("enabled", True) else "禁用"
        level = rule.get("level", "?")
        desc = rule.get("description", "")
        print(f"{rid:<25} {level:<6} {enabled:<6} {desc}")
        for p in rule.get("patterns", []):
            print(f"  · {p['name']}: {p.get('example', '')}")
    print(f"\n共 {len(DEFAULT_RULES)} 条规则组，支持 --rules custom.json 自定义扩展")


if __name__ == '__main__':
    sys.exit(main())
