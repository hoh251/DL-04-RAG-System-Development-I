$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 and ensure python is available, then run SETUP.cmd again.' }
    }
    $pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    & $pythonExe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) { throw 'PyTorch installation failed.' }
    & $pythonExe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    Write-Output 'Setup complete. Open RUN.cmd inside the desired lab. The first run downloads public embedding/reranker models.'
} finally { Pop-Location }
