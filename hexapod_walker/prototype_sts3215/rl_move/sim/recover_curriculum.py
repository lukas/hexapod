"""Recovery-curriculum bookkeeping for ``train_ppo_mjx``.

Per-episode outcome extraction from env infos, the sidecar restore of a
warm-started curriculum, the deterministic MJX certification plan and its
scoring/admission/regression updates, and the cert runner that steps a
small dedicated pool of envs. No trainer state lives here; everything is
passed in explicitly.

Moved verbatim out of train_ppo_mjx.py (which re-exports these names).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _recover_episode_outcome(info: dict) -> tuple[int, bool] | None:
    """Extract one exact terminal training outcome from an env info."""
    if not any(str(k).startswith("recover_episode_bucket_")
               for k in info):
        return None
    bucket = int(float(info.get("recover_start_bucket", -1)))
    if bucket < 0:
        return None
    success = bool(
        info.get("recover_success", 0.0) > 0.0
        or info.get("termination_reason") == "recover_success")
    return bucket, success


def _recover_episode_training_error(info: dict) -> tuple[int, float] | None:
    """Extract sampler-only terminal shortfall from a training episode."""
    outcome = _recover_episode_outcome(info)
    if outcome is None or "recover_training_error" not in info:
        return None
    bucket, _success = outcome
    error = float(np.clip(info["recover_training_error"], 0.0, 1.0))
    return bucket, error


def _restore_recover_curriculum_from_sidecar(venv, sidecar_path) -> dict:
    """Restore promotion-time recovery curriculum state on EVERY env.

    Backs the default-off --recover-init-curriculum flag (operator order
    2026-08-18: continue the finished recover-any21-pop3 cohort from its
    exact final state instead of restarting the frontier at B0).  Accepts
    a promotion ``*.curriculum.json`` sidecar (the ``curriculum`` key) or
    a bare curriculum dict, applies it via the same env method the
    in-run rollback/adoption machinery uses, and verifies the fleet is
    synchronized afterwards.  Returns the curriculum dict applied.
    """
    payload = json.loads(Path(sidecar_path).read_text())
    curriculum = payload.get("curriculum", payload)
    venv.env_method("restore_recover_curriculum_checkpoint_state",
                    curriculum)
    active = [int(value) for value in venv.get_attr("_rec_active_n")]
    expected = int(curriculum["active_n"])
    if len(active) != venv.num_envs or set(active) != {expected}:
        counts = {value: active.count(value)
                  for value in sorted(set(active))}
        raise RuntimeError(
            "recover curriculum restore desynchronized the training "
            f"fleet: expected active_n={expected}, counts={counts}")
    return curriculum


def _recover_cert_bucket_plan(frontier: int, retention_count: int,
                              cursor: int,
                              weak_bucket: int | None) -> tuple[list[int], int]:
    """Frontier plus a weak bucket and rotating old-bucket assays."""
    frontier = max(0, int(frontier))
    old = list(range(frontier))
    buckets = [frontier]
    weak = -1 if weak_bucket is None else int(weak_bucket)
    if weak in old:
        buckets.append(weak)
    if not old or retention_count <= 0:
        return buckets, 0
    cursor = int(cursor) % len(old)
    scanned = 0
    added = 0
    while scanned < len(old) and added < int(retention_count):
        bucket = old[(cursor + scanned) % len(old)]
        scanned += 1
        if bucket in buckets:
            continue
        buckets.append(bucket)
        added += 1
    return buckets, (cursor + scanned) % len(old)


def _recover_update_regression_timers(
        failed_since: dict[int, int], gate_fractions: dict[int, float],
        step: int, threshold: float, rollback_after_steps: int
        ) -> list[int]:
    """Update per-bucket regression timers and return timed-out buckets."""
    for bucket in list(failed_since):
        if bucket not in gate_fractions:
            failed_since.pop(bucket, None)
    for bucket, fraction in gate_fractions.items():
        if float(fraction) < float(threshold):
            failed_since.setdefault(int(bucket), int(step))
        else:
            failed_since.pop(int(bucket), None)
    return sorted(
        bucket for bucket, failed_at in failed_since.items()
        if int(step) - failed_at >= int(rollback_after_steps))


def _recover_update_admission_all(vec_env, cert_round: int) -> tuple[dict, int]:
    """Atomically advance every training env and verify agreement.

    Recovery curriculum state lives on each host-side shim. Updating only
    env zero makes certification appear to advance while nearly every PPO
    rollout remains on B0, so treat a divergent fleet as a fatal error.
    """
    admissions = vec_env.env_method(
        "_recover_update_admission", int(cert_round))
    if not admissions:
        raise RuntimeError("recovery admission updated zero training envs")
    canonical = admissions[0]
    fields = ("active_before", "active_after", "promoted")
    expected = tuple(canonical[field] for field in fields)
    divergent = [
        index for index, admission in enumerate(admissions)
        if tuple(admission[field] for field in fields) != expected
    ]
    if divergent:
        preview = divergent[:8]
        raise RuntimeError(
            "recovery curriculum desynchronized across training envs; "
            f"canonical={expected}, divergent_indices={preview}, "
            f"divergent_count={len(divergent)}")
    return canonical, len(admissions)


def _recover_score_payload(state: dict, best_score: float = 0.0,
                           cert_ages: dict[int, int] | None = None
                           ) -> tuple[dict, float]:
    """Build the dedicated W&B recovery scoreboard.

    Bucket B contributes B+1 points times its latest deterministic success
    fraction. The denominator includes every curriculum bucket, including
    locked/untested ones, so the normalized score rises as harder abilities
    are unlocked rather than renormalizing the task underneath the policy.
    """
    total = int(state["total_buckets"])
    maximum = total * (total + 1) / 2.0
    rows = state.get("buckets", {})
    training_errors = state.get("training_errors", {})
    points = 0.0
    certified_weight = 0.0
    payload = {
        "RECOVER_SCORE/max_unlocked_bucket": float(
            state["max_unlocked_bucket"]),
        "RECOVER_SCORE/focus_bucket": float(state["focus_bucket"]),
        "RECOVER_SCORE/weakest_bucket": float(state["weakest_bucket"]),
        "RECOVER_SCORE/maximum_points": maximum,
    }
    gate_fractions = []
    for bucket in range(total):
        key = str(bucket)
        row = rows.get(key)
        weight = float(bucket + 1)
        if row is not None:
            fraction = float(row["success_fraction"])
            gate_fraction = float(row["gate_fraction"])
            bucket_points = weight * fraction
            points += bucket_points
            certified_weight += weight
            gate_fractions.append(gate_fraction)
            stem = f"RECOVER_SCORE/bucket_{bucket:02d}"
            payload[f"{stem}_success_fraction"] = fraction
            payload[f"{stem}_gate_fraction"] = gate_fraction
            payload[f"{stem}_successes"] = float(row["successes"])
            payload[f"{stem}_episodes"] = float(row["episodes"])
            payload[f"{stem}_points"] = bucket_points
            if cert_ages is not None and bucket in cert_ages:
                payload[f"{stem}_cert_age_rounds"] = float(
                    cert_ages[bucket])
        probability = state.get("sample_probabilities", {}).get(key)
        if probability is not None:
            payload[
                f"RECOVER_SCORE/bucket_{bucket:02d}_sample_probability"
            ] = float(probability)
        training_error = training_errors.get(key)
        if training_error is not None:
            stem = f"RECOVER_SCORE/bucket_{bucket:02d}"
            payload[f"{stem}_training_error_ema"] = float(
                training_error["ema"])
            payload[f"{stem}_training_error_episodes"] = float(
                training_error["episodes"])
            payload[f"{stem}_training_error_priority"] = float(
                training_error.get("priority", 0.0))
    score = points / maximum if maximum > 0.0 else 0.0
    best = max(float(best_score), score)
    payload.update({
        "RECOVER_SCORE/overall_points": points,
        "RECOVER_SCORE/overall_weighted_success": score,
        "RECOVER_SCORE/best_overall_weighted_success": best,
        "RECOVER_SCORE/certified_weight_fraction": (
            certified_weight / maximum if maximum > 0.0 else 0.0),
        "RECOVER_SCORE/min_certified_gate_fraction": (
            min(gate_fractions) if gate_fractions else 0.0),
    })
    return payload, best


def _run_recover_cert_kind(vec_env, model, kind: str) -> dict:
    """One deterministic first-episode recovery assay on an MJX VecEnv."""
    n_envs = int(vec_env.num_envs)
    vec_env.set_attr("force_recover_start", str(kind))
    obs = vec_env.reset()
    state = None
    episode_start = np.ones(n_envs, dtype=bool)
    finished = np.zeros(n_envs, dtype=bool)
    outcomes = np.zeros(n_envs, dtype=bool)
    finish_ticks = np.zeros(n_envs, dtype=np.int64)
    max_ticks = int(getattr(vec_env, "_episode_steps", 0)) + 2
    if max_ticks <= 2:
        raise RuntimeError("MJX recovery cert env has no episode horizon")
    ticks = 0
    while not bool(np.all(finished)):
        actions, state = model.predict(
            obs, state=state, episode_start=episode_start,
            deterministic=True)
        obs, _rewards, dones, infos = vec_env.step(actions)
        ticks += 1
        episode_start = np.asarray(dones, dtype=bool)
        for i in np.flatnonzero(np.asarray(dones) & ~finished):
            info = infos[int(i)]
            outcomes[i] = bool(
                info.get("recover_success", 0.0) > 0.0
                or info.get("termination_reason") == "recover_success")
            finished[i] = True
            finish_ticks[i] = ticks
        if ticks > max_ticks:
            missing = np.flatnonzero(~finished).tolist()
            raise RuntimeError(
                f"MJX recovery certification exceeded the episode "
                f"horizon for envs {missing}")
    dt = float(getattr(vec_env, "_dt", 0.0))
    return {
        "kind": str(kind),
        "outcomes": outcomes.tolist(),
        "successes": int(outcomes.sum()),
        "episodes": n_envs,
        "success": float(outcomes.mean()),
        "time_mean_s": float(finish_ticks.mean() * dt),
    }
