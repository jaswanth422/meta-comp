from inference import log_end, log_start, log_step


def test_log_functions_emit_expected_format(capsys) -> None:
    log_start("password_reset_triage", "support_ops_env", "Qwen")
    log_step(1, "{}", 0.0, False, None)
    log_end(True, 1, 0.9, [0.0])

    out = capsys.readouterr().out.strip().splitlines()
    assert out[0] == "[START] task=password_reset_triage env=support_ops_env model=Qwen"
    assert out[1] == "[STEP] step=1 action={} reward=0.00 done=false error=null"
    assert out[2] == "[END] success=true steps=1 score=0.900 rewards=0.00"
