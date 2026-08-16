"""Tests for general Knowledge Base question answering."""

from app.services import KnowledgeChatService
from app.tools import KnowledgeSearchResult


class StubLanguageModel:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.prompt = prompt
        return self.response


class StubKnowledgeRetriever:
    def __init__(self, results: tuple[KnowledgeSearchResult, ...]) -> None:
        self.results = results
        self.question: str | None = None

    def retrieve(
        self,
        question: str,
        *,
        number_of_results: int = 5,
    ) -> tuple[KnowledgeSearchResult, ...]:
        self.question = question
        return self.results


def test_general_answer_is_grounded_in_retrieval_and_returns_citations() -> None:
    model = StubLanguageModel("The negotiation period is 30 business days [KB-2].")
    retriever = StubKnowledgeRetriever(
        (
            KnowledgeSearchResult(
                guidance="The open negotiation period lasts 30 business days.",
                source_id="KB-2",
                document_location="s3://knowledge/onr.md",
                score=0.98,
            ),
        )
    )
    service = KnowledgeChatService(model, retriever)

    result = service.answer("How long is open negotiation?")

    assert result.answer.endswith("[KB-2].")
    assert result.citations[0].source_id == "KB-2"
    assert model.prompt is not None
    assert "The open negotiation period lasts 30 business days." in model.prompt
    assert retriever.question == "How long is open negotiation?"


def test_no_retrieval_results_returns_safe_message_without_generation() -> None:
    model = StubLanguageModel("must not be used")
    service = KnowledgeChatService(model, StubKnowledgeRetriever(()))

    result = service.answer("Unknown topic")

    assert "couldn't find supporting" in result.answer
    assert result.citations == ()
    assert model.prompt is None
