# AI 助手「擅作主张」防控制度 — 实现计划（tasks.md）

> 对应 spec: `.trae/specs/ai-self-control-20260828/spec.md`

## Task 1：撰写文档 §1 事件复盘 + §2 根因分析（对应 AC-1）
- **Status**: `pending`
- **Priority**: high
- **Depends On**: 无
- **Description**:
  - 生成方案文档前 2 章：§1 事件复盘（E-01~E-05 5 行四列完整表格，红/绿判定标注清楚）；§2 根因分析（Contract/Scope/Gate/Memory 四项四 Gap 逐条给出证据链）
  - 严格基于本轮对话已发生的真实事件，不扩写、不编故事
  - 四列表头统一为「编号/时间点/用户指令/AI 实际执行/授权边界判断/是否越界/断点失效原因」（七列，含 spec 要求的四列再加编号、时间点、越界判定）
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `rule` TR-1.1: 文档中能 grep 出 E-01~E-05 共 5 个事件编号，且 E-01 行文本含「红灯越界 / 越界」字样，E-03~E-05 行含「合规 / 未越界」之一，E-04 含「主动停步 / 停步汇报」类词。
  - `rule` TR-1.2: 根因分析 4 项 Gap 齐全（Contract-Gap / Scope-Gap / Gate-Gap / Memory-Gap），每项有对应的证据描述（不是空标题）。
  - `rubric` TR-1.3: 复盘客观性；维度=是否客观呈现越界事实（回避、洗白、找借口扣分）；scale 1-5；1=明显甩锅；3=客观但多处遗漏；5=中立全面；阈值 >=4；证据=评审通读评分。

## Task 2：撰写 §3 行业最佳实践与裁剪表（对应 AC-7）
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - 汇总 6+ 外部来源，给出每条外部来源对应文档后续章节哪一个制度条款的映射
  - 表格形式：【外部出处（标题+日期+链接）/ 原主张 / 本仓库裁剪后的应用】
  - 外部出处必须覆盖 spec 背景里提到的 6 篇：CSDN 全链路工作流、Agent 工程化安全、AGENTSAFE、explainx HITL 2026、Zalt Guardrails 2026、PlanVault production checklist；可再加 AWS AGENTSEC04-BP02、EU AI Act 作为加分
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `rule` TR-2.1: 表格行数 ≥ 6（6 个不同出处），每条有标题+日期（YYYY-MM-DD）+ 超链接 + 原主张 + 裁剪应用三栏不空
  - `rubric` TR-2.2: 来源覆盖度；维度=关键制度条款是否有出处；scale 1-5；1=只有 1-2 个出处覆盖核心；3=3-5 个出处覆盖 6 段合同和分级；5=核心 6 条款每条至少一个出处；阈值 >= 4
  - `rule` TR-2.3: 所有超链接 2026-08-28 当日可达（评审用 WebFetch HEAD）

## Task 3：撰写 §4 六段执行合同 + §5 工具三层分级 + §6 审批五要素模板（对应 AC-2/3/4）
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 2
- **Description**:
  - §4 六段执行合同：理解/拆解/清单/确认/执行/复验，每段 2 句以内规则；确认段给确认词白名单（执行/OK/确认/改吧 + 方案字母编号，用户自定义也可）
  - §5 工具三层分级：Tier1 只读列 Read/Grep/LS/Glob/SearchCodebase/WebFetch 只读；Tier2 范围写列 Edit/Write（条件：项目内+本轮指令提及）；Tier3 高辐射列外部文件/删除/推送/solidify/mirror_push/publish_production，每类至少 3 个本仓库真实工具/动作名
  - §6 审批五要素模板：给出一个 6 列标准表格 + 一行示例（示例用 E-01 模型 limit 恢复的真实内容，具体到模型名和新数值），列名为 spec AC-4 规定的 6 项
- **Acceptance Criteria Addressed**: AC-2、AC-3、AC-4
- **Test Requirements**:
  - `rule` TR-3.1: §4 有 6 段小标题（理解段/拆解段/清单段/确认段/执行段/复验段）；确认段列出 ≥4 个确认词白名单；含「不接受模糊措辞」6 字
  - `rule` TR-3.2: Tier1/Tier2/Tier3 每层至少列出 3 个本仓库真实工具/动作，Tier3 明确包含外部文件写和推送类操作
  - `rule` TR-3.3: §6 有完整的审批清单模板表，表头 6 列齐全；有且至少有 1 行示例；示例行「完整改动内容」列不含「若干」「一些」「部分」模糊词（grep 过滤失败）

