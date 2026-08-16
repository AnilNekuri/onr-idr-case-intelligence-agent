[CmdletBinding()]
param(
    [string]$OutputPath = "output/agentcore/deployment_package.zip",
    [string]$PythonVersion = "3.13",
    [string]$PythonExecutable = ".venv/Scripts/python.exe"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..")
)
$stagingPath = [System.IO.Path]::GetFullPath(
    (Join-Path $repositoryRoot "tmp/agentcore-package")
)
$resolvedOutputPath = [System.IO.Path]::GetFullPath(
    (Join-Path $repositoryRoot $OutputPath)
)

if (-not $stagingPath.StartsWith($repositoryRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The staging path must stay inside the repository."
}
if (-not $resolvedOutputPath.StartsWith($repositoryRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The output path must stay inside the repository."
}
if (Test-Path -LiteralPath $stagingPath) {
    Remove-Item -LiteralPath $stagingPath -Recurse -Force
}
New-Item -ItemType Directory -Path $stagingPath | Out-Null
New-Item -ItemType Directory -Path (Split-Path $resolvedOutputPath) -Force |
    Out-Null

$requirementsPath = Join-Path $repositoryRoot "requirements-agentcore.txt"
$resolvedPython = [System.IO.Path]::GetFullPath(
    (Join-Path $repositoryRoot $PythonExecutable)
)
if (-not (Test-Path -LiteralPath $resolvedPython -PathType Leaf)) {
    throw "The configured Python executable is not available."
}
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    uv pip install `
        --python-platform aarch64-manylinux2014 `
        --python-version $PythonVersion `
        --target $stagingPath `
        --only-binary=:all: `
        --requirements $requirementsPath
}
else {
    $compactPythonVersion = $PythonVersion.Replace(".", "")
    & $resolvedPython -m pip install `
        --platform manylinux2014_aarch64 `
        --python-version $compactPythonVersion `
        --implementation cp `
        --target $stagingPath `
        --ignore-installed `
        --only-binary=:all: `
        --requirement $requirementsPath
}
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed."
}

Copy-Item -LiteralPath (Join-Path $repositoryRoot "agentcore_main.py") `
    -Destination $stagingPath
Copy-Item -LiteralPath (Join-Path $repositoryRoot "claim_intake_agentcore_main.py") `
    -Destination $stagingPath
Copy-Item -LiteralPath (Join-Path $repositoryRoot "app") `
    -Destination $stagingPath -Recurse
Copy-Item -LiteralPath (Join-Path $repositoryRoot "data") `
    -Destination $stagingPath -Recurse

Get-ChildItem -LiteralPath $stagingPath -Directory -Recurse `
    -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $stagingPath -File -Recurse |
    Where-Object { $_.Extension -in ".pyc", ".pyo" } |
    Remove-Item -Force

if (Test-Path -LiteralPath $resolvedOutputPath) {
    Remove-Item -LiteralPath $resolvedOutputPath -Force
}
& $resolvedPython (Join-Path $repositoryRoot "scripts/create_agentcore_archive.py") `
    $stagingPath $resolvedOutputPath
if ($LASTEXITCODE -ne 0) {
    throw "Deployment ZIP creation failed."
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($resolvedOutputPath)
try {
    $archiveFiles = @(
        $archive.Entries |
            Where-Object { $_.Length -gt 0 } |
            ForEach-Object { $_.FullName.Replace("\", "/") }
    )
    $requiredFiles = @(
        "agentcore_main.py",
        "app/agentcore_adapter.py",
        "claim_intake_agentcore_main.py",
        "app/claim_intake_agentcore_adapter.py",
        "bedrock_agentcore/__init__.py",
        "opentelemetry-instrument"
    )
    foreach ($requiredFile in $requiredFiles) {
        if ($requiredFile -notin $archiveFiles) {
            throw "Deployment ZIP is missing required file: $requiredFile"
        }
    }
    $launcherEntry = $archive.Entries |
        Where-Object { $_.FullName -eq "opentelemetry-instrument" } |
        Select-Object -First 1
    $launcherMode = ($launcherEntry.ExternalAttributes -shr 16) -band 0x1FF
    if ($launcherMode -ne 493) {
        throw "The OpenTelemetry launcher must have Linux mode 0755."
    }
    if ($archiveFiles.Count -lt 10) {
        throw "Deployment ZIP contains too few files to be deployable."
    }
    $uncompressedBytes = (
        $archive.Entries | Measure-Object -Property Length -Sum
    ).Sum
}
finally {
    $archive.Dispose()
}

$maximumZipBytes = 250MB
if ((Get-Item -LiteralPath $resolvedOutputPath).Length -gt $maximumZipBytes) {
    throw "Deployment ZIP exceeds AgentCore's 250 MB compressed limit."
}
$maximumUncompressedBytes = 750MB
if ($uncompressedBytes -gt $maximumUncompressedBytes) {
    throw "Deployment ZIP exceeds AgentCore's 750 MB uncompressed limit."
}

Remove-Item -LiteralPath $stagingPath -Recurse -Force
Write-Output $resolvedOutputPath
