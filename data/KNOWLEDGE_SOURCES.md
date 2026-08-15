# ONR/IDR Demo Knowledge Set

This folder contains five short, retrieval-friendly documents derived from public U.S. government materials about the No Surprises Act open negotiation and Federal Independent Dispute Resolution (IDR) process.

## Intended use

- Demo and training only.
- Use only synthetic case facts. Do not upload PHI or PII.
- Treat the case store as authoritative for case dates, status, documents, and events.
- Treat these documents as general process guidance, not legal advice or an eligibility determination.
- Recheck official CMS notices before operational use because forms, fees, extensions, and phased 2026 rule changes can change.

In this project, `ONR` is a local case-type label for the open-negotiation stage. Official CMS and Department of Labor materials generally use the terms **open negotiation notice** and **open negotiation period**; they do not consistently use `ONR` as an official acronym.

## Files to ingest

Upload only the Markdown files under `data/knowledge/` to the Bedrock Knowledge Base source:

1. `01_scope_and_eligibility.md`
2. `02_open_negotiation_workflow.md`
3. `03_federal_idr_workflow.md`
4. `04_required_information_and_blockers.md`
5. `05_demo_faq.md`

The files intentionally repeat a few high-value rules so a short retrieval result can still answer common demo questions.

`data/knowledge_demo_questions.json` contains the same demo prompts in a machine-readable retrieval-evaluation format, with expected document IDs and concepts.

## Easy demo questions

1. What kinds of claims may qualify for Federal IDR?
2. Does Medicare use this Federal IDR process?
3. When must open negotiation be started?
4. Can IDR start before the 30-business-day negotiation period ends?
5. What information belongs in an open negotiation notice?
6. What commonly causes an IDR initiation to be delayed or rejected?
7. What should the analyst do if the EOB or QPA is missing?
8. How long does a party have to initiate IDR after negotiation ends?
9. What is the current Federal IDR administrative fee?
10. Which 2026 changes should the agent avoid applying prematurely?

## Expected grounding behavior

A good answer should:

- cite one or more knowledge documents;
- distinguish an authoritative case fact from general process guidance;
- avoid calculating business-day deadlines in the language model;
- state `needs eligibility review` when state law, plan type, consent, coverage, or claim details are unresolved;
- never declare a dispute legally eligible based only on the knowledge base;
- mention that the CMS Notices page should be checked for current extensions and phased changes.

## Public sources reviewed

Last reviewed: **2026-08-12**

- CMS, About Independent Dispute Resolution: https://www.cms.gov/nosurprises/help-resolve-payment-disputes/payment-disputes-between-providers-and-health-plans
- CMS, Tips for Disputing Parties: https://www.cms.gov/nosurprises/help-resolve-payment-disputes/tips-for-disputing-parties
- CMS, Notices: https://www.cms.gov/nosurprises/notices
- CMS, Federal IDR Guidance for Disputing Parties (December 2023 update): https://www.cms.gov/files/document/federal-idr-guidance-disputing-parties-march-2023.pdf
- CMS, IDR Timeline for Claims: https://www.cms.gov/files/document/independent-dispute-resolution-idr-timeline-claims.pdf
- CMS, Chart for Determining Applicability of the Federal IDR Process: https://www.cms.gov/files/document/caa-federal-idr-applicability-chart.pdf
- CMS, 2026 Federal IDR Operations Final Rule fact sheet: https://www.cms.gov/newsroom/fact-sheets/federal-independent-dispute-resolution-operations-final-rule
- U.S. Department of Labor, Open Negotiation Notice: https://www.dol.gov/agencies/ebsa/laws-and-regulations/laws/no-surprises-act/surprise-billing-part-ii-information-collection-documents-attachment-2
