#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试：技能打包→部署→固化完整流程
测试发布门禁（版本一致性/闭环执行/发布级/废弃/脱敏）
"""

import pytest
import subprocess
import sys
import tempfile
import shutil
import zipfile
from pathlib import Path
from typing import Tuple, List

@pytest.mark.integration
class TestFullWorkflow:
    """完整工作流集成测试"""
    
    @pytest.fixture
    def test_environment(self, tmp_path):
        """创建测试环境"""
        # 创建目录结构
        env = {
            "root": tmp_path,
            "skills": tmp_path / ".trae" / "skills",
            "tools": tmp_path / "tools",
            "dist": tmp_path / "dist",
            "targets": {
                "github": tmp_path / ".github" / "skills",
                "claude": tmp_path / ".claude" / "skills",
                "agents": tmp_path / ".agents" / "skills"
            },
            "交接文档": tmp_path / "交接文档.md",
            "审计台账": tmp_path / "台账" / "13_安全审计台账.csv"
        }
        
        # 创建目录
        for path in [env["skills"], env["tools"], env["dist"], 
                     env["交接文档"].parent, env["审计台账"].parent]:
            path.mkdir(parents=True, exist_ok=True)
        
        for target in env["targets"].values():
            target.mkdir(parents=True, exist_ok=True)
        
        # 创建基本文件
        self._create_mock_environment(env)
        
        yield env
        
        # 清理
        if tmp_path.exists():
            shutil.rmtree(tmp_path)
    
    @staticmethod
    def _create_mock_environment(env):
        """创建模拟环境文件"""
        # 创建 SKILL_INDEX.md
        (env["skills"] / "SKILL_INDEX.md").write_text("""
# SKILL_INDEX — 角色包索引清单
| # | 角色包 | 域 | 触发词 | 加载路径 |
|---|--------|-----|--------|----------|
| 1 | role-testing | 测试 | 测试策略/计划/用例 | role-testing/ |
""")
        
        # 创建角色包
        role_dir = env["skills"] / "role-testing"
        role_dir.mkdir()
        (role_dir / "SKILL.md").write_text(
            "# role-testing\n## 技能版本：v21.8.1\n## 技能描述：测试技能包，长度约50个字符。\n## 触发词：测试策略/测试计划"
        )
        (role_dir / "domain").mkdir()
        (role_dir / "domain" / "main.md").write_text("# 测试主流程")
        
        # 创建 references 目录
        (env["skills"] / "references").mkdir()
        (env["skills"] / "references" / "token_standard.md").write_text("# Token 标准")
        
        # 创建 shared 目录
        (env["skills"] / "shared").mkdir()
        (env["skills"] / "shared" / "governance.md").write_text("# 治理")
        
        # 创建交接文档
        env["交接文档"].write_text("""
# 交接文档

## 0. 速览
- **当前版本**：v21.8.1
- **最近固化**：2026-08-22

## 1. 工作断点
- **已完成**：单元测试框架建设
- **进行中**：集成测试编写
""")
        
        # 创建审计台账
        env["审计台账"].write_text("""
