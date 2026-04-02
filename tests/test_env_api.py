import pytest
from fastapi.testclient import TestClient

from support_ops_env.models import ActionType, SupportOpsAction
from support_ops_env.server.app import app
from support_ops_env.server.support_ops_environment import SupportOpsEnv


@pytest.mark.asyncio
async def test_reset_and_state_are_clean() -> None:
    env = SupportOpsEnv(task_id="password_reset_triage")
    result = await env.reset()
    state = await env.state()

    assert result.observation.task_id == "password_reset_triage"
    assert state.step_count == 0
    assert state.done is False
    assert state.active_ticket is None


@pytest.mark.asyncio
async def test_invalid_action_before_open_ticket() -> None:
    env = SupportOpsEnv(task_id="password_reset_triage")
    await env.reset()
    result = await env.step(SupportOpsAction(action_type=ActionType.SET_PRIORITY, priority="high"))

    assert result.observation.last_action_status == "error"
    assert result.reward < 0


@pytest.mark.asyncio
async def test_episode_terminates_on_submit_resolution_for_non_closing_task() -> None:
    env = SupportOpsEnv(task_id="billing_refund_policy")
    await env.reset()
    await env.step(SupportOpsAction(action_type=ActionType.OPEN_TICKET, ticket_id="T-2201"))
    result = await env.step(
        SupportOpsAction(action_type=ActionType.SUBMIT_RESOLUTION, resolution_code="prorated_refund_review")
    )

    assert result.done is True


def test_runtime_endpoints_expose_validation_metadata() -> None:
    client = TestClient(app)

    health = client.get("/health")
    metadata = client.get("/metadata")
    schema = client.get("/schema")
    mcp = client.post("/mcp", json={})

    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert metadata.status_code == 200
    assert metadata.json()["name"] == "support_ops_env"
    assert schema.status_code == 200
    assert "action" in schema.json()
    assert "observation" in schema.json()
    assert "state" in schema.json()
    assert mcp.status_code == 200
    assert mcp.json()["jsonrpc"] == "2.0"
