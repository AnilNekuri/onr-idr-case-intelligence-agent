---
document_id: KB-NSA-004
title: Required Information, Evidence, and Common Blockers
topic: missing_information
authority: synthesized_from_official_cms_guidance
last_reviewed: 2026-08-12
---

# Required Information, Evidence, and Common Blockers

## Core case evidence

For a demo case, track these documents and data elements separately:

- complete remittance advice, Explanation of Benefits, or notice of denial of payment;
- claim number and line-level service information;
- QPA for each disputed item or service;
- information explaining any downcoding, when applicable;
- provider or facility identity and National Provider Identifier;
- payer, plan, and plan-type identity;
- complete contact information for both parties;
- date and location of service;
- open negotiation notice and proof of transmission;
- open negotiation start and end dates;
- negotiation communications and any final agreement;
- Federal IDR initiation confirmation and dispute reference number;
- certified IDR entity communications;
- offers, supporting materials, and fee confirmations; and
- extension approval or attestation when an extension is claimed.

Do not store real PHI or PII in the demo. Use fabricated names, identifiers, claims, and documents.

## Common initiation problems identified by CMS

CMS highlights these frequent problems:

- submitting a dispute governed by a specified state law or All-Payer Model Agreement;
- incorrect batching or bundling;
- using contact information other than the contact supplied with the initial payment or denial;
- omitting the QPA;
- providing the wrong health plan type;
- missing or incorrect non-initiating-party information;
- failing to document initiation of open negotiation;
- failing to redact PHI and PII; and
- failing to respond on time to a certified IDR entity's request.

CMS also identifies complete contact details, claim numbers, a complete EOB, and QPA data as items that are frequently missing and cause delay.

## Deterministic missing-information rules

Use explicit checks before asking the model to recommend an action:

| Condition | Blocker code | Recommended next action |
|---|---|---|
| Initial payment or denial date absent | `MISSING_PAYMENT_EVENT_DATE` | Retrieve remittance or denial record. |
| Claim number absent | `MISSING_CLAIM_NUMBER` | Obtain claim identifier before notice or initiation. |
| QPA absent | `MISSING_QPA` | Request the required QPA disclosure from the payer. |
| Complete EOB/remittance absent | `MISSING_EOB` | Obtain the complete EOB or remittance with relevant codes. |
| Non-initiating contact incomplete | `MISSING_COUNTERPARTY_CONTACT` | Verify contact information from the payment or denial. |
| Open negotiation proof absent | `MISSING_ONR_EVIDENCE` | Retrieve the sent notice and transmission evidence. |
| State/process applicability unresolved | `ELIGIBILITY_UNRESOLVED` | Determine plan type, state law, and opt-in facts. |
| Open negotiation period still active | `ONR_NOT_EXHAUSTED` | Continue negotiation and monitor the calculated end date. |
| IDR window passed, no extension | `IDR_INITIATION_LATE` | Escalate for analyst review; do not invent an extension. |
| PHI/PII detected in demo material | `SENSITIVE_DATA_PRESENT` | Stop ingestion and replace with synthetic/redacted content. |
| Claimed extension lacks evidence | `EXTENSION_UNVERIFIED` | Request official approval or applicable attestation. |

## Priority order for recommendations

1. Protect data: stop if real PHI or PII is present.
2. Resolve eligibility facts.
3. Resolve missing trigger dates and deadline evidence.
4. Complete required claim and counterparty data.
5. Preserve notice and delivery evidence.
6. Monitor the next deterministic deadline.
7. Recommend portal action only when prerequisites are complete.

## Agent response pattern

Separate the response into:

- **Fact:** exact value from the case record.
- **Blocker:** deterministic missing-information result.
- **Guidance:** relevant rule retrieved from this knowledge set.
- **Recommendation:** one concrete next step.
- **Evidence:** case document IDs and knowledge document IDs.

If a fact is not in the case record, say `not available` rather than filling it from general guidance.

## Sources

- CMS, Tips for Disputing Parties: https://www.cms.gov/nosurprises/help-resolve-payment-disputes/tips-for-disputing-parties
- CMS, About Independent Dispute Resolution: https://www.cms.gov/nosurprises/help-resolve-payment-disputes/payment-disputes-between-providers-and-health-plans
- CMS, Federal IDR Guidance for Disputing Parties: https://www.cms.gov/files/document/federal-idr-guidance-disputing-parties-march-2023.pdf

