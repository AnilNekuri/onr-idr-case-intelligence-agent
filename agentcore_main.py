"""Amazon Bedrock AgentCore Runtime entry point."""

from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from app.agentcore_adapter import invoke_agentcore

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict[str, Any]) -> dict[str, object]:
    """Adapt an AgentCore invocation to the local grounded-agent contract."""
    return invoke_agentcore(payload)


if __name__ == "__main__":
    app.run()
