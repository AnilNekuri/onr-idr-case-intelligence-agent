"""Contract check for the claim-intake AgentCore SDK entry point."""

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


class SyntheticAgentCoreApp:
    def __init__(self) -> None:
        self.registered = None

    def entrypoint(self, function):  # type: ignore[no-untyped-def]
        self.registered = function
        return function

    def run(self) -> None:
        raise AssertionError("run is not called while importing the entry point")


def test_delegates_payload_with_context_session_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = ModuleType("bedrock_agentcore")
    runtime = ModuleType("bedrock_agentcore.runtime")
    runtime.BedrockAgentCoreApp = SyntheticAgentCoreApp  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "bedrock_agentcore", package)
    monkeypatch.setitem(sys.modules, "bedrock_agentcore.runtime", runtime)
    sys.modules.pop("claim_intake_agentcore_main", None)

    entrypoint = importlib.import_module("claim_intake_agentcore_main")
    expected = {"state": "WELCOME", "message": "How can I help?"}
    received: dict[str, object] = {}

    def invoke(payload, *, runtime_session_id):  # type: ignore[no-untyped-def]
        received["payload"] = payload
        received["session_id"] = runtime_session_id
        return expected

    monkeypatch.setattr(entrypoint, "invoke_claim_intake_agentcore", invoke)
    context = SimpleNamespace(
        session_id="12345678-1234-1234-1234-123456789012"
    )

    assert entrypoint.invoke({"action": "START"}, context) == expected
    assert received == {
        "payload": {"action": "START"},
        "session_id": "12345678-1234-1234-1234-123456789012",
    }
