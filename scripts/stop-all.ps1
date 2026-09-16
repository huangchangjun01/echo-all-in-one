<#
.SYNOPSIS
  停止 Echo All-in-One 已启动的服务（按 logs/<name>.pid 逐树强杀）。
.EXAMPLE
  .\scripts\stop-all.ps1
#>
[CmdletBinding()]
param()

$root = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $root 'logs'
$pidDir = $logs

if (-not (Test-Path $pidDir)) {
    Write-Host '未找到 logs/ 目录，当前没有通过 start-all.ps1 启动的服务 PID 记录。' -ForegroundColor Yellow
    exit 0
}

$stopped = 0
Get-ChildItem $pidDir -Filter '*.pid' -ErrorAction SilentlyContinue | ForEach-Object {
    $name = $_.BaseName
    $pidVal = Get-Content $_.FullName -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pidVal -match '^\d+$') {
        Write-Host "==> 停止 [$name] (PID=$pidVal, 包含子进程树) ..." -ForegroundColor Cyan
        # /T 连同子进程（vite / uvicorn 子进程等）一起终止
        taskkill.exe /PID ([int]$pidVal) /T /F 2>&1 | Out-Null
        $stopped++
    }
    Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
}

if ($stopped -eq 0) { Write-Host '没有正在运行的纪录 PID。' } else { Write-Host "已停止 $stopped 个服务（PID 记录已清理）。残留进程可执行: tasklist | findstr /i \"echo-core python node\"" }