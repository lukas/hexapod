"""Explain saved hardware plans without treating queue state as readiness."""

from collections.abc import Mapping
from html import escape
from typing import Any, Dict, Optional


def run_requirements(item: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(item, Mapping) or item.get("status") != "waiting_for_operator":
        return None
    parameters = item.get("parameters")
    if not isinstance(parameters, Mapping):
        parameters = {}
    compatibility = parameters.get("current_compatibility")
    if not isinstance(compatibility, Mapping):
        compatibility = {}
    blockers = parameters.get("hard_blockers")
    adaptive_admission = parameters.get("_adaptive_admission")
    if not isinstance(adaptive_admission, Mapping):
        adaptive_admission = {}
    # These fields are part of the immutable saved experiment specification.
    # They describe what was known when the plan was authored; they are not a
    # live probe of the current checkout or robot. In particular, an analysis
    # run cannot prove a runner/hash that may be prepared later by the
    # full-access engineering lane. Keep the warning visible, but do not turn
    # this historical snapshot into a self-renewing live blocker.
    recorded_software_requirements = (
        bool(blockers)
        or compatibility.get("ready") is False
        or (
            adaptive_admission.get("analysis_generated") is True
            and adaptive_admission.get("ready") is False
        )
    )
    if isinstance(blockers, (list, tuple)):
        blocker_text = " ".join(value for value in blockers if isinstance(value, str))
    else:
        blocker_text = blockers if isinstance(blockers, str) else ""
    architecture = compatibility.get("architecture", "")
    if not isinstance(architecture, str):
        architecture = ""
    technical_text = (architecture + " " + blocker_text).lower()
    recurrent = "gru" in technical_text or "recurrent" in technical_text
    obs_dim = compatibility.get("obs_dim")
    supported_dims = compatibility.get("board_runtime_supported_obs_dims")
    input_format = (
        isinstance(obs_dim, int)
        and not isinstance(obs_dim, bool)
        and obs_dim > 0
        and isinstance(supported_dims, (list, tuple))
        and bool(supported_dims)
        and all(isinstance(value, int) for value in supported_dims)
        and obs_dim not in supported_dims
    ) or any(word in technical_text for word in ("observation", "obs-", "obs "))

    checks = []
    if recorded_software_requirements:
        if recurrent:
            checks.append("Add and test support for this policy’s memory between control steps and its input format.")
        elif input_format:
            checks.append("Add and test the input format this policy needs on the robot.")
        else:
            checks.append("Resolve and verify the plan’s recorded software requirements.")
        checks.append("Verify that the exported policy and robot runtime produce matching results with correct timing.")
    if any(parameters.get(key) is True for key in (
        "blocked_until_sequence_1_reviewed_clean",
        "blocked_until_prior_candidates_reviewed",
    )):
        checks.append("Complete and review the required earlier tests before starting this one.")
    checks.extend([
        "Verify the installed robot software and the exact policy selected for this plan.",
        (
            "Use a clean dedicated worktree at the exact reviewed source revision, or "
            "a clean documented validated integration branch; never deploy controller "
            "files from the shared checkout’s uncommitted state."
        ),
        (
            "Before deployment, compare the staged deploy-manifest hashes with both "
            "the currently installed robot revision/files and the latest sealed "
            "successful hardware provenance; do not overwrite a newer or different "
            "controller revision."
        ),
        "Check fresh, healthy robot readings, the physical pose, and live cameras.",
        "Keep the live camera and fresh telemetry visible with the remote stop path ready; that counts as supervision when they show a normal state.",
    ])
    return {
        "headline": (
            "Saved software requirements need current revalidation"
            if recorded_software_requirements
            else "Guarded-run checks are still required"
        ),
        # Six sentences of caveat above every queued plan trained the operator
        # to skip the whole box. Each clause below is load-bearing and pinned
        # by tests -- waiting is not readiness, the site does not launch, the
        # runner neither rewrites the plan nor needs re-authorization -- so
        # this is the same set of facts in half the words.
        "detail": (
            "These are not current blockers: they were recorded when the plan "
            "was saved, and waiting here does not confirm that the robot is "
            "ready. The guarded runner rechecks them against the live robot "
            "and may then proceed without rewriting the historical plan or "
            "asking for another operator authorization. The website itself "
            "does not launch a plan."
        ),
        # Deprecated compatibility field. Saved parameters alone cannot
        # establish a *current* software blocker; consumers should use the
        # explicitly named historical count below and live execution progress.
        "software_blocked": False,
        "recorded_software_requirements": recorded_software_requirements,
        "checks": checks,
    }


def run_requirements_html(item: Any) -> str:
    requirements = run_requirements(item)
    if requirements is None:
        return ""
    checks = "".join(f"<li>{escape(check)}</li>" for check in requirements["checks"])
    count = len(requirements["checks"])
    # Collapsed by default: this is reference material about a plan that has
    # not run, and expanded it buried the description of the experiment.
    return (
        '<section class="context run-requirements" aria-label="Before this can run">'
        '<details><summary>'
        f'<strong>{escape(requirements["headline"])}</strong>'
        f' · {count} check{"" if count == 1 else "s"}'
        '</summary>'
        f'<p>{escape(requirements["detail"])}</p>'
        f'<ul>{checks}</ul>'
        '</details></section>'
    )
