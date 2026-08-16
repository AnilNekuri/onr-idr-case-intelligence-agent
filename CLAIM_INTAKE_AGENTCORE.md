# Conversational Claim Intake AgentCore Runtime

The claim-intake runtime is separate from the existing case-question runtime.
It owns conversational routing, temporary-document review, explicit submission,
grounded summaries, and Knowledge Base next actions. The existing runtime remains
read-only for authoritative cases.

## Conversation contract

Clients reuse one `runtimeSessionId` and send explicit events:

```json
{"action":"START"}
```

```json
{"action":"MESSAGE","message":"I want to process a claim"}
```

After the client uploads the PDF to the configured private document bucket:

```json
{
  "action": "DOCUMENT_UPLOADED",
  "document": {
    "document_id": "DOC-1",
    "file_name": "notice.pdf",
    "s3_key": "temporary/INTAKE-session/DOC-1/notice.pdf"
  }
}
```

Submission is a separate, explicit event:

```json
{
  "action": "CONFIRM_SUBMISSION",
  "confirmation": true,
  "idempotency_key": "one-stable-key-for-this-confirmation"
}
```

The runtime returns a validated `ClaimIntakeResponse` containing the current
state, expected input, document type, extracted fields, missing fields, summary,
submission readiness, case ID, next actions, and Knowledge Base citations.

## Trust and persistence boundaries

- The LLM classifies conversational intent, with strict JSON validation and a
  deterministic fallback.
- Textract and Bedrock extract the document, but deterministic signals must
  confirm ONR or IDR. `UNKNOWN` cannot proceed.
- Missing review fields block submission.
- Only `CONFIRM_SUBMISSION` with `confirmation=true` and an idempotency key can
  create a case.
- The case ID is derived from the runtime session, so retries cannot create a
  second case.
- DynamoDB stores durable workflow state; an AgentCore microVM is not treated as
  authoritative storage.
- General and post-submission guidance comes from the managed Knowledge Base and
  retains citations.

## Build and validate

The shared deployment ZIP contains both independent entry points:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\build-agentcore-package.ps1 `
  -OutputPath output/agentcore/claim_intake_deployment_package.zip
```

Then validate Terraform from `infra/environments/dev`:

```powershell
terraform init
terraform fmt -check -recursive ..\..
terraform validate
```

## Review and deploy

Set these development variables only when ready to create the paid runtime:

```hcl
enable_claim_intake_agentcore_runtime = true
agentcore_bedrock_model_id            = "your-supported-mantle-model-id"
```

Review before applying:

```powershell
terraform plan -out claim-intake.tfplan
terraform show claim-intake.tfplan
terraform apply claim-intake.tfplan
```

Applying creates a separate AgentCore runtime and endpoint, a private deployment
bucket, IAM role/policy, and a DynamoDB intake-session table. It also enables
billable Textract, Knowledge Base retrieval, and model calls when invoked.

After apply, restart the local UI with `scripts/run-local-app.ps1`. The launcher
loads these outputs automatically:

```text
CLAIM_INTAKE_TABLE
CLAIM_AGENTCORE_RUNTIME_ARN
CLAIM_AGENTCORE_ENDPOINT_NAME
```

When both runtime values are present, the Assistant page becomes a thin client
to the remote runtime. Without them, it retains the local demonstration flow.
