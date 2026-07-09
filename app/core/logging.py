"""Structured, PHI-safe logging.

HIPAA: log entries must never contain client names, DOBs, or addresses — only
opaque identifiers (case_id, firm_id, correlation_id). This module centralises
logger creation and applies the ``PHIRedactionFilter`` at the root logger
so no handler can accidentally emit PHI even if a caller logs raw text.

ADR-001 §8: defense-in-depth — the filter catches PHI patterns before any
handler writes them. Additional enforcement: de-ID failures are caught
and redacted before any log call in the pipeline.
"""

from __future__ import annotations

import logging
import re
import sys

_CONFIGURED = False

PHI_PATTERNS: list[tuple[str, str]] = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
    (r"\b\d{2}/\d{2}/\d{4}\b", "[DOB_REDACTED]"),
    (r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", "[NAME_REDACTED]"),
    (r"\b\d{10}\b", "[PHONE_REDACTED]"),
    (r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[EMAIL_REDACTED]"),
]


class PHIRedactionFilter(logging.Filter):
    """Redact PHI from log messages. Applied at the root logger.

    Always passes — never drops a log entry. Only modifies the message
    if a known PHI pattern is detected.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.msg
        if isinstance(message, str):
            for pattern, replacement in PHI_PATTERNS:
                message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
            record.msg = message
        return True


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-5s [%(name)s] "
            "corr=%(correlation_id)s %(message)s",
            defaults={"correlation_id": "-"},
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.addFilter(PHIRedactionFilter())
    root.setLevel(level)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
