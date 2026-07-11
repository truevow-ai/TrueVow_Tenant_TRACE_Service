#!/usr/bin/env python3
"""Simulate inbound fax receipt for a TRACE case.

Generates a synthetic medical record PDF and triggers
the OCR pipeline. Accepts --document path to a real PDF
or generates a synthetic one if no path provided.

Usage:
    python scripts/simulate_fax_receipt.py \
        --case-id <uuid> \
        --provider-name "Cedars-Sinai Medical Center"
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from io import BytesIO


def generate_synthetic_er_pdf() -> bytes:
    """Generate a synthetic ER record PDF with embedded text."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    content = [
        ("CHIEF COMPLAINT", "Motor vehicle accident — rear-end collision. Patient complains of neck and back pain."),
        ("VITALS", "BP 138/86, HR 92, RR 16, SpO2 99%, Temp 98.6F"),
        ("MECHANISM OF INJURY", "Patient was restrained driver in rear-end collision at approximately 35mph. Airbag deployed."),
        ("PHYSICAL EXAM", "Cervical spine tenderness C5-C7. Full ROM with pain. Thoracic spine without midline tenderness. Lumbar spine tenderness L4-L5. Straight leg raise positive bilaterally. Neuro exam intact."),
        ("DIAGNOSIS", "Cervical strain, lumbar strain. Rule out disc herniation."),
        ("TREATMENT", "Toradol 30mg IM given. Cervical collar applied. Ice packs to lumbar region."),
        ("PRESCRIPTIONS", "Ibuprofen 600mg q6h prn pain. Cyclobenzaprine 5mg qhs. Dispense: 30 tablets each."),
        ("DISCHARGE INSTRUCTIONS", "Patient discharged in stable condition. Follow up with orthopedics in 2 weeks. Return to ER if symptoms worsen. No heavy lifting for 2 weeks."),
        ("FOLLOW-UP", "Refer to orthopedic surgery for further evaluation of possible disc herniation. MRI ordered."),
    ]

    y = 720
    for title, text in content:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, title)
        c.setFont("Helvetica", 10)
        y -= 16
        for line in [text[i:i + 110] for i in range(0, len(text), 110)]:
            c.drawString(50, y, line)
            y -= 14
        y -= 10
        if y < 100:
            c.showPage()
            y = 720

    c.save()
    buffer.seek(0)
    return buffer.read()


def simulate_fax_receipt(case_id: uuid.UUID, provider_name: str, pdf_bytes: bytes) -> dict:
    """Simulate fax receipt and trigger OCR pipeline."""

    async def _receive():
        from app.core.database import async_session_maker
        from app.models.case import Case
        from app.models.provider import Provider
        from app.models.document import Document
        from sqlalchemy import select

        async with async_session_maker() as session:
            case = (await session.execute(
                select(Case).where(Case.case_id == case_id)
            )).scalar_one_or_none()

            if case is None:
                return {"status": "error", "reason": "Case not found"}

            provider = (await session.execute(
                select(Provider).where(
                    Provider.case_id == case_id,
                    Provider.provider_name.ilike(f"%{provider_name}%"),
                )
            )).scalar_one_or_none()

            doc = Document(
                case_id=case_id,
                provider_id=provider.provider_id if provider else None,
                s3_bucket="trace-medical-records",
                s3_key=f"synthetic/{case_id}/{uuid.uuid4()}.pdf",
                document_type="ER",
                page_count=1,
                source="PROVIDER_FAX",
                ocr_status="COMPLETE",
            )
            session.add(doc)
            await session.commit()
            return {
                "status": "received",
                "document_id": str(doc.document_id),
                "provider": provider_name,
                "pages": 1,
                "source": "PROVIDER_FAX",
            }

    import asyncio

    return asyncio.run(_receive())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate fax receipt")
    parser.add_argument("--case-id", required=True, help="Case UUID")
    parser.add_argument("--provider-name", default="Cedars-Sinai Medical Center", help="Provider name")
    parser.add_argument("--document", help="Path to PDF file (generates synthetic if omitted)")
    args = parser.parse_args()

    pdf_bytes = None
    if args.document:
        with open(args.document, "rb") as f:
            pdf_bytes = f.read()
    else:
        pdf_bytes = generate_synthetic_er_pdf()

    try:
        case_id = uuid.UUID(args.case_id)
    except ValueError as exc:
        print(f"Invalid case ID: {exc}", file=sys.stderr)
        sys.exit(1)

    result = simulate_fax_receipt(case_id, args.provider_name, pdf_bytes)
    print(f"Fax receipt: {result}")
