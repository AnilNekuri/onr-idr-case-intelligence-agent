# Hybrid Development Plan

## Objective

Build the ONR/IDR Case Intake and Intelligence Agent one component at a time using:

- Python for application code.
- Terraform for AWS infrastructure.
- AI to implement narrowly scoped components.
- Human review and individual testing before components are connected.

The implementation specification remains in
`ONR_IDR_Case_Intelligence_Agent_Codex_Guide.md`.

## Component Development Loop

Use this loop for every component:

1. Define the component's responsibility, input, output, business rules, and failure cases.
2. Ask AI to implement only that component and its tests.
3. Read and understand the implementation before running it.
4. Run the unit tests.
5. Manually test at least one normal case and one failure case.
6. Explain the implementation and its tradeoffs in your own words.
7. Commit the working component.
8. Continue only after the component passes its checkpoint.

### Reusable AI Prompt

```text
Implement only <component name>.

Before writing code:
1. Restate its responsibility.
2. List its inputs, outputs, and edge cases.
3. Show the files you plan to change.

Requirements:
- <component-specific behavior>
- Do not modify unrelated components.
- Add focused pytest tests.
- Keep AWS and LLM dependencies out unless this is specifically an integration component.

After implementation:
1. Explain the important code paths.
2. Show the test command.
3. Show how to test one success and one failure manually.
```

## Phase 1: Repository Foundation

### Step 1: Create the Project Structure

Start with:

```text
app/
  models/
  services/
  repositories/
  tools/
  aws/
data/
infra/
  modules/
  environments/dev/
tests/
  unit/
  contract/
  integration/
scripts/
```

Initial Python tooling:

- Python 3.12 or newer.
- Pydantic.
- pytest.
- Ruff.
- mypy.
- boto3.

Do not add Streamlit, Bedrock agent libraries, AgentCore, RAG, or Textract yet.

Checkpoint:

- The virtual environment can be created.
- Dependencies install successfully.
- An empty pytest run and lint command work.

## Phase 2: Local Deterministic Python

### Step 2: Build the Domain Model

Implement:

- `Case`.
- `CaseEvent`.
- `Document`.
- Enums such as `CaseType` and `CaseStatus`.

Test:

- A valid case.
- Missing required fields.
- Invalid dates.
- Invalid case type.
- JSON serialization and loading.

Constraint: no AWS or LLM dependencies.

### Step 3: Build the Local Case Repository

Define a repository interface:

```python
class CaseRepository(Protocol):
    def get(self, case_id: str) -> Case | None: ...
    def save(self, case: Case) -> None: ...
```

First implement `JsonCaseRepository`.

Test:

- Loading an existing case.
- Looking up an unknown case.
- Saving and reloading a case.
- Handling malformed JSON.

Later, `DynamoDbCaseRepository` will implement the same interface without changing
the business logic.

### Step 4: Build Deterministic Tools

Implement and test one tool at a time in this order:

1. `get_case`.
2. `get_case_timeline`.
3. `get_missing_information`.
4. `calculate_deadline_risk`.

Rules:

- Write expected examples before implementation.
- Pass the current date into date calculations instead of calling `date.today()`
  inside the business logic.
- Test boundary values.
- Do not involve an LLM.

Deadline-risk cases:

```text
Past deadline    -> MISSED
0-3 days         -> HIGHHi Hi
4-7 days         -> MEDIUM
More than 7 days -> LOW
```

### Step 5: Add the Local Service Layer

Create a `CaseService` that coordinates the repository and deterministic tools.

Initial operations:

```text
create_case
get_case
get_timeline
get_missing_information
get_deadline_risk
```

Test the service with an in-memory or JSON repository.

Phase checkpoint:

- Five deterministic synthetic cases load successfully.
- Timelines are sorted.
- Missing information is correct.
- Deadline boundaries are correct.
- All unit tests pass without AWS credentials or an LLM.

## Phase 3: Terraform and AWS Data Infrastructure

### Step 6: Create the Terraform Foundation

Start with:

```text
infra/
  modules/
    budget/
    case_table/
    case_documents/
  environments/
    dev/
```

Configure:

- AWS provider and pinned version constraints.
- Required Terraform version.
- Common resource tags.
- A low AWS budget alert.
- Development-environment variables.
- Useful Terraform outputs.

Validate before applying:

```powershell
terraform fmt -check -recursive
terraform init
terraform validate
terraform plan
```

Review every resource in `terraform plan` before approving `terraform apply`.

### Step 7: Create DynamoDB

Create only the case table first.

Initial design:

```text
Partition key: case_id
Billing mode: PAY_PER_REQUEST
Encryption: enabled
Point-in-time recovery: optional for the demo
```

After applying Terraform:

1. Inspect the table in AWS.
2. Implement `DynamoDbCaseRepository`.
3. Run the repository contract tests against a development table.
4. Manually verify create, read, update, and not-found behavior.

Unit tests should remain local. Real AWS tests must be marked as integration tests.

### Step 8: Create the Case-Document S3 Bucket

Create a separate Terraform module with:

- Public access blocked.
- Encryption enabled.
- Versioning if required.
- A lifecycle rule for temporary demo documents.
- CORS only if direct browser uploads need it.

Then implement `S3DocumentRepository`.

Test:

- PDF upload.
- Metadata storage.
- Object-key generation.
- Missing files.
- Unsupported file types.
- Failed AWS requests.

Do not add Textract yet.

### Step 9: Connect Python to AWS

Select repository implementations through configuration:

```text
CASE_REPOSITORY=json
CASE_REPOSITORY=dynamodb
```

The service layer must not know which repository implementation is active.

Phase checkpoint:

1. Create a synthetic case.
2. Save it to DynamoDB.
3. Upload a synthetic PDF to S3.
4. Retrieve the case.
5. Calculate its timeline, missing information, and deadline risk.

