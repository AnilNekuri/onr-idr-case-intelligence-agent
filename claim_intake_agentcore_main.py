"""Amazon Bedrock AgentCore entry point for conversational claim intake."""

from typing import Any, Protocol

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from app.claim_intake_agentcore_adapter import invoke_claim_intake_agentcore

app = BedrockAgentCoreApp()


class RuntimeContext(Protocol):
    """Subset of AgentCore request context used by this entry point."""

    session_id: str


@app.entrypoint
def invoke(
    payload: dict[str, Any],
    context: RuntimeContext,
) -> dict[str, object]:
    """Run one intake event in the caller's isolated runtime session."""
    return invoke_claim_intake_agentcore(
        payload,
        runtime_session_id=context.session_id,
    )


if __name__ == "__main__":
    app.run()
