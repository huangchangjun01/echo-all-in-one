<#
.SYNOPSIS
  一键启动 Echo All-in-One 三个服务：ai (Python) → core (Go) → web (Vite)。
  - 服务按依赖顺序启动：ai 先行（core 转发依赖），core 其次，web 最后。
  - 每个服务日志写入 logs/<name>.out.log / logs/<name>.err.log，PID 写入 logs/<name>.pid。
  - 已运行的服务自动跳过（幂等）。
.EXAMPLE
  .\scripts\start-all.ps1              # 启动全部三个服务
  .\scripts\start-all.ps1 -Only ai     # 只启动 ai
#>
[CmdletBinding()]
param(
    [Parameter()][ValidateSet('ai', 'core', 'web')]
    [string[]]$Only = @()
)

$ErrorActionPreference = 'Stop'
$root   = Split-Path -Parent $PSScriptRoot
$logs   = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$wanted = if ($Only.Count -gt 0) { $Only } else { @('ai', 'core', 'web') }

function Write-Step { param([string]$msg) Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Warn { param([string]$msg) Write-Host "[warn] $msg" -ForegroundColor Yellow }

function Start-One {
    param([string]$Name, [string[]]$Cmd, [string]$WorkDir)
    $out     = Join-Path $logs "$Name.out.log"
    $err     = Join-Path $logs "$Name.err.log"
    $pidFile = Join-Path $logs "$Name.pid"

    # 幂等：已有存活 PID 则跳过
    if (Test-Path $pidFile) {
        $old = Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($old -match '^\d+$' -and (Get-Process -Id ([int]$old) -ErrorAction SilentlyContinue)) {
            Write-Warn "[$Name] 已在运行 (PID=$old)，跳过。如需重启请先执行 stop-all.ps1"
            return
        }
    }

    Write-Step "启动 [$Name]: $($Cmd -join ' ')  (工作目录: $WorkDir)"
    $p = Start-Process -FilePath $Cmd[0] -ArgumentList $Cmd[1..($Cmd.Count - 1)] `
        -WorkingDirectory $WorkDir -WindowStyle Hidden `
        -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
    $p.Id | Out-File -FilePath $pidFile -Encoding ascii
    Write-Host "     PID=$($p.Id)  日志: $out" -ForegroundColor DarkGray
    return $p
}

function Wait-Health {
    param([string]$Name, [string]$Url, [int]$TimeoutSec = 30)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -eq 200) {
                Write-Host "     [$Name] 健康检查通过: $Url" -ForegroundColor Green
                return $true
            }
        } catch { Start-Sleep -Milliseconds 800 }
    }
    Write-Warn "[$Name] $TimeoutSec 秒内未通过健康检查，请查看对应日志"
    return $false
}

# ---------- 1. ai (Python FastAPI :8000) ----------
if ($wanted -contains 'ai') {
    $pyExe = Join-Path $root 'ai\.venv\Scripts\python.exe'
    if (-not (Test-Path $pyExe)) {
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            throw '未找到 python 解释器。请安装 Python 3.10+ 或在 ai/ 下创建虚拟环境 (python -m venv .venv)'
        }
        $pyExe = 'python'
        Write-Warn '未找到 ai\.venv，将使用系统 python。生产建议: python -m venv ai\.venv 后 pip install -r ai\requirements.txt'
    }
    Start-One 'ai' @($pyExe, 'run.py') (Join-Path $root 'ai') | Out-Null
    # ai 模型加载较慢，不做阻塞式健康等待，提示用户稍后自检
    Write-Host '     ai 加载本地模型较慢（CLIP/Whisper/BGE-M3），请稍后访问 http://localhost:8000/health 确认' -ForegroundColor DarkGray
}

# ---------- 2. core (Go Gin :8080) ----------
if ($wanted -contains 'core') {
    $coreDir = Join-Path $root 'core'
    $exe = Join-Path $coreDir '.bin\echo-core.exe'
    Write-Step "编译 core: go build -o .bin/echo-core.exe"
    Push-Location $coreDir
    try { go build -o '.bin\echo-core.exe' . } finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { throw "core 编译失败 (exit=$LASTEXITCODE)，详见上方错误输出" }
    $coreProc = Start-One 'core' @($exe) $coreDir
    Wait-Health 'core' 'http://localhost:8080/health' 30
}

# ---------- 3. web (Vite dev :5173) ----------
if ($wanted -contains 'web') {
    if (-not (Test-Path (Join-Path $root 'web\node_modules'))) {
        Write-Warn 'web\node_modules 不存在，正在执行 npm install（可能较慢）'
        Push-Location (Join-Path $root 'web')
        try { npm install } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) { throw 'npm install 失败' }
    }
    Start-One 'web' @('npm.cmd', 'run', 'dev') (Join-Path $root 'web') | Out-Null
    Wait-Health 'web' 'http://localhost:5173' 30
}

Write-Host ''
Write-Host '=========== 启动摘要 ===========' -ForegroundColor Cyan
Write-Host '  ai   : http://localhost:8000  (/health, /chat, /memory/*)'
Write-Host '  core : http://localhost:8080  (/health, /api/*)'
Write-Host '  web  : http://localhost:5173  (前端，/api 代理到 core)'
Write-Host '日志目录: logs/    停止: .\scripts\stop-all.ps1'