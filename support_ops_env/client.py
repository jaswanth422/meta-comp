from support_ops_env.models import SupportOpsAction
from support_ops_env.server.support_ops_environment import SupportOpsEnv


async def create_env(task_id: str | None = None) -> SupportOpsEnv:
    return SupportOpsEnv(task_id=task_id)


def action(action_type: str, **kwargs: object) -> SupportOpsAction:
    payload = {"action_type": action_type, **kwargs}
    return SupportOpsAction.model_validate(payload)
