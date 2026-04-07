from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any, Optional

from support_ops_env.graders import clamp_score, grade_task
from support_ops_env.models import (
    ActionHistoryEntry,
    ActionType,
    DraftReply,
    StepResult,
    SupportOpsAction,
    SupportOpsObservation,
    SupportOpsState,
)
from support_ops_env.reward import compute_step_reward
from support_ops_env.task_bank import TASK_ORDER, build_task_bank


class SupportOpsEnv:
    def __init__(self, task_id: Optional[str] = None) -> None:
        self.task_bank = build_task_bank()
        self._task_cursor = 0
        self._forced_task_id = task_id
        self._task = None
        self._state: Optional[SupportOpsState] = None

    @classmethod
    async def from_docker_image(cls, image_name: Optional[str] = None) -> "SupportOpsEnv":
        # For local reproducibility in tests and baseline runs, this classmethod returns
        # a local in-process env instance while preserving the expected API surface.
        _ = image_name
        return cls()

    async def close(self) -> None:
        return None

    async def reset(self, task_id: Optional[str] = None) -> StepResult:
        chosen_task_id = task_id or self._forced_task_id
        if chosen_task_id is None:
            chosen_task_id = TASK_ORDER[self._task_cursor % len(TASK_ORDER)]
            self._task_cursor += 1
        self._task = self.task_bank[chosen_task_id]

        ticket = deepcopy(self._task.ticket)
        self._state = SupportOpsState(
            episode_id=str(uuid.uuid4()),
            task_id=self._task.task_id,
            step_count=0,
            done=False,
            max_steps=self._task.max_steps,
            ticket_ground_truth=self._task.ticket.model_dump(),
            expected_resolution=self._task.expected.model_dump(),
            queue=[ticket],
            active_ticket=None,
            customer=deepcopy(self._task.customer),
            kb_articles=deepcopy(self._task.kb_articles),
            kb_results=[],
            draft_reply=DraftReply(body=""),
            escalation_status=None,
            internal_notes=[],
            submitted_resolution_code=None,
            visited_articles=set(),
            achieved_milestones=set(),
            reward_breakdown={},
            grader_inputs={},
        )
        obs = self._build_observation()
        return StepResult(observation=obs, reward=0.0, done=False, info={"task_id": self._task.task_id})

    async def step(self, action: SupportOpsAction) -> StepResult:
        if self._state is None or self._task is None:
            raise RuntimeError("Environment is not initialized. Call reset() first.")

        if self._state.done:
            obs = self._build_observation()
            return StepResult(observation=obs, reward=0.0, done=True, info={"score": clamp_score(self._state.score)})

        self._state.step_count += 1
        self._state.last_action_status = "ok"
        self._state.last_action_error = None
        action_valid = self._apply_action(action)

        reward, components = compute_step_reward(self._state, self._task, action, action_valid)
        for key, value in components.items():
            self._state.reward_breakdown[key] = self._state.reward_breakdown.get(key, 0.0) + value
            if value > 0:
                self._state.achieved_milestones.add(key)

        done = self._is_done(action)
        if done:
            self._state.done = True
            final_score = clamp_score(grade_task(self._state, self._task))
            self._state.score = final_score
            reward += 0.30 * final_score
            self._state.reward_breakdown["final_score_bonus"] = 0.30 * final_score

        self._state.action_history.append(
            ActionHistoryEntry(
                step=self._state.step_count,
                action_type=action.action_type,
                payload=action.model_dump(exclude_none=True),
            )
        )

        obs = self._build_observation()
        info: dict[str, Any] = {
            "score": clamp_score(self._state.score),
            "error": self._state.last_action_error,
            "task_id": self._state.task_id,
        }
        return StepResult(observation=obs, reward=round(reward, 4), done=self._state.done, info=info)

    async def state(self) -> SupportOpsState:
        if self._state is None:
            raise RuntimeError("Environment is not initialized. Call reset() first.")
        return self._state

    def _apply_action(self, action: SupportOpsAction) -> bool:
        assert self._state is not None
        assert self._task is not None

        ticket = self._state.active_ticket

        if action.action_type == ActionType.VIEW_QUEUE:
            return True

        if action.action_type == ActionType.OPEN_TICKET:
            target_id = action.ticket_id or self._task.ticket.ticket_id
            found = next((t for t in self._state.queue if t.ticket_id == target_id), None)
            if not found:
                return self._invalid_action(f"Ticket not found: {target_id}")
            self._state.active_ticket = found
            return True

        if ticket is None and action.action_type != ActionType.VIEW_QUEUE:
            return self._invalid_action("No active ticket. Open a ticket first.")

        if action.action_type == ActionType.SEARCH_KB:
            query = (action.query or "").strip().lower()
            if not query:
                return self._invalid_action("Missing query")
            self._state.kb_results = [
                a for a in self._state.kb_articles if any(token in a.keywords for token in query.split())
            ]
            if not self._state.kb_results:
                self._state.kb_results = [
                    a for a in self._state.kb_articles if query in a.title.lower() or query in a.content.lower()
                ]
            return True

        if action.action_type == ActionType.READ_KB_ARTICLE:
            if not action.article_id:
                return self._invalid_action("Missing article_id")
            exists = any(a.article_id == action.article_id for a in self._state.kb_articles)
            if not exists:
                return self._invalid_action("Unknown article_id")
            self._state.visited_articles.add(action.article_id)
            return True

        if action.action_type == ActionType.SET_PRIORITY:
            if action.priority not in {"low", "normal", "high", "critical"}:
                return self._invalid_action("Invalid priority")
            ticket.priority = action.priority
            return True

        if action.action_type == ActionType.ADD_TAG:
            if not action.tag:
                return self._invalid_action("Missing tag")
            if action.tag not in ticket.tags:
                ticket.tags.append(action.tag)
            return True

        if action.action_type == ActionType.REMOVE_TAG:
            if not action.tag:
                return self._invalid_action("Missing tag")
            if action.tag in ticket.tags:
                ticket.tags.remove(action.tag)
            return True

        if action.action_type == ActionType.ASSIGN_TEAM:
            if not action.team:
                return self._invalid_action("Missing team")
            ticket.assigned_team = action.team
            return True

        if action.action_type == ActionType.DRAFT_REPLY:
            if not action.message:
                return self._invalid_action("Missing message")
            self._state.draft_reply.body = action.message
            return True

        if action.action_type == ActionType.REQUEST_ESCALATION:
            if not action.team:
                return self._invalid_action("Missing escalation team")
            self._state.escalation_status = action.team
            return True

        if action.action_type == ActionType.ADD_INTERNAL_NOTE:
            if not action.note:
                return self._invalid_action("Missing note")
            self._state.internal_notes.append(action.note)
            return True

        if action.action_type == ActionType.CLOSE_TICKET:
            ticket.status = "closed"
            return True

        if action.action_type == ActionType.SUBMIT_RESOLUTION:
            if not action.resolution_code:
                return self._invalid_action("Missing resolution_code")
            self._state.submitted_resolution_code = action.resolution_code
            return True

        return self._invalid_action("Unsupported action")

    def _invalid_action(self, message: str) -> bool:
        assert self._state is not None
        self._state.last_action_status = "error"
        self._state.last_action_error = message
        self._state.mistakes.append(message)
        return False

    def _is_done(self, action: SupportOpsAction) -> bool:
        assert self._state is not None
        assert self._task is not None
        if self._state.step_count >= self._state.max_steps:
            return True
        if action.action_type == ActionType.SUBMIT_RESOLUTION and not self._task.expected.must_close:
            return True
        if self._state.active_ticket and self._state.active_ticket.status == "closed":
            return True
        if "unsafe_reply" in self._state.reward_breakdown and self._task.task_id == "account_compromise_signals":
            return True
        return False

    def _build_observation(self) -> SupportOpsObservation:
        assert self._state is not None
        assert self._task is not None
        ticket = self._state.active_ticket
        return SupportOpsObservation(
            task_id=self._task.task_id,
            task_title=self._task.title,
            task_instructions=self._task.instructions,
            step_count=self._state.step_count,
            max_steps=self._state.max_steps,
            queue_snapshot=[
                {
                    "ticket_id": t.ticket_id,
                    "subject": t.subject,
                    "priority": t.priority,
                    "status": t.status,
                }
                for t in self._state.queue
            ],
            active_ticket=ticket.model_dump() if ticket else None,
            visible_kb_results=[a.model_dump() for a in self._state.kb_results],
            current_draft_reply=self._state.draft_reply.body,
            current_labels=(ticket.tags if ticket else []),
            current_priority=(ticket.priority if ticket else "normal"),
            assigned_team=(ticket.assigned_team if ticket else None),
            escalation_status=self._state.escalation_status,
            last_action_status=self._state.last_action_status,
            last_action_error=self._state.last_action_error,
            progress_signals={
                "opened_ticket": "opened_ticket" in self._state.achieved_milestones,
                "priority_set": "set_correct_priority" in self._state.achieved_milestones,
                "kb_consulted": "read_required_kb" in self._state.achieved_milestones,
                "has_reply": bool(self._state.draft_reply.body),
            },
            available_actions=[a.value for a in ActionType],
        )
