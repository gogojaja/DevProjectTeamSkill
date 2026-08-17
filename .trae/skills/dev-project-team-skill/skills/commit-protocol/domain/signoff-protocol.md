# 签署协议：Signed-off-by / Co-authored-by / 审查签署

> 编排器：`../SKILL.md`

---

## 1. Signed-off-by (DCO 签署)

### 1.1 定义
`Signed-off-by` 是开发者对提交内容的法律声明，遵循 **Developer Certificate of Origin (DCO) v1.1**：

```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.
660 York Street, Suite 102, San Francisco, CA 94110 USA

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.

Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including
    all personal information I submit with it, including my
    sign-off) is maintained indefinitely and may be redistributed
    consistent with this project or the open source license(s)
    involved.
```

### 1.2 格式
```
Signed-off-by: Full Name <email@example.com>
```
- **姓名**：法定全名或惯用名
- **邮箱**：有效联系邮箱（建议使用项目认可的邮箱）
- **生成**：`git commit -s` 自动添加（需配置 `user.name`/`user.email`）

### 1.3 强制要求
| 场景 | 强制 |
|------|------|
| 所有正式提交 | ✅ 是 |
| PR/MR 合并提交 | ✅ 是 |
| 发布提交 | ✅ 是 |
| Revert 提交 | ✅ 是 |
| 仅格式化/重排 (style) | 建议 |
| 仅文档/注释 (docs) | 建议 |

---

## 2. Co-authored-by (协作作者)

### 2.1 定义
标记对提交有实质贡献但非主要作者的协作者，GitHub/GitLab 会在提交页面显示其头像。

### 2.2 格式
```
Co-authored-by: Full Name <email@example.com>
```
- 可多行，每行一位协作者
- 邮箱需与 GitHub/GitLab 账号关联才能正确显示头像

### 2.3 适用场景
| 场景 | 是否添加 |
|------|----------|
| 两人以上共同编程 | ✅ 是 |
| 代码审查者提出关键修改并由作者提交 | ✅ 是 |
| 设计/架构师提供核心方案 | ✅ 是 |
| 仅提出建议/意见 | ❌ 否 |
| 仅测试/验证 | 视贡献程度 |

---

## 3. 审查签署

### 3.1 代码审查签署
在 PR/MR 审查通过时，审查者在评论中签署：

```markdown
## Review Sign-off

✅ **Approved** by @reviewer-name

**Review Scope**: Full codebase / auth-module / api-contracts
**Confidence**: High
**Conditions**: None / Fix flaky test before merge

**Signed-off-by**: Reviewer Name <reviewer@example.com>
```

### 3.2 架构审查签署
```markdown
## Architecture Review Sign-off

✅ **Architecture Approved** by @architect-name

**ADR References**: ADR-012 (OAuth2), ADR-015 (Async Migration)
**Compliance**: PASS - All constraints satisfied
**Risk Acceptance**: RA-20260808-001 (E2E gap)

**Signed-off-by**: Architect Name <architect@example.com>
```

### 3.3 安全审查签署
```markdown
## Security Review Sign-off

✅ **Security Approved** by @security-engineer

**Threat Model**: STRIDE completed, no critical gaps
**SAST/DAST**: PASS (0 critical, 0 high)
**Secrets Scan**: PASS
**Compliance**: GDPR/PCI-DSS alignment verified

**Signed-off-by**: Security Engineer <security@example.com>
```

---

## 4. 签署验证自动化

### 4.1 Git Hook 验证
```bash
#!/bin/bash
# .git/hooks/commit-msg
# 验证 Signed-off-by 存在

MSG_FILE=$1
if ! grep -q "^Signed-off-by:" "$1"; then
    echo "ERROR: Missing Signed-off-by trailer"
    echo "Run 'git commit -s' to add automatically"
    exit 1
fi
exit 0
```

### 4.2 CI 验证
```yaml
# .github/workflows/dco-check.yml
name: DCO Check
on: [pull_request]
jobs:
  dco:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Check DCO
        run: |
          commits=$(git log --format="%H" ${{ github.event.pull_request.base.sha }}..HEAD)
          for sha in $commits; do
            if ! git log -1 --format="%B" $sha | grep -q "^Signed-off-by:"; then
              echo "❌ Commit $sha missing Signed-off-by"
              exit 1
            fi
          done
          echo "✅ All commits have DCO sign-off"
```

### 4.3 GitHub DCO App
```yaml
# 使用 GitHub DCO App 自动检查
# 安装: https://github.com/apps/dco
# 配置: .github/dco.yml
repos:
  - your-org/your-repo
require_signoff: true
allow_rebase: false
```

---

## 5. 签署最佳实践

### 5.1 配置全局签署
```bash
# 设置用户信息
git config --global user.name "Your Full Name"
git config --global user.email "your.email@example.com"

# 启用自动签署
git config --global commit.gpgsign true  # 可选：GPG 签名
git config --global commit.signoff true  # 自动添加 Signed-off-by
```

### 5.2 GPG 签名 (可选增强)
```bash
# 生成 GPG 密钥
gpg --full-generate-key

# 配置 Git 使用 GPG
git config --global user.signingkey <KEY_ID>
git config --global commit.gpgsign true
git config --global tag.gpgsign true

# 导出公钥到 GitHub/GitLab
gpg --armor --export <KEY_ID>
```

### 5.3 团队签署规范
| 角色 | 签署要求 |
|------|----------|
| 开发者 | 每次提交 `Signed-off-by` |
| 审查者 | PR 批准时 `Co-authored-by` 或审查签署 |
| 架构师 | 架构决策提交 `Signed-off-by` + ADR 引用 |
| 安全工程师 | 安全修复提交 `Signed-off-by` + 威胁模型引用 |
| 发布工程师 | 发布提交 `Signed-off-by` + 版本/变更日志 |
| 专案负责人 | 关键发布/风险接受 `Signed-off-by` |

---

## 6. 签署异常处理

| 异常 | 处理 |
|------|------|
| 缺少 Signed-off-by | CI 阻断，要求补充 `git commit --amend -s` |
| 邮箱不匹配 GitHub | 提示更新 `user.email` 或在 GitHub 添加邮箱 |
| 多人共用一提交 | 主作者 `Signed-off-by`，协作者 `Co-authored-by` |
| 批量提交缺少签署 | `git rebase -i` 逐个 `amend -s` 或脚本批量添加 |
| GPG 密钥过期 | 更新密钥或暂时关闭 `commit.gpgsign` |

---

**文档版本**: v1.0.0  **最后更新**: 2026-08-08