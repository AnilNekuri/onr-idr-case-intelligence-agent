"""Deterministic deadline-risk calculation for a case."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.models import Case
from app.repositories import CaseRepository
from app.tools.case_tool import require_case


class DeadlineRisk(StrEnum):
    """Risk levels determined only by days remaining."""

    MISSED = "MISSED"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True, slots=True)
class DeadlineRiskResult:
    """A case deadline together with its deterministic risk assessment."""

    deadline: date
    days_remaining: int
    risk: DeadlineRisk


def calculate_deadline_risk(
    repository: CaseRepository,
    case_id: str,
    *,
    current_date: date,
) -> DeadlineRiskResult:
    """Calculate deadline risk relative to an explicitly supplied date."""
    case = require_case(repository, case_id)
    return assess_deadline_risk(case, current_date=current_date)


def assess_deadline_risk(
    case: Case,
    *,
    current_date: date,
) -> DeadlineRiskResult:
    """Calculate deadline risk from an already retrieved authoritative case."""
    deadline = case.open_negotiation_end_date
    days_remaining = (deadline - current_date).days

    if days_remaining < 0:
        risk = DeadlineRisk.MISSED
    elif days_remaining <= 3:
        risk = DeadlineRisk.HIGH
    elif days_remaining <= 7:
        risk = DeadlineRisk.MEDIUM
    else:
        risk = DeadlineRisk.LOW

    return DeadlineRiskResult(
        deadline=deadline,
        days_remaining=days_remaining,
        risk=risk,
    )
