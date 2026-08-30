# walkcurr — prior-free walking curriculum (Kawawa-2022 lineage)

**Phase-sv line (operator directive 2026-08-29 ~16:5x, executed by the
operator-side agent):** a gait CLOCK is allowed for the
`cw-walkcurr-phase-sv-*` line only (founding rule (a) superseded for
this line; these runs are NOT prior-free — still no BC/imitation/AMP/
warm-start, random init, 18 joint targets). First wave: `-obsonly-s0`
(phase obs only) + `-contact-s0` (obs + k_phase_contact=0.03), exact
respec clones of `cw-walkcurr-pf-central-sv-s0-rr2`, which is REUSED as
the no-phase control (parity by clone construction — no duplicate
control launched). WALKCURR_PHASE_SV bank green before launch.
Lightweight pre-registration per operator (no decision tree); Arm B
name/dose + seed-replicate-on-positive inferred from the truncated
directive and recorded in the ledger entries.

Registered 2026-08-23 by operator order (MCP focus note
20260823T154657Z) after the `cw-kawawa2022-pf-flat1` FAIL. Plain
English: teach a from-scratch PPO policy (no gait clock, no BC
teacher, no motion prior) to walk by climbing a curriculum that starts
with ONE fixed forward command and only widens after certified passes.

**STALE-FLAG RETRACTED (08-25 ~17:0x, ledger-verified):** a flag
placed here 08-25 ~16:1x claimed the 08-23 ~21:3x rung-0 escalation
("build a rung-0 semantics bank, then launch the swing-dominant/
no-travel-charge diet") "was recorded but never executed" and invited
a future idle-capacity cycle to pick it up as runnable work. **That
reading is wrong — do NOT act on it.** Ledger facts: the rung-0 diet
WAS launched the same hour it was committed (`cw-walkcurr-pf-rung0-
swing3`/`-swing9`, created 08-23T21:41/21:43, both verdicted FAIL —
stork lean and airborne hover respectively; see the "rung-0 swing
income CLOSED" Now entry below), followed by RND-on-rung-0 arms
(`swing3-rnd1`/`-rnd3`, also FAIL). The "zero launches since
2026-08-24T03:50" observation is true but has the opposite meaning:
by 03:50 the campaign had exhausted EVERY rule-(a)-legal lever (14
mechanism/architecture/reset-diversity classes, tally in
`OPERATOR_QUESTIONS.md` q_20260824T0233Z, including the final
`shortep3`/`shortep8` pair — both FAIL), and the track deliberately
recorded itself as blocked: "no further walkcurr rung-1 arms will be
launched by the agent fleet until [the BC-kickstart question] is
answered." Idle capacity is NOT license to relaunch here; the wait is
a genuine `[operator]` ruling on the track's own founding rule (see
WAITING-ON), the closest analogue to the spend-approval carve-out.
Rebuilding a semantics bank for the already-refuted swing diet would
be filler.

## Now (2026-08-30 ~07:4x — graduated step-partial pretrain read: FAIL, CLOSES pretrain-staging 4/4; every operator-named non-BC lever now closed except the in-flight SAC tilt5 20M continuation)

Plain English: read the graduated step-completion pretrain pair the
prior cycle launched. Does giving partial credit for an incomplete
(sub-10mm) forward swing let a fresh-random-init policy discover real
stepping where the all-or-nothing `k_step_event`-only pretrain
(decleg/central-antifreeze-pretrain-s0, both FAIL) could not? **No.**
`cw-walkcurr-pf-decleg-antifreeze-pretrain-grad-s0` and its
centralized twin both verdicted **FAIL** — same static-stand-to-
park-floor basin, numerically near-identical to EACH OTHER (arch not
the confound, again) and to the pure-STEP pretrain pair (ep_len_mean
climbs the identical 63->547 shape; ep_rew_mean settles at 202.0
pure-STEP vs 202.9 graduated — the +0.9 delta is fully explained by
the graduated taper's own small nonzero income, not by any behavior
change). `env/reward_step_event` sat flat/noisy in [0.0026,0.0034]
for the ENTIRE 2M run in both arms — already at that value at the
FIRST logged checkpoint (786k steps), never a genuine rising trend;
`env/walk_speed` pinned at the same ~0.02 m/s static floor as every
other FAIL in this campaign (cmd 0.05-0.06). The taper widens the
credit-earning TARGET (a partial stride now earns something) but does
nothing to create exploration PRESSURE toward ever attempting one —
2M steps of PPO from random init still never samples a real
forward-projecting swing to reinforce. Prediction-if-false confirmed;
this closes pretrain-staging at **4/4 FAIL** (pure-STEP x2 archs +
graduated-taper x2 archs).

**Track-wide tally, all under the operator's 08-29 ruling
(q_20260824T0233Z, fb 20260829T145710_06f739 — BC-kickstart out of
bounds, 4 levers named in priority order: (i) decentralized per-leg,
(ii) plain-velocity/no-charge-stack SV diet, (iii) bigger one-shot
budget, (iv) off-policy SAC):** (i) decleg-sv 3 seeds + central-sv
control = 4/4 FAIL (08-29). (ii) is the SV diet itself, tested
throughout — no arm of it has ever escaped the static basin. (iii)
decleg/central population-budget sweep at 100M = 6/6 FAIL (this
morning). (iv) SAC-SV dose/settle-window branch = 7/7 FAIL (08-29
night), PLUS two self-invented forks tried on top of the same basin —
terrain diversity 2/2 FAIL, idle-charge lever 2/2 FAIL — PLUS this
track's own pretrain-staging fork, 4/4 FAIL (this entry). **Every
operator-named lever and every self-invented fork this campaign could
build is now closed EXCEPT the operator-ordered overnight SAC tilt5
20M-budget continuation x4 seeds** (`cw-walkcurr-sac-sv-tilt5-{s1-
b20m,s2,s3,s4}`, still training as of this entry — a genuine
budget-raise re-test of lever (iv)'s own most-promising single data
point, seed1's partial escape at 2M/dose5.0).

**Pre-committed next step (assume-and-go, recorded now so the cycle
that reads tilt5 doesn't re-derive this): if ALL FOUR tilt5 arms also
read FAIL** (same 24/24-fall signature, or flat/declining reward with
no fall-rate/forward-dist gain past the already-measured tilt5-s1
ceiling of ~0.055m fwd_dist), **that is the same terminal position
this track reached once before on 08-24 (BC-kickstart question) — but
now with the operator's own follow-up ladder ALSO exhausted.** Per
that precedent's resolved path (2): record rung-1 progress as blocked
at the from-scratch-MLP/decleg-PPO-and-SAC architecture/budget this
campaign has been able to fund and test (a scope/architecture
finding, not a permanent failure of the goal) — CPG-style direct
optimization is explicitly out of this track's from-scratch charter
and is not a lever this track may adopt on its own initiative. File a
fresh, explicit operator note (do NOT silently re-close and go quiet)
naming the two remaining honest options: (a) a genuinely new
mechanism idea from the operator, or (b) an explicit scope ruling
(walkcurr rung-1 stays open-but-parked while the fleet's effort
concentrates on whichever track has runnable work — currently
`standwalk`, which is under active concurrent development). Do NOT
invent an 18th mechanism class unprompted; do NOT relaunch any closed
lever at a new dose without a new mechanism idea attached to it.
**If even ONE of the four tilt5 arms shows a real escape** (fall rate
below 24/24, or forward_dist clearing meaningfully past 0.055m, with
gait_valid true and no over_current confound) — that re-opens lever
(iv) for real: seed-replicate, consider building genuine SAC
`--init-from` checkpoint-continuation support (still missing, see
08-29 ~18:4x entry) so future budget raises don't need the
fresh-relaunch workaround, and defer the BLOCKED framing above.
Snapshot: none this cycle (bank/mechanism code unchanged; only
verdicts + STATUS/OPERATOR_QUESTIONS recorded).

## Now (2026-08-30 ~06:5x — decleg-sv-s4-b100m dig-in RESOLVED (metric artifact, FAIL); graduated step-shaping mechanism built + launched)

Plain English: resolved the DIG-IN flag left by the prior cycle on
`cw-walkcurr-pf-decleg-sv-s4-b100m` (5th/5th decleg-b100m pop-sweep
seed, anomalous 0.30-0.55 DR-0 progress_ratio vs its 4 FAIL siblings).
Root cause: `progress_ratio = along_dist_m / cmd_dist_m`, and the
episodes that die to over_current FASTEST get the SMALLEST `cmd_dist_m`
denominator (some walk/det episodes were cut off at ~6s vs ~25s for
others) -- the absolute `along_dist_m` is uniformly tiny across ALL 24
held-out episodes regardless of episode length (0.007-0.037m total,
i.e. ~1-2mm/s), identical in magnitude to every already-FAIL'd sibling;
the short episodes just divide by a smaller number, inflating the
ratio. Training curves confirm no real escape across the full 100M
steps: `env/walk_speed` oscillates 0.018-0.028 (never clears the 0.02
floor decisively), `terminations/over_current` stays 600-1000/window
throughout (not background), `ep_len_mean` bounces with no clean
rising trend, `env/walk_freeprog_score` hovers ~0. Verdicted **FAIL**
-- closes the operator-ordered PPO population/budget-seed sweep at
**6/6 FAIL** (decleg s2/s3/s4/s5/s6 + central-sv-s0, all the same
static-quiver-to-over_current basin). SAC tilt5 x4 (s1-b20m/s2/s3/s4)
still training, another cycle's/the drain's to read.

Per the prior cycle's own deferred NEXT item, built and launched the
graduated step-completion shaping mechanism instead of leaving it as a
placeholder. New `reward.k_step_partial` (walk_task.py): the pure
`k_step_event`-only pretrain (decleg/central-antifreeze-pretrain-s0,
both FAIL 08-30 ~06:16) gave a fresh-random-init policy NO reward
gradient anywhere near a partial/incomplete stride (the term is an
all-or-nothing cliff at along_f>=10mm) -- `k_step_partial` pays a
LINEAR taper for a genuine completed lift->swing->touchdown that falls
short of the 10mm gate, seamless with the existing credit at the
boundary. Bank-probe discovery during construction: a naive zero-floor
taper measurably breaks the wrong-direction-earns-nothing invariant --
the scripted "sideways" bank twin (real 90-deg-off-command gait) has a
small but nonzero net forward drift from its own leg kinematics
(~2.6cm/episode) that a zero-floor taper pays MORE than an honest tiny
forward partial stride. Fixed with `reward.step_partial_deadband_mm`
(default 2mm): holds the taper at exactly 0 up to the deadband, only
ramps 0->k_step_partial across (deadband, 10mm) -- brings the sideways
leak back under the same <5 margin every other wrong-direction probe
in this file uses. New bank `WALKCURR_SV_PRETRAIN_GRAD`
(test_task_semantics.py, 5/5 green: partial progress earns clearly
more than floor, income is monotone in stride completeness, fidget
forms stay near floor, wrong-direction bounded, topple is the floor).
Default `k_step_partial=0.0` = legacy exact (confirmed: the pure-STEP
bank's own 4/4 tests are unaffected; wider step_event/walkcurr_sv
slice 33/33 green, one pre-existing unrelated topple-timing flake
confirmed identical on clean HEAD). Launched a matched 2-architecture
pair at the same 2M discovery budget, `k_step_partial=0.5`:
`cw-walkcurr-pf-decleg-antifreeze-pretrain-grad-s0` (train-0),
`cw-walkcurr-pf-central-antifreeze-pretrain-grad-s0` (train-1), both
VERIFIED RUNNING. Prediction-if-true: `env/reward_step_event` (or a
comparable partial-credit signal) rises measurably off ~0 before 2M
steps and walk_speed/ep_len show early real motion rather than an
immediate safe-stand convergence. Prediction-if-false: same static
basin as the pure-STEP pretrain -- exploration-bootstrap is refuted as
the blocker, pretrain-staging closes altogether and the fork moves to
a non-PPO search method or an operator prior-free-constraint
escalation (per the prior cycle's own NEXT note).

## Now (2026-08-30 ~06:1x — 4/5 decleg-b100m population-sweep arms read FAIL this cycle; built + launched the candidate-1 antifreeze-pretrain fork)

Plain English: triaged the overnight population sweep as its own reads
landed. `cw-walkcurr-pf-decleg-sv-s3-b100m` (health-stopped 67.6M/
100M), `-s2-b100m` (89.7M/100M, the operator-named "cleanest lineage"
re-extended), and `-s6-b100m` (83.8M/100M, fresh seed) all verdicted
**FAIL** — identical static-quiver-to-over_current basin as the
concurrent cycle's `-s5-b100m` read (now 4/5 decleg-b100m arms FAIL;
`-s4-b100m` is the only one still running, another cycle's). All four
share the signature: reward quarters peak-early-then-flat (not
rising, so not an 08-21 continue case), DR-0 gate prog med ~0 to
negative, slip/m 2x the cap, 0-1/6 (occasionally higher but
zero-net-translation) gait_valid, 24/24 over_current terminations,
static quiver on video. This closes the decleg half of the operator's
"budget/seed axis" question at 100M; `central-sv-s0-b100m` (the
matched-budget centralized control) is still running (claimed by a
concurrent cycle) and will give the other half.

Per the track's own pre-registered escalation (see the "IDLE-CHARGE
LEVER CLOSED" entry below): with the population/budget lever now
reading FAIL 4/4 on decleg, built and launched candidate 1 (the
structural anti-freeze/posture-curriculum fork) THIS cycle rather than
leaving it as a placeholder. Design correction on the way in: a naive
"reward/preserve ANY joint motion" pretrain would reopen the exact
"fake fidget" dodge that already closed this track's raw-|qvel|
`safety.walk_idle_terminate_s` mechanism (WALKCURR_PF_IDLE_TERM bank,
08-24 — idleterm1-3 all FAIL, one of them specifically via a policy
that kept mean|qvel| above the eviction floor via meaningless in-place
jiggle, never triggering the safeguard). Since every current SV-wave
failure IS already a static QUIVER (small nonzero motion, not
literally frozen), a raw motion reward would very likely reinforce
that quiver rather than real stepping. Built
**`WALKCURR_SV_PRETRAIN_STEP`** instead (`test_task_semantics.py`,
4/4 green): a PURE discovery-phase diet built from the already-
validated `reward.k_step_event` term ALONE (`k_walk_freeprog` set to
a 1e-6 epsilon, not literal 0 — bank-probe discovery: literal 0
reopens a separate always-on legacy Gaussian velocity kernel,
`K_WALK=2.0` hardcoded in `walk_task.py`, that pays a frozen park
twin ~1.3/tick regardless of behavior; the epsilon takes the
freeprog-replaces-the-kernel code branch while contributing
~nothing itself). `k_step_event` pays a leg NOTHING unless it
completes a real `>=10mm`-along-command lift-swing-touchdown — a
quiver/fidget in place structurally cannot earn anything, unlike the
raw-|qvel| mechanism. Bank proves: real forward stepping earns
positive income; park/stall(marching-in-place)/belly_sit/reverse/
sideways are all pose- and fidget-invariant near a common floor
(no dodge reopened); topple remains the strict floor. Launched a
matched 2-architecture pair, fresh random init (rule (a): no BC/
imitation/motion-prior warm-start — this is a same-diet RL reward-
curriculum stage, not imitation), 2M PRETRAIN phase only (own-cfg
health read, not a formal gate):
`cw-walkcurr-pf-decleg-antifreeze-pretrain-s0` (train-1),
`cw-walkcurr-pf-central-antifreeze-pretrain-s0` (train-3) — BOTH
finished within the same cycle (2M steps at ~16-26k steps/s, ~2-3 min
wall clock) and BOTH verdicted **FAIL**, same-cycle: a genuinely
informative, clean, symmetric result, not the quiver-to-over_current
basin. `env/reward_step_event` settled at ~0.0007 (essentially never
fires — no real forward-projecting swing was ever completed),
`env/walk_speed` pinned at the same 0.0205 static floor as every
prior FAIL, `walk_direction_err_deg` ~90deg (chance) — BUT
`ep_len_mean` rose 63->547 over the run and `terminations/truncated`
(not over_current/tilt) dominates: the policy learned to SURVIVE via
a safe static stand rather than a quivering death, converging its
reward EXACTLY to the scripted "park" floor (202 in the
WALKCURR_SV_PRETRAIN_STEP bank) and never approaching "gait" (~254).
Central and decleg twins are numerically IDENTICAL (ep_len_mean
547.29 both, ep_rew_mean 202.0/202.03) — architecture is not the
confound. **Root cause (assumed, not yet proven): this is an
exploration-BOOTSTRAP problem, not a reward-ranking problem** — the
bank already proves the ranking is correct, but `k_step_event` is
all-or-nothing at a >=10mm-along-command completed swing, so a fresh
random-init policy that has never once produced anything resembling
a real stride has no shaping gradient anywhere near a PARTIAL swing
and 2M steps (further, cheap to fund) may just never sample one by
chance. **NEXT** (not yet built/launched — a fresh cycle's own
sized decision, not rushed onto this one's tail): before re-trying at
higher budget alone (the same one-more-dose mistake this track's
whole fallback ladder already warns against), build a GRADUATED
step-completion shaping bank (partial credit for airborne time /
partial forward displacement below the 10mm bar, tapering to zero at
truly-zero motion) so a first, incomplete stride attempt is
reinforced instead of requiring a lucky complete one — genuinely
different from every already-tried mechanism (idle-terminate/
park_duty/RND/tilt/terrain/idle-charge, all priced the STATIONARY
side; this reshapes the ACTIVE side's income curve). If that also
fails, pretrain-staging is closed altogether and the fork moves to a
non-PPO search method (already the CPG track's own solved approach,
out of this track's from-scratch scope) or an operator prior-free-
constraint escalation.
Snapshot `47d24895` (bank only, no production-code changes — reused
existing `reward.k_step_event`/`reward.k_walk_freeprog` cfg keys).

**DIG-IN FLAGGED, NOT VERDICTED (08-30 ~06:2x): `cw-walkcurr-pf-
decleg-sv-s4-b100m`** (the 5th and last decleg-b100m population-sweep
arm, 100.3M/100M steps, finished+unclaimed this cycle) reads
ANOMALOUS vs its 4 already-FAIL'd byte-identical-recipe siblings
(s2/s3/s5/s6 — seed is the only lever): DR-0 gate shows genuinely
POSITIVE median progress on 3/4 sub-panels (walk/det prog med
**0.30**, individual episodes up to 0.55; walk_startjitter/det med
0.14) vs every sibling's ~0/negative, and frame strips show visible
net forward translation (checkerboard/marker shift across all 8
frames) unlike every sibling's flat zero-translation quiver. BUT the
run's own binding litmus is NOT clearly met: `env/walk_speed` only
0.026 (barely off the 0.02 floor, not a clean escape),
`terminations/over_current` still fires 24/24 gate episodes (716/
window in training, not "background"), slip/m still 2.97-7.84 (mixed,
some above cap), reward quarters [173.0,166.5,166.7,167.2] identical
peak-then-flat shape to every FAIL. This could be the population
sweep's first genuine partial escape (the literal prediction-if-true
this whole wave was funded to detect) OR a sharper instance of the
already-named "freeprog escape co-occurring with an over_current
surge" artifact (a burst of real motion in the seconds before an
over-current death, not sustained gait) — telling the two apart
needs a per-episode time-series read (does progress accrue steadily
across the episode or spike right before termination?) beyond this
triage cycle's scope. Left UNVERDICTED; flagged for the deep-model
dig-in cycle. If it reads as a genuine partial escape: this becomes
the seed the population sweep should replicate/extend BEFORE writing
off the raw budget/seed axis or funding the graduated-step-shaping
idea above. Evidence: `logs/ckpt_eval/cw_walkcurr_pf_decleg_sv_s4_
b100m_gate/`, W&B `6ogllxfh`.

## Goal (DONE gate)

A prior-free policy passes a held-out C-env contextual walking panel
(fixed forward + heading set + irregular direction changes) with zero
falls, directions actually followed, low slip/m, all-six-leg gait
validity, on video. Speed obedience is secondary throughout.

## Binding track rules (operator, 08-23)

- **Walk-only diet**: every rung trains with `goal.walk_pure=1`. The
  flat1 failure mode (hold/raise/track/unload carrying aggregate
  reward while walk dies) must be impossible by construction.
- **Bank before launch**: any reward-mechanism change re-proves the
  WALKCURR_PF ranking bank (test_task_semantics.py): clean commanded
  walking > park/stall > sideways/reverse/wrong-way >
  high-slip/skate/fall, under the run's exact cfg.
  **AMENDED by operator ruling fb_20260829T145710 (08-29):** the full
  ranking gates rung PASSES **eval-side**; the DISCOVERY-phase
  *training* reward may be far simpler (plain along-command velocity +
  fall termination, no charge stack — the operator-registered
  literature's discovery diet). A simple-diet launch proves its own
  reduced bank instead (WALKCURR_SV in test_task_semantics.py: travel
  > every stationary pose > wrong-way > dying; slip deliberately
  unpriced at discovery, re-priced only after a gait exists).
- **Rule (a) covers initialization (operator ruling
  fb_20260829T145710, 08-29, closes q_20260824T0233Z):** BC-kickstart
  — any imitation warm-start, however brief, including "solely to
  escape the initial-state basin" — is OUT OF BOUNDS for this track.
  No gait clock, no BC teacher, no motion prior, including init.
- **Triage rule**: every triage logs reward trend AND walk-eval trend.
  Reward rising while walk eval is flat/down or walk terminates =
  MISALIGNED -> stop same-recipe seeds/continuations, audit
  reward/eval/simulator. No same-recipe seed sweeps past a misaligned
  read.
- Slip is priced by charge (loadslip excess), never by a hard early
  gate that teaches parking, unless bank and eval agree.

## Rung ladder

1. **fwd1 (NOW)**: fixed forward 0.05-0.06 m/s, heading 0, DR0,
   discovery 2M. Recipe: `rl_move/sim/kawawa2022_recipe.py`.
2. Small heading set (± up to ~15 deg), one command/episode.
3. Full fixed headings.
4. Irregular direction changes (mid-episode resampling).
5. DR/push hardening (paper's friction 0.5-1.25 + periodic pushes).

Update (2026-08-30 ~05:5x — centralized control arm read: `central-sv-s0-b100m` FAIL, budget-alone closes for the centralized architecture too, 4/6 PPO population-sweep arms in)

Plain English: the sweep's centralized-architecture control (100M
target, no decleg) lands in the SAME static-quiver-to-over_current
basin as its decleg siblings — confirming budget alone (100M) does
not escape it either, for either architecture. `env/walk_speed`
pinned 0.012-0.03 m/s the whole 95.5M-step run (never off the ~0.02
floor), `ep_len_mean` spiked once to ~1182 at ~5M then collapsed to
350-440 and stayed there through 95M, `terminations/over_current`
rose to ~1000-1200/window by ~10M and never returned to background,
reward quarters [173.7,167.4,167.1,166.7] — peak early, then
flat/declining, not rising. DR-0 gate n=24: prog med 0.00 (need
>=0.35), slip/m med 4.96-6.44 (cap 3.0), fwd med 0.01-0.02m/25s,
every episode TERM over_current across all 4 sub-panels; `gait_valid`
nominally 6/6 on det/startjitter-det is the same paddle-creep
false-positive already seen on `s6` — contact sheet confirms zero
net translation, static splayed crouch across all 10 frames. Litmus
unmet on all 3 conditions, aligned FAIL. Tally so far: `s2`/`s5`/`s6`
(decleg) + `central-sv-s0` (centralized) = 4 of 6 PPO population-sweep
arms in, ALL FAIL, same basin every time — only `s3` (concurrent
cycle) and `s4` remain unread on the PPO side, plus the 4 SAC-tilt5-
20M arms still training. If `s3`/`s4` also close this basin, the raw
budget/seed-population axis is CLOSED for both architectures at 100M
and the structural anti-freeze/balance-pretrain curriculum (candidate
1, below) becomes the track's next funded item — no further same-
class dose/seed/architecture arm should be launched off this read
alone. Evidence: `logs/ckpt_eval/cw_walkcurr_pf_central_sv_s0_b100m_gate/`,
W&B `ha3nppmt`.

Update (2026-08-30 ~05:3x — two more population-sweep arms read: `decleg-sv-s2-b100m` + `decleg-sv-s6-b100m` both FAIL, 3/5 decleg-100M seeds in)

Plain English: both finished this cycle, same static-quiver-to-
over_current basin as `s5`. `s2` (89.6M steps, exact rerun-and-extend
of the operator-named "cleanest lineage"): `env/walk_speed` pinned
0.02-0.03 m/s the WHOLE run (never off the ~0.02 floor),
`ep_len_mean` spiked to 1210-1249 at 5-10M then collapsed to 300-450
and stayed there through 85M, `terminations/over_current` rose
15->~1000-1200/window by ~15M and never returned to background,
reward peaked 200 at ~5M then declined/flattened to 165-167. DR-0
gate: prog med -0.09 to -0.18 (need >=0.35), slip/m med 4.1-4.6 (cap
3.0), gait_valid 0-1/6, every episode TERM over_current. `s6` (83.8M
steps, fresh seed): identical shape (`walk_speed` 0.017-0.03 pinned,
`ep_len_mean` 1165@5M -> ~390-440 plateau, `over_current` 79->~1000
and flat, reward 184.8@5M -> 165-168 flat/declining); DR-0 slip/m
5.9-6.7 (worse than s2/s5) and 2 sub-panels nominally read
`gait_valid` 5/6 and 6/6 but the frame strip shows ZERO net
translation across the full episode — legs cycling in place
(paddle-creep), not real stepping, terminating in over_current at the
end; the numeric gait_valid flag is a false positive here, not a
better arm. Litmus (decleg-sv dig-in, binding) unmet on all 3
conditions for both — aligned FAILs, not 08-21 continue cases (reward
flat/declining in both, not rising). Running tally: 3/5 decleg-100M
seeds now FAIL (s2, s5, s6), same basin every time; `s3`/`s4` still
training (concurrent cycle owns `s3`), `central-sv-s0-b100m` +
`sac-sv-tilt5-s1..s4` also still training. Per the Now entry's own
instruction, this does NOT close the population-sweep question yet —
read jointly once the remaining 4 arms land. No new launch this
cycle: nothing in the wave is genuinely ready to read early, and the
Now entry's candidate-1 (structural anti-freeze/balance pretrain
curriculum) explicitly needs its own bank/hypothesis build before
funding, not a rushed same-cycle add-on off a partial wave read.
Evidence: `logs/ckpt_eval/cw_walkcurr_pf_decleg_sv_{s2,s6}_b100m_gate/`,
W&B `0mfa0z00` (s2) / `t6mqyye2` (s6).

Update (2026-08-30 ~05:3x — first population-sweep arm read: `decleg-sv-s5-b100m` FAIL, 1/5 decleg-100M seeds in)

Plain English: `cw-walkcurr-pf-decleg-sv-s5-b100m` (fresh seed 5,
100M target) finished early — auto-stopped by the regress-streak
health check at 71.5M once `health/composite_score` turned negative
3 evals in a row — and verdicted **FAIL**: identical static-quiver-
to-over_current basin as every prior decleg-sv/central-sv arm.
`env/walk_speed` never left its ~0.02 m/s floor (0.017-0.026 the
whole run), `rollout/ep_len_mean` spiked once to 1422 at 7M steps
then collapsed to 340-420 and stayed there through 71M,
`terminations/over_current` sat at 900-1150/window from ~11M steps
on (not background), reward peaked 167.9 at ~43M then declined into
the auto-stop. DR-0 gate n=24: prog med -0.02 to -0.13 across
sub-panels (need >=0.35), slip/m med 4.7-5.8 (cap 3.0), gait_valid
0/6 walk/det, every episode TERM over_current. Contact-sheet frame
strip: near-zero net translation over the full episode, legs quiver
in place. Litmus (decleg-sv dig-in, binding) unmet on all 3
conditions — an aligned FAIL, not an 08-21 continue (reward was
flat-then-declining, not rising). This is 1 of 5 decleg-100M seeds
(+1 central-sv-100M control +4 SAC-tilt5-20M) in the same wave; do
NOT treat this as closing the population-sweep question alone — read
jointly once the remaining arms (`-s2/-s3/-s4/-s6-b100m`,
`central-sv-s0-b100m`, `sac-sv-tilt5-s1..s4`) report. If all 10 land
here, the selection-discipline paragraph below already names the
next step (structural anti-freeze/balance pretrain curriculum,
candidate 1) — no further same-class seed/budget arm should be
funded past that point. Evidence: `logs/ckpt_eval/
cw_walkcurr_pf_decleg_sv_s5_b100m_gate/`, W&B `3w54sn4c`.


> Older journal entries (08-23 -> 08-30 ~04:3x sweep-launch Now, and
> everything before) archived VERBATIM in
> `archive/walkcurr_STATUS_journal_2026-08-30_trim.md` (meta 08-30 trim
> -- the ledger + that file hold all history; nothing was reworded).

## Key facts

- The RAW kawawa2022 reward stack was bank-REFUTED on 08-23: park
  (+387) out-earned clean walking (+325) under the walk goal alone —
  flat1's walk was misaligned even before the multi-goal diet starved
  it. v2e re-pricing measured: gait +346 > stall -31 > park -352 >
  sideways -609 > reverse -741 > skate -1058 > topple -1164.
- The harsh SLIPWALK doses (idle 20 / loadslip 6 / gait_gate) are
  refuted for from-scratch discovery (8 statue arms, amp track).
- Lost code: desktop temp commit b126ceb3 (RecurrentPPO/LSTM trainer
  support) was never pushed and the pod deploy copy was overwritten;
  recipe/tests/docs were recovered from the pod and re-landed
  canonically with `--activation-fn` trainer support (08-23).

## WAITING-ON

- (none — the q_20260824T0233Z BC-kickstart ruling landed 08-29:
  OUT OF BOUNDS, track resumed with non-BC literature-informed arms;
  see the 08-29 Now section at top.)
- **[operator, CLEARED 08-29]** (08-24 ~03:4x): rung-1
  discovery-from-scratch was
  blocked pending a ruling on `OPERATOR_QUESTIONS.md` q_20260824T0233Z
  — is a brief BC-kickstart (imitation warm-start solely to escape the
  initial-state basin) in-bounds despite the track's own founding rule
  (a) "no gait clock, no BC teacher, no motion prior"? 14
  independently-designed non-BC mechanism/architecture/reset-diversity
  classes have now failed with an aligned signature at the 2M (up to
  6M) discovery budget (full tally in the question note and the "Now"
  entries above) — no further non-BC lever is pre-registered or
  credible. Do NOT launch further rung-1 discovery arms on this
  recipe until answered; the fleet's effort concentrates on
  amp/cpg maintenance and joystick polish in the meantime (per
  `CURRENT_TRUTHS.md`, both amp M5 and the cpg gate are already
  GREEN/`[operator]`-owned past this point).

