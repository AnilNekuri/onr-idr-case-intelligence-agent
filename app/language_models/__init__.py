"""Language-model contracts and concrete adapters."""

from app.language_models.bedrock import BedrockLanguageModel
from app.language_models.factory import create_language_model
from app.language_models.language_model import LanguageModel, LanguageModelError
from app.language_models.mantle import BedrockMantleLanguageModel

__all__ = [
    "BedrockLanguageModel",
    "BedrockMantleLanguageModel",
    "LanguageModel",
    "LanguageModelError",
    "create_language_model",
]
