# Grounding Evaluations

Step 11 adds a deterministic grounding boundary and a small evaluation suite.
It does not call AWS or a real language model.

## Response trust boundary

`GroundedCaseAgent.answer()` performs work in this order:

1. Retrieve the case through the storage-independent `CaseRepository` protocol.
2. Calculate missing evidence and deadline risk from that retrieved case.
3. Build a delimited evidence prompt.
4. Ask the configured model for recommendation text only.
5. Reject recognizable dates, document names, status values, or event types that
   are not present in the authoritative case.
6. Return an object with four explicitly separated sections:
   `authoritative_facts`, `deterministic_deadline`, `unavailable_evidence`, and
   `non_authoritative_recommendation`.

If the case does not exist, the agent reports `case:<case-id>` as unavailable
evidence and does not call the model.

## Evaluation dataset

[`data/evaluations/grounding_cases.json`](data/evaluations/grounding_cases.json)
contains one entry for every case in `data/cases.json`. Each entry records:

- expected dates, documents, events, and status;
- expected missing-evidence markers;
- the exact deadline, days remaining, and deterministic risk for 2026-08-10.

The coverage test fails if a synthetic case is added without a matching
evaluation entry, if an evaluation is duplicated, or if an expected fact drifts
from the authoritative source fixture.

## Run the grounding evaluations

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\evaluation\test_grounding.py -vv
```

Run every local test afterward:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

These local tests verify orchestration and deterministic safeguards. Real-model
quality remains an opt-in integration/evaluation concern because model calls are
paid and nondeterministic.
