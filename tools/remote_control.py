#!/usr/bin/env python3
"""
远程控制工具 - 封装ADB和scrcpy功能
支持设备连接、屏幕镜像、文件传输等功能
"""

import subprocess
import sys
import os
import time
import argparse
from pathlib import Path

class RemoteControl:
    def __init__(self):
        self.adb_path = self._find_adb()
        self.scrcpy_path = self._find_scrcpy()
        
    def _find_adb(self):
        """查找ADB路径"""
        # 首先尝试where命令
        try:
            result = subprocess.run(['where', 'adb'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        # 常见路径
        common_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
            r"C:\Android\platform-tools\adb.exe",
        ]
        
        # 添加winget安装路径
        localappdata = os.path.expandvars(r"%LOCALAPPDATA%")
        winget_paths = [
            os.path.join(localappdata, "Microsoft", "WinGet", "Packages", "Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe", "platform-tools", "adb.exe"),
            os.path.join(localappdata, "Microsoft", "WinGet", "Packages", "Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe", "scrcpy-win64-v4.1", "adb.exe"),
        ]
        common_paths.extend(winget_paths)
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError("ADB未找到，请先安装Android SDK Platform Tools")
    
    def _find_scrcpy(self):
        """查找scrcpy路径"""
        # 首先尝试where命令
        try:
            result = subprocess.run(['where', 'scrcpy'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        # 常见路径
        common_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\scrcpy\scrcpy.exe"),
            r"C:\scrcpy\scrcpy.exe",
        ]
        
        # 添加winget安装路径
        localappdata = os.path.expandvars(r"%LOCALAPPDATA%")
        winget_paths = [
            os.path.join(localappdata, "Microsoft", "WinGet", "Packages", "Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe", "scrcpy-win64-v4.1", "scrcpy.exe"),
        ]
        common_paths.extend(winget_paths)
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError("scrcpy未找到，请先安装scrcpy")
    
    def run_adb(self, args, capture_output=True):
        """运行ADB命令"""
        cmd = [self.adb_path] + args
        try:
            result = subprocess.run(cmd, capture_output=capture_output, text=True)
            return result
        except Exception as e:
            print(f"ADB命令执行失败: {e}")
            return None
    
    def run_scrcpy(self, args=None):
        """运行scrcpy命令"""
        cmd = [self.scrcpy_path]
        if args:
            cmd.extend(args)
        
        try:
            # scrcpy需要交互式运行，不捕获输出
            process = subprocess.Popen(cmd)
            return process
        except Exception as e:
            print(f"scrcpy启动失败: {e}")
            return None
    
    def list_devices(self):
        """列出已连接的设备"""
        result = self.run_adb(['devices', '-l'])
        if result and result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            devices = []
            for line in lines[1:]:  # 跳过第一行标题
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        device_id = parts[0]
                        status = parts[1]
                        info = ' '.join(parts[2:]) if len(parts) > 2 else ''
                        devices.append({
                            'id': device_id,
                            'status': status,
                            'info': info
                        })
            return devices
        return []
    
    def get_device_info(self, device_id=None):
        """获取设备信息"""
        cmd = ['-s', device_id] if device_id else []
        
        info = {}
        
        # 获取设备型号
        result = self.run_adb(cmd + ['shell', 'getprop', 'ro.product.model'])
        if result and result.returncode == 0:
            info['model'] = result.stdout.strip()
        
        # 获取Android版本
        result = self.run_adb(cmd + ['shell', 'getprop', 'ro.build.version.release'])
        if result and result.returncode == 0:
            info['android_version'] = result.stdout.strip()
        
        # 获取电池信息
        result = self.run_adb(cmd + ['shell', 'dumpsys', 'battery'])
        if result and result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'level:' in line:
                    info['battery_level'] = line.split(':')[1].strip()
                elif 'status:' in line:
                    info['battery_status'] = line.split(':')[1].strip()
        
        # 获取存储信息
        result = self.run_adb(cmd + ['shell', 'df', '/data'])
        if result and result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 4:
                    info['storage_total'] = parts[1]
                    info['storage_used'] = parts[2]
                    info['storage_available'] = parts[3]
        
        return info
    
    def connect_wireless(self, ip, port=5555):
        """无线连接设备"""
        print(f"正在连接到 {ip}:{port}...")
        result = self.run_adb(['connect', f'{ip}:{port}'])
        if result and result.returncode == 0:
            if 'connected' in result.stdout.lower():
                print(f"成功连接到 {ip}:{port}")
                return True
            else:
                print(f"连接失败: {result.stdout}")
        return False
    
    def enable_tcpip(self, port=5555):
        """启用TCP/IP模式"""
        print(f"正在启用TCP/IP模式，端口: {port}")
        result = self.run_adb(['tcpip', str(port)])
        if result and result.returncode == 0:
            print("TCP/IP模式已启用")
            return True
        return False
    
    def push_file(self, local_path, remote_path, device_id=None):
        """推送文件到设备"""
        cmd = ['-s', device_id] if device_id else []
        cmd.extend(['push', local_path, remote_path])
        
        print(f"正在推送文件: {local_path} -> {remote_path}")
        result = self.run_adb(cmd)
        if result and result.returncode == 0:
            print("文件推送成功")
            return True
        return False
    
    def pull_file(self, remote_path, local_path, device_id=None):
        """从设备拉取文件"""
        cmd = ['-s', device_id] if device_id else []
        cmd.extend(['pull', remote_path, local_path])
        
        print(f"正在拉取文件: {remote_path} -> {local_path}")
        result = self.run_adb(cmd)
        if result and result.returncode == 0:
            print("文件拉取成功")
            return True
        return False
    
    def install_apk(self, apk_path, device_id=None):
        """安装APK"""
        cmd = ['-s', device_id] if device_id else []
        cmd.extend(['install', apk_path])
        
        print(f"正在安装APK: {apk_path}")
        result = self.run_adb(cmd)
        if result and result.returncode == 0:
            print("APK安装成功")
            return True
        return False
    
    def mirror_screen(self, args=None):
        """启动屏幕镜像"""
        print("正在启动屏幕镜像...")
        print("提示：按 Ctrl+C 退出镜像")
        
        scrcpy_args = []
        if args:
            scrcpy_args.extend(args)
        
        process = self.run_scrcpy(scrcpy_args)
        if process:
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
                print("\n屏幕镜像已关闭")
    
    def record_screen(self, output_file, duration=None, args=None):
        """录制屏幕"""
        print(f"正在录制屏幕到: {output_file}")
        
        scrcpy_args = ['--record', output_file]
        if duration:
            scrcpy_args.extend(['--time-limit', str(duration)])
        if args:
            scrcpy_args.extend(args)
        
        process = self.run_scrcpy(scrcpy_args)
        if process:
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()
                print(f"\n录制已保存到: {output_file}")
    
    def take_screenshot(self, output_file, device_id=None):
        """截图"""
        cmd = ['-s', device_id] if device_id else []
        cmd.extend(['shell', 'screencap', '-p', '/sdcard/screenshot.png'])
        
        # 截图
        result = self.run_adb(cmd)
        if result and result.returncode == 0:
            # 拉取文件
            pull_cmd = ['-s', device_id] if device_id else []
            pull_cmd.extend(['pull', '/sdcard/screenshot.png', output_file])
            
            result = self.run_adb(pull_cmd)
            if result and result.returncode == 0:
                print(f"截图已保存到: {output_file}")
                return True
        
        print("截图失败")
        return False

def main():
    parser = argparse.ArgumentParser(description='远程控制Android设备')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 设备列表
    subparsers.add_parser('devices', help='列出已连接的设备')
    
    # 设备信息
    info_parser = subparsers.add_parser('info', help='获取设备信息')
    info_parser.add_argument('-s', '--serial', help='设备序列号')
    
    # 无线连接
    connect_parser = subparsers.add_parser('connect', help='无线连接设备')
    connect_parser.add_argument('ip', help='设备IP地址')
    connect_parser.add_argument('-p', '--port', type=int, default=5555, help='端口号')
    
    # 启用TCP/IP
    tcpip_parser = subparsers.add_parser('tcpip', help='启用TCP/IP模式')
    tcpip_parser.add_argument('-p', '--port', type=int, default=5555, help='端口号')
    
    # 推送文件
    push_parser = subparsers.add_parser('push', help='推送文件到设备')
    push_parser.add_argument('local', help='本地文件路径')
    push_parser.add_argument('remote', help='设备上的路径')
    push_parser.add_argument('-s', '--serial', help='设备序列号')
    
    # 拉取文件
    pull_parser = subparsers.add_parser('pull', help='从设备拉取文件')
    pull_parser.add_argument('remote', help='设备上的路径')
    pull_parser.add_argument('local', help='本地文件路径')
    pull_parser.add_argument('-s', '--serial', help='设备序列号')
    
    # 安装APK
    install_parser = subparsers.add_parser('install', help='安装APK')
    install_parser.add_argument('apk', help='APK文件路径')
    install_parser.add_argument('-s', '--serial', help='设备序列号')
    
    # 屏幕镜像
    mirror_parser = subparsers.add_parser('mirror', help='启动屏幕镜像')
    mirror_parser.add_argument('-m', '--max-size', type=int, help='最大分辨率')
    mirror_parser.add_argument('-b', '--bit-rate', help='视频比特率')
    mirror_parser.add_argument('--max-fps', type=int, help='最大帧率')
    
    # 录制屏幕
    record_parser = subparsers.add_parser('record', help='录制屏幕')
    record_parser.add_argument('output', help='输出文件路径')
    record_parser.add_argument('-d', '--duration', type=int, help='录制时长(秒)')
    record_parser.add_argument('-m', '--max-size', type=int, help='最大分辨率')
    
    # 截图
    screenshot_parser = subparsers.add_parser('screenshot', help='截取屏幕')
    screenshot_parser.add_argument('output', help='输出文件路径')
    screenshot_parser.add_argument('-s', '--serial', help='设备序列号')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        rc = RemoteControl()
        
        if args.command == 'devices':
            devices = rc.list_devices()
            if devices:
                print("已连接的设备:")
                for dev in devices:
                    print(f"  {dev['id']} - {dev['status']} {dev['info']}")
            else:
                print("未找到已连接的设备")
                print("提示：请确保手机已开启USB调试并连接到电脑")
        
        elif args.command == 'info':
            info = rc.get_device_info(args.serial)
            if info:
                print("设备信息:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
            else:
                print("无法获取设备信息")
        
        elif args.command == 'connect':
            rc.connect_wireless(args.ip, args.port)
        
        elif args.command == 'tcpip':
            rc.enable_tcpip(args.port)
        
        elif args.command == 'push':
            rc.push_file(args.local, args.remote, args.serial)
        
        elif args.command == 'pull':
            rc.pull_file(args.remote, args.local, args.serial)
        
        elif args.command == 'install':
            rc.install_apk(args.apk, args.serial)
        
        elif args.command == 'mirror':
            scrcpy_args = []
            if args.max_size:
                scrcpy_args.extend(['-m', str(args.max_size)])
            if args.bit_rate:
                scrcpy_args.extend(['-b', args.bit_rate])
            if args.max_fps:
                scrcpy_args.extend(['--max-fps', str(args.max_fps)])
            rc.mirror_screen(scrcpy_args)
        
        elif args.command == 'record':
            scrcpy_args = []
            if args.max_size:
                scrcpy_args.extend(['-m', str(args.max_size)])
            rc.record_screen(args.output, args.duration, scrcpy_args)
        
        elif args.command == 'screenshot':
            rc.take_screenshot(args.output, args.serial)
    
    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请先安装必要的工具:")
        print("  winget install Google.PlatformTools")
        print("  winget install Genymobile.scrcpy")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == '__main__':
    main()