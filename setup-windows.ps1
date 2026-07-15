# susurrate Windows setup — idempotent. Run from the susurrate folder root:
#   powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1
$ErrorActionPreference = "Stop"

$whisperDir = "$env:USERPROFILE\Tools\whisper.cpp"
$whisperCli = "$whisperDir\Release\whisper-cli.exe"
$dataDir    = "$env:USERPROFILE\.local\share\susurrate"
$modelPath  = "$dataDir\models\ggml-base.en.bin"
$wordsPath  = "$dataDir\words"
$whisperZip = "https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-blas-bin-x64.zip"
$modelUrl   = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
$wordsUrl   = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"

# 1. uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    winget install --id astral-sh.uv -e --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + $env:Path
}

# 2. whisper.cpp prebuilt binaries
if (-not (Test-Path $whisperCli)) {
    Write-Host "Downloading whisper.cpp binaries..."
    New-Item -ItemType Directory -Force $whisperDir | Out-Null
    curl.exe -sL -o "$whisperDir\whisper-bin.zip" $whisperZip
    Expand-Archive "$whisperDir\whisper-bin.zip" -DestinationPath $whisperDir -Force
    Remove-Item "$whisperDir\whisper-bin.zip"
}

# 3. speech model (~141 MB) + wordlist for the personal dictionary's learn guard
New-Item -ItemType Directory -Force "$dataDir\models" | Out-Null
if (-not (Test-Path $modelPath)) {
    Write-Host "Downloading ggml-base.en.bin (~141 MB)..."
    curl.exe -sL -o $modelPath $modelUrl
}
if (-not (Test-Path $wordsPath)) {
    Write-Host "Downloading English wordlist..."
    curl.exe -sL -o $wordsPath $wordsUrl
}

# 4. tell susurrate where whisper-cli.exe lives (new shells pick this up)
[Environment]::SetEnvironmentVariable("SUSURRATE_WHISPER_CLI", $whisperCli, "User")
$env:SUSURRATE_WHISPER_CLI = $whisperCli

# 5. python env + tests
Write-Host "Installing Python environment..."
uv sync
Write-Host "Running tests..."
uv run python -m unittest discover -s tests

Write-Host ""
Write-Host "Done. Open a NEW terminal, then:"
Write-Host "  uv run susurrate once --seconds 5   # speak; transcript prints"
Write-Host "  uv run susurrate run                # hold right-Alt to dictate anywhere"
