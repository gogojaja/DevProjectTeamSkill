#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全映射加载器（Secure Mapping Loader）

从加密 ZIP 加载脱敏映射规则，会话结束后自动清除。
符合 iron_rules.md §3.2.7 脱敏映射安全存储要求。

用法：
    # 加载映射（会话开始）
    python secure_mapping_loader.py --load
    
    # 卸载映射（会话结束）
    python secure_mapping_loader.py --unload
    
    # 查看映射状态
    python secure_mapping_loader.py --status
    
    # 轮换映射（手动，建议每季度一次）
    python secure_mapping_loader.py --rotate

作者：DevProjectTeamSkill
版本：v1.0.0
日期：2026-09-08
"""

import os
import sys
import zipfile
import tempfile
import shutil
import getpass
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict


class SecureMappingLoader:
    """安全映射加载器：从加密 ZIP 加载，会话结束后自动清除"""
    
    DEFAULT_ZIP_PATH = Path(r"D:\MyProjects\.secrets\desensitize_mapping.zip")
    STATE_FILE = Path(tempfile.gettempdir()) / "desensitize_mapping_state.json"
    
    def __init__(self, zip_path: Optional[Path] = None):
        self.zip_path = zip_path or self.DEFAULT_ZIP_PATH
        self.mapping: Dict[str, str] = {}
        self.temp_dir: Optional[Path] = None
        self.metadata: Dict = {}
    
    def load(self) -> bool:
        """从加密 ZIP 加载映射（需用户输入密码）"""
        if not self.zip_path.exists():
            print(f"❌ 映射包不存在: {self.zip_path}")
            print("   请先创建加密映射包（见文档）")
            return False
        
        # 检查是否已加载
        if self._is_loaded():
            print(f"⚠️  映射已加载，临时目录: {self.temp_dir}")
            print("   如需重新加载，请先执行 --unload")
            return True
        
        # 提示用户输入密码
        password = getpass.getpass("🔐 请输入脱敏映射包密码: ")
        
        try:
            # 解压到临时目录
            self.temp_dir = Path(tempfile.mkdtemp(prefix="desensitize_"))
            
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                # 验证密码并解压
                zf.extractall(self.temp_dir, pwd=password.encode('utf-8'))
                
                # 加载元数据
                metadata_file = self.temp_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        self.metadata = json.load(f)
                
                # 加载映射
                mapping_file = self.temp_dir / "current_mapping.csv"
                if not mapping_file.exists():
                    print("❌ 映射包内缺少 current_mapping.csv")
                    self._cleanup()
                    return False
                
                self.mapping = self._read_mapping(mapping_file)
                
                if not self.mapping:
                    print("⚠️  映射为空")
                    self._cleanup()
                    return False
                
                # 保存状态
                self._save_state()
                
                print(f"✅ 映射加载成功")
                print(f"   规则数: {len(self.mapping)} 条")
                print(f"   版本: {self.metadata.get('version', 'unknown')}")
                print(f"   临时目录: {self.temp_dir}")
                return True
        
        except RuntimeError as e:
            if 'Bad password' in str(e) or 'password' in str(e).lower():
                print("❌ 密码错误")
            else:
                print(f"❌ 解压失败: {e}")
            self._cleanup()
            return False
        
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            self._cleanup()
            return False
    
    def unload(self) -> bool:
        """安全卸载映射（会话结束时调用）"""
        if not self._is_loaded():
            print("ℹ️  映射未加载")
            return True
        
        temp_dir = self.temp_dir
        self._cleanup()
        self._clear_state()
        
        print(f"🔒 映射已清除")
        print(f"   临时目录已删除: {temp_dir}")
        return True
    
    def status(self) -> None:
        """查看映射状态"""
        if self._is_loaded():
            print(f"✅ 映射已加载")
            print(f"   规则数: {len(self.mapping)} 条")
            print(f"   版本: {self.metadata.get('version', 'unknown')}")
            print(f"   临时目录: {self.temp_dir}")
            print(f"   ZIP 路径: {self.zip_path}")
        else:
            print(f"❌ 映射未加载")
            print(f"   ZIP 路径: {self.zip_path}")
            if self.zip_path.exists():
                print(f"   ZIP 大小: {self.zip_path.stat().st_size} 字节")
            else:
                print(f"   ⚠️  ZIP 不存在")
    
    def rotate(self) -> bool:
        """轮换映射规则（生成新的随机映射）"""
        if not self._is_loaded():
            print("❌ 请先加载映射（--load）")
            return False
        
        print("🔄 生成新映射中...")
        
        # 归档旧映射
        archive_dir = self.temp_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        
        old_version = self.metadata.get('version', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = archive_dir / f"mapping_{old_version}_{timestamp}.csv"
        
        # 保存旧映射到归档
        self._write_mapping(self.mapping, archive_file)
        
        # 生成新映射（示例：保留原关键字，生成新的随机替换值）
        new_mapping = {}
        for keyword in self.mapping.keys():
            # 生成随机替换值（16 字符）
            import secrets
            import string
            chars = string.ascii_letters + string.digits + "!@#$%"
            new_value = ''.join(secrets.choice(chars) for _ in range(16))
            new_mapping[keyword] = new_value
        
        # 保存新映射
        new_mapping_file = self.temp_dir / "current_mapping.csv"
        self._write_mapping(new_mapping, new_mapping_file)
        
        # 更新元数据
        new_version = datetime.now().strftime("%Y.%m")
        self.metadata['version'] = new_version
        self.metadata['rotated_at'] = datetime.now().isoformat()
        self.metadata['previous_version'] = old_version
        
        metadata_file = self.temp_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        
        # 更新内存中的映射
        self.mapping = new_mapping
        
        print(f"✅ 新映射已生成")
        print(f"   版本: {new_version}")
        print(f"   旧映射已归档: {archive_file.name}")
        print(f"   ⚠️  建议：更新加密 ZIP 包以持久化新映射")
        
        return True
    
    def _is_loaded(self) -> bool:
        """检查映射是否已加载"""
        return self.temp_dir is not None and self.temp_dir.exists()
    
    def _cleanup(self):
        """安全清除临时文件"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = None
        self.mapping = {}
        self.metadata = {}
    
    def _save_state(self):
        """保存加载状态（用于跨进程检查）"""
        state = {
            'loaded': True,
            'temp_dir': str(self.temp_dir),
            'zip_path': str(self.zip_path),
            'loaded_at': datetime.now().isoformat(),
            'rule_count': len(self.mapping),
            'version': self.metadata.get('version', 'unknown')
        }
        with open(self.STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def _clear_state(self):
        """清除状态文件"""
        if self.STATE_FILE.exists():
            self.STATE_FILE.unlink()
    
    def _read_mapping(self, filepath: Path) -> Dict[str, str]:
        """读取映射文件（CSV 格式）"""
        mapping = {}
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                keyword = row.get('keyword', '').strip()
                replacement = row.get('replacement', '').strip()
                if keyword and replacement:
                    mapping[keyword] = replacement
        return mapping
    
    def _write_mapping(self, mapping: Dict[str, str], filepath: Path) -> None:
        """写入映射文件（CSV 格式）"""
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['keyword', 'replacement', 'type', 'description'])
            writer.writeheader()
            for keyword, replacement in mapping.items():
                writer.writerow({
                    'keyword': keyword,
                    'replacement': replacement,
                    'type': 'auto_rotated',
                    'description': f'Auto-generated at {datetime.now().isoformat()}'
                })


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="安全映射加载器（符合 iron_rules.md §3.2.7）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 加载映射（会话开始）
  python secure_mapping_loader.py --load
  
  # 卸载映射（会话结束）
  python secure_mapping_loader.py --unload
  
  # 查看映射状态
  python secure_mapping_loader.py --status
  
  # 轮换映射（手动，建议每季度一次）
  python secure_mapping_loader.py --rotate
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--load', action='store_true', help='加载映射（需输入密码）')
    group.add_argument('--unload', action='store_true', help='卸载映射（清除临时文件）')
    group.add_argument('--status', action='store_true', help='查看映射状态')
    group.add_argument('--rotate', action='store_true', help='轮换映射规则')
    
    parser.add_argument('--zip-path', type=Path, help='自定义 ZIP 路径（默认：D:\\MyProjects\\.secrets\\desensitize_mapping.zip）')
    
    args = parser.parse_args()
    
    loader = SecureMappingLoader(args.zip_path)
    
    if args.load:
        success = loader.load()
        sys.exit(0 if success else 1)
    
    elif args.unload:
        success = loader.unload()
        sys.exit(0 if success else 1)
    
    elif args.status:
        loader.status()
        sys.exit(0)
    
    elif args.rotate:
        success = loader.rotate()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

