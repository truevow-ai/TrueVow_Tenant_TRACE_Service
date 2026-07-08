"""Structured, PHI-safe logging.

HIPAA: log entries must never contain client names, DOBs, or addresses — only
opaque identifiers (case_id, firm_id, correlation_id). This module centralises
logger creation so that convention is easy to follow.
"""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


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
    root.setLevel(level)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