## Task 4：撰写 §7 参数绑定与重确认 + §8 越界识别红黄灯 + 回滚 SOP（对应 AC-5/AC-6）
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 3
- **Description**:
  - §7 参数哈希绑定：绑定对象 3 项（操作名+目标路径+改动内容 SHA 前 10 位）；变更→回确认段→新审批→旧审批作废 3 步流程；引用行业出处（PlanVault #14 / Zalt 2026）并说明裁剪
  - §8 红黄灯清单：红灯 ≥3 条（未确认即执行 / 顺带做范围外 / 参数变不重申请 / 路径越界）；黄灯 ≥2 条（清单要素不全 / 风险级标低 / 确认词模糊接受）；回滚 SOP 3 步（保全证据→还原备份→记违规次数）；包含「连续 2 次红灯进入全闸模式」一句话，并解释全闸模式=下一轮所有 Tier2/Tier3 操作必须走完整 6 段合同 + 额外再要一轮确认
- **Acceptance Criteria Addressed**: AC-5、AC-6
- **Test Requirements**:
  - `rule` TR-4.1: §7 绑定对象含 3 项（grep 命中）；回确认段流程三步明确写出；出处引用 ≥1（PlanVault 或 Zalt，带链接）
  - `rule` TR-4.2: §8 红灯条数 ≥3，黄灯 ≥2；SOP 步骤数 ≥3；grep 命中「全闸模式」4 字
  - `rubric` TR-4.3: 条款可执行性；维度=条款能否被 AI 工具前强制检查时二值判定；scale 1-5；1=大量「尽量」「应该」模糊词；3=一半是规则一半是模糊建议；5=所有红灯/黄灯/SOP 都有明确判定词，可直接转成 prompt 约束；阈值 >= 4

## Task 5：撰写 §9 落地路径（文档化不执行）+ 附录 A 确认词模板 + 附录 B 常见问答
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 4
- **Description**:
  - §9 落地路径：列出 5 类可实施动作的具体目标文件、动作描述、估计会话次数，但明确写"不在本轮执行——请在后续独立会话中申请"：① Prompt / 系统提示词钉死（在 dev-project-team-skill SKILL.md 增加 3 条铁律段落）；② 用户偏好硬边界强化（将 6 段合同摘要写进 user_profile.md 开头摘要段，避免摘要截断漏看）；③ 项目铁律《项目铁律.md》追加"AI 操作合同"段；④ 审计台账 13/14 扩展列（参数哈希列、确认词留痕列）——文档化定义；⑤ pre-commit 钩子加一个「本次 commit 消息中是否含 AI 操作相关变更，必须有确认词留痕」的可选检查（不强制）
  - 附录 A：给 AI 用的「输出审批清单时的固定模板」—— 一段可复制粘贴的 Markdown 表格模板
  - 附录 B：常见问答 3 条（Q1"只读操作要不要清单"、Q2"用户说'改了就行'算不算确认词"→算绿灯但建议仍然清单→确认的提示；Q3"全闸模式持续多久？—— 1 次完整合规操作后解除）
- **Acceptance Criteria Addressed**: AC-8（文档结构合规，不包含可执行代码）
- **Test Requirements**:
  - `rule` TR-5.1: §9 落地路径 5 类动作齐全，每类带"明确不执行"声明
  - `rule` TR-5.2: 附录 A/B 存在；附录 A 模板表格有 6 列；附录 B 至少 3 条问答
  - `rule` TR-5.3: 全文不出现任何代码块（```python / ```bash），除了附录 A 的 Markdown 示例（```markdown）和必要的 JSON 配置示例（```jsonc，且明确标注为"仅示例，不执行"）；没有 .py/.sh 代码内容

## Task 6：文档审校收尾 + 推送前 diff 预检（对应 AC-8）
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1–5
- **Description**:
  - 通读全文，校验：语言全中文（代码标识符/模型名除外）；TOC 标题与内容一致；引用链接与 §3 出处一致；字数≤6,000 中文（正文不含表格代码）
  - 输出最终方案文档到 `docs/AI助手行为门禁与授权合同.md`（默认名，Approve gate 若有改动则用新名）
  - `git diff --stat` 预检确保本次新增/修改只涉及方案文档、spec 产物，不含 .py/.sh、不涉及外部文件痕迹
  - 生成《门禁执行单模板 csv》副本到 `docs/AI助手行为门禁-执行单模板.csv`（UTF-8 BOM），供实际使用
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `rule` TR-6.1: 最终方案文档 `docs/AI助手行为门禁与授权合同.md` 存在，且 `wc -m` 正文中文字段（不含表格）≤6000
  - `rule` TR-6.2: git diff --stat 统计结果中新增/修改文件清单：全部是 .md / .csv，不包含任何 .py/.sh/.jsonc 外的代码/配置文件；**特别要求**：不包含 `~/.config` 或任何绝对路径的外部文件
  - `rule` TR-6.3: `docs/AI助手行为门禁-执行单模板.csv` 存在，表头有 6 列（对齐审批要素 6 列），有一行示例（与正文附录 A 一致）
  - `rubric` TR-6.4: 文档整体可读性；维度=5 分钟能否快速读通核心 6 段合同流程；scale 1-5；1=结构混乱；3=需跳读找重点；5=目录/表格/加粗提示丰富，一目了解；阈值 >= 4
