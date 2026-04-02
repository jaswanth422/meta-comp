import pytest

from support_ops_env.models import ActionType, SupportOpsAction
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
async def test_episode_terminates_on_submit_resolution() -> None:
    env = SupportOpsEnv(task_id="password_reset_triage")
    await env.reset()
    await env.step(SupportOpsAction(action_type=ActionType.OPEN_TICKET, ticket_id="T-1001"))
    result = await env.step(
        SupportOpsAction(action_type=ActionType.SUBMIT_RESOLUTION, resolution_code="password_reset_guided")
    )

    assert result.done is True
