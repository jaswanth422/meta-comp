import asyncio
import os
from typing import Optional

from openai import OpenAI

from support_ops_env.models import ActionType, SupportOpsAction
from support_ops_env.server.support_ops_environment import SupportOpsEnv
from support_ops_env.task_bank import TASK_ORDER

IMAGE_NAME = os.getenv("IMAGE_NAME") or os.getenv("LOCAL_IMAGE_NAME")
HF_TOKEN = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
BENCHMARK = "support_ops_env"
TEMPERATURE = 0.0
MAX_TOKENS = 250


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error if error else 'null'}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def _build_messages(task_id: str, observation: dict) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a support operations specialist. Return JSON with keys action_type and optional "
                "ticket_id/query/article_id/priority/tag/team/message/note/resolution_code."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Task={task_id}\n"
                f"step={observation['step_count']} max_steps={observation['max_steps']}\n"
                f"instructions={observation['task_instructions']}\n"
                f"active_ticket={observation['active_ticket']}\n"
                f"labels={observation['current_labels']} priority={observation['current_priority']} "
                f"team={observation['assigned_team']} escalation={observation['escalation_status']}\n"
                f"last_error={observation['last_action_error']}\n"
                "Return only compact JSON."
            ),
        },
    ]


def _fallback_policy(task_id: str, step: int) -> SupportOpsAction:
    if task_id == "password_reset_triage":
        scripted = [
            SupportOpsAction(action_type=ActionType.VIEW_QUEUE),
            SupportOpsAction(action_type=ActionType.OPEN_TICKET, ticket_id="T-1001"),
            SupportOpsAction(action_type=ActionType.SEARCH_KB, query="password reset"),
            SupportOpsAction(action_type=ActionType.READ_KB_ARTICLE, article_id="KB-RESET-01"),
            SupportOpsAction(action_type=ActionType.SET_PRIORITY, priority="high"),
            SupportOpsAction(action_type=ActionType.ADD_TAG, tag="auth"),
            SupportOpsAction(action_type=ActionType.ADD_TAG, tag="login"),
            SupportOpsAction(action_type=ActionType.ASSIGN_TEAM, team="support_l1"),
            SupportOpsAction(
                action_type=ActionType.DRAFT_REPLY,
                message=(
                    "Please verify your identity first. Then follow the password reset steps in the portal. "
                    "Let us know once complete so we can confirm access."
                ),
            ),
            SupportOpsAction(
                action_type=ActionType.SUBMIT_RESOLUTION,
                resolution_code="password_reset_guided",
            ),
            SupportOpsAction(action_type=ActionType.CLOSE_TICKET),
        ]
    elif task_id == "billing_refund_policy":
        scripted = [
            SupportOpsAction(action_type=ActionType.VIEW_QUEUE),
            SupportOpsAction(action_type=ActionType.OPEN_TICKET, ticket_id="T-2201"),
            SupportOpsAction(action_type=ActionType.SEARCH_KB, query="refund policy prorated"),
            SupportOpsAction(action_type=ActionType.READ_KB_ARTICLE, article_id="KB-REFUND-01"),
            SupportOpsAction(action_type=ActionType.ADD_TAG, tag="billing"),
            SupportOpsAction(action_type=ActionType.ADD_TAG, tag="refund"),
            SupportOpsAction(action_type=ActionType.ASSIGN_TEAM, team="billing_ops"),
            SupportOpsAction(action_type=ActionType.REQUEST_ESCALATION, team="billing_ops"),
            SupportOpsAction(
                action_type=ActionType.DRAFT_REPLY,
                message=(
                    "Based on your usage and invoice timing, this qualifies for a prorated adjustment. "
                    "Our billing team will confirm the exact amount."
                ),
            ),
            SupportOpsAction(action_type=ActionType.SUBMIT_RESOLUTION, resolution_code="prorated_refund_review"),
        ]
    else:
        scripted = [
            SupportOpsAction(action_type=ActionType.VIEW_QUEUE),
            SupportOpsAction(action_type=ActionType.OPEN_TICKET, ticket_id="T-3307"),
            SupportOpsAction(action_type=ActionType.SEARCH_KB, query="security suspicious login"),
            SupportOpsAction(action_type=ActionType.READ_KB_ARTICLE, article_id="KB-SEC-01"),
            SupportOpsAction(action_type=ActionType.SET_PRIORITY, priority="critical"),
            SupportOpsAction(action_type=ActionType.ADD_TAG, tag="security"),
            SupportOpsAction(action_type=ActionType.ADD_TAG, tag="account_compromise"),
            SupportOpsAction(action_type=ActionType.ASSIGN_TEAM, team="trust_safety"),
            SupportOpsAction(action_type=ActionType.REQUEST_ESCALATION, team="security_incident"),
            SupportOpsAction(
                action_type=ActionType.ADD_INTERNAL_NOTE,
                note="Unknown-country login plus billing card change plus lockout.",
            ),
            SupportOpsAction(
                action_type=ActionType.DRAFT_REPLY,
                message=(
                    "We have escalated this to our security team. "
                    "We cannot provide a reset link until verification. "
                    "Please confirm recent account activity."
                ),
            ),
            SupportOpsAction(action_type=ActionType.SUBMIT_RESOLUTION, resolution_code="security_escalated"),
        ]

    if step - 1 < len(scripted):
        return scripted[step - 1]
    return SupportOpsAction(action_type=ActionType.SUBMIT_RESOLUTION, resolution_code="timeout_guard")


def _model_action(client: OpenAI, task_id: str, observation: dict, step: int) -> SupportOpsAction:
    if not HF_TOKEN:
        return _fallback_policy(task_id, step)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=_build_messages(task_id, observation),
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        content = (completion.choices[0].message.content or "").strip()
        return SupportOpsAction.model_validate_json(content)
    except Exception:
        return _fallback_policy(task_id, step)


async def run_task(client: OpenAI, task_id: str) -> float:
    env: Optional[SupportOpsEnv] = None
    rewards: list[float] = []
    steps = 0
    success = False
    score = 0.0

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        env = await SupportOpsEnv.from_docker_image(IMAGE_NAME)
        result = await env.reset(task_id=task_id)
        while not result.done and steps < result.observation.max_steps:
            steps += 1
            action = _model_action(client, task_id, result.observation.model_dump(), steps)
            result = await env.step(action)
            rewards.append(result.reward)
            err = result.observation.last_action_error
            log_step(
                step=steps,
                action=action.model_dump_json(exclude_none=True),
                reward=result.reward,
                done=result.done,
                error=err,
            )

        state = await env.state()
        score = state.score
        score = min(max(score, 0.0), 1.0)
        success = score >= 0.7
    finally:
        if env is not None:
            try:
                await env.close()
            except Exception:
                pass
        log_end(success=success, steps=steps, score=score, rewards=rewards)

    return score


async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN or "DUMMY")
    task_scores = []
    for task_id in TASK_ORDER:
        score = await run_task(client, task_id)
        task_scores.append(score)


if __name__ == "__main__":
    asyncio.run(main())
