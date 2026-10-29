param([ValidateSet('Chat', 'Check', 'Evaluate')][string]$Mode = 'Chat', [switch]$NoPrompt)
. (Join-Path $PSScriptRoot 'Runtime.ps1')
$env:RAG_LLM_PROVIDER = 'gemini'
if (-not $env:RAG_GEMINI_MODEL) { $env:RAG_GEMINI_MODEL = 'gemini-3.5-flash-lite' }
$env:RAG_LLM_MODEL = $env:RAG_GEMINI_MODEL
$env:RAG_USE_LLM = '1'

# Read only the selected provider's named environment variables. Never print values.
if (-not $env:GOOGLE_API_KEY -and -not $env:GEMINI_API_KEY) {
    foreach ($keyName in @('GOOGLE_API_KEY', 'GEMINI_API_KEY')) {
        $candidateKey = [Environment]::GetEnvironmentVariable($keyName, 'User')
        if ($candidateKey) { $env:GOOGLE_API_KEY = $candidateKey; $candidateKey = $null; break }
    }
}
$enteredKey = $false
if (-not $env:GOOGLE_API_KEY -and -not $env:GEMINI_API_KEY) {
    if ($NoPrompt) { throw 'Missing GOOGLE_API_KEY or GEMINI_API_KEY. Run RUN-AI.cmd to enter it privately.' }
    $secureKey = Read-Host 'Gemini API key (hidden; used only for this session)' -AsSecureString
    $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    try { $env:GOOGLE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer); $secureKey.Dispose() }
    if ([string]::IsNullOrWhiteSpace($env:GOOGLE_API_KEY)) { throw 'No key was entered.' }
    $enteredKey = $true
}

Push-Location -LiteralPath $PSScriptRoot
try {
    if ($Mode -eq 'Chat') {
        & $pythonExe gemini_preflight.py
        if ($LASTEXITCODE -ne 0) { throw 'Gemini preflight failed. No chat started.' }
        & $pythonExe run_assignment.py --chat
    } elseif ($Mode -eq 'Check') {
        & $pythonExe gemini_preflight.py
    } elseif ($Mode -eq 'Evaluate') {
        & $pythonExe -m evaluation.benchmark_gemini --resume
        $benchmarkExit = $LASTEXITCODE
        if ($benchmarkExit -ne 0) { throw 'Gemini evaluation is incomplete. Completed trials are saved for resume.' }
    }
    if ($LASTEXITCODE -ne 0) { throw 'Gemini task failed; see evidence/gemini/.' }
} finally {
    Pop-Location
    if ($enteredKey) { Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue }
}
