from __future__ import annotations

from typing import Callable

from support_ops_env.models import SupportOpsState, TaskSpec


EPSILON = 1e-6


def clamp_score(value: float) -> float:
    # Competition validator requires scores to be strictly within (0, 1).
    return min(max(value, EPSILON), 1.0 - EPSILON)


def _contains_all(text: str, required: list[str]) -> bool:
    lowered = text.lower()
    return all(phrase.lower() in lowered for phrase in required)


def _contains_any(text: str, forbidden: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase.lower() in lowered for phrase in forbidden)


def grade_task_common(state: SupportOpsState, task: TaskSpec) -> float:
    score = 0.0
    expected = task.expected
    ticket = state.active_ticket
    if ticket is None:
        return clamp_score(0.0)

    if ticket.priority == expected.required_priority and expected.required_priority:
        score += 0.20

    route_ok = True
    if expected.required_team and ticket.assigned_team != expected.required_team:
        route_ok = False
    if expected.required_escalation_team and state.escalation_status != expected.required_escalation_team:
        route_ok = False
    if route_ok:
        score += 0.20

    tags = set(ticket.tags)
    if expected.required_tags.issubset(tags):
        score += 0.20

    reply = state.draft_reply.body
    reply_ok = _contains_all(reply, expected.required_reply_phrases)
    if reply_ok:
        score += 0.25

    safety_ok = not _contains_any(reply, expected.forbidden_reply_phrases)
    if task.task_id == "account_compromise_signals" and ticket.status == "closed":
        safety_ok = False
    if expected.require_internal_note and not state.internal_notes:
        safety_ok = False
    if safety_ok:
        score += 0.15

    return clamp_score(score)


def grade_password_reset_triage(state: SupportOpsState, task: TaskSpec) -> float:
    score = grade_task_common(state, task)
    expected = task.expected
    ticket = state.active_ticket
    if not ticket:
        return clamp_score(0.0)
    if expected.must_close and ticket.status != "closed":
        score -= 0.20
    if state.submitted_resolution_code != expected.required_resolution_code:
        score -= 0.20
    if not expected.required_kb_article_ids.issubset(state.visited_articles):
        score -= 0.10
    return clamp_score(score)


def grade_billing_refund_policy(state: SupportOpsState, task: TaskSpec) -> float:
    score = grade_task_common(state, task)
    expected = task.expected
    reply = state.draft_reply.body.lower()
    if "full refund" in reply:
        score -= 0.20
    if not expected.required_kb_article_ids.issubset(state.visited_articles):
        score -= 0.10
    return clamp_score(score)


def grade_account_compromise_signals(state: SupportOpsState, task: TaskSpec) -> float:
    score = grade_task_common(state, task)
    expected = task.expected
    ticket = state.active_ticket
    if not ticket:
        return clamp_score(0.0)
    if ticket.status == "closed":
        score -= 0.35
    if not expected.required_kb_article_ids.issubset(state.visited_articles):
        score -= 0.10
    if state.escalation_status != expected.required_escalation_team:
        score -= 0.10
    return clamp_score(score)


GRADERS: dict[str, Callable[[SupportOpsState, TaskSpec], float]] = {
    "password_reset_triage": grade_password_reset_triage,
    "billing_refund_policy": grade_billing_refund_policy,
    "account_compromise_signals": grade_account_compromise_signals,
}


def grade_task(state: SupportOpsState, task: TaskSpec) -> float:
    grader = GRADERS[task.task_id]
    return clamp_score(grader(state, task))
