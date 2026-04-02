# Build Plan: OpenEnv Submission

## 1. Goal

Build a complete OpenEnv environment that simulates a real human workflow, exposes the standard `reset()` / `step()` / `state()` API with typed models, includes at least 3 graded tasks, ships with a reproducible `inference.py`, and can be deployed as a containerized Hugging Face Space.

This plan is designed to optimize for the judging rubric in `instructions.md` while keeping implementation scope realistic for a single high-quality submission.

## 2. Recommended Environment Concept

### Environment name
`support_ops_env`

### Domain
B2B SaaS customer support triage and resolution.

### Why this is the best fit

- It is clearly a real-world task humans do every day.
- It supports structured state, multi-step reasoning, and realistic tool use.
- It is easy to grade deterministically because outcomes can be tied to known policies, tags, priorities, escalation rules, and required reply content.
- It supports meaningful partial rewards across the full trajectory.
- It is easier to make robust and reproducible than open-ended domains like code review or content writing.

## 3. What the Submission Must Contain

The final repo must include all of the following:

- A valid OpenEnv environment with typed `Action`, `Observation`, and `State` models.
- Working `reset()`, `step()`, and `state()` behavior.
- A correct `openenv.yaml`.
- At least 3 tasks with deterministic graders returning scores in `[0.0, 1.0]`.
- A shaped reward function with partial progress and penalties.
- Root-level `inference.py` using `HF_TOKEN` for all model-backed testing and submission runs.
- Structured stdout logs using `[START]`, `[STEP]`, and `[END]`.
- A working Dockerfile.
- A Hugging Face Space deployment that responds successfully.
- A README with setup, usage, task descriptions, action/observation definitions, and baseline scores.

## 4. Important Instruction Ambiguities To Resolve Up Front

The provided instructions have a few inconsistencies. Handle them deliberately instead of discovering them late.

### 4.1 Credential policy

Use `HF_TOKEN` exclusively for local testing, baseline evaluation, deployment validation, and submission.

Decision:

- `HF_TOKEN` is the only credential documented in this build plan.
- Do not add alternate token paths for judged or local runs.

### 4.2 Inference log format mismatch

The prose format says:

- `[END] success=<true|false> steps=<n> rewards=<...>`

But the sample code prints:

- `[END] success=<true|false> steps=<n> score=<0.000> rewards=<...>`

Decision:

- Implement the exact sample code format and include `score=...` in the `[END]` line.
- Keep field order exactly stable.
- Add a note in README that this follows the provided sample implementation because the prose and code conflict.

### 4.3 Docker image env var mismatch

The instructions mention `LOCAL_IMAGE_NAME`, while the sample code uses `IMAGE_NAME`.

Decision:

- Support both:
  - `IMAGE_NAME = os.getenv("IMAGE_NAME") or os.getenv("LOCAL_IMAGE_NAME")`
- Document both, but prefer `IMAGE_NAME` internally.

### 4.4 OpenEnv shape is evolving

OpenEnv is still moving quickly, so do not invent structure.

Decision:

- Scaffold from current OpenEnv conventions.
- Run `openenv validate` early and often.

## 5. Product Definition

### User story

An AI agent acts as a support operations specialist handling inbound SaaS support tickets. It must inspect tickets, search the knowledge base, apply the right labels and priority, choose whether to escalate, draft a compliant response, and close or route the case correctly.

### Episode objective

For each task, the agent must produce the correct operational handling of one support case or queue slice within a bounded number of steps.

### Why evaluators will like this

- The domain has obvious real-world utility.
- Success is measurable.
- Hard tasks can still be deterministic.
- Failure modes are easy to model: wrong tag, wrong escalation, wrong SLA handling, unsafe reply, premature closure.

## 6. Environment Design

### 6.1 Core entities

Represent these as structured Python data classes or Pydantic models inside the environment state:

- `Ticket`
- `CustomerProfile`
- `AccountPlan`
- `KnowledgeBaseArticle`
- `DraftReply`
- `ActionHistoryEntry`
- `TaskSpec`
- `EpisodeState`

