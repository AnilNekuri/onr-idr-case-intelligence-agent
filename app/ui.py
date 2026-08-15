"""Streamlit presentation layer for case intake and intelligence workflows."""

from datetime import date
from typing import Any
from uuid import uuid4

import streamlit as st

from app.agentcore_client import (
    AgentCoreRuntimeClient,
    create_agentcore_runtime_client,
)
from app.config import ApplicationSettings
from app.models import Case, CaseType
from app.services import (
    CaseDocumentService,
    CaseService,
    CaseSummaryService,
    create_case_document_service,
    create_case_service,
    create_case_summary_service,
)

_WORKFLOWS = (
    "Case lookup",
    "Submit a case",
    "Upload a document",
    "Case summary",
    "Case chat",
)


@st.cache_resource
def _case_service(settings: ApplicationSettings) -> CaseService:
    return create_case_service(settings)


@st.cache_resource
def _document_service(settings: ApplicationSettings) -> CaseDocumentService:
    return create_case_document_service(settings)


@st.cache_resource
def _summary_service(settings: ApplicationSettings) -> CaseSummaryService:
    return create_case_summary_service(settings)


@st.cache_resource
def _case_agent(settings: ApplicationSettings) -> AgentCoreRuntimeClient:
    return create_agentcore_runtime_client(settings)


def _show_error(workflow: str, error: Exception) -> None:
    """Present a concise error at the application boundary."""
    message = str(error).strip() or error.__class__.__name__
    st.error(f"{workflow} failed: {message}")


