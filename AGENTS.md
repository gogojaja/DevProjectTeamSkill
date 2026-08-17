# AGENTS.md

## 项目定位

DevProjectTeamSkill：软件研发全生命周期多角色编排技能库（9 个角色包 + 1 个编排器）。本体即技能源码，不是业务应用。AI Agent 在本仓库的职责是**维护技能库本身**（skill 编写/结构/打包/部署），不是执行软件项目业务。

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
7. **系统/项目外文件铁律**：修改、删除**系统文件（如 %windir%\System32、hosts、注册表）或项目外部文件（仓库之外路径，含其他项目目录）**必须：①先获得用户明确授权；②操作前强制备份到项目内 `.backup/`（含时间戳）；③操作留痕至 `13_安全审计台账.csv`。未获授权或未备份，一律禁止执行。该操作必须经 `security_audit` 前置审计。
7a. **目录访问边界铁律**：本项目可读写/删除范围=本项目所在目录（启动时经 `declare_access_boundary` 声明入 `台账/26_访问边界.csv`）；本项目目录之外的任何访问一律经 `register_auth` 授权（`台账/14_授权登记.csv`），**未填有效期默认仅本次对话有效**，会话结束自动失效；跨会话须用户显式指定到期时间并留痕。操作目标在本项目目录外 → 先查 `26_访问边界.csv` + `14_授权登记.csv`，无授权禁止。
8. **敏感信息分级处理铁律**：敏感信息统一按三级处理（细则见 `.trae/skills/references/iron_rules.md` §3）——**A 级禁止入库**（密钥/凭据/Token 只存别名，真实值走 `.secrets/`+凭据管理器）；**B 级脱敏入库**（本机/环境专属信息——**主机名、IP、用户名、绝对路径**提交公共仓库前必须脱敏，IP 完全脱敏为默认 `192.168.x.x`→`xxx.xxx.xxx.xxx`，保留主机名须用户授权，脱敏后复查全文）；**C 级正常入库**。提交前一律自问属于哪级。违反即禁止提交。

## 命令

```sh
bash tools/package_skills.sh            # 打包全部 9 角色包到 dist/
bash tools/package_skills.sh --role role-testing
bash tools/deploy_skills.sh --roles role-a,role-b
bash tools/solidify.sh "说明"
python tools/excel_to_csv.py            # 迁移存量 xlsx→csv
bash scripts/install-hooks.sh           # 新 clone 后一键安装 pre-commit 环境门禁钩子（core.hooksPath .githooks，git 钩子不随 clone 分发，必须执行一次）
git commit                              # 每原子改动一次提交（钩子未安装时先跑 install-hooks.sh）
```

> **环境门禁钩子**：`.githooks/pre-commit` 提交前自动检查 A 级密钥/B 级脱敏/.env 与 .secrets 禁提交/大文件 >4K。失败阻断提交（`git commit --no-verify` 仅应急，不推荐）。

## GitHub 访问异常处理规则（win32 / macOS / PowerShell / zsh 环境）

本机访问 `github.com:443` 偶发 DNS 解析到坏 IP 或全部候选 IP 不可达，最常见根因是 DNS 实效，导致远端环境无法访问。故障现象：`Failed to connect` / `Could not connect` / `Recv failure: Connection was reset` / `nc: connection failed, SOCKS error 2`。

### 0. 动态补充 DNS Resource Records（ipaddress.com）

`docs/github_ip_records.csv` 的候选 IP（§1）是**静态快照，可能过期**。出现「全部候选 IP 不可达 / DNS 实效」时，**先动态刷新最新 A 记录，再决定恢复路径**：

1. **一键动态刷新**（首选；只要本机 DNS 正常即可解析，即使 `github.com:443` 被墙也能解析）：
   ```powershell
   py -3.11 tools/github_ip_refresh.py            # 系统解析器(nslookup) 动态补充
   py -3.11 tools/github_ip_refresh.py --doh      # 追加 DNS-over-HTTPS(1.1.1.1/dns.google)
   ```
   工具经系统解析器 / DoH 动态解析 `github.com / api.github.com / gist.github.com / codeload.github.com / raw.githubusercontent.com / github.global.ssl.fastly.net / assets-cdn.github.com / fastly.net / github.io` 的当前 A 记录，去重追加进 `docs/github_ip_records.csv`，并对 `github.com` 候选 IP 做可达性探测（`curl --resolve`），打印 hosts 覆盖块与 `restore_github_push.sh` 恢复命令。
2. **权威站点人工核验**（页面受 Cloudflare 挑战保护，无法自动抓取，可人工抄录后登记）：
   - https://sites.ipaddress.com/github.com/
   - https://sites.ipaddress.com/fastly.net/
   - https://sites.ipaddress.com/assets-cdn.github.com/
   
   在页面「DNS Resource Records」区读取最新 A 记录，用以下命令登记（避免手改 CSV）：
   ```powershell
   py -3.11 tools/github_ip_refresh.py --manual github.com=20.205.243.166,140.82.112.4 assets-cdn.github.com=185.199.108.153 fastly.net=151.101.0.0
   ```
3. **刷新后仍不可达**：走 §3 token 推送或 §4 VPN/代理；必要时按铁律 #7 临时 hosts 覆盖 `github.com <可达IP>`（先备份、留痕 `13_安全审计台账.csv`）。

> 设计原则：**DNS 解析与 TCP/443 可达性解耦**——`nslookup` 能解析说明 DNS 正常、问题在路由；动态刷新保证候选池始终是最新「DNS Resource Records」，而非依赖过期快照。

