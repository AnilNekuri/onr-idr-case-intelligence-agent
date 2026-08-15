"""Composition helpers for configured application services."""

from app.config import ApplicationSettings
from app.language_models import create_language_model
from app.repositories import create_case_repository, create_document_repository
from app.services.case_document_service import CaseDocumentService
from app.services.case_service import CaseService
from app.services.case_summary_service import CaseSummaryService
from app.services.document_service import DocumentService
from app.services.grounded_case_agent import GroundedCaseAgent
from app.tools import create_knowledge_retriever


def create_case_service(settings: ApplicationSettings) -> CaseService:
    """Assemble storage-independent case use cases."""
    return CaseService(create_case_repository(settings))


def create_case_document_service(
    settings: ApplicationSettings,
) -> CaseDocumentService:
    """Assemble the document upload and authoritative-case update workflow."""
    return CaseDocumentService(
        create_case_service(settings),
        DocumentService(create_document_repository(settings)),
    )


def create_case_summary_service(
    settings: ApplicationSettings,
) -> CaseSummaryService:
    """Assemble fact-only case summarization."""
    return CaseSummaryService(create_language_model(settings))


def create_grounded_case_agent(settings: ApplicationSettings) -> GroundedCaseAgent:
    """Assemble the case tools, Knowledge Base retrieval, and Mantle model."""
    repository = create_case_repository(settings)
    language_model = create_language_model(settings)
    knowledge_retriever = create_knowledge_retriever(settings)
    return GroundedCaseAgent(
        repository,
        language_model,
        knowledge_retriever,
    )