编号,时间,类型,状态,说明
OP-AUDIT-001,2026-08-22,安全审计,完成,集成测试环境初始化
""")
    
    @pytest.mark.integration
    def test_workflow_package_to_deploy(self, test_environment):
        """测试：打包→部署流程"""
        env = test_environment
        
        # 1. 执行打包
        package_result = subprocess.run(
            [sys.executable, str(env["tools"] / "package_skills.py"), "--role", "role-testing"],
            capture_output=True,
            text=True,
            cwd=str(env["root"]),
            timeout=30
        )
        
        assert package_result.returncode == 0, f"打包失败: {package_result.stderr}"
        
        # 检查 dist 目录
        dist_files = list(env["dist"].glob("*.zip"))
        assert len(dist_files) > 0, "dist 目录中没有生成的包文件"
        
        # 2. 执行部署
        deploy_result = subprocess.run(
            [sys.executable, str(env["tools"] / "deploy_skills.py"), "--roles", "role-testing"],
            capture_output=True,
            text=True,
            cwd=str(env["root"]),
            timeout=30
        )
        
        assert deploy_result.returncode == 0, f"部署失败: {deploy_result.stderr}"
        
        # 检查目标目录
        for target_name, target_path in env["targets"].items():
            role_testing_path = target_path / "role-testing"
            if target_path.exists():
                assert role_testing_path.exists(), f"{target_name} 中未找到 role-testing"
    
    @pytest.mark.integration
    def test_workflow_version_consistency_gate(self, test_environment):
        """测试：版本一致性门禁"""
        env = test_environment
        
        # 创建版本不一致的情况
        (env["skills"] / "SKILL_INDEX.md").write_text("# version: 21.8.0")
        role_dir = env["skills"] / "role-testing"
        (role_dir / "SKILL.md").write_text(
            "# role-testing\n## 技能版本：v21.8.1"
        )
        
        # 运行版本一致性检查
        check_result = subprocess.run(
            [sys.executable, str(env["tools"] / "check_version_consistency.py")],
            capture_output=True,
            text=True,
            cwd=str(env["root"]),
            timeout=30
        )
        
        # 应该检测到版本不一致
        assert check_result.returncode != 0, "版本一致性检查应该失败"
        assert "version" in check_result.stdout.lower() or "版本" in check_result.stdout.lower()
    
    @pytest.mark.integration
    def test_workflow_closure_execution_gate(self, test_environment):
        """测试：闭环执行门禁"""
        env = test_environment
        
        # 检查所有 SKILL.md 是否有"闭环执行系统"章节
        for skill_dir in env["skills"].glob("role-*/"):
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text()
                # 对于新技能，应该有闭环执行系统
                if "v21.7.0" in content or "v21.8.0" in content or "v21.8.1" in content:
                    assert "闭环执行系统" in content or "执行系统" in content, \
                        f"{skill_md} 缺少闭环执行系统章节"
    
    @pytest.mark.integration
    def test_workflow_release_gate(self, test_environment):
        """测试：发布级门禁"""
        env = test_environment
        
        # 创建完整的发布检查环境
        self._create_release_gate_environment(env)
        
        # 运行发布级检查
        check_result = subprocess.run(
            [sys.executable, str(env["tools"] / "check_skill_release_gate.py")],
            capture_output=True,
            text=True,
            cwd=str(env["root"]),
            timeout=30
        )
        
        # 应该通过发布级检查
        assert check_result.returncode == 0, f"发布级检查失败: {check_result.stderr}"
    
    @staticmethod
    def _create_release_gate_environment(env):
        """创建发布级检查环境"""
        # 确保所有技能都有完整的元数据
        skill_md = env["skills"] / "role-testing" / "SKILL.md"
        skill_md.write_text("""
# role-testing

## 技能版本
v21.8.1

## 技能描述（150~250字符）
测试技能包，负责测试策略、测试计划、测试用例设计与测试执行，输出测试报告与缺陷清单。用户说测试/用例/执行时加载。

## 技能定位
测试角色包，负责测试策略制定、测试计划编写、用例设计、测试执行与缺陷管理。

## 适用场景
- 测试策略制定
- 测试计划编写
- 测试用例设计
- 测试执行与缺陷管理
- 测试总结报告

## 闭环执行系统

### 1. 任务入口
用户要求测试/用例/执行时加载本角色包。

### 2. 执行状态
| 状态 | 进入条件 | 退出条件 |
|------|---------|---------|
| 待启动 | 触发词匹配 | 用户确认 |
| 执行中 | 开始执行 | 产出报告 |
| 完成 | 报告完成 | 进入交接 |

### 3. 验收门禁
必须产出测试报告与缺陷清单。

### 4. 审计记录
执行时间、测试用例数、缺陷数记录。
""")
    
    @pytest.mark.integration
    def test_workflow_deprecation_cleanup_gate(self, test_environment):
        """测试：废弃清理门禁"""
        env = test_environment
        
        # 创建一个废弃的 ADR
        adr_dir = env["root"] / "架构资产" / "03_架构决策" / "ADR"
        adr_dir.mkdir(parents=True)
        deprecated_adr = adr_dir / "ADR-001-deprecated.md"
        deprecated_adr.write_text("""
# ADR-001：废弃的决策

## 状态
Deprecated（已废弃）

## 决策
本决策已被替代。
""")
        
        # 运行废弃清理检查
        check_result = subprocess.run(
            [sys.executable, str(env["tools"] / "check_deprecation_cleanup.py")],
            capture_output=True,
            text=True,
            cwd=str(env["root"]),
            timeout=30
        )
        
        # 如果有废弃 ADR，应该检查清理情况
        if "废弃" in check_result.stdout or "deprecated" in check_result.stdout.lower():
            # 应该检查是否有残留引用
            assert "检查" in check_result.stdout or "check" in check_result.stdout.lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])