$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

$hostValue = if ($env:AIR_API_HOST) { $env:AIR_API_HOST } else { "127.0.0.1" }
$portValue = if ($env:AIR_API_PORT) { $env:AIR_API_PORT } else { "8000" }

& $python -m uvicorn main:app --reload --host $hostValue --port $portValue
