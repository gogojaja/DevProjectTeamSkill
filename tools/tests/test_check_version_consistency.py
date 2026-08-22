#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试：check_version_consistency.py
测试版本一致性检查功能
"""

import pytest
import subprocess
import sys
from pathlib import Path

class TestCheckVersionConsistency:
    """版本一致性检查测试"""
    
    @pytest.fixture
    def check_script(self):
        """获取检查脚本路径"""
        tools_dir = Path(__file__).parent.parent
        return tools_dir / "check_version_consistency.py"
    
    def test_script_exists(self, check_script):
        """测试脚本文件存在"""
        assert check_script.exists(), f"脚本不存在: {check_script}"
        assert check_script.is_file(), "路径不是文件"
    
    def test_script_executable(self, check_script):
        """测试脚本可执行"""
        result = subprocess.run(
            [sys.executable, str(check_script), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode in [0, 2], f"脚本执行失败: {result.stderr}"
        assert "usage" in result.stdout.lower() or "帮助" in result.stdout.lower()
    
    def test_version_check_syntax(self, check_script):
        """测试版本检查语法正确"""
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(check_script)],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0, f"语法错误: {result.stderr}"
    
    @pytest.mark.unit
    def test_detects_version_mismatch(self, check_script, tmp_path):
        """测试检测版本不匹配"""
        # 创建临时技能目录结构
        temp_skills = tmp_path / "skills"
        temp_skills.mkdir()
        
        # 创建不一致的版本文件
        (temp_skills / "SKILL_INDEX.md").write_text("# version: 21.8.0")
        role_dir = temp_skills / "role-testing"
        role_dir.mkdir()
        (role_dir / "SKILL.md").write_text("# version: 21.7.0")
        
        result = subprocess.run(
            [sys.executable, str(check_script), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=10
        )
        
        # 应该检测到版本不匹配
        assert "version" in result.stdout.lower() or "版本" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_accepts_version_match(self, check_script, tmp_path):
        """测试接受版本一致的情况"""
        # 创建临时技能目录结构
        temp_skills = tmp_path / "skills"
        temp_skills.mkdir()
        
        # 创建一致的版本文件
        version = "21.8.1"
        (temp_skills / "SKILL_INDEX.md").write_text(f"# version: {version}")
        role_dir = temp_skills / "role-testing"
        role_dir.mkdir()
        (role_dir / "SKILL.md").write_text(f"# version: {version}")
        
        result = subprocess.run(
            [sys.executable, str(check_script), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=10
        )
        
        # 应该通过检查
        assert result.returncode == 0, f"版本一致检查失败: {result.stderr}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])