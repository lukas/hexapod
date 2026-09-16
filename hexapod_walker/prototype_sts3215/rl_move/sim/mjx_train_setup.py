"""Run setup and bookkeeping for ``train_ppo_mjx``.

Env construction kwargs from the CLI, MJX backend resolution and the
fail-closed GPU-physics guard, the walk-curriculum cert cfg overrides and
post-promotion schedule, W&B run initialisation, and the JSON-safe config
and training-complete marker written at the end of a run.

Moved verbatim out of train_ppo_mjx.py (which re-exports these names).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .servo_model import SimServoParams
from .cfg_set import _parse_cfg_set
from .env_registry import ENV_CLASSES
from .train_ppo_sim import (
    WANDB_ENTITY_DEFAULT, WANDB_PROJECT_DEFAULT,
    _learning_line, _load_wandb_env, _parse_goal_mix,
    _resolved_reward_cfg, _reward_notes,
)


def _env_kwargs(args, params: SimServoParams | None = None) -> dict:
    """Per-shim-env kwargs — mirrors train_ppo_sim._build_env, minus the
    model-DR pieces the shared-model backend can't honor yet.

    ``params=None`` resolves the actuator set from the run's cfg
    (bus.servo_params: "" = air fit, "loaded" = loaded bench fit)."""
    kw = dict(randomize=not args.no_dr,
              dr_scale=args.dr_scale,
              episode_seconds=getattr(
                  args, "training_episode_seconds", args.episode_seconds))
    overrides = _parse_cfg_set(args.cfg_set)
    external_recover_cert = (
        args.recover_cert_every > 0
        and args.recover_cert_envs > 0
        and float(_parse_goal_mix(args.goal_mix).get("recover", 0.0)) > 0.0)
    if overrides or external_recover_cert:
        from rl_move.config import load_config
        cfg = load_config()
        for dotted, val in overrides.items():
            node = cfg
            *path, leaf = dotted.split(".")
            for k in path:
                node = node.setdefault(k, {})
            node[leaf] = val
        if external_recover_cert:
            cfg.setdefault("goal", {})[
                "recover_external_certification"] = 1.0
        kw["cfg"] = cfg
    kw["params"] = (params if params is not None
                    else SimServoParams.from_cfg(kw.get("cfg")))
    return kw


def _resolve_impl(requested: str) -> str | None:
    """'auto' = warp when importable (GPU pods), else the mjx default."""
    if requested == "auto":
        try:
            import mujoco_warp  # noqa: F401
            return "warp"
        except Exception:
            return None
    return None if requested == "default" else requested


def _unwrap_vec(venv):
    """Innermost VecEnv under any wrapper chain (VecMonitor etc.)."""
    core = venv
    while hasattr(core, "venv"):
        core = core.venv
    return core


def _assert_gpu_physics(venv, impl: str | None) -> None:
    """Fail-closed all-GPU-physics guard (operator order 2026-08-18,
    fb_20260818T065930_03b422): a run launched with
    --require-gpu-physics must train on batched MJX/Warp physics — the
    actual VecEnv class is checked, so a SubprocVecEnv/DummyVecEnv of
    C-MuJoCo envs (CPU physics, whatever device Torch runs on) is
    REFUSED, and so is the XLA/jax fallback impl. Raises SystemExit;
    unit-tested in rl_move/tests/test_walkcurr_mjx.py."""
    from .mjx_sharded_vec_env import MjxShardedVecEnv
    from .mjx_vec_env import MjxVecEnv
    core = _unwrap_vec(venv)
    if not isinstance(core, (MjxVecEnv, MjxShardedVecEnv)):
        raise SystemExit(
            "--require-gpu-physics: the training VecEnv is "
            f"{type(core).__name__}, not MjxVecEnv/MjxShardedVecEnv — "
            "training physics would NOT run on the GPU. SubprocVecEnv/"
            "C-MuJoCo training physics is forbidden for this run "
            "(fb_20260818T065930_03b422).")
    if impl != "warp":
        raise SystemExit(
            f"--require-gpu-physics: physics impl is {impl!r}, not "
            "'warp' — the CUDA-batched Warp backend is required "
            "(fb_20260818T065930_03b422).")
    print(f"[backend] training physics VERIFIED: "
          f"{type(core).__name__} impl=warp n_envs={core.num_envs} "
          "(batched GPU physics; SubprocVecEnv refused by contract)",
          flush=True)


def apply_walkcurr_cert_cfg_overrides(cfg_d: dict,
                                      specs: list[str] | None) -> dict:
    """--walkcurr-cert-cfg-set (2026-08-24 freeze40 dig-in): apply
    dotted K=V cfg overrides to the CERT env's cfg dict only. The
    training env never sees these. Empty/None specs = no-op, bit-exact
    prior behavior. Returns cfg_d for chaining. Unit-tested in
    rl_move/tests/test_walkcurr_mjx.py."""
    for dotted, val in _parse_cfg_set(list(specs or [])).items():
        node = cfg_d
        *path, leaf = dotted.split(".")
        for k in path:
            node = node.setdefault(k, {})
        node[leaf] = val
    return cfg_d


def apply_walkcurr_post_promo_schedule(model, epochs: int,
                                       actor_lr: float,
                                       actor_lr_final: float) -> dict:
    """Frontier-gated update-schedule handover (default OFF; operator
    order fb_20260818T085648_2a0a60): on the walk curriculum's FIRST
    promotion (B0 mastered) the acquisition-strength update (high
    actor LR / extra epochs, needed to ignite walking from scratch)
    hands over to the consolidation recipe proven by
    cw-dynrep-criticD-40m1 (fewer epochs, decaying actor LR). Mutates
    ``model.n_epochs`` and the update_health actor group in place;
    returns {knob: (old, new)} for logging. Unit-tested in
    rl_move/tests/test_walkcurr_mjx.py."""
    changed: dict = {}
    if epochs > 0:
        changed["n_epochs"] = (int(model.n_epochs), int(epochs))
        model.n_epochs = int(epochs)
    if actor_lr > 0.0:
        st = getattr(model, "_ac_state", None)
        if st is None:
            raise RuntimeError(
                "--walkcurr-post-promo-actor-lr requires --actor-lr "
                "(update_health actor/critic groups not attached)")
        final = float(actor_lr_final) if actor_lr_final > 0.0 \
            else float(actor_lr)
        changed["actor_lr"] = (float(st["actor_lr"]), float(actor_lr))
        changed["actor_lr_final"] = (float(st["actor_lr_final"]), final)
        st["actor_lr"] = float(actor_lr)
        st["actor_lr_final"] = final
    return changed


def _init_wandb(args, params: SimServoParams):
    if args.no_wandb:
        return None
    _load_wandb_env()
    try:
        import wandb
    except Exception:
        print("[wandb] not installed — logging skipped")
        return None
    import os
    if not os.environ.get("WANDB_API_KEY"):
        try:
            if not wandb.api.api_key:
                raise RuntimeError
        except Exception:
            print("[wandb] no API key — logging skipped")
            return None
    # Plain-English objective FIRST (operator 08-10: the overview must
    # open with what the run is learning, not lineage babble).
    notes = (_learning_line(args) + "\n\n" + (args.notes or "")).strip()
    notes += "\n\n" + _reward_notes(args.cfg_set)
    _contract = getattr(args, "_motor_contract", None)
    if _contract is None:
        from .servo_model import motor_contract
        _contract = motor_contract(params=params,
                                   backend=f"mjx_tickparams:{args.impl}")
    wandb_identity = {}
    if args.recover_population_id:
        population_ids = tuple(
            run_id.strip()
            for run_id in args.recover_population_run_ids.split(",")
            if run_id.strip())
        wandb_identity = {
            "id": population_ids[args.recover_population_member],
            "resume": "never",
        }
    run = wandb.init(
        entity=WANDB_ENTITY_DEFAULT,
        project=os.environ.get("WANDB_PROJECT", WANDB_PROJECT_DEFAULT),
        # Research tracks (operator 08-11) arrive as WANDB_TAGS
        # (track:<id>), which wandb.init honors natively.
        group=(args.recover_population_id or "mjx-trainer"),
        job_type=(f"recover-member-{args.recover_population_member}"
                  if args.recover_population_id else None),
        name=args.run_name, notes=notes,
        **wandb_identity,
        sync_tensorboard=True,   # SB3 train/* metrics, like the campaign
        config={"trainer": "train_ppo_mjx", "task": args.task,
                # Resolved motor contract (fb_20260820T000059): stashed
                # on args by main from the actual env params/cfg;
                # fallback resolves from the run's params (from_cfg is
                # the single enforcement point either way).
                "motor_contract": _contract,
                "n_envs": args.n_envs, "impl": args.impl,
                "n_steps": args.n_steps, "batch_size": args.batch_size,
                "learning_rate": args.lr, "seed": args.seed,
                "dr_scale": args.dr_scale, "no_dr": args.no_dr,
                "predictive_actor": bool(args.predictive_actor),
                "predictive_live": bool(args.predictive_live),
                "cfg_set": args.cfg_set,
                "reward_cfg": _resolved_reward_cfg(args.cfg_set),
                "episode_seconds": getattr(
                    args, "training_episode_seconds", args.episode_seconds),
                "eval_episode_seconds": args.episode_seconds,
                "walk_curriculum": bool(args.walk_curriculum),
                "walk_curriculum_version": args.walk_curriculum_version,
                "walkcurr_cert_every": args.walkcurr_cert_every,
                "walkcurr_cert_episodes": args.walkcurr_cert_episodes,
                "walkcurr_cert_cfg_set": list(
                    getattr(args, "walkcurr_cert_cfg_set", []) or []),
                "mjx_iterations": args.mjx_iterations,
                "mjx_ls_iterations": args.mjx_ls_iterations,
                "recover_cert_every": args.recover_cert_every,
                "recover_cert_envs": args.recover_cert_envs,
                "recover_retention_buckets": args.recover_retention_buckets,
                "recover_full_retention_every": (
                    args.recover_full_retention_every),
                "recover_rollback_after_steps": (
                    args.recover_rollback_after_steps),
                "recover_rollback_fraction": (
                    args.recover_rollback_fraction),
                "recover_population_id": args.recover_population_id,
                "recover_population_member": (
                    args.recover_population_member),
                "recover_population_runs": (
                    args.recover_population_runs.split(",")
                    if args.recover_population_runs else []),
                "recover_population_run_ids": (
                    args.recover_population_run_ids.split(",")
                    if args.recover_population_run_ids else []),
                "recover_population_barrier_timeout_seconds": (
                    args.recover_population_barrier_timeout_seconds),
                "recover_population_bootstrap_rollouts": (
                    args.recover_population_bootstrap_rollouts),
                "recover_population_bootstrap_steps": (
                    args.n_envs * args.n_steps
                    * args.recover_population_bootstrap_rollouts),
                "recover_replay_mix": {
                    "focus": 0.50, "recent_three": 0.25,
                    "weakest": 0.15, "uniform_older": 0.10,
                    "training_error_overlay": 0.10},
                "recover_buckets": {
                    str(i): list(family) for i, family in enumerate(
                        getattr(ENV_CLASSES[args.task],
                                "RECOVER_FAMILIES", ()))},
                "model_dr": False,  # v1 backend limit, see MJX_PORT.md
                "sim_model_source": params.source})
    # Same headline-score pinning as the C trainer (the periodic eval
    # is shared code, so MJX runs emit identical SCORE/* names).
    run.define_metric("SCORE/*", step_metric="global_step",
                      summary="last")
    run.define_metric("eval/*", step_metric="global_step")
    run.define_metric("CERT/*", step_metric="global_step", summary="last")
    run.define_metric("TRAIN/*", step_metric="global_step", summary="last")
    run.define_metric("RECOVER_SCORE/*", step_metric="global_step",
                      summary="last")
    run.define_metric("RECOVER_GUARD/*", step_metric="global_step",
                      summary="last")
    run.define_metric("RECOVER_POPULATION/*", step_metric="global_step",
                      summary="last")
    print(f"[wandb] logging to {run.url or 'offline run dir'}")
    return run


def _json_safe_config(ns: argparse.Namespace) -> dict:
    """`vars(args)` filtered to JSON-serializable values (best-effort
    `str()` fallback for anything else, e.g. `Path`/`argparse` custom
    types) — used only for the `--defer-final-artifacts` marker below,
    NOT the source of truth for a resumed run's cfg (that's still the
    checkpoint + `--cfg-set` argv the launcher recorded)."""
    out: dict = {}
    for k, v in vars(ns).items():
        if v is None or isinstance(v, (bool, int, float, str)):
            out[k] = v
        elif isinstance(v, (list, tuple)):
            out[k] = [x if isinstance(x, (bool, int, float, str, type(None)))
                      else str(x) for x in v]
        else:
            out[k] = str(v)
    return out


def _write_training_complete_marker(
    out_path: Path, *, steps: int, run_name: str, task: str,
    run_id: str | None, resolved_config: dict,
) -> Path:
    """Atomically persist `<checkpoint>.training_complete.json` the
    moment optimization genuinely finishes (`model.learn()` returned),
    BEFORE the potentially slow background eval/video drain
    (`bg.shutdown()`) that currently holds the GPU-owning trainer
    process (and its ~46GB of CUDA memory) alive for minutes doing
    CPU-only work.

    Item 1 of the `--defer-final-artifacts` plan
    (fb_20260906T032210_129bed). Since the 09-06 follow-through
    (fb_20260906T035950_cd260e) the rest of the plan is live too: with
    the flag set, `VideoCallback._on_training_end` no longer blocks,
    `bg.handoff()` collects outstanding eval/video jobs instead of
    draining them, `artifact_handoff.write_manifest` records them
    immutably (registry phase training -> artifacts_pending ->
    evaluated in state.json), and a detached CPU-only
    `artifact_finalizer` completes + logs them to the same W&B run
    AFTER this GPU-owning process exits. The marker exists so that
    finalizer (and any auditor) has a durable, unambiguous record
    (actual steps, checkpoint hash, resolved argv, W&B run id) rather
    than re-deriving them from a possibly-still-writing directory.

    Caller must have already saved `out_path` (checkpoint) before
    calling this, else `checkpoint_md5` is recorded as null.
    """
    import hashlib

    marker_path = out_path.parent / f"{out_path.stem}.training_complete.json"
    md5 = (hashlib.md5(out_path.read_bytes()).hexdigest()
           if out_path.exists() else None)
    payload = {
        "schema": 1,
        "run_name": run_name,
        "task": task,
        "steps": int(steps),
        "checkpoint_path": str(out_path),
        "checkpoint_md5": md5,
        "wandb_run_id": run_id,
        "written_at": time.time(),
        "resolved_config": resolved_config,
    }
    tmp_path = marker_path.with_name(marker_path.name + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, default=str))
    tmp_path.replace(marker_path)  # atomic rename on the same filesystem
    return marker_path
