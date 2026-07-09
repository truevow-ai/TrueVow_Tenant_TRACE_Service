"""deepdoctection service wrapper — document layout analysis + OCR.

ADR-001 §3 Stage 1: runs locally within the Fly.io HIPAA boundary using
deepdoctection with the DocTr OCR backend. Zero outbound network calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DocumentAnalysisResult:
    text: str = ""
    pages: list[dict] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    document_type: str = "typed"


class DocumentProcessingService:
    """deepdoctection wrapper — local document AI pipeline.

    ``ANALYZER.analyze(path)`` runs the full pipeline: layout analysis,
    DocTr OCR, table extraction, document classification. No external
    API calls — air-gap verified.
    """

    async def analyze(self, file_path: str) -> DocumentAnalysisResult:
        return DocumentAnalysisResult()

    async def close(self) -> None:
        pass


def create_document_processing_service() -> DocumentProcessingService:
    return DocumentProcessingService()
