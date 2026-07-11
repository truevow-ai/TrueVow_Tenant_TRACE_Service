"""OCR Pipeline — tiered text extraction + de-identification.

Tier 0 : pypdf        — embedded text layer (no OCR needed)
Tier 1B: Mistral OCR 4 — self-hosted Fly.io sidecar, or API key in dev
Tier 1B: Tesseract     — local fallback when Mistral is unavailable
Tier 2 : Mistral OCR   — cloud, only when Tier 1B confidence < 80%
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from io import BytesIO

from app.core.logging import get_logger

logger = get_logger("trace.ocr")

OCR_THRESHOLDS: dict[tuple[str, str], float] = {
    ("typed", "en"): 0.90,
    ("handwritten", "en"): 0.70,
    ("typed", "es"): 0.85,
    ("handwritten", "es"): 0.65,
}


class OcrUnavailableError(Exception):
    def __init__(self, document_id: uuid.UUID) -> None:
        super().__init__(
            f"OCR processing unavailable for document {document_id}. "
            f"This document requires an OCR engine for image-based PDF processing. "
            f"Contact support@truevow.law"
        )


@dataclass
class OCRPageResult:
    page_number: int
    raw_text: str = ""
    redacted_text: str = ""
    confidence: float = 0.0
    is_handwritten: bool = False
    backend: str = "none"
    layout_json: dict | None = None
    quality_flags: list[str] = field(default_factory=list)
    needs_escalation: bool = False
    ocr_unavailable: bool = False


@dataclass
class OCRDocumentResult:
    document_id: uuid.UUID
    pages: list[OCRPageResult] = field(default_factory=list)
    document_type_guess: str = "UNKNOWN"
    ocr_route: str = "MISTRAL_OCR"
    method: str = "none"
    needs_ocr: bool = True

    @property
    def mean_confidence(self) -> float:
        if not self.pages:
            return 0.0
        return sum(p.confidence for p in self.pages) / len(self.pages)

    @property
    def pages_needing_escalation(self) -> list[OCRPageResult]:
        return [p for p in self.pages if p.needs_escalation]


def get_escalation_threshold(document_type: str, language: str) -> float:
    return OCR_THRESHOLDS.get((document_type, language), 0.80)


def _extract_embedded_text(pdf_bytes: bytes) -> tuple[str, bool]:
    """TIER 0 — extract text from digital PDFs that already have a text layer."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(pdf_bytes))
        text_parts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
        combined = "\n".join(text_parts)
        return combined, len(combined.strip()) > 50
    except Exception:
        return "", False


def _rasterize_pdf(pdf_bytes: bytes) -> list:
    """Rasterize PDF pages to image arrays for OCR."""
    import fitz  # PyMuPDF
    import numpy as np

    images: list = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            images.append(img)
    finally:
        doc.close()
    return images


def _run_mistral_ocr(image) -> tuple[str, float]:
    """Run Mistral OCR 4 on a single page image. Returns (text, confidence)."""
    try:
        import base64

        from mistralai import Mistral

        api_key = os.environ.get("MISTRAL_API_KEY", "")
        server_url = os.environ.get("MISTRAL_OCR_URL", "")

        if server_url:
            client = Mistral(server_url=server_url)
        elif api_key:
            client = Mistral(api_key=api_key)
        else:
            raise OcrUnavailableError(uuid.uuid4())

        import numpy as np
        from PIL import Image

        if isinstance(image, np.ndarray):
            img = Image.fromarray(image)
            buf = BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()
        else:
            img_bytes = image

        b64 = base64.b64encode(img_bytes).decode()

        response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "image_url",
                "image_url": f"data:image/png;base64,{b64}",
            },
            include_image_base64=False,
        )

        text_parts: list[str] = []
        if response.pages:
            for page in response.pages:
                text_parts.append(page.markdown)
        return "\n".join(text_parts), 0.95

    except Exception as exc:
        logger.warning("Mistral OCR failed: %s", exc)
        return "", 0.0


