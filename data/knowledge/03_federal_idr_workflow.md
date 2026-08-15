---
document_id: KB-NSA-003
title: Federal IDR Initiation and Workflow
topic: idr_workflow
authority: synthesized_from_official_cms_guidance
last_reviewed: 2026-08-12
---

# Federal IDR Initiation and Workflow

## Entry condition

Federal IDR may be initiated only after the required 30-business-day open negotiation period ends without an agreed payment amount and the dispute is a potential Federal IDR candidate.

## Initiation window

Under the baseline workflow, either party may initiate Federal IDR during the four-business-day period beginning on the 31st business day after open negotiation began. Initiation requires notice to the other party and submission through the Federal IDR portal. The portal receipt date is the Federal IDR initiation date.

Do not use the language model to calculate this window. Store the open negotiation start date and use a deterministic business-calendar function.

## Information needed to initiate

The initiation submission generally needs:

- initiating party type;
- complete contact information for both parties;
- description and type of each qualified item or service;
- date and location of service, including state or territory;
- claim number, service code, and place-of-service code;
- whether items are submitted as a batch or bundle;
- QPA, allowed cost sharing, and initial payment amount when applicable;
- plan or issuer identity and plan type;
- provider or facility name, National Provider Identifier, and contact information;
- open negotiation start date;
- initial payment or denial date;
- preferred certified IDR entity;
- attestation that the items or services are within Federal IDR scope; and
- required general process information for the non-initiating party.

Use the current Federal IDR portal and form instructions rather than creating a substitute form.

## Baseline milestones after initiation

- Certified IDR entity selection: parties generally have three business days after initiation to agree. If they do not agree, the Departments select an entity under the applicable process.
- Offers and fees: under the baseline guidance, each party submits its offer and required fees no later than 10 business days after final entity selection.
- Payment determination: under the baseline guidance, the certified IDR entity selects one of the parties' offers and provides its decision within 30 business days after final entity selection.
- Payment after determination: an amount owed must be paid within 30 calendar days after determination.

Portal notices and certified IDR entity communications are authoritative for case-specific due dates. If they conflict with a locally calculated date, flag the conflict for analyst review rather than silently choosing one.

## Settlement after IDR begins

The parties may continue negotiating until the certified IDR entity makes a determination. If they settle, the initiating party must notify the Departments and the selected certified IDR entity, if any, as soon as possible and no later than three business days after the agreement. The settlement record should include the agreed out-of-network rate and authorized signatures.

## Fees and current notices

For disputes initiated on or after June 11, 2026, CMS states that the Federal IDR administrative fee is $15 per party per dispute. Certified IDR entity fees are separate. Never hard-code a fee into a permanent business rule; retrieve it from current official guidance.

CMS announced that batching provisions under the 2026 final rule will apply to disputes whose open negotiation periods begin on or after November 1, 2026. Those provisions include a maximum of 50 line items in a batch and a 30-business-day cooling-off period for the described subsequent disputes. Apply the correct rule version based on the open negotiation start date.

Other 2026 workflow changes are phased and depend on CMS announcing supporting functionality. Until CMS says otherwise, continue to follow current web forms and portal instructions.

## Suggested case statuses

- `IDR_WINDOW_NOT_OPEN`
- `IDR_READY_TO_INITIATE`
- `IDR_INITIATED`
- `IDR_ENTITY_SELECTION`
- `IDR_OFFER_DUE`
- `IDR_DETERMINATION_PENDING`
- `IDR_SETTLED`
- `IDR_DETERMINED`
- `IDR_PAYMENT_DUE`
- `IDR_CLOSED`
- `IDR_DEADLINE_MISSED`
- `NEEDS_ELIGIBILITY_REVIEW`

## Sources

- CMS, About Independent Dispute Resolution: https://www.cms.gov/nosurprises/help-resolve-payment-disputes/payment-disputes-between-providers-and-health-plans
- CMS, Federal IDR Guidance for Disputing Parties, sections 4-8: https://www.cms.gov/files/document/federal-idr-guidance-disputing-parties-march-2023.pdf
- CMS, IDR Timeline for Claims: https://www.cms.gov/files/document/independent-dispute-resolution-idr-timeline-claims.pdf
- CMS, Notices: https://www.cms.gov/nosurprises/notices
- CMS, 2026 Federal IDR Operations Final Rule fact sheet: https://www.cms.gov/newsroom/fact-sheets/federal-independent-dispute-resolution-operations-final-rule

