# Step 13: Assembled Case Intelligence Agent

## Responsibility

`GroundedCaseAgent` coordinates the existing tools and the Mantle language-model
adapter. It does not implement case rules, deadline arithmetic, Knowledge Base
search, or model-provider calls itself.

## Execution order

For each valid case question, the agent executes this sequence:

1. `get_case()` reads the authoritative case once.
2. `get_case_timeline()`, `get_missing_information()`, and
   `calculate_deadline_risk()` run against that immutable case snapshot.
3. `search_process_knowledge()` runs only for explanation or operational-guidance
   questions, including the required blocker and next-step questions.
4. The agent serializes the authoritative results and retrieved guidance into
   separate prompt blocks.
5. The configured Mantle client generates one answer after retrieval finishes.
6. The response returns the generated text separately from case facts, tool
   results, retrieved passages, and citations.

The Knowledge Base integration uses its existing retrieval-only contract. The
agent never calls `RetrieveAndGenerate`.

## Inspectable response

`GroundedCaseAnswer.model_dump()` includes:

- `authoritative_facts`;
- `timeline`;
- `deterministic_deadline`;
- `unavailable_evidence`;
- `process_guidance`, including every retrieved passage and score;
- `citations`, containing each source ID and document location;
- `generated_answer`;
- `tool_results`, keyed by the five Step 13 tool names.

Missing cases do not call Mantle. When process guidance is required but no
retriever is configured, no results are returned, or retrieval fails, the agent
records `process_guidance` as unavailable and generates from the authoritative
case evidence without guessing the missing guidance.

## Runtime assembly

Use `create_grounded_case_agent(settings)` to connect:

- the configured JSON or DynamoDB case repository;
- the Amazon Bedrock Managed Knowledge Base retriever;
- the Amazon Bedrock Mantle language-model client.

The factory requires both `BEDROCK_KNOWLEDGE_BASE_ID` and `BEDROCK_MODEL_ID`.

Run one real configured question from PowerShell with:

```powershell
.\scripts\run-grounded-agent.ps1 `
  -ModelId "your-mantle-model-id" `
  -KnowledgeBaseId "ABCDEFGHIJ" `
  -CaseId "CASE-1001" `
  -Question "What should happen next?"
```

Replace the example Knowledge Base value with its actual 10-character ID. The
launcher sets the JSON repository path, AWS region, AWS profile, model ID, and
Knowledge Base ID for the Python process, then restores the previous environment.
Use `-Profile` or `-Region` to override their defaults. This command invokes AWS
services and can incur charges.

## Verification

Run the Step 13 unit and grounding evaluations:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_grounded_case_agent.py `
  tests\unit\test_agent_factory.py `
  tests\evaluation\test_grounding.py -vv
```

The unit tests ask these questions individually:

1. `What is the case status?`
2. `What information is missing?`
3. `Is the deadline at risk?`
4. `Why is the case blocked?`
5. `What should happen next?`

Only questions 4 and 5 retrieve process guidance. Every required retrieval is
recorded before the model-generation event.
