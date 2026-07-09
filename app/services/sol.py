"""Statute-of-limitations resolution.

Per ADR-000, TRACE prefers the SOL snapshot already computed and attorney-facing
in INTAKE (``intake_sessions.statute_*`` + the 23 jurisdiction JSON files). When
a snapshot is supplied on the intake record we use it verbatim; otherwise we fall
back to the standard per-state personal-injury table below (spec §5.4), which
covers all 50 states + DC.

The mandatory, non-dismissible disclaimer is attached to EVERY SOL result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Standard personal-injury SOL, in years (spec §5.4). This is a fallback only —
# it does NOT model tolling, discovery rules, or government-entity notice.
SOL_TABLE: dict[str, int] = {
    "AL": 2, "AK": 2, "AZ": 2, "AR": 3, "CA": 2, "CO": 3,
    "CT": 2, "DE": 2, "FL": 4, "GA": 2, "HI": 2, "ID": 2,
    "IL": 2, "IN": 2, "IA": 2, "KS": 2, "KY": 1, "LA": 1,
    "ME": 6, "MD": 3, "MA": 3, "MI": 3, "MN": 2, "MS": 3,
    "MO": 5, "MT": 3, "NE": 4, "NV": 2, "NH": 3, "NJ": 2,
    "NM": 3, "NY": 3, "NC": 3, "ND": 6, "OH": 2, "OK": 2,
    "OR": 2, "PA": 2, "RI": 3, "SC": 3, "SD": 3, "TN": 1,
    "TX": 2, "UT": 4, "VT": 3, "VA": 2, "WA": 3, "WV": 2,
    "WI": 3, "WY": 4, "DC": 3,
}

SOL_DISCLAIMER = (
    "This calculation is based on the standard personal injury statute of "
    "limitations for the indicated state and incident date. Tolling provisions, "
    "discovery rules, government entity notice requirements, and other "
    "state-specific exceptions may apply. The attorney is responsible for "
    "confirming the applicable deadline before relying on this calculation for "
    "any purpose."
)

# Bump when the SOL_TABLE is reviewed by counsel (spec §5.4 maintenance requirement).
SOL_TABLE_VERSION = "2026-07"


@dataclass(frozen=True)
class SOLResult:
    sol_deadline: date | None
    days_remaining: int | None
    urgency: str
    reference: str | None
    source: str  # "intake_snapshot" | "sol_table"
    table_version: str = SOL_TABLE_VERSION
    disclaimer: str = SOL_DISCLAIMER

    def to_dict(self) -> dict:
        return {
            "sol_deadline": self.sol_deadline.isoformat() if self.sol_deadline else None,
            "days_remaining": self.days_remaining,
            "sol_urgency": self.urgency,
            "sol_reference": self.reference,
            "sol_source": self.source,
            "sol_table_version": self.table_version,
            "sol_disclaimer": self.disclaimer,
        }


def _urgency(days_remaining: int) -> str:
    if days_remaining > 180:
        return "Standard"
    if days_remaining > 90:
        return "Monitor"
    if days_remaining > 30:
        return "Urgent"
    return "Critical"


def _deadline(incident_date: date, years: int) -> date:
    try:
        return incident_date.replace(year=incident_date.year + years)
    except ValueError:
        # Feb 29 incident + non-leap deadline year -> use Feb 28.
        return incident_date.replace(year=incident_date.year + years, day=28)


def calculate_sol(
    incident_date: date,
    state: str,
    *,
    today: date | None = None,
    sol_years: int | None = None,
    reference: str | None = None,
) -> SOLResult:
    """Resolve the SOL.

    ``sol_years``/``reference`` (from the INTAKE snapshot) take precedence; when
    absent, the standard per-state table is used. Raises ``KeyError`` if the
    state is unknown and no snapshot is provided.
    """
    today = today or date.today()
    state_code = (state or "").upper()

    if sol_years is not None:
        source = "intake_snapshot"
        years = sol_years
    else:
        if state_code not in SOL_TABLE:
            raise KeyError(f"State '{state_code}' not found in SOL table.")
        source = "sol_table"
        years = SOL_TABLE[state_code]

    deadline = _deadline(incident_date, years)
    days_remaining = (deadline - today).days
    return SOLResult(
        sol_deadline=deadline,
        days_remaining=days_remaining,
        urgency=_urgency(days_remaining),
        reference=reference,
        source=source,
    )
