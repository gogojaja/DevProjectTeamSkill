# GitHub 访问异常处理规则

> 适用：win32 / PowerShell 5.1 环境，访问 `github.com:443` 偶发 DNS 解析到坏 IP 或全部候选 IP 不可达时使用。
> 故障现象：`Failed to connect` / `Could not connect` / `Recv failure: Connection was reset`。

## 1. 候选 IP 池（按优先级排序）

完整 DNS 资源记录见项目 `docs/github_ip_records.csv`（含 api/ssh/gist/raw/pages/Fastly CDN 等子域）。

### github.com 主站（当前解析）
```
20.205.243.166    ← 多 DNS 服务器确认（8.8.8.8/1.1.1.1/208.67.222.222）
```

### github.com 历史可达 IP（AS36459 140.82.112.0/20）
```
140.82.112.4      ← 已验
140.82.113.4      ← corpus.lantern.io 记录
140.82.114.4      ← 已验
140.82.121.4      ← 已验
```

### GitHub Pages / assets-cdn（AS36459 185.199.108.0/22）
```
185.199.108.153   ← github.io / assets-cdn
185.199.109.153
185.199.110.153
185.199.111.153
```

### raw.githubusercontent.com / github.map.fastly.net（Camo/头像/媒体 CDN）
```
185.199.108.133   ← raw / camo / avatars
185.199.109.133
185.199.110.133
185.199.111.133
```

### github.global.ssl.fastly.net（Fastly 全局 CDN）
```
162.125.34.133    ← DNS 确认
```

### Fastly 公网 IP 段（assets-cdn 走 Fastly）
```
23.235.32.0/20    151.101.0.0/16    199.232.0.0/16    146.75.0.0/17
104.156.80.0/20   140.248.64.0/18   185.31.16.0/22
```

## 2. 连通性验证流程

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

## 3. push 需带凭据 token

fine-grained PAT（Contents read/write；token 由用户提供，勿硬编码入库）：

```powershell
$url="https://gogojaja:<token>@github.com/gogojaja/DevProjectTeamSkill.git"
git remote set-url origin $url        # 临时带凭据
git push origin main
git remote set-url origin "https://github.com/gogojaja/DevProjectTeamSkill.git"  # 用完还原
```

> PowerShell 拼接 `https://user:token@host/path` 直传会损坏 URL，必须经 `git remote set-url` 传参。

## 4. 其他故障处理

- `api.github.com` 偶发 CRL 离线（`CRYPT_E_REVOCATION_OFFLINE`）为瞬时网络问题，重试即可。
- 推送成功后 `git rev-parse HEAD origin/main` 应一致（领先/落后 0）。
- 全部 IP 不可达时，建议用户使用 VPN/代理打通 GitHub 后再操作。

## 5. 数据来源

- DNS 解析：`nslookup -type=A github.com 8.8.8.8` / `1.1.1.1` / `208.67.222.222`
- GitHub Meta API：`https://api.github.com/meta`（返回完整服务 IP 段）
- Fastly 公网 IP：`https://api.fastly.com/public-ip-list`
- 社区记录：`docs/github_ip_records.csv`（含历史 IP、各子域、Fastly CDN 节点）

---

**文档版本**：v1.0.0
**最后更新**：2026-08-10
