# Start the Member agent console in a new window (Windows).
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if ((Test-Path agent.pid) -and (Get-Process -Id (Get-Content agent.pid) -ErrorAction SilentlyContinue)) {
    Write-Host "Agent already running (PID $(Get-Content agent.pid))."
    exit 1
}

uv sync --quiet
$proc = Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m", "agent" -PassThru
$proc.Id | Set-Content agent.pid
Write-Host "Agent started (PID $($proc.Id)) in a new console window."
