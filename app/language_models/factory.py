"""Composition helper for the configured language-model provider."""

from app.config import ApplicationSettings, ConfigurationError
from app.language_models.language_model import LanguageModel
from app.language_models.mantle import BedrockMantleLanguageModel


def create_language_model(settings: ApplicationSettings) -> LanguageModel:
    """Construct the configured Amazon Bedrock Mantle language model."""
    if settings.bedrock_model_id is None:
        raise ConfigurationError(
            "BEDROCK_MODEL_ID is required to create the language model"
        )
    return BedrockMantleLanguageModel(
        settings.bedrock_model_id,
        region_name=settings.aws_region,
        profile_name=settings.aws_profile,
    )
