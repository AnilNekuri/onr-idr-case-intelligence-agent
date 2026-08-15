"""Command-line entry point for the real AWS Step 9 phase checkpoint."""

import argparse
import json
import os
from datetime import date

from app.config import ApplicationSettings, CaseRepositoryKind, ConfigurationError
from app.repositories import create_case_repository, create_document_repository
from app.services import CaseService, DocumentService
from app.workflows import run_phase_checkpoint


def main() -> int:
    """Run the explicitly authorized development AWS checkpoint."""
    parser = argparse.ArgumentParser(
        description="Run the deterministic Step 9 checkpoint against development AWS."
    )
    parser.add_argument(
        "--confirm-development-aws",
        action="store_true",
        help="Confirm that writing one synthetic case and PDF is intentional.",
    )
    args = parser.parse_args()

    if not args.confirm_development_aws or os.getenv("RUN_AWS_INTEGRATION") != "1":
        parser.error("Pass --confirm-development-aws and set RUN_AWS_INTEGRATION=1")

    try:
        settings = ApplicationSettings.from_environment()
        if settings.case_repository is not CaseRepositoryKind.DYNAMODB:
            raise ConfigurationError(
                "The AWS checkpoint requires CASE_REPOSITORY=dynamodb"
            )
        case_repository = create_case_repository(settings)
        document_repository = create_document_repository(settings)
    except ConfigurationError as error:
        parser.error(str(error))

    result = run_phase_checkpoint(
        CaseService(case_repository),
        DocumentService(document_repository),
        current_date=date.today(),
    )
    print(json.dumps(result.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
