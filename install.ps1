# PowerShell installer for Xavani Agent (Windows)
# Built by Entornovate. Open source.
param()

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Installing Xavani Agent"

Write-Host ""
Write-Host "╔══════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   XAVANI AGENT              ║" -ForegroundColor Cyan
Write-Host "║   by Entornovate             ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installing Xavani Agent - the open-source AI agent gateway..." -ForegroundColor Cyan

# Check Python
try {
    $py = (Get-Command python3 -ErrorAction Stop).Source
} catch {
    try {
        $py = (Get-Command python -ErrorAction Stop).Source
    } catch {
        Write-Host "ERROR: Python 3.11+ is required. Install from https://python.org" -ForegroundColor Red
        exit 1
    }
}
$pyver = & $py --version
Write-Host "  Python: $pyver" -ForegroundColor Gray

# Install directory
$installDir = Join-Path $env:LOCALAPPDATA "xavani"
$repoDir = Join-Path $installDir "repo"

# Clone
if (Test-Path (Join-Path $repoDir ".git")) {
    Write-Host "  Updating existing installation..." -ForegroundColor Gray
    Set-Location $repoDir
    git pull --ff-only 2>$null
} else {
    Write-Host "  Cloning Xavani Agent..." -ForegroundColor Gray
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    git clone --depth 1 "https://github.com/enternovate/xavani-agent.git" $repoDir
    Set-Location $repoDir
}

# Install
Write-Host "  Installing Python package..." -ForegroundColor Gray
& $py -m pip install -e $repoDir 2>$null

# Create xavani.cmd wrapper
$wrapperDir = Join-Path $env:LOCALAPPDATA "xavani\bin"
New-Item -ItemType Directory -Force -Path $wrapperDir | Out-Null
@"
@echo off
python -m xavani %*
"@ | Out-File -FilePath (Join-Path $wrapperDir "xavani.cmd") -Encoding ASCII

# Add to PATH (user-level)
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$wrapperDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$wrapperDir", "User")
    $env:PATH = "$env:PATH;$wrapperDir"
}

# Create Xavani home
$xavaniHome = Join-Path $env:USERPROFILE ".xavani"
@("logs", "skills", "policies", "installed", "data") | ForEach-Object {
    New-Item -ItemType Directory -Force -Path (Join-Path $xavaniHome $_) | Out-Null
}
New-Item -ItemType File -Force -Path (Join-Path $xavaniHome ".env") | Out-Null

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Run:  xavani" -ForegroundColor White
Write-Host ""
Write-Host "  Config:  $xavaniHome\" -ForegroundColor Gray
Write-Host "  Logs:    $xavaniHome\logs\" -ForegroundColor Gray
Write-Host ""
Write-Host "  Set your API keys in: $xavaniHome\.env" -ForegroundColor Gray
Write-Host ""
Write-Host "  Quick test:  xavani --message 'Hello'" -ForegroundColor Gray
Write-Host ""
Write-Host "Buffalo out. ⚡" -ForegroundColor Cyan
