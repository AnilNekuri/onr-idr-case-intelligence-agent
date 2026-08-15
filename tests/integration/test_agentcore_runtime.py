"""Opt-in deployment, observability, and paid AgentCore invocation checks."""

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import boto3  # type: ignore[import-untyped]
import pytest

from app.config import ApplicationSettings
from app.models import Case

pytestmark = pytest.mark.integration


def _required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"Set {name} from the corresponding Terraform output")
    return value


def _session() -> Any:
    settings = ApplicationSettings.from_environment()
    return boto3.Session(
        profile_name=settings.aws_profile,
        region_name=settings.aws_region,
    )


def test_agentcore_runtime_and_endpoint_are_ready() -> None:
    if os.getenv("RUN_AGENTCORE_INTEGRATION") != "1":
        pytest.skip("Set RUN_AGENTCORE_INTEGRATION=1 to inspect the deployment")

    runtime_id = _required_environment("AGENTCORE_RUNTIME_ID")
    runtime_arn = _required_environment("AGENTCORE_RUNTIME_ARN")
    endpoint_name = _required_environment("AGENTCORE_ENDPOINT_NAME")
    log_group_name = _required_environment("AGENTCORE_LOG_GROUP_NAME")

    session = _session()
    control = session.client("bedrock-agentcore-control")
    runtime = control.get_agent_runtime(agentRuntimeId=runtime_id)
    endpoint = control.get_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        endpointName=endpoint_name,
    )

    assert runtime["agentRuntimeArn"] == runtime_arn
    assert runtime["status"] == "READY"
    assert runtime["networkConfiguration"]["networkMode"] == "PUBLIC"
    assert runtime["protocolConfiguration"]["serverProtocol"] == "HTTP"
    assert endpoint["status"] == "READY"
    assert endpoint["name"] == endpoint_name

    logs = session.client("logs").describe_log_groups(
        logGroupNamePrefix=log_group_name,
    )
    assert any(
        item["logGroupName"] == log_group_name
        for item in logs.get("logGroups", [])
    )


def test_agentcore_transaction_search_is_enabled() -> None:
    if os.getenv("RUN_AGENTCORE_OBSERVABILITY_INTEGRATION") != "1":
        pytest.skip(
            "Set RUN_AGENTCORE_OBSERVABILITY_INTEGRATION=1 when Terraform owns "
            "Transaction Search"
        )

    xray = _session().client("xray")
    destination = xray.get_trace_segment_destination()
    indexing = xray.get_indexing_rules()

    assert destination["Destination"] == "CloudWatchLogs"
    default_rule = next(
        item for item in indexing["IndexingRules"] if item["Name"] == "Default"
    )
    assert default_rule["Rule"]["Probabilistic"]["DesiredSamplingPercentage"] > 0


def test_agentcore_invocation_uses_case_retrieval_and_mantle() -> None:
    if os.getenv("RUN_AGENTCORE_INVOCATION_INTEGRATION") != "1":
        pytest.skip(
            "Set RUN_AGENTCORE_INVOCATION_INTEGRATION=1 to allow paid retrieval "
            "and Mantle inference"
        )

    runtime_arn = _required_environment("AGENTCORE_RUNTIME_ARN")
    endpoint_name = _required_environment("AGENTCORE_ENDPOINT_NAME")
    table_name = _required_environment("DYNAMODB_CASE_TABLE")
    session = _session()
    table = session.resource("dynamodb").Table(table_name)

    source = json.loads(Path("data/cases.json").read_text(encoding="utf-8"))[0]
    case_id = f"AGENTCORE-INTEGRATION-{uuid4()}"
    source["case_id"] = case_id
    case = Case.model_validate(source)
    table.put_item(Item=case.model_dump(mode="json"))

    try:
        response = session.client("bedrock-agentcore").invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            qualifier=endpoint_name,
            runtimeSessionId=str(uuid4()),
            payload=json.dumps(
                {
                    "case_id": case_id,
                    "question": "What should happen next?",
                    "current_date": "2026-08-14",
                }
            ).encode("utf-8"),
        )
        body = response["response"]
        raw = body.read() if hasattr(body, "read") else b"".join(body)
        result = json.loads(raw.decode("utf-8"))

        assert result["case_id"] == case_id
        assert result["authoritative_facts"]["case_id"] == case_id
        assert result["process_guidance_required"] is True
        assert result["process_guidance"]
        assert result["citations"]
        assert result["generated_answer"]
    finally:
        table.delete_item(Key={"case_id": case_id})
