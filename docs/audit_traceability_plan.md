# 审计溯源增强 — 实施计划

> 配套设计文档：`docs/audit_traceability_design.md`
> 目标：将 13/14 台账扩展为五维溯源（会话 + 主机 + 客户端工具 + 模型 + 时间），
> 新建自动埋点助手，授权主机名明文保留，并更新铁律 #7。

---

## 里程碑总览

| 阶段 | 交付物 | 状态 |
|---|---|---|
| M1 扩展 13 表头 + 回填 | `13_安全审计台账.csv` 新 schema + 历史回填 | 待执行 |
| M2 扩展 14 表头 + 回填 + AUTH-021 | `14_授权登记.csv` + 主机名明文授权 | 待执行 |
| M3 新建 `tools/audit.py` 埋点助手 | 自动抓主机/时间、生成会话ID、写台账 | 待执行 |
| M4 AGENTS.md 铁律 #7 增补 7b | 四维定位条款落地 | 待执行 |
| M5 验证 + 提交双推 | 跑通助手写一条实测、git 提交 origin+mirror | 待执行 |
| M6（可选）哈希链/对象哈希 | tamper-evident 增强 | 路线图 |

---

## M1：扩展 13 表头 + 历史回填

**新表头（15 列）：**
```
操作ID,会话ID,主机标识,客户端工具,模型名称,操作时间,
操作类型,对象,风险等级,授权人,授权ID,是否备份,备份路径,留痕时间,结果
```

**回填规则（一次性 Python 脚本）：**
1. 读旧 CSV（9 列），按新表头映射。
2. `主机标识`：
   - 文本含 `douglas` → `douglas`（Windows 机，依据 `douglas\<user>` 推断）；
   - 属本机且 2026-08-2x 期间（macOS 操作）→ `gogojajadeMac-mini`；
   - 否则 `未知`。
3. `客户端工具` / `模型名称`：
   - 本次会话已确认行（AUD-20260827-12/13、OP-AUDIT-049/050/051）→ `opencode` / `ark-coding/deepseek-v4-flash`；
   - 其余历史行 → `未知`。
4. `操作时间`：解析旧 `留痕时间` → ISO8601+TZ：
   - `20260827233121` → `2026-08-27T23:31:21+08:00`；
   - `2026-08-28 07:33:18` → `2026-08-28T07:33:18+08:00`。
5. `会话ID`：历史行填 `未知`（无原始会话上下文）。
6. **修复 OP-AUDIT-051 转义乱码**：将字段内 `\uXXXX` 序列还原为中文（正则 `\\u([0-9a-fA-F]{4})`）。
7. 写回 UTF-8 / LF（`lineterminator="\n"`）。

---

## M2：扩展 14 表头 + 回填 + AUTH-021

**新表头（11 列）：**
```
授权ID,主机标识,授权对象,对象类型,路径,权限,授权人,授权时间,有效期至,状态,备注
```

**回填：** `主机标识` 同 M1 规则（douglas / gogojajadeMac-mini / 未知）。

**追加 AUTH-021（主机名明文保留授权）：**
```
AUTH-021, gogojajadeMac-mini, 审计/授权台账主机名明文保留, 系统/台账,
台账/13_安全审计台账.csv;台账/14_授权登记.csv, 读/写, 用户(本机),
2026-08-28, 长期, 有效,
用户明确授权-为跨机异常定位需在审计台账明文保留主机名(铁律#8 B级脱敏例外, 范围限定本仓库)
```

---

## M3：新建 `tools/audit.py` 埋点助手

**接口：**
```bash
# 关键操作审计
python3 tools/audit.py op \
  --type "修改项目外文件" \
  --target "~/.config/opencode/opencode.jsonc" \
  --risk 中 --auth AUTH-020 --backup 是 \
  --backup-path ".backup/xxx" --result "成功" \
  [--tool Trae] [--model ark-coding/deepseek-v4-flash] [--session-id <uuid>]

# 授权登记
python3 tools/audit.py auth \
  --object "..." --otype 文件 --path "..." --perm 改 \
  [--host gogojajadeMac-mini] [--valid-until 2026-08-28] [--status 有效] --note "..."
```

**行为：**
- 自动 `socket.gethostname()` → 主机标识；
- 自动 `datetime.now().astimezone().isoformat()`（含 +08:00）→ 操作时间；
- `会话ID`：参数缺失则生成 `uuid4()`；
- `模型名称`：参数缺失则读 `opencode.json` 的 `model`，再降级 `未知`；
- `操作ID`：`OP-AUDIT-<NNN>` / `AUTH-<NNN>` 自增（扫描现有最大序号）；
- 写入对应台账（UTF-8 / LF）。

---

## M4：AGENTS.md 铁律 #7 增补

在铁律 #7 后新增 **7b**：
> **7b. 审计四维定位铁律**：凡属「关键操作」（修改系统/项目外文件、授权、发布、基线固化、MCP 注册等），
> 审计台账（`台账/13_安全审计台账.csv`）**必须**记录 `主机标识 / 客户端工具 / 模型名称 / 操作时间(ISO8601+TZ)`，
> 并建议带 `会话ID` 聚合同次运行多操作；统一由 `tools/audit.py` 写入。主机名明文保留须用户授权（见 AUTH-021，铁律 #8 B 级脱敏例外）。

---

## M5：验证 + 提交双推

1. 跑 `tools/audit.py op` 写一条测试审计（如「审计schema升级验证」），确认四列有真实值、时间格式合规。
2. `git add 台账/ docs/ tools/audit.py AGENTS.md` → 提交。
3. `python3 tools/mirror_push.py` 双推 origin + mirror。
4. 核对 `git rev-parse --short HEAD` 三端一致。

---

## M6（可选路线图）
- 哈希链：每行 `前序哈希` 形成 tamper-evident 链（呼应 arXiv:2601.20727）。
- 对象前后哈希：`对象哈希(前→后)` 直接验证变更完整性。
- SIEM 导出：台账按 OTel GenAI 语义序列化推送至 Langfuse / SIEM，实现多机集中溯源。

---

## 验收标准
- [ ] 13 台账含 5 个溯源列，历史行已回填且 OP-AUDIT-051 乱码修复；
- [ ] 14 台账含 `主机标识`，AUTH-021 已登记；
- [ ] `tools/audit.py` 可独立写入 op/auth 且自动填主机/时间；
- [ ] AGENTS.md 7b 条款生效；
- [ ] 三端（本地/origin/mirror）提交一致。
