# ONR / IDR PDF extraction

The **Extract ONR / IDR PDF** Streamlit workflow implements this chain:

```text
PDF -> private S3 object -> Textract -> normalized OCR -> Bedrock Mantle
    -> JSON validation/retry -> Pydantic -> evidence + review warnings
```

Textract reads the document; Bedrock Mantle maps document labels to a stable
semantic schema included in the prompt; Pydantic rejects malformed output. The
workflow retries an invalid model response up to three times and then fails
safely. It does not validate a claim, decide No Surprises Act eligibility, or
calculate legal deadlines.

## Configure

Use an S3 bucket in the same AWS Region as Textract and a model listed in your
Bedrock Mantle catalog.

```powershell
$env:AWS_REGION = "us-east-1"
$env:AWS_PROFILE = "your-development-profile" # optional
$env:S3_CASE_DOCUMENTS_BUCKET = "your-private-document-bucket"
$env:BEDROCK_EXTRACTION_API = "mantle"
$env:BEDROCK_MODEL_ID = "anthropic.claude-haiku-4-5"
# Optional when extraction should use a different Mantle model:
# $env:BEDROCK_EXTRACTION_MODEL_ID = "another-mantle-model-id"

streamlit run streamlit_app.py
```

Mantle is the default extraction API. `BEDROCK_EXTRACTION_MODEL_ID` falls back to
`BEDROCK_MODEL_ID` in Mantle mode. Mantle does not enforce a structured-output
grammar, so the application supplies the full JSON schema in the prompt,
requires JSON-only output, validates every required property, and retries
invalid output. Fields without direct Textract evidence are still flagged.

The former strict Runtime path remains available with
`BEDROCK_EXTRACTION_API=runtime`. Runtime mode requires an explicit Runtime model
ID in `BEDROCK_EXTRACTION_MODEL_ID`; it does not accept a Mantle model ID.

The AWS identity running Streamlit needs, at minimum, permissions equivalent to:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET/temporary/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "textract:StartDocumentAnalysis",
        "textract:GetDocumentAnalysis"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-mantle:CreateInference",
        "bedrock-mantle:GetProject",
        "bedrock-mantle:ListProjects",
        "bedrock-mantle:ListTagsForResources"
      ],
      "Resource": "*"
    }
  ]
}
```

Keep the bucket private and encrypted. Temporary extraction objects use opaque
IDs rather than claim, member, provider, or patient identifiers. Add a bucket
lifecycle rule if those objects should expire automatically.

## Uniform output contract

ONR and IDR documents return the same field set. Non-applicable or absent scalar
values are `null`; absent CPT/HCPCS codes are `[]`. Type-specific fields include:

| ONR | IDR |
| --- | --- |
| `notice_date` | `federal_idr_reference` |
| `requested_amount` | `idr_initiation_date` |
| negotiation start/end | `payer_offer` and `negotiation_outcome` |

The shared fields include claim identifiers, member ID, provider identifiers,
date of service, CPT/HCPCS, billed amount, initial payment, QPA, requested amount,
initiating party, and extraction summary.

Every supported value is matched back to a Textract key/value or line when
possible. `field_evidence` retains the page, OCR confidence, and raw supporting
text. Unsupported LLM values and ONR/IDR classifier disagreements become review
warnings rather than silently accepted results.

## Test without AWS

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
python -m ruff check app tests
python -m mypy app
```

The unit tests use synthetic Textract and Bedrock responses. Live AWS calls are
not part of the default test run, so verification does not create cloud cost.

The included `demo/synthetic_onr_case_001.pdf` and
`demo/synthetic_idr_case_001.pdf` contain only synthetic demo data.