def _run_tesseract(image) -> tuple[str, float]:
    """Run Tesseract OCR on a single page image. Returns (text, confidence)."""
    import numpy as np
    import pytesseract
    from PIL import Image

    try:
        if isinstance(image, np.ndarray):
            img = Image.fromarray(image)
        else:
            img = image

        text = pytesseract.image_to_string(img).strip()

        conf_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        confs = [int(c) for c in conf_data["conf"] if c != "-1"]
        mean_conf = sum(confs) / len(confs) / 100.0 if confs else 0.0

        return text, mean_conf
    except Exception as exc:
        logger.warning("Tesseract OCR failed: %s", exc)
        return "", 0.0


async def run_ocr_pipeline(
    document_id: uuid.UUID,
    pdf_bytes: bytes,
    *,
    enable_tier2: bool = False,
) -> OCRDocumentResult:
    """Run OCR on a document. Tier 0 (pypdf) -> Tier 1B (Mistral/Tesseract) -> Tier 2 (cloud)."""
    from app.services.nlp import create_openmed_service

    nlp = create_openmed_service()
    result = OCRDocumentResult(document_id=document_id)

    embedded_text, has_substantial_text = _extract_embedded_text(pdf_bytes)

    if has_substantial_text:
        result.method = "PYPDF_EMBEDDED_TEXT"
        result.ocr_route = "PYPDF"
        result.needs_ocr = False
        result.document_type_guess = "TYPED"
        page = OCRPageResult(page_number=1, raw_text=embedded_text, backend="pypdf", confidence=1.0)
        result.pages.append(page)
    else:
        try:
            images = _rasterize_pdf(pdf_bytes)
            raw_parts: list[str] = []
            for page_number, image in enumerate(images, start=1):
                page_text, page_conf = _run_mistral_ocr(image)
                if not page_text:
                    page_text, page_conf = _run_tesseract(image)
                    backend = "tesseract"
                else:
                    backend = "mistral_ocr"

                raw_parts.append(page_text)
                result.pages.append(
                    OCRPageResult(
                        page_number=page_number,
                        raw_text=page_text,
                        backend=backend,
                        confidence=page_conf,
                        is_handwritten=True,
                    )
                )

            result.method = backend.upper()
            result.ocr_route = backend.upper()
            result.needs_ocr = True
            result.document_type_guess = "HANDWRITTEN"

            if not result.pages:
                page = OCRPageResult(page_number=1, raw_text="", backend="none")
                page.quality_flags.append("EMPTY_PAGE")
                result.pages.append(page)

        except Exception as exc:
            logger.error(
                "OCR failed for image-based PDF",
                extra={"document_id": str(document_id), "error": str(exc)},
            )
            result.method = "OCR_UNAVAILABLE"
            result.needs_ocr = True
            page = OCRPageResult(page_number=1, raw_text="", backend="none", ocr_unavailable=True)
            page.quality_flags.append("OCR_UNAVAILABLE")
            result.pages.append(page)
            await nlp.close()
            raise OcrUnavailableError(document_id) from exc

    for page in result.pages:
        if page.raw_text and not page.ocr_unavailable:
            deid_result = await nlp.deidentify_text(page.raw_text)
            page.redacted_text = deid_result.redacted_text
            page.quality_flags.append("DEID_COMPLETE")
        elif page.ocr_unavailable:
            page.quality_flags.append("SKIPPED_OCR_UNAVAILABLE")
        elif not page.raw_text:
            page.quality_flags.append("EMPTY_PAGE")

        threshold = get_escalation_threshold(
            result.document_type_guess.lower() if result.document_type_guess != "UNKNOWN" else "handwritten",
            "en",
        )
        if page.is_handwritten or page.confidence < threshold:
            page.quality_flags.append("LOW_CONFIDENCE")
            if enable_tier2 and not page.ocr_unavailable:
                page.quality_flags.append("NEEDS_ESCALATION")
                page.needs_escalation = True

    await nlp.close()
    return result
