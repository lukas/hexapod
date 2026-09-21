# walkcurr-rlonly-fs-bisect-drv-safewiden6-acq1-50hz — GO/NO-GO (2026-09-21 packaging cycle)

## Verdict: GO for simulation/export readiness as a fully-packaged FALLBACK candidate to `slew-smooth-s0` (not a promotion over it). NOT a physical-acceptance verdict.

One plain sentence: `walkcurr/STATUS.md`'s 2026-09-21 ~07:3x entry closed
the fs-bisect safe-widen bisection for good and named repackaging this
checkpoint's rot60/lifecycle sub-bundles (the same treatment
`slew-smooth-s0` already received at ~04:2x) as its own optional,
unclaimed, low-cost CPU-only follow-up "so it is a fully packaged
fallback candidate if slew-smooth-s0 ever needs replacing" -- this
cycle did that.

## Why this cycle did this (gap it closes)

15/15 GPU slots free, empty backlog, and every track's own latest
STATUS independently closed pending Robot Lab, an operator scope
ruling, or a genuinely new structural design not yet conceived
(surveyed fresh via `ops.sh board` + each track's own head). The
walkcurr track's own newest entry named this exact packaging gap as
concrete and agent-doable; nobody had picked it up yet. Doing it turns
a bare "confirmed budget-trained DR-robustness candidate" verdict into
a fully evidenced, decision-ready artifact matching the project's own
established schema -- the same discipline `slew-smooth-s0` itself
received one promotion cycle earlier.

## What shipped this cycle

1. **`rl_move/sim/cfg_recipe_walk50hz_fs_bisect_drv_safewiden6_acq1.py`**
   (+5 tests): versioned `--cfg-set` recipe for this checkpoint,
   verbatim from `ops.sh entry cw-walk50hz-fs-bisect-drv-safewiden6-acq1`,
   mirroring the `cfg_recipe_walk50hz_slew_smooth_s0.py` sibling module
   1:1 (same DR-field exclusion convention, extended docstring
   explaining why the one differing always-on key, `dr.latency_scale`,
   is inert at eval's own dr-scale=0.0 either way).
2. **`--walk-recipe safewiden6_acq1` choice on
   `eval_lifecycle_handoff_rlonly.py`** (default `rlonly_v2` unchanged,
   bit-exact) so the lifecycle-composition tool can build `env_walk`
   from this checkpoint's own real cfg contract too.
3. **Exported the np policy**: `linux_control/policies/
   walkscratch_walk50hz_fs_bisect_drv_safewiden6_acq1.json`, parity
   2.41e-07 (bar 1e-5).
4. **Ran the rot60 sustained-multiheading gate** (identical panel
   structure to `slew-smooth-s0`'s own: DR-0, 60s episodes, --rot60,
   per-mode 4, det+sto x walk/walk_startjitter): **16/16 gait_valid,
   0/16 falls** across all 4 panels -- ties `slew-smooth-s0`'s own
   result exactly.
5. **Ran the composed lifecycle full-heading panel** (identical
   8-heading x2-episode baseline/candidate structure): found a
   genuinely DIFFERENT result shape from `slew-smooth-s0`'s own panel
   -- see "Honest finding" below.
6. **Wrote this manifest** (`transfer_manifest.json`, same schema as
   the parent bundle and `slew_smooth_s0`).

## Honest finding: rot60's effect here is real but smaller-in-kind than on slew-smooth-s0

`slew-smooth-s0`'s own composed full-heading panel showed the RAW
(rot60 off) checkpoint failing `gait_valid` outright at h+-90/h135/
h-135 (11/16) -- the chronic leg-sacrifice class this whole saga is
about. This checkpoint's RAW baseline does **not** reproduce that:
16/16 `gait_valid`, 0/16 falls at every heading, even off-axis. That
is plausibly the 5-group DR-widen training itself partially mitigating
the sacrifice mechanism (not proven causally here, just observed) --
worth flagging, not worth over-claiming.

But `gait_valid` alone hides a real residual: at h135/h180/h-135 the
RAW baseline's own `dist_m` collapses to 0.03-0.42m (near-stationary)
vs 0.65-1.02m on-axis -- the policy is technically cycling all six legs
(hence `gait_valid=True`) but making almost no net progress off-axis.
Wrapping the SAME checkpoint in `rot60.Rot60Policy` (zero retrain)
restores off-axis `dist_m` to 0.77-0.95m, matching the on-axis band,
with 0/16 falls in both arms. So rot60 is still a free, real
improvement on this checkpoint -- just a PROGRESS fix here rather than
a gait-validity rescue, a materially different (milder) failure
signature than the one `slew-smooth-s0`/`crutchoff-s0` showed. Do not
cite this checkpoint as a second independent confirmation of the exact
chronic-sacrifice mechanism; it is evidence of a related but distinct,
lesser instance.

## TODAY bars (same rubric bundle_rlonly_v2/slew_smooth_s0 use)

- Clean `rl_only` training lineage: PASS -- plain warm-start of an
  already-clean lineage, no demonstration data, no scripted role.
- Reproducible non-interactive sim evidence: PASS -- own DR-0 gate
  (n=6/mode, 21/24, already recorded at promotion), rot60 sustained
  panel (n=4/mode x4, 16/16), composed-lifecycle full-heading panel
  (n=2/heading x8 x2 arms) all committed.
- Video: NOT re-rendered this cycle (the numeric panels above are the
  evidence; a video pass is a further optional step, not required for
  this packaging gap).
- Off-forward limitation: PRESENT but MILDER than the reference
  checkpoint's own signature (progress-only, not gait-validity) --
  OPTION available (rot60 wrap, validated through the composed
  rise+hold->walk handoff, same as the parent).
- DR-robustness margin: this candidate's own reason to exist -- 21/24
  own gate vs `slew-smooth-s0`'s 23/24, wider mass/contact_stiff/
  kv+vel/latency/com_offset ranges.
- Physical acceptance: NOT CLAIMED -- sim-only, no robot access.

Evidence: `transfer_manifest.json` (this directory);
`logs/ckpt_eval/cw_walk50hz_fs_bisect_drv_safewiden6_acq1_gate/report.json`;
`logs/ckpt_eval/cw_walk50hz_fs_bisect_drv_safewiden6_acq1_rot60_sectorstop60s/report.json`;
`logs/ckpt_eval/lifecycle_rot60_fullheading_panel_safewiden6acq1_20260921/`;
`rl_move/sim/cfg_recipe_walk50hz_fs_bisect_drv_safewiden6_acq1.py`.
