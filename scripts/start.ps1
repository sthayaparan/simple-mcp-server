# Start the Member MCP Server in the background (Windows).
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (Test-Path server.pid) {
    Write-Host "Server already running (PID $(Get-Content server.pid))."
    exit 1
}

uv sync --quiet
$proc = Start-Process -FilePath ".venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "member_mcp.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -RedirectStandardOutput server.log -RedirectStandardError server.err.log `
    -WindowStyle Hidden -PassThru
$proc.Id | Set-Content server.pid
Write-Host "Server started (PID $($proc.Id)) at http://127.0.0.1:8000/mcp"
