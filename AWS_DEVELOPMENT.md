# AWS Development Configuration

Application repository selection happens at startup in `app.config` and
`app.repositories.factory`. Services receive repository protocols and do not
know whether data is stored in JSON, DynamoDB, or S3.

## Local JSON case storage

```powershell
$env:CASE_REPOSITORY = "json"
$env:JSON_CASES_PATH = "data/cases.json"
```

`CASE_REPOSITORY` defaults to `json`, and `JSON_CASES_PATH` defaults to
`data/cases.json`.

## Development AWS storage

Authenticate first:

```powershell
aws sso login --profile anekur-admin
aws sts get-caller-identity --profile anekur-admin
```

Configure the process:

```powershell
$env:CASE_REPOSITORY = "dynamodb"
$env:DYNAMODB_CASE_TABLE = "onr-idr-case-intelligence-dev-cases"
$env:S3_CASE_DOCUMENTS_BUCKET = "onr-idr-case-intelligence-dev-992020986043-case-documents"
$env:AWS_REGION = "us-east-1"
$env:AWS_PROFILE = "anekur-admin"
```

## Explicit Step 9 checkpoint

The checkpoint writes one clearly labeled synthetic case and one synthetic PDF.
It uses no LLM or AI model. Both an environment flag and a command-line flag are
required to prevent accidental AWS writes:

```powershell
$env:RUN_AWS_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m app.checkpoint --confirm-development-aws
Remove-Item Env:RUN_AWS_INTEGRATION
```

The PDF is stored under the `temporary/` prefix and is eligible for the bucket's
30-day lifecycle expiration. The case remains in DynamoDB until explicitly
deleted.

Normal unit tests exclude real-AWS integration tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run the guarded phase integration test explicitly with the AWS variables above:

```powershell
$env:RUN_AWS_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m pytest -m integration tests\integration\test_phase_checkpoint.py
Remove-Item Env:RUN_AWS_INTEGRATION
```

The integration test deletes its unique case and PDF in a `finally` block.

## Managed process-knowledge retrieval

Step 12 uses a separate S3 bucket and a Bedrock Managed Knowledge Base. Configure
the deployed Knowledge Base ID without configuring an embedding model or vector
store:

```powershell
$env:BEDROCK_KNOWLEDGE_BASE_ID = "terraform-output-id"
```

`search_process_knowledge()` calls the `Retrieve` API and returns process
passages, source identifiers, and document locations. It does not call
`RetrieveAndGenerate` or the Mantle model. See
[`KNOWLEDGE_BASE_DEVELOPMENT.md`](KNOWLEDGE_BASE_DEVELOPMENT.md) for deployment,
ingestion, and opt-in integration-test commands.
