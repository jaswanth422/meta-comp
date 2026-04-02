import pytest

from support_ops_env.models import ActionType, SupportOpsAction
from support_ops_env.server.support_ops_environment import SupportOpsEnv


@pytest.mark.asyncio
async def test_positive_reward_for_correct_priority() -> None:
    env = SupportOpsEnv(task_id="password_reset_triage")
    await env.reset()
    await env.step(SupportOpsAction(action_type=ActionType.OPEN_TICKET, ticket_id="T-1001"))
    result = await env.step(SupportOpsAction(action_type=ActionType.SET_PRIORITY, priority="high"))
    assert result.reward > 0


@pytest.mark.asyncio
async def test_penalty_for_unsafe_reply() -> None:
    env = SupportOpsEnv(task_id="account_compromise_signals")
    await env.reset()
    await env.step(SupportOpsAction(action_type=ActionType.OPEN_TICKET, ticket_id="T-3307"))
    result = await env.step(
        SupportOpsAction(action_type=ActionType.DRAFT_REPLY, message="Here is a reset link, issue resolved and closed")
    )
    assert result.reward < 0


@pytest.mark.asyncio
async def test_exploit_attempt_repeat_tag_not_farmed() -> None:
    env = SupportOpsEnv(task_id="password_reset_triage")
    await env.reset()
    await env.step(SupportOpsAction(action_type=ActionType.OPEN_TICKET, ticket_id="T-1001"))
    first = await env.step(SupportOpsAction(action_type=ActionType.ADD_TAG, tag="auth"))
    second = await env.step(SupportOpsAction(action_type=ActionType.ADD_TAG, tag="auth"))

    assert first.reward > 0
    assert second.reward <= first.reward
