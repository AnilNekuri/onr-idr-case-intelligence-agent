"""Expected examples for deterministic case timelines."""

from datetime import date

import pytest

from app.models import CaseEvent, CaseEventType
from app.tools.case_tool import CaseNotFoundError
from app.tools.timeline_tool import get_case_timeline
from tests.unit.tool_support import StubCaseRepository, make_case


def test_timeline_is_returned_in_chronological_order() -> None:
    later_event = CaseEvent(
        date=date(2026, 8, 3),
        type=CaseEventType.NOTICE_SENT,
        description="Notice sent",
    )
    earlier_event = CaseEvent(
        date=date(2026, 8, 1),
        type=CaseEventType.CASE_CREATED,
        description="Case created",
    )
    case = make_case(events=[later_event, earlier_event])
    repository = StubCaseRepository(case)

    timeline = get_case_timeline(repository, case.case_id)

    assert timeline == [earlier_event, later_event]
    assert case.events == [later_event, earlier_event]


def test_empty_case_timeline_returns_empty_list() -> None:
    case = make_case(events=[])

    assert get_case_timeline(StubCaseRepository(case), case.case_id) == []


def test_timeline_rejects_unknown_case() -> None:
    with pytest.raises(CaseNotFoundError, match="CASE-9999"):
        get_case_timeline(StubCaseRepository(), "CASE-9999")
