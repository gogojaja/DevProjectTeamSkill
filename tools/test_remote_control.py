#!/usr/bin/env python3
"""
远程控制工具测试脚本
"""

import sys
import os

# 添加工具目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from remote_control import RemoteControl

def test_basic():
    """基本功能测试"""
    print("=== 远程控制工具测试 ===\n")
    
    try:
        # 初始化
        print("1. 初始化远程控制工具...")
        rc = RemoteControl()
        print(f"   ADB路径: {rc.adb_path}")
        print(f"   scrcpy路径: {rc.scrcpy_path}")
        print("   [OK] 初始化成功\n")
        
        # 列出设备
        print("2. 检查已连接设备...")
        devices = rc.list_devices()
        if devices:
            print(f"   找到 {len(devices)} 个设备:")
            for dev in devices:
                print(f"   - {dev['id']} ({dev['status']}) {dev['info']}")
        else:
            print("   未找到已连接的设备")
            print("   提示：请确保手机已开启USB调试并连接到电脑")
        print()
        
        # 测试ADB命令
        print("3. 测试ADB命令...")
        result = rc.run_adb(['version'])
        if result and result.returncode == 0:
            print(f"   ADB版本: {result.stdout.split(chr(10))[0]}")
            print("   [OK] ADB命令执行成功")
        else:
            print("   [FAIL] ADB命令执行失败")
        print()
        
        print("=== 测试完成 ===")
        print("\n下一步:")
        print("1. 连接Android设备（USB或无线）")
        print("2. 运行 'python tools\\remote_control.py devices' 查看设备")
        print("3. 运行 'python tools\\remote_control.py mirror' 启动屏幕镜像")
        
    except Exception as e:
        print(f"错误: {e}")
        print("\n请确保已安装必要的工具:")
        print("  winget install Google.PlatformTools")
        print("  winget install Genymobile.scrcpy")

if __name__ == '__main__':
    test_basic()