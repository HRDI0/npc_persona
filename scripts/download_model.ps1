param(
    [string]$ModelId = $env:VLLM_MODEL,
    [string]$LocalDir = $env:LOCAL_MODEL_DIR,
    [string]$Revision = "main",
    [int]$MaxWorkers = 1
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ModelId)) {
    $ModelId = "google/gemma-4-E4B-it"
}

if ([string]::IsNullOrWhiteSpace($LocalDir)) {
    $LocalDir = "models/google-gemma-4-E4B-it"
}

$ResolvedDir = Join-Path (Get-Location) $LocalDir
New-Item -ItemType Directory -Path $ResolvedDir -Force | Out-Null

$DownloadArgs = @(
    "--from",
    "huggingface_hub",
    "hf",
    "download",
    $ModelId,
    "--revision",
    $Revision,
    "--local-dir",
    $ResolvedDir,
    "--max-workers",
    [string]$MaxWorkers
)

# Legacy equivalent: huggingface-cli download

if (-not [string]::IsNullOrWhiteSpace($env:HF_TOKEN)) {
    $DownloadArgs += @("--token", $env:HF_TOKEN)
}

& uvx @DownloadArgs
"MODEL_DIR=$ResolvedDir"
