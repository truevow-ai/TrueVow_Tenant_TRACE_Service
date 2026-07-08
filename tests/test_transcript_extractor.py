"""Transcript provider-extractor tests (rule-based path; no model download)."""

from __future__ import annotations

from app.services.transcript_extractor import extract_provider_hints

_TRANSCRIPT = (
    "After the accident I was taken by ambulance to Cedars-Sinai Medical Center. "
    "A few days later I saw Dr. Jane Smith for my back pain, and she referred me to "
    "LA Ortho Clinic. I also had scans done at Westside Imaging."
)


def test_extracts_facilities_and_doctors():
    hints = extract_provider_hints(_TRANSCRIPT, use_spacy=False)
    joined = " | ".join(hints)
    assert "Cedars-Sinai Medical Center" in joined
    assert "LA Ortho Clinic" in joined
    assert "Westside Imaging" in joined
    assert "Dr. Jane Smith" in joined


def test_empty_transcript_returns_empty():
    assert extract_provider_hints("", use_spacy=False) == []


def test_dedupes_repeated_mentions():
    text = "I went to Mercy Hospital. Later, Mercy Hospital called me back."
    hints = extract_provider_hints(text, use_spacy=False)
    assert hints.count("Mercy Hospital") == 1
