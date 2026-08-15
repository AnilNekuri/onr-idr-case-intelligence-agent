param(
    [Parameter(Mandatory = $true)]
    [string]$ModelId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9A-Za-z]{10}$")]
    [string]$KnowledgeBaseId,

    [string]$CaseId = "CASE-1001",
    [string]$Question = "What should happen next?",
    [string]$CurrentDate = (Get-Date -Format "yyyy-MM-dd"),
    [string]$Region = "us-east-1",
    [string]$Profile = "anekur-admin"
)

$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repositoryRoot

$pythonPath = ".\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Virtual-environment Python was not found: $pythonPath"
}

$environmentNames = @(
    "CASE_REPOSITORY",
    "JSON_CASES_PATH",
    "AWS_REGION",
    "AWS_PROFILE",
    "BEDROCK_MODEL_ID",
    "BEDROCK_KNOWLEDGE_BASE_ID"
)
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable(
        $name,
        "Process"
    )
}

$env:CASE_REPOSITORY = "json"
$env:JSON_CASES_PATH = "data/cases.json"
$env:AWS_REGION = $Region
$env:AWS_PROFILE = $Profile
$env:BEDROCK_MODEL_ID = $ModelId
$env:BEDROCK_KNOWLEDGE_BASE_ID = $KnowledgeBaseId

try {
    Write-Host "Calling the grounded case agent. This can incur AWS charges."
    Write-Host "Case: $CaseId"
    Write-Host "Question: $Question"

    & $pythonPath -m app.agent_cli `
        --case-id $CaseId `
        --question $Question `
        --current-date $CurrentDate

    if ($LASTEXITCODE -ne 0) {
        throw "The grounded case agent failed with exit code $LASTEXITCODE."
    }
}
finally {
    foreach ($name in $environmentNames) {
        $previousValue = $previousEnvironment[$name]
        if ($null -eq $previousValue) {
            Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        }
        else {
            Set-Item "Env:$name" $previousValue
        }
    }
}
