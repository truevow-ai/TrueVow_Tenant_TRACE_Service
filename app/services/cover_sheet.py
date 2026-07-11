"""HIPAA fax cover sheet generation — real implementation.

ADR-003 §3: generates attorney-branded cover sheet PDF. No TRACE branding.
Includes HIPAA authorization as page 2 when available from signed-documents
bucket. All fields that could contain PHI are on the PDF — never in logs.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


class CoverSheetGenerator:
    """Generate HIPAA-compliant fax cover sheets for medical record requests."""

    def generate(
        self,
        case_ref: str,
        provider_name: str,
        provider_fax: str,
        return_fax: str = "",
        hipaa_auth_ref: str = "",
        record_types: str = "All available medical records",
        attorney_name: str = "",
        attorney_firm: str = "",
        attorney_bar: str = "",
        attorney_phone: str = "",
        patient_name: str = "",
        patient_dob: str = "",
        incident_date: str = "",
        dates_of_service: str = "",
        hipaa_auth_pdf: bytes | None = None,
    ) -> BytesIO:
        from datetime import datetime, timezone

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        today = datetime.now(timezone.utc).strftime("%B %d, %Y")

        y = height - inch

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(inch, y, "MEDICAL RECORDS REQUEST")
        y -= 18
        c.setFont("Helvetica", 9)
        c.drawString(inch, y, f"Date: {today}")
        y -= 8
        c.line(inch, y, width - inch, y)
        y -= 20

        # FROM: Attorney
        c.setFont("Helvetica-Bold", 11)
        c.drawString(inch, y, "FROM:")
        c.setFont("Helvetica", 10)
        y -= 14
        if attorney_name:
            c.drawString(inch, y, f"Attorney: {attorney_name}")
            y -= 14
        if attorney_firm:
            c.drawString(inch, y, f"Firm: {attorney_firm}")
            y -= 14
        if attorney_bar:
            c.drawString(inch, y, f"Bar No: {attorney_bar}")
            y -= 14
        if attorney_phone:
            c.drawString(inch, y, f"Phone: {attorney_phone}")
            y -= 14
        c.drawString(inch, y, f"Return Fax: {return_fax or 'N/A'}")
        y -= 22

        # TO: Provider
        c.setFont("Helvetica-Bold", 11)
        c.drawString(inch, y, "TO:")
        c.setFont("Helvetica", 10)
        y -= 14
        c.drawString(inch, y, f"Provider: {provider_name}")
        y -= 14
        c.drawString(inch, y, f"Fax: {provider_fax}")
        y -= 22

        # RE: Case + Patient
        c.setFont("Helvetica-Bold", 11)
        c.drawString(inch, y, "RE:")
        c.setFont("Helvetica", 10)
        y -= 14
        c.drawString(inch, y, f"Reference: {case_ref}")
        y -= 14
        if patient_name:
            c.drawString(inch, y, f"Patient: {patient_name}")
            y -= 14
        if patient_dob:
            c.drawString(inch, y, f"DOB: {patient_dob}")
            y -= 14
        if incident_date:
            c.drawString(inch, y, f"Incident Date: {incident_date}")
            y -= 14
        if dates_of_service:
            c.drawString(inch, y, f"Dates of Service: {dates_of_service}")
            y -= 14
        c.drawString(inch, y, f"HIPAA Authorization: {hipaa_auth_ref or 'Signed — on file'}")
        y -= 22

        # Records requested
        c.setFont("Helvetica-Bold", 11)
        c.drawString(inch, y, "RECORDS REQUESTED:")
        c.setFont("Helvetica", 10)
        y -= 14
        c.drawString(inch, y, record_types[:100])
        y -= 30

        # HIPAA notice
        c.setFont("Helvetica-Oblique", 7)
        for line in [
            "This fax contains information protected by HIPAA and state law.",
            "It is intended only for the named recipient. If received in error,",
            "please notify the sender immediately and destroy this document.",
            "Unauthorized review or distribution is prohibited by law.",
        ]:
            c.drawString(inch, y, line)
            y -= 10

        # Footer
        c.setFont("Helvetica", 6)
        c.drawString(inch, 20, f"Generated {today} — Case {case_ref}")

        c.save()
        buffer.seek(0)

        # Append HIPAA authorization as page 2 (when available)
        if hipaa_auth_pdf:
            try:
                from pypdf import PdfReader, PdfWriter
                combined = BytesIO()
                writer = PdfWriter()
                writer.add_page(PdfReader(buffer).pages[0])
                reader = PdfReader(BytesIO(hipaa_auth_pdf))
                if reader.pages:
                    writer.add_page(reader.pages[0])
                writer.write(combined)
                combined.seek(0)
                return combined
            except ImportError:
                pass  # pypdf not installed — return cover sheet only

        return buffer
