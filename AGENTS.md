# AGENTS.md

## 项目定位

DevProjectTeamSkill：软件研发全生命周期多角色编排技能库（8 个角色包 + 1 个编排器）。本体即技能源码，不是业务应用。AI Agent 在本仓库的职责是**维护技能库本身**（skill 编写/结构/打包/部署），不是执行软件项目业务。

## 仓库结构

```
.trae/skills/         技能源码（唯一事实来源）
  SKILL_INDEX.md      8 包路由索引
  references/         公共标准（token/csv/api 契约等）
  shared/             单源共享库：governance/evolution/authoring + references 副本
  dev-project-team-skill/   编排器（薄壳）
  role-*/             SKILL.md(根) + domain/ 流程 + *__resources/ 明细
tools/                打包/部署/固化脚本（.sh + .py 双实现）
交接文档.md            跨会话断点，改动后必须刷新
opencode.json         opencode 技能注册
```

## 核心规则（违反即返工）

1. **源码单源**：`.trae/skills/` 是唯一事实来源，`tools/deploy_skills.py`/`solidify.py` 均以它为源；共享内容只存 `shared/`，角色包用 `../shared/...` 相对引用；**禁止手工复制** shared/references 进角色包（打包时自动内嵌）。
2. **源码不备覆盖**：deploy 目标是 `.github/skills/`、`.claude/skills/`、`.agents/skills/` 及全局库（Windows：`C:\Users\<user>\.config\opencode\skills`；macOS/Linux：`~/.config/opencode/skills`），**永不覆盖 `.trae/skills/`**；改技能只在 `.trae/skills/` 源操作，改完即跑 `solidify` 部署到目标目录。
3. **新增/修改技能**：必须同步 `SKILL_INDEX.md` + `references/api_contracts.md`；description 150~250 字符（`做什么。<触发词>。Load when...`）。
4. **输出格式**：>4K token 或 >20 列 → CSV（UTF-8 with BOM）；仅回显首 5 行 + 行数。禁止 .xlsx。
5. **改动后固化**：任务完成执行 `tools/solidify.sh "<说明>"` 并刷新 `交接文档.md` 断点区，然后 git commit。
6. **文件保护**：无明确指令禁止删除/移动/重命名文件。
7. **系统/项目外文件铁律**：修改、删除**系统文件（如 %windir%\System32、hosts、注册表）或项目外部文件（仓库之外路径）**必须：①先获得用户明确授权；②操作前强制备份到项目内 `.backup/`（含时间戳）；③操作留痕至 `13_安全审计台账.csv`。未获授权或未备份，一律禁止执行。该操作必须经 `security_audit` 前置审计。
8. **环境信息脱敏铁律**：本机/环境专属信息（**主机名、IP、用户名、绝对路径**）在提交 GitHub 等公共仓库前**必须脱敏**——IP 完全脱敏为默认（`192.168.x.x`→`xxx.xxx.xxx.xxx`），保留主机名须用户授权；脱敏后复查全文确认无真实值残留。细则见 `.trae/skills/references/iron_rules.md` §3.1。违反即禁止提交。

## 命令

```sh
bash tools/package_skills.sh            # 打包全部 8 角色包到 dist/
bash tools/package_skills.sh --role role-testing
bash tools/deploy_skills.sh --roles role-a,role-b
bash tools/solidify.sh "说明"
python tools/excel_to_csv.py            # 迁移存量 xlsx→csv
git commit                              # 每原子改动一次提交
```

## GitHub 访问异常处理规则（win32，PowerShell 环境）

本机访问 `github.com:443` 偶发 DNS 解析到坏 IP 或全部候选 IP 不可达。故障现象：`Failed to connect` / `Could not connect` / `Recv failure: Connection was reset`。

### 1. 候选 IP 池（按优先级排序）

完整 DNS 资源记录见 `docs/github_ip_records.csv`（含 api/ssh/gist/raw/pages/Fastly CDN 等子域）。

**github.com 主站（当前解析）：**
```
20.205.243.166    ← 多 DNS 服务器确认（8.8.8.8/1.1.1.1/208.67.222.222）
```

**github.com 历史可达 IP（AS36459 140.82.112.0/20）：**
```
140.82.112.4      ← 已验
140.82.113.4      ← corpus.lantern.io 记录
140.82.114.4      ← 已验
140.82.121.4      ← 已验
```

**GitHub Pages / assets-cdn（AS36459 185.199.108.0/22）：**
```
185.199.108.153   ← github.io / assets-cdn
185.199.109.153
185.199.110.153
185.199.111.153
```

**raw.githubusercontent.com / github.map.fastly.net（Camo/头像/媒体 CDN）：**
```
185.199.108.133   ← raw / camo / avatars
185.199.109.133
185.199.110.133
185.199.111.133
```

**github.global.ssl.fastly.net（Fastly 全局 CDN）：**
```
162.125.34.133    ← DNS 确认
```

**Fastly 公网 IP 段（assets-cdn 走 Fastly）：**
```
23.235.32.0/20    151.101.0.0/16    199.232.0.0/16    146.75.0.0/17
104.156.80.0/20   140.248.64.0/18   185.31.16.0/22
```

### 2. 连通性验证流程

```powershell
# 逐个测试候选 IP（超时 8 秒）
$ips = @("20.205.243.166","140.82.112.4","140.82.113.4","140.82.114.4","140.82.121.4","185.199.108.153")
foreach ($ip in $ips) {
  $r = curl.exe -s -o NUL -w "%{http_code}" --connect-timeout 8 --resolve github.com:443:$ip https://github.com
  Write-Output "$ip -> $r"
}
```

```powershell
# 尝试刷新本地 DNS 缓存
ipconfig /flushdns
```

```powershell
# 如全部不可达，用 --resolve 强制绑定可达 IP 执行 git 操作
curl.exe -s --resolve github.com:443:140.82.112.4 https://github.com
```

### 3. push 需带凭据 token（fine-grained PAT，Contents read/write；token 由用户提供，勿硬编码入库）

```powershell
$url="https://gogojaja:<token>@github.com/gogojaja/DevProjectTeamSkill.git"
git remote set-url origin $url        # 临时带凭据
git push origin main
git remote set-url origin "https://github.com/gogojaja/DevProjectTeamSkill.git"  # 用完还原
```

> PowerShell 拼接 `https://user:token@host/path` 直传会损坏 URL，必须经 `git remote set-url` 传参。

### 4. 其他故障处理

- `api.github.com` 偶发 CRL 离线（`CRYPT_E_REVOCATION_OFFLINE`）为瞬时网络问题，重试即可。
- 推送成功后 `git rev-parse HEAD origin/main` 应一致（领先/落后 0）。
- 全部 IP 不可达时，建议用户使用 VPN/代理打通 GitHub 后再操作。

### 5. 数据来源

- DNS 解析：`nslookup -type=A github.com 8.8.8.8` / `1.1.1.1` / `208.67.222.222`
- GitHub Meta API：`https://api.github.com/meta`（返回完整服务 IP 段）
- Fastly 公网 IP：`https://api.fastly.com/public-ip-list`
- 社区记录：`docs/github_ip_records.csv`（含历史 IP、各子域、Fastly CDN 节点）

## 效率约定

- 先读根 `SKILL.md` 路由表 → 命中后只读目标文件，**禁止**一次性 Read 全部文件。
- 目录内先 `ls` / 文件列表，小文件直接 Read，大文件 grep 定位后读片段。
- 日志与命令输出仅回显变更/错误，不 cat 大文件全文。
- 引用路径保持相对，避免改动后全文失效。
