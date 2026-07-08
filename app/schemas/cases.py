"""Case API schemas."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field


class ClientData(BaseModel):
    name: str = Field(min_length=1)
    dob: str = Field(min_length=1)  # kept as string; encrypted, never parsed/stored in clear
    address: str = Field(min_length=1)
    phone: str = Field(min_length=1)


class IntakeStatute(BaseModel):
    """SOL snapshot carried from INTAKE (preferred over TRACE's fallback table)."""

    sol_years: int | None = None
    reference: str | None = None
    version: str | None = None


class CaseCreateRequest(BaseModel):
    intake_record_id: uuid.UUID
    attorney_id: uuid.UUID | None = None
    firm_id: uuid.UUID | None = None  # must match the authenticated firm if provided
    client_data: ClientData
    incident_date: date
    jurisdiction_state: str = Field(min_length=2, max_length=2)
    intake_statute: IntakeStatute | None = None
    provider_hints: list[str] = Field(default_factory=list)


class CaseCreateResponse(BaseModel):
    case_id: str
    sol_deadline: str | None
    sol_urgency: str
    sol_disclaimer: str
    stage: str
