"""Opt-in paid integration test for a real Amazon Bedrock Mantle model."""

import os

import pytest

from app.config import ApplicationSettings
from app.language_models import create_language_model

pytestmark = pytest.mark.integration


def test_real_bedrock_text_generation() -> None:
    if os.getenv("RUN_AWS_INTEGRATION") != "1":
        pytest.skip("Set RUN_AWS_INTEGRATION=1 to allow AWS calls")
    if os.getenv("RUN_BEDROCK_INTEGRATION") != "1":
        pytest.skip("Set RUN_BEDROCK_INTEGRATION=1 to allow a paid model call")

    settings = ApplicationSettings.from_environment()
    if settings.bedrock_model_id is None:
        pytest.skip("Set BEDROCK_MODEL_ID to a model from Mantle's /v1/models")

    response = create_language_model(settings).generate(
        "Reply with a brief sentence stating that this is a synthetic test."
    )

    assert response.strip()
