# Managed Knowledge Base Development

Step 12 uses an Amazon Bedrock Managed Knowledge Base with service-managed
embeddings. Terraform creates no embedding-model ARN, OpenSearch collection,
database, vector bucket, or other customer-managed vector store.

## Component boundaries

- `infra/modules/knowledge_documents` creates the private, encrypted S3 source
  bucket.
- `infra/modules/managed_knowledge_base` creates the dedicated service role,
  S3 access policy, Managed Knowledge Base, managed S3 connector, and a reusable
  least-privilege `bedrock:Retrieve` policy for a future application runtime.
- `data/knowledge` contains only synthetic process guidance and no case records.
- `scripts/sync-knowledge-base.ps1` performs the explicit upload and ingestion.
- `app.tools.search_process_knowledge` performs retrieval only. It does not call
  `RetrieveAndGenerate`, a Mantle model, or an authoritative case repository.

The Managed Knowledge Base service role has read access only to the configured
knowledge-document prefix. Service-managed embeddings require no model ARN or
customer-managed Bedrock model access.

## 1. Validate and review the infrastructure

From `infra/environments/dev`:

```powershell
terraform init -upgrade
terraform fmt -check -recursive ..\..
terraform validate
terraform plan -out step12.tfplan
terraform show step12.tfplan
```

Before applying, verify the plan contains:

- One new private S3 knowledge bucket and its security resources.
- One dedicated Bedrock service role with prefix-scoped S3 read access.
- One `aws_bedrockagent_knowledge_base` with `type = "MANAGED"` and
  `embedding_model_type = "MANAGED"`.
- One `aws_bedrockagent_data_source` with a managed S3 connector.
- One unattached application retrieval policy containing only
  `bedrock:Retrieve` for the new Knowledge Base.
- No vector-store resource and no embedding-model ARN.

`terraform apply` creates billable AWS resources. Run it only after reviewing the
account, Region, resource count, IAM policies, and budget:

```powershell
terraform apply step12.tfplan
```

## 2. Capture the deployment outputs

Still in `infra/environments/dev`:

```powershell
$knowledgeBucket = terraform output -raw knowledge_documents_bucket_name
$knowledgePrefix = terraform output -raw knowledge_documents_prefix
$knowledgeBaseId = terraform output -raw bedrock_knowledge_base_id
$dataSourceId = terraform output -raw bedrock_knowledge_data_source_id
```

The application consumes only `bedrock_knowledge_base_id`. The other values are
deployment and ingestion inputs.

## 3. Upload and ingest the synthetic corpus

Return to the repository root and run the explicit sync script:

```powershell
Set-Location ..\..\..

.\scripts\sync-knowledge-base.ps1 `
  -BucketName $knowledgeBucket `
  -KnowledgeBaseId $knowledgeBaseId `
  -DataSourceId $dataSourceId `
  -Prefix $knowledgePrefix `
  -Profile "anekur-admin" `
  -Region "us-east-1"
```

The script uploads only Markdown files under `data/knowledge`, starts one
ingestion job, and waits for `COMPLETE`. It does not delete remote objects and it
does not invoke Mantle.

## 4. Run the opt-in retrieval verification

The integration test verifies the deployed Knowledge Base is managed, uses managed
embeddings, has no embedding-model ARN or vector configuration, and returns only
locations inside the isolated knowledge-document prefix.

```powershell
$env:AWS_PROFILE = "anekur-admin"
$env:AWS_REGION = "us-east-1"
$env:BEDROCK_KNOWLEDGE_BASE_ID = $knowledgeBaseId
$env:KNOWLEDGE_DOCUMENTS_BUCKET = $knowledgeBucket
$env:KNOWLEDGE_DOCUMENTS_PREFIX = $knowledgePrefix
$env:RUN_KNOWLEDGE_BASE_INTEGRATION = "1"

.\.venv\Scripts\python.exe -m pytest -m integration `
  tests\integration\test_knowledge_search.py

Remove-Item Env:RUN_KNOWLEDGE_BASE_INTEGRATION
Remove-Item Env:KNOWLEDGE_DOCUMENTS_PREFIX
Remove-Item Env:KNOWLEDGE_DOCUMENTS_BUCKET
Remove-Item Env:BEDROCK_KNOWLEDGE_BASE_ID
```

Normal test runs exclude this integration test and make no Knowledge Base calls.

## 5. Use retrieval in application code

```python
from app.config import ApplicationSettings
from app.tools import create_knowledge_retriever, search_process_knowledge

settings = ApplicationSettings.from_environment()
retriever = create_knowledge_retriever(settings)
results = search_process_knowledge(
    retriever,
    "What should happen when required process evidence is missing?",
)

for result in results:
    print(result.guidance)
    print(result.source_id)
    print(result.document_location)
```

Each result is retrieval evidence, not a generated answer or an authoritative
case fact. Step 13 may supply these results to the separate Mantle model while
preserving their source identifiers and document locations.
