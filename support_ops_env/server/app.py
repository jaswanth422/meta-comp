import argparse

from fastapi import FastAPI

from support_ops_env.models import SupportOpsAction, SupportOpsObservation, SupportOpsState
from support_ops_env.server.support_ops_environment import SupportOpsEnv

app = FastAPI(title="support_ops_env", version="0.1.0")
_env = SupportOpsEnv()


@app.get("/")
async def root() -> dict:
    return {
        "name": "support_ops_env",
        "status": "ok",
        "routes": ["/health", "/metadata", "/schema", "/reset", "/step", "/state"],
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/metadata")
async def metadata() -> dict[str, str]:
    return {
        "name": "support_ops_env",
        "description": "Deterministic B2B SaaS support operations environment with triage and policy workflows.",
        "version": "0.1.0",
    }


@app.get("/schema")
async def schema() -> dict:
    return {
        "action": SupportOpsAction.model_json_schema(),
        "observation": SupportOpsObservation.model_json_schema(),
        "state": SupportOpsState.model_json_schema(),
    }


@app.post("/mcp")
async def mcp() -> dict:
    return {
        "jsonrpc": "2.0",
        "id": None,
        "error": {"code": -32601, "message": "MCP methods are not implemented in this environment."},
    }


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


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(host=args.host, port=args.port)
