"""In-process smoke test for the deterministic Streamlit workflow."""

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.models import (
    ClaimExpectedInput,
    ClaimIntakeResponse,
    ClaimIntakeStage,
)


class ModelDrivenAssistantStub:
    """Avoid a live Bedrock call while preserving model-selected intake behavior."""

    def handle(self, session_id, _request):  # type: ignore[no-untyped-def]
        return ClaimIntakeResponse(
            session_id=session_id,
            state=ClaimIntakeStage.AWAITING_DOCUMENT,
            message="Please upload your ONR or IDR PDF.",
            expected_input=ClaimExpectedInput.PDF,
        )


def test_case_lookup_renders_deterministic_results() -> None:
    entry_point = Path(__file__).parents[2] / "streamlit_app.py"
    with patch(
        "app.ui._local_claim_intake_agent",
        return_value=ModelDrivenAssistantStub(),
    ):
        app = AppTest.from_file(entry_point, default_timeout=15).run()

        assert not app.exception
        assert app.radio[0].options == [
            "Assistant",
            "Case lookup",
            "Submit a case",
            "Upload a document",
            "Extract ONR / IDR PDF",
            "Case summary",
            "Case chat",
        ]

        assert len(app.chat_input) == 1
        app.chat_input[0].set_value("I want to process a claim")
        app.run()

        assert not app.exception
        assert len(app.file_uploader) == 1
        assert app.button[0].label == "Process claim document"
        assert app.button[0].disabled

        app.radio[0].set_value("Case lookup")
        app.run()
        app.text_input[0].input("CASE-1001")
        app.button[0].click()
        app.run()

        assert not app.exception
        metrics = {metric.label: metric.value for metric in app.metric}
        assert metrics["Status"] == "PENDING_PROVIDER_RESPONSE"
        assert metrics["Case type"] == "ONR"
        assert metrics["Deadline risk"] in {"MISSED", "HIGH", "MEDIUM", "LOW"}

        for workflow in app.radio[0].options[2:]:
            app.radio[0].set_value(workflow)
            app.run()
            assert not app.exception
