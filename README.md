---
title: meta-comp
emoji: 📈
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# support_ops_env

A deterministic OpenEnv-style environment that simulates B2B SaaS support operations workflows.

## Why This Environment

This benchmark models real support operations work: queue triage, policy lookup, classification, escalation, and customer-safe communication.

It is designed to evaluate whether an agent can complete realistic support workflows end-to-end while respecting policy and safety constraints.

## Action Space

Typed action model: `SupportOpsAction` with `action_type` and structured optional fields.

Supported actions:
- `view_queue`
- `open_ticket`
- `search_kb`
- `read_kb_article`
- `set_priority`
- `add_tag`
- `remove_tag`
- `assign_team`
- `draft_reply`
- `request_escalation`
- `add_internal_note`
- `close_ticket`
- `submit_resolution`

## Observation Space

`SupportOpsObservation` fields:
- task metadata (`task_id`, `task_title`, `task_instructions`)
- step information (`step_count`, `max_steps`)
- current queue and active ticket
- visible KB results
- labels, priority, assignment, escalation
- last action status and error
- progress signals and available actions

## Tasks

1. `password_reset_triage` (easy)
	 Objective: Triage a locked-account request, consult the password reset runbook, route correctly, and close with the proper resolution code.

2. `billing_refund_policy` (medium)
	 Objective: Apply prorated refund policy correctly, avoid over-promising, route to billing operations, and submit a compliant resolution.

3. `account_compromise_signals` (hard)
	 Objective: Handle conflicting compromise signals by prioritizing security, escalating correctly, adding internal notes, and avoiding unsafe closure.

All graders are deterministic and return scores in `[0.0, 1.0]`.

## Reward Design

The reward function is dense and trajectory-aware.

- Positive shaping:
	- Opening a ticket.
	- Reading required knowledge-base articles.
	- Setting required priority.
	- Adding required tags.
	- Assigning/escalating to correct teams.
	- Drafting policy-compliant replies with required phrases.
- Negative shaping:
	- Invalid actions.
	- Unsafe response content.
	- Premature closure in security incidents.
	- Max-step timeout pressure.
- Episode-end bonus:
	- Final task grade bonus proportional to normalized grader score.

This creates partial progress signals throughout an episode rather than only sparse terminal reward.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run Tests

```bash
pytest -q
```

## Run Baseline Inference

```bash
export HF_TOKEN=your_token
python inference.py
```

Required env vars:
- `HF_TOKEN` (required for model-backed runs)
- `API_BASE_URL` (default: `https://router.huggingface.co/v1`)
- `MODEL_NAME` (default: `Qwen/Qwen2.5-72B-Instruct`)
- `IMAGE_NAME` or `LOCAL_IMAGE_NAME` (optional)

For local validation:

```bash
pip install -e .[dev]
openenv validate
```

## Structured Log Format

The script emits:
- `[START] task=<task_name> env=<benchmark> model=<model_name>`
- `[STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>`
- `[END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>`

Note: This implementation includes `score=<...>` in `[END]` to align with the provided sample code behavior.

Formatting guarantees:
- Exactly one `[START]` at episode begin.
- Exactly one `[STEP]` for each successful `env.step(...)` call.
- Exactly one `[END]` per task run, even when runtime failures occur.
- Reward fields are printed with fixed decimal precision.

## Docker

```bash
docker build -t support-ops-local .
docker run --rm -p 7860:7860 support-ops-local
```

Then verify:

```bash
curl -s http://localhost:7860/health
curl -s -X POST http://localhost:7860/reset -H 'content-type: application/json' -d '{}'
```

## OpenEnv Validation

Run local validator checks before submission:

```bash
/Users/katurijaswanth/Desktop/meta-comp/.venv/bin/openenv validate
```

Or, if your virtual environment is activated:

```bash
openenv validate
```

## Hugging Face Space Deployment

1. Create a Docker Space tagged `openenv`.
2. Push this repository as the Space source.
3. Set variables: `HF_TOKEN`, `API_BASE_URL`, `MODEL_NAME`.
4. Wait for build, then validate `/health` and `/reset` endpoints.

## Baseline Scores

Deterministic scripted fallback policy scores:
- `password_reset_triage`: `1.0` (11 steps)
- `billing_refund_policy`: `1.0` (10 steps)
- `account_compromise_signals`: `1.0` (12 steps)

Observed baseline run metrics (`python inference.py`):
- Total tasks: `3`
- Mean score: `1.000`
- Success rate (`score >= 0.7`): `100%` (`3/3`)
- Mean steps per task: `11.0`

## Pre-Submission Validator Script

Use the repository-provided validator for pre-submission checks:

```bash
bash scripts/validate-submission.sh <your_space_url>
```

This validates:
- Hugging Face Space responds to `/reset`.
- Docker build succeeds.
- `openenv validate` passes.
