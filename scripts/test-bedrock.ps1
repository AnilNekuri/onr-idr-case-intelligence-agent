param(
    [Parameter(Mandatory = $true)]
    [string]$ModelId
)

$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repositoryRoot

$env:AWS_PROFILE = "anekur-admin"
$env:AWS_REGION = "us-east-1"
$env:BEDROCK_MODEL_ID = $ModelId
$env:RUN_AWS_INTEGRATION = "1"
$env:RUN_BEDROCK_INTEGRATION = "1"

try {
    Write-Host "Verifying AWS identity..."
    & aws sts get-caller-identity `
        --profile $env:AWS_PROFILE `
        --query "{Account:Account,Arn:Arn}" `
        --output json
    if ($LASTEXITCODE -ne 0) {
        throw "AWS authentication failed. Run: aws sso login --profile $env:AWS_PROFILE"
    }

    Write-Host "Running one paid Bedrock Mantle integration test with model $env:BEDROCK_MODEL_ID..."
    & .\.venv\Scripts\python.exe -m pytest `
        -m integration `
        tests\integration\test_bedrock_language_model.py `
        -vv
    if ($LASTEXITCODE -ne 0) {
        throw "The Bedrock integration test failed with exit code $LASTEXITCODE."
    }
}
finally {
    Remove-Item Env:RUN_BEDROCK_INTEGRATION -ErrorAction SilentlyContinue
    Remove-Item Env:RUN_AWS_INTEGRATION -ErrorAction SilentlyContinue
    Remove-Item Env:BEDROCK_MODEL_ID -ErrorAction SilentlyContinue
    Remove-Item Env:AWS_REGION -ErrorAction SilentlyContinue
    Remove-Item Env:AWS_PROFILE -ErrorAction SilentlyContinue
}
