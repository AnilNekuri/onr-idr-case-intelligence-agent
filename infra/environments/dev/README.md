# Development Terraform Environment

This development root module configures the AWS provider, common resource tags,
a low monthly AWS budget, the DynamoDB case table, the private case-document
bucket, the Step 12 Managed Knowledge Base resources, and the opt-in Step 15
AgentCore runtime and observability resources.

The development case and knowledge buckets set `force_destroy = true` for
convenient demo cleanup. Running `terraform destroy` can therefore permanently
remove every object and object version in those buckets. Production environments
should retain the module default of `false`.

## Prerequisites

- Terraform 1.15.x
- AWS credentials with permission to read caller identity and manage AWS Budgets,
  S3, IAM, and Amazon Bedrock Knowledge Bases
- An email address that can receive the budget notifications

## Validate and review

From this directory in PowerShell:

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars and replace the sample email and owner.

terraform fmt -check -recursive ..\..
terraform init -upgrade
terraform validate
terraform plan -out dev.tfplan
terraform show dev.tfplan
```

Review every planned attribute. Do not run `terraform apply` until the email,
USD limit, AWS account, table settings, bucket security settings, tags, and
resource count are all correct.

## Deploy and test Step 12

See [`../../../KNOWLEDGE_BASE_DEVELOPMENT.md`](../../../KNOWLEDGE_BASE_DEVELOPMENT.md)
for the explicit Managed Knowledge Base apply, upload, ingestion, configuration
verification, and retrieval-test procedure. Those paid actions are intentionally
separate from normal Terraform validation and unit tests.

## Deploy and test Step 15

See [`../../../STEP_15_AGENTCORE.md`](../../../STEP_15_AGENTCORE.md) for the
local-agent gate, Linux ARM64 ZIP build, AgentCore and Transaction Search flags,
reviewed apply, CloudWatch verification, and opt-in paid invocation test.

## Run the explicit DynamoDB integration contract test

Only after applying and inspecting the development table:

```powershell
$env:AWS_PROFILE = "anekur-admin"
$env:AWS_REGION = "us-east-1"
$env:DYNAMODB_CASE_TABLE = terraform output -raw case_table_name
$env:RUN_AWS_INTEGRATION = "1"

Set-Location ..\..\..
.\.venv\Scripts\python.exe -m pytest -m integration tests\integration

Remove-Item Env:RUN_AWS_INTEGRATION
Remove-Item Env:DYNAMODB_CASE_TABLE
```

The test creates a uniquely named synthetic case, verifies create, read, update,
and not-found behavior, and removes its test record in a `finally` block.

## Inspect and test the Step 8 S3 bucket

Only after applying the reviewed Step 8 plan:

```powershell
$bucket = terraform output -raw case_documents_bucket_name

aws s3api get-public-access-block --bucket $bucket --profile anekur-admin
aws s3api get-bucket-encryption --bucket $bucket --profile anekur-admin
aws s3api get-bucket-versioning --bucket $bucket --profile anekur-admin
aws s3api get-bucket-lifecycle-configuration --bucket $bucket --profile anekur-admin
```

Run the explicitly selected repository integration test from the repository
root:

```powershell
$env:AWS_PROFILE = "anekur-admin"
$env:AWS_REGION = "us-east-1"
$env:S3_CASE_DOCUMENTS_BUCKET = $bucket
$env:RUN_AWS_INTEGRATION = "1"

Set-Location ..\..\..
.\.venv\Scripts\python.exe -m pytest -m integration tests\integration\test_s3_document_repository.py

Remove-Item Env:RUN_AWS_INTEGRATION
Remove-Item Env:S3_CASE_DOCUMENTS_BUCKET
```

The test uploads a synthetic PDF under `temporary/`, verifies bytes and
metadata, checks missing-file behavior, and deletes the test object in a
`finally` block. Textract is not configured or called.
