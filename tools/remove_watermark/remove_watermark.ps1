# remove_watermark.ps1 — 去水印工具 PowerShell 封装（v1.0.0）
# 用法: .\tools\remove_watermark\remove_watermark.ps1 --auto --in-place report.docx
param(
    [Parameter(Position=0, ValueFromRemainingArguments=$true)]
    $Args
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-Python {
    $pyCmd = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $r = & py.exe -3 --version 2>&1
        if ($LASTEXITCODE -eq 0) { return "py.exe", "-3" }
    }
    $pythonCmd = Get-Command "python.exe" -ErrorAction SilentlyContinue
    if ($pythonCmd) { return "python.exe" }
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$python = Find-Python
if (-not $python) {
    Write-Host "❌ 未找到 Python 解释器，请先安装 Python 3.10+" -ForegroundColor Red
    exit 1
}

$scriptPath = Join-Path $ScriptDir "remove_watermark.py"
& $python $scriptPath @Args
exit $LASTEXITCODE