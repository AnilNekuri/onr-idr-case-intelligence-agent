"""Local JSON-file implementation of the case repository contract."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.models import Case
from app.repositories.case_repository import RepositoryDataError


class JsonCaseRepository:
    """Store validated cases in a JSON array on the local filesystem."""

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def get(self, case_id: str) -> Case | None:
        """Return the requested case, or ``None`` if its ID is not stored."""
        return next(
            (case for case in self._load_cases() if case.case_id == case_id),
            None,
        )

    def save(self, case: Case) -> None:
        """Add a case or replace the stored case with the same ID."""
        cases = self._load_cases()
        for index, stored_case in enumerate(cases):
            if stored_case.case_id == case.case_id:
                cases[index] = case
                break
        else:
            cases.append(case)

        self._write_cases(cases)

    def _load_cases(self) -> list[Case]:
        if not self._file_path.exists():
            return []

        try:
            raw_data: Any = json.loads(self._file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise RepositoryDataError(
                f"Malformed JSON in case repository: {self._file_path}"
            ) from error

        if not isinstance(raw_data, list):
            raise RepositoryDataError(
                f"Case repository must contain a JSON array: {self._file_path}"
            )

        try:
            return [Case.model_validate(item) for item in raw_data]
        except ValidationError as error:
            raise RepositoryDataError(
                f"Invalid case data in repository: {self._file_path}"
            ) from error

    def _write_cases(self, cases: list[Case]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._file_path.with_suffix(self._file_path.suffix + ".tmp")
        serialized = json.dumps(
            [case.model_dump(mode="json") for case in cases],
            indent=2,
        )
        temporary_path.write_text(serialized + "\n", encoding="utf-8")
        temporary_path.replace(self._file_path)