### 6.2 Action space

Use a single typed action model with an `action_type` discriminator and optional fields.

Recommended actions:

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

Keep actions explicit and limited. Avoid natural-language-only tool design because graders become harder and errors become harder to diagnose.

### 6.3 Observation space

Observation should expose enough information for the agent to act, but not leak the grader answer.

Recommended observation fields:

- `task_id`
- `task_title`
- `task_instructions`
- `step_count`
- `max_steps`
- `queue_snapshot`
- `active_ticket`
- `visible_kb_results`
- `current_draft_reply`
- `current_labels`
- `current_priority`
- `assigned_team`
- `escalation_status`
- `last_action_status`
- `last_action_error`
- `progress_signals`
- `available_actions`

### 6.4 State model

State should be richer than observation and include grader-facing details.

Recommended state fields:

- `episode_id`
- `task_id`
- `step_count`
- `done`
- `ticket_ground_truth`
- `expected_resolution`
- `action_history`
- `reward_breakdown`
- `mistakes`
- `grader_inputs`

## 7. Task Set

Ship exactly 3 benchmark tasks first. Add more only after the validator path is stable.

### Task 1: Password Reset Queue Triage

Difficulty: Easy

Scenario:

- Single urgent login issue.
- One obvious KB article solves it.
- Correct handling requires opening the ticket, checking the customer plan, selecting correct priority, attaching the right tag, drafting a concise reply, and closing correctly.

Grader checks:

- Correct priority selected.
- Correct tag applied.
- Correct KB article consulted or referenced.
- Reply includes required guidance phrases.
- Ticket closed with the right resolution code.

### Task 2: Billing Refund With Policy Constraints

Difficulty: Medium

Scenario:

- Customer requests a refund after partial usage.
- Policy requires checking account plan, invoice age, and refund eligibility.
- Correct handling may require partial refund language instead of full approval.

Grader checks:

- Refund eligibility determined correctly.
- Proper team assignment.
- Proper escalation decision.
- Reply contains policy-compliant explanation.
- Unsafe or over-promising language is penalized.

### Task 3: Suspected Account Compromise With Conflicting Signals

Difficulty: Hard

Scenario:

- Ticket includes suspicious login behavior, recent billing change, and a request for account access restoration.
- Agent must avoid unsafe closure, identify security risk, prioritize appropriately, escalate to security, and send a constrained customer-safe response.

Grader checks:

- Priority set to high or critical as defined by task spec.
- Escalation requested to the correct team.
- Ticket not closed prematurely.
- Reply avoids disallowed actions like sharing reset links before verification.
- Internal note captures the key security facts.

## 8. Grader Design

Each task must have a deterministic grader returning a normalized score in `[0.0, 1.0]`.

### 8.1 Grader principles

- No LLM judge in the grader.
- No fuzzy semantic scoring unless it is rule-based and reproducible.
- Use weighted subchecks.
- Clamp final score into `[0.0, 1.0]`.

### 8.2 Suggested scoring formula

For each task:

- `0.20` correct classification and priority
- `0.20` correct routing or escalation
- `0.20` correct operational action sequence
- `0.25` reply content contains required elements
- `0.15` safety and policy compliance

Return exact float values, then round only for logging or display.

### 8.3 Reply grading method

Grade draft replies using rule-based content requirements:

- Required phrases or facts list
- Forbidden phrases list
- Length bounds
- Presence of required next step
- Correct tone markers if necessary

Do not score for eloquence. Score for correctness and policy compliance.

## 9. Reward Function

Reward should reflect progress during the episode, not just final correctness.

### 9.1 Positive reward events

- Opening the relevant ticket after viewing queue
- Searching with a policy-relevant query
- Reading the correct KB article
- Setting the correct priority
- Applying the correct tag
- Assigning the correct team
- Adding a useful internal note
- Drafting a reply that satisfies some required elements
- Submitting a correct final resolution

### 9.2 Negative reward events

