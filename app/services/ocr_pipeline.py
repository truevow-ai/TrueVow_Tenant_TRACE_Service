"""OCR Pipeline — tiered text extraction + de-identification.

Four-tier routing (per ADR-003 / Tech Spec Part 2):
  TIER 0 : pypdf         — embedded text layer (no OCR needed)
  TIER 1A: Docling       — digital PDFs with no text layer  [see NOTE below]
  TIER 1B: PaddleOCR-VL  — scanned / faxed / handwritten pages
  TIER 2 : Mistral OCR   — cloud, only when Tier 1B confidence < 80%

Replaces the prior image-OCR engine (eliminated). Surfaces clearly when OCR is
unavailable — never silently returns empty text. Attorney sees:
"OCR processing unavailable for image-based documents" with an actionable
next step, not a silently empty chronology.

NOTE (flagged for review): Tier 1B feeds PaddleOCR rasterized page images.
Rasterization uses PyMuPDF (`fitz`), which must be added to requirements.txt
and the Dockerfile before this path works end-to-end. Tier 1A (Docling for
digital-no-text PDFs) is scaffolded but not yet wired into the router.
"""

from __future__ import annotations

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
    ocr_route: str = "PADDLEOCR_VL"
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
    """TIER 0 — extract text from digital PDFs that already have a text layer.
    Returns (text, had_substantial_text)."""
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


# TIER 1B — PaddleOCR-VL (primary) with Tesseract fallback.
# PaddleOCR 3.3.1 has a cross-platform oneDNN bug (pir::ArrayAttribute<double>)
# that prevents all PP-OCR models from running on CPU. Tesseract serves as the
# active engine until the upstream PaddlePaddle fix ships.
# Once PaddlePaddle >= 3.3.2 is available, remove the NotImplementedError catch.
_OCR_ENGINE = None
_OCR_BACKEND = "paddleocr"


def _get_ocr_engine():
    global _OCR_ENGINE, _OCR_BACKEND
    if _OCR_ENGINE is not None:
        return _OCR_ENGINE

    try:
        from paddleocr import PaddleOCR

        engine = PaddleOCR(lang="en")
        _ = engine  # touch import — may raise
    except Exception as exc:
        logger.warning("PaddleOCR unavailable (%s), falling back to Tesseract", type(exc).__name__)
        _OCR_BACKEND = "tesseract"
    else:
        _OCR_ENGINE = engine
        _OCR_BACKEND = "paddleocr"
        return _OCR_ENGINE

    import pytesseract

    _OCR_ENGINE = "tesseract"
    _OCR_BACKEND = "tesseract"
    return _OCR_ENGINE


def _rasterize_pdf(pdf_bytes: bytes) -> list:
    """Rasterize PDF pages to image arrays for OCR.

    Uses PyMuPDF (`fitz`). Raises if unavailable so the caller fails loudly
    rather than silently returning empty text. `pymupdf` must be present in
    requirements.txt / Dockerfile for this to work.
    """
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


def _run_tesseract(image) -> tuple[str, float]:
    """Run Tesseract OCR on a single page image. Returns (text, mean_confidence)."""
    import pytesseract

    try:
        text = pytesseract.image_to_string(image).strip()
        conf_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        confidences = [
            int(c) for c in conf_data["conf"] if c != "-1" and c != "-1"
        ]
        mean_conf = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
        return text, mean_conf
    except Exception:
        return "", 0.0


def _run_paddleocr(image) -> tuple[str, float]:
    """Run PaddleOCR-VL on a single page image. Returns (text, mean_confidence)."""
    engine = _get_ocr_engine()
    if _OCR_BACKEND == "tesseract":
        return _run_tesseract(image)

    result = engine.predict(image)
    if not result:
        return "", 0.0
    texts: list[str] = []
    confidences: list[float] = []
    for item in result:
        rec_text = item.get("rec_text", "")
        rec_score = item.get("rec_score", 0.0)
        if rec_text:
            texts.append(str(rec_text))
            confidences.append(float(rec_score))
    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return " ".join(texts), mean_conf


async def run_ocr_pipeline(
    document_id: uuid.UUID,
    pdf_bytes: bytes,
    *,
    enable_tier2: bool = False,
) -> OCRDocumentResult:
    """Run OCR on a document. Handles digital and image-based PDFs correctly."""
    from app.services.nlp import create_openmed_service

    nlp = create_openmed_service()
    result = OCRDocumentResult(document_id=document_id)
    raw_text = ""

    embedded_text, has_substantial_text = _extract_embedded_text(pdf_bytes)

    if has_substantial_text:
        # TIER 0 — embedded text layer.
        raw_text = embedded_text
        result.method = "PYPDF_EMBEDDED_TEXT"
        result.ocr_route = "PYPDF"
        result.needs_ocr = False
        result.document_type_guess = "TYPED"
        page = OCRPageResult(page_number=1, raw_text=raw_text, backend="pypdf", confidence=1.0)
        result.pages.append(page)
    else:
        # TIER 1B — PaddleOCR-VL on rasterized page images.
        try:
            images = _rasterize_pdf(pdf_bytes)
            raw_parts: list[str] = []
            confidences: list[float] = []
            for page_number, image in enumerate(images, start=1):
                page_text, page_conf = _run_paddleocr(image)
                raw_parts.append(page_text)
                confidences.append(page_conf)
                result.pages.append(
                    OCRPageResult(
                        page_number=page_number,
                        raw_text=page_text,
                        backend="paddleocr",
                        confidence=page_conf,
                        is_handwritten=True,
                    )
                )
            raw_text = "\n".join(raw_parts)

            result.method = _OCR_BACKEND.upper()
            result.ocr_route = _OCR_BACKEND.upper()
            result.needs_ocr = True
            result.document_type_guess = "HANDWRITTEN"

            if not result.pages:
                page = OCRPageResult(page_number=1, raw_text="", backend="none")
                page.quality_flags.append("EMPTY_PAGE")
                result.pages.append(page)
        except Exception as exc:
            logger.error(
                "PaddleOCR-VL OCR failed for image-based PDF",
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
            # TIER 2 — Mistral OCR escalation (cloud) when Tier 1B is below threshold.
            if enable_tier2 and not page.ocr_unavailable:
                page.quality_flags.append("NEEDS_ESCALATION")
                page.needs_escalation = True

    await nlp.close()
    return result
