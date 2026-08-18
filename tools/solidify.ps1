# =============================================================================
# solidify.ps1 — 育权台断点固化 Windows 原生入口（v21.7.0）
# 跨平台封装：自动查找 Python 解释器并调用 solidify.py 执行完整固化流程
#
# 用法:
#   .\tools\solidify.ps1
#   .\tools\solidify.ps1 "描述本次改动"
#   .\tools\solidify.ps1 --dry-run
# =============================================================================
param(
    [Parameter(Position=0)]
    [string]$Note = "",
    [switch]$DryRun = $false,
    [switch]$Json = $false
)

$ErrorActionPreference = "Stop"

# ---- 定位项目根目录 ----
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")

# ---- 查找 Python 解释器（按优先级） ----
function Find-Python {
    # 1. py 启动器（Windows Python Launcher）
    $pyCmd = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $result = & py.exe -3.11 --version 2>&1
        if ($LASTEXITCODE -eq 0) { return "py.exe", "-3.11" }
        $result = & py.exe -3 --version 2>&1
        if ($LASTEXITCODE -eq 0) { return "py.exe", "-3" }
    }

    # 2. python 命令
    $pythonCmd = Get-Command "python.exe" -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $result = & python.exe --version 2>&1
        if ($LASTEXITCODE -eq 0) { return "python.exe" }
    }

    # 3. 常见安装路径
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }

    return $null
}

$pythonExe = Find-Python
if (-not $pythonExe) {
    Write-Host "❌ 未找到 Python 解释器。请安装 Python 3.10+ 或确保其在 PATH 中。" -ForegroundColor Red
    Write-Host "   下载地址: https://www.python.org/downloads/" -ForegroundColor DarkYellow
    exit 1
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " 育权台断点固化 (solidify v21.7.0, PowerShell)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " Python: $pythonExe" -ForegroundColor Gray
Write-Host " 项目根: $Root" -ForegroundColor Gray
Write-Host ""

# ---- 构建参数 ----
$argsList = @()
if ($DryRun) { $argsList += "--dry-run" }
if ($Json)   { $argsList += "--json" }
if ($Note)   { $argsList += $Note }

$solidifyPy = Join-Path $ScriptDir "solidify.py"

# ---- 执行 solidify.py ----
& $pythonExe $solidifyPy @argsList
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "==============================================================" -ForegroundColor Green
    Write-Host " 固化完成。请执行: git add -A; git commit -m ""<说明>""" -ForegroundColor Green
    Write-Host "==============================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ 固化失败（退出码: $exitCode）" -ForegroundColor Red
    exit $exitCode
}
