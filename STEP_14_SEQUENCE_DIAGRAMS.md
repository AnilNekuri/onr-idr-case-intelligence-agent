# Step 14 Sequence Diagrams

These diagrams describe the implemented Streamlit workflows. Streamlit calls
local application services for the first four workflows and invokes the
deployed AgentCore endpoint for Case chat. AWS adapters remain behind those
boundaries.

## LLM boundary

Only case summary and case chat generate text with the configured language
model. Knowledge Base retrieval returns passages and citations but does not
generate the final answer.

```mermaid
flowchart LR
    UI[Streamlit UI]
    CS[CaseService]
    CDS[CaseDocumentService]
    SS[CaseSummaryService]
    Client[AgentCore Client]
    Runtime[AgentCore Runtime]
    Agent[GroundedCaseAgent]
    Tools[Deterministic Tools]
    Search[Knowledge Search]
    LM[LanguageModel]
    Model[Bedrock Mantle Model]

    UI --> CS
    UI --> CDS
    UI --> SS
    UI --> Client
    Client --> Runtime
    Runtime --> Agent
    CS --> Tools
    Agent --> Tools
    Agent --> Search
    SS --> LM
    Agent --> LM
    LM --> Model
```

## 1. Case lookup and deterministic results

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant CS as CaseService
    participant Tools as Deterministic Tools
    participant Repo as CaseRepository
    participant DB as DynamoDB

    User->>UI: Enter case ID
    UI->>CS: get_case(case_id)
    CS->>Repo: get(case_id)
    Repo->>DB: GetItem
    DB-->>Repo: Case item or not found
    Repo-->>CS: Case or None
    CS-->>UI: Case or None

    alt Case not found
        UI-->>User: Show case-not-found warning
    else Case found
        loop Timeline, missing information, deadline risk
            UI->>CS: Request deterministic result
            CS->>Tools: Execute deterministic tool
            Tools->>Repo: get(case_id)
            Repo->>DB: GetItem
            DB-->>Repo: Authoritative case
            Repo-->>Tools: Case
            Tools-->>CS: Deterministic result
            CS-->>UI: Result
        end
        UI-->>User: Display case facts and results
    end
```

## 2. Case submission

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant CS as CaseService
    participant Repo as CaseRepository
    participant DB as DynamoDB

    User->>UI: Enter case intake fields
    User->>UI: Select Create case
    UI->>CS: submit_case(intake fields)

    CS->>CS: Generate ID if blank
    CS->>Repo: get(case_id)
    Repo->>DB: GetItem
    DB-->>Repo: Existing item or not found
    Repo-->>CS: Existing case or None

    alt Case ID already exists
        CS-->>UI: CaseAlreadyExistsError
        UI-->>User: Show clear error
    else New case ID
        CS->>CS: Validate dates and required fields
        CS->>CS: Determine initial status
        CS->>CS: Create CASE_CREATED event
        CS->>Repo: save(validated case)
        Repo->>DB: PutItem
        DB-->>Repo: Save completed
        Repo-->>CS: Success
        CS-->>UI: Created Case
        UI-->>User: Show ID, status, and confirmation
    end
```

## 3. Document upload

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant CDS as CaseDocumentService
    participant CS as CaseService
    participant DS as DocumentService
    participant CaseRepo as CaseRepository
    participant DocRepo as DocumentRepository
    participant DB as DynamoDB
    participant S3 as Amazon S3

    User->>UI: Enter case ID and select PDF
    User->>UI: Select Upload document
    UI->>CDS: upload_document(case_id, file)

    CDS->>CS: get_case(case_id)
    CS->>CaseRepo: get(case_id)
    CaseRepo->>DB: GetItem
    DB-->>CaseRepo: Case item or not found
    CaseRepo-->>CS: Case or None
    CS-->>CDS: Case or None

    alt Case not found
        CDS-->>UI: CaseNotFoundError
        UI-->>User: Show case-not-found error
    else Case found
        CDS->>DS: upload_case_pdf(case_id, name, bytes)
        DS->>DocRepo: upload_pdf(...)
        DocRepo->>DocRepo: Validate PDF extension and signature

        alt Invalid PDF
            DocRepo-->>DS: UnsupportedDocumentTypeError
            DS-->>CDS: Upload error
            CDS-->>UI: Upload error
            UI-->>User: Show PDF validation error
        else Valid PDF
            DocRepo->>S3: PutObject
            S3-->>DocRepo: Upload completed
            DocRepo-->>DS: Document metadata
            DS-->>CDS: Document

            CDS->>CS: attach_document(case_id, document)
            CS->>CaseRepo: get(case_id)
            CaseRepo->>DB: GetItem
            DB-->>CaseRepo: Current case
            CaseRepo-->>CS: Case

            CS->>CS: Add document metadata
            CS->>CS: Add DOCUMENT_RECEIVED event
            CS->>CaseRepo: save(updated case)
            CaseRepo->>DB: PutItem
            DB-->>CaseRepo: Update completed

            CS-->>CDS: Updated case
            CDS-->>UI: Updated case and document
            UI-->>User: Show upload confirmation
        end
    end
