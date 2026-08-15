"""Expected examples for the deterministic case lookup tool."""

from app.tools.case_tool import get_case
from tests.unit.tool_support import StubCaseRepository, make_case


def test_get_case_returns_authoritative_case() -> None:
    expected_case = make_case()
    repository = StubCaseRepository(expected_case)

    assert get_case(repository, "CASE-1001") is expected_case


def test_get_case_returns_none_for_unknown_id() -> None:
    repository = StubCaseRepository()

    assert get_case(repository, "CASE-9999") is None
