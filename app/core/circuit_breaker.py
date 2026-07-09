"""Circuit breaker for external API calls.

ADR-001 §10: prevent cascading failures from unresponsive external
dependencies (Fax.Plus, CMS NPI Registry). If >50% of calls fail
within a 5-minute window, the circuit opens and calls are queued
for retry instead of blocking the pipeline.

Pattern: failures + reset timeout. Not a full pybreaker-style
state machine — deliberately simple for the number of external
dependencies TRACE has (exactly two in Phase 1).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CircuitState:
    name: str
    fail_max: int = 5
    reset_timeout: float = 300.0
    _failures: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _open: bool = field(default=False, init=False)

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.time()
        if self._failures >= self.fail_max:
            self._open = True

    def record_success(self) -> None:
        self._failures = 0
        self._open = False

    @property
    def is_open(self) -> bool:
        if self._open and (time.time() - self._last_failure_time) > self.reset_timeout:
            self._open = False
            self._failures = 0
        return self._open

    @property
    def is_closed(self) -> bool:
        return not self.is_open


_fax_circuit = CircuitState(name="fax_plus", fail_max=5, reset_timeout=300.0)
_npi_circuit = CircuitState(name="cms_npi", fail_max=5, reset_timeout=300.0)


def get_fax_circuit() -> CircuitState:
    return _fax_circuit


def get_npi_circuit() -> CircuitState:
    return _npi_circuit