```

## 4. Case summary

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant CS as CaseService
    participant Repo as CaseRepository
    participant DB as DynamoDB
    participant SS as CaseSummaryService
    participant LM as LanguageModel
    participant Mantle as Bedrock Mantle

    User->>UI: Enter case ID
    User->>UI: Select Generate summary

    UI->>CS: get_case(case_id)
    CS->>Repo: get(case_id)
    Repo->>DB: GetItem
    DB-->>Repo: Case item or not found
    Repo-->>CS: Case or None
    CS-->>UI: Case or None

    alt Case not found
        UI-->>User: Show case-not-found warning
    else Case found
        UI->>SS: summarize(case)
        SS->>SS: Serialize authoritative facts
        SS->>SS: Build fact-only prompt
        SS->>LM: generate(prompt)
        LM->>Mantle: Chat completion request
        Mantle-->>LM: Generated summary
        LM-->>SS: Summary text
        SS-->>UI: Summary text
        UI-->>User: Display case summary
    end
```

## 5. Case chat with Knowledge Base citations

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant Client as AgentCore Client
    participant Runtime as AgentCore Runtime
    participant Agent as GroundedCaseAgent
    participant Repo as CaseRepository
    participant DB as DynamoDB
    participant Tools as Deterministic Tools
    participant Search as Knowledge Search Tool
    participant KB as Bedrock Knowledge Base
    participant LM as LanguageModel
    participant Mantle as Bedrock Mantle

    User->>UI: Enter case ID and question
    UI->>Client: answer(case_id, question, today, session ID)
    Client->>Runtime: InvokeAgentRuntime(payload, live qualifier)
    Runtime->>Agent: answer(case_id, question, today)

    Agent->>Repo: get(case_id)
    Repo->>DB: GetItem
    DB-->>Repo: Case item or not found
    Repo-->>Agent: Case or None

    alt Case not found
        Agent-->>UI: Answer with unavailable case evidence
        UI-->>User: Show case-not-found response
    else Case found
        Agent->>Agent: Create read-only case snapshot

        Agent->>Tools: Build timeline
        Tools-->>Agent: Ordered events
        Agent->>Tools: Find missing information
        Tools-->>Agent: Missing evidence markers
        Agent->>Tools: Calculate deadline risk
        Tools-->>Agent: Deadline result

        Agent->>Agent: Determine whether guidance is required

        alt Question requires process guidance
            Agent->>Search: search_process_knowledge(question)
            Search->>KB: Retrieve passages
            KB-->>Search: Passages, source IDs, locations
            Search-->>Agent: Knowledge results

            alt Retrieval unavailable
                Agent->>Agent: Mark process guidance unavailable
            else Retrieval successful
                Agent->>Agent: Build deduplicated citations
            end
        end

        Agent->>Agent: Build separated evidence prompt
        Agent->>LM: generate(grounded prompt)
        LM->>Mantle: Chat completion request
        Mantle-->>LM: Generated answer
        LM-->>Agent: Answer text
        Agent->>Agent: Validate factual tokens

        alt Unsupported facts detected
            Agent-->>Runtime: UngroundedRecommendationError
            Runtime-->>Client: Invocation error
            Client-->>UI: Invocation error
            UI-->>User: Show grounding error
        else Answer is grounded
            Agent-->>Runtime: Answer, citations, unavailable evidence
            Runtime-->>Client: Response JSON
            Client-->>UI: Parsed answer
            UI-->>User: Display answer and KB citations
        end
    end
```
