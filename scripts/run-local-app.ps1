param(
    [string]$ModelId,
    [string]$Profile,
    [ValidateRange(1, 65535)]
    [int]$Port = 8501,
    [switch]$LocalAssistant,
    [switch]$UseDynamoDbCases,
    [switch]$Check
)

$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$terraformDirectory = Join-Path $repositoryRoot "infra\environments\dev"
$statePath = Join-Path $terraformDirectory "terraform.tfstate"
$variablesPath = Join-Path $terraformDirectory "terraform.tfvars"
$pythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$entryPoint = Join-Path $repositoryRoot "streamlit_app.py"

if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
    throw "Development Terraform state was not found at $statePath"
}
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Virtual-environment Python was not found at $pythonPath"
}

$state = Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json

function Get-TerraformOutput {
    param([Parameter(Mandatory = $true)][string]$Name)

    $output = $state.outputs.$Name
    if ($null -eq $output -or -not [string]$output.value) {
        throw "Terraform output '$Name' is missing from $statePath"
    }
    return [string]$output.value
}

function Get-OptionalTerraformOutput {
    param([Parameter(Mandatory = $true)][string]$Name)

    $output = $state.outputs.$Name
    if ($null -eq $output -or -not [string]$output.value) {
        return $null
    }
    return [string]$output.value
}

function Get-TerraformVariable {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Test-Path -LiteralPath $variablesPath -PathType Leaf)) {
        return $null
    }
    $escapedName = [regex]::Escape($Name)
    $pattern = '^\s*{0}\s*=\s*"([^"]+)"\s*$' -f $escapedName
    $match = Select-String -LiteralPath $variablesPath -Pattern $pattern `
        | Select-Object -First 1
    if ($null -eq $match) {
        return $null
    }
    return $match.Matches[0].Groups[1].Value
}

if (-not $env:AWS_REGION) {
    $env:AWS_REGION = Get-TerraformOutput "aws_region"
}
if (-not $env:AWS_PROFILE) {
    $env:AWS_PROFILE = if ($Profile) {
        $Profile
    } else {
        Get-TerraformVariable "aws_profile"
    }
}
if (-not $env:BEDROCK_KNOWLEDGE_BASE_ID) {
    $env:BEDROCK_KNOWLEDGE_BASE_ID = `
        Get-TerraformOutput "bedrock_knowledge_base_id"
}
if (-not $env:S3_CASE_DOCUMENTS_BUCKET) {
    $env:S3_CASE_DOCUMENTS_BUCKET = `
        Get-TerraformOutput "case_documents_bucket_name"
}
if ($UseDynamoDbCases) {
    $env:CASE_REPOSITORY = "dynamodb"
    $env:DYNAMODB_CASE_TABLE = Get-TerraformOutput "case_table_name"
}
elseif (-not $env:CASE_REPOSITORY) {
    $env:CASE_REPOSITORY = "json"
}
if ($LocalAssistant) {
    Remove-Item Env:CLAIM_AGENTCORE_RUNTIME_ARN -ErrorAction SilentlyContinue
    Remove-Item Env:CLAIM_AGENTCORE_ENDPOINT_NAME -ErrorAction SilentlyContinue
}
else {
    if (-not $env:CLAIM_INTAKE_TABLE) {
        $env:CLAIM_INTAKE_TABLE = `
            Get-OptionalTerraformOutput "claim_intake_table_name"
    }
    if (-not $env:CLAIM_AGENTCORE_RUNTIME_ARN) {
        $env:CLAIM_AGENTCORE_RUNTIME_ARN = `
            Get-OptionalTerraformOutput "claim_agentcore_runtime_arn"
    }
    if (-not $env:CLAIM_AGENTCORE_ENDPOINT_NAME) {
        $env:CLAIM_AGENTCORE_ENDPOINT_NAME = `
            Get-OptionalTerraformOutput "claim_agentcore_endpoint_name"
    }
}
if (-not $env:BEDROCK_MODEL_ID) {
    $env:BEDROCK_MODEL_ID = if ($ModelId) {
        $ModelId
    } else {
        Get-TerraformVariable "agentcore_bedrock_model_id"
    }
}
if (-not $env:BEDROCK_MODEL_ID) {
    throw "No model ID was configured. Pass -ModelId or set BEDROCK_MODEL_ID."
}

Write-Host "Starting ONR / IDR Case Intelligence"
Write-Host "AWS region: $env:AWS_REGION"
Write-Host "AWS profile: $env:AWS_PROFILE"
Write-Host "Knowledge Base: $env:BEDROCK_KNOWLEDGE_BASE_ID"
Write-Host "Model: $env:BEDROCK_MODEL_ID"
Write-Host "Case repository: $env:CASE_REPOSITORY"
if ($env:DYNAMODB_CASE_TABLE) {
    Write-Host "DynamoDB case table: $env:DYNAMODB_CASE_TABLE"
}
if ($env:CLAIM_AGENTCORE_RUNTIME_ARN) {
    Write-Host "Claim-intake AgentCore endpoint: $env:CLAIM_AGENTCORE_ENDPOINT_NAME"
}
else {
    Write-Host "Assistant execution: local process"
}

if ($Check) {
    Write-Host "Configuration check passed."
    return
}

Push-Location $repositoryRoot
try {
    & $pythonPath -m streamlit run $entryPoint `
        --server.port $Port `
        --browser.gatherUsageStats false
}
finally {
    Pop-Location
}
