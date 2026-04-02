from fastapi import FastAPI

from support_ops_env.models import SupportOpsAction
from support_ops_env.server.support_ops_environment import SupportOpsEnv

app = FastAPI(title="support_ops_env")
_env = SupportOpsEnv()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/reset")
async def reset(payload: dict | None = None) -> dict:
    task_id = (payload or {}).get("task_id")
    result = await _env.reset(task_id=task_id)
    return result.model_dump()


@app.post("/step")
async def step(payload: dict) -> dict:
    action = SupportOpsAction.model_validate(payload)
    result = await _env.step(action)
    return result.model_dump()


@app.get("/state")
async def state() -> dict:
    s = await _env.state()
    return s.model_dump()
