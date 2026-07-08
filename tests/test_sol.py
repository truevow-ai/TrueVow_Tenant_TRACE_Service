"""SOL service unit tests (no DB required)."""

from __future__ import annotations

import datetime

import pytest

from app.services.sol import SOL_DISCLAIMER, SOL_TABLE, calculate_sol


def test_all_states_and_dc_present_and_computable():
    incident = datetime.date(2025, 1, 15)
    assert len(SOL_TABLE) == 51  # 50 states + DC
    for state in SOL_TABLE:
        result = calculate_sol(incident, state, today=datetime.date(2025, 6, 1))
        assert result.sol_deadline is not None
        assert result.disclaimer == SOL_DISCLAIMER


def test_deadline_and_urgency_boundaries():
    incident = datetime.date(2024, 1, 1)
    # CA = 2 years -> deadline 2026-01-01.
    # Standard: > 180 days out.
    r = calculate_sol(incident, "CA", today=datetime.date(2025, 1, 1))
    assert r.sol_deadline == datetime.date(2026, 1, 1)
    assert r.urgency == "Standard"
    # Monitor: exactly 120 days out.
    r = calculate_sol(incident, "CA", today=datetime.date(2025, 9, 3))
    assert r.urgency == "Monitor"
    # Urgent: 45 days out.
    r = calculate_sol(incident, "CA", today=datetime.date(2025, 11, 17))
    assert r.urgency == "Urgent"
    # Critical: 10 days out.
    r = calculate_sol(incident, "CA", today=datetime.date(2025, 12, 22))
    assert r.urgency == "Critical"


def test_urgency_exact_thresholds():
    incident = datetime.date(2024, 1, 1)
    deadline = datetime.date(2026, 1, 1)  # CA 2yr
    # 181 days -> Standard; 180 -> Monitor
    assert calculate_sol(incident, "CA", today=deadline - datetime.timedelta(days=181)).urgency == "Standard"
    assert calculate_sol(incident, "CA", today=deadline - datetime.timedelta(days=180)).urgency == "Monitor"
    assert calculate_sol(incident, "CA", today=deadline - datetime.timedelta(days=90)).urgency == "Urgent"
    assert calculate_sol(incident, "CA", today=deadline - datetime.timedelta(days=30)).urgency == "Critical"


def test_intake_snapshot_takes_precedence_over_table():
    incident = datetime.date(2024, 1, 1)
    r = calculate_sol(
        incident,
        "CA",
        today=datetime.date(2025, 1, 1),
        sol_years=3,  # snapshot says 3 (e.g., med-mal), overriding the PI table's 2
        reference="Cal. Code Civ. Proc. § 340.5",
    )
    assert r.sol_deadline == datetime.date(2027, 1, 1)
    assert r.source == "intake_snapshot"
    assert r.reference == "Cal. Code Civ. Proc. § 340.5"


def test_unknown_state_without_snapshot_raises():
    with pytest.raises(KeyError):
        calculate_sol(datetime.date(2025, 1, 1), "ZZ")


def test_leap_day_incident_does_not_crash():
    r = calculate_sol(datetime.date(2024, 2, 29), "CA", today=datetime.date(2024, 3, 1))
    assert r.sol_deadline == datetime.date(2026, 2, 28)
