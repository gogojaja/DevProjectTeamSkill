# 远程控制工具使用指南

## 概述

远程控制工具封装了ADB和scrcpy，提供便捷的Android设备管理、屏幕镜像、文件传输等功能。

## 安装状态

- **ADB**: ✅ 已安装 (Google.PlatformTools)
- **scrcpy**: ✅ 已安装 (Genymobile.scrcpy)

## 快速开始

### 1. 连接Android设备

#### USB连接
1. 在手机上开启"开发者选项"
2. 开启"USB调试"
3. 使用USB数据线连接手机到电脑
4. 在手机上点击"允许USB调试"

#### 无线连接
```bash
# 先通过USB连接，然后启用TCP/IP模式
python tools\remote_control.py tcpip

# 获取手机IP地址（在手机设置中查看）
# 连接到手机
python tools\remote_control.py connect <手机IP>
```

### 2. 检查设备连接
```bash
python tools\remote_control.py devices
```

### 3. 获取设备信息
```bash
python tools\remote_control.py info
```

## 功能详解

### 屏幕镜像
```bash
# 基本镜像
python tools\remote_control.py mirror

# 高分辨率镜像
python tools\remote_control.py mirror -m 1024

# 限制帧率
python tools\remote_control.py mirror --max-fps 30
```

### 录制屏幕
```bash
# 录制屏幕
python tools\remote_control.py record output.mp4

# 录制30秒
python tools\remote_control.py record output.mp4 -d 30

# 高分辨率录制
python tools\remote_control.py record output.mp4 -m 1024
```

### 截图
```bash
python tools\remote_control.py screenshot output.png
```

### 文件传输
```bash
# 推送文件到手机
python tools\remote_control.py push local.txt /sdcard/

# 从手机拉取文件
python tools\remote_control.py pull /sdcard/file.txt ./
```

### 安装应用
```bash
python tools\remote_control.py install app.apk
```

## 常用ADB命令

### 设备管理
```bash
# 列出设备
adb devices

# 设备详细信息
adb devices -l

# 重启设备
adb reboot

# 重启到恢复模式
adb reboot recovery
```

### 文件操作
```bash
# 推送文件
adb push local.txt /sdcard/

# 拉取文件
adb pull /sdcard/file.txt ./

# 列出文件
adb shell ls /sdcard/
```

### 应用管理
```bash
# 安装应用
adb install app.apk

# 卸载应用
adb uninstall com.package.name

# 列出已安装应用
adb shell pm list packages
```

### 系统信息
```bash
# 获取设备型号
adb shell getprop ro.product.model

# 获取Android版本
adb shell getprop ro.build.version.release

# 获取电池信息
adb shell dumpsys battery
```

## 常用scrcpy参数

### 分辨率控制
```bash
# 设置最大分辨率
scrcpy -m 1024

# 设置具体分辨率
scrcpy -m 1280:720
```

### 比特率控制
```bash
# 设置视频比特率
scrcpy -b 2M

# 设置具体比特率
scrcpy -b 8000000
```

### 帧率控制
```bash
# 设置最大帧率
scrcpy --max-fps 30
```

### 窗口设置
```bash
# 设置窗口标题
scrcpy --window-title "My Phone"

# 无边框窗口
scrcpy --window-borderless

# 始终置顶
scrcpy --always-on-top
```

### 录制设置
```bash
# 录制屏幕
scrcpy --record output.mp4

# 限制录制时长
scrcpy --record output.mp4 --time-limit 60
```

## 故障排除

### 设备未检测到
1. 确认USB调试已开启
2. 检查USB数据线是否支持数据传输
3. 尝试更换USB端口
4. 重启ADB服务：`adb kill-server && adb start-server`

### 无线连接失败
1. 确保手机和电脑在同一网络
2. 检查防火墙设置
3. 尝试重新启用TCP/IP模式

### scrcpy启动失败
1. 检查设备是否已连接
2. 尝试降低分辨率：`scrcpy -m 800`
3. 检查设备是否支持屏幕投射

## 安全提示

1. **仅连接信任的设备**：避免连接未知设备
2. **及时断开连接**：使用完毕后及时断开
3. **保护USB调试**：不在公共场合开启USB调试
4. **定期检查授权**：定期检查已授权的USB调试设备

## 更多资源

- [ADB官方文档](https://developer.android.com/tools/adb)
- [scrcpy GitHub](https://github.com/Genymobile/scrcpy)
- [Android开发者指南](https://developer.android.com/)