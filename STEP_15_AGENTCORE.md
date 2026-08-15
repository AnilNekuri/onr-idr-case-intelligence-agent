# Step 15: Amazon Bedrock AgentCore Runtime

Step 15 keeps `GroundedCaseAgent` and its tool orchestration unchanged. The new
`agentcore_main.py` entry point is only an HTTP runtime adapter: it validates an
AgentCore payload, loads the existing environment configuration, calls
`create_grounded_case_agent`, and returns the existing inspectable response.

The deployment uses AgentCore direct code deployment rather than a container.
The ZIP is built with Linux ARM64 wheels, stored in a private versioned S3
bucket, and deployed through Terraform's native AgentCore runtime and endpoint
resources.

## 1. Reconfirm the local agent

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\scripts\run-grounded-agent.ps1 `
  -CaseId "CASE-1001" `
  -Question "What should happen next?" `
  -CurrentDate "2026-08-14"
```

Do not enable the runtime until this local boundary passes with the intended
Knowledge Base and Mantle model.

## 2. Build the direct-deploy ZIP

Run the package builder:

```powershell
.\scripts\build-agentcore-package.ps1
```

The script prefers `uv` when it is installed and otherwise uses the current
virtual environment's `pip` cross-platform wheel installer. Both paths install
Python 3.13-compatible Linux ARM64 wheels and write the ignored artifact to
`output/agentcore/deployment_package.zip`. It includes the AgentCore SDK and
AWS Distro for OpenTelemetry so Terraform can use this entry point:

```text
opentelemetry-instrument agentcore_main.py
```

The builder excludes the Streamlit-only dependency tree and verifies required
files plus AgentCore's 250 MB compressed-size limit before reporting success.
On Windows, it also replaces pip's `.exe` console wrapper with a Linux launcher
stored with executable mode `0755`; AgentCore cannot start a Windows console
wrapper.

## 3. Review the Terraform boundary

Set these values in `infra/environments/dev/terraform.tfvars`:

```hcl
enable_agentcore_runtime   = true
agentcore_bedrock_model_id = "the-model-id-returned-by-bedrock-mantle"
```

The runtime role can only:

- read the direct-deploy ZIP;
- read one case with DynamoDB `GetItem`;
- call `bedrock:Retrieve` on this environment's Knowledge Base;
- call the four documented `bedrock-mantle` inference/project actions;
- write AgentCore logs, traces, and metrics.

The runtime uses public AWS service endpoints and receives only non-secret
environment values. It does not receive a local AWS profile.

CloudWatch Transaction Search is an account-level setting. If it is not
already managed elsewhere, let this Terraform root own it:

```hcl
enable_agentcore_transaction_search = true
agentcore_trace_indexing_percentage = 1
```

The 1% default follows AWS's no-additional-cost indexing recommendation. Do not
enable this flag if another Terraform stack or an administrator already owns
the account's X-Ray trace destination or `Default` indexing rule; import those
resources first or leave the flag disabled.

## 4. Plan and deploy

From `infra/environments/dev`:

```powershell
terraform init
terraform fmt -check -recursive ..\..
terraform validate
terraform plan -out step15.tfplan
terraform show step15.tfplan
terraform apply step15.tfplan
```

The principal running Terraform needs permission to upload and read the S3
artifact, pass the generated execution role, and manage AgentCore, IAM, S3,
CloudWatch Logs, and X-Ray resources. Applying creates paid resources; inspect
the plan first.

## 5. Run deployment and invocation integration tests

Populate the environment from Terraform outputs:

```powershell
$env:AWS_REGION = terraform output -raw aws_region
$env:CASE_REPOSITORY = "dynamodb"
$env:DYNAMODB_CASE_TABLE = terraform output -raw case_table_name
$env:BEDROCK_KNOWLEDGE_BASE_ID = terraform output -raw bedrock_knowledge_base_id
$env:BEDROCK_MODEL_ID = "the-model-id-returned-by-bedrock-mantle"
$env:AGENTCORE_RUNTIME_ID = terraform output -raw agentcore_runtime_id
$env:AGENTCORE_RUNTIME_ARN = terraform output -raw agentcore_runtime_arn
$env:AGENTCORE_ENDPOINT_NAME = terraform output -raw agentcore_endpoint_name
$env:AGENTCORE_LOG_GROUP_NAME = terraform output -raw agentcore_cloudwatch_log_group_name
```

The control-plane check verifies that the runtime and endpoint are ready and
that the AgentCore CloudWatch log group exists:

```powershell
$env:RUN_AGENTCORE_INTEGRATION = "1"
Set-Location ..\..\..
.\.venv\Scripts\python.exe -m pytest -m integration `
  tests\integration\test_agentcore_runtime.py `
  -k "runtime_and_endpoint"
```

If this Terraform root owns Transaction Search, verify its destination and
indexing rule:

```powershell
$env:RUN_AGENTCORE_OBSERVABILITY_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m pytest -m integration `
  tests\integration\test_agentcore_runtime.py `
  -k "transaction_search"
```

The paid invocation test creates a temporary synthetic DynamoDB case, invokes
the stable endpoint, requires non-empty Knowledge Base guidance and citations,
requires Mantle-generated text, and deletes the case in `finally`:

```powershell
$env:RUN_AGENTCORE_INVOCATION_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m pytest -m integration `
  tests\integration\test_agentcore_runtime.py `
  -k "invocation"
```

Unset the three `RUN_AGENTCORE_*` variables after testing. Inspect sessions,
traces, metrics, and logs in CloudWatch's GenAI Observability dashboard.

## References

- [AgentCore direct code deployment for Python](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html)
- [AgentCore Runtime permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html)
- [Bedrock Mantle inference permissions](https://docs.aws.amazon.com/bedrock/latest/userguide/inference.html)
- [AgentCore observability with CloudWatch](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-get-started.html)
- [InvokeAgentRuntime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-invoke-agent.html)
