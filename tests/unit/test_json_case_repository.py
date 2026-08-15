"""Unit tests for the local JSON case repository."""

import json
from datetime import date
from pathlib import Path

import pytest

from app.models import Case, CaseStatus, CaseType
from app.repositories import CaseRepository, JsonCaseRepository, RepositoryDataError


def make_case(
    case_id: str = "CASE-1001",
    status: CaseStatus = CaseStatus.PENDING_PROVIDER_RESPONSE,
) -> Case:
    """Create a valid synthetic case for repository tests."""
    return Case(
        case_id=case_id,
        case_type=CaseType.ONR,
        status=status,
        created_date=date(2026, 8, 1),
        open_negotiation_start_date=date(2026, 8, 2),
        open_negotiation_end_date=date(2026, 8, 31),
        provider_name="Synthetic Provider A",
    )


def write_cases(file_path: Path, cases: list[Case]) -> None:
    """Seed a JSON repository with validated case records."""
    file_path.write_text(
        json.dumps([case.model_dump(mode="json") for case in cases]),
        encoding="utf-8",
    )


def test_loads_existing_case(tmp_path: Path) -> None:
    file_path = tmp_path / "cases.json"
    expected_case = make_case()
    write_cases(file_path, [expected_case])
    repository = JsonCaseRepository(file_path)

    loaded_case = repository.get("CASE-1001")

    assert loaded_case == expected_case


def test_unknown_case_returns_none(tmp_path: Path) -> None:
    file_path = tmp_path / "cases.json"
    write_cases(file_path, [make_case()])
    repository = JsonCaseRepository(file_path)

    assert repository.get("CASE-9999") is None


def test_saves_and_reloads_case(tmp_path: Path) -> None:
    file_path = tmp_path / "nested" / "cases.json"
    repository: CaseRepository = JsonCaseRepository(file_path)
    expected_case = make_case(case_id="CASE-2001", status=CaseStatus.NEW)

    repository.save(expected_case)
    reloaded_repository = JsonCaseRepository(file_path)

    assert reloaded_repository.get("CASE-2001") == expected_case


def test_malformed_json_raises_repository_data_error(tmp_path: Path) -> None:
    file_path = tmp_path / "cases.json"
    file_path.write_text('[{"case_id": "CASE-1001"}', encoding="utf-8")
    repository = JsonCaseRepository(file_path)

    with pytest.raises(RepositoryDataError, match="Malformed JSON"):
        repository.get("CASE-1001")
