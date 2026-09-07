import pytest

from hexapod_lab.run_requirements import run_requirements, run_requirements_html


def waiting(parameters=None):
    return {"status": "waiting_for_operator", "execution_mode": "external_guarded", "parameters": parameters}


@pytest.mark.parametrize("item", [None, [], {}, {"status": "queued"}, {"status": "running"}, {"status": "succeeded"}])
def test_other_states_have_no_waiting_requirements(item):
    assert run_requirements(item) is None
    assert run_requirements_html(item) == ""


@pytest.mark.parametrize("parameters", [None, [], "malformed", 42, {}, {"current_compatibility": []}])
def test_unknown_plans_require_guarded_checks_without_claiming_readiness(parameters):
    result = run_requirements(waiting(parameters))
    assert result["software_blocked"] is False
    assert result["recorded_software_requirements"] is False
    assert result["headline"] == "Guarded-run checks are still required"
    assert "does not confirm that the robot is ready" in result["detail"]
    assert "website itself does not launch" in result["detail"]
    assert len(result["checks"]) == 5
    assert any("exact policy" in check for check in result["checks"])
    assert any("clean dedicated worktree" in check for check in result["checks"])
    assert any("staged deploy-manifest hashes" in check for check in result["checks"])
    assert any("newer or different" in check for check in result["checks"])
    assert any("live cameras" in check for check in result["checks"])
    assert any("counts as supervision" in check for check in result["checks"])


def test_unsupported_input_format_is_explained_without_using_name():
    item = waiting({
        "current_compatibility": {"ready": False, "obs_dim": 75, "architecture": "MLP 128x128"},
        "hard_blockers": ["Build and test obs-75 board semantics"],
        "blocked_until_sequence_1_reviewed_clean": True,
    })
    result = run_requirements(item)
    assert result["software_blocked"] is False
    assert result["recorded_software_requirements"] is True
    assert "current revalidation" in result["headline"]
    assert "not current blockers" in result["detail"]
    assert "without rewriting the historical plan" in result["detail"]
    assert "input format" in result["checks"][0]
    assert any("earlier tests" in check for check in result["checks"])
    assert "obs-75" not in " ".join(result["checks"])


def test_recurrent_policy_explains_memory_and_input_requirements():
    result = run_requirements(waiting({
        "current_compatibility": {"ready": False, "obs_dim": 81, "architecture": "dual-core GRU"},
        "hard_blockers": ["Implement persistent actor state"],
        "blocked_until_prior_candidates_reviewed": True,
    }))
    assert result["software_blocked"] is False
    assert result["recorded_software_requirements"] is True
    assert "memory between control steps" in result["checks"][0]
    assert any("correct timing" in check for check in result["checks"])


@pytest.mark.parametrize("blockers", ["Unknown requirement", [None, 42, "Unrecognized blocker"], {"malformed": "data"}])
def test_unrecognized_nonempty_blockers_remain_visible_for_revalidation(blockers):
    result = run_requirements(waiting({"hard_blockers": blockers}))
    assert result["software_blocked"] is False
    assert result["recorded_software_requirements"] is True
    assert "recorded software requirements" in result["checks"][0]


def test_compatibility_flag_never_claims_ready_to_run():
    result = run_requirements(waiting({"current_compatibility": {"ready": True, "obs_dim": 74}}))
    assert result["software_blocked"] is False
    assert result["recorded_software_requirements"] is False
    assert result["headline"] == "Guarded-run checks are still required"
    assert any("installed robot software" in check for check in result["checks"])
    assert "does not confirm" in result["detail"]


def test_unknown_compatibility_failure_does_not_invent_input_mismatch():
    result = run_requirements(waiting({"current_compatibility": {"ready": False, "obs_dim": 74}}))
    assert result["software_blocked"] is False
    assert result["recorded_software_requirements"] is True
    assert "recorded software requirements" in result["checks"][0]


def test_analysis_admission_is_a_historical_preflight_receipt_not_a_live_blocker():
    result = run_requirements(waiting({
        "_adaptive_admission": {
            "policy": "known-bounded-runner-v1",
            "analysis_generated": True,
            "ready": False,
            "reason": "runner had not been prepared when analysis ran",
        },
    }))

    assert result["software_blocked"] is False
    assert result["recorded_software_requirements"] is True
    assert "current revalidation" in result["headline"]
    assert "another operator authorization" in result["detail"]


def test_malformed_compatibility_fields_and_untrusted_prose_are_not_rendered():
    payload = '<script>alert("injection")</script>'
    item = waiting({
        "current_compatibility": {"ready": False, "architecture": [payload], "obs_dim": []},
        "hard_blockers": [payload],
        "prerequisites": [payload],
    })
    html = run_requirements_html(item)
    assert "Before this can run" in html
    assert "<ul>" in html and "<li>" in html
    assert payload not in html
    assert "<script>" not in html
