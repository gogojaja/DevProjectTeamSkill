# 脱敏字典文档（Desensitize Dictionary）

> 版本：v1.0.0　创建：2026-08-19
> 依据：`iron_rules.md` §3 敏感信息三级处理（A/B/C 级）+ `tools/desensitize/desensitize.py` 规则集

本字典是「文档脱敏」的统一依据与执行清单：当需要对某个文档/目录脱敏时，**同时按脱敏规则（正则）与脱敏字典关键字（字面匹配）进行脱敏**，二者合并后一次性执行。

---

## 1. 用法速查

```bash
# 扫描目标文件/目录，按 脱敏规则 + 脱敏字典 联合检测（只读，不修改）
python3 tools/desensitize/desensitize.py --dictionary tools/desensitize/desensitize_dictionary.csv --scan <目标>

# 脱敏到输出目录（推荐，保留原件）
python3 tools/desensitize/desensitize.py --dictionary tools/desensitize/desensitize_dictionary.csv <目标> -o <输出>

# 脱敏字典 + 命令行临时关键字 组合（临时关键字不写入字典）
python3 tools/desensitize/desensitize.py --dictionary tools/desensitize/desensitize_dictionary.csv --keywords "内部代号,张三" <目标> -o <输出>

# 原地替换（危险，先备份；或先用 --dry-run 预览）
python3 tools/desensitize/desensitize.py --dictionary tools/desensitize/desensitize_dictionary.csv --dry-run <目标>
```

Windows 用 `py -3.11` 或 `.\tools\desensitize\desensitize.ps1` 替换 `python3`。

---

## 2. 脱敏规则（正则，由 desensitize.py 内置 + 自定义 JSON 提供）

| 规则组 | 级别 | 检测内容 | 替换方式 |
|--------|------|---------|---------|
| `a_secrets` | A | GitHub PAT / AWS Key / sk-密钥 / 私钥 / 密码行 / gitee_token / Bearer | `***` 掩去 |
| `b_ipv4` | B | IPv4 地址 | `xxx.xxx.xxx.xxx`（豁免回环/组播/已脱敏） |
| `b_paths` | B | Windows/macOS/Linux 用户绝对路径 | `%USERPROFILE%` / `~/` |
| `b_email` | B | 邮箱地址 | 首字母+`***`@域名 |
| `b_phone_cn` | B | 中国大陆手机号 | 中间 4 位 `****` |

- 完整规则可用 `--list-rules` 查看；自定义正则规则经 `--rules custom_rules.json` 并入。
- **规则与字典合并顺序**：默认正则 → `--rules` 自定义正则 → `--dictionary` 字典关键字 → `--keywords` 临时关键字。替换按级别 A→B→C 依次执行。

---

## 3. 脱敏字典（关键字集，CSV UTF-8 with BOM）

字典文件：`tools/desensitize/desensitize_dictionary.csv`

### 3.1 列定义

| 列 | 必填 | 说明 |
|----|------|------|
| `keyword` | ✅ | 要脱敏的关键字，**直接子串匹配**（兼容中文与英文），自动 re.escape |
| `level` | 空则 B | 敏感级别 `A` / `B` / `C`（A 级同时触发扫描告警退出码 1） |
| `replacement` | 空则 `***` | 替换文本 |
| `type` | 建议填 | 分类标签 `hostname` / `domain` / `project` / `username` / `secret_alias` 等（仅生成规则名用） |
| `description` | 可选 | 说明（供审计，不参与匹配） |

> 以 `#` 开头的整行视为注释，程序跳过；空行跳过。文件需 UTF-8 with BOM 保存。

### 3.2 推荐维护哪些关键字

- 内部主机名、内部域名、内网网段标识
- 内部用户名、真实姓名（员工名）
- 内部项目代号 / 编码 / 业务代号
- 内部连接串别名、内部服务名、工作区内网路径中的专属段
- 客户名 / 供应商名 / 未公开产品名

> 注意：**A 级真实值（密钥/Token/密码）本身禁止入库**。A 级关键字只用于「扫描告警 + 替换为 `***`」，真实值应走 `.secrets/` + 凭据管理器，不入字典文件。

### 3.3 维护流程

1. 打开 `desensitize_dictionary.csv`（UTF-8 with BOM，勿改编码）；
2. 按上表新增一行（keyword 必填，其余可默认）；
3. 用脱敏模式跑一遍目标，复查替换结果；
4. 若含本机/环境专属信息，提交公共仓库前复查是否还残留真实值。

---

## 4. 脱敏执行流程（当用户要求"对某文档脱敏"时）

1. **定位目标**：确认文件/目录路径；
2. **先扫描**：`--dictionary ... --scan <目标>` 产出 CSV 报告，查看命中清单与级别（A 级命中 → 退出码 1，禁止入库）；
3. **确认授权与备份**：按铁律 #7 / #8，A 级真实值不落库、B 级脱敏、对外提交先获授权；脱敏输出用 `-o` 目录或先备份；
4. **执行脱敏**：`--dictionary ... <目标> -o <输出>`（规则 + 字典联合替换）；
5. **复查全文**：确认无真实值残留（含注释、JSON 字符串、示例文本内误写）；
6. **审计留痕**：替换统计 + 报告 CSV 留存；如涉及内网/环境信息，留痕至 `13_安全审计台账.csv`。

---

## 5. 常见问题

| 问题 | 处理 |
|------|------|
| 字典不生效 | 确认路径正确、CSV 为 UTF-8 with BOM、首行健值为 keyword |
| 想临时加词不动文件 | 用 `--keywords "词1,词2"` |
| 想自定义正则 | 用 `--rules xxx.json`（格式见 `custom_rules.example.json`） |
| 扫描发现 A 级 | 退出码 1，须先处理真实值（轮换+存. .secrets/）再提交 |
| 脱敏后仍有残留 | 检查豁免规则命中（如 `xxx.` 开头、`~/`）；补字典关键字后重跑 |

---

**文档版本**：v1.0.0　**最后更新**：2026-08-19（新增脱敏字典，`--dictionary` 并入 desensitize.py）