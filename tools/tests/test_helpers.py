#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试基础工具类
提供通用的测试辅助功能
"""

import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

class TestHelper:
    """测试辅助工具类"""
    
    @staticmethod
    def run_python_script(
        script_path: Path,
        args: List[str] = None,
        cwd: Optional[Path] = None,
        timeout: int = 30
    ) -> Tuple[int, str, str]:
        """运行 Python 脚本
        
        Args:
            script_path: 脚本路径
            args: 命令行参数
            cwd: 工作目录
            timeout: 超时时间（秒）
            
        Returns:
            (退出码, 标准输出, 标准错误)
        """
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            timeout=timeout
        )
        
        return result.returncode, result.stdout, result.stderr
    
    @staticmethod
    def create_temp_structure(structure: dict, base_path: Path) -> Path:
        """创建临时目录结构
        
        Args:
            structure: 目录结构字典
            base_path: 基础路径
            
        Returns:
            创建的目录路径
        """
        for name, content in structure.items():
            path = base_path / name
            if isinstance(content, dict):
                path.mkdir(exist_ok=True)
                TestHelper.create_temp_structure(content, path)
            else:
                path.write_text(content)
        
        return base_path
    
    @staticmethod
    def create_mock_skill_package(
        package_name: str,
        version: str,
        temp_dir: Path
    ) -> Path:
        """创建模拟技能包
        
        Args:
            package_name: 包名
            version: 版本号
            temp_dir: 临时目录
            
        Returns:
            创建的包路径
        """
        package_dir = temp_dir / package_name
        package_dir.mkdir()
        
        # 创建 SKILL.md
        skill_md = package_dir / "SKILL.md"
        skill_md.write_text(f"# version: {version}\n模拟技能包")
        
        # 创建 domain 目录
        domain_dir = package_dir / "domain"
        domain_dir.mkdir()
        (domain_dir / "main.md").write_text("# 主流程")
        
        return package_dir
    
    @staticmethod
    def cleanup_temp_path(path: Path):
        """清理临时路径"""
        if path.exists():
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)

class ScriptTester:
    """脚本测试基类"""
    
    def __init__(self, script_path: Path):
        self.script_path = script_path
    
    def check_exists(self) -> bool:
        """检查脚本是否存在"""
        return self.script_path.exists() and self.script_path.is_file()
    
    def check_syntax(self) -> Tuple[bool, str]:
        """检查脚本语法"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(self.script_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0, result.stderr
        except Exception as e:
            return False, str(e)
    
    def run_help(self) -> Tuple[int, str, str]:
        """运行 --help 命令"""
        return TestHelper.run_python_script(
            self.script_path,
            ["--help"],
            timeout=10
        )
    
    def run_dry_run(self, cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """运行 --dry-run 模式"""
        return TestHelper.run_python_script(
            self.script_path,
            ["--dry-run"],
            cwd=cwd,
            timeout=30
        )