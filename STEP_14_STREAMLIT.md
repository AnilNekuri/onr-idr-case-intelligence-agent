# Step 14: Streamlit

The Streamlit UI exposes five workflows without importing DynamoDB, S3, or
Bedrock adapters directly. Four workflows invoke local application services;
Case chat invokes the deployed AgentCore runtime through an SDK-backed client.

## Run locally

Install dependencies and start the app from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

The default JSON repository supports case lookup and case submission without AWS
configuration. Use synthetic IDs such as `CASE-1001` through `CASE-1005` for the
lookup demonstration.

For a complete scripted presentation with upload-ready synthetic PDFs, follow
[`STEP_14_DEMO.md`](STEP_14_DEMO.md).

The service and AWS interactions for every workflow are documented in
[`STEP_14_SEQUENCE_DIAGRAMS.md`](STEP_14_SEQUENCE_DIAGRAMS.md).

## Configure AWS-backed workflows

Document upload requires the case-document bucket. Case summary requires the
Mantle model. Case chat requires the deployed AgentCore runtime ARN and its
stable endpoint name; Knowledge Base and model configuration stay inside the
runtime.

```powershell
$env:CASE_REPOSITORY = "dynamodb"
$env:DYNAMODB_CASE_TABLE = "<development-case-table>"
$env:S3_CASE_DOCUMENTS_BUCKET = "<development-case-document-bucket>"
$env:BEDROCK_MODEL_ID = "<mantle-model-id>"
$env:AGENTCORE_RUNTIME_ARN = "<deployed-agentcore-runtime-arn>"
$env:AGENTCORE_ENDPOINT_NAME = "live"
$env:AWS_REGION = "us-east-1"
$env:AWS_PROFILE = "<development-profile>"

.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Missing or invalid configuration and adapter failures are rendered in the active
workflow rather than producing a silent failure. Document upload accepts PDFs
only; the document service and repository enforce the content validation.

## Manual checkpoint

1. Look up `CASE-1001` and inspect status, deadline risk, missing information,
   timeline, and documents.
2. Submit a case once with a supplied ID and once with the ID blank.
3. Upload a PDF to an existing case and confirm its document metadata.
4. Generate a case summary with `BEDROCK_MODEL_ID` configured.
5. Ask a next-action question in Case chat and inspect the separate Knowledge
   Base citation list.

Run automated verification with:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app streamlit_app.py tests\unit
.\.venv\Scripts\python.exe -m mypy app streamlit_app.py tests\unit
```
