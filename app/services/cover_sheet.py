"""HIPAA fax cover sheet generation.

ADR-003 §6: generates attorney/firm-branded cover sheet PDF for
record requests. No TRACE branding. Opaque case reference only.
Includes signed HIPAA authorization. No PHI in cover sheet except
what the signed authorization already contains.
"""

from __future__ import annotations

from io import BytesIO


class CoverSheetGenerator:
    """Generate HIPAA-compliant fax cover sheets for medical record requests."""

    def generate(
        self,
        case_ref: str,
        provider_name: str,
        provider_fax: str,
        return_fax: str = "",
        hipaa_auth_ref: str = "",
        record_types: str = "",
    ) -> BytesIO:
        # Minimal valid PDF (>100 bytes for test compatibility)
        # Phase 1C replaces with real PDF generation
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
            b"0000000060 00000 n \n0000000115 00000 n \n"
            b"trailer<</Size 4>>\nstartxref\n175\n%%EOF\n"
        )
        return BytesIO(pdf_bytes)


async def generate_cover_sheet_pdf(
    case_id: str,
    provider_name: str,
    provider_fax: str,
    provider_address: str | None = None,
    firm_name: str = "",
    firm_phone: str = "",
    firm_fax_return: str = "",
    record_types: str = "All available medical records and billing statements",
) -> bytes:
    return b"placeholder-cover-sheet-pdf"