### 1. 候选 IP 池（按优先级排序）

优先保留真实 IP 记录；若 DNS 失效，直接用候选 IP 做临时解析回退。完整 DNS 资源记录见 `docs/github_ip_records.csv`（含 api/ssh/gist/raw/pages/Fastly CDN 等子域）。

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
# 先解除代理，避免 SOCKS/HTTP 代理造成误判
Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:ALL_PROXY -ErrorAction SilentlyContinue

# 逐个测试候选 IP（超时 8 秒）
$ips = @("20.205.243.166","140.82.112.4","140.82.113.4","140.82.114.4","140.82.121.4","185.199.108.153","162.125.34.133")
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
curl.exe -s --resolve github.com:443:20.205.243.166 https://github.com
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
- **动态刷新工具**：`tools/github_ip_refresh.py`（系统解析器 / DoH 动态补充 `docs/github_ip_records.csv`；`--manual` 登记 ipaddress.com 人工抄录）
- GitHub Meta API：`https://api.github.com/meta`（返回完整服务 IP 段）
- Fastly 公网 IP：`https://api.fastly.com/public-ip-list`
- 权威站点核验：`sites.ipaddress.com/{github.com,fastly.net,assets-cdn.github.com}`（Cloudflare 挑战保护，人工读取 DNS Resource Records）
- 社区记录：`docs/github_ip_records.csv`（含历史 IP、各子域、Fastly CDN 节点）

## 国内镜像同步（地缘风险对冲）

GitHub 为境外服务器，**网络访问不稳定 + 存在地缘政治风险**。为避免单点失联导致源码/台账无法推送或丢失，采用**国内代码托管镜像**对冲：以 Gitee（码云）为主镜像（最像 GitHub、免费导入+同步、HTTPS/SSH 稳），备选 GitCode / 阿里云效 Codeup / 腾讯工蜂 / 华为云 CodeHub / AtomGit。

### 1. 同步策略（双推为主，定时校验为辅）
- **主策略：每次提交双推** `origin`(GitHub) + `mirror`(Gitee)。用 `tools/mirror_push.py` 逐目标推送，**单目标失败不阻断另一个**，并写 `台账/32_镜像同步记录.csv` 留痕。
- **辅策略：Gitee 侧「仓库同步」** 周期性从 GitHub 拉取兜底（即使本机某次双推遗漏，也能补回）；也可在 Gitee 创建仓库时「从 GitHub 导入」。
- 不要依赖「本机定时从 GitHub 拉取再推国内」作为唯一手段——本机访问 GitHub 本身会 flapping，反而单点失败。

### 2. 凭据（铁律 #3 A 级，禁止入库）
- 国内 token（fine-grained PAT，Contents read/write）**只经环境变量 / `.secrets/` 文件 / 系统钥匙串提供**，`tools/mirror_push.py` 通过 `tools/load_secret.py` 跨平台自动装载（env > `.secrets/<name>` > macOS Keychain），并以 `url.<auth>@.insteadOf` 注入，**绝不打印、不写入仓库、不硬编码**。
- 三种提供方式（任选其一，脚本自动读取，无需手动 export）：
  - **a) 环境变量**（临时、最常用）：
    ```powershell
    # Windows (PowerShell)
    $env:GITEE_TOKEN="<从 Gitee 设置→私人令牌 读取>"; $env:GITEE_USER="gogojaja"
    py -3.11 tools/mirror_push.py
    ```
    ```bash
    # macOS / Linux (zsh/bash)
    export GITEE_TOKEN="<从 Gitee 设置→私人令牌 读取>"; export GITEE_USER="gogojaja"
    python3 tools/mirror_push.py
    ```
  - **b) 文件**（持久、gitignore 不入库）：写 `.secrets/gitee_token` 与 `.secrets/gitee_user`
  - **c) macOS Keychain**（系统级安全存储）：
    ```bash
    security add-generic-password -s gitee_token -a gogojaja -w "<token>"
    python3 tools/mirror_push.py     # 自动从钥匙串取密，无需 export
    ```
- 跨平台约定：本仓库 `tools/*.py` 均为跨平台脚本——Windows 用 `py -3.11`，macOS/Linux 用 `python3`，其余逻辑一致。

### 3. 初始化步骤（搭框架后由用户补全）
1. 在 Gitee 建仓库 `DevProjectTeamSkill`（建议「从 GitHub 导入」或空仓）；
2. 添加 remote：`git remote add mirror https://gitee.com/<user>/DevProjectTeamSkill.git`；
3. 配置凭据：把 `GITEE_TOKEN` 放入系统凭据管理器 / `.secrets/gitee_token`（仓库已 gitignore `.secrets/`）；
4. 此后统一用 `py -3.11 tools/mirror_push.py` 替代裸 `git push`（脚本会自动跳过未配置的 remote，框架阶段不报错阻断）。

### 4. 同步台账
- `台账/32_镜像同步记录.csv`（UTF-8 BOM）：同步编号 / 同步时间 / 源commit / 目标remote / 远程URL(脱敏) / 状态 / 耗时秒 / 说明。每次双推追加，便于审计与故障回溯。

## 效率约定

- 先读根 `SKILL.md` 路由表 → 命中后只读目标文件，**禁止**一次性 Read 全部文件。
- 目录内先 `ls` / 文件列表，小文件直接 Read，大文件 grep 定位后读片段。
- 日志与命令输出仅回显变更/错误，不 cat 大文件全文。
- 引用路径保持相对，避免改动后全文失效。
