# Remote Control Skill

## Description
远程控制Android设备的技能，支持ADB连接、屏幕镜像、文件传输和设备管理。通过scrcpy实现高质量的屏幕投射和控制，支持USB和无线连接方式。

## Trigger Keywords
- 远程控制
- 手机连接
- 屏幕镜像
- ADB连接
- scrcpy
- 设备管理

## Load When
用户需要连接Android设备、进行屏幕镜像、远程控制手机、传输文件或管理设备时加载。

## Capabilities

### 1. 设备连接管理
- **USB连接**：通过USB数据线连接Android设备
- **无线连接**：通过WiFi连接Android设备（需要先USB配对）
- **设备检测**：自动检测已连接的设备
- **连接状态**：显示设备连接状态和信息

### 2. 屏幕镜像与控制
- **高清镜像**：使用scrcpy进行高质量屏幕投射
- **实时控制**：通过鼠标和键盘控制手机
- **屏幕录制**：录制手机屏幕操作
- **截图功能**：快速截取手机屏幕

### 3. 文件管理
- **文件传输**：在电脑和手机之间传输文件
- **应用安装**：安装APK应用到手机
- **文件浏览**：浏览手机文件系统

### 4. 设备信息
- **设备信息**：获取设备型号、系统版本等信息
- **电池状态**：查看电池电量和充电状态
- **存储空间**：查看存储使用情况

## Usage Examples

### 基本连接
```bash
# 检测已连接设备
adb devices

# 启动scrcpy屏幕镜像
scrcpy

# 无线连接（需要先USB配对）
adb tcpip 5555
adb connect <设备IP>:5555
```

### 高级功能
```bash
# 高分辨率镜像
scrcpy -m 1024

# 录制屏幕
scrcpy --record screen.mp4

# 传输文件
adb push local.txt /sdcard/
adb pull /sdcard/file.txt ./

# 安装应用
adb install app.apk
```

## Configuration

### 连接参数
- **分辨率**：`-m` 或 `--max-size` 设置最大分辨率
- **比特率**：`-b` 或 `--bit-rate` 设置视频比特率
- **帧率**：`--max-fps` 设置最大帧率
- **窗口标题**：`--window-title` 设置窗口标题

### 设备选择
- **USB设备**：默认连接第一个USB设备
- **指定设备**：`-s <设备序列号>` 指定特定设备
- **无线设备**：`adb connect <IP>:<端口>` 连接无线设备

## Dependencies
- **ADB**：Android Debug Bridge（已安装）
- **scrcpy**：屏幕镜像工具（已安装）
- **Android设备**：开启USB调试的Android设备

## Notes
1. **USB调试**：必须在手机开发者选项中开启USB调试
2. **驱动安装**：某些设备可能需要安装USB驱动
3. **无线连接**：首次无线连接需要USB配对
4. **性能影响**：高分辨率镜像可能影响设备性能
5. **安全提示**：仅连接信任的设备，避免恶意连接