import pytest

from support_ops_env.graders import grade_task
from support_ops_env.models import ActionType, SupportOpsAction
from support_ops_env.server.support_ops_environment import SupportOpsEnv


@pytest.mark.asyncio
async def test_perfect_password_flow_scores_high() -> None:
    env = SupportOpsEnv(task_id="password_reset_triage")
    await env.reset()
    await env.step(SupportOpsAction(action_type=ActionType.VIEW_QUEUE))
    await env.step(SupportOpsAction(action_type=ActionType.OPEN_TICKET, ticket_id="T-1001"))
    await env.step(SupportOpsAction(action_type=ActionType.READ_KB_ARTICLE, article_id="KB-RESET-01"))
    await env.step(SupportOpsAction(action_type=ActionType.SET_PRIORITY, priority="high"))
    await env.step(SupportOpsAction(action_type=ActionType.ADD_TAG, tag="auth"))
    await env.step(SupportOpsAction(action_type=ActionType.ADD_TAG, tag="login"))
    await env.step(SupportOpsAction(action_type=ActionType.ASSIGN_TEAM, team="support_l1"))
    await env.step(
        SupportOpsAction(
            action_type=ActionType.DRAFT_REPLY,
            message=(
                "Please verify your identity and complete password reset. "
                "Let us know once complete."
            ),
        )
    )
    await env.step(
        SupportOpsAction(action_type=ActionType.SUBMIT_RESOLUTION, resolution_code="password_reset_guided")
    )
    await env.step(SupportOpsAction(action_type=ActionType.CLOSE_TICKET))

    state = await env.state()
    task = env.task_bank["password_reset_triage"]
    score = grade_task(state, task)
    assert 0.8 <= score <= 1.0


@pytest.mark.asyncio
async def test_wrong_flow_scores_low() -> None:
    env = SupportOpsEnv(task_id="account_compromise_signals")
    await env.reset()
    await env.step(SupportOpsAction(action_type=ActionType.OPEN_TICKET, ticket_id="T-3307"))
    await env.step(SupportOpsAction(action_type=ActionType.SET_PRIORITY, priority="low"))
    await env.step(SupportOpsAction(action_type=ActionType.CLOSE_TICKET))

    state = await env.state()
    task = env.task_bank["account_compromise_signals"]
    score = grade_task(state, task)
    assert 0.0 <= score <= 0.4
