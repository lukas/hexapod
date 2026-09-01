# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-01 ~22:3x (triage: durfix-canary training finished;
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

## Goal (operator, 08-24 evening)

Retrain the best rising-and-lowering (stance) model on the NEW mesh
MuJoCo model at 100 Hz, then use it as a teacher to distill rise/lower
plus the best walking behavior into one policy. Product: a single
mesh-family 100 Hz policy that, starting from sit, rises, follows a
randomized 60 s joystick session with zero falls, and lowers back.

## Binding constraints (why this is a retrain, not a resume)

- Families do NOT transfer (CURRENT_TRUTHS "SIM MODEL FAMILIES"): the
  legacy stance champion `ppo_goal_cw_stance_dr10` and walk champion
  `ppo_goal_cw_dep_bcgait4_phasedir9_stotight45_seed13` are
  primitive-family 25 Hz policies. NO `respec --from` / warm-start of
  them onto mesh — stage 1 is a recipe rerun on the new model.
- New launches already get `control.hz=100` (launcher-injected) and
  `env.model_source=mesh` (the default) — do not pin legacy values
  here, and never pin `model_source=primitive` in this track.
- Legacy champions MAY be queried as teachers (same obs layout), but
  they carry 25 Hz action scale and primitive dynamics: any
  distillation mechanism must handle the 25->100 Hz gap (query at
  25 Hz + interpolate, distill trajectories, DAgger with rate
  conversion, ...) and must MEASURE whether primitive-trained advice
  is good on mesh dynamics before trusting it.

## Stage 1 — mesh/100 Hz stance retrain (rise + lower)

Recipe basis: the `stance_dr10` lineage recipe (exact cfg in the
ledger/W&B). The rise-reference machinery (`extract_rise_ref.py`,
rise bank) is green as of 08-24. Bank/semantics-check the stance
reward ON MESH before the first launch (mass went 2.104 -> 3.50 kg;
thresholds calibrated on primitive may rank behaviors differently).

GATE (pre-registered): stance panel rise/hold/lower (pod_eval stance
modes), n>=12, det+sto, DR-0 + own-DR: zero falls/tips, quiet hold
(no creep), rise/lower height tracking comparable to the legacy
champion's band. Absolute numbers shift with the +66% mass — the
first passing run's numbers become the recorded mesh reference band.

## Stage 2 — teacher distillation into the best walking model

Use the stage-1 policy as the rise/lower TEACHER. Walking source: the
joystick champion lineage (`stotight45-seed13`) or its mesh-era
successor if the joystick track's in-flight mesh arms produce one
first — either adoption is PRE-REGISTERED here, never a silent
teacher swap (cpg containment rule applies). Mechanism is
cycle-designed (BC clone + RL fine-tune a la bcgait, KL-to-teacher,
phase-scheduled multi-teacher, ...); every mechanism arm pre-registers
its gate and a matched control.

DONE GATE (the track's): ONE mesh-family 100 Hz policy, from sit:
rise -> randomized 60 s joystick command script -> lower to sit.
Zero falls, directions followed, slip/m within the joystick band
(<=~2.9), held-out panel n>=12, det+sto, DR-0 + own-DR.
`eval_joystick_gate` covers the walk segment; the sit->rise->walk->
lower session harness is stage-2 tooling to build.

## Landmines

- Sim only — hardware stand/plant transfer stays operator-owned.
- No stage-2 arm may warm-start from a primitive checkpoint.
- The joystick track owns generic mesh walking; this track owns
  rise/lower + the unification. Coordinate via STATUS, don't
  duplicate its mesh conversion arms.
- **Tooling flag (09-01) CLOSED:** the standing `_mixedsession`
  harness's REPEATING rise<->walk<->lower grammar compounds any
  single-rise fragility into a misleadingly total session failure
  (see Update) — treat it as a mechanism-robustness stress test, NOT
  the DONE-gate instrument; use `eval_done_gate_session`
  (`ops.sh donegatecmd`) for the actual one-cycle DONE-gate read.

