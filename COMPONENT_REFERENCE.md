# Component Reference

A component is a small part of the system with one clear responsibility that can
be implemented and tested independently.

## Python Components

### 1. Domain Models

- `Case`.
- `CaseEvent`.
- `Document`.
- Status and case-type enums.

Responsibility: define the system's data structures and validation rules.

### 2. Case Repository

- `JsonCaseRepository` for local development.
- `DynamoDbCaseRepository` for AWS.

Responsibility: save and retrieve authoritative case records.

### 3. Document Repository

- Local document storage for development.
- `S3DocumentRepository` for AWS.

Responsibility: upload, identify, and retrieve supporting documents.

### 4. Case Service

- Creates and updates cases.
- Coordinates repositories and business rules.
- Keeps the UI separate from AWS implementation details.

Responsibility: provide the application's use cases through one stable interface.

### 5. Timeline Tool

- Sorts case events chronologically.
- Produces the case history.

Responsibility: create a deterministic timeline from authoritative events.

### 6. Missing Information Tool

- Finds missing fields.
- Finds missing documents.
- Finds missing responses.

Responsibility: identify incomplete case information using explicit Python rules.

### 7. Deadline Risk Tool

- Calculates days remaining.
- Returns `LOW`, `MEDIUM`, `HIGH`, or `MISSED`.

Responsibility: calculate deadline risk deterministically instead of asking an LLM
to calculate dates.

### 8. Knowledge Search Tool

- Searches ONR/IDR process documents.
- Calls the Bedrock Managed Knowledge Base `Retrieve` API.
- Returns relevant passages, source identifiers, and document locations.
- Does not provide authoritative case facts.
- Does not generate an answer.

Responsibility: retrieve process guidance from the knowledge base.

### 9. Bedrock Mantle Model Client

- Provides a small Python interface to a model on the Bedrock Mantle endpoint.
- Keeps Mantle-specific code out of the business logic.

Responsibility: generate an answer from authoritative case facts and any process
guidance already retrieved by the Knowledge Search Tool.

### 10. Case Intelligence Agent

- Coordinates the case, timeline, missing-information, deadline, and knowledge
  tools.
- Produces grounded summaries and recommendations.
- Does not replace deterministic business rules.

Responsibility: combine authoritative facts and process guidance into a useful
response.

### 11. Configuration

- Selects local or AWS repositories.
- Holds environment names, table names, bucket names, the managed knowledge-base
  ID, and the Mantle model ID.

Responsibility: separate environment-specific settings from application code.

### 12. Streamlit UI

- Case-submission view.
- Case-intelligence view.
- Calls the service layer instead of calling AWS directly.

Responsibility: provide the user-facing workflow.

## Terraform Components

Each infrastructure component should be a separate Terraform module.

### 1. Budget Module

Responsibility: create spending alerts and help control development costs.

### 2. DynamoDB Module

Responsibility: create the authoritative case table.

### 3. Case Documents S3 Module

Responsibility: create secure storage for uploaded case PDFs.

### 4. Knowledge Documents S3 Module

Responsibility: store synthetic ONR/IDR process guidance.

### 5. IAM Module

Responsibility: create roles and least-privilege permissions for the application
and AWS services.

### 6. Bedrock Knowledge Base Module

Responsibility: create a Bedrock Managed Knowledge Base with managed embeddings,
its S3 data source, ingestion configuration, and related permissions. The managed
service owns embedding-model selection, indexing, and vector storage; this module
does not create a separate vector store or configure an embedding-model ARN.

### 7. AgentCore Module

Responsibility: deploy the completed agent. Add this only after the agent works
locally.

### 8. Observability Module

Responsibility: create logs, metrics, and CloudWatch configuration.

## Testing Components

### Unit Tests

Test one Python function or class without AWS credentials or network access.

### Contract Tests

Ensure local JSON, in-memory, and DynamoDB repositories provide the same behavior.

### Integration Tests

Test Python components against dedicated development AWS resources. Keep Mantle
inference tests separate from Managed Knowledge Base ingestion and retrieval tests,
and require explicit opt-in for both.

### Agent Evaluation Tests

Verify grounding, citations, tool use, and the absence of invented case facts.

### Terraform Validation

Run formatting, validation, and plan checks before applying infrastructure.

## Recommended Build Order

```text
Domain models
    |
JSON case repository
    |
Timeline tool
    |
Missing-information tool
    |
Deadline-risk tool
    |
Case service
    |
Terraform foundation
    |
DynamoDB repository
    |
S3 document repository
    |
Bedrock Mantle model client
    |
Managed Knowledge Base search
    |
Agent
    |
Streamlit
    |
AgentCore
```

## Starting Point

The first independently testable component is the domain model. The JSON case
repository comes next. Together, they establish a stable data contract without
requiring AWS credentials or an LLM.
