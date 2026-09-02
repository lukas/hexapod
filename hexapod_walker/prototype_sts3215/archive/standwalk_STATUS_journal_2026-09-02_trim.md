# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~00:4x (idle-kick triage: read 3/4 duration-mismatch
quartet flat-only `eval_done_gate_session` verdicts — `durctrl-canary`
train-1 DONE, `durfix-canary` train-3 DONE, `durfix-canary-s1` train-4
DONE; `durctrl-canary-s1` train-2 STILL RUNNING, ~2h45m elapsed vs
~20-40min for the other three — pod is heavily CPU-contended (122
python procs incl. 3 OTHER concurrent eval jobs for the same
checkpoint: mixedsession/gate/owncfg, likely another cycle's reads;
left running, not killed, per "trust only mechanical state"/don't
fight concurrent-cycle traffic).

**FINDING: the quartet's own pre-registered PASS/PARTIAL/FAIL text
does not cleanly resolve — DIG-IN, not closeable this cycle** (see
DIG-IN line below). Per-episode analysis (pulled `report.json` per
dr0+owndr pass, not just the summary — walk-segment terminations
`seq_end_seg_mode=='walk'`, near-instant := `seq_end_t_s` within 2s of
that segment's own start):

| run | n_term | walk_term | near-instant/n_term | prog_med | slip_med | dir_err_med | gait_valid |
|---|---|---|---|---|---|---|---|
| durctrl-canary (control) | 24 | 10 | 6/24=25% | 0.051 | 12.465 | 75.1° | 0.444 |
| durfix-canary (seed0) | 21 | 18 | 15/21=71% | 0.141 | 9.756 | 72.0° | 0.379 |
| durfix-canary-s1 (seed1) | 24 | 13 | 10/24=42% | 0.291 | 5.985 | 57.6° | 0.381 |

Gate text: PASS needs near-instant terms drop MEANINGFULLY below the
pre-continuation baseline (16/22=73%|21/22=95%) AND prog>=0.25 AND
slip<=4.0, a gap the control does not close. Neither durfix seed
clears all three; **durfix-canary is basically UNCHANGED from its own
baseline (71% vs 73%) and its walk-segment termination COUNT (18) is
almost double the control's (10)** — durfix reaches the walk segment
far more often (fewer rise-mode terminations: 3 vs 14) but then still
dies almost immediately once there. durfix-canary-s1 does show a real
near-instant improvement (95%->42%) and clears the progress bar
(0.291) but misses slip (5.985 vs cap 4.0). Reads as **PARTIAL at best
on seed1, matching-the-control (not beating it) on seed0** — an
inconsistent, seed-dependent result, not the clean PASS or clean FAIL
either gate branch predicted. `zero_falls=false`/`gate.pass=false` on
all three (as expected, mechanism-health canary only).

**Root-cause LEAD (code-read, not yet instrumented/confirmed) for why
duration alone wouldn't fix this even if it fully worked**:
`sim_env._seq_maybe_switch` installs the NEW segment family's
canonical `q_nom`/`z0`/`pad_z_ref` (`SEQ_FRAME_FAMILY = {"rise":
"belly", "walk": "plant", ...}`) at the exact switch tick — but the
blend window (`traj.height/roll/pitch`) only smooths the GOAL
trajectory, not the frame used to compute the observation itself
(`build_obs` reads `q - q_nom`, height rel. `z0`). `_seq_capture_frames`
probes "belly" from an all-zero joint pose and "plant" from the
standing `plant_deg` pose — two genuinely different canonical
baselines (the full rise range apart). At the rise->walk boundary the
robot's ACTUAL joints are near the plant pose (rise's whole job), so
`q_nom` teleporting from belly->plant makes the WALK segment's very
first observed joint-delta jump from "large, has been shrinking all of
rise" to "near zero" in one tick — a genuine input discontinuity at
the identical offset every switch, independent of how long the
segment that follows is allowed to run. This is consistent with (a)
terminations clustering at a FIXED short offset post-switch regardless
of duration budget, and (b) durfix (which only widened the ALLOWED
segment length, never touched the switch's frame-blend) not closing
the near-instant fraction. NOT YET instrumented (no per-tick obs-delta
trace pulled, no video frame-by-frame check of the exact switch tick) —
a hypothesis worth a dig-in cycle's time, not a repair to land blind.

**DIG-IN: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-
gradclip0p15-durfix-canary (+ -s1, + read durctrl-canary-s1 once its
flat-only session lands on train-2) — mixed/seed-inconsistent
duration-mismatch quartet result (one seed PARTIAL-improves, one seed
matches-or-worsens vs control) decides the mechanism-campaign fork
(widen duration further vs. fix the switch's frame-blend); a candidate
code-level cause (q_nom/z0 canonical-frame teleport at
`_seq_maybe_switch`, unblended unlike the goal trajectory) is
identified but not instrumented. Needs: per-tick obs-delta/action-norm
trace across 2-3 actual near-instant-terminating episodes (both
durctrl and durfix) plus frame-by-frame video at the switch tick,
before deciding whether to blend `q_nom`/`z0` across switches too or
whether this is a red herring.**

No same-recipe mechanism arm launched this cycle pending that dig-in,
per Next item 3's own standing bar. All other 5 tracks re-confirmed
DONE/retired/delivered this cycle (joystick DONE-gate met 08-23,
100Hz/mesh hardening explicitly non-blocking and deferred to this
track; amp DONE at M5 sim-scope, M6 hardware `[operator]`-only; cpg
DONE pending only an `[operator]` hardware-adoption call; walkcurr
RETIRED 08-31; todaypolicy DELIVERED 08-30) — standwalk is the fleet's
only track with agent-launchable open work right now, and its own
queue is this dig-in until it lands. 11/12 pods free
(`hexapod-mjx-train-0` still cluster-Pending, unrelated) — no filler
launched; a same-cycle blind mechanism arm before the dig-in reads the
switch-frame lead would burn a GPU-hour on a guess this cycle already
has a cheaper, code-level next step for.

Previous entry (2026-09-01 ~22:3x, triage: durfix-canary training finished;
durfix-canary-s1 ALSO quietly finished mid-cycle — launched its
missing flat-only read, completing the 4-arm quartet).
Plain English: `durfix-canary` (the assigned run) finished at 2M
steps, reward healthy (dips hard mid-run then partially recovers to
-353.8, same shape as both durctrl arms) — recorded `CANARY PASS (own
scope) - joint pending flatonly-read`, no new info since its own
flat-only read was already launched last cycle (train-3, still
running). While checking pod state, found `durfix-canary-s1` had ALSO
finished training on train-4 (ledger was stale `RUNNING`; checkpoint
synced 22:13) with its OWN flat-only read still un-launched (STATUS
Next#1 flagged this as the missing 4th arm) — launched it on train-4
this cycle (same flat-only cfg as durfix-canary, own checkpoint) and
verdicted the training run `CANARY PASS (own scope)` too (reward
healthy: dips then recovers to -240.5). **All 4 arms of the
duration-mismatch quartet are now running concurrently**
(durctrl-canary train-1, durctrl-canary-s1 train-2, durfix-canary
train-3, durfix-canary-s1 train-4), none landed yet — checked via
`ps aux` on each pod, not guessed. Other 5 tracks re-confirmed
green/retired/closed per the 15:1x fresh sweep, no new runnable work
found (`hexapod-mjx-train-0` is Pending on cluster CPU pressure,
already flagged as infra 21:26, not re-poked this cycle — 11 other
pods available and the standwalk queue itself has nothing further to
launch until these 4 reads land). Nothing else to do this cycle but
wait for the joint read; no filler launched.

Previous entry (2026-09-01 ~22:0x, triage: durctrl-canary +
durctrl-canary-s1 training finished; launched the flat-only
duration-mismatch reads) verbatim below.
Plain English: the two training runs finished (2M steps each,
matched no-cfg-change CONTROL twins of the duration-mismatch pair).
Both are mechanism-health canaries with no independent PASS/FAIL bar
(recorded `CANARY PASS (own scope) - joint pending flatonly-read` —
reward curves healthy: both dipped hard mid-run then self-corrected,
seed0 to 140.6, seed1 to a weaker 4.2, neither flat/blown-up). The
real decision needs the SAME flat-only `eval_done_gate_session` used
to find the duration-mismatch bug (`goal.rise_flat_frac=1.0
rise_partial_frac=0 rise_start_bank_frac=0 rise_rsi_frac=0`, n=8,
video), read jointly against the `durfix-canary` twins per Next item
1 below — durfix-canary had ALSO already finished training (checked
`launch_run.py status`: its pod was free, checkpoint synced) so its
flat-only read was launched too, alongside durctrl/durctrl-s1, so all
land together (durfix-canary-s1 is still training on train-4, its
read follows once it finishes). Launched on-pod (train-1 durctrl,
train-2 durctrl-s1, train-3 durfix), not yet read.

Previous entry (2026-09-01 ~21:0x, idle-kick: flat-only DONE-gate
sessions READ — decisive gate FAIL, and a campaign-reframing root
cause) verbatim below.
Plain English: the flat-only `eval_done_gate_session` panels queued
18:5x (`gradclip0p15-canary`/`-canary-s1`, n=32 each, literal cold-
flat starts) finished. **Gate FAILS both** (`zero_falls=false`, 22/32
terminated, all `over_current`), but the termination LOCUS flipped
from the rise segment (prior scoping-bug read) to the WALK segment:
16/22 (canary) and 21/22 (`-s1`) terms now land in `walk`. Reading the
raw per-episode JSON: every one of those walk-segment terminations has
`seq_end_t_s` in **10.3-12.3s** — i.e. within **0.3-2.3 seconds of the
walk segment's own start** (`t_s=10.0` in the plan) — with ALL SIX legs
sacrificed and `cur_max_a` pinned at the 2.64A safety cap. This is not
a steering failure; it looks and measures like an immediate shock at
the mode-switch boundary. **Root cause, found by config archaeology
(not speculation):** this checkpoint's own training recipe sets
`goal.mode_seq=0.75` (75% of episodes ARE sequence episodes) but uses
the DEFAULT `goal.mode_seq_segment_s_min/max=6.0/8.0` inside a flat
`--episode-seconds 30` — so it has **literally never experienced more
than ~8 continuous seconds of one mode**. `eval_checkpoint.py`'s own
default `--episode-seconds` is 10.0, and every isolated per-mode read
used to score this whole campaign (`probe_turn_authority`, the
"purewalk" canary reads, the standard DR-0/own-DR gate) rides
similarly short windows. **None of them exercise the DONE gate's
actual requirement: one continuous 60-second walk segment.** This
reframes the entire day's turn-authority mechanism campaign (kl-
rollback/value-warmup/yaw-credit/grad-clip) as tuned against a proxy
that may not predict the real gate at all. Even the walk segments that
don't crash barely move (`forward_dist_m` ~0.08-0.1m over a nominal
60s) with `course_err_1s_med_deg` ~100-109, `wrong_course_frac` ~0.6 —
consistent with the policy running fully outside its trained
distribution once a single mode sustains past ~8-10s, not merely
"steering badly." **Launched the direct test**, off the exact
`gradclip0p15-canary` checkpoint, 2M steps each: `...-durfix-canary`
(`--episode-seconds` 30->90, `goal.mode_seq_segment_s_min/max`
6/8->20/60 — the single coupled lever that lets a segment actually run
long) vs `...-durctrl-canary` (same warm-start/steps, no cfg change —
isolates "just more training" from "long-segment exposure"), PLUS
`--seed 1` twins of both (`...-durfix-canary-s1` / `...-durctrl-canary-
s1`, same recipe, per this campaign's own same-cycle-seed-twin
practice) so the verdict rests on n=2 seeds, not one. All four VERIFIED
RUNNING (train-3/train-1/train-4/train-2). Not yet read. wandb notes
added to both evaluated checkpoints (informational — does not reopen
their closed CANARY PASS/FAIL verdicts, narrowly scoped to
mechanism-health turn-authority).

Prior entries (RISE-DIET SCOPING BUG find, mixedsession audit close +
`eval_done_gate_session` build, `gradclip0p15-acq1` 38M PARTIAL read +
intermediate-checkpoint probe, grad-clip bracket close, `-canary-s1`
seed split, klrolltight2 close, yaw-critic build) VERBATIM in
`archive/standwalk_STATUS_journal_2026-09-01_trim.md`.

## Next (meta 09-01 ~22:3x)

1. **Read the duration-mismatch fix quartet once the flat-only
   `eval_done_gate_session` (n=8, video, `goal.rise_flat_frac=1.0
   rise_partial_frac=0 rise_start_bank_frac=0 rise_rsi_frac=0`) lands**
   — ALL 4 checkpoints now have their read LAUNCHED and running:
   `durctrl-canary` (train-1), `durctrl-canary-s1` (train-2),
   `durfix-canary` (train-3), `durfix-canary-s1` (train-4, launched
   this cycle once its training was found finished). Nothing left to
   launch on this item — just needs the next cycle to read all 4
   `session_verdict.json`s jointly. DECISION: if `durfix`
   clears
   meaningfully fewer near-instant-onset (`seq_end_t_s` within ~2s of
   the walk segment's start) `over_current` walk-segment terminations
   than `durctrl`, AND its progress/slip/direction move toward the
   isolated-probe band while the control doesn't — duration-mismatch
   is CONFIRMED as (part of) the driver; escalate the fix (bigger
   `mode_seq_segment_s_max`, a real 60s-walk-segment training rung, or
   raise `--episode-seconds` further) and re-score every closed
   turn-authority mechanism verdict this campaign made through that
   lens (they were all read via short-window probes). If both arms
   land the same — the switch mechanism itself (state discontinuity at
   segment handoff) or long-horizon reward pricing is the real
   defect, not duration exposure; dig into `sim_env._seq_maybe_switch`
   / the reanchor-to-canonical-frame code next.
2. **Campaign reference artifact, DOWNGRADED:** the 2M
   `...-gradclip0p15-canary` checkpoint was the best isolated turn-
   authority + walk-quality SINGLE-MODE combination found this
   campaign, but item 1's flat-only DONE-gate read is now DECISIVE
   FAIL evidence (own six-legs-sacrificed over_current collapse
   ~0.3-2.3s into every walk segment) — it is NOT yet usable as a
   stage-2 walk teacher until the duration-mismatch question (item 1)
   is resolved. Do not adopt it for distillation before that read.
3. **Standing bar, SUSPECT pending item 1:** the `probe_turn_authority
   >=0.10 both signs` bar assumed short-window turn-authority predicts
   the real gate; today's finding says it may not (the checkpoint that
   hit the campaign-best turn-authority number still catastrophically
   fails the literal 60s-walk DONE gate). Do not fund another short-
   probe-scored mechanism arm before item 1 answers whether the probe
   itself is the wrong instrument.
4. **Closed:** update-size constraints (freeze/value-warmup/
   kl-rollback), reward pricing, exploration magnitude, anchor
   dose/isolate-update, turn-skip, yaw-credit with NO clip, clip=0.5,
   clip=2.0, acquisition-scale retention of clip=0.15 (`-acq1` 38M
   PARTIAL: turn authority+stability hold, walk quality regresses vs
   the 2M canary), the mixedsession-audit landmine (root cause =
   repeating-cycle statistics, not a cfg bug), and the mixed-diet
   `eval_done_gate_session` read (own-cfg RSI/bridge/crouch rise-start
   mix, superseded by the flat-only read above; see archive).

> Journal archives (VERBATIM): pre-08-30 in
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`; 08-30 through
> 09-01 ~15:0x in `archive/standwalk_STATUS_journal_2026-09-01_trim.md`.
> Current state = newest Update at the TOP; don't act on archived Next.
