"""Command-line entry point for one configured Step 13 agent question."""

import argparse
import json
from datetime import date

from app.config import ApplicationSettings
from app.services import create_grounded_case_agent


def iso_date(value: str) -> date:
    """Parse an ISO date for argparse with a concise validation message."""
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("use YYYY-MM-DD") from error


def main() -> int:
    """Run one grounded question and print its inspectable JSON response."""
    parser = argparse.ArgumentParser(
        description="Call the configured GroundedCaseAgent once.",
    )
    parser.add_argument("--case-id", default="CASE-1001")
    parser.add_argument(
        "--question",
        default="What should happen next?",
    )
    parser.add_argument(
        "--current-date",
        type=iso_date,
        default=date.today(),
        help="Deadline comparison date in YYYY-MM-DD format (default: today).",
    )
    args = parser.parse_args()

    settings = ApplicationSettings.from_environment()
    agent = create_grounded_case_agent(settings)
    answer = agent.answer(
        case_id=args.case_id,
        question=args.question,
        current_date=args.current_date,
    )
    print(json.dumps(answer.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
