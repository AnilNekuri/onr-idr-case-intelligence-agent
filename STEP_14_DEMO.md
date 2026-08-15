# Step 14 End-to-End Demo

This walkthrough uses fictional organizations and contains no PHI or PII. It
demonstrates case submission, two document uploads, fact-only summarization, and
case chat with separate Knowledge Base citations.

## Before the demo

Set the development environment variables and launch Streamlit as documented in
`STEP_14_STREAMLIT.md`. Confirm the sidebar says `Case repository: dynamodb`.

The upload-ready documents are:

- `output/pdf/demo_open_negotiation_notice.pdf`
- `output/pdf/demo_itemized_bill.pdf`

Regenerate them when needed with:

```powershell
.\.venv\Scripts\python.exe scripts\generate-demo-pdfs.py
```

## 1. Submit a case

Choose **Submit a case** and enter:

| Field | Demo value |
| --- | --- |
| Case type | `IDR` |
| Case ID | `DEMO-IDR-001` |
| Provider name | `Cascadia Ambulatory Center (Synthetic)` |
| Negotiation start date | `2026-08-14` |
| Negotiation end date | `2026-08-31` |
| Missing document names | Leave blank |
| Additional notes | `Synthetic demo only. Negotiation notice prepared; awaiting provider review. Disputed amount: $4,850.00.` |

Select **Create case**. The expected confirmation shows case
`DEMO-IDR-001` with deterministic status `NEW` and one `CASE_CREATED` event.

If that ID was used in an earlier demo, use `DEMO-IDR-002` and use the same ID
in all remaining steps. The PDFs remain synthetic examples even though their
printed reference is `DEMO-IDR-001`.

## 2. Upload documents

Choose **Upload a document**. Use case ID `DEMO-IDR-001` and upload each file in
a separate submission:

1. `output/pdf/demo_open_negotiation_notice.pdf`
2. `output/pdf/demo_itemized_bill.pdf`

Each upload should return document metadata. Look up the case afterward to show
both documents and two new `DOCUMENT_RECEIVED` timeline events.

## 3. Generate the case summary

Choose **Case summary**, enter `DEMO-IDR-001`, and select **Generate summary**.
The exact wording is model-generated, but it should remain limited to these
authoritative facts:

- Case type `IDR` and status `NEW`.
- Provider `Cascadia Ambulatory Center (Synthetic)`.
- Negotiation window from August 14 through August 31, 2026.
- The two uploaded PDF filenames.
- The creation and document-received events.
- The synthetic additional notes.

It should not invent a provider response, status transition, new deadline, or
additional document.

## 4. Chat about the case

Choose **Case chat**, enter `DEMO-IDR-001`, and ask these questions in order:

1. `What is the current status of this case?`
2. `Give me the case timeline and list the uploaded documents.`
3. `Is there a deadline risk as of today?`
4. `What should the analyst do next, and what process guidance supports that action?`
5. `What evidence is unavailable for this case?`

The first three questions demonstrate authoritative case facts and deterministic
tools. The fourth is the citation showcase: it triggers process-guidance
retrieval and should display a separate **Knowledge Base citations** section.
The answer may use retrieved guidance, but must not present it as an official
case fact.

## Built-in fallback demo

If you want a richer chat without submitting a new case, use `CASE-1001` and
ask:

- `Why is this case pending?`
- `What information is missing?`
- `What should the analyst do next, and cite the process guidance?`

This case is already `PENDING_PROVIDER_RESPONSE`, includes a notice document,
and has a waiting-for-response note.
