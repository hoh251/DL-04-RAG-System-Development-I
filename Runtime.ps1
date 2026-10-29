$ErrorActionPreference = 'Stop'
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if ($env:RAG_PYTHON_EXE) { $pythonExe = $env:RAG_PYTHON_EXE }
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Python environment not found. Run SETUP.cmd first.' }
$cacheRoot = Join-Path $PSScriptRoot '.cache'
if ($env:RAG_CACHE_ROOT) { $cacheRoot = $env:RAG_CACHE_ROOT }
$env:PYTHONUTF8 = '1'
$env:HF_HOME = Join-Path $cacheRoot 'hf-cache'
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'
$env:PYTHAINLP_DATA = Join-Path $cacheRoot 'pythainlp-data'
