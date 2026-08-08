# 發布提交：版本號/變更日誌/標籤/回滾

> 編排器：`../SKILL.md`

---

## 1. 發布提交流程

### 1.1 版本號規範 (SemVer)
```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]

示例:
  1.0.0           # 正式版
  2.1.0           # Minor 發布
  2.1.1           # Patch 修復
  3.0.0-rc.1      # Release Candidate
  2.0.0-beta.3    # Beta
  1.0.0+build.123 # Build 元數據
```

### 1.2 版本升級規則
| 變更類型 | 版本升級 | 示例 |
|----------|----------|------|
| 破壞性 API 變更 | MAJOR +1 | 1.2.3 → 2.0.0 |
| 新功能 (向後兼容) | MINOR +1 | 1.2.3 → 1.3.0 |
| Bug 修復 | PATCH +1 | 1.2.3 → 1.2.4 |
| 預發布 | 追加標識 | 1.2.3 → 1.3.0-rc.1 |

---

## 2. 發布提交格式

### 2.1 標準發布提交
```bash
release: v2.1.0

## Changelog
### Features
- feat(auth): add OAuth2 login (#1234)
- feat(api): add batch endpoint (#1256)

### Fixes
- fix(db): handle connection timeout (#1301)
- fix(ui): correct modal z-index (#1289)

### Performance
- perf(cache): add Redis layer (#1312)

### Security
- security(deps): upgrade lodash to 4.17.21 (#1298)

### Breaking Changes
- BREAKING: API v1 removed, migrate to v2 (ADR-012)

### Documentation
- docs: update migration guide v1→v2

## Metadata
Version: 2.1.0
Date: 2026-08-08
Previous: 2.0.1
Commits: 47
Contributors: 8

Signed-off-by: Release Engineer <release@example.com>
```

### 2.2 預發布提交
```bash
release: v2.2.0-rc.1

## Changelog (Pre-release)
### Features
- feat(payment): add Stripe integration (#1401)

### Fixes
- fix(webhook): handle retry logic (#1423)

## Metadata
Version: 2.2.0-rc.1
Date: 2026-08-15
Previous: 2.1.0
Type: release-candidate
RC: 1

Signed-off-by: Release Engineer <release@example.com>
```

---

## 3. 變更日誌生成

### 3.1 自動生成腳本
```python
#!/usr/bin/env python3
# generate-changelog.py
import subprocess, re, sys
from collections import defaultdict

def get_commits(since_tag: str) -> list:
    cmd = ["git", "log", f"{since_tag}..HEAD", "--pretty=format:%H|%s|%b", "--reverse"]
    output = subprocess.check_output(cmd, text=True)
    commits = []
    for line in output.strip().split('\n'):
        if not line: continue
        parts = line.split('|', 2)
        commits.append({"hash": parts[0], "subject": parts[1], "body": parts[2] if len(parts) > 2 else ""})
    return commits

def categorize(commits: list) -> dict:
    categories = defaultdict(list)
    type_map = {
        'feat': 'Features', 'fix': 'Fixes', 'perf': 'Performance',
        'security': 'Security', 'docs': 'Documentation',
        'refactor': 'Refactoring', 'perf': 'Performance',
        'test': 'Tests', 'chore': 'Chores', 'ci': 'CI/CD',
        'build': 'Build', 'config': 'Config', 'revert': 'Reverts'
    }
    for c in commits:
        m = re.match(r'^(feat|fix|perf|security|docs|refactor|test|chore|ci|build|config|revert)(\(.+\))?: ', c['subject'])
        cat = type_map.get(m.group(1), 'Other') if m else 'Other'
        categories[cat].append(c)
    return categories

def generate_changelog(categories: dict, version: str, prev_version: str) -> str:
    lines = [f"## Changelog ({version})"]
    for cat in ['Features', 'Fixes', 'Performance', 'Security', 'Breaking Changes', 'Documentation', 'Tests', 'Refactoring', 'CI/CD', 'Chores', 'Other']:
        items = categories.get(cat, [])
        if not items: continue
        lines.append(f"\n### {cat}")
        for c in items:
            # 提取 PR/Issue 引用
            refs = re.findall(r'(?:Fixes|Related|Closes)\s*[#:]?(\d+)', c['body'], re.IGNORECASE)
            ref_str = f" (#{refs[0]})" if refs else ""
            lines.append(f"- {c['subject']}{ref_str}")
    return '\n'.join(lines)

if __name__ == '__main__':
    prev = sys.argv[1] if len(sys.argv) > 1 else subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], text=True).strip()
    commits = get_commits(sys.argv[1] if len(sys.argv) > 1 else "HEAD")
    cats = categorize(commits)
    print(generate_changelog(cats, "unreleased", sys.argv[1] if len(sys.argv) > 1 else "HEAD"))
```

