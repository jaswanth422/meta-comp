from __future__ import annotations

from support_ops_env.models import ActionType, SupportOpsAction, SupportOpsState, TaskSpec


def compute_step_reward(
    state: SupportOpsState,
    task: TaskSpec,
    action: SupportOpsAction,
    action_valid: bool,
) -> tuple[float, dict[str, float]]:
    reward = 0.0
    components: dict[str, float] = {}
    expected = task.expected
    ticket = state.active_ticket

    if not action_valid:
        components["invalid_action"] = -0.02
        reward -= 0.02
        return reward, components

    if action.action_type == ActionType.OPEN_TICKET and "opened_ticket" not in state.achieved_milestones:
        reward += 0.05
        components["opened_ticket"] = 0.05

    if (
        action.action_type == ActionType.READ_KB_ARTICLE
        and action.article_id in expected.required_kb_article_ids
        and "read_required_kb" not in state.achieved_milestones
    ):
        reward += 0.10
        components["read_required_kb"] = 0.10

    if (
        action.action_type == ActionType.SET_PRIORITY
        and ticket
        and ticket.priority == expected.required_priority
        and "set_correct_priority" not in state.achieved_milestones
    ):
        reward += 0.05
        components["set_correct_priority"] = 0.05

    if action.action_type == ActionType.ADD_TAG and action.tag in expected.required_tags:
        tag_key = f"tag_{action.tag}"
        if tag_key not in state.achieved_milestones:
            reward += 0.05
            components[tag_key] = 0.05

    if (
        action.action_type == ActionType.ASSIGN_TEAM
        and ticket
        and expected.required_team
        and ticket.assigned_team == expected.required_team
        and "assigned_correct_team" not in state.achieved_milestones
    ):
        reward += 0.10
        components["assigned_correct_team"] = 0.10

    if (
        action.action_type == ActionType.REQUEST_ESCALATION
        and action.team == expected.required_escalation_team
        and "escalated_correctly" not in state.achieved_milestones
    ):
        reward += 0.10
        components["escalated_correctly"] = 0.10

    if action.action_type == ActionType.DRAFT_REPLY and state.draft_reply.body:
        text = state.draft_reply.body.lower()
        required_hits = sum(1 for phrase in expected.required_reply_phrases if phrase in text)
        if required_hits > 0 and "partial_reply_quality" not in state.achieved_milestones:
            partial = min(0.10, required_hits * 0.03)
            reward += partial
            components["partial_reply_quality"] = partial
        if any(phrase in text for phrase in expected.forbidden_reply_phrases):
            reward -= 0.10
            components["unsafe_reply"] = -0.10

    if action.action_type == ActionType.CLOSE_TICKET and task.task_id == "account_compromise_signals":
        reward -= 0.10
        components["premature_close"] = -0.10

    if state.step_count >= state.max_steps and not state.done:
        reward -= 0.02
        components["max_steps_reached"] = -0.02

    return reward, components