Do not continue until this flow works without an LLM.

## Phase 4: AI Integration

### Step 10: Add the Bedrock Mantle Model Client

Create a narrow model interface:

```python
class LanguageModel(Protocol):
    def generate(self, prompt: str) -> str: ...
```

Test orchestration with a fake model. Keep real Bedrock Mantle calls in integration
tests because they cost money and are nondeterministic.

Initially, allow the model to summarize only facts supplied to it.

### Step 11: Add Grounding Tests

Verify that the agent:

- Retrieves the case before answering.
- Does not invent dates, documents, events, or status.
- Separates authoritative facts from recommendations.
- Reports unavailable evidence.
- Uses deterministic deadline results unchanged.

Maintain a small evaluation dataset with expected facts for every synthetic case.

## Phase 5: Knowledge Base and RAG

### Step 12: Add Managed Knowledge-Base Infrastructure

Use an Amazon Bedrock Managed Knowledge Base with managed embeddings. This keeps
embedding-model selection, hosting, scaling, indexing, and vector storage inside
the managed service. It also avoids making this project depend on a
customer-managed `bedrock-runtime` embedding-model quota.

Create separate Terraform modules or deployment components for:

- Knowledge-document S3 storage.
- Bedrock Managed Knowledge Base configured to use managed embeddings.
- IAM roles and least-privilege policies.
- S3 data-source and ingestion configuration.
- Application configuration that exposes the deployed knowledge-base ID.

Do not create a separate vector store, configure an embedding-model ARN, or add a
vector-store endpoint for this path. Treat a customer-managed Knowledge Base as a
future fallback only if regular Bedrock embedding-model quota becomes available.

Add this only after the deterministic application and Bedrock Mantle model wrapper
work.

Implement `search_process_knowledge()` with the Knowledge Base `Retrieve` API,
not `RetrieveAndGenerate`, and verify that it returns:

- Relevant process guidance.
- Source identifiers.
- Citations or document locations.
- No authoritative case facts.

Keep ingestion and retrieval integration tests opt-in because they use deployed
AWS resources and can incur cost. Verify that documents sync and retrieval works
without a customer-managed embedding-model ARN or vector store.

### Step 13: Assemble the Agent

The agent coordinates existing tools instead of reproducing their logic:

```text
get_case
get_case_timeline
get_missing_information
calculate_deadline_risk
search_process_knowledge
```

Keep retrieval and generation as separate operations:

1. Retrieve case facts and deterministic results.
2. Call `search_process_knowledge()` when process guidance is needed.
3. Preserve the retrieved passages, source identifiers, and document locations.
4. Send the grounded context to the Bedrock Mantle language-model client.
5. Return the generated answer with the retrieval citations.

Do not use Knowledge Base `RetrieveAndGenerate`; it would introduce a separate
generation-model dependency outside the Mantle adapter.

Test these questions individually:

```text
What is the case status?
What information is missing?
Is the deadline at risk?
Why is the case blocked?
What should happen next?
```

Record the retrieved facts and tool results so each answer can be inspected.

Phase checkpoint:

- Answers are grounded in retrieved case facts.
- Process recommendations cite knowledge sources.
- Mantle generates responses only after the required retrieval steps complete.
- Missing evidence is reported honestly.
- Evaluation tests pass for the five synthetic cases.

## Phase 6: User Interface

### Step 14: Add Streamlit

Build one workflow at a time:

1. Case lookup and deterministic results.
2. Case submission.
3. Document upload.
4. Case summary.
5. Chat with citations from Knowledge Base retrieval.

The UI must call the service layer rather than calling DynamoDB, S3, or Bedrock
directly.

Checkpoint:

- Each workflow can be manually demonstrated.
- Errors are shown clearly.
- The UI does not contain duplicate business rules.

## Phase 7: AgentCore and Optional Features

### Step 15: Add AgentCore

Migrate to AgentCore only after the Python agent works locally. Deployment should
change the runtime boundary, not the business behavior.

Add:

- AgentCore-compatible entry point.
- Terraform-managed runtime resources where supported and appropriate.
- Runtime permissions for Knowledge Base retrieval and Bedrock Mantle inference.
- CloudWatch and AgentCore observability.
- Deployment and invocation integration tests.

### Step 16: Consider Optional Features

Only after the MVP is stable, consider:

- One Textract-backed PDF workflow.
- Broader agent evaluations.
- Multi-case insights.
- Production authentication.

## Test Strategy

Use four distinct test groups:

### Unit Tests

Pure Python tests that are fast and require no AWS credentials.

### Contract Tests

Verify that JSON, in-memory, and DynamoDB repositories obey the same behavioral
contract.

### Integration Tests

Use dedicated development AWS resources. These tests must be explicitly selected
and must never run accidentally as part of the unit-test suite.

Keep the paid Mantle inference test separate from Managed Knowledge Base ingestion
and retrieval tests so either integration can be diagnosed and run independently.

### Evaluation Tests

Check factual grounding, tool selection, evidence handling, and expected AI
behavior.

Useful commands:

```powershell
pytest tests/unit
pytest tests/contract
pytest -m integration
ruff check .
ruff format --check .
mypy app
terraform fmt -check -recursive infra
terraform validate
```

## Git Workflow

Create one commit per working component. Examples:

```text
feat: add case domain models
feat: add JSON case repository
feat: add deterministic timeline tool
feat: add deadline risk calculation
infra: add DynamoDB case table
feat: add DynamoDB case repository
```

Do not combine several untested components into one commit.

## Next Component

Begin with the Pydantic domain model and focused unit tests. This creates the stable
data contract that the local repositories, AWS adapters, deterministic tools, and
AI agent will use.
