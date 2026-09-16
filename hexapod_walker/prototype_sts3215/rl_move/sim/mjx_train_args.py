"""CLI validation and schedule parsing for ``train_ppo_mjx``.

Activation lookup, the mutually-exclusive-flag validators (gSDE, GRU
variants), the ``--log-std-final`` / ``--clip-range-final`` anneal spec
parsers and evaluators, the training-episode-length resolver and the
argv fixup that lets ``--log-std-final`` take a negative value.

Moved verbatim out of train_ppo_mjx.py (which re-exports these names).
"""
from __future__ import annotations


def _activation_fn(name: str):
    """Map an --activation-fn name to the torch activation class.

    walkcurr track (operator order 20260823T154657Z, recovering the
    lost Kawawa-2022 desktop trainer support canonically): the paper's
    prior-free policy uses ELU heads. Default flag value "" never
    reaches here (the caller skips the policy_kwargs entry entirely),
    so existing lineages stay bit-exact.
    """
    from torch import nn
    table = {"tanh": nn.Tanh, "relu": nn.ReLU, "elu": nn.ELU}
    try:
        return table[name]
    except KeyError:
        raise SystemExit(f"--activation-fn {name!r} not in "
                         f"{sorted(table)}") from None


def _validate_use_sde_scratch_only(use_sde: bool, init_from,
                                    init_from_actor_only: bool,
                                    init_from_policy_backbone: bool) -> None:
    """--use-sde (gSDE) only applies to from-scratch/transplant builds,
    mirroring --activation-fn's own restriction: a plain --init-from
    warm start keeps the checkpoint's own exploration mode (use_sde is
    baked into the saved policy, not something a CLI flag can safely
    override post-hoc without touching PPO.load's kwargs). Pulled out
    of main() as a pure function so it is unit-testable without mujoco/
    GPU. No-op (returns None) whenever the combination is legal.
    """
    if not use_sde:
        return
    if init_from is not None and not init_from_actor_only \
            and not init_from_policy_backbone:
        raise SystemExit("--use-sde only applies to from-scratch/"
                         "transplant builds; a plain --init-from "
                         "warm start keeps the checkpoint's own "
                         "exploration mode")


def _validate_gru_dual_log_std_split(log_std_split: bool,
                                     gru_dual: bool) -> None:
    """--gru-dual-log-std-split (a second learnable log_std_b for core
    B/stance) only makes sense on DualGruActorCriticPolicy — there is
    no core B to give a std to otherwise. Pulled out of main() as a
    pure function so it is unit-testable without mujoco/GPU (mirrors
    _validate_use_sde_scratch_only above). No-op when off (default).
    """
    if log_std_split and not gru_dual:
        raise SystemExit("--gru-dual-log-std-split requires --gru-dual")


def _validate_gru_triple(gru_triple: bool, gru_dual: bool,
                         gru_experts: bool, init_from,
                         init_from_actor_only: bool,
                         init_from_policy_backbone: bool,
                         mode_onehot: float,
                         mode_onehot_turn_cmd: float) -> None:
    """--gru-triple (gru_policy.TripleGruActorCriticPolicy) is a
    WARM-START-ONLY architecture (standwalk item-2 escalation, 09-04):
    it exists to specialize an already-decent walk core onto pure-turn
    ticks, not to learn locomotion from scratch, so it requires a
    Dual-policy --init-from (checked here structurally; the actual
    isinstance check happens once the checkpoint is loaded, in
    dual_to_triple_transplant). Pulled out of main() as a pure function
    so it is unit-testable without mujoco/GPU, mirroring
    _validate_gru_dual_log_std_split/_validate_use_sde_scratch_only.
    No-op (returns None) when --gru-triple is off (default).
    """
    if not gru_triple:
        return
    if gru_dual or gru_experts:
        raise SystemExit("--gru-triple is exclusive with --gru-dual/"
                         "--gru-experts")
    if init_from is None:
        raise SystemExit("--gru-triple requires --init-from (a "
                         "DualGruActorCriticPolicy checkpoint — Triple "
                         "is a warm-start-only architecture, see "
                         "gru_policy.dual_to_triple_transplant)")
    if init_from_actor_only or init_from_policy_backbone:
        raise SystemExit("--gru-triple uses its own dedicated "
                         "Dual->Triple transplant; drop --init-from-"
                         "actor-only/--init-from-policy-backbone")
    if float(mode_onehot) <= 0.0:
        raise SystemExit("--gru-triple requires --cfg-set "
                         "obs.mode_onehot=1 (the policy routes by the "
                         "obs-tail skill one-hot)")
    if float(mode_onehot_turn_cmd) <= 0.0:
        raise SystemExit("--gru-triple requires --cfg-set "
                         "obs.mode_onehot_turn_cmd=1 (otherwise the "
                         "\"turn\" slot never lights and core_t trains "
                         "on nothing)")


