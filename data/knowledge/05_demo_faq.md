---
document_id: KB-NSA-005
title: ONR and Federal IDR Demo FAQ
topic: faq
authority: synthesized_from_official_cms_and_dol_guidance
last_reviewed: 2026-08-12
---

# ONR and Federal IDR Demo FAQ

## What is ONR in this demo?

`ONR` is the project's label for the open-negotiation stage. The official workflow uses an open negotiation notice to begin a 30-business-day open negotiation period.

## What is Federal IDR?

Federal Independent Dispute Resolution is a process in which a certified IDR entity selects one of the disputing parties' payment offers for certain qualifying out-of-network items or services after unsuccessful open negotiation.

## Who are the disputing parties?

Depending on the claim, the parties are an out-of-network provider, facility, or air ambulance provider and a plan, issuer, or Federal Employees Health Benefits carrier. The patient is not one of the payment-dispute parties in this process.

## When can open negotiation start?

Either party may start it within 30 business days beginning on the day the provider receives the initial payment or notice of denial of payment. Use deterministic date logic and the federal holiday calendar.

## How long does open negotiation last?

It lasts 30 business days beginning on the day the open negotiation notice is first sent. The parties may agree earlier, but they may not initiate Federal IDR early when no agreement is reached.

## When can Federal IDR be initiated?

Under the baseline workflow, it may be initiated within four business days after the 30-business-day open negotiation period closes. The first day is the 31st business day after open negotiation began. Exceptions, extensions, and cooling-off rules require authoritative evidence and current CMS guidance.

## What is the best next action when the EOB or QPA is missing?

Do not initiate a supposedly complete dispute. Retrieve the complete EOB or remittance and request the required QPA information from the payer. Mark the case with a deterministic missing-information blocker.

## Can the agent decide that a claim is eligible?

No. The agent can identify a potential candidate and missing eligibility facts. Formal eligibility depends on claim, plan, state-law, consent, and other facts and is determined through the applicable official process.

## What should happen when open negotiation is still active?

The recommendation should be to continue good-faith negotiation, resolve missing information, and monitor the calculated end date. The agent must not recommend early IDR initiation.

## What should happen when open negotiation ended with no agreement?

First confirm that the dispute remains a potential Federal IDR candidate, the notice and delivery evidence are complete, and the four-business-day initiation window is open. Then recommend completing the current Federal IDR portal initiation process.

## What if the parties settle after IDR begins?

They may continue negotiating until a determination. If they reach agreement, the initiating party must notify the Departments and the selected certified IDR entity, if any, as soon as possible and no later than three business days after agreement.

## What is the Federal IDR administrative fee?

CMS states that the administrative fee is $15 per party per dispute for disputes initiated on or after June 11, 2026. Certified IDR entity fees are separate. Always verify current fee guidance before operational use.

## What changed in 2026?

CMS finalized changes involving communications, open negotiation, eligibility review, batching, fees, and a future IDR Gateway. The changes have different applicability dates. CMS announced that new batching provisions apply when open negotiation begins on or after November 1, 2026; other workflow changes depend on later functionality announcements. As of this document's review date, CMS instructs parties to continue using existing Federal IDR web forms until the Gateway transition.

## What should every demo answer include?

- authoritative case facts from the case tool;
- deterministic deadline and missing-information results;
- retrieved process guidance;
- one actionable next step;
- evidence identifiers or citations; and
- a clear statement when eligibility or evidence is unresolved.

## Sources

- CMS, About Independent Dispute Resolution: https://www.cms.gov/nosurprises/help-resolve-payment-disputes/payment-disputes-between-providers-and-health-plans
- CMS, Tips for Disputing Parties: https://www.cms.gov/nosurprises/help-resolve-payment-disputes/tips-for-disputing-parties
- CMS, Notices: https://www.cms.gov/nosurprises/notices
- CMS, 2026 Federal IDR Operations Final Rule fact sheet: https://www.cms.gov/newsroom/fact-sheets/federal-independent-dispute-resolution-operations-final-rule
- CMS, Federal IDR Guidance for Disputing Parties: https://www.cms.gov/files/document/federal-idr-guidance-disputing-parties-march-2023.pdf

