"""OCRService abstraction — deepdoctection + DocTr with adaptive thresholds.

ADR-001 §2: ``OCR_CLOUD_BACKEND`` env var selects the cloud escalation
backend (LlamaParse). Tier 2 is only active if the Phase 1C handwriting
accuracy spike (§19) triggers escalation.

Tier 1 (always active): deepdoctection + DocTr — local, air-gapped,
zero outbound calls.

Adaptive thresholds per ADR-001 §10: document-type-aware (typed vs
handwritten) and language-aware (en vs es). Defaults to 0.80 if
classification is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

OCR_THRESHOLDS: dict[tuple[str, str], float] = {
    ("typed", "en"): 0.90,
    ("handwritten", "en"): 0.70,
    ("typed", "es"): 0.85,
    ("handwritten", "es"): 0.65,
}


class OCRProvider(str, Enum):
    DEEPDOCTECTION = "deepdoctection"
    LLAMAPARSE = "llamaparse"


@dataclass
class OCRPageResult:
    text: str
    confidence: float
    is_handwritten: bool = False
    backend: str = "doctr"
    layout_json: dict | None = None


@dataclass
class OCRDocumentResult:
    pages: list[OCRPageResult]
    document_type: str = "typed"
    language: str = "en"

    @property
    def mean_confidence(self) -> float:
        if not self.pages:
            return 0.0
        return sum(page.confidence for page in self.pages) / len(self.pages)


def get_review_threshold(document_type: str, language: str) -> float:
    return OCR_THRESHOLDS.get((document_type, language), 0.80)


class DeepdoctectionOCRService:
    """Tier 1 OCR — deepdoctection + DocTr, local, air-gapped, zero outbound."""

    async def process_document(self, file_path: str) -> OCRDocumentResult:
        return OCRDocumentResult(pages=[])


class LlamaParseOCRService:
    """Tier 2 OCR escalation — LlamaParse VLM, BAA-covered, activated only
    if Phase 1C handwriting spike fails (ADR-001 §19)."""

    def __init__(self) -> None:
        self._configured = False

    async def process_page(self, page_image: bytes) -> OCRPageResult:
        return OCRPageResult(text="[LlamaParse stub]", confidence=0.95, backend="llamaparse")


class HybridOCRService:
    """Routes pages through Tier 1 first, escalates to Tier 2 only for
    handwritten or low-confidence pages."""

    def __init__(self) -> None:
        self.tier1 = DeepdoctectionOCRService()
        self.tier2: LlamaParseOCRService | None = None

    async def process_document(self, file_path: str) -> OCRDocumentResult:
        result = await self.tier1.process_document(file_path)
        for page in result.pages:
            threshold = get_review_threshold(result.document_type, result.language)
            if page.is_handwritten or page.confidence < threshold:
                if self.tier2 is not None:
                    cloud_result = await self.tier2.process_page(b"")
                    page.text = cloud_result.text
                    page.confidence = cloud_result.confidence
                    page.backend = cloud_result.backend
        return result


def create_ocr_service() -> HybridOCRService:
    service = HybridOCRService()
    return service
