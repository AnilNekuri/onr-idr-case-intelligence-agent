---
document_id: KB-NSA-001
title: Federal IDR Scope and Eligibility Triage
topic: eligibility
authority: synthesized_from_official_cms_guidance
last_reviewed: 2026-08-12
---

# Federal IDR Scope and Eligibility Triage

## Use this document for

Use this guidance when a user asks whether a claim might belong in the No Surprises Act Federal Independent Dispute Resolution (IDR) process. This is a triage aid, not a legal eligibility determination.

## What the process resolves

Federal IDR resolves certain payment-rate disputes between an out-of-network provider, facility, or air ambulance provider and a health plan, issuer, or Federal Employees Health Benefits carrier. It does not resolve a patient's dispute with a provider, and it is not the ordinary plan claims-and-appeals process.

## Claims that may be candidates

A claim may be a Federal IDR candidate when it concerns one of these categories:

- emergency services, including certain post-stabilization services;
- certain non-emergency services furnished by an out-of-network provider during a patient visit to an in-network facility; or
- air ambulance services furnished by an out-of-network air ambulance provider.

The parties must first complete the required 30-business-day open negotiation period without reaching an agreement.

## Situations that are not Federal IDR candidates

Do not label a dispute as a Federal IDR candidate when the available facts establish that:

- the item or service is payable by Medicare, Medicaid, the Children's Health Insurance Program, or TRICARE;
- an applicable specified state law or All-Payer Model Agreement determines the out-of-network payment amount;
- the issue is a denial of coverage or adverse benefit determination that belongs in the plan's claims-and-appeals process;
- the dispute is between an uninsured or self-pay patient and a provider; or
- valid notice and consent removed the item or service from the applicable surprise-billing protections.

Some self-insured plans can opt into a state process. Plan type, state, and opt-in facts therefore matter.

## Minimum eligibility facts

Before recommending IDR initiation, retrieve or request:

- service category;
- date and location of service, including state or territory;
- provider network status;
- facility network status when relevant;
- plan type and payer identity;
- whether a specified state law or All-Payer Model Agreement applies;
- whether valid notice and consent was obtained, when relevant;
- whether the dispute is about payment amount rather than coverage;
- initial payment or notice-of-denial date; and
- open negotiation start and end dates.

## Deterministic triage outcomes

Return one of these labels:

- `FEDERAL_IDR_CANDIDATE`: all minimum facts are present, the service category is potentially covered, no state or federal-program exclusion is identified, and open negotiation ended without agreement.
- `NOT_FEDERAL_IDR`: an exclusion is established by authoritative case facts.
- `NEEDS_ELIGIBILITY_REVIEW`: any material eligibility fact is absent or conflicting.

Never change `NEEDS_ELIGIBILITY_REVIEW` to `FEDERAL_IDR_CANDIDATE` by guessing.

## Recommended agent wording

Say: "The case facts make this a potential Federal IDR candidate, subject to formal eligibility review."

Do not say: "This claim is legally eligible" unless an authoritative eligibility result exists in the case record.

## Sources

- CMS, About Independent Dispute Resolution: https://www.cms.gov/nosurprises/help-resolve-payment-disputes/payment-disputes-between-providers-and-health-plans
- CMS, Federal IDR Guidance for Disputing Parties, sections 1.2-1.4 and 3.1: https://www.cms.gov/files/document/federal-idr-guidance-disputing-parties-march-2023.pdf
- CMS, Chart for Determining Applicability of the Federal IDR Process: https://www.cms.gov/files/document/caa-federal-idr-applicability-chart.pdf