def _parse_log_std_anneal_specs(log_std_final, log_std_anneal_core,
                                log_std_anneal_frac):
    """Parses --log-std-final/--log-std-anneal-core/--log-std-anneal-
    frac into a list of (core, final, frac) triples, one per anneal
    callback to construct.

    Pulled out of main() as a pure function so it is unit-testable
    without mujoco/GPU (mirrors _validate_use_sde_scratch_only above).

    Born from the standwalk dualbc5-turncap lineage (08-31): every
    prior canary in that mechanism search could anneal only ONE
    core's log_std per launch (--log-std-anneal-core stance, cooling
    stance while the walk core's log_std sat untouched under pure PPO
    gradient) -- there was no way to ALSO give the walk core its own
    guaranteed-to-move exploration schedule (raising it, not lowering
    it) in the SAME run without silently overwriting the stance
    anneal. Comma-separated lists on all three flags let the caller
    target independent (core, final, frac) triples in one launch,
    e.g. `--log-std-final=-0.7,-4.0 --log-std-anneal-core=walk,stance
    --log-std-anneal-frac=0.1,0.5`.

    Single (non-comma) values are the pre-existing behavior, bit-
    exact: returns exactly one triple, matching every already-launched
    recipe's CLI byte-for-byte. `log_std_anneal_frac` broadcasts a
    single value across multiple (core, final) pairs (nearly every
    existing single-anneal launch never sets it explicitly, so
    defaulting one frac across N pairs is the least-surprising
    reading); `log_std_anneal_core` broadcasts "all" the same way only
    when a single core is requested for multiple finals is NOT the
    intent -- REFUSES ambiguous input instead (mismatched list
    lengths, "all" combined with >1 pair, unknown core name, or a
    duplicate core) rather than guessing.

    Returns [] when log_std_final is None (the anneal is off,
    unchanged from every pre-08-31 call site's `is not None` gate).
    """
    if log_std_final is None:
        return []
    finals = [float(x) for x in str(log_std_final).split(",")]
    cores = [c.strip() for c in str(log_std_anneal_core).split(",")]
    fracs = [float(x) for x in str(log_std_anneal_frac).split(",")]
    n = len(finals)
    if len(cores) == 1 and n > 1:
        cores = cores * n
    if len(fracs) == 1 and n > 1:
        fracs = fracs * n
    if len(cores) != n or len(fracs) != n:
        raise SystemExit(
            "--log-std-final/--log-std-anneal-core/--log-std-anneal-"
            f"frac list-length mismatch: {n} final(s), {len(cores)} "
            f"core(s), {len(fracs)} frac(s) — each must be a single "
            "value (broadcast) or match the others' count exactly")
    bad_cores = [c for c in cores
                if c not in ("all", "walk", "stance", "turn")]
    if bad_cores:
        raise SystemExit(
            f"--log-std-anneal-core: unknown core(s) {bad_cores!r} — "
            "must be 'all', 'walk', 'stance', or 'turn' (the last "
            "only targetable on TripleGruActorCriticPolicy)")
    if n > 1 and "all" in cores:
        raise SystemExit(
            "--log-std-anneal-core: 'all' cannot be combined with "
            "other cores in a multi-anneal list (ambiguous overlap) "
            "— name the specific cores instead, e.g. 'walk,stance'")
    if len(set(cores)) != len(cores):
        raise SystemExit(
            f"--log-std-anneal-core: duplicate core(s) in {cores!r} "
            "— each anneal callback needs its own distinct target")
    return list(zip(cores, finals, fracs))