- Invalid action
- Repeated no-op behavior
- Searching irrelevant KB terms repeatedly
- Wrong priority downgrade on urgent cases
- Premature ticket closure
- Unsafe reply content
- Exceeding step budget

### 9.3 Reward implementation approach

Use additive reward shaping with caps:

- Small positive increments for intermediate correct actions
- Moderate penalties for clearly wrong actions
- Final task score bonus on successful completion
- Duplicate reward suppression so the same correct action cannot be farmed repeatedly

Example design:

- `+0.05` correct intermediate action
- `+0.10` major milestone
- `-0.02` invalid or wasteful action
- `-0.10` serious safety violation
- `+0.30` final successful resolution

## 10. Episode Boundaries

Episodes should end when one of the following happens:

- The agent submits a final resolution.
- The ticket is closed.
- A hard safety failure occurs.
- `max_steps` is reached.

Recommended `max_steps`:

- Easy: 8
- Medium: 10
- Hard: 12

## 11. Project Structure

Recommended repo layout:

```text
support_ops_env/
├── support_ops_env/
│   ├── __init__.py
│   ├── models.py
│   ├── client.py
│   ├── openenv.yaml
│   ├── task_bank.py
│   ├── graders.py
│   ├── reward.py
│   ├── README.md
│   └── server/
│       ├── __init__.py
│       ├── app.py
│       └── support_ops_environment.py
├── inference.py
├── tests/
│   ├── test_tasks.py
│   ├── test_graders.py
│   ├── test_rewards.py
│   └── test_env_api.py
├── Dockerfile
├── pyproject.toml
├── README.md
└── .env.example
```

Notes:

- Keep `inference.py` at the repo root because the instructions require it.
- Keep a root README for judges.
- If OpenEnv scaffold places Dockerfile under `server/`, either mirror that structure or make root Docker usage explicit and consistent.

## 12. Implementation Plan

### Phase 1: Scaffold the environment

1. Install OpenEnv tooling.
2. Scaffold a new environment from the current OpenEnv template if available.
3. Rename the scaffold to `support_ops_env`.
4. Confirm import paths and package naming early.
5. Run `openenv validate` immediately after scaffolding.

### Phase 2: Define typed models

Create Pydantic models for:

- `SupportOpsAction`
- `SupportOpsObservation`
- `SupportOpsState`

Also create structured internal models for tickets, KB articles, and task specs.

Requirements:

- Action fields must validate strictly.
- Observation must never include hidden answer keys.
- State must be serializable and stable.

### Phase 3: Build deterministic task bank

Create a static task bank with exactly 3 launch tasks.

For each task, define:

- scenario text
- initial ticket and customer context
- KB articles
- allowed and expected actions
- expected final resolution
- grader rubric
- max steps

Store task definitions in code or JSON fixtures. Prefer code if it keeps validation simpler.

### Phase 4: Implement server environment logic

Implement:

- `reset()`
- `step(action)`
- `state()`

`reset()` should:

- choose a task by explicit task id or default task order
- initialize clean state
- return the first observation

`step()` should:

- validate the action
- mutate state
- compute shaped reward
- decide `done`
- return observation, reward, done, and info

`state()` should:

- expose current internal state for debugging and validation

### Phase 5: Implement graders

Build one grader function per task, plus a shared normalization helper.

Each grader should score:

- route correctness
- policy correctness
- safety
- final resolution quality

Also create unit tests that prove:

- perfect trajectory gets `1.0`
- obviously wrong trajectory gets low score
- scores are deterministic
- all outputs remain within `[0.0, 1.0]`

### Phase 6: Implement reward shaping

Write reward logic separately from the grader so both are understandable.

Requirements:

- rewards should track incremental progress
- major safety mistakes should incur immediate penalties
- repeated reward farming should be blocked
- final reward should align with grader outcome

### Phase 7: Build `inference.py`

Requirements:

- root-level file named exactly `inference.py`
- reads `API_BASE_URL`, `MODEL_NAME`, and `HF_TOKEN`
- uses `HF_TOKEN` as the credential for all testing and submission runs
- can run all 3 tasks sequentially
- produces deterministic, structured stdout

