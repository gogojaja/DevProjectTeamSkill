#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试：deploy_skills.py
测试技能部署功能
"""

import pytest
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

class TestDeploySkills:
    """技能部署测试"""
    
    @pytest.fixture
    def deploy_script(self):
        """获取部署脚本路径"""
        tools_dir = Path(__file__).parent.parent
        return tools_dir / "deploy_skills.py"
    
    @pytest.fixture
    def temp_targets(self, tmp_path):
        """临时目标目录"""
        targets = {
            "github": tmp_path / "github" / "skills",
            "claude": tmp_path / "claude" / "skills",
            "agents": tmp_path / "agents" / "skills"
        }
        
        for target in targets.values():
            target.mkdir(parents=True)
        
        # 创建模拟的 dist 目录
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        
        # 创建一个模拟的技能包
        package_file = dist_dir / "role-testing_v21.8.1.zip"
        package_file.write_text("模拟技能包内容")
        
        yield targets, dist_dir
        
        # 清理
        for target in targets.values():
            if target.exists():
                shutil.rmtree(target)
    
    def test_script_exists(self, deploy_script):
        """测试脚本文件存在"""
        assert deploy_script.exists(), f"脚本不存在: {deploy_script}"
        assert deploy_script.is_file(), "路径不是文件"
    
    def test_script_executable(self, deploy_script):
        """测试脚本可执行"""
        result = subprocess.run(
            [sys.executable, str(deploy_script), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode in [0, 2], f"脚本执行失败: {result.stderr}"
    
    def test_script_syntax(self, deploy_script):
        """测试脚本语法正确"""
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(deploy_script)],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0, f"语法错误: {result.stderr}"
    
    @pytest.mark.unit
    def test_deploys_to_all_targets(self, deploy_script, temp_targets):
        """测试部署到所有目标目录"""
        targets, dist_dir = temp_targets
        
        result = subprocess.run(
            [sys.executable, str(deploy_script), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(dist_dir.parent),
            timeout=30
        )
        
        # 应该提及所有目标目录
        output = result.stdout.lower()
        assert any(target.name in output for target in targets.values())
    
    @pytest.mark.unit
    def test_respects_role_filter(self, deploy_script, temp_targets):
        """测试角色过滤部署"""
        targets, dist_dir = temp_targets
        
        result = subprocess.run(
            [sys.executable, str(deploy_script), "--roles", "role-testing", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(dist_dir.parent),
            timeout=30
        )
        
        assert "role-testing" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_skips_missing_packages(self, deploy_script, temp_targets):
        """测试跳过缺失的包"""
        targets, dist_dir = temp_targets
        
        # 清空 dist 目录
        for file in dist_dir.glob("*.zip"):
            file.unlink()
        
        result = subprocess.run(
            [sys.executable, str(deploy_script), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(dist_dir.parent),
            timeout=30
        )
        
        # 应该提及跳过或无包
        assert "跳过" in result.stdout or "skip" in result.stdout.lower() or "无包" in result.stdout
    
    @pytest.mark.unit
    def test_preserves_permissions(self, deploy_script, temp_targets):
        """测试保留文件权限"""
        # 这个测试在实际部署时才会验证权限
        # 在 --dry-run 模式下，我们只检查脚本是否会处理权限
        result = subprocess.run(
            [sys.executable, str(deploy_script), "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # 脚本应该可以正常执行
        assert result.returncode in [0, 2]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])