# walkcurr-rlonly-widen8-crutchoff-s0-warmadapt-50hz-acq1-v2 + rot60 — GO/NO-GO (2026-09-18 packaging cycle)

## Verdict: GO for sim-demo readiness as an ENVELOPE-EXTENSION option (same checkpoint, inference-time frame wrapper). NOT a physical-acceptance verdict, and NOT a claim that this beats `bundle_rlonly_v2`'s own tight forward-tracking numbers.

One plain sentence: `bundle_rlonly_v2`'s own registered physical-trial plan
tells Robot Lab to AVOID sustained off-forward headings because the raw
policy chronically sacrifices a front leg there (13/13 mechanism classes
closed, no fix in flight as of 2026-09-10); this packages already-built,
already-validated evidence (2026-09-13/14, scattered across `walkcurr/
STATUS.md` prose and orphaned eval artifacts, never before collected into
a transfer-manifest decision artifact) that wrapping the SAME checkpoint in
the mesh-verified `rot60.Rot60Policy` exact-symmetry canonicalizer removes
that specific catastrophic failure mode across a 16-episode sustained
(60s/episode) full-heading gate panel — 0 falls, gait_valid 15/16 (vs. the
raw policy's own chronic every-off-forward-heading collapse).

## Why this cycle did this (gap it closes)

Nothing else was runnable this cycle (empty backlog, 15/15 GPU free, every
one of the 7 tracks independently re-confirmed closed pending Robot
Lab/operator per the board digest and this cycle's own fresh reads,
walkyaw itself fully parked as of the ~03:1x entry earlier today). Rather
than declare idle, surveyed `walkcurr/STATUS.md` for a named,
evidence-backed, zero-GPU gap and found one: the 09-17 ~18:2x entry already
states in passing that "`bundle_rlonly_v2` + rot60 already gives the
`rl_only` walk role near-parity full-circle TRANSLATION," and the 09-14
~12:0x entry closed rot60's own last confirmation item with the explicit
note "the one piece ... left open before a rot60-composed demo can go in a
physical transfer manifest" — but no such manifest was ever actually
written. This packages it, exactly the pattern `todaypolicy`'s
`composed_turn_role/` sub-bundle already established for a different
composed capability on a different track.

## What shipped this cycle

No code change (every mechanism — `rot60.py`, its `--rot60`/`--rot60-walk`
CLI flags in `eval_checkpoint.py`/`drive_video.py`/`web_server.py`, the
np-export parity probe — was already built, tested and snapshotted on
2026-09-13/14). Pure packaging + one fresh honest read of a previously
unread-in-full eval artifact:

1. Re-read `logs/ckpt_eval/cw_walk50hz_rlonly_crutchoff_s0_warmadapt_acq1_rot60_sectorstop60s/report.json`
   (confirmed already logged 2026-09-13 ~16:41 in `RL_LOG.md` as "CONFIRMS
   Canary A survives sector-boundary transients + stop/restart, 0 falls,
   gait_valid 15/16" — this cycle re-derived the per-episode numbers from
   the raw JSON rather than trusting the one-line summary, since no prior
   STATUS.md entry had actually broken out the per-mode breakdown or the
   `success`/`vel_err_mean` fields).
2. Found the one substantive thing the prior one-line log entry did NOT
   surface: `success` (this eval's own strict `vel_err_mean<=0.03` bar) is
   FALSE in all 16 episodes, and traced WHY — the panel's default speed
   draw (`speed_mean_m_s` 0.11-0.15) sits well above the 0.06 m/s point the
   checkpoint was actually demoed/wrapped-tested at elsewhere, so this is a
   speed-regime mismatch in the eval's own command distribution, not
   evidence the rot60 wrap breaks tracking. Recorded as an open caveat
   (`transfer_manifest.json.open_caveats_not_hidden`) rather than
   suppressed or over-claimed either way.
3. Wrote `transfer_manifest.json` (this directory) collecting: the
   physics-exactness tests, the SB3-vs-np-export parity probe (2.36e-07),
   both real interactive HTTP-joystick-session confirmations (zip + np
   export runtime paths), and the sustained-multiheading gate — all
   dated evidence that already existed, now in one decision-ready place.
4. Appended (not overwrote) a pointer to this sub-bundle in the parent
   `bundle_rlonly_v2/GO_NOGO.md`'s "Next" section.

## TODAY bars (same rubric bundle_rlonly_v2 uses)

- Clean `rl_only` training lineage: PASS (unchanged — rot60 is an
  inference-time wrapper, zero new trained parameters, zero demonstration
  data; same checkpoint as the parent bundle).
- Physics-exactness of the frame map on the actual deployable model:
  PASS (`test_rot60_mesh.py`, mesh model, not just the legacy primitive).
- SB3-vs-np-export runtime parity under the wrapper: PASS (2.36e-07,
  matches the project's own ~2e-7 floor).
- Reproducible interactive session, both runtime paths, 0 falls: PASS
  (both `rlonly_v2_websession_rot60_{zip,npjson}_20260914` sessions).
- Removes the named chronic off-forward leg-sacrifice failure mode under
  SUSTAINED (60s), full-heading commands: PASS-WITH-ONE-EXCEPTION (15/16
  `gait_valid`, 0/16 falls — not claiming 16/16, the one exception is
  named plainly above).
- Tight velocity/heading tracking under rot60 at the SAME fixed 0.06 m/s
  point bundle_rlonly_v2's own demo uses: **RESOLVED 2026-09-18** (matched-
  contract rerun, `transfer_manifest.json`'s
  `matched_trained_contract_speed_check_2026_09_18`): 16/16 gait_valid,
  0/16 falls, in-band slip — BETTER than the original panel's 15/16. The
  strict `vel_err_mean<=0.03` "success" bar still reads FALSE, but that
  is now explained mechanistically (this checkpoint's own trained reward
  carries `k_track=0.0` — no active speed-tracking term, so it cruises at
  its natural ~0.13 m/s regardless of the nominal command, rot60 or not),
  not a rot60 defect or an untested speed regime. A matched with/without-
  rot60 control at the correct trained contract produced IDENTICAL
  numbers either way — rot60 is fully exonerated.
- Physical acceptance: NOT CLAIMED — no robot access from this process.

## Next

No open cloud-side item remains on this sub-bundle's own tracking
question (closed above). Robot Lab: this stays an OPTION layered on top
of `bundle_rlonly_v2`'s already-registered physical-trial plan, not a
replacement — the parent bundle's forward-biased envelope remains the
conservative default; this sub-bundle exists for whenever a wider
command range is wanted. Caution for any future eval of this or a
sibling checkpoint: build the `--cfg-set` list from that checkpoint's
own recipe module (e.g. `cfg_recipe_walk50hz_rlonly_v2.CFG_ARGS`), never
a hand-picked subset — an incomplete cfg-set silently falls back to the
wrong motor contract (control.hz=100/legacy bus defaults instead of the
trained 50Hz/4096-cps contract) and produces a spurious catastrophic
fall pattern that looks like a real regression until checked against a
matched-contract control (see the transfer_manifest.json caution note).

## UPDATE 2026-09-21: same OPTION re-verified on the promoted `slew-smooth-s0` reference (no retrain)

One plain sentence: `walkcurr/STATUS.md`'s 09-21 ~03:3x entry promoted
`cw-walk50hz-slew-smooth-s0` over this bundle's own `crutchoff-s0-
warmadapt-acq1` checkpoint as the walkcurr 50Hz hardware-transfer
reference, and this sub-bundle's own rot60 sustained-multiheading gate
had never been re-run against it — closed that gap this cycle, CPU-only,
zero retrain, same wrapper.

**What ran:** `rl_move/sim/cfg_recipe_walk50hz_slew_smooth_s0.py` (new,
mirrors this checkpoint's sibling recipe module 1:1, verbatim from
`ops.sh entry cw-walk50hz-slew-smooth-s0`) + the SAME sustained (60s)
sector-stop panel this sub-bundle's own `matched_trained_contract_
speed_check_2026_09_18` entry used (`--task joint_walk --modes walk
--per-mode 4 --episode-seconds 60 --dr-scale 0.0 --rot60`, full-circle
heading override), against `ppo_goal_cw_walk50hz_slew_smooth_s0.zip`.

**Result:** 16/16 `gait_valid`, 0/16 falls/terminations across all 4
panels (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto)
— matches or exceeds this sub-bundle's original 15/16 finding on the
superseded checkpoint. `roll_peak_deg` 7.0-11.4deg, `slip_per_m`
3.7-12.9 (in-band with the rest of this bundle's own numbers).

**Reading:** the rot60 envelope-extension OPTION transfers cleanly onto
the newly-promoted reference checkpoint — same zero-retrain wrapper,
same mesh-verified exact-symmetry argument (`rot60.py` never depended
on which walk checkpoint it wraps), no new caveat introduced. This does
NOT change the verdict above (still an OPTION layered on top, not a
replacement for the conservative forward-biased default) and does NOT
re-litigate the parent bundle's own physical-trial plan — it just keeps
this sub-bundle's evidence current with the promoted reference instead
of silently going stale.

Evidence: `logs/ckpt_eval/cw_walk50hz_slew_smooth_s0_rot60_sectorstop60s_speed006/report.json`;
`rl_move/sim/cfg_recipe_walk50hz_slew_smooth_s0.py`; `rl_move/tests/
test_cfg_recipe_walk50hz_slew_smooth_s0.py` (5 tests); see also
`bundle_rlonly_lifecycle_v1/slewsmooth_s0/` for the composed rise+hold
-> walk full-heading re-verification.

## UPDATE 2026-09-21 (later same day): same OPTION verified on the `safewiden6-acq1` fallback candidate too (no retrain)

Ran the identical rot60 sustained-multiheading gate (DR-0, 60s
episodes, per-mode 4, det+sto x walk/walk_startjitter) against
`cw-walk50hz-fs-bisect-drv-safewiden6-acq1` (the fs-bisect 5-group
safe-widen DR-robustness alternative, packaged this cycle as
`bundle_rlonly_v2/safewiden6_acq1/`): **16/16 gait_valid, 0/16 falls**
-- ties `slew-smooth-s0`'s own result. Full detail, including an
honest finding that this checkpoint's off-axis defect is a milder
progress-only issue (not the gait_valid-breaking sacrifice
`slew-smooth-s0` shows), in `bundle_rlonly_v2/safewiden6_acq1/
{transfer_manifest.json,GO_NOGO.md}`.

## UPDATE 2026-09-21 (later still): tracking-accuracy item CLOSED for BOTH packaged candidates — no new eval needed, the numbers were already sitting in cached report.json files

One plain sentence: the ~08:2x STATUS.md entry flagged "measure the rot60
sub-bundle's TRACKING ACCURACY at its fixed 0.06 m/s command point for both
packaged candidates ... never measured" as an open CPU-only item, but both
candidates' own `cfg_recipe_*` modules already pin
`goal.walk_speed_min_m_s=goal.walk_speed_max_m_s=0.06`, so the sustained
rot60 panels each candidate already has on record (`slew_smooth_s0`'s own
`_speed006` rerun; `safewiden6_acq1`'s `_rot60_sectorstop60s` panel from
this same day) ARE the fixed-0.06-m/s tracking measurement — this update
just pulls `vel_err_mean`/`speed_mean_m_s` out of the already-cached JSON
rather than running anything new.

**Numbers (n=16 episodes each, det+sto x walk/walk_startjitter):**

| candidate | speed_mean_m_s range | vel_err_mean range | success (vel_err<=0.03) | gait_valid |
|---|---:|---:|---:|---:|
| `slew-smooth-s0` | 0.119-0.140 | 0.052-0.072 | 0/16 | 16/16 |
| `safewiden6-acq1` | 0.119-0.153 | 0.053-0.086 | 0/16 | 16/16 |

**Reading:** both candidates reproduce the exact same pattern the
`crutchoff-s0-warmadapt-acq1` matched-contract check already explained
mechanistically on 2026-09-18: `reward.k_track=0.0` in every one of these
lineages' own trained cfg (confirmed directly in
`cfg_recipe_walk50hz_slew_smooth_s0.py` and
`cfg_recipe_walk50hz_fs_bisect_drv_safewiden6_acq1.py` — both carry the
identical line), so there is no active velocity-tracking reward term and
each checkpoint cruises at its own natural ~0.12-0.15 m/s regardless of the
0.06 m/s nominal command, independent of rot60. The strict
`vel_err_mean<=0.03` "success" bar therefore reads FALSE for both, exactly
as expected from that mechanism — this is NOT a rot60 defect, NOT a
regression vs the reference checkpoint, and NOT a new finding requiring
action; it is confirmation that the already-closed 2026-09-18 explanation
generalizes losslessly to both packaged fallback/alternative candidates.
`gait_valid` (the actual walking-quality bar this sub-bundle exists to
protect) stays 16/16 for both at this exact command point, matching each
candidate's own headline result.

No new eval run, no code change, no GPU spend. This closes the
`rot60_fullcircle` sub-bundle's own open item in full — no further tracking
-accuracy question is open on any of its three now-packaged checkpoints
(`crutchoff-s0-warmadapt-acq1`, `slew-smooth-s0`, `safewiden6-acq1`).

Evidence: `logs/ckpt_eval/cw_walk50hz_slew_smooth_s0_rot60_sectorstop60s_speed006/report.json`;
`logs/ckpt_eval/cw_walk50hz_fs_bisect_drv_safewiden6_acq1_rot60_sectorstop60s/report.json`;
`rl_move/sim/cfg_recipe_walk50hz_slew_smooth_s0.py` (`reward.k_track=0.0`);
`rl_move/sim/cfg_recipe_walk50hz_fs_bisect_drv_safewiden6_acq1.py`
(`reward.k_track=0.0`).