Suggested behavior:

- loop through tasks in fixed order
- use `temperature=0` for reproducibility
- cap steps per task
- log every step immediately after `env.step()`
- always emit `[END]` even on exception

### Phase 8: Documentation

Root `README.md` must include:

- environment motivation
- why the domain matters
- action space definition
- observation space definition
- task descriptions and difficulty
- setup instructions
- local run instructions
- Docker instructions
- HF Space deployment steps
- inference instructions
- baseline scores
- known constraints and environment variables

### Phase 9: Packaging and deployment

Build a container that:

- installs the package cleanly
- starts the OpenEnv server without manual intervention
- responds to `/reset`

Then deploy to a Hugging Face Space tagged with `openenv`.

### Phase 10: Validation and hardening

Before submission, run:

- unit tests
- `openenv validate`
- local Docker build
- local Docker run
- inference script end-to-end
- validator script or equivalent checks

## 13. `inference.py` Contract

Implement logs in the required order:

```text
[START] task=<task_name> env=<benchmark> model=<model_name>
[STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
[END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>
```

Implementation rules:

- One `[START]` per task episode.
- One `[STEP]` immediately after each `step()`.
- One `[END]` always, even on error.
- Keep `done` and `success` lowercase.
- Format per-step rewards to 2 decimals.
- Format final `score` consistently.
- Never print extra non-debug lines to stdout during judged runs.

## 14. Testing Requirements

Create tests for:

- model validation
- reset-state cleanliness
- step transitions
- invalid action handling
- reward shaping
- episode termination
- grader determinism
- task score normalization
- inference log format

Minimum test cases:

- one successful trajectory per task
- one failure trajectory per task
- one exploit attempt per task

## 15. Validation Checklist

The repo is ready only when all items below pass:

- `openenv validate` succeeds
- all three tasks run end-to-end
- graders return values only in `[0.0, 1.0]`
- `inference.py` completes successfully
- stdout log format exactly matches the required schema
- Docker image builds locally
- container responds to reset and step
- Hugging Face Space returns HTTP `200` on reset
- README includes baseline scores and usage instructions

## 16. Suggested Development Order

Use this order to avoid late-stage surprises:

1. Scaffold package and validate the empty shell.
2. Implement models and simple reset/step/state.
3. Implement one easy task end-to-end.
4. Add grader and reward shaping for that task.
5. Add the medium and hard tasks.
6. Build inference script.
7. Add tests.
8. Add Docker and local container validation.
9. Deploy to Hugging Face Space.
10. Run the full pre-submission checklist.

## 17. Risks and Mitigations

### Risk: grader too brittle

Mitigation:

- score structured outputs and required content atoms, not prose quality

### Risk: reward can be gamed

Mitigation:

- reward each milestone once
- add repeat-action penalties

### Risk: environment is too toy-like

Mitigation:

- include realistic policies, SLA rules, and escalation constraints

### Risk: hard task becomes impossible

Mitigation:

- make the hard task operationally complex, not ambiguous beyond grading

### Risk: deployment passes locally but fails on Space

Mitigation:

- keep dependencies minimal
- avoid heavy models or datasets
- test container startup path exactly as deployed

## 18. Nice-To-Have If Time Remains

- Add 2 to 3 more tasks after the first 3 are stable.
- Add a small web UI for manual debugging if OpenEnv tooling supports it.
- Add trajectory export for offline analysis.
- Add seeded task variants for broader evaluation.

## 19. Definition of Done

This project is done when:

- the environment is a believable support-operations simulator
- all required OpenEnv interfaces are implemented and validated
- three deterministic graded tasks work across easy, medium, and hard difficulty
- the inference baseline runs reproducibly with the required log format
- Docker and Hugging Face Space deployment both work
- the README is complete enough that an evaluator can run everything without guessing

## 20. Final Recommendation

Do not start by building all three tasks at once.

Build the environment around a single excellent easy task first, prove the full OpenEnv lifecycle, then expand to medium and hard tasks using the same action model, grader architecture, and reward framework.
