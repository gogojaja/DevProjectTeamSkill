# Review 第三方多视角评审（FULL）

> 归属：`../SKILL.md` §2.2.4b　版本：v1.2.0

## 1. 目的
对高风险决策方案做多视角评审，收敛形成最优；本库语境下为「多视角自评（非真实第三方）」，必须显式申明并补充真实外部信号。

## 2. 视角集（决策选型专用，缺省 3 视角）
| 视角 | 聚焦 | 输出 |
|------|------|------|
| 架构/技术路线一致性 | 方案是否符合技术路线、可演进性、接口边界 | SIGNED_OFF/FAIL + 意见 |
| 安全合规 | 威胁、合规、敏感信息、数据保护 | SIGNED_OFF/FAIL + 意见 |
| 成本+可演进性 | 实施/维护成本、长期演进、替换成本 | SIGNED_OFF/FAIL + 意见 |
| 性能（按需，决策选型 ≤3+1） | 延迟/吞吐/资源/扩展性 | SIGNED_OFF/FAIL + 意见 |

> 评审对象真是"代码/文档"时，复用 `multi-perspective-validation` 原装五视角（Architect/CodeReviewer/Security/Test/Performance），并行上限沿用 MPV 5。

## 3. 评审动作
1. **缺省串行（单模型）**：3 视角合并为一次连贯评审（只做对照证据+反向信号，不做独立并行仪式）；仅 team-orchestration 真并行/多模型时独立并行且启用防 conformity
2. **显式申明**：报告头部写明「多视角自评，非真实第三方；如需真实第三方，请用户指定外部评审人或转人工」
3. **真实外部信号（必修，≥1 条）**：
   - 真实工具核验（实际编译/测试/跑脚本）
   - 官方文档版本比对（webfetch 核验实际版本与 claim 一致）
   - 人工复核签署**移到交付后**作最终 sign-off，不作评审前置（方案未交付前用户无法签署）
   - 缺失 → 该评审标记「未完成」
4. **严重度判据（引用 MPV rubric）**：high=影响范围大或不可逆/高概率/强不可逆；medium=可逆但影响模块；low=文档级/可回退。无 rubric 不得以"高严重度"升级人工
5. **裁决规则**：
   - 证据加权（T1/T2 来源数）优先于自我反思
   - 外部信号 > 内部自评
   - 平票：由收敛者裁定，强制记录反信号
   - 平票仅限技能内视角；跨角色/跨技能方案冲突升级 `team-orchestration` priority-arbitration（P0~P6）
6. **防 conformity**：仅真并行（多 Worker / 多模型）时启用匿名化+防翻转显式提示；串行执行时不做仪式化防翻转，只保留对照证据与反向信号检查

## 4. 产物
```markdown
# 多视角评审报告（FULL）
- 模式：多视角自评（声明确认）＋外部信号清单
- 决策：SIGNED_OFF / CHANGES_REQUESTED / BLOCKED
- 意见清单：CR-001..（观点 | 严重度 | 证据引用 | status: new|ack|closed|deferred）
```
- **决策聚合（引 MPV 决策矩阵）**：全视角 SIGNED_OFF→SIGNED_OFF；1 视角 FAIL→CHANGES_REQUESTED；≥2 视角 FAIL 或任意 ERROR→BLOCKED；BLOCKED 未经人工确认禁止交付
- 报告 CSV 按 MPV `token_standard` §3 规范（UTF-8 BOM）命名 `评审报告_<对象>_<版本>_<…>.csv` 存项目根，仅回显首 5 行

## 5. 门禁
- 缺失真实外部信号 → 评审记为「未完成」，不可作为 SIGNED_OFF 依据
- 报告落盘前跑 `desensitize.py` A/B 级扫描（内网 URL/IP/密钥三查）
- CHANGES_REQUESTED 与 BLOCKED 均计入 ≤2 轮收敛；第 2 次 BLOCKED 强制人工确认
- 未经人工确认不得交付 BLOCKED 原方案