def _parse_clip_range_anneal(clip_range_final, clip_range_anneal_frac,
                             clip_range_init: float):
    """Validates --clip-range-final/--clip-range-anneal-frac.

    Pure function (unit-testable without mujoco/GPU, like
    _parse_log_std_anneal_specs above). Returns None when
    clip_range_final is None — the anneal is OFF, no callback is
    constructed, bit-exact legacy behavior. Otherwise returns
    (final, tail_frac) after refusing nonsensical requests: a
    non-positive final clip range (would zero every PPO gradient), a
    final ABOVE the constructor value (this is a tail TIGHTENING
    schedule — widening the clip late is the instability we are
    trying to prevent, never a fix), or a tail fraction outside
    (0, 1].

    Born from the stand50hz dqfix/cont2m/stdfloor2 dig-in (09-11): the
    dqfix stance recipe learns rise+hold+lower by ~5M steps, then a
    single late PPO update event (train/approx_kl 0.36 with
    clip_fraction 0.32-0.42, std annealed to its -4.0 floor 3M steps
    earlier) scrambles a clause. target_kl=0.02 was already ON and did
    not prevent it — SB3's KL check fires per-minibatch AFTER the
    damaging optimizer.step(). Shrinking the clip range across the
    training tail bounds the per-minibatch movement itself.
    """
    if clip_range_final is None:
        return None
    final = float(clip_range_final)
    frac = float(clip_range_anneal_frac)
    init = float(clip_range_init)
    if final <= 0.0:
        raise SystemExit(
            f"--clip-range-final {final}: must be > 0 (a zero/negative "
            "clip range zeroes every PPO policy gradient)")
    if final > init:
        raise SystemExit(
            f"--clip-range-final {final}: must be <= the launch clip "
            f"range {init} — this is a tail TIGHTENING schedule only")
    if not (0.0 < frac <= 1.0):
        raise SystemExit(
            f"--clip-range-anneal-frac {frac}: must be in (0, 1] "
            "(fraction of --steps forming the annealed TAIL)")
    return final, frac


def _clip_range_anneal_value(num_timesteps: int, steps: int,
                             init: float, final: float,
                             tail_frac: float) -> float:
    """Clip-range value at ``num_timesteps`` under the TAIL schedule.

    Holds ``init`` for the first (1 - tail_frac) of ``steps``, then
    anneals linearly to ``final`` over the last ``tail_frac`` of
    ``steps``, then holds ``final``. TAIL semantics (unlike the
    log-std anneal, which starts at step 0): early acquisition keeps
    the full clip range for fast learning; only the
    late, low-exploration refinement window gets tightened.
    """
    start = max(0, int(round((1.0 - float(tail_frac)) * int(steps))))
    denom = max(1, int(steps) - start)
    p = (int(num_timesteps) - start) / float(denom)
    p = min(1.0, max(0.0, p))
    return float(init) + p * (float(final) - float(init))


def _resolve_training_episode_seconds(training_episode_seconds,
                                       episode_seconds: float) -> float:
    """Normalizes --training-episode-seconds vs --episode-seconds.

    Pulled out of main() as a pure function so it is unit-testable
    without mujoco/GPU (mirrors _validate_use_sde_scratch_only above).
    ``None`` (the CLI default) resolves to ``episode_seconds`` —
    bit-exact with the pre-flag behavior, where the training env
    kwargs' ``getattr(args, "training_episode_seconds",
    args.episode_seconds)`` fallback always hit the same value because
    the attribute did not exist yet. A non-positive override is
    rejected (raises SystemExit, matching argparse's own ap.error
    convention) rather than silently producing a zero/negative-length
    episode.
    """
    if training_episode_seconds is None:
        return episode_seconds
    if training_episode_seconds <= 0.0:
        raise SystemExit("--training-episode-seconds must be > 0")
    return training_episode_seconds


def _fixup_log_std_final_argv(argv: list[str]) -> list[str]:
    """Rewrites a bare `--log-std-final -0.8,-4.0` two-token argv into
    the single-token `--log-std-final=-0.8,-4.0` form.

    Pure function so it's unit-testable without argparse/mujoco
    (mirrors _validate_use_sde_scratch_only above). Born from the
    standwalk dualbc5-turncap-stdwalk-mild launch crash (08-31):
    argparse's built-in negative-number heuristic only recognizes a
    BARE negative number (regex `-\\d+$|-\\d*\\.\\d+$`) as a value
    token — a comma-list value like `-0.8,-4.0`
    (`_parse_log_std_anneal_specs`'s multi-core format) does not
    match, so argparse treats it as an unrecognized option string and
    crashes the whole trainer process pre-boot with "--log-std-final:
    expected one argument". The launch_run.py respec/launch harness's
    `--arg='--log-std-final=...'` convention always re-emits flag and
    value as SEPARATE argv tokens (`set_flag`'s `args.extend([flag,
    val])`), so the "=" joining the caller wrote is lost before this
    process ever sees argv — the fix has to live here, not in the
    caller. Only touches `--log-std-final` immediately followed by a
    token starting with a single `-` (a value) but not `--` (another
    flag — every option in this parser is long-form); every other
    token, including a bare single negative number (already argparse-
    safe) or any other flag, passes through untouched.
    """
    out: list[str] = []
    i = 0
    n = len(argv)
    while i < n:
        tok = argv[i]
        if (tok == "--log-std-final" and i + 1 < n
                and argv[i + 1].startswith("-")
                and not argv[i + 1].startswith("--")):
            out.append(f"{tok}={argv[i + 1]}")
            i += 2
            continue
        out.append(tok)
        i += 1
    return out
