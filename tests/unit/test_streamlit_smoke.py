"""In-process smoke test for the deterministic Streamlit workflow."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_case_lookup_renders_deterministic_results() -> None:
    entry_point = Path(__file__).parents[2] / "streamlit_app.py"
    app = AppTest.from_file(entry_point, default_timeout=15).run()

    assert not app.exception
    assert app.radio[0].options == [
        "Case lookup",
        "Submit a case",
        "Upload a document",
        "Case summary",
        "Case chat",
    ]

    app.text_input[0].input("CASE-1001")
    app.button[0].click()
    app.run()

    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Status"] == "PENDING_PROVIDER_RESPONSE"
    assert metrics["Case type"] == "ONR"
    assert metrics["Deadline risk"] in {"MISSED", "HIGH", "MEDIUM", "LOW"}

    for workflow in app.radio[0].options[1:]:
        app.radio[0].set_value(workflow)
        app.run()
        assert not app.exception
