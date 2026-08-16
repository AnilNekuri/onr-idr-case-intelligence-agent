"""Composition helpers for configured application services."""

from app.config import (
    ApplicationSettings,
    BedrockExtractionApi,
    ConfigurationError,
)
from app.language_models import BedrockMantleLanguageModel, create_language_model
from app.repositories import (
    InMemoryClaimIntakeRepository,
    create_case_repository,
    create_claim_intake_repository,
    create_document_repository,
)
from app.services.bedrock_extraction_service import (
    BedrockExtractionService,
    DisputeFieldExtractor,
)
from app.services.case_document_service import CaseDocumentService
from app.services.case_service import CaseService
from app.services.case_summary_service import CaseSummaryService
from app.services.claim_intake_upload_service import ClaimIntakeUploadService
from app.services.conversational_claim_agent import ConversationalClaimAgent
from app.services.document_extraction_service import DocumentExtractionService
from app.services.document_service import DocumentService
from app.services.document_summary_service import DocumentSummaryService
from app.services.grounded_case_agent import GroundedCaseAgent
from app.services.knowledge_chat_service import KnowledgeChatService
from app.services.mantle_extraction_service import MantleExtractionService
from app.services.textract_service import TextractService
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


def create_claim_intake_upload_service(
    settings: ApplicationSettings,
) -> ClaimIntakeUploadService:
    """Assemble temporary S3 upload for the remote intake runtime."""
    return ClaimIntakeUploadService(
        DocumentService(create_document_repository(settings))
    )


def create_case_summary_service(
    settings: ApplicationSettings,
) -> CaseSummaryService:
    """Assemble fact-only case summarization."""
    return CaseSummaryService(create_language_model(settings))


def create_document_extraction_service(
    settings: ApplicationSettings,
) -> DocumentExtractionService:
    """Assemble S3 -> Textract -> Bedrock document extraction."""
    if settings.s3_case_documents_bucket is None:
        raise ConfigurationError(
            "S3_CASE_DOCUMENTS_BUCKET is required for document extraction"
        )
    extractor: DisputeFieldExtractor
    if settings.bedrock_extraction_api is BedrockExtractionApi.MANTLE:
        model_id = settings.bedrock_extraction_model_id or settings.bedrock_model_id
        if model_id is None:
            raise ConfigurationError(
                "BEDROCK_EXTRACTION_MODEL_ID or BEDROCK_MODEL_ID is required for "
                "Mantle document extraction"
            )
        extractor = MantleExtractionService(
            BedrockMantleLanguageModel(
                model_id,
                region_name=settings.aws_region,
                profile_name=settings.aws_profile,
                max_output_tokens=2048,
            )
        )
    else:
        model_id = settings.bedrock_extraction_model_id
        if model_id is None:
            raise ConfigurationError(
                "BEDROCK_EXTRACTION_MODEL_ID is required when "
                "BEDROCK_EXTRACTION_API=runtime"
            )
        extractor = BedrockExtractionService(
            model_id,
            region_name=settings.aws_region,
            profile_name=settings.aws_profile,
        )
    return DocumentExtractionService(
        create_document_repository(settings),
        TextractService(
            settings.s3_case_documents_bucket,
            region_name=settings.aws_region,
            profile_name=settings.aws_profile,
        ),
        extractor,
    )


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


def create_knowledge_chat_service(
    settings: ApplicationSettings,
) -> KnowledgeChatService:
    """Assemble general Knowledge Base question answering."""
    return KnowledgeChatService(
        create_language_model(settings),
        create_knowledge_retriever(settings),
    )


def create_conversational_claim_agent(
    settings: ApplicationSettings,
) -> ConversationalClaimAgent:
    """Assemble the dedicated conversational claim-intake runtime."""
    model = create_language_model(settings)
    return ConversationalClaimAgent(
        create_claim_intake_repository(settings),
        create_document_extraction_service(settings),
        DocumentSummaryService(model),
        create_case_service(settings),
        CaseSummaryService(model),
        KnowledgeChatService(model, create_knowledge_retriever(settings)),
        model,
    )


def create_local_conversational_claim_agent(
    settings: ApplicationSettings,
) -> ConversationalClaimAgent:
    """Assemble the full intake workflow with process-local session state."""
    model = create_language_model(settings)
    return ConversationalClaimAgent(
        InMemoryClaimIntakeRepository(),
        create_document_extraction_service(settings),
        DocumentSummaryService(model),
        create_case_service(settings),
        CaseSummaryService(model),
        KnowledgeChatService(model, create_knowledge_retriever(settings)),
        model,
    )
