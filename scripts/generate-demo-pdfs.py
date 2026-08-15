"""Generate synthetic PDF documents for the Step 14 Streamlit demo."""

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
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT_DIRECTORY = Path("output/pdf")
CASE_ID = "DEMO-IDR-001"
NAVY = colors.HexColor("#183153")
BLUE = colors.HexColor("#246BCE")
PALE_BLUE = colors.HexColor("#EAF2FD")
PALE_GRAY = colors.HexColor("#F4F6F8")
DARK_GRAY = colors.HexColor("#364152")


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DemoTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "DemoSubtitle",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "heading": ParagraphStyle(
            "DemoHeading",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=BLUE,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "DemoBody",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=DARK_GRAY,
            spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "DemoSmall",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=DARK_GRAY,
        ),
    }


def _page(canvas: Any, document: SimpleDocTemplate) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D8DEE8"))
    canvas.line(0.65 * inch, 0.55 * inch, 7.85 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#637083"))
    canvas.drawString(0.65 * inch, 0.35 * inch, "Synthetic demo - no PHI or PII")
    canvas.drawRightString(
        7.85 * inch,
        0.35 * inch,
        f"{CASE_ID} | Page {document.page}",
    )
    canvas.restoreState()


def _banner(styles: dict[str, ParagraphStyle]) -> Table:
    banner = Table(
        [[Paragraph("SYNTHETIC TRAINING DOCUMENT", styles["subtitle"])]],
        colWidths=[7.2 * inch],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("BOX", (0, 0), (-1, -1), 0, NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return banner


def _details_table(
    rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]
) -> Table:
    table = Table(
        [
            [
                Paragraph(f"<b>{label}</b>", styles["small"]),
                Paragraph(value, styles["small"]),
            ]
            for label, value in rows
        ],
        colWidths=[1.75 * inch, 5.45 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), PALE_BLUE),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def build_negotiation_notice(output_path: Path) -> None:
    styles = _styles()
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.72 * inch,
        title="Synthetic Open Negotiation Notice",
        author="ONR/IDR Case Intelligence Demo",
    )
    story = [
        _banner(styles),
        Spacer(1, 0.2 * inch),
        Paragraph("Open Negotiation Notice", styles["title"]),
        Spacer(1, 0.05 * inch),
        _details_table(
            [
                ("Case reference", CASE_ID),
                ("Notice date", "August 14, 2026"),
                ("From", "Northstar Health Plan (Synthetic)"),
                ("To", "Cascadia Ambulatory Center (Synthetic)"),
                ("Negotiation window", "August 14-31, 2026"),
                ("Disputed amount", "$4,850.00"),
            ],
            styles,
        ),
        Paragraph("Purpose", styles["heading"]),
        Paragraph(
            "This synthetic notice opens negotiation for a demonstration claim. "
            "It is designed only to exercise document upload, case summary, and "
            "grounded chat workflows in the ONR/IDR Case Intelligence application.",
            styles["body"],
        ),
        Paragraph("Position summary", styles["heading"]),
        Paragraph(
            "The plan proposes the previously issued payment of $3,850.00 as the "
            "out-of-network allowed amount. The provider's synthetic billed amount "
            "is $8,700.00, leaving $4,850.00 in dispute.",
            styles["body"],
        ),
        Paragraph("Requested response", styles["heading"]),
        Paragraph(
            "Please acknowledge the notice and provide a written response or "
            "counteroffer during the recorded negotiation window. Supporting "
            "information should reference the case ID shown above.",
            styles["body"],
        ),
        Spacer(1, 0.18 * inch),
        KeepTogether(
            [
                Paragraph("Demonstration control", styles["heading"]),
                Paragraph(
                    "All organizations, amounts, and circumstances in this document "
                    "are fictional. Do not use this document for an actual claim.",
                    styles["body"],
                ),
            ]
        ),
    ]
    document.build(story, onFirstPage=_page, onLaterPages=_page)


def build_itemized_bill(output_path: Path) -> None:
    styles = _styles()
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.72 * inch,
        title="Synthetic Itemized Bill",
        author="ONR/IDR Case Intelligence Demo",
    )
    line_items = [
        ["Demo code", "Description", "Service date", "Charge"],
        ["DEMO-100", "Outpatient facility service", "2026-08-10", "$6,800.00"],
        ["DEMO-200", "Synthetic surgical supplies", "2026-08-10", "$1,250.00"],
        ["DEMO-300", "Synthetic imaging service", "2026-08-10", "$650.00"],
    ]
    charges = Table(
        line_items,
        colWidths=[1.05 * inch, 3.15 * inch, 1.35 * inch, 1.25 * inch],
        repeatRows=1,
    )
    charges.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GRAY]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    totals = Table(
        [
            ["Total billed", "$8,700.00"],
            ["Plan payment", "-$3,850.00"],
            ["Amount in dispute", "$4,850.00"],
        ],
        colWidths=[5.55 * inch, 1.25 * inch],
    )
    totals.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, 1), "Helvetica"),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 2), (-1, 2), NAVY),
                ("LINEABOVE", (0, 2), (-1, 2), 1, BLUE),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story = [
        _banner(styles),
        Spacer(1, 0.2 * inch),
        Paragraph("Itemized Bill", styles["title"]),
        Spacer(1, 0.05 * inch),
        _details_table(
            [
                ("Case reference", CASE_ID),
                ("Provider", "Cascadia Ambulatory Center (Synthetic)"),
                ("Account", "SYNTHETIC-DEMO-001"),
                ("Statement date", "August 14, 2026"),
                ("Service setting", "Synthetic outpatient facility"),
            ],
            styles,
        ),
        Paragraph("Charge detail", styles["heading"]),
        charges,
        Spacer(1, 0.08 * inch),
        totals,
        Spacer(1, 0.18 * inch),
        Paragraph("Demonstration control", styles["heading"]),
        Paragraph(
            "The codes are invented demo identifiers and are not billing codes. "
            "All organizations, amounts, and circumstances are fictional. This "
            "document contains no PHI or PII.",
            styles["body"],
        ),
    ]
    document.build(story, onFirstPage=_page, onLaterPages=_page)


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    build_negotiation_notice(OUTPUT_DIRECTORY / "demo_open_negotiation_notice.pdf")
    build_itemized_bill(OUTPUT_DIRECTORY / "demo_itemized_bill.pdf")
    print(f"Created demo PDFs in {OUTPUT_DIRECTORY.resolve()}")


if __name__ == "__main__":
    main()
