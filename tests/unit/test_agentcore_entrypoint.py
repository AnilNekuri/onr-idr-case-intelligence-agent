"""Contract check for the AgentCore SDK entry point module."""

import importlib
import sys
from types import ModuleType

import pytest


class _SyntheticAgentCoreApp:
    def __init__(self) -> None:
        self.registered = None

    def entrypoint(self, function):  # type: ignore[no-untyped-def]
        self.registered = function
        return function

    def run(self) -> None:
        raise AssertionError("run is not called while importing the entry point")


def test_registers_sdk_entrypoint_and_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = ModuleType("bedrock_agentcore")
    runtime = ModuleType("bedrock_agentcore.runtime")
    runtime.BedrockAgentCoreApp = _SyntheticAgentCoreApp  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "bedrock_agentcore", package)
    monkeypatch.setitem(sys.modules, "bedrock_agentcore.runtime", runtime)
    sys.modules.pop("agentcore_main", None)

    entrypoint = importlib.import_module("agentcore_main")
    expected = {"case_id": "CASE-1001", "generated_answer": "ok"}
    monkeypatch.setattr(entrypoint, "invoke_agentcore", lambda _payload: expected)

    assert entrypoint.app.registered is entrypoint.invoke
    assert entrypoint.invoke({"case_id": "CASE-1001", "prompt": "hello"}) == expected
