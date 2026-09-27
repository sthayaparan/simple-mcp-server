# Stop the Member agent console (Windows).
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not (Test-Path agent.pid)) {
    Write-Host "Agent not running."
    exit 1
}

$agentPid = Get-Content agent.pid
Stop-Process -Id $agentPid -Force -ErrorAction SilentlyContinue
Remove-Item agent.pid
Write-Host "Agent stopped (PID $agentPid)."