---

## 3. 發布自動化流程

### 2.1 發布腳本
```bash
#!/bin/bash
# release.sh - 自動化發布流程
set -e

VERSION_TYPE=${1:-patch}  # major | minor | patch | prerelease
DRY_RUN=${2:-false}

# 1. 檢查工作目錄乾淨
if [[ -n $(git status --porcelain) ]]; then
    echo "❌ Working directory not clean"
    exit 1
fi

# 2. 獲取當前版本
CURRENT=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
CURRENT=${CURRENT#v}
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

# 3. 計算新版本
case $1 in
    major) NEW_VERSION="$((MAJOR+1)).0.0" ;;
    minor) NEW_VERSION="$MAJOR.$((MINOR+1)).0" ;;
    patch) NEW_VERSION="$MAJOR.$MINOR.$((PATCH+1))" ;;
    prerelease) NEW_VERSION="$MAJOR.$MINOR.$((PATCH+1))-rc.1" ;;
    *) echo "Usage: $0 [major|minor|patch|prerelease]"; exit 1 ;;
esac

NEW_TAG="v$NEW_VERSION"
PREV_TAG="v$CURRENT"

echo "Current: v$CURRENT"
echo "New:     $NEW_TAG"
echo "Previous tag: $PREV_TAG"

if [[ "$DRY_RUN" == "true" ]]; then
    echo "🔍 DRY RUN - would create tag $NEW_TAG"
    exit 0
fi

# 3. 生成變更日誌
CHANGELOG=$(python3 tools/generate-changelog.py "$PREV_TAG")
echo "$CHANGELOG" > CHANGELOG.md

# 3. 更新版本文件
# 根據項目類型更新: package.json / pyproject.toml / Cargo.toml / go.mod / pom.xml 等
update_version_files "$NEW_VERSION"

# 3. 提交版本更新
git add -A
git commit -m "release: v$NEW_VERSION

## Changelog
$(cat CHANGELOG.md)

## Metadata
Version: ${NEW_VERSION#v}
Previous: $CURRENT
Date: $(date -u +%Y-%m-%d)

Signed-off-by: $(git config user.name) <$(git config user.email)>"

# 4. 創建標籤
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION

$(cat CHANGELOG.md | head -50)"

# 5. 推送
git push origin main
git push origin "v$NEW_VERSION"

echo "✅ Released $NEW_TAG"
```

---

## 3. 回滾流程

### 3.1 版本回滾
```bash
#!/bin/bash
# rollback.sh - 版本回滾

TARGET_VERSION=${1:-}  # 目標版本，如 v2.0.1

if [[ -z $TARGET_VERSION ]]; then
    echo "Usage: $0 <target-version>"
    echo "Example: $0 v2.0.1"
    exit 1
fi

# 1. 檢查目標標籤存在
if ! git rev-parse "refs/tags/$TARGET_VERSION" >/dev/null 2>&1; then
    echo "❌ Tag $TARGET_VERSION not found"
    exit 1
fi

# 2. 創建回滾分支
ROLLBACK_BRANCH="rollback/$(date +%Y%m%d-%H%M%S)-to-$TARGET_VERSION"
git checkout -b "$ROLLBACK_BRANCH" "$TARGET_VERSION"

# 3. 更新版本號 (添加 .rollback 後綴)
CURRENT=$(git describe --tags --abbrev=0)
NEW_VERSION="${TARGET_VERSION#v}.1-rollback"
update_version_files "$NEW_VERSION"

git add -A
git commit -m "rollback: to $TARGET_VERSION

Rollback to $TARGET_VERSION due to critical issue in current release.

Rollback-Metadata:
  From: $(git describe --tags --abbrev=0)
  To: $TARGET_VERSION
  Reason: <填寫回滾原因>
  Initiated-by: $(git config user.name)

Signed-off-by: $(git config user.name) <$(git config user.email)>"

# 4. 推送回滾分支
git push origin "$ROLLBACK_BRANCH"
echo "✅ Rollback branch created: $ROLLBACK_BRANCH"
echo "Create PR from $ROLLBACK_BRANCH to main for deployment"
```

