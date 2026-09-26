# Stop the Member MCP Server (Windows).
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not (Test-Path server.pid)) {
    Write-Host "Server not running."
    exit 1
}

$serverPid = Get-Content server.pid
Stop-Process -Id $serverPid -Force -ErrorAction SilentlyContinue
Remove-Item server.pid
Write-Host "Server stopped (PID $serverPid)."
