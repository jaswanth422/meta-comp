from support_ops_env.task_bank import TASK_ORDER, build_task_bank


def test_task_bank_has_three_tasks() -> None:
    tasks = build_task_bank()
    assert len(tasks) >= 3
    assert TASK_ORDER == ["password_reset_triage", "billing_refund_policy", "account_compromise_signals"]


def test_task_step_budgets() -> None:
    tasks = build_task_bank()
    assert tasks["password_reset_triage"].max_steps == 8
    assert tasks["billing_refund_policy"].max_steps == 10
    assert tasks["account_compromise_signals"].max_steps == 12
