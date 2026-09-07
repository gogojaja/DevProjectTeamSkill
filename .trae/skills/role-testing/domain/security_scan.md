# S-05：security-scan-suite —— 安全扫描套件技能

> 关联工具：T-09 dep_vuln_scan · desensitize 脱敏扫描 · audit.py 审计检查
> 编排者：`nightly_quality_gate.py`（夜间扫描自动编排本技能）

## 1. 触发条件

用户表达「安全扫描」「夜间扫描」「发布前检查」「漏洞扫描」时加载本技能。
`nightly_quality_gate.py` 夜间扫描自动编排。

## 2. 端到端流程

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  ① T-09      │    │  ② 脱敏扫描   │    │  ③ 审计检查   │    │  ④ 聚合报告   │
│  依赖漏洞扫描 │───▶│  A/B 级检查   │───▶│  授权/边界    │───▶│  安全报告     │
│  OSV API     │    │  敏感信息      │    │  台账合规      │    │  CSV 落盘     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### 步骤 1：依赖漏洞扫描（T-09）

```sh
python tools/dep_vuln_scan.py --requirements requirements.txt --output vuln_report.csv
```

降级策略：在线 → OSV API；离线 → 标记待扫描。

### 步骤 2：脱敏扫描

```sh
python tools/desensitize/desensitize.py --scan docs/ --output desensitize_report.csv
```

检查 A 级（真实凭据）和 B 级（主机名/IP/路径）敏感信息。

### 步骤 3：审计检查

```sh
python tools/audit.py --check-boundary --check-auth
```

检查访问边界和授权登记是否合规。

### 步骤 4：聚合安全报告

汇总以上三项结果，输出安全扫描总报告。

## 3. 与 nightly_quality_gate.py 分工

| 维度 | S-05 security-scan-suite | nightly_quality_gate.py |
|---|---|---|
| 定位 | 安全扫描执行者（被编排） | 扫描编排者（调度 S-05） |
| 触发 | 手动/夜间/发布前 | 定时（凌晨 3 点）/手动 |
| 输出 | 漏洞清单 + 脱敏报告 + 审计结果 | 聚合质量报告 + 告警 |

## 4. 质量门禁

- A 级敏感信息发现 → 立即告警 + 阻断发布
- 严重 CVE 漏洞 → 告警 + 建议修复版本
- 授权过期 → 告警 + 建议续期
