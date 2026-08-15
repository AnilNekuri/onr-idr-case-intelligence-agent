param(
    [Parameter(Mandatory = $true)]
    [string]$BucketName,

    [Parameter(Mandatory = $true)]
    [string]$KnowledgeBaseId,

    [Parameter(Mandatory = $true)]
    [string]$DataSourceId,

    [string]$SourcePath = "data\knowledge",
    [string]$Prefix = "documents/",
    [string]$Region = "us-east-1",
    [string]$Profile,
    [ValidateRange(30, 3600)]
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourcePath -PathType Container)) {
    throw "Knowledge source directory not found: $SourcePath"
}

if ($KnowledgeBaseId -notmatch "^[0-9A-Za-z]{10}$") {
    throw "KnowledgeBaseId must contain exactly 10 letters or numbers."
}

$normalizedPrefix = $Prefix.Trim("/")
if (-not $normalizedPrefix) {
    throw "Prefix must contain at least one path component."
}

$awsCommon = @("--region", $Region)
if ($Profile) {
    $awsCommon += @("--profile", $Profile)
}

function Invoke-AwsCli {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $output = (& aws @Arguments @awsCommon | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI command failed: aws $($Arguments -join ' ')"
    }
    return $output
}

$source = (Resolve-Path -LiteralPath $SourcePath).Path
$destination = "s3://$BucketName/$normalizedPrefix/"

Write-Host "Uploading Markdown knowledge documents to $destination"
Invoke-AwsCli @(
    "s3", "sync", $source, $destination,
    "--exclude", "*", "--include", "*.md", "--only-show-errors"
) | Out-Null

Write-Host "Starting an explicit Managed Knowledge Base ingestion job"
$startResponse = Invoke-AwsCli @(
    "bedrock-agent", "start-ingestion-job",
    "--knowledge-base-id", $KnowledgeBaseId,
    "--data-source-id", $DataSourceId,
    "--description", "Curated public process-guidance sync",
    "--output", "json"
) | ConvertFrom-Json

$jobId = $startResponse.ingestionJob.ingestionJobId
if (-not $jobId) {
    throw "AWS did not return an ingestion job ID."
}

$timer = [System.Diagnostics.Stopwatch]::StartNew()
do {
    $jobResponse = Invoke-AwsCli @(
        "bedrock-agent", "get-ingestion-job",
        "--knowledge-base-id", $KnowledgeBaseId,
        "--data-source-id", $DataSourceId,
        "--ingestion-job-id", $jobId,
        "--output", "json"
    ) | ConvertFrom-Json

    $status = $jobResponse.ingestionJob.status
    Write-Host "Ingestion job $jobId status: $status"

    if ($status -eq "COMPLETE") {
        $jobResponse.ingestionJob | ConvertTo-Json -Depth 10
        exit 0
    }
    if ($status -in @("FAILED", "STOPPED")) {
        $reasons = $jobResponse.ingestionJob.failureReasons -join "; "
        throw "Ingestion job $jobId ended with status $status. $reasons"
    }

    Start-Sleep -Seconds 5
} while ($timer.Elapsed.TotalSeconds -lt $TimeoutSeconds)

throw "Ingestion job $jobId did not complete within $TimeoutSeconds seconds."
