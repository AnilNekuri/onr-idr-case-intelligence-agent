---
document_id: KB-NSA-002
title: Open Negotiation Notice and Workflow
topic: open_negotiation
authority: synthesized_from_official_cms_and_dol_guidance
last_reviewed: 2026-08-12
---

# Open Negotiation Notice and Workflow

## Terminology

This demo uses `ONR` as a local label for a case in the open-negotiation stage. Official materials generally call the initiating document the **open negotiation notice** and the workflow the **open negotiation period**.

## Purpose

Open negotiation gives the disputing parties an opportunity to agree on an out-of-network payment rate before paying the fees and completing the formal Federal IDR process.

## Baseline operational timeline

1. A plan sends an initial payment or notice of denial of payment for a potentially qualified item or service.
2. Either party may initiate open negotiation within 30 business days beginning on the day the provider receives the initial payment or notice of denial.
3. The initiating party sends the required written open negotiation notice to the other party.
4. The 30-business-day open negotiation period begins on the day the notice is first sent.
5. The parties may settle early, but if they do not settle, they must allow the entire 30-business-day period to run before initiating Federal IDR.
6. Continuing to negotiate after day 30 does not pause or extend the separate four-business-day IDR initiation window.

Business days are Monday through Friday excluding federal holidays. Deadline dates must be calculated by deterministic application code, not by the language model.

## Open negotiation notice checklist

The written notice should contain enough information to identify the dispute, including:

- description of each item or service;
- claim number;
- provider or facility name and National Provider Identifier;
- date each item or service was furnished;
- service code;
- initial payment amount or notice of denial of payment;
- initiating party's offer for the total out-of-network rate, including cost sharing; and
- initiating party contact information.

Use the current standard government notice. Confirm the other party's correct contact information and preserve evidence that the notice was sent and received, such as the sent notice, email metadata, delivery confirmation, or read receipt.

## Suggested case statuses

- `ONR_NOT_STARTED`: initial payment or denial exists, but no valid notice is recorded.
- `ONR_INCOMPLETE`: a notice exists but required fields or delivery evidence are missing.
- `ONR_ACTIVE`: a complete notice was sent and the 30-business-day period has not ended.
- `ONR_SETTLED`: the parties agreed on the out-of-network rate.
- `ONR_COMPLETE_NO_AGREEMENT`: the full period ended without agreement; assess the IDR initiation window.
- `ONR_DEADLINE_MISSED`: deterministic calculation shows the initiation deadline passed and no approved extension is recorded.

## Common blockers and next actions

- Missing initial payment or denial date: retrieve the remittance or denial before calculating a deadline.
- Missing claim, service, or provider identifiers: complete the notice before treating open negotiation as valid.
- Unverified recipient contact: verify the contact supplied with the initial payment or denial.
- No delivery evidence: preserve or request proof of transmission and receipt.
- Open negotiation still active: continue negotiation and monitor the deterministic end date; do not initiate IDR early.
- Extension claimed but not documented: mark `EXTENSION_UNVERIFIED` and request the official approval or applicable attestation.

## 2026 transition guardrail

The 2026 final rule includes future portal-based submission and an open negotiation response notice. Most of those workflow changes apply only after the Departments announce that supporting functionality is available and the specified transition period runs. As of the review date, do not invent or enforce a response-notice deadline unless current CMS guidance and the portal show that the provision applies to the dispute. Check the CMS Notices page before giving operational guidance.

## Sources

- CMS, Federal IDR Guidance for Disputing Parties, sections 3.1-3.2: https://www.cms.gov/files/document/federal-idr-guidance-disputing-parties-march-2023.pdf
- U.S. Department of Labor, Open Negotiation Notice: https://www.dol.gov/agencies/ebsa/laws-and-regulations/laws/no-surprises-act/surprise-billing-part-ii-information-collection-documents-attachment-2
- CMS, 2026 Federal IDR Operations Final Rule fact sheet: https://www.cms.gov/newsroom/fact-sheets/federal-independent-dispute-resolution-operations-final-rule
- CMS, Notices: https://www.cms.gov/nosurprises/notices

