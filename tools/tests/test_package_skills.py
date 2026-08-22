#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试：package_skills.py
测试技能打包功能
"""

import pytest
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

class TestPackageSkills:
    """技能打包测试"""
    
    @pytest.fixture
    def package_script(self):
        """获取打包脚本路径"""
        tools_dir = Path(__file__).parent.parent
        return tools_dir / "package_skills.py"
    
    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """临时工作空间"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        # 创建模拟的技能目录结构
        skills_dir = workspace / "skills"
        skills_dir.mkdir()
        
        # 创建 SKILL_INDEX.md
        (skills_dir / "SKILL_INDEX.md").write_text("""
# SKILL_INDEX
| # | 角色包 | 域 | 触发词 | 加载路径 |
|---|--------|-----|--------|----------|
| 1 | role-testing | 测试 | 测试策略/计划/用例 | role-testing/ |
""")
        
        # 创建角色包目录
        role_dir = skills_dir / "role-testing"
        role_dir.mkdir()
        (role_dir / "SKILL.md").write_text("# version: 21.8.1\n测试角色包")
        
        yield workspace, skills_dir
        
        # 清理
        if workspace.exists():
            shutil.rmtree(workspace)
    
    def test_script_exists(self, package_script):
        """测试脚本文件存在"""
        assert package_script.exists(), f"脚本不存在: {package_script}"
        assert package_script.is_file(), "路径不是文件"
    
    def test_script_executable(self, package_script):
        """测试脚本可执行"""
        result = subprocess.run(
            [sys.executable, str(package_script), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode in [0, 2], f"脚本执行失败: {result.stderr}"
    
    def test_script_syntax(self, package_script):
        """测试脚本语法正确"""
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(package_script)],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0, f"语法错误: {result.stderr}"
    
    @pytest.mark.unit
    def test_creates_dist_directory(self, package_script, temp_workspace):
        """测试创建 dist 目录"""
        workspace, skills_dir = temp_workspace
        dist_dir = workspace / "dist"
        
        result = subprocess.run(
            [sys.executable, str(package_script), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(workspace),
            timeout=30
        )
        
        # --dry-run 模式下应该不创建实际文件
        # 但应该显示将要创建的文件
        assert "dist" in result.stdout.lower() or "打包" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_respects_role_filter(self, package_script, temp_workspace):
        """测试角色过滤"""
        workspace, skills_dir = temp_workspace
        
        result = subprocess.run(
            [sys.executable, str(package_script), "--role", "role-testing", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(workspace),
            timeout=30
        )
        
        assert "role-testing" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_generates_package_info(self, package_script, temp_workspace):
        """测试生成包信息文件"""
        workspace, skills_dir = temp_workspace
        
        result = subprocess.run(
            [sys.executable, str(package_script), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(workspace),
            timeout=30
        )
        
        # 应该包含包信息（文件数、大小等）
        assert "文件" in result.stdout or "file" in result.stdout.lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])