# 文档脱敏工具（desensitize）

> 版本：v1.1.0  
> 依据：`iron_rules.md` §3 敏感信息三级处理（A/B/C 级）＋ 脱敏字典文档

通用文档脱敏小工具，可在各项目中独立调用。支持扫描检测、批量脱敏、自定义规则、**脱敏字典**、生成 CSV 报告。

## 功能特性

- **三级分级**：A 级（密钥/Token/密码，告警）、B 级（IP/路径/邮箱，脱敏入库）、可扩展 C 级
- **脱敏字典**：`desensitize_dictionary.csv` 关键字集（子串匹配）+ `--dictionary` 参数自动并入，见 `DESENSITIZE_DICTIONARY.md`
- **两种模式**：扫描模式（只读检测）+ 脱敏模式（自动替换）
- **批量处理**：支持单个文件或整个目录，自动识别文本文件
- **报告输出**：CSV 格式（UTF-8 with BOM），含位置/级别/类型/替换统计
- **可扩展规则**：JSON 格式自定义规则，与默认规则合并
- **跨平台**：Python 实现，Windows/macOS/Linux 通用

## 快速开始

### 扫描模式（安全，不修改文件）

```bash
# 扫描单个文件
python tools/desensitize/desensitize.py --scan document.md

# 扫描整个目录并生成报告
python tools/desensitize/desensitize.py --scan ./docs --report scan_result.csv

# 仅检查 A 级（密钥/Token）
python tools/desensitize/desensitize.py --scan --level A ./src
```

### 脱敏模式

```bash
# 脱敏到输出目录（推荐）
python tools/desensitize/desensitize.py ./docs -o ./docs_safe

# 原地替换（危险，请先备份）
python tools/desensitize/desensitize.py --in-place config.yaml

# 预览将替换的内容（不写入）
python tools/desensitize/desensitize.py --dry-run ./src
```

### 脱敏字典（关键字集）

```bash
# 单文件脱敏到输出目录（规则 + 字典联合替换）
python tools/desensitize/desensitize.py --dictionary desensitize_dictionary.csv ./doc.md -o ./doc_safe

# 扫描时同时按字典检测
python tools/desensitize/desensitize.py --dictionary desensitize_dictionary.csv --scan ./docs

# 字典 + 命令行临时关键字
python tools/desensitize/desensitize.py --dictionary desensitize_dictionary.csv --keywords "内部代号,张三" ./doc.md
```

- 字典文件格式与维护详见 **[脱敏字典文档 `DESENSITIZE_DICTIONARY.md`](./DESENSITIZE_DICTIONARY.md)**
- CSV 列：`keyword, level, replacement, type, description`（UTF-8 with BOM，`#` 开头为注释）

### 自定义规则

```bash
python tools/desensitize/desensitize.py --rules my_rules.json --scan ./docs
```

## 默认规则

| 规则组 | 级别 | 检测内容 | 替换方式 |
|--------|------|---------|---------|
| `a_secrets` | A | GitHub PAT / AWS Key / sk-密钥 / 私钥 / 密码行 | `***` 掩去 |
| `b_ipv4` | B | IPv4 地址 | `xxx.xxx.xxx.xxx` |
| `b_paths` | B | Windows/macOS/Linux 用户绝对路径 | `~/` 或 `%USERPROFILE%` |
| `b_email` | B | 邮箱地址 | 首字母+`***`@域名 |
| `b_phone_cn` | B | 中国大陆手机号 | 中间 4 位 `****` |

查看完整规则：`python tools/desensitize/desensitize.py --list-rules`

## 自定义规则格式（JSON）

```json
{
  "b_ipv4": {
    "enabled": true,
    "patterns": [
      {
        "name": "ipv4_mask_c",
        "regex": "\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b",
        "replacement": "192.168.x.x",
        "example": "192.168.1.100 → 192.168.x.x"
      }
    ]
  },
  "custom_internal_domain": {
    "level": "B",
    "description": "内部域名（自定义）",
    "enabled": true,
    "patterns": [
      {
        "name": "corp_domain",
        "regex": "\\b[a-z0-9.-]*\\.corp\\.internal\\b",
        "replacement": "***.internal",
        "example": "api.corp.internal → ***.internal"
      }
    ]
  }
}
```

规则合并逻辑：
- 规则 ID 与默认相同 → 覆盖该规则的 `enabled`/`patterns`/`exempt_patterns`
- 规则 ID 为新值 → 作为新规则加入

## 命令行参数

| 参数 | 说明 |
|------|------|
| `target` | 目标文件或目录（位置参数） |
| `--scan` | 仅扫描，不修改（安全模式） |
| `--in-place` | 原地替换（危险，先备份） |
| `-o, --output` | 输出目录 |
| `--report` | 报告 CSV 路径（默认自动生成） |
| `--rules` | 自定义规则 JSON 文件 |
| `--dictionary` | 脱敏字典 CSV（关键字集，UTF-8 with BOM） |
| `--level A/B/C` | 仅处理指定级别及以上 |
| `--dry-run` | 预览模式，不写入 |
| `--include-ext` | 额外包含的扩展名，逗号分隔 |
| `--exclude-dir` | 额外排除的目录，逗号分隔 |
| `--list-rules` | 列出所有规则后退出 |
| `--json` | 以 JSON 输出统计结果 |

## 退出码

- `0`：正常完成（扫描模式无 A 级发现 / 脱敏模式完成）
- `1`：扫描模式发现 A 级敏感信息（告警）
- 其他：参数错误或文件读取失败

## 与 iron_rules.md 对齐说明

- **A 级（禁止入库）**：发现即告警，退出码非零，CI 中可阻断提交
- **B 级（脱敏入库）**：自动替换为脱敏值，提交前复查确认无残留
- **默认行为**：IP 完全脱敏（`xxx.xxx.xxx.xxx`），与 iron_rules §3.1 默认策略一致
- **豁免机制**：已脱敏标记（`xxx.` 开头、`~/`、`%VAR%` 等）自动跳过

## 与 pre-commit 钩子的关系

- `.githooks/pre-commit` 做提交级快速检查（A 级密钥 + B 级路径/IP 快速扫描）
- 本工具做**文档级全面脱敏**（更丰富的规则、支持批量处理、生成详细报告）
- 两者互补：pre-commit 是门禁，desensitize 是主动处理工具