---

## 3. 標籤管理

### 3.1 標籤命名
| 類型 | 格式 | 示例 |
|------|------|------|
| 正式發布 | `v<MAJOR>.<MINOR>.<PATCH>` | `v2.1.0` |
| RC | `v<MAJOR>.<MINOR>.<PATCH>-rc.<N>` | `v2.1.0-rc.1` |
| Beta | `v<MAJOR>.<MINOR>.<PATCH>-beta.<N>` | `v2.0.0-beta.3` |
| Alpha | `v<MAJOR>.<MINOR>.<PATCH>-alpha.<N>` | `v1.0.0-alpha.1` |
| 熱修復 | `v<MAJOR>.<MINOR>.<PATCH+1>` | `v2.0.1` |

### 3.2 標籤操作
```bash
# 創建帶註釋標籤
git tag -a v2.1.0 -m "Release v2.1.0

## Changelog
- feat: add OAuth2
- fix: connection timeout

Signed-off-by: Release Engineer"

# 推送標籤
git push origin v2.1.0

# 刪除本地/遠端標籤
git tag -d v2.1.0
git push origin :refs/tags/v2.1.0

# 列出標籤
git tag -l "v2.*" --sort=-v:refname
```

---

## 4. CI/CD 集成

### 4.1 GitHub Actions 發布
```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags:
      - 'v*'
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Generate changelog
        id: changelog
        run: |
          PREV=$(git describe --tags --abbrev=0 HEAD^)
          python3 tools/generate-changelog.py ${{ github.ref_name }} > CHANGELOG.md
          echo "changelog<<EOF" >> $GITHUB_OUTPUT
          cat CHANGELOG.md >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
      
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          tag_name: ${{ github.ref_name }}
          body: ${{ steps.changelog.outputs.changelog }}
          draft: false
          prerelease: ${{ contains(github.ref_name, '-rc') || contains(github.ref_name, '-beta') }}
          generate_release_notes: false
      
      - name: Deploy
        if: github.ref_type == 'tag' && !contains(github.ref_name, '-rc') && !contains(github.ref_name, '-beta')
        run: |
          # 部署腳本
          ./deploy.sh ${{ github.ref_name }}
```

---

## 5. 版本文件同步

### 5.1 多語言版本文件更新
```python
# update_version_files.py
import sys, json, toml, xml.etree.ElementTree as ET, re, yaml

def update_version(version: str):
    v = version.lstrip('v')
    
    # package.json
    update_json('package.json', {'version': v})
    
    # pyproject.toml
    update_toml('pyproject.toml', {'project': {'version': v}})
    
    # Cargo.toml
    update_toml('Cargo.toml', {'package': {'version': v}})
    
    # go.mod (手動或 go mod edit)
    # go.mod 通常不直接編輯版本
    
    # pom.xml
    update_xml('pom.xml', './/version', v)
    
    # setup.py / setup.cfg
    # 通常從 pyproject.toml 讀取
    
    # Dockerfile
    update_dockerfile('Dockerfile', v)
    
    # .version 文件
    with open('.version', 'w') as f:
        f.write(v + '\n')

def update_json(path, data):
    with open(path) as f: content = json.load(f)
    content.update(data)
    with open(path, 'w') as f: json.dump(content, f, indent=2)

def update_toml(path, data):
    with open(path) as f: content = toml.load(f)
    def deep_update(d, u):
        for k, v in u.items():
            if isinstance(v, dict) and k in d:
                deep_update(d[k], v)
            else:
                d[k] = v
    deep_update(content, data)
    with open(path, 'w') as f: toml.dump(content, f)

def update_xml(path, xpath, value):
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}
    for elem in root.findall(xpath, ns):
        elem.text = value
    tree.write(path, encoding='utf-8', xml_declaration=True)

def update_dockerfile(path, version):
    with open(path) as f: lines = f.readlines()
    with open(path, 'w') as f:
        for line in lines:
            if line.startswith('LABEL version='):
                f.write(f'LABEL version="{version}"\n')
            elif 'ARG VERSION=' in line:
                f.write(f'ARG VERSION={version}\n')
            else:
                f.write(line)

if __name__ == '__main__':
    update_version(sys.argv[1])
```

---

**文檔版本**: v1.0.0  **最後更新**: 2026-08-08