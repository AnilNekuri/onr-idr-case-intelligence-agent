"""Generate synthetic ONR and IDR PDFs for document-extraction demos."""

from pathlib import Path
from typing import Any

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_CENTER  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.lib.styles import (  # type: ignore[import-untyped]
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import inch  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT_DIRECTORY = Path("demo")

NAVY = colors.HexColor("#15324B")
BLUE = colors.HexColor("#1D6FA5")
TEAL = colors.HexColor("#0C7C86")
PALE_BLUE = colors.HexColor("#EAF4FA")
PALE_TEAL = colors.HexColor("#E9F7F5")
PALE_GRAY = colors.HexColor("#F5F7F9")
MID_GRAY = colors.HexColor("#667786")
DARK_GRAY = colors.HexColor("#263845")
BORDER = colors.HexColor("#C8D5DE")


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "banner": ParagraphStyle(
            "DemoBanner",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "title": ParagraphStyle(
            "DemoTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "DemoSubtitle",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=MID_GRAY,
            alignment=TA_CENTER,
        ),
        "heading": ParagraphStyle(
            "DemoHeading",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=BLUE,
            spaceBefore=10,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "DemoBody",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=DARK_GRAY,
            spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "DemoSmall",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=DARK_GRAY,
        ),
        "small_bold": ParagraphStyle(
            "DemoSmallBold",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=DARK_GRAY,
        ),
        "callout": ParagraphStyle(
            "DemoCallout",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=NAVY,
        ),
    }


def _page_footer(canvas: Any, document: SimpleDocTemplate) -> None:
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.line(0.65 * inch, 0.55 * inch, 7.85 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MID_GRAY)
    canvas.drawString(0.65 * inch, 0.35 * inch, "SYNTHETIC DEMO - NO PHI OR PII")
    canvas.drawRightString(
        7.85 * inch,
        0.35 * inch,
        f"ONR/IDR Case Intelligence Demo | Page {document.page}",
    )
    canvas.restoreState()


def _banner(styles: dict[str, ParagraphStyle], label: str) -> Table:
    table = Table(
        [[Paragraph(label, styles["banner"])]],
        colWidths=[7.2 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _field_table(
    rows: list[tuple[str, str]],
    styles: dict[str, ParagraphStyle],
    *,
    tint: colors.Color = PALE_BLUE,
) -> Table:
    table = Table(
        [
            [
                Paragraph(label, styles["small_bold"]),
                Paragraph(value or " ", styles["small"]),
            ]
            for label, value in rows
        ],
        colWidths=[2.35 * inch, 4.85 * inch],
        repeatRows=0,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), tint),
                ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, PALE_GRAY]),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _amount_table(
    rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]
) -> Table:
    table = Table(
        [
            [
                Paragraph(label, styles["small_bold"]),
                Paragraph(value, styles["small"]),
            ]
            for label, value in rows
        ],
        colWidths=[5.35 * inch, 1.85 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, PALE_GRAY]),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _document(
    output_path: Path, title: str, subject: str
) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.72 * inch,
        title=title,
        author="ONR/IDR Case Intelligence Demo",
        subject=subject,
        creator="Synthetic document generator",
    )


def build_onr(output_path: Path) -> None:
    styles = _styles()
    document = _document(
        output_path,
        "Synthetic Open Negotiation Notice",
        "Synthetic ONR document for OCR and structured-data extraction demos",
    )
    story = [
        _banner(styles, "SYNTHETIC TRAINING DOCUMENT - OPEN NEGOTIATION"),
        Spacer(1, 0.18 * inch),
        Paragraph("Open Negotiation Notice", styles["title"]),
        Paragraph(
            "Federal No Surprises Act - demo document only",
            styles["subtitle"],
        ),
        Paragraph("Document Information", styles["heading"]),
        _field_table(
            [
                ("Document Type", "ONR"),
                ("Source File Name", "synthetic_onr_case_001.pdf"),
                ("Notice Date", "07/15/2026"),
                ("Initiating Party", "PROVIDER"),
            ],
            styles,
        ),
        Paragraph("Claim Information", styles["heading"]),
        _field_table(
            [
                ("Claim Number", "CLM-987654321"),
                ("Provider Claim Number", "PCN-2026-44107"),
                ("Member ID", "SYN-MBR-1001"),
                ("Date of Service", "07/10/2026"),
                ("CPT/HCPCS", "99285"),
            ],
            styles,
        ),
        Paragraph("Provider Information", styles["heading"]),
        _field_table(
            [
                ("Provider Name", "Synthetic Emergency Physicians"),
                ("Provider NPI", "1234567890"),
                ("Provider TIN", "91-7654321"),
            ],
            styles,
            tint=PALE_TEAL,
        ),
        PageBreak(),
        _banner(styles, "SYNTHETIC TRAINING DOCUMENT - OPEN NEGOTIATION"),
        Spacer(1, 0.16 * inch),
        Paragraph("Financial and Negotiation Details", styles["title"]),
        Paragraph("Claim CLM-987654321", styles["subtitle"]),
        Paragraph("Financial Information", styles["heading"]),
        _amount_table(
            [
                ("Billed Amount", "$8,500.00"),
                ("Initial Payment", "$2,100.00"),
                ("Qualifying Payment Amount (QPA)", "$1,950.00"),
                ("Requested Amount", "$6,000.00"),
            ],
            styles,
        ),
        Paragraph("Open Negotiation Period", styles["heading"]),
        _field_table(
            [
                ("Open Negotiation Start Date", "07/15/2026"),
                ("Open Negotiation End Date", "08/13/2026"),
                ("Federal IDR Reference", ""),
            ],
            styles,
        ),
        Paragraph("Notice Statement", styles["heading"]),
        Paragraph(
            "Synthetic Emergency Physicians initiates open negotiation concerning "
            "the out-of-network payment for the emergency service identified above. "
            "The provider requests a total payment of $6,000.00 and asks the plan to "
            "review the service complexity and the submitted documentation.",
            styles["body"],
        ),
        Spacer(1, 0.08 * inch),
        Table(
            [[Paragraph(
                "DEMONSTRATION CONTROL: All names, identifiers, dates, amounts, and "
                "circumstances are fictional. This document contains no PHI or PII "
                "and must not be used for an actual claim.",
                styles["callout"],
            )]],
            colWidths=[7.2 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PALE_TEAL),
                    ("BOX", (0, 0), (-1, -1), 0.75, TEAL),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            ),
        ),
    ]
    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)


def build_idr(output_path: Path) -> None:
    styles = _styles()
    document = _document(
        output_path,
        "Synthetic Federal Independent Dispute Resolution Notice",
        "Synthetic IDR document for OCR and structured-data extraction demos",
    )
    story = [
        _banner(styles, "SYNTHETIC TRAINING DOCUMENT - FEDERAL IDR"),
        Spacer(1, 0.18 * inch),
        Paragraph("Federal Independent Dispute Resolution", styles["title"]),
        Paragraph("Initiation notice - demo document only", styles["subtitle"]),
        Paragraph("Document Information", styles["heading"]),
        _field_table(
            [
                ("Document Type", "IDR"),
                ("Source File Name", "synthetic_idr_case_001.pdf"),
                ("Federal IDR Reference", "IDR-DEMO-782456"),
                ("IDR Initiation Date", "08/14/2026"),
                ("Initiating Party", "PROVIDER"),
            ],
            styles,
        ),
        Paragraph("Claim Information", styles["heading"]),
        _field_table(
            [
                ("Claim Number", "CLM-987654321"),
                ("Provider Claim Number", "PCN-2026-44107"),
                ("Member ID", "SYN-MBR-1001"),
                ("Date of Service", "07/10/2026"),
                ("CPT/HCPCS", "99285"),
            ],
            styles,
        ),
        Paragraph("Provider Information", styles["heading"]),
        _field_table(
            [
                ("Provider Name", "Synthetic Emergency Physicians"),
                ("Provider NPI", "1234567890"),
                ("Provider TIN", "91-7654321"),
            ],
            styles,
            tint=PALE_TEAL,
        ),
        PageBreak(),
        _banner(styles, "SYNTHETIC TRAINING DOCUMENT - FEDERAL IDR"),
        Spacer(1, 0.16 * inch),
        Paragraph("Offers and Negotiation History", styles["title"]),
        Paragraph("Federal IDR Reference IDR-DEMO-782456", styles["subtitle"]),
        Paragraph("Financial Information", styles["heading"]),
        _amount_table(
            [
                ("Billed Amount", "$8,500.00"),
                ("Initial Payment", "$2,100.00"),
                ("Qualifying Payment Amount (QPA)", "$1,950.00"),
                ("Provider Offer / Requested Amount", "$5,200.00"),
                ("Payer Offer", "$3,000.00"),
            ],
            styles,
        ),
        Paragraph("Open Negotiation History", styles["heading"]),
        _field_table(
            [
                ("Open Negotiation Start Date", "07/15/2026"),
                ("Open Negotiation End Date", "08/13/2026"),
                ("Negotiation Outcome", "No agreement reached"),
            ],
            styles,
        ),
        Paragraph("Initiation Statement", styles["heading"]),
        Paragraph(
            "The provider initiates the Federal IDR process for the service and "
            "claim identified in this notice. The provider submits an offer of "
            "$5,200.00. The payer offer is $3,000.00. This synthetic notice records "
            "the parties' demo positions and does not determine claim validity, "
            "legal eligibility, or payment responsibility.",
            styles["body"],
        ),
        Spacer(1, 0.08 * inch),
        Table(
            [[Paragraph(
                "DEMONSTRATION CONTROL: All names, identifiers, dates, amounts, and "
                "circumstances are fictional. This document contains no PHI or PII "
                "and must not be used for an actual dispute.",
                styles["callout"],
            )]],
            colWidths=[7.2 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PALE_TEAL),
                    ("BOX", (0, 0), (-1, -1), 0.75, TEAL),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            ),
        ),
    ]
    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    build_onr(OUTPUT_DIRECTORY / "synthetic_onr_case_001.pdf")
    build_idr(OUTPUT_DIRECTORY / "synthetic_idr_case_001.pdf")
    print(f"Created synthetic ONR and IDR PDFs in {OUTPUT_DIRECTORY.resolve()}")


if __name__ == "__main__":
    main()
