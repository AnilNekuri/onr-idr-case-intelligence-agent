"""Safety and consistency checks for the process-guidance corpus."""

import json
import re
from datetime import date
from pathlib import Path

DATA_DIRECTORY = Path("data")
KNOWLEDGE_DIRECTORY = DATA_DIRECTORY / "knowledge"


def _front_matter(content: str) -> dict[str, str]:
    match = re.match(r"---\s*\n(?P<body>.*?)\n---\s*\n", content, re.DOTALL)
    assert match is not None

    metadata: dict[str, str] = {}
    for line in match.group("body").splitlines():
        key, separator, value = line.partition(":")
        assert separator
        metadata[key.strip()] = value.strip()
    return metadata


def test_knowledge_manifest_matches_safe_process_guidance_corpus() -> None:
    manifest = json.loads(
        (DATA_DIRECTORY / "knowledge_manifest.json").read_text(encoding="utf-8")
    )
    document_names = manifest["documents"]
    documents = sorted(KNOWLEDGE_DIRECTORY.glob("*.md"))

    assert manifest["schema_version"] == 1
    assert [document.name for document in documents] == sorted(document_names)

    document_ids: set[str] = set()
    for document in documents:
        content = document.read_text(encoding="utf-8")
        metadata = _front_matter(content)

        document_id = metadata["document_id"]
        assert re.fullmatch(r"KB-NSA-[0-9]{3}", document_id)
        assert document_id not in document_ids
        document_ids.add(document_id)

        assert metadata["authority"].startswith("synthesized_from_official_")
        date.fromisoformat(metadata["last_reviewed"])
        assert re.search(r"\bCASE-[0-9]+\b", content) is None

    questions = json.loads(
        (DATA_DIRECTORY / "knowledge_demo_questions.json").read_text(encoding="utf-8")
    )
    expected_document_ids = {
        document_id
        for question in questions
        for document_id in question["expected_document_ids"]
    }

    assert expected_document_ids <= document_ids