def _render_case(case: Case, service: CaseService) -> None:
    """Render authoritative facts and service-computed deterministic results."""
    status, case_type, provider = st.columns(3)
    status.metric("Status", case.status.value)
    case_type.metric("Case type", case.case_type.value)
    provider.metric("Provider", case.provider_name)

    st.caption(
        f"Created {case.created_date.isoformat()} | Negotiation window "
        f"{case.open_negotiation_start_date.isoformat()} to "
        f"{case.open_negotiation_end_date.isoformat()}"
    )

    risk = service.get_deadline_risk(case.case_id, current_date=date.today())
    risk_col, remaining_col, deadline_col = st.columns(3)
    risk_col.metric("Deadline risk", risk.risk.value)
    remaining_col.metric("Days remaining", risk.days_remaining)
    deadline_col.metric("Deadline", risk.deadline.isoformat())

    st.subheader("Missing information")
    missing = service.get_missing_information(case.case_id)
    if missing:
        for item in missing:
            st.warning(item)
    else:
        st.success("No missing information identified by deterministic checks.")

    st.subheader("Timeline")
    timeline = service.get_timeline(case.case_id)
    if timeline:
        st.dataframe(
            [
                {
                    "Date": event.date.isoformat(),
                    "Event": event.type.value,
                    "Description": event.description,
                }
                for event in timeline
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("No timeline events are recorded.")

    st.subheader("Documents")
    if case.documents:
        st.dataframe(
            [
                {
                    "File": document.file_name,
                    "Document ID": document.document_id,
                    "Storage key": document.s3_key,
                }
                for document in case.documents
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("No supporting documents are attached.")

    if case.additional_notes:
        st.subheader("Notes")
        st.write(case.additional_notes)


def _lookup_workflow(settings: ApplicationSettings) -> None:
    st.header("Case lookup and deterministic results")
    st.write(
        "Retrieve authoritative facts, timeline, missing items, and deadline risk."
    )
    with st.form("case_lookup_form"):
        case_id = st.text_input("Case ID", placeholder="CASE-1001")
        submitted = st.form_submit_button("Look up case", type="primary")

    if not submitted:
        return
    try:
        service = _case_service(settings)
        case = service.get_case(case_id.strip())
        if case is None:
            st.warning(f"No case was found for {case_id.strip() or 'the supplied ID'}.")
            return
        _render_case(case, service)
    except Exception as error:  # Streamlit must turn adapter failures into UI errors.
        _show_error("Case lookup", error)


def _submission_workflow(settings: ApplicationSettings) -> None:
    st.header("Submit a case")
    st.write(
        "Leave Case ID blank to generate one. Initial status is set by the service."
    )
    with st.form("case_submission_form", clear_on_submit=False):
        case_type_value = st.selectbox("Case type", [item.value for item in CaseType])
        case_id = st.text_input("Case ID (optional)", placeholder="Generated if blank")
        provider_name = st.text_input("Provider name")
        start_date = st.date_input("Negotiation start date", value=date.today())
        end_date = st.date_input("Negotiation end date", value=date.today())
        missing_text = st.text_input(
            "Missing document names (optional)",
            help="Separate multiple document names with commas.",
        )
        notes = st.text_area("Additional notes (optional)")
        submitted = st.form_submit_button("Create case", type="primary")

    if not submitted:
        return
    missing_documents = [
        item.strip() for item in missing_text.split(",") if item.strip()
    ]
    try:
        created = _case_service(settings).submit_case(
            case_type=CaseType(case_type_value),
            case_id=case_id.strip() or None,
            provider_name=provider_name,
            created_date=date.today(),
            open_negotiation_start_date=start_date,
            open_negotiation_end_date=end_date,
            missing_documents=missing_documents,
            additional_notes=notes or None,
        )
        st.success(
            f"Case {created.case_id} was created with status {created.status.value}."
        )
        st.json(created.model_dump(mode="json"))
    except Exception as error:
        _show_error("Case submission", error)


def _upload_workflow(settings: ApplicationSettings) -> None:
    st.header("Upload a supporting document")
    st.write("PDFs are stored through the document service and attached to the case.")
    with st.form("document_upload_form"):
        case_id = st.text_input("Case ID", placeholder="CASE-1001")
        uploaded_file = st.file_uploader("PDF document", type=["pdf"])
        submitted = st.form_submit_button("Upload document", type="primary")

    if not submitted:
        return
    if uploaded_file is None:
        st.error("Document upload failed: select a PDF document.")
        return
    try:
        updated_case, document = _document_service(settings).upload_document(
            case_id,
            uploaded_file.name,
            uploaded_file.getvalue(),
            received_date=date.today(),
            metadata={"uploaded-by": "streamlit"},
        )
        st.success(f"{document.file_name} was attached to {updated_case.case_id}.")
        st.json(document.model_dump(mode="json"))
    except Exception as error:
        _show_error("Document upload", error)


def _summary_workflow(settings: ApplicationSettings) -> None:
    st.header("Case summary")
    st.write("Generate a fact-only summary of one authoritative case record.")
    with st.form("case_summary_form"):
        case_id = st.text_input("Case ID", placeholder="CASE-1001")
        submitted = st.form_submit_button("Generate summary", type="primary")

    if not submitted:
        return
    try:
        case = _case_service(settings).get_case(case_id.strip())
        if case is None:
            st.warning(f"No case was found for {case_id.strip() or 'the supplied ID'}.")
            return
        with st.spinner("Generating grounded summary..."):
            summary = _summary_service(settings).summarize(case)
        st.markdown(summary)
    except Exception as error:
        _show_error("Case summary", error)


def _render_chat_message(message: dict[str, Any]) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        citations = message.get("citations", [])
        if citations:
            st.caption("Knowledge Base citations")
            for citation in citations:
                st.code(
                    f"[{citation['source_id']}] {citation['document_location']}",
                    language=None,
                )
        unavailable = message.get("unavailable", [])
        if unavailable:
            st.warning("Unavailable evidence: " + ", ".join(unavailable))


def _chat_workflow(settings: ApplicationSettings) -> None:
    st.header("Chat with case intelligence")
    st.write(
        "Answers use authoritative case facts and cite retrieved process guidance."
    )
    case_id = st.text_input("Case ID", placeholder="CASE-1001", key="chat_case_id")

    histories = st.session_state.setdefault("case_chat_histories", {})
    history = histories.setdefault(case_id.strip(), []) if case_id.strip() else []
    for message in history:
        _render_chat_message(message)

    question = st.chat_input(
        "Ask about status, missing information, deadlines, or next actions",
        disabled=not bool(case_id.strip()),
    )
    if not question:
        return

    user_message = {"role": "user", "content": question}
    history.append(user_message)
    _render_chat_message(user_message)
    try:
        session_ids = st.session_state.setdefault("agentcore_session_ids", {})
        runtime_session_id = session_ids.setdefault(case_id.strip(), str(uuid4()))
        with st.spinner("Retrieving evidence and generating an answer..."):
            answer = _case_agent(settings).answer(
                case_id.strip(),
                question,
                current_date=date.today(),
                runtime_session_id=runtime_session_id,
            )
        content = answer.generated_answer or (
            "No answer was generated because the authoritative case was not found."
        )
        assistant_message = {
            "role": "assistant",
            "content": content,
            "citations": [citation.model_dump() for citation in answer.citations],
            "unavailable": list(answer.unavailable_evidence),
        }
        history.append(assistant_message)
        _render_chat_message(assistant_message)
    except Exception as error:
        _show_error("Case chat", error)


def main() -> None:
    """Render the selected Streamlit workflow."""
    st.set_page_config(
        page_title="ONR / IDR Case Intelligence",
        page_icon=":material/assignment:",
        layout="wide",
    )
    st.title("ONR / IDR Case Intelligence")
    st.caption("Authoritative case workflows with deterministic and grounded results")

    try:
        settings = ApplicationSettings.from_environment()
    except Exception as error:
        _show_error("Application configuration", error)
        st.stop()

    with st.sidebar:
        st.subheader("Workflow")
        selected = st.radio(
            "Choose a workflow", _WORKFLOWS, label_visibility="collapsed"
        )
        st.divider()
        st.caption(f"Case repository: {settings.case_repository.value}")
        st.caption(f"AWS region: {settings.aws_region}")

    workflows = {
        "Case lookup": _lookup_workflow,
        "Submit a case": _submission_workflow,
        "Upload a document": _upload_workflow,
        "Case summary": _summary_workflow,
        "Case chat": _chat_workflow,
    }
    workflows[selected](settings)
