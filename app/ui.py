"""Streamlit presentation layer for case intake and intelligence workflows."""

from datetime import date
from typing import Any
from uuid import uuid4

import streamlit as st

from app.agentcore_client import (
    AgentCoreRuntimeClient,
    create_agentcore_runtime_client,
)
from app.claim_intake_agentcore_client import (
    ClaimIntakeAgentCoreClient,
    create_claim_intake_agentcore_client,
)
from app.config import ApplicationSettings, ConfigurationError
from app.models import (
    Case,
    CaseType,
    ClaimExpectedInput,
    ClaimIntakeAction,
    ClaimIntakeRequest,
    ClaimIntakeResponse,
    DisputeDocumentExtraction,
)
from app.services import (
    CaseDocumentService,
    CaseService,
    CaseSummaryService,
    ClaimIntakeUploadService,
    ConversationalClaimAgent,
    DocumentExtractionService,
    KnowledgeChatService,
    create_case_document_service,
    create_case_service,
    create_case_summary_service,
    create_claim_intake_upload_service,
    create_document_extraction_service,
    create_knowledge_chat_service,
    create_local_conversational_claim_agent,
)

_WORKFLOWS = (
    "Assistant",
    "Case lookup",
    "Submit a case",
    "Upload a document",
    "Extract ONR / IDR PDF",
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
def _extraction_service(settings: ApplicationSettings) -> DocumentExtractionService:
    return create_document_extraction_service(settings)


@st.cache_resource
def _case_agent(settings: ApplicationSettings) -> AgentCoreRuntimeClient:
    return create_agentcore_runtime_client(settings)


@st.cache_resource
def _knowledge_chat_service(settings: ApplicationSettings) -> KnowledgeChatService:
    return create_knowledge_chat_service(settings)


@st.cache_resource
def _claim_intake_agent(
    settings: ApplicationSettings,
) -> ClaimIntakeAgentCoreClient:
    return create_claim_intake_agentcore_client(settings)


@st.cache_resource
def _claim_intake_upload_service(
    settings: ApplicationSettings,
) -> ClaimIntakeUploadService:
    return create_claim_intake_upload_service(settings)


@st.cache_resource
def _local_claim_intake_agent(
    settings: ApplicationSettings,
) -> ConversationalClaimAgent:
    return create_local_conversational_claim_agent(settings)


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


def _extraction_workflow(settings: ApplicationSettings) -> None:
    st.header("ONR / IDR document extraction")
    st.write(
        "Upload a synthetic PDF to run S3, Amazon Textract, Bedrock Mantle JSON "
        "extraction, and Pydantic validation."
    )
    st.caption(
        "The result is assistive OCR interpretation. It does not validate a claim "
        "or determine legal eligibility."
    )
    with st.form("document_extraction_form"):
        uploaded_file = st.file_uploader(
            "ONR or IDR PDF", type=["pdf"], key="extraction_pdf"
        )
        submitted = st.form_submit_button("Extract document", type="primary")

    if not submitted:
        return
    if uploaded_file is None:
        st.error("Document extraction failed: select a PDF document.")
        return

    try:
        with st.spinner("Reading document structure and extracting fields..."):
            result = _extraction_service(settings).extract(
                file_name=uploaded_file.name,
                content=uploaded_file.getvalue(),
            )
    except Exception as error:
        _show_error("Document extraction", error)
        return

    document = result.document
    document_type, evidence_count, missing_count = st.columns(3)
    document_type.metric("Document type", document.document_type.value)
    evidence_count.metric("Fields with OCR evidence", len(result.field_evidence))
    missing_count.metric("Review fields missing", len(result.missing_fields))

    if result.warnings:
        st.subheader("Review warnings")
        for warning in result.warnings:
            st.warning(warning)
    if result.missing_fields:
        st.info("Missing review fields: " + ", ".join(result.missing_fields))

    st.subheader("Normalized document")
    st.json(document.model_dump(mode="json"))

    st.subheader("Field evidence")
    if result.field_evidence:
        st.dataframe(
            [
                {
                    "Field": field,
                    "Value": evidence.value,
                    "Page": evidence.page,
                    "Confidence": evidence.confidence,
                    "OCR evidence": evidence.raw_text,
                }
                for field, evidence in result.field_evidence.items()
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.warning("No direct field evidence could be matched.")

    with st.expander("Raw normalized Textract text"):
        st.text(result.raw_textract_text or "No OCR text returned")
    with st.expander("Complete extraction JSON"):
        st.json(result.model_dump(mode="json"))


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
        extraction = message.get("extraction")
        if isinstance(extraction, DisputeDocumentExtraction):
            _render_assistant_extraction(extraction)
        claim_response = message.get("claim_response")
        if isinstance(claim_response, ClaimIntakeResponse):
            _render_claim_intake_response(claim_response)


def _render_claim_intake_response(response: ClaimIntakeResponse) -> None:
    """Render the structured response from the remote intake runtime."""
    if response.tools_used:
        st.caption("Tools used: " + ", ".join(response.tools_used))
    if response.specialist_agent:
        st.caption("Specialist agent: " + response.specialist_agent)
    if response.document_type is not None:
        document_type, missing, ready = st.columns(3)
        document_type.metric("Document type", response.document_type.value)
        missing.metric("Missing fields", len(response.missing_fields))
        ready.metric("Ready to submit", "Yes" if response.can_submit else "No")
    if response.case_id:
        if response.duplicate_detected:
            st.info(f"Existing case: {response.case_id}")
        else:
            st.success(f"Created case: {response.case_id}")
    if response.summary:
        st.markdown("**Summary**")
        st.write(response.summary)
    if response.missing_fields:
        st.warning(
            "Missing information: "
            + ", ".join(field.replace("_", " ") for field in response.missing_fields)
        )
    if response.next_actions:
        st.markdown("**Next actions**")
        for action in response.next_actions:
            st.markdown(f"- {action}")
    if response.warnings:
        with st.expander("Review warnings"):
            for warning in response.warnings:
                st.warning(warning)
    if response.extracted_fields:
        with st.expander("Extracted claim information"):
            st.json(response.extracted_fields)


def _render_assistant_extraction(result: DisputeDocumentExtraction) -> None:
    """Show the claim document result inside its assistant response."""
    document = result.document
    document_type, evidence_count, missing_count = st.columns(3)
    document_type.metric("Document type", document.document_type.value)
    evidence_count.metric("Fields with evidence", len(result.field_evidence))
    missing_count.metric("Missing review fields", len(result.missing_fields))

    if result.warnings:
        with st.expander("Review warnings"):
            for warning in result.warnings:
                st.warning(warning)
    with st.expander("Extracted claim data"):
        st.json(document.model_dump(mode="json"))
    if result.field_evidence:
        with st.expander("OCR field evidence"):
            st.dataframe(
                [
                    {
                        "Field": field,
                        "Value": evidence.value,
                        "Page": evidence.page,
                        "Confidence": evidence.confidence,
                        "OCR evidence": evidence.raw_text,
                    }
                    for field, evidence in result.field_evidence.items()
                ],
                hide_index=True,
                width="stretch",
            )


def _append_assistant_message(
    history: list[dict[str, Any]],
    content: str,
    *,
    citations: list[dict[str, str]] | None = None,
    extraction: DisputeDocumentExtraction | None = None,
) -> None:
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if citations:
        message["citations"] = citations
    if extraction is not None:
        message["extraction"] = extraction
    history.append(message)
    _render_chat_message(message)


def _local_assistant_workflow(settings: ApplicationSettings) -> None:
    """Run the model-driven assistant with process-local intake state."""
    st.header("ONR / IDR Assistant")
    st.write(
        "Ask a general process question, or tell me you want to process a claim."
    )
    st.caption(
        "The model selects grounded case, Knowledge Base, and claim-intake tools. "
        "Claim documents must be PDFs identified as ONR or IDR."
    )

    history = st.session_state.setdefault(
        "assistant_chat_history",
        [
            {
                "role": "assistant",
                "content": (
                    "How can I help? Ask me about the ONR/IDR process, or say "
                    "**I want to process a claim** and I'll request the PDF."
                ),
            }
        ],
    )
    for message in history:
        _render_chat_message(message)

    session_id = st.session_state.setdefault(
        "local_claim_intake_session_id",
        str(uuid4()),
    )
    expected = st.session_state.get(
        "local_claim_intake_expected_input",
        ClaimExpectedInput.MESSAGE.value,
    )

    if (
        st.session_state.get("assistant_awaiting_pdf", False)
        or expected == ClaimExpectedInput.PDF.value
    ):
        with st.container(border=True):
            st.subheader("Upload the claim PDF")
            uploaded_file = st.file_uploader(
                "ONR or IDR document",
                type=["pdf"],
                key="assistant_claim_pdf",
                help="Unsupported or unrelated documents will not be processed.",
            )
            process_pdf = st.button(
                "Process claim document",
                type="primary",
                disabled=uploaded_file is None,
                key="assistant_process_pdf",
            )
        if process_pdf and uploaded_file is not None:
            try:
                with st.spinner(
                    "Reading, identifying, extracting, and summarizing the PDF..."
                ):
                    document = _claim_intake_upload_service(settings).upload(
                        session_id,
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                    )
                    response = _local_claim_intake_agent(settings).handle(
                        session_id,
                        ClaimIntakeRequest(
                            action=ClaimIntakeAction.DOCUMENT_UPLOADED,
                            document=document,
                        ),
                    )
                history.append({"role": "user", "content": uploaded_file.name})
                _append_claim_response(
                    history,
                    response,
                    expected_input_state_key="local_claim_intake_expected_input",
                )
                st.session_state["assistant_awaiting_pdf"] = (
                    response.expected_input is ClaimExpectedInput.PDF
                )
                st.rerun()
            except Exception as error:
                _show_error("Claim document processing", error)

    if expected == ClaimExpectedInput.SUBMISSION_CONFIRMATION.value:
        confirm, cancel = st.columns(2)
        if confirm.button(
            "Submit claim",
            type="primary",
            key="local_claim_submit",
        ):
            idempotency_key = st.session_state.setdefault(
                "local_claim_submission_idempotency_key",
                str(uuid4()),
            )
            try:
                with st.spinner("Submitting the reviewed claim..."):
                    response = _local_claim_intake_agent(settings).handle(
                        session_id,
                        ClaimIntakeRequest(
                            action=ClaimIntakeAction.CONFIRM_SUBMISSION,
                            confirmation=True,
                            idempotency_key=idempotency_key,
                        ),
                    )
                history.append({"role": "user", "content": "Submit claim"})
                _append_claim_response(
                    history,
                    response,
                    expected_input_state_key="local_claim_intake_expected_input",
                )
                st.rerun()
            except Exception as error:
                _show_error("Claim submission", error)
        if cancel.button("Cancel intake", key="local_claim_cancel"):
            try:
                response = _local_claim_intake_agent(settings).handle(
                    session_id,
                    ClaimIntakeRequest(action=ClaimIntakeAction.CANCEL),
                )
                history.append({"role": "user", "content": "Cancel intake"})
                _append_claim_response(
                    history,
                    response,
                    expected_input_state_key="local_claim_intake_expected_input",
                )
                st.session_state["assistant_awaiting_pdf"] = False
                st.rerun()
            except Exception as error:
                _show_error("Claim intake cancellation", error)

    question = st.chat_input(
        "Ask a question or say you want to process a claim",
        key="assistant_chat_input",
    )
    if not question:
        return

    user_message = {"role": "user", "content": question}
    history.append(user_message)
    _render_chat_message(user_message)

    try:
        with st.spinner("The assistant is selecting and running grounded tools..."):
            response = _local_claim_intake_agent(settings).handle(
                session_id,
                ClaimIntakeRequest(
                    action=ClaimIntakeAction.MESSAGE,
                    message=question,
                ),
            )
        _append_claim_response(
            history,
            response,
            expected_input_state_key="local_claim_intake_expected_input",
        )
        st.session_state["assistant_awaiting_pdf"] = (
            response.expected_input is ClaimExpectedInput.PDF
        )
        if response.expected_input is ClaimExpectedInput.PDF:
            st.session_state.pop("local_claim_submission_idempotency_key", None)
        st.rerun()
    except ConfigurationError as error:
        st.error(f"Assistant request failed: {error}")
        st.info(
            "Restart the local app with its deployed Terraform configuration:"
        )
        st.code(
            "powershell -NoProfile -ExecutionPolicy Bypass -File "
            ".\\scripts\\run-local-app.ps1",
            language="powershell",
        )
    except Exception as error:
        _show_error("Assistant request", error)


def _append_claim_response(
    history: list[dict[str, Any]],
    response: ClaimIntakeResponse,
    *,
    expected_input_state_key: str = "claim_intake_expected_input",
) -> None:
    message: dict[str, Any] = {
        "role": "assistant",
        "content": response.message,
        "claim_response": response,
        "citations": [citation.model_dump() for citation in response.citations],
    }
    history.append(message)
    st.session_state[expected_input_state_key] = response.expected_input.value


def _remote_claim_intake_workflow(settings: ApplicationSettings) -> None:
    """Render a thin client over the conversational AgentCore endpoint."""
    st.header("ONR / IDR Assistant")
    st.caption(
        "Conversation, document review, submission, summaries, and next actions "
        "are orchestrated by the dedicated AgentCore claim-intake runtime."
    )
    session_id = st.session_state.setdefault(
        "claim_intake_runtime_session_id",
        str(uuid4()),
    )
    history = st.session_state.setdefault("remote_claim_intake_history", [])
    client = _claim_intake_agent(settings)
    if not history:
        try:
            response = client.invoke(
                ClaimIntakeRequest(action=ClaimIntakeAction.START),
                runtime_session_id=session_id,
            )
            _append_claim_response(history, response)
        except Exception as error:
            _show_error("Claim-intake AgentCore startup", error)
            return

    for message in history:
        _render_chat_message(message)

    expected = st.session_state.get(
        "claim_intake_expected_input",
        ClaimExpectedInput.MESSAGE.value,
    )
    if expected == ClaimExpectedInput.PDF.value:
        with st.container(border=True):
            uploaded_file = st.file_uploader(
                "Upload ONR or IDR PDF",
                type=["pdf"],
                key="remote_claim_intake_pdf",
            )
            process_pdf = st.button(
                "Extract and summarize",
                type="primary",
                disabled=uploaded_file is None,
                key="remote_claim_intake_process",
            )
        if process_pdf and uploaded_file is not None:
            try:
                with st.spinner("Uploading and processing the claim document..."):
                    document = _claim_intake_upload_service(settings).upload(
                        session_id,
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                    )
                    response = client.invoke(
                        ClaimIntakeRequest(
                            action=ClaimIntakeAction.DOCUMENT_UPLOADED,
                            document=document,
                        ),
                        runtime_session_id=session_id,
                    )
                history.append({"role": "user", "content": uploaded_file.name})
                _append_claim_response(history, response)
                st.rerun()
            except Exception as error:
                _show_error("Remote claim document processing", error)

    if expected == ClaimExpectedInput.SUBMISSION_CONFIRMATION.value:
        confirm, cancel = st.columns(2)
        if confirm.button(
            "Submit claim",
            type="primary",
            key="remote_claim_submit",
        ):
            idempotency_key = st.session_state.setdefault(
                "claim_submission_idempotency_key",
                str(uuid4()),
            )
            try:
                with st.spinner("Submitting the reviewed claim..."):
                    response = client.invoke(
                        ClaimIntakeRequest(
                            action=ClaimIntakeAction.CONFIRM_SUBMISSION,
                            confirmation=True,
                            idempotency_key=idempotency_key,
                        ),
                        runtime_session_id=session_id,
                    )
                history.append({"role": "user", "content": "Submit claim"})
                _append_claim_response(history, response)
                st.rerun()
            except Exception as error:
                _show_error("Claim submission", error)
        if cancel.button("Cancel intake", key="remote_claim_cancel"):
            try:
                response = client.invoke(
                    ClaimIntakeRequest(action=ClaimIntakeAction.CANCEL),
                    runtime_session_id=session_id,
                )
                history.append({"role": "user", "content": "Cancel intake"})
                _append_claim_response(history, response)
                st.rerun()
            except Exception as error:
                _show_error("Claim intake cancellation", error)

    question = st.chat_input(
        "Ask a question or tell me you want to process a claim",
        key="remote_claim_intake_chat_input",
    )
    if question:
        try:
            history.append({"role": "user", "content": question})
            with st.spinner("AgentCore is working..."):
                response = client.invoke(
                    ClaimIntakeRequest(
                        action=ClaimIntakeAction.MESSAGE,
                        message=question,
                    ),
                    runtime_session_id=session_id,
                )
            _append_claim_response(history, response)
            st.rerun()
        except Exception as error:
            _show_error("Claim-intake conversation", error)


def _assistant_workflow(settings: ApplicationSettings) -> None:
    """Prefer remote AgentCore intake, with the local demo as a fallback."""
    if (
        settings.claim_agentcore_runtime_arn is not None
        and settings.claim_agentcore_endpoint_name is not None
    ):
        _remote_claim_intake_workflow(settings)
        return
    _local_assistant_workflow(settings)


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
        "Assistant": _assistant_workflow,
        "Case lookup": _lookup_workflow,
        "Submit a case": _submission_workflow,
        "Upload a document": _upload_workflow,
        "Extract ONR / IDR PDF": _extraction_workflow,
        "Case summary": _summary_workflow,
        "Case chat": _chat_workflow,
    }
    workflows[selected](settings)
