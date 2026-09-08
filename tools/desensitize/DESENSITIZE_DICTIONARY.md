# 脱敏字典使用指南（Desensitize Dictionary Guide）

> 版本：v1.1.0 创建：2026-08-19 更新：2026-09-08
> 依据：`iron_rules.md` §3 敏感信息三级处理（A/B/C 级）+ §3.2.7 脱敏映射安全存储

## ⚠️ 重要说明

**本仓库内的 `desensitize_dictionary.example.csv` 仅为格式示例，不含真实映射规则。**

**真实脱敏映射规则必须存储在仓库外**：

```
D:\MyProjects\.secrets\
└── desensitize_mapping.zip    # 加密 ZIP（AES-256）
    ├── current_mapping.csv    # 真实映射规则
    └── metadata.json          # 版本元数据
```

详细指南见：`D:\MyProjects\.secrets\README.md`

---

## 1. 用法速查

### 1.1 使用安全映射加载器（推荐）

```bash
# 会话开始：加载加密映射包
python tools/desensitize/secure_mapping_loader.py --load
# 🔐 请输入脱敏映射包密码: ********
# ✅ 映射加载成功（47 条规则）

# 执行脱敏（自动使用已加载的映射）
python tools/desensitize/desensitize.py --scan <目标>

# 会话结束：卸载映射
python tools/desensitize/secure_mapping_loader.py --unload
# 🔒 映射已清除
```

### 1.2 使用示例字典（仅测试/参考）

```bash
# 扫描目标文件/目录（使用示例字典，仅用于测试）
python tools/desensitize/desensitize.py --dictionary tools/desensitize/desensitize_dictionary.example.csv --scan <目标>

# 脱敏到输出目录
python tools/desensitize/desensitize.py --dictionary tools/desensitize/desensitize_dictionary.example.csv <目标> -o <输出>

# 临时关键字（不写入字典）
python tools/desensitize/desensitize.py --keywords "内部代号,张三" <目标> -o <输出>
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

## 3. 映射规则格式（CSV UTF-8 with BOM）

### 3.1 列定义

| 列 | 必填 | 说明 |
|----|------|------|
| `keyword` | ✅ | 要脱敏的关键字，**直接子串匹配**（兼容中文与英文），自动 re.escape |
| `replacement` | 空则 `***` | 替换文本 |
| `type` | 建议填 | 分类标签 `hostname` / `domain` / `project` / `username` / `secret_alias` 等 |
| `description` | 可选 | 说明（供审计，不参与匹配） |

> 以 `#` 开头的整行视为注释，程序跳过；空行跳过。文件需 UTF-8 with BOM 保存。

### 3.2 推荐维护哪些关键字

- 内部主机名、内部域名、内网网段标识
- 内部用户名、真实姓名（员工名）
- 内部项目代号 / 编码 / 业务代号
- 内部连接串别名、内部服务名、工作区内网路径中的专属段
- 客户名 / 供应商名 / 未公开产品名

> **铁律**：A 级真实值（密钥/Token/密码）本身禁止入库。真实映射规则必须存储在 `D:\MyProjects\.secrets\` 并加密保护。

---

## 4. 安全映射加载器

### 4.1 命令清单

```bash
# 加载映射（会话开始）
python tools/desensitize/secure_mapping_loader.py --load

# 卸载映射（会话结束）
python tools/desensitize/secure_mapping_loader.py --unload

# 查看映射状态
python tools/desensitize/secure_mapping_loader.py --status

# 轮换映射（建议每季度一次）
python tools/desensitize/secure_mapping_loader.py --rotate
```

### 4.2 工作原理

1. **加密存储**：映射文件打包为 AES-256 加密 ZIP
2. **会话加载**：用户输入密码解锁，解压到临时目录
3. **自动清除**：会话结束时自动删除临时文件
4. **零知识**：系统（包括 AI）在无密码时无法访问映射

### 4.3 首次创建加密映射包

详见 `D:\MyProjects\.secrets\README.md`「首次创建加密映射包」章节。

---

## 5. 脱敏执行流程（当用户要求"对某文档脱敏"时）

1. **加载映射**：`secure_mapping_loader.py --load`（如使用加密映射）
2. **定位目标**：确认文件/目录路径
3. **先扫描**：`--scan <目标>` 产出 CSV 报告，查看命中清单与级别
4. **确认授权与备份**：A 级真实值不落库、B 级脱敏、对外提交先获授权
5. **执行脱敏**：`<目标> -o <输出>`（规则 + 字典联合替换）
6. **复查全文**：确认无真实值残留
7. **卸载映射**：`secure_mapping_loader.py --unload`（会话结束）
8. **审计留痕**：替换统计 + 报告 CSV 留存

---

## 6. 常见问题

| 问题 | 处理 |
|------|------|
| 映射不生效 | 确认已执行 `--load` 加载映射，或 `--dictionary` 路径正确 |
| 想临时加词不动文件 | 用 `--keywords "词1,词2"` |
| 想自定义正则 | 用 `--rules xxx.json`（格式见 `custom_rules.example.json`） |
| 扫描发现 A 级 | 退出码 1，须先处理真实值（轮换+存 `.secrets/`）再提交 |
| 脱敏后仍有残留 | 检查豁免规则命中（如 `xxx.` 开头、`~/`）；补字典关键字后重跑 |
| 忘记密码 | 无法恢复，需重新创建映射包 |

---

## 7. 铁律要求（iron_rules.md §3.2.7）

1. **仓库外存储**：映射文件存放在 `D:\MyProjects\.secrets\`，禁止写入仓库内
2. **加密保护**：打包为 AES-256 加密 ZIP，密码由用户单独管理
3. **会话加载**：会话开始时用户输入密码加载，禁止将密码写入任何文件
4. **自动清除**：会话结束时临时文件自动删除
5. **零入库**：禁止将映射文件（含解密后的临时文件）写入仓库内

---

**文档版本**：v1.1.0 **最后更新**：2026-09-08（混合方案：示例字典 + 外部加密映射）
