param([switch]$Chat, [switch]$Pdf)
. (Join-Path $PSScriptRoot 'Runtime.ps1')
Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not $Chat) { $env:RAG_USE_LLM = '0' }
    if ($Pdf) {
        if ($Chat) { & $pythonExe run_pdf_assignment.py --chat }
        else { & $pythonExe run_pdf_assignment.py }
    } elseif ($Chat) { & $pythonExe run_assignment.py --chat }
    else { & $pythonExe run_assignment.py }
    if ($LASTEXITCODE -ne 0) { throw 'Lab run failed. See evidence logs.' }
} finally { Pop-Location }
