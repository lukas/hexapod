# walkcurr — prior-free walking curriculum (Kawawa-2022 lineage)

## PRIMARY GPU CAMPAIGN 2026-09-05 — operator full-fleet order (supersedes the bounded pilot ceiling)

- 09-05 ~18:2x this cycle (assigned `headset-halfgrav-medhead-c1`,
  `sde-s2-c2-dgatefix-cont40m`): 2 verdicts + 1 refill. (1)
  `headset-halfgrav-medhead-c1` **CANARY PASS** — sibling of the base
  (1g) medhead-c1 canary a concurrent cycle already passed. The DR-0
  harness (synced this cycle) shows gait_valid TRUE on all 24/24
  episodes across walk/walk_sto/walk_startjitter_det/sto, zero
  sacrificed legs, zero terminations, forward_dist_m 2.6-3.4m/20s
  every episode, slip_per_m median 2.4-3.7 (near the 2.9 teacher
  band), frame strip confirms genuine six-leg cycling. The naive
  W&B read (`ep_rew_mean` falling -24.6->-85.3->-138.8->-164.5) looked
  like a violation of the gate's "must rise or hold" text, but
  per-tick reward is flat while `ep_len_mean` climbs on the identical
  fixed warm-up ramp the base sibling's PASS already characterized —
  same shape, not a collapse. Launched the 40M acquisition
  continuation `headset-halfgrav-medhead-acq1` (warm-started from this
  checkpoint, VERIFIED RUNNING train-2), mirroring
  `headset-base-medhead-acq1`'s template. (2)
  `sde-s2-c2-dgatefix-cont40m` **ACQ FAIL** — the entrenched-checkpoint
  `walk_duty_gate` continuation (the one live exception kept running
  as a sunk-cost read per the 17:2x/17:3x closure notes below) does
  NOT rescue the gSDE leg-park exploit over a full 40M budget: harness
  gait_valid 1/24 overall, leg 1 (sometimes +4) chronically sacrificed,
  walk/det IDENTICAL across all 6 episodes (dead-leg drag,
  frame-strip-confirmed). `env/walk_duty_gate_factor` genuinely
  declined 1.0->0.62 through the first ~2M (the signal that licensed
  this continuation) but then MONOTONICALLY RE-SATURATED to 0.85-0.94
  by 40M despite the persisting sacrifice — the exact disqualifying
  condition the gate named at launch — while `ep_rew_mean` climbed
  hugely (90->2100+) on the other five legs' work and `env/walk_speed`
  stayed flat ~0.13-0.14 m/s throughout (no genuine acceleration once
  re-saturated). **This closes the last live gSDE exception — the
  gSDE sub-lineage (bare-sde + sdehalfgrav-remcost, every repair
  mechanism, fresh-init or entrenched-checkpoint) is now CLOSED
  end-to-end.** No further gSDE arm of any kind should be funded.
  Capacity re-checked before exiting: 8-9/11 GPU pods free, no other
  non-duplicative walkcurr arm identified this cycle beyond the one
  acquisition launch above (the concurrent cycle owns the
  `dgate2-c1`/`irr-dgate2-c1` strong-floor retry and `base-medhead-acq1`
  lines already in flight). Evidence: `ops.sh review
  cw-walkscratch-easy0905-{headset-halfgrav-medhead-c1,sde-s2-c2-
  dgatefix-cont40m}`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  halfgrav_medhead_c1_gate/report.json`, `logs/ckpt_eval/
  cw_walkscratch_easy0905_sde_s2_c2_dgatefix_cont40m_gate/report.json`,
  W&B `uxuboegj`/`66wc8jin`.

- 09-05 ~17:3x this cycle (assigned `headset-{base,halfgrav}-
  fullhead-c1`, `sde-dgidle-s1`): 3 verdicts + 1 correction pass + 1
  refill. (1) `sde-dgidle-s1` **CANARY FAIL - MECHANISM** — corroborates
  the concurrent `sde-dgidle-s0` FAIL below with an independent harness
  read (det fwd 0.10m/20s IDENTICAL across all 6 episodes, stride
  0.001m, duty 0.72-0.97 all six legs — same vibration-not-stride
  freeze), gSDE sub-lineage closure now n=2/2 on this price combo.
  (2)+(3) `headset-{base,halfgrav}-fullhead-c1` (full 8-way heading
  jump, both non-gSDE families): both `gate` evals were found
  genuinely still computing on their own pods (orphaned-supervisor
  sync gotcha) after an initial W&B-only FAIL verdict; backgrounded
  `pollreap`/direct reap synced the real harness data, which forced a
  **verdict CORRECTION (FORCE=1)**: both are real, stable six-leg
  gaits (`gait_valid` 22/24 and 24/24, forward_dist_m 2.3-3.4m/20s
  every episode, zero det falls) — NOT the collapse the training-
  rollout W&B averages implied. The actual failure is course-tracking
  (`success` 0/24 both — `direction_err_mean_deg` swings 28-161deg
  episode-to-episode, tracking well near the original {0,+-45} set,
  degrading hard toward quarter-turn/reversal headings). Net verdict
  stays CANARY FAIL - MECHANISM on both (walkcurr's own success bar is
  unmet), but characterized correctly now: a distance-graded
  heading-generalization gap, not instability. **Refill**: built +
  bank-proved the missing intermediate rung `EASY_HEADING_MED` (5-way:
  0,+-45,+-90, no reversal) in `test_walkscratch_easy_pilot.py` (5 new
  tests, 37/37 green, `walkcurr-headingmed-bank-0905` snapshot,
  pushed); launched 2M canaries warm-started from each family's own
  small-set champion: `headset-base-medhead-c1` (train-1),
  `headset-halfgrav-medhead-c1` (train-2), both VERIFIED RUNNING — do
  not re-attempt the bare 8-way jump on either family until these
  land. Evidence: `ops.sh review cw-walkscratch-easy0905-{sde-dgidle-
  s1,headset-base-fullhead-c1,headset-halfgrav-fullhead-c1}`,
  CURRENT_TRUTHS.md 09-05 ~17:3x, W&B `q3vgzdlu`/`a0zu90u6`/`xiajh8ja`.

- 09-05 ~17:2x this cycle (assigned `sde-dgidle-s0`; sibling
  `sde-dgidle-s1` is a concurrent cycle's, already independently
  verdicted FAIL): **CANARY FAIL - MECHANISM (FULL FREEZE/VIBRATION)**,
  2/2 with the sibling. `walk_duty_gate=1.0`+`k_walk_idle_charge=2.0`
  together, from scratch, still converges to the disqualified freeze
  fingerprint: det fwd med 0.047m/20s, stride_m_mean 0.001m, duty
  0.78-0.98 on ALL SIX legs (vibration, not stride — swing_count up to
  266/20s), slip_per_m 95.97 (33x the 2.9 band); sto/startjitter modes
  fall MORE not less (5-6/6 terminations tilt_roll/tilt_pitch) —
  fragile, not just static. Video (`walk_det_0.png`,
  `walk_startjitter_det_0.png`) shows the identical splayed-leg pose
  every sampled frame. **This closes reward-shaping-alone repair for
  the bare-sde/easy0905 LEGPARK-SKATE pathology FOR GOOD**: 6
  independently-designed price/termination mechanisms now FAIL
  (`walk_gait_gate`+`k_step_event` 6/6, `k_park_duty`+
  `k_walk_idle_charge`+qvel-terminate 2/2, bare `walk_duty_gate` fresh
  3/3, `walk_duty_gate` on entrenched checkpoints 4/4 below funding
  bar, `walk_duty_gate`+`k_walk_idle_charge` fresh 2/2). **Recommend
  CLOSING the gSDE sub-lineage entirely** — the campaign's own launch
  hypothesis for `sde-s0` already states the controlled A/B verbatim
  ("ONLY change vs base-s0 is --use-sde"); the identical bare recipe
  passes ACQ cleanly on the non-gSDE base/halfgrav families (4+/4,
  six-leg video-confirmed) and fails on every gSDE seed tried (7+) —
  gSDE is the confirmed causal ingredient, not remcost pricing, not
  warm-start entrenchment, not the duty-gate/idle-charge combo. No
  further gSDE price/termination variant should be funded from here.
  The one live exception: `sde-s2-c2-dgatefix-cont40m` (entrenched-
  checkpoint, genuinely rising reward, 08-21-justified, already
  running) — let it finish as a sunk-cost read; fund no NEW gSDE arms
  after it. Remaining walkcurr GPU budget belongs to the working
  base/halfgrav (Gaussian) curriculum ladder (fullhead-widen in
  flight on a concurrent cycle; irr-timing 1g still open — see below).
  CURRENT_TRUTHS.md updated (~17:2x entry). Capacity re-checked:
  `launch_run.py status` shows 10/11 GPU pods free, backlog empty —
  did not launch a fresh gSDE arm (just closed) nor duplicate the
  concurrent cycle's fullhead-med work; see refill note below for the
  one new non-duplicative arm this cycle funded instead. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_sde_dgidle_s0_gate/
  report.json`, W&B `4ubnoqq3`.
  **Refill (same cycle):** with the gSDE lineage closed and 8+ GPU
  pods free, built + bank-proved a STRONGER dose of `walk_duty_gate`
  (`duty_gate_floor` 0.15 -> 0.35, `g`=1.0; `test_duty_gate_strong_
  floor_*`, 2 new tests, 39/39 file green,
  `walkcurr-dutygate-strongfloor-bank-0905`) targeting the DIFFERENT,
  still-open "marginal underuse" class on the non-gSDE base family
  (one leg chronically at duty 0.03-0.07 with real infrequent swings,
  NOT the closed gSDE near-zero-touch LEGPARK-SKATE) -- the prior 0.9/
  0.15 dose (`headset-base-s0c1-dgate-c1`) was CANARY FAIL - MECHANISM
  (INERT-DOSE): PPO's training-time rollout noise already satisfied
  the lenient 0.15 floor even for a leg whose deterministic policy
  sits at 0.04-0.07, so almost no repair gradient reached eval-time
  behavior. The new floor keeps a healthy tripod's income untouched
  (leg-4 duty ~0.52 >> 0.35, measured directly) while pricing a
  ~0.05-duty scripted twin measurably harder (-432 -> -536 on the
  identical trajectory) -- a real, not saturated, difference. Launched
  both marginal-underuse FAILs this class has produced so far:
  `headset-base-s0c1-dgate2-c1` (from `s0c1-acq1`'s own checkpoint,
  train-3) and `headset-base-irr-dgate2-c1` (from `irr-acq1`'s own
  checkpoint, the irr-timing/1g composition, train-4), both VERIFIED
  RUNNING (2M canaries, ~2-5 min wall clock at this fps). Gate: real
  movement of `env/walk_duty_min` off the pinned-1.0 plateau + det-mode
  leg duty climbing measurably above the 0.04-0.07 baseline; FAIL if
  still pinned (repeats INERT-DOSE) or a different leg parks/falls
  appear. Snapshot `walkcurr-dutygate-strongfloor-bank-0905`.

- 09-05 ~16:5x this cycle (assigned `sde-s2-c2-dgatefix`/
  `sdehalfgrav-remcost-{s0,s1}-dgatefix`, 3 of the 4-arm
  entrenched-checkpoint `walk_duty_gate` batch — `sde-s1-c2-dgatefix`
  is a concurrent cycle's, left untouched): **3 verdicts, all CANARY
  FAIL - MECHANISM**, but a THIRD distinct fingerprint from the two
  already-closed patterns (saturating-factor and full-freeze):
  `env/walk_duty_gate_factor` genuinely DECLINES across training on
  all 3 (bare-sde 1.0->0.64, remcost-s0 1.0->0.72, remcost-s1
  1.0->0.66 — real ungamed pressure, not saturation) and none
  full-freeze — all 3 keep real speed (0.09-0.26 m/s) and net
  displacement (1.5-4.6m/20s). Harness walk/det `gait_valid` stays
  0/6 on all 3, same 1-2 legs stuck at 0.00-0.01 duty the whole clip
  (leg 1 for bare-sde; legs 1+4 both remcost seeds — same pair both
  seeds). The two recipes diverge on reward direction: bare-sde
  (`sde-s2-c2-dgatefix`) has `ep_rew_mean` quarters RISING throughout
  (94->224->332->406, the 08-21 rising-reward/bad-eval continue
  pattern), while both remcost seeds WORSEN (-344->-495, -322->-582 —
  absorbing more penalty for the same frozen park without escaping).
  Read: the mechanism works as designed against an entrenched
  exploiter, it just hasn't had enough budget yet on the one
  promising seed — the next lever for THIS specific question is a
  longer continuation of `sde-s2-c2-dgatefix` (not a new price/
  termination mechanism), once `sde-s1-c2-dgatefix`'s own harness read
  completes the n=4 picture. CURRENT_TRUTHS.md updated (~16:5x entry).
  Capacity: re-checked `launch_run.py status` — only
  `headset-{base,halfgrav}-fullhead-c1` hold live GPU trainers (both
  another cycle's, mid-training, left alone) plus `sde-dgidle-{s0,s1}`
  (also another cycle's, mid-training) — everything else free,
  backlog empty. Did not launch a longer `sde-s2-c2-dgatefix`
  continuation this cycle: that arm's own promising signal is only
  1/3 same-batch data points and the sibling entrenched-checkpoint
  read (`sde-s1-c2-dgatefix`) is still mid-DIG-IN on a concurrent
  cycle — spending a 40M continuation before all 4 arms of THIS batch
  are read together would be premature and duplicative of that
  cycle's own next move once it lands. No other non-duplicative
  walkcurr/track work identified (fullheading canaries + dgidle pair
  already own their pods; other tracks closed/maintenance-only per
  prior entries). Evidence: `ops.sh review cw-walkscratch-easy0905-
  {sde-s2-c2-dgatefix,sdehalfgrav-remcost-s0-dgatefix,sdehalfgrav-
  remcost-s1-dgatefix}`, W&B `jw13d0rn`/`mmbhvbzs`/`m9sj7qzp`.

- 09-05 ~16:5x this cycle (assigned `sde-dgfresh-s0b`/
  `sdehalfgrav-dgfresh-s0`, the from-scratch `walk_duty_gate`
  disambiguation pair): **3 verdicts, all CANARY FAIL - MECHANISM
  (FULL FREEZE)**, closing the disambiguation for good. Found the
  assigned pair's name-collision twin (`sde-dgfresh-s0`, a real
  separate W&B run, `8h25tu4l`) also finished and read it too (3/3,
  not 2/2). All three: `reward.walk_duty_gate=1.0` from step 0, NO
  remcost pricing, NO inherited checkpoint — det walk fwd med
  0.02-0.07m/20s, IDENTICAL to 2 decimals across all 6 det episodes
  (video: static splayed-leg pose, no leg mid-swing at any sampled
  tick, `walk_det_0..5.png`), `env/walk_duty_gate_factor` saturated
  0.92-1.0 the entire 2M run, `ep_rew_mean` quarters strictly
  WORSENING (not the 08-21 rising-reward-bad-eval case, so no
  continue). **Closes `walk_duty_gate` alone as a from-scratch repair
  lever**: the freeze is intrinsic to the mechanism (a duty floor
  alone is trivially satisfied by 6-leg stasis, cheaper than any real
  gait) — not an artifact of remcost pricing or of warm-starting from
  an entrenched exploiter, both confounds now independently ruled
  out. CURRENT_TRUTHS.md updated (~16:3x entry). Do not fund another
  bare `walk_duty_gate` arm (fresh or entrenched) until a joint
  duty-floor + `reward.k_walk_idle_charge` travel-floor design+bank
  pass lands — the in-flight entrenched `dgatefix` batch (see the
  16:4x+ entries below) is a separate confound (cure vs. prevent) and
  should still be read on its own.
  **Capacity fill (11 free pods, backlog empty):** identified one
  genuinely non-duplicative, non-blocked next rung — the walkcurr
  ladder's own "full fixed headings" step (after "small heading set",
  before "irregular direction changes"), on the two ALREADY-WORKING
  non-gSDE families (base 1g / halfgrav 0.5g), untouched by the
  duty_gate question. Built + bank-proved `EASY_HEADING_WIDE` (full
  8-way compass incl. reversals, same `k_walk_freeprog` mechanism, no
  new reward keys) in `test_walkscratch_easy_pilot.py`: 5 new
  `test_easy_heading_wide_*` tests, 32/32 green
  (`walkcurr-fullheading-bank-0905` snapshot, pushed). Launched 2M
  mechanism-health canaries warm-started from each family's own
  heading champion: `headset-base-fullhead-c1` (from
  `headset-base-acq1`, train-2) + `headset-halfgrav-fullhead-c1`
  (from `headset-halfgrav-acq1`, train-5), both VERIFIED RUNNING.
  Evidence: `ops.sh review cw-walkscratch-easy0905-{sde-dgfresh-s0,
  sde-dgfresh-s0b,sdehalfgrav-dgfresh-s0}`, W&B `8h25tu4l`/`vwnbmgq2`/
  `c3kd1elp`.

- 09-05 ~16:4x this cycle (own spawn, assigned only
  `sde-dgfresh-s0`): independently confirmed the concurrent cycle's
  **CANARY FAIL — FULL FREEZE** verdict already landed on it (det walk
  fwd 0.06m/20s all 6 eps, duty 0.75-0.96 but stride_m_mean 0.001m/
  swing_count up to 302 in 20s — a vibration-not-stride pathology, not
  literal stillness). Bare `walk_duty_gate` from-scratch is now CLOSED
  3/3 (`sde-dgfresh-{s0,s0b}`, `sdehalfgrav-dgfresh-s0`). **New
  finding (CURRENT_TRUTHS updated)**: the "Next: pair with
  `k_walk_idle_charge`" every one of those FAILs named is NOT untested
  ground — `sde-idleterm-{s0,s1}` already ran `k_park_duty`+
  `k_walk_idle_charge`+a hard qvel-based `safety.walk_idle_terminate_s`
  on this exact recipe and ALSO froze (the qvel-terminate got
  jitter-dodged by servo micro-vibration, no coherent stepping — the
  same vibration signature). Three independent price/termination
  mechanisms now share this one fate on the sde/easy0905 recipe.
  Launched one more canary pair anyway (`sde-dgidle-{s0,s1}`,
  `walk_duty_gate`+`k_walk_idle_charge` together, dropping the
  dodgeable qvel-terminate since idle-charge's own along-speed EMA
  prices BODY displacement not joint motion) since the specific
  combination is genuinely new, but flagged in-run: a 4th FAIL closes
  "price-shaping alone escapes this basin" for this recipe and the
  next lever must be structural (BC/CPG-seeded init, higher
  exploration/entropy schedule, moving-state curriculum start), not a
  5th price variant. Full evidence: CURRENT_TRUTHS.md 09-05 ~16:4x.

- 09-05 ~16:4x this cycle (own spawn, assigned only
  `sde-s1-c2-dgatefix` — its 3 siblings `sde-s2-c2-dgatefix`/
  `sdehalfgrav-remcost-{s0,s1}-dgatefix` are NOT this cycle's, left
  untouched): W&B finished (2M, `ep_rew_mean` 94.3->234.2->337.9->
  409.9, climbing) but the harness gate eval was silently orphaned —
  `logs/ckpt_eval/..._gate*` missing on the controller, yet
  `eval_checkpoint` genuinely still running on its own pod
  (train-4, PID 61366, started 16:12, ~28min in when checked;
  `--video-every 1` panels run 1.5-2h, per the documented
  prestage-timeout-vs-genuinely-still-running gotcha). Started a
  single backgrounded `pollreap` (not a second podeval) so the next
  reader gets the synced report/video without re-discovering this.
  **Preliminary W&B-only signal, NOT yet a verdict** (no harness
  gait_valid/per-leg duty or video available this cycle): across the
  4 logged checkpoints (524k/1.05M/1.57M/2.1M steps),
  `env/walk_duty_gate_factor` (== `walk_duty_min`, this arm has one
  binding leg) goes 1.0 -> 1.0 -> 0.718 -> 0.539 — DECLINING, the
  opposite of the gate's hypothesized "climb toward 1.0" cure
  direction, while `env/reward_walk` also declines across the same 4
  points (1.13 -> 1.26 -> 0.92 -> 0.69) even as the multi-goal
  `ep_rew_mean` keeps climbing (walk is one of 5 goals — hold/lean/
  track/unload/rise — in this fine-tune's mix, so a rising blended
  reward can coexist with walk-specific decay). This is the same
  entrenched-checkpoint question `sde-s1-dg1` (from the early
  undifferentiated ancestor) already found CANARY PASS on and this
  arm's own hypothesis was written to test on the REAL 40M exploiter
  — the declining-not-saturating factor pattern is anomalous enough
  (and this result forks the whole entrenched-checkpoint repair
  question, see the 4-arm read note above) to want the harness
  per-leg duty numbers + video before calling it either way per the
  08-21 ruling (declining factor could mean genuine partial repair
  with a harder residual leg, OR the multi-goal mix let the policy
  route reward-seeking away from walk entirely while nominally
  keeping duty_gate satisfied at the sampled/noisy level PPO explores
  at — either needs the actual gait_valid/duty_cycle readout, not
  scalar curves, to distinguish). **DIG-IN flagged for next spawn**
  once `logs/ckpt_eval/cw_walkscratch_easy0905_sde_s1_c2_dgatefix_gate/
  report.json` lands (pollreap running, up to 2h) — do not re-run
  podeval/pollreap for this run, and do not launch further
  entrenched-checkpoint dgatefix arms until all 4 are read together.
  Capacity re-confirmed by direct `ps aux` (not ledger, which is
  stale): only train-2/train-5 hold live trainers
  (`headset-{base,halfgrav}-fullhead-c1`), everything else free,
  backlog empty — no non-duplicative walkcurr arm identified this
  cycle either (same conclusion as the ~16:1x entry below, now
  re-verified after the dgatefix batch's own training finished).

- 09-05 ~16:1x this cycle: REFILL completing the corrected
  entrenched-checkpoint `walk_duty_gate` batch. With `sde-s1-c2-dgatefix`
  already RUNNING (built earlier this cycle, see the same-cycle entry
  further below) and 6+ GPU pods genuinely free (`launch_run.py
  status`, backlog empty), hand-built (via `backlog add`, bypassing
  `respec` entirely to sidestep the checkpoint-provenance gotcha) the
  remaining 3 arms that make this an n=2 bare-sde + n=2 remcost batch
  instead of n=1: `sde-s2-c2-dgatefix` (`--init-from` explicit
  `sde_s2_c2.zip`, the real 40M LEGPARK exploiter, companion to
  `sde-s1-c2-dgatefix`), `sdehalfgrav-remcost-{s0,s1}-dgatefix`
  (`--init-from` explicit `sdehalfgrav_remcost_{s0,s1}.zip`, each
  seed's own real 40M ACQ-CONTINUE LEGPARK checkpoint — the remcost
  `-dg1` siblings never touched these, they were fully from-scratch
  per the checkpoint-provenance finding above). All 3 stripped
  `--use-sde`/`--sde-sample-freq` and blanked `--activation-fn` per the
  documented gSDE+`--init-from` SystemExit gotcha (remcost sources are
  from-scratch gSDE launches). All 3 VERIFIED RUNNING
  (train-0/train-1/train-3). This is the real "does walk_duty_gate
  cure an ALREADY-entrenched LEGPARK-SKATE policy" test for every
  recipe in the campaign, at n=2 each (bare-sde, remcost) rather than
  the n=1 `sde-s1-c2-dgatefix` alone — read all 4 entrenched-checkpoint
  arms together before judging the mechanism's fate on converged
  exploiters (the already-launched from-scratch `dgfresh` pair is a
  separate, complementary question). Capacity at cycle end:
  train-2/4/5/7/8/9/10/11 free, backlog empty — no further
  non-duplicative arm identified (every open walkcurr question now has
  evidence in flight: 4 entrenched-checkpoint dgatefix arms, 3
  from-scratch dgfresh arms, this cycle's own 3 verdicts already
  recorded above).

- 09-05 ~16:0x this cycle: 2 verdicts closing the irr-timing rung's
  last two pending reads (both found already-landed on their own
  pods, orphaned-eval gotcha, evidence not yet read by anyone).
  (1) `headset-halfgrav-irr-c3` **CANARY PASS** — 23/24 gait_valid
  (only one marginal walk_startjitter/det leg-1 flag), 0/24 falls,
  slip med 2.18-2.27, six-leg video-clean (`walk_det_0.png`). This
  closes the halfgrav irr-timing n=3 canary confirmation set (irr-c1/
  c2/c3 all PASS). (2) `headset-base-irr-acq1` **ACQ FAIL
  (misaligned)** — this is the real 40M acquisition read for the
  irr-timing rung on the 1g cell (warm-started from `headset-base-
  irr-c1`'s own 2M checkpoint, itself off the `headset-base-acq1`
  champion). walk/det (the PRIMARY un-perturbed mode) gait_valid only
  3/6 — FAILS the adopted `>=4/6 primary` bar from the s0c1-acq1
  ruling — legs [4]/[1] flagged in 3 different det episodes, duty as
  low as 0.04-0.07 (below the 0.10 sacrifice bar) though swing_count
  37-84/20s (real infrequent swings, the "active marginal underuse"
  class already seen on `s3acq`/`s0c1-acq1`, NOT sde-style near-zero-
  touch LEGPARK-SKATE — video confirms legs actively cycling, not
  frozen). walk_startjitter/det also 3/6 (one flagged leg duty as low
  as 0.01). Overall 18/24 clears the secondary bar alone but the
  adopted rule is an AND. Separately, `slip_per_m` runs 3.86-4.76
  across ALL 24 episodes (including gait_valid ones) — uniformly
  worse than every base/halfgrav sibling this campaign (typically
  2.2-3.0, inside the 2.9 band); this run clears none of them. 0/24
  falls, reward quarters 503.7/969.4/1118.5/1296.7 still climbing
  (+16% Q3->Q4) — per 08-21 this is NOT an auto-continue: the pattern
  (canary-level marginal duty hardening rather than healing with more
  budget) is the SAME class already closed on `s0c1-acq1`, and this is
  the second independent lineage showing it, now specifically under
  the irr-timing (jittered heading-resample) composition. **New
  finding: the irr-timing rung's real ACQ gate is NOT clean on the 1g
  cell off this lineage**, even though the identical plain-freeprog
  recipe passes cleanly WITHOUT irr-timing (`base-acq1`/`s1c1-acq1`)
  and the SAME irr-timing composition passes cleanly on the 0.5g cell
  (`headset-halfgrav-irr-acq1`, concurrent-cycle-owned — read its own
  report before assuming this generalizes across gravity cells).
  Consequence: once the in-flight `walk_duty_gate` mechanism-health
  reads resolve favorably, that lever is the pre-registered repair
  candidate to try on THIS irr-timing/1g composition too (a new cell
  for it, not yet tested) rather than relaunching a plain-recipe seed
  here — do not re-attempt this exact lineage without that mechanism.
  Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  {halfgrav_irr_c3,base_irr_acq1}_gate/report.json`, W&B
  `0vpok57r`/`hqxngd1e`. Capacity check this cycle: 7 of 11 reachable
  GPU pods genuinely idle (`ps aux` confirmed on every pod, not just
  ledger) and `backlog.json` empty, but every open walkcurr question
  is already funded/in-flight (the from-scratch `walk_duty_gate`
  disambiguation batch, its `dgatefix` entrenched-checkpoint
  companion, both irr-acq1 reads now landed/verdicted, the
  `headset-base-s0c1-dgate-c1` repair canary) or genuinely blocked on
  those same in-flight reads landing first — no other registered
  track has launchable GPU work either (`joystick`/`amp`/`cpg` DONE/
  maintenance-only, `standwalk`'s gait-structure axis fully CLOSED
  with no next lever queued per its own STATUS, `todaypolicy`
  DELIVERED). Left the free pods idle rather than invent filler; no
  new launch this cycle.

- 09-05 ~16:0x this cycle (own spawn, reads the remaining 2 of the
  5-canary `walk_duty_gate` batch the entry below left unread, plus one
  new acquisition): (1) `sde-s1-dg1` **CANARY PASS (scope-corrected)**:
  walk/det is a genuine six-leg escape from LEGPARK-SKATE (6/6
  gait_valid, 0 falls, all-leg duty 0.22-0.84, slip/m 3.33) — but
  sto/startjitter modes show 13/24 falls (tilt_pitch, fragile-not-
  parked, a NEW caveat). Independently found the SAME checkpoint-
  provenance bug the entry below documents (this run's own `--init-from`
  is `sde_s1.zip`, the original 2M ancestor, not `sde_s1_c2.zip`) and
  banked it in `CURRENT_TRUTHS.md`; hand-built (via `backlog add`,
  bypassing respec) the corrected entrenched-checkpoint test
  `sde-s1-c2-dgatefix` (`--init-from` explicitly `sde_s1_c2.zip`,
  ps-verified) — this is the run the entry below found already RUNNING
  on train-4 and correctly attributed to a concurrent cycle. (2)
  `headset-base-s0c1-dgate-c1` **CANARY FAIL - MECHANISM (DUTY-GATE
  INERT-DOSE)**: walk_duty_gate=0.9 on the genuine s0c1-acq1 FAIL
  checkpoint made ZERO measurable behavior change after 2M — every
  per-leg duty number matches the parent's own gate report to within
  noise, `env/walk_duty_gate_factor` sits 0.945-1.0 nearly the whole
  run because PPO's own rollout noise already satisfies the 0.15 floor
  for this MILD (0.03-0.07 duty) chronic-underuse case, so almost no
  repair gradient reaches the deterministic policy the harness
  evaluates — a different failure mode than the closed walk_gait_gate
  rare-token-dodge (that engaged and got gamed; this barely engages at
  all). No 40M continuation funded; does not change base-family
  champion selection (already excluded pre-dgate). (3)
  `headset-halfgrav-irr-acq1` **ACQ PASS**: first irr-timing-rung 40M
  acquisition to clear the gait_valid-majority bar (0/24 falls,
  gait_valid 20/24, slip 2.18-3.04, no chronically-parked leg) — closes
  the 0.5g half of the irr-timing rung (1g `base-irr-acq1` is a
  separate concurrent-cycle-owned run, read it before calling the rung
  closed for both cells). SKILLS.md updated x2 (irr-timing PASS row +
  none needed for the two FAILs).

- 09-05 ~16:0x this cycle, CORRECTED ~16:2x (checkpoint provenance):
  3 verdicts + 2 refill launches closing out the first
  `walk_duty_gate` mechanism-health canary wave. Verdicts:
  `sde-s2-dg1`, `sdehalfgrav-remcost-{s0,s1}-dg1` all **CANARY FAIL**
  — good news first: `env/walk_duty_gate_factor` behaved exactly as
  designed on all 3 (declined 0.69-0.92, i.e. penalizing real low
  duty, NOT saturating/gamed like the closed `walk_gait_gate`), and
  det-mode `gait_valid`/`sac` genuinely cleared (no chronically-parked
  leg on any of the 3) — the SPECIFIC one-leg-park exploit is
  prevented from forming at all. **Correction to my own first pass**:
  per the respec-clone provenance gotcha a concurrent cycle banked in
  CURRENT_TRUTHS mid-cycle, none of these 3 were actually "warm-started
  off an already-converged 40M exploiter" as I first wrote —
  `sde-s2-dg1`'s real `--init-from` is `sde_s2.zip` (the ORIGINAL 2M
  canary, which falls tilt_pitch in every single eval episode, not the
  40M `sde_s2_c2.zip` exploiter), and both `sdehalfgrav-remcost-
  {s0,s1}-dg1` carried NO `--init-from` at all (fully FROM SCRATCH).
  Re-verdicted (FORCE=1) with the corrected story: within the 2M
  budget the policy still didn't reach real six-leg locomotion, but by
  a different route per recipe — `sde-s2-dg1` (from the falling 2M
  ancestor) made real progress (stopped falling in det) but ends each
  episode yawed ~174deg from start with current 0.30A->1.40A
  (spin/destabilize, not travel), falls 5/6 sto; both `sdehalfgrav-
  remcost-{s0,s1}-dg1` (from scratch, remcost pricing + duty_gate
  together) go FULL FREEZE (v 0.001-0.037 m/s, net displacement
  0.00-0.01m over the whole 20s det episode, slip 20-75x band from leg
  micro-vibration with zero net travel, falls 6/6 sto) — a leg that
  never lifts trivially clears the duty floor (duty~1.0), cheaper than
  a real gait's necessarily-lower swinging-leg duty, so full stasis is
  an even EASIER dodge than the sacrifice it replaced, AND this now
  directly confirms (from scratch, no warm-start confound needed) the
  remcost recipe's OWN launch hypothesis, which named "retreat to the
  ~0-income park basin" as its predicted failure mode if term_cost
  pricing over-corrects toward fall-aversion; reward for the remcost
  pair tracks their UN-gated from-scratch parents' own trajectories at
  matched absolute steps almost exactly (not a new collapse, remcost
  is already this negative on its own). **This closes "walk_duty_gate
  =1.0 on the early falling sde_s2 2M checkpoint" (n=1) and
  "walk_duty_gate=1.0 + remcost term_cost pricing, from scratch"
  (n=2)** — do NOT fund a 40M acquisition off any of these 3
  checkpoints, and do not relaunch either exact combination. Still NOT
  proof `walk_duty_gate` itself is unsound absent remcost's
  fall-aversion pricing, since remcost's own term_cost is a plausible
  independent contributor to the freeze — a genuinely from-scratch,
  no-remcost read is the clean test. Refill: launched the
  disambiguating from-scratch pair
  (`cw-walkscratch-easy0905-sde-dgfresh-s0`,
  `-sdehalfgrav-dgfresh-s0`, 2M canaries, `reward.walk_duty_gate=1.0`
  from step 0, otherwise identical to `sde-s0`/`sdehalfgrav-s0`, no
  remcost pricing, no warm-start) on free capacity (11/11 GPU pods
  were idle at cycle start — VERIFIED RUNNING both, train-1/train-0;
  a same-drain-pass pod-claim race produced one harmless extra
  same-config replicate, `sde-dgfresh-s0b` on train-2, left running
  rather than risk a botched kill mid-training). **Next: read those
  two from-scratch verdicts before trying any further
  `walk_duty_gate` variant** — if fresh init ALSO freezes/spins, the
  mechanism needs pairing with `reward.k_walk_idle_charge` (already
  implemented, anti-idle income floor, 0 in every arm so far) before
  further spend; if it produces even partial real forward progress,
  the fix is a gradual dose ramp for warm-starts rather than instant
  full-strength. `sde-s1-dg1` and `headset-base-s0c1-dgate-c1` (the
  remaining 2 of the original 5-canary batch) were left unread this
  cycle — `cw-walkscratch-easy0905-sde-s1-c2-dgatefix` was found
  RUNNING on train-4 at cycle end (not launched by this cycle),
  presumably a concurrent cycle's own repair attempt on the same
  `sde-s1-dg1` finding; read its notes before assuming this entry is
  the last word on that arm. CURRENT_TRUTHS.md updated. Evidence:
  `ops.sh review cw-walkscratch-easy0905-sde-s2-dg1` /
  `cw-walkscratch-easy0905-sdehalfgrav-remcost-s{0,1}-dg1`, W&B notes
  on the three verdicted runs.

- 09-05 ~15:4x this cycle: 4 verdicts, 2 refill-registrations, no new
  launch. (1) `headset-halfgrav-irr-c2` **CANARY PASS** — cleanest
  irr-timing canary of the whole campaign: 24/24 gait_valid across
  ALL four scenarios (walk/sto/startjitter x det/sto), 0 falls, zero
  sacrificed legs anywhere, slip med 2.16-2.96. (2) `sde-s0-c4gg` and
  (3) `sde-s3-c1bgg` both **ACQ FAIL (misaligned)** — same
  gait_valid-0/24 + saturated `walk_gait_gate_factor` (0.81-1.0)
  fingerprint as every prior gg arm. **This CLOSES the
  `walk_gait_gate`+`k_step_event` repair lever at 6/6, fully
  confirmed** (bare sde x2 c3gg, sdehalfgrav-remcost x2 gg2, bare sde
  x2 c4gg/c1bgg) — CURRENT_TRUTHS.md updated; do not relaunch this
  lever anywhere in the family. Only the newer `reward.walk_duty_gate`
  mechanism remains open (5 canaries mid-gate-eval, see below).
  (4) my own assigned run `headset-halfgrav-irr-c3` finished training
  (reward quarters 32.6/74.2/73.0/126.5, healthy) but its own gate
  eval is still genuinely computing remotely on train-1 (~26min in,
  matches sibling timing) — registered `evalpending`, do not
  re-launch, read `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  halfgrav_irr_c3_gate/report.json` next cycle. Also found+registered
  two more orphaned-pod evals (the exact 09-05 gotcha: pod moves on to
  the NEXT eval before the local supervisor re-polls) that weren't in
  `pending_evals.json`: `headset-halfgrav-irr-acq1` (train-2) and
  `headset-base-irr-acq1` (train-3) — both 40M trainings FINISHED with
  strongly rising reward (quarters up to 918/1297), their own 24-ep
  gate panels now genuinely computing; these are the two irr-timing
  rung's real acquisition reads for both gravity cells, registered
  `evalpending` for both. Capacity check: only train-0/train-4/
  train-11 genuinely idle (`ps aux` on every pod, not just ledger) —
  8 of 11 reachable pods mid CPU-only gate-eval (this run's own c3,
  both irr-acq1, and all 5 walk_duty_gate canaries). Every open
  walkcurr question (does duty_gate escape LEGPARK-SKATE; do both
  irr-acq1 cells pass their real gate; does c3 confirm the halfgrav
  irr-canary set at 3/3) already has evidence in flight — left the 3
  free pods idle rather than invent a premature heading-set-widening
  or a 2nd irr-acquisition seed before any of those land (same
  precedent as the 14:3x/14:4x/14:6x/15:3x entries below). No launch,
  no code this cycle.

- 09-05 ~15:3x this cycle (assigned `headset-halfgrav-irr-c2`): its
  harness gate eval was still genuinely computing remotely on
  train-4 at triage time (~27min in when checked, `video-every=1`
  panels commonly run 30-45min per sibling evidence this cycle —
  NOT stalled: confirmed via `ps`/`nvidia-smi`, process alive,
  0% GPU util as expected for a CPU-only eval_checkpoint pass).
  Registered `ops.sh evalpending add hexapod-mjx-train-4
  .../cw_walkscratch_easy0905_headset_halfgrav_irr_c2_gate/
  report.json` rather than blocking; next cycle (or the watcher's
  auto-spawn on file-appear) reads the verdict, do not re-launch.
  Refill check: cross-checked `launch_run.py status` against live
  `ps`/`nvidia-smi` on every reachable pod (status's train_ppo-only
  grep undercounts busy — 9 of 11 reachable pods are mid CPU-only
  gate-eval for this wave's other just-finished canaries:
  `base_irr_c2`(train-0), `halfgrav_irr_c3`(train-1),
  `sde_s1_dg1`(train-2), `sdehalfgrav_remcost_s1_dg1`(train-8),
  `sdehalfgrav_remcost_s0_dg1`(train-9), `sde_s2_dg1`(train-10),
  `headset_base_s0c1_dgate_c1`(train-5), plus this run(train-4) —
  GPU idle on all of them but CPU near-saturated (~700-800% of an
  eval_checkpoint pass each), leaving effectively ONE pod
  (`train-11`) with genuine CPU+GPU headroom for a new launch.
  Checked every open walkcurr thread against that one slot: irr-timing
  rung (both gravity cells, n=2/3 canaries + both acq1 continuations)
  already funded/running; the `walk_duty_gate` repair mechanism's
  full pre-registered 4-arm batch (line ~5 below) already launched
  and is the exact set of 4 gate evals listed above; the direct
  `s0c1-acq1`-lineage repair check (`s0c1-dgate-c1`) already running
  too — every pre-registered "Next" in this file is already in
  flight with no verdict landed yet to justify a NEW (non-duplicative)
  arm off a single free pod. Left `train-11` idle rather than invent
  filler, matching this file's own repeated precedent (14:3x/14:4x/
  14:6x entries) for the same situation. No launch, no verdict, no
  code this cycle — pure hold until the incoming verdict wave lands.

- 09-05 ~15:2x this cycle, FILLS the pre-registered "next" slot from
  the ~15:1x entry below one step early: with the sde gait-gate n=4
  cohort already CLOSED (CURRENT_TRUTHS, 4/4 FAIL, confirmed this
  cycle) and 8 GPU pods genuinely idle (`launch_run.py status`/
  `capacity.py` cross-checked), launched the FULL 4-arm
  `reward.walk_duty_gate=1.0` canary batch on every closed-lever
  recipe in one go rather than the single base-family arm alone:
  `sde-s1-dg1` (from `sde-s1-c2`), `sde-s2-dg1` (from `sde-s2-c2`),
  `sdehalfgrav-remcost-s0-dg1` (from `sdehalfgrav-remcost-s0`),
  `sdehalfgrav-remcost-s1-dg1` (from `sdehalfgrav-remcost-s1`) — all
  2M, `k_step_event`/`walk_gait_gate` left at 0 to isolate the new
  lever alone, all VERIFIED RUNNING (train-7/10/9/8) after one
  REFUSED/requeue race with the sibling `base-s0c1-dgate-c1` launch
  (mechanical, resolved by `drain`). **Correction to the ~15:1x
  entry's own caution:** plain `respec --init-from` did NOT hit the
  `--use-sde`+`--init-from` SystemExit gotcha on any of the 4 arms —
  all four parents' own commands already carry `--activation-fn ''`
  (empty string, falsy) from the earlier sde-c1 crash-forensics fix,
  so the guard never fires; `sde-s1-dg1`'s pod log confirms a clean
  2.1M-step run (checkpoint saved, `ep_rew_mean` 20.1, no traceback).
  The MANUAL `backlog add` workaround is only needed for a parent
  whose own command still passes a truthy `--activation-fn` (i.e. an
  original from-scratch sde launch, not one of these c2-generation
  continuations) — re-check per-parent before assuming the workaround
  is required. Gate (all 4, pre-registered): watch
  `env/walk_duty_gate_factor` in each run's `wandb_history.csv` for a
  real climb toward 1.0 (healthy) vs staying pinned near ceiling
  despite low duty (the exact `walk_gait_gate` failure signature) —
  next cycle to touch any of these four reads that column first, then
  the harness gate's own `duty_cycle`/`gait_valid` once the prestage
  evals land. PASS on a given arm funds a 40M acquisition follow-up;
  FAIL (factor saturates or reward/speed collapses) closes
  `walk_duty_gate` on that recipe. This cycle's own assigned run
  (`headset-base-irr-c2`) triage is separate, below/pending its own
  gate sync — not blocking this refill.

- 09-05 ~15:1x MECHANISM BUILT + REPAIR CANARY LAUNCHED:
  `reward.walk_duty_gate` — per-leg contact-DUTY income gate
  (transport income x [(1-g) + g * MIN over support legs of
  clip(trailing-3s contact duty / 0.15, 0, 1)]). Motivated by the
  s0c1-acq1 dig-in below: it combines the two proven-right halves of
  the failed levers (walk_gait_gate's income-collapse STRUCTURE +
  k_park's duty SIGNAL — the harness's own sacrifice bar) and is
  un-dodgeable by the token-swing trick that gamed the completion
  window (one contact tick moves a 3 s window mean ~1/300). Default
  0 = bit-exact off; state (`_dgate_hist`) rides MJX_SNAPSHOT_EXTRA.
  Bank-proved in `test_walkscratch_easy_pilot.py` (5 new tests,
  27/27 file, +17/17 adjacent semantics spot-check): default-off
  bit-exact; healthy six-leg tripod keeps 100% income (measured
  factor 1.0 throughout); the leg-4-aloft exploit twin loses ~430/ep
  on an IDENTICAL trajectory; a 0.2s-touch-every-2s token twin stays
  collapsed (restores <50% of removed income — the exact dodge that
  restored ~100% under walk_gait_gate). Snapshot
  `exp/walk-duty-gate-mechanism-0905`. Launched
  `headset-base-s0c1-dgate-c1` (2M canary, VERIFIED RUNNING
  train-5): warm-start of the FAILED s0c1-acq1 checkpoint itself
  with the gate on — the direct does-the-leg-come-back-down read.
  **Next (pre-registered, launch when the sde gg n=4 verdicts land):
  the same walk_duty_gate repair on a gSDE LEGPARK checkpoint**
  (pick the strongest surviving sde parent then; use the gg2-style
  MANUAL arg-vector build via `backlog add`, NOT respec — the
  `--use-sde`/`--activation-fn`+`--init-from` respec SystemExit
  gotcha; cfg add `reward.walk_duty_gate=0.9`). If the base-family
  canary shows the leg recovering, this mechanism also becomes the
  candidate hardening dose for future acq recipes.

- 09-05 ~14:6x this cycle, capacity sweep after the verdicts below:
  found `headset-base-irr-c2` (declared "still training" at cycle
  start) had ALSO finished (reward quarters 42.0/88.3/150.5/198.5,
  matching -c1's fingerprint) with its gate eval already genuinely
  computing remotely on train-0 (not mine to have started, prestage or
  a concurrent cycle beat me to it) — registered via `ops.sh
  evalpending add` + a backgrounded `ops.sh pollreap` rather than
  blocking or duplicating; read `logs/ckpt_eval/cw_walkscratch_
  easy0905_headset_base_irr_c2_gate/report.json` next cycle, do not
  re-launch. Separately, with 7-8 GPU pods genuinely idle (`ps aux`
  confirmed, not just ledger-free) and the operator's full-fleet order
  live, launched the halfgrav irr-timing rung's 3rd independent
  cross-checkpoint canary, `headset-halfgrav-irr-c3` (2M, warm-started
  from this cycle's own `headset-halfgrav-s3acq` ACQ PASS champion —
  the halfgrav family's third and last clean champion, completing the
  n=3 confirmation pattern already used for irr-c1/-c2 off
  acq1/s1acq), VERIFIED RUNNING on train-1. Left the remaining
  ~6 idle pods untouched: every other open walkcurr question either
  depends on an in-flight sibling's still-computing read (both irr
  acq1 arms, base-irr-c2's gate, the sde gait-gate n=4 cohort owned by
  concurrent cycles) or requires a genuinely new mechanism/bank pass
  (sde per-leg-utilization pricing design, closed per CURRENT_TRUTHS;
  heading-set widening, premature before the irr rung itself closes
  for both gravity cells) — not safe filler for a triage cycle.

- 09-05 ~14:5x this cycle: two verdicts + one refill closing two open
  campaign threads. (1) `headset-halfgrav-s3acq` **ACQ PASS** — closes
  the halfgrav heading-family n=3 confirmation set (acq1/s1acq/s3acq
  all PASS): 0/24 falls, gait_valid 22/24 (walk/det 6/6, walk/sto 6/6,
  walk_startjitter/sto 6/6, walk_startjitter/det 4/6 with leg[1]
  duty 0.10-0.15 but swing_count still 82-164/20s — active
  micro-underuse, not LEGPARK-SKATE), fwd med 2.32-2.80m/20s, slip med
  1.83-2.72 (tight, near-campaign-best). This is a genuine improvement
  over the seed's own 2M canary (which had flagged leg-1 sacrifice in
  BOTH det panels, 3/6 and 1/6) — clears the sibling entry's own
  `>=4/6 primary walk/det` + `>=13/24 overall` bar comfortably. SKILLS.md
  updated. (2) `headset-base-irr-c1` **CANARY PASS** — mechanism-health
  confirmed (walk_speed alive 0.155-0.170 all 4 quarters, ep_rew_mean
  monotonic 42->191, ep_len_mean 108->488) AND the prestage tooling
  had already run the full 24-ep gate panel at 2M: 0/24 falls,
  gait_valid 21/24 (only the established base-family walk_startjitter/
  det leg1/4 favoritism, 3/6). Both gate evals had gone ORPHANED
  (the known 09-05 tooling gotcha — pullckpt synced but eval_checkpoint
  was still computing remotely with no local poller left); reattached
  via `ops.sh pollreap` for both, ~30min. Refill: launched
  `headset-base-irr-acq1` (40M, own-checkpoint warm start from
  `headset-base-irr-c1`'s own 2M checkpoint via `respec
  --init-from-source`), VERIFIED RUNNING on train-3 — mirrors the
  halfgrav sibling's `headset-halfgrav-irr-acq1` (already running via a
  concurrent cycle) so both gravity cells now have the irr-timing rung
  funded at full budget. Evidence: `logs/ckpt_eval/cw_walkscratch_
  easy0905_headset_{halfgrav_s3acq,base_irr_c1}_gate/report.json`, W&B
  `uwewt762`/`0zs57vwc`.

- 09-05 ~14:5x DIG-IN closure: `headset-base-s0c1-acq1` **ACQ FAIL
  (MISALIGNED)** — the 3rd base-family 40M heading seed walks fast
  with 0/24 falls but chronically parks leg 4 (duty 0.03-0.07,
  29-71 airborne paddle-swings/20s, never load-bearing) in ALL 12
  det episodes; gait_valid 9/24 vs the siblings' 18/24. The caveat
  HARDENED with budget: parent canary had walk/det 6/6 valid with
  leg-4 duty 0.10-0.15 (marginal), and wandb_history shows
  ep_rew_mean 342->724 while `env/walk_speed` sat flat at 0.161 for
  the whole 40M — reward paid while the marginal leg slid under the
  0.10 sacrifice bar. THREE campaign-level consequences:
  (1) **base heading family CLOSES at 2/3 ACQ PASS** — champions are
  `headset-base-acq1` / `headset-base-s1c1-acq1`, never `s0c1-acq1`;
  campaign-best overall remains `headset-halfgrav-s1acq` (24/24).
  (2) **LEGPARK is NOT gSDE-specific**: 1/3 plain-Gaussian base
  seeds hardens into the paddle variant at 40M. Any future diet
  repair (hard per-leg min-duty price, non-gameable — the
  completion-window `walk_gait_gate` is closed 2/2 as gameable)
  benefits every cell, not just sde revival. Marginal per-leg duty
  (<0.15 in walk/det) at canary time is now an early-warning flag
  worth recording in canary verdicts.
  (3) **Explicit gait_valid-majority bar adopted for all acquisition
  gates** (assume-and-go, recorded in OPERATOR_QUESTIONS.md
  q_20260905T1455Z): ACQ PASS requires gait_valid >=4/6 in the
  primary un-perturbed walk/det mode AND >=13/24 overall; a
  persistently sacrificed leg in walk/det disqualifies regardless of
  speed/falls (formalizes the guardrails `gait_validity_gate` that
  every prior PASS already happened to satisfy — no prior verdict
  flips). Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  base_s0c1_acq1_gate/report.json`, W&B `6n31rtzj`.

- 09-05 ~14:5x this cycle, concrete NEXT for the closed `walk_gait_gate`
  lever (see the 14:4x entry below and CURRENT_TRUTHS.md — 4/4 FAIL,
  bare sde x2 + sdehalfgrav+remcost x2): scoped, NOT built this cycle
  (would need careful `mjx_vec_env.py` snapshot integration, out of
  budget for a triage cycle) — a duty-FRACTION gate, not a recency-
  since-last-swing gate. `walk_task.py`'s per-tick contact loop
  (~line 4900) already computes a real touch-sensor `contacts[f]`
  bool every commanded tick (gated behind existing `k_swing/k_step/
  g_gait`-type keys being nonzero — add the new key to that gate
  list). Add a per-leg EMA `self._duty_ema[f] += (dt/tau) * (float(
  contacts[f]) - self._duty_ema[f])`, tau ~4-6s (long enough to
  average a full stride, short enough to react within an episode),
  init to 1.0 (grace, matches `walk_gait_gate`'s start-of-episode
  convention). New key `reward.walk_duty_gate` (0..1, default 0 =
  off) multiplies transport income by MIN over support legs of a
  smooth ramp `clip((duty_ema - floor_lo)/(floor_hi - floor_lo), 0,
  1)` — floor_lo/floor_hi ~0.08/0.15 (straddling the harness's own
  `gait_valid` duty>0.10 bar). Why this escapes the closed lever's
  rare-token-dodge: `walk_gait_gate` scores RECENCY of the last
  qualifying touchdown (a single brief contact every ~2-4s re-arms it
  to 1.0 for a whole window), but `duty_ema` integrates TIME FRACTION
  — the measured LEGPARK-SKATE fingerprint (duty 0.0-0.03 all four
  gg-repair FAILs) stays far below even a lenient 0.08 floor no
  matter how the rare touches are timed, while genuine six-leg gaits
  (duty 0.13-0.48 every PASS this campaign) clear it with margin.
  MUST add `_duty_ema` to `SimHexapodJointWalkEnv.MJX_SNAPSHOT_EXTRA`
  (the GPU vec-env pooled-reset attribute list, currently ~line 408)
  and reset it at all 4 existing `_gait_last_step = [0] * 6` sites —
  missing either is a silent GPU-only correctness bug, not a crash.
  SPECIFICATION-phase prerequisite before ANY launch: a
  `test_task_semantics.py` bank twin reproducing the rare-token-dodge
  itself (a scripted leg held aloft except one qualifying touchdown
  every ~3s, modeled on the existing `flagleg`/`midpin` twins ~line
  5555-5680) proving (a) the OLD `walk_gait_gate` fails to collapse
  its income (documents the exact loophole formally) and (b) the NEW
  `walk_duty_gate` does collapse it while leaving the honest `gait`
  twin's income within a few percent — same structure as the
  `WALKCURR_PF_IDLE_TERM` bank (~line 8748). Not a pre-registered
  backlog item (no bank exists yet) — the next cycle with room to do
  this carefully should build bank-first, verify green, snapshot,
  THEN queue a 2M canary.

- 09-05 ~14:4x this cycle: `sdehalfgrav-remcost-{s0,s1}-gg2` both
  **ACQ FAIL (misaligned)** — the `walk_gait_gate`+`k_step_event`
  structural repair does NOT generalize off bare sde onto the
  sdehalfgrav+remcost recipe, closing the lever at 4/4 across every
  recipe tried. Evidence (`logs/ckpt_eval/cw_walkscratch_easy0905_
  sdehalfgrav_remcost_s{0,1}_gg2_gate/report.json`, 40.37M steps each):
  0/24 falls both seeds, but `gait_valid` only 2/24 both seeds (legs
  1/4 chronically parked, `duty_cycle` 0.0-0.03 in nearly every
  episode vs 0.77-0.89 for the four active legs). Video (`walk_det_0.
  png` contact sheets) shows the SAME splayed-rigid-leg drag already
  seen on the bare-sde FAILs. Root cause identical too:
  `env/walk_gait_gate_factor` (`wandb_history.csv`) sits SATURATED at
  0.985-1.0 for essentially the entire 40M run on both seeds — never
  a real ~0->1 climb, already at ceiling from early training despite
  the harness flagging near-total leg sacrifice the whole time.
  Reward quarters strongly rising both seeds (s0
  -539.9/-240.3/361.1/991.9, s1 -694.5/-530.0/-39.7/538.0) is NOT
  evidence of real progress per 08-21: the mechanism's own internal
  proxy is already saturated, so more budget cannot move a factor
  reading 1.0. **The `walk_gait_gate`+`k_step_event` repair is now
  CLOSED 4/4 (bare sde x2 `sde-s1-c3gg`/`sde-s2-c3gg`, sdehalfgrav+
  remcost x2 this entry) — do not relaunch it anywhere in the sde/
  sdehalfgrav family.** CURRENT_TRUTHS.md updated. Both `idle-
  terminate` and `gait-gate` repair levers are now closed on every
  recipe tried; any further LEGPARK-SKATE repair on this family needs
  a genuinely new per-leg-utilization pricing mechanism (hard
  minimum-duty/swing-count price, not a gameable completion score),
  its own design+bank pass before further spend. `sde-s0-c4gg`/
  `sde-s3-c1bgg` (2 more bare-sde gait-gate seeds, concurrent-cycle-
  owned) still in flight at cycle end — if either FAILs the same way
  that's 6/6 confirmation and fully forecloses the lever; if either
  clears, that reopens it and this closure needs revisiting. Also
  this cycle: `headset-halfgrav-irr-c1` **CANARY PASS**
  — the irregular-direction-change-timing canary on the 0.5g heading
  family, mirroring the base-family `irr-c1`/`-c2` pair on the other
  physics cell. Evidence (`wandb_history.csv`, 2.1M steps): `env/
  walk_speed` alive across all 4 quarters (0.175/0.183/0.186/0.183
  m/s, not decaying), `rollout/ep_rew_mean` rising monotonically
  (36.2/65.6/99.0/129.2), `rollout/ep_len_mean` tripling (108->488,
  fewer early falls), `env/wrong_way` low (2.0-3.0%) throughout — its
  own harness gate eval was still genuinely computing on train-2 at
  verdict time (registered `evalpending` + backgrounded `pollreap`,
  non-blocking; gate text explicitly allows a canary verdict off the
  reward/speed trend alone). Funded the 40M acquisition follow-up
  `headset-halfgrav-irr-acq1` (own-checkpoint `--init-from-source` off
  `headset-halfgrav-s1acq`, VERIFIED RUNNING on train-2) to test
  whether jittered-timing six-leg walking actually matures at the
  real gate rather than just surviving. Also found+registered
  `sdehalfgrav-remcost-{s0,s1}-gg2` (the gait-gate-repair
  generalization test onto the remcost recipe) both FINISHED (40.37M,
  reward quarters strongly rising/not flat: s0
  -539.9/-240.3/361.1/991.9, s1 -694.5/-530.0/-39.7/538.0) with their
  own harness gate evals genuinely still computing remotely (train-10/
  train-11) — registered `evalpending` + backgrounded `pollreap` for
  both rather than blocking; per 08-21 the still-rising reward means
  these are NOT a flat-reward auto-fail regardless of what the gate
  read shows, but the actual gait_valid verdict needs the harness
  report, not yet landed. Left unverdicted this cycle; read `logs/
  ckpt_eval/cw_walkscratch_easy0905_sdehalfgrav_remcost_s{0,1}_gg2_
  gate/report.json` once they land. Capacity at cycle end: only
  train-5/train-7 genuinely idle (no eval, no trainer) — every other
  next-rung question (base/halfgrav heading n=3, both irr-timing
  cells' n=2 canaries, sde bare-family gait-gate closure at n=4,
  remcost gait-gate generalization) already has evidence in flight
  elsewhere; backlog.json empty; no non-duplicative arm launched on
  the 2 free pods rather than invent filler.

- 09-05 ~14:3x this cycle: `headset-halfgrav-s1acq` **ACQ PASS** —
  cleanest heading-acquisition read of the whole campaign: 24/24
  `gait_valid`, ZERO sacrificed legs in every one of the 4 scenarios
  (incl. `walk_startjitter/det`, the one scenario where every other
  seed in both heading families shows leg1/4 favoritism), 0/24
  falls, `slip_per_m` med 2.28-2.48 (tightest of the campaign, every
  prior PASS ran 2.4-5.2), fwd 0.15-0.17 m/s, no belly drag. 2nd of
  the halfgrav family's n=3 acq1 seeds (`halfgrav-acq1` PASS,
  `s1acq` PASS, `s3acq` still evaluating on another pod). SKILLS.md
  updated. Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_
  headset_halfgrav_s1acq_gate/report.json`, W&B `yqm9c7e8`. Capacity
  check this cycle: 8/11 reachable GPU pods were running on-pod
  evals (CPU-only, GPU idle) for other in-flight arms — `train-4`/
  `train-5`/`train-7` were the only genuinely idle pods (no process
  at all). Used one to launch a base-heading-family confirmation
  seed (`headset-base-irr-c2`, below); left the other two idle
  rather than invent filler, since every other next-rung question
  (does `walk_cmd_resample_jitter` survive a 2nd seed, does the
  sde `walk_gait_gate` repair replicate at n=4, does `halfgrav-s3acq`
  close the family) is already funded and mid-eval elsewhere.

- 09-05 ~14:4x this cycle: launched `headset-base-irr-c2`, a second
  independent seed of the already-running `headset-base-irr-c1`
  irregular-direction-change-timing canary (`goal.walk_cmd_resample_
  jitter=0.5` on top of the acq1 recipe), warm-started from the
  OTHER already-PASSed base seed's own 40M checkpoint
  (`headset_base_s1c1_acq1.zip`, not the same source as `-c1` which
  used the flagship `headset_base_acq1.zip`) — a genuine cross-seed
  read of whether the irr mechanism generalizes, not a duplicate.
  Cheap (2M canary, ~2min GPU time): batching this now rather than
  waiting for `-c1`'s own not-yet-landed verdict follows the 08-22
  batching guidance for a seed-count question this inexpensive.
  VERIFIED RUNNING on a genuinely idle pod. If `-c1` fails outright
  before `-c2` finishes, read both together — a seed-specific fluke
  vs. a class failure is itself useful information.

- 09-05 ~14:3x this cycle: `sde-s1-c3gg`/`sde-s2-c3gg` both **ACQ
  FAIL (misaligned)** — the structural `walk_gait_gate`+`k_step_event`
  repair does NOT escape LEGPARK-SKATE, closing this lever 2/2. It
  partially works: multi-leg sacrifice (2-3 legs on the `-c2` parents)
  narrows to exactly ONE chronically-parked leg per seed (leg 4 on
  s1, leg 1 on s2; duty 0.0, ~3 swings/20s, every det/sto/startjitter
  scenario) — but harness `gait_valid` is still 1/24 (s1) and 0/24
  (s2), 0 falls, walk_speed stable 0.13-0.17 m/s, reward still
  climbing gently to ~2600-2700 at the 40M cutoff with no plateau.
  Root cause, read directly from `wandb_history.csv`: `env/walk_gait_
  gate_factor` sits at 0.98-0.99 for the ENTIRE back half of training
  even though the harness's duty>0.10 bar flags the same leg as
  sacrificed throughout — the reward-side gate's "recently completed
  swing" scoring window is satisfied by a rare token swing every
  several seconds and never drives the MIN-over-legs factor down the
  way a true duty-cycle price would. Same rare-token-dodge shape as
  the already-closed qvel-idle-terminate lever, different threshold.
  Contact sheets confirm visually (one leg rigid/extended, minimal net
  body translation). Per 08-21 this is MISALIGNED, not continue-blind:
  the mechanism's own internal proxy is ALSO plateaued at its ceiling,
  so more budget would not move it. **Both named bare-sde repair
  levers (idle-terminate, gait-gate) are now closed 2/2 each** — no
  cheap repair variant remains untried; `CURRENT_TRUTHS.md` updated.
  Any further sde revival needs a genuinely new per-leg-utilization
  mechanism (hard minimum-duty/swing-count price, not a gameable
  completion score) with its own design+bank pass before further sde
  spend. `sdehalfgrav-remcost-{s0,s1}-gg2` (same lever on the remcost
  recipe, funded by a prior cycle) left running untouched — its own
  report.json may or may not share this exact failure, read it before
  assuming the same fate. Evidence: `ops.sh review cw-walkscratch-
  easy0905-sde-s{1,2}-c3gg`, W&B notes `zr5lg756`/`vb2m7gr2`.
  Awaiting `sde-s0-c4gg`/`sde-s3-c1bgg` (this cycle's assigned pair,
  same gait-gate repair applied to the other two originally-failed
  seeds `sde-s0-c4`/`sde-s3-c1b`) — gate evals still genuinely
  computing on train-8/train-9 at cycle end (video-every=1, ~9-13min
  in of an expected ~35-40min full 24-episode panel); registered via
  `ops.sh evalpending add` (both) + a backgrounded `ops.sh pollreap`
  (both, max 60min) rather than blocking this cycle — do NOT
  re-launch, read `logs/ckpt_eval/cw_walkscratch_easy0905_sde_s{0_c4,
  3_c1b}gg_gate/report.json` once they land. If both replicate this
  same 1-leg-parked/gate-factor-plateau fingerprint (expected, same
  mechanism/family), the bare-sde cell can be formally CLOSED at 4/4
  gait-gate-repair FAIL; if either clears (gait_valid majority true,
  no chronically-parked leg), that would be the first genuine escape
  and reopens the mechanism as viable after all — read carefully, do
  not assume from this cycle's 2/2.

- 09-05 ~14:1x DIG-IN TRIGGER (this cycle) — `headset-base-s0c1-acq1`
  finished (40.37M steps, reward quarters 342.6/623.2/696.5/720.2,
  plateauing not still-climbing) but its gate eval never made it to
  the controller: the prestage `pullckpt` synced fine, but the actual
  `eval_checkpoint` pass was still computing on train-3 when a
  DIFFERENT concurrent cycle's drain reused that SAME pod for the
  NEXT training job (`headset-base-irr-c1`) at 14:02 — harmless to
  both processes (pod has spare CPU, `ps aux` confirmed the harness
  kept computing fine under the new trainer at 860% CPU), but the
  local supervisor that was meant to copy results back got orphaned,
  so `logs/ckpt_eval/..._gate/` sat missing with no artifact dir and
  no active local process. **New tooling gotcha, banked in
  CURRENT_TRUTHS.md**: a pod's outstanding gate podeval can go
  silently orphaned when its own pod is drained into a new training
  launch mid-eval; `ops.sh podeval <run>` correctly detects the
  remote pass is `already RUNNING` and refuses to duplicate it, but
  nothing then re-polls for completion — use `ops.sh pollreap <run>`
  (backgrounded) to reattach. Recovered it this cycle (pollreap synced
  all 24 episodes + videos, ~30 min after finding it stuck). Per-leg
  read: 0/24 falls, speed 0.137-0.191 m/s every episode (clears the
  bar), BUT leg 4 duty 0.03-0.09 (swings 29-71/20s vs 190-260 for the
  other five) in **ALL 6 plain `walk/det` AND all 6
  `walk_startjitter/det` episodes** (`gait_valid` 0/6 + 0/6), plus 3/6
  `walk_startjitter/sto`; only plain `walk/sto` is clean (6/6).
  Net: 9/24 gait_valid, 15/24 flagged. **This is a materially worse
  read than the family's own established precedent**:
  `headset-base-acq1` (same recipe class, PASSED) had the identical
  single-leg-favoritism fingerprint confined ENTIRELY to
  `walk_startjitter/det` (0/6 there, but a CLEAN 6/6 on plain
  `walk/det` — `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_acq1_gate/report.json`).
  Here the same pathology has generalized from the perturbed-start
  edge case into the PRIMARY un-perturbed walk scenario — exactly the
  "watch whether it clears with budget or hardens" question the
  09-05 ~13:0x canary verdict flagged for this specific seed, now
  answered: it HARDENED, not cleared. Not falls, not full
  LEGPARK-SKATE (leg 4 still swings dozens of times/episode, duty
  isn't pinned at 0), but a real one-leg-underutilized pattern that
  fails this gate's own "six-leg lift/place on video" clause on the
  primary mode. Video: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s0c1_acq1_gate/walk_det_0.mp4`
  (+ `_sheet.png`). Leaving UNVERDICTED per model-tiering (metrics
  anomalous vs a named same-family precedent beyond eval noise) —
  **DIG-IN: cw-walkscratch-easy0905-headset-base-s0c1-acq1** — decides
  whether this seed should be excluded from base-family champion
  selection and whether the campaign's acquisition gate needs an
  explicit gait_valid-majority bar, not just net-forward-speed +
  no-falls.

- 09-05 ~14:2x this cycle: `headset-base-s1c1-acq1` **ACQ PASS** —
  a THIRD base-family heading-set seed, and unlike the concurrent
  cycle's `s0c1-acq1` finding just above, this one reproduces
  `headset-base-acq1`'s CLEAN fingerprint exactly: 0/24 falls, speed
  0.14-0.172 m/s every episode, `gait_valid` 18/24 with the 6 false
  episodes ALL confined to `walk_startjitter/det` (leg1/4 duty drops
  but `swing_count` stays 39-160/20s, micro-stepping not
  LEGPARK-SKATE), plain `walk/det` and `walk/sto` both clean 6/6,
  slip med 3.98 (same 3.0-4.8 band as every prior base-family PASS).
  SKILLS.md row added. **Family read after all three heading-set
  seeds**: `acq1` clean, `s1c1` clean, `s0c1` hardened-worse (leg 4
  sacrificed in plain walk too, not just startjitter) — 2/3 clean,
  1/3 a genuine regression on THIS specific seed, not a family-wide
  fingerprint shift. Champion pick should use `acq1` or `s1c1`, not
  `s0c1`, until/unless the open DIG-IN above says otherwise. This
  cycle's own prestage gate eval was still genuinely computing at
  spawn (registered via `ops.sh evalpending add` rather than
  re-polling — worth reusing next time a fresh spawn hits a
  still-running eval instead of exiting empty). Capacity at cycle
  end: 9/12 pods genuinely ps-busy with in-flight campaign evals
  (both heading families' n=3 confirmations, the two new irr-timing
  canaries, the sde gait-gate n=4 cohort) — only train-4/train-7
  idle, no new arm launched since every next-rung candidate needs one
  of those in-flight reads first (launching now would be a
  same-recipe dribble ahead of evidence, not a batch).

- 09-05 ~13:3x this cycle: `headset-halfgrav-s1`/`-s3` (heading canary,
  n=3 seed check for the 0.5g family) both **CANARY PASS**. `s1` is
  the cleanest read of the whole heading-canary cohort so far (24/24
  gait_valid, 0 falls, slip 1.8-3.0 med 2.1-2.4 vs the 2.9 band, fwd
  3.2-4.0m/20s across all 3 headings, all six legs balanced duty
  0.14-0.35). `s3` clears the bar with a caveat (0/24 det falls, slip
  1.9-2.6, but leg 1 intermittently sacrificed in det-mode only —
  gait_valid 3/6 and 1/6 on the two det panels, clean 5/6 on both sto
  panels; not the LEGPARK-SKATE full-shuffle pattern, flagged for the
  acq follow-up to watch). Both n=3 for the halfgrav-family heading-
  canary cohort (c2/s1/s3) now complete. Funded both 40M acquisitions,
  `headset-halfgrav-s1acq` (train-0) + `headset-halfgrav-s3acq`
  (train-1), `--init-from-source` from their own 2M checkpoints,
  matching the c2->acq1 pattern (see the acq1 PASS row below) — both
  VERIFIED RUNNING (ps-confirmed genuine trainer processes, not just
  ledger state). Independently found+chased `sde-s1-c3gg`/`sde-s2-c3gg`
  (both finished 40M, reward quarters 1436/2477/2616/2687 and
  1410/2465/2563/2630, both monotonic — the run that decides whether
  the structural `walk_gait_gate` repair actually escapes LEGPARK-SKATE
  or the sde cell closes for good) sitting with NO gate eval running
  (their pods had gone idle) — kicked off `ops.sh podeval` for both by
  hand so the data is ready for the next pass; still mid-run at cycle
  end (video-every=1, 24-episode panel, ~13/24 videos rendered after
  20+ min) — do NOT re-launch, read `logs/ckpt_eval/cw_walkscratch_
  easy0905_sde_s{1,2}_c3gg_gate/report.json` once it lands (this is
  THE decision point named in the 12:3x entry below). Two tooling
  snags hit and fixed this cycle, both worth banking: (1) a stale
  `/workspace/hexapod/.git/index.lock` (leftover from an unrelated
  `git add -A` that died with a SIGBUS mid-snapshot) blocked
  `snapshot.sh` with "Unable to create index.lock" — no live git
  process was holding it (`ps aux` checked), safe to remove by hand;
  retried snapshot+push succeeded clean. (2) `s3acq`'s own respec
  launch raced ITSELF: `launch_run.py` genuinely `kexec`'d the trainer
  (confirmed alive via `ps aux`, W&B run `uwewt762` genuinely
  `state=running`) but its own post-launch verification then
  re-checked pod occupancy, saw the process it had just started, and
  wrote a false `REFUSED: hexapod-mjx-train-1 already runs
  cw-walkscratch-easy0905-headset-halfgrav-s3acq` — the ledger said
  REFUSED while the GPU was genuinely training a real, undropped run.
  Repaired by hand via `launch_run.py update` (status/wandb_id/pod/
  pid); `launch_run.py checkup` afterward confirms HEALTHY. Any cycle
  seeing "REFUSED: already runs <run-you-just-launched>" immediately
  after a `--now` respec should check `ps aux`/W&B before assuming the
  launch failed — it may have succeeded and only the verification race
  lied. (Separately: my own read of `sde-idleterm-{s0,s1}` reached the
  same "detector gamed by qvel jitter, don't fund a continuation" call
  the concurrent cycle's CANARY FAIL verdict below already recorded —
  cross-confirms it, not duplicated here.)

- 09-05 ~13:2x this cycle: `headset-halfgrav-acq1` **ACQ PASS** — first
  FULLY clean (24/24 `gait_valid`, zero sacrificed legs anywhere) 3-
  heading 40M acquisition in the campaign, 0/24 falls, median fwd
  speed 0.147-0.164 m/s, slip 2.4-2.6/m. Heading PRECISION caveat
  (moderate/noisy `course_err`, worse under sto) flagged as a next-
  rung hardening item, not disqualifying — see SKILLS.md row. Also
  verdicted 3 unclaimed-finished runs found idle-next-to-real-work:
  `sdehalfgrav-remcost-s0` ACQ CONTINUE (survival fix confirmed,
  LEGPARK-SKATE fingerprint matches `remcost-s1`) and `sde-idleterm-
  {s0,s1}` both CANARY FAIL - MECHANISM (idle-terminate detector gamed
  via qvel jitter, downloaded final-checkpoint video shows the SAME
  frozen splayed pose as `sde-s0-c4`, no real six-leg motion — do not
  fund a 40M continuation of this lever). REFILL: generalized the
  bank-proven `walk_gait_gate`+`k_step_event` repair (already funded
  on bare-sde as `sde-{s1,s2}-c3gg`) onto the `sdehalfgrav-remcost`
  recipe as own-checkpoint continuations `sdehalfgrav-remcost-{s0,s1}-
  gg2` (VERIFIED RUNNING, train-10/train-11) — tests whether the gait-
  gate fix generalizes beyond bare sde. Hit a NEW tooling gotcha doing
  this (`respec` cannot strip a bare flag like `--use-sde` from a
  from-scratch gSDE source, so two earlier attempts — `remcost-s0-gg`/
  `remcost-s1-gg`(-rr1) — silently trained fresh-scratch instead of
  continuing; caught via `ops.sh procs`, killed before meaningful
  spend, fixed via a hand-built arg vector through `backlog add ... --
  <args>` instead of `respec`). Gotcha banked in `CURRENT_TRUTHS.md`.

- 09-05 ~13:1x `sde-idleterm-s0`/`sde-idleterm-s1` **CANARY FAIL —
  detector gamed, not repaired.** The alternate LEGPARK-SKATE repair
  lever (porting the bank-proven `WALKCURR_PF_IDLE_TERM` qvel-
  termination combo onto the bare sde recipe, launched 12:4x alongside
  `walk_gait_gate`/c3gg) looked escape-shaped in W&B alone
  (`rollout/ep_len_mean` triples 117-118 -> ~315 over the 2M budget,
  `walk_idle_terminate` termination reason disappears from the final
  checkpoint's rollout captions) but the downloaded+frame-stripped
  final-checkpoint video on BOTH seeds shows the SAME static
  splayed-leg pose as `sde-s0-c4`'s disqualified frozen stance,
  on-screen speed 0.001-0.032 m/s, no leg mid-swing anywhere: enough
  qvel/servo jitter to dodge the idle-terminate detector's threshold,
  not a genuine escape into six-leg walking. Closes this as the
  10th-scope repair attempt on this basin (2nd on the easy0905 sde
  cohort specifically, after `walk_gait_gate`'s prior FAIL history on
  the harder joyfullcurr13 curriculum). **No 40M continuation funded.**
  sde/sdehalfgrav family revival now rides entirely on the structural
  `walk_gait_gate` repair (`sde-s1-c3gg`/`sde-s2-c3gg`, already funded
  and training; `sdehalfgrav-remcost-{s0,s1}-gg*` mirrors it for the
  halfgrav+gSDE cell) — if that also fails, the per-leg-utilization
  pricing design question reopens from scratch, no cheap variant left
  untried. Evidence: `ops.sh review cw-walkscratch-easy0905-sde-
  idleterm-{s0,s1}`; CURRENT_TRUTHS.md updated.

- 09-05 ~13:1x `headset-base-acq1` **ACQ PASS** — first family member to
  clear the FULL 40M heading-generalization acquisition rung (3-heading
  set 0/+45/-45deg, resampled every 6s, no new reward keys). Gate
  (`logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_acq1_gate/
  report.json`, 24 eps): 0/24 falls, speed 0.147-0.20 m/s every ep,
  gait_valid true 18/24 — the 6/24 false episodes are ALL
  `walk_startjitter/det`, with leg1/4 duty dropping to 0.04-0.14 but
  swing_count still 39-121/20s (micro-stepping, not LEGPARK-SKATE's
  near-zero-touch pattern), same fingerprint already CANARY-PASSed on
  `headset-base-s0c1`/`s1c1`. Same slip (3.0-4.8/m)+small-stride
  (12-21mm) caveats as every base-family PASS this campaign; heading
  tracking loose (course_err 20-94deg) but this rung's gate only asks
  for net forward motion per heading, not tight tracking. SKILLS.md
  updated. Next: let `s0c1-acq1`/`s1c1-acq1` land for n=3 confirmation,
  then pick a base-family heading champion once halfgrav's `acq1` also
  reports.

- 09-05 ~13:0x `headset-base-s0c1`/`headset-base-s1c1` CANARY PASS
  (3rd + 4th base-family heading-canary seeds, same recipe as
  `headset-base-c1`), gate evals synced same cycle: 0/24
  falls/terminations each; plain `walk` det+sto 12/12 `gait_valid`
  both seeds (0 sacrificed legs), fwd_dist 1.95-3.82m/20s (0.10-0.19
  m/s), slip_per_m 2.8-5.2 (near/above the 2.9 band — paddle-quality
  at 2M, not gate-blocking for a canary). One narrow shared weak
  spot: `walk_startjitter/det` sacrifices leg [4] (s0c1, 6/6) or
  [1]/[1,4] (s1c1, 5/6) — a single/dual-leg favoritism specific to
  the perturbed-start deterministic scenario only; `walk_startjitter/
  sto` mostly or fully recovers (5/6, 6/6). NOT the gSDE
  LEGPARK-SKATE fingerprint (plain Gaussian family, no `--use-sde`,
  no near-zero-stride paddling, no reward-vs-speed divergence) — 19/24
  episodes real six-leg locomotion on BOTH seeds at just 2M steps,
  the base family's heading generalization now stands at n=4 (c1 +
  s0c1 + s1c1, all PASS; halfgrav at n=3 with s1/s3 canaries still
  computing). Launched both 40M own-checkpoint acquisition
  continuations mirroring `headset-base-acq1`: `headset-base-s0c1-
  acq1` (train-3) + `headset-base-s1c1-acq1` (train-5), both VERIFIED
  RUNNING — watch whether the startjitter/det leg-favoritism clears
  with budget or hardens into a real pathology. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s{0c1,1c1}_gate/
  report.json`, W&B notes on `tm703vax`/`xors486s`.
- 09-05 ~12:4x DIG-IN CLOSED (independent cycle) — `sde-s0-c4` FAIL,
  confirms **LEGPARK-SKATE** as a 4th seed (this run) alongside
  `sde-s1-c2`/`sde-s2-c2`/`sde-s3-c1b` above: gate harness (24/24
  episodes, det+sto+startjitter) shows leg 4 duty 0.00-0.03 (3-9
  ground touches/20s, every scenario) + leg 1 duty 0.01-0.23
  (sacrificed in det), remaining 4 legs duty 0.6-0.97 but
  `stride_m_mean`=0.007 (7mm micro-quiver), 0/24 falls, slip/m
  4.8-5.2 (vs the 2.9 band). Same class, independently reproduced.
  Full verdict: `ops.sh review cw-walkscratch-easy0905-sde-s0-c4` /
  W&B notes on run `6e15jpmw`. **SECOND, ALTERNATE repair lever
  launched in parallel to this cycle's `walk_gait_gate` repair**
  (worth funding both — cheap, and a real A/B on which structural
  fix actually escapes the basin): `cw-walkscratch-easy0905-sde-
  idleterm-{s0,s1}` (2M canaries, fresh-from-scratch, train-2/3,
  VERIFIED RUNNING) ports the track's own already-bank-proven
  `WALKCURR_PF_IDLE_TERM` combo (`k_park_duty=4.0`,
  `k_walk_idle_charge=2.0`, `k_loadslip_excess=4.5` +gate/ok/max/
  floor, `safety.walk_idle_terminate_s=3.0` grace=3.0 qvel<2deg/s,
  dedicated `walk_idle_terminate_penalty=150`) onto the bare sde
  recipe instead of `walk_gait_gate`. Flagging one risk for whoever
  reads `sde-s1-c3gg`/`sde-s2-c3gg` next: `reward.walk_gait_gate`
  (+ its usual pairing `k_walk_move_current`) was tried against a
  related leg-sacrifice/rigid-tripod-lock exploit on the joystick
  track's harder full-DR `joyfullcurr13` curriculum and was CLOSED
  there — made the fall rate WORSE at every dose/architecture tried
  (RL_LOG 08-25: "a policy can satisfy a rolling swing-completion
  window with rare token swings while spending most ticks in the
  same rigid lock"). Not a reason to abandon c3gg (this easy0905
  context is materially simpler: single fixed low speed, DR-scale
  0.0, no joystick curriculum, and the just-recalibrated bank now
  passes at gait_gate_stride_mm=5) — just read its gait_valid/
  sacrificed-leg numbers with that precedent in mind rather than
  assuming a clean escape. `CURRENT_TRUTHS.md` updated with the
  class-level fact + this caution.

- 09-05 ~12:3x DIG-IN RESOLVED + VERDICTED: `sde-s1-c2`/`sde-s2-c2`
  both **ACQ FAIL (misaligned)** — new exploit class named
  **LEGPARK-SKATE**, now banked in both verdicts: 0/24 falls and the
  det speed bar clears (0.047/0.078 m/s), but 1-3 legs permanently
  sacrificed (s1 duty [0.96,0.04,0.87,0.95,0.00,0.97], leg 4 = ONE
  swing in 20 s), stride 6 mm, slip 3.5-6.5/m, and the smoking gun:
  per-tick `reward_walk` RISES 0.77->1.25 while `walk_speed` falls
  0.22->0.14 (speed decays toward the 0.06 freeprog cap because speed
  above cap pays nothing and NOTHING in the easy0905 minimal diet
  prices a parked leg — `k_step_event`/`k_park_duty`/`k_walk_idle_
  charge`/`k_loadslip_excess` are all 0 in the actual launch vector,
  unlike the recipe-file doses). 08-21 MISALIGNED branch, not
  continue-blind. Repair = the STRUCTURAL `reward.walk_gait_gate`
  (08-13; quadwalk5 proved additive k_park_duty reprices are simply
  paid) — its 3 semantics-bank tests had been RED since the 09-02
  merge (66c4af30): `GG_FLAG_RAD`/midpin tuck were stale
  joint-frame-v2 sim-relative bypass literals (decoded post-v2 to
  impossible knee targets -> over_current at t=4.7 s / tilt_pitch at
  0.86 s), and the honest scripted gait's qualifying strides drifted
  to 7-10 mm vs the 10 mm bar (at 7 mm the factor pins 1.000 all
  episode; mechanism code untouched by the merge — pure calibration).
  Fixed all three (robot_abs literals, test-local stride bar 7 mm,
  midpin splay 0.06->0.08), 4/4 green; collateral-checked — the
  remaining `slipwalk_swing_bonus` x2 + `fullcircle_directions` reds
  PRE-DATE these edits (verified failing at the 09-04 snapshot),
  flagged in OPERATOR_QUESTIONS.md with the untouched shared
  `QW_TUCK_RAD` stale literal. Repair arms launched:
  `sde-s1-c3gg`/`sde-s2-c3gg` — own-checkpoint continuations with
  `walk_gait_gate=1.0` + `gait_gate_stride_mm=5` (parked legs hold
  the MIN at 0 regardless of bar; 5 mm lets current ~6 mm active-leg
  swings qualify so income returns the moment ALL SIX cycle) +
  `k_step_event=1.0` (per-leg completed-swing credit = the recovery
  gradient for the parked legs). Family score at the acquisition
  rung: Gaussian 8/8 valid-gait PASS, sde 0/4 — if c3gg also fails,
  close the sde cell and let Gaussian carry the campaign.

- 09-05 ~12:3x `sde-s3-c1b` DIG-IN FINALIZED -> **ACQ FAIL** (closes
  the 12:2x flag; dedicated dig-in cycle). Per-leg harness data is
  conclusive: all 24 episodes duty [~0.96, 0.00, 0.98, 0.00, ~0.6,
  ~0.94] — legs 1/3 parked airborne (1-4 swings/20s), legs 0/2/5
  dragged anchors, leg 4 micro-paddling ~11 Hz (215-249 swings/20s);
  contact sheets visually confirm the tucked right-side legs +
  near-identical pose creep. W&B: `env/walk_speed` monotone DECLINES
  0.238->0.132 (v_along_cmd 0.169->0.112) while ep_rew climbs to 2198
  and ep_len saturates 1996/2000 — reward buying survival income, so
  the 08-21 continuation clause does NOT apply (task metric moving
  away from the gate). FAILED rather than CONTINUE because the matched
  Gaussian control `base-s3` (same recipe/seed minus gSDE) is a clean
  six-leg ACQ PASS: gSDE is the isolated causal variable (now 4 sde +
  2 sdehalfgrav-remcost frozen-leg seeds vs 8 clean Gaussian seeds).
  **The bare-gSDE sde cell is CLOSED at this recipe** — no further
  seeds/continuations; any gSDE revival (per-leg-utilization pricing,
  bank-proven first) belongs to the still-open `sde-s1-c2`/`sde-s2-c2`
  design pass, which this verdict feeds but does not pre-empt
  (s1-c2/s2-c2/s0-c4 left unverdicted for that cycle). Caveat noted in
  the verdict: this gate read is PRE gsde-reset-noise fix (b4259414),
  so its sto panel is one frozen noise draw; det reads + verdict
  unaffected.
- 09-05 ~12:2x REFILL — heading-canary n=3 batch: with 8-9 GPU pods
  genuinely idle after the sde/remcost cohort finished (their
  relaunch is a concurrent cycle's job, left untouched) and no other
  pre-registered grid item open, launched 4 more heading canaries
  (same bank-proven `EASY_HEADING` recipe/boundaries as `headset-
  base-c1`/`headset-halfgrav-c2`, 2M each, `--activation-fn` blanked
  per the `--init-from` gotcha): `headset-base-s0c1` (from
  `base-s0-c1`, train-3), `headset-base-s1c1` (from `base-s1-c1`,
  train-5), `headset-halfgrav-s1` (from `halfgrav-s1`, train-10),
  `headset-halfgrav-s3` (from `halfgrav-s3`, train-9) — brings both
  families' heading-canary seed count to n=3 once these read, instead
  of resting on n=1 each while the first pair's 40M acquisitions
  (`headset-base-acq1`, `headset-halfgrav-acq1`) run. All 4 confirmed
  genuinely training via `ops.sh procs` (not just ledger RUNNING).
  Left train-2/4/7/8/11 untouched (attributable to the concurrent
  cycle's own 4 in-flight continuations + my 2 DIG-IN'd runs).
- 09-05 ~12:1x DIG-IN TRIGGER on `sde-s0-c4` (40M own-checkpoint
  continuation, found FINISHED+unverdicted, not on any concurrent
  cycle's owned list): W&B (`6e15jpmw`) looks like a clean PASS on
  scalars alone — reward quarters 53.0/306.5/1004.2/1614.1 (strongly
  monotonic, no plateau), full 40M steps completed. BUT hand-pulled
  frame strips from the in-flight gate eval
  (`logs/ckpt_eval/cw_walkscratch_easy0905_sde_s0_c4_gate/`, on
  train-8) show a possible gait-quality red flag the scalars can't
  see: the on-screen `feet` telemetry reads the IDENTICAL 4-on/2-off
  contact pattern at four widely-spaced samples across one det
  episode (t=0.01s all six planted at reset, then t=4.45s/8.89s/
  20.00s all read the same pattern with only ONE leg visibly
  extended/swinging and the other five tucked near-identical to each
  other pose-to-pose) despite `v` reading 0.055-0.117 m/s (near/above
  the 0.06 ref) and full `t=20.00s` survival (no fall). A true
  alternating tripod gait sampled 4-5s apart should rarely land on
  the identical support pattern every single time; this looks more
  like a MOSTLY-FROZEN pose creeping forward (possible paddle/skate
  or micro-oscillation exploit) than six-leg cycling — gate text
  requires "six-leg lift/place on video, no belly drag", which this
  may not clear even though every scalar milestone (`v_along_cmd`
  positive, `ep_len` full, reward rising) reads PASS-shaped. This is
  exactly a gate-vs-video disagreement trigger — **DIG-IN, not
  verdicted**. `sde-s3-c1b` (also found FINISHED+unverdicted, same
  pod-free discovery) shares the identical wandb fingerprint (reward
  quarters 248.5/1008.5/1512.6/1989.4, monotonic, full 40M) — its own
  gate eval was also already running in-flight (train-9) at cycle
  end, not yet visually spot-checked; read it alongside `sde-s0-c4`
  once both `report.json`s land (per-leg `duty_cycle`/`gait_valid`
  will settle this definitively, no more guessing from sparse frame
  samples). If the pattern replicates: the `sde` family's "ACQ
  CONTINUE not FAIL" read may need a THIRD bucket — high reward/full
  survival but NOT a six-leg gait (a new exploit class, name it and
  bank it before funding further sde budget). Both gate evals were
  left running (train-8, train-9), do not re-launch.
- 09-05 ~12:0x `headset-base-c1` formally CANARY PASS (closes the
  11:4x early read above): finite losses, reward_walk quarters
  38.3/81.5/108.7/140.7 monotonic, `env/v_along_cmd_m_s` rises
  0.115->holds 0.131 (heading gradient genuinely live, not marching
  in place), `rollout/ep_len_mean` climbs 107.8->487.9 (near the
  500-tick truncation — almost no falls by the end). Video (frame
  strips pulled mid-eval, `walk_det_1`/`walk_det_4`) shows clean
  six-leg cycling with visible net forward translation on two
  different heading trials. Gate/spot-check eval left running on
  train-1 (12-ep det+sto panel, video-every=1 is slow) — read
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_c1_gate/
  report.json` when it lands; do not re-launch. By verdict time a
  concurrent cycle had ALREADY launched the 40M acquisition follow-up
  `headset-base-acq1` (train-1) and its halfgrav sibling
  `headset-halfgrav-acq1` (train-0) off the strength of the same
  wandb fingerprint on both canaries — consistent with this PASS,
  left running, not touched. `headset-halfgrav-c2` (the halfgrav
  canary) also finished with the identical monotonic-reward
  fingerprint (quarters 25.9/53.5/64.0/98.8) but is being formally
  verdicted by whichever cycle owns its acq1 launch — not duplicated
  here. Tooling note: `ops.sh podeval <run> <sfx>`'s second arg is a
  SUFFIX ON THE OUTPUT DIR, not a "--check" dry-run flag — passing
  `--check` launches a genuine duplicate eval process against a
  `_gate--check` dir instead of a no-op status check. Caught and
  killed this cycle (train-1 pids); there is no dry-run/check mode,
  use `ops.sh procs <pod>` to see if an eval is already alive instead.

Operator order 09-05 ("Make sure the orchestrator dedicates the
available hardware for this — it's not really using the hardware"):
teacher-free easy-sim walking is now the PRIMARY GPU campaign. The
earlier bounded four-lineage/80M pilot-only paragraphs below and in
`EASY_PILOT_20260905.md` are SUPERSEDED for scale (boundaries — no
teacher/BC/AMP/CPG/phase/motion prior, no robot access, easy fixed
physics/no DR/no amps gate — all still bind). Keep every ready GPU
slot supplied with pre-registered easy-campaign work + a stocked
backlog; idle slots next to this unmet priority are the failure state.

- 09-05 ~11:5x DIG-IN TRIGGER FOUND (not verdicted, escalating):
  `sde-s1-c2` + `sde-s2-c2` (both 40M own-checkpoint continuations)
  gate evals landed with a NEW class-level fingerprint, identical on
  both independent seeds: 0/24 falls (real progress — the -c1-scale
  parents fell every det trial) BUT `gait_valid`=False in ALL 24
  episodes on BOTH, every episode with 1-3 permanently
  `sacrificed_legs` (harness definition, `eval_checkpoint.py`:
  duty<0.10 parked-airborne or duty>0.95-with-zero-swings dragged-
  anchor) — s1-c2 sacrifices leg [4] (sto scenarios) or [1,4] (det),
  s2-c2 sacrifices [1] or [3,4] or [1,3,4], `slip_per_m` 3.46-6.49
  (both seeds), well above the 2.9 teacher band and above the clean
  `base`/`halfgrav` families' own 2.6-3.4. Cross-checked
  `wandb_history.csv` for both: `rollout/ep_len_mean` climbs to
  ~1950-2000 (near-full-episode survival) and `rollout/ep_rew_mean`
  climbs monotonically to +2003/+2023 with NO plateau (the
  08-21-ruling "still learning" shape) — but `env/walk_speed` and
  `env/v_along_cmd_m_s` are MONOTONICALLY DECLINING through the same
  back half on BOTH seeds (walk_speed 0.22-0.24 -> 0.13-0.15,
  v_along_cmd 0.16 -> 0.11-0.13) even as reward keeps rising. Reading
  this together: the policy is trading locomotion speed/six-leg gait
  quality for survival duration (permanently favoring a stable subset
  of legs, i.e. a degraded tripod-ish stance, over a full six-leg
  gait) — reward keeps climbing because per-tick survival income
  outweighs the freeprog speed term, not because the walk is
  improving. This is exactly the reward<->eval fork the 08-21 ruling
  asks a cycle to root-cause before a verdict: is more budget likely
  to recover six-leg use (genuine "still learning"), or is this a
  stable local optimum the reward needs to price against (a
  `k_walk_freeprog`-vs-survival-income rebalance, or a direct
  sacrificed-leg/gait_valid price, analogous to the `remcost`
  term_cost fix already validated for the sdehalfgrav cell)? Video
  frame strips (`walk_det_0.png` both runs) are consistent with but
  not conclusive proof of a parked leg at this camera angle/
  resolution — the quantitative harness fields (`gait_valid`,
  `sacrificed_legs`, per-leg `duty_cycle`/`swing_count`) are the real
  evidence. NOT verdicted (left for the dig-in escalation this
  triggers); do not close or continue-fund the `sde` cell off a
  single-seed read until this is root-caused. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_sde_s{1,2}_c2_gate/
  report.json`, `logs/experiments/cw-walkscratch-easy0905-sde-s{1,2}-
  c2/wandb_history.csv`.
- 09-05 ~11:0x: triaged 3 finished own-checkpoint continuations +
  1 found-unverdicted run. `sde-s0-c1` ACQ CONTINUE (already verdicted
  by a concurrent cycle before I reached it — same still-climbing
  ep_len/reward fingerprint as sde-s1/s2, no new note needed).
  `sde-s1-c1`/`sde-s2-c1` FAILED (0-step SystemExit crashes, already
  diagnosed+superseded by sde-s1-c2/sde-s2-c2 per the 10:4x cycle —
  closed out their formal `verdict` field, which had been missing).
  Found+fixed a RECURRENCE of the SystemExit bug: a concurrent cycle's
  `sde-s0-c2` respec'd from `sde-s1` (a gSDE sibling still carrying
  bare `--use-sde`) instead of a `base-*` sibling, blanked only
  `--activation-fn`, and died in <1s the same way — the "non-gSDE
  sibling" rule needs the respec SOURCE itself to never carry
  `--use-sde`, not just the CLI flags on this launch. FAILED it,
  strengthened the `CURRENT_TRUTHS.md` gotcha wording, relaunched as
  `sde-s0-c3` (respec from `base-s0`) — VERIFIED RUNNING on train-8,
  BUT `base-s0` is itself the 2M-CANARY config (not `base-s0-c1`'s 40M
  acquisition config) and I forgot an explicit `--steps` override, so
  it silently trained only 2M steps (FINISHED_BEFORE_CHECKUP, no
  crash, just the wrong budget). A concurrent cycle caught this via
  checkup and relaunched correctly as `sde-s0-c4` (respec from
  `base-s1`'s 40M config + explicit `--steps 40000000` belt-and-
  braces, `--init-from` sde-s0-c3's checkpoint so the extra 2M isn't
  wasted) — confirmed VERIFIED RUNNING on train-8 with `--steps
  40000000` in the live process args. Lesson: always pass an explicit
  `--steps` on any respec whose source might be a canary-scale config,
  never rely on "default: same as source." Also found `sdehalfgrav-s2`
  FINISHED but unverdicted
  (gate eval already synced, nobody had triaged it): 4th sde+halfgrav
  seed, same flat-`ep_len` fingerprint as s0/s1/s3 (rose to 239 by 8M,
  collapsed to a 64-83-tick plateau the whole back half, TERM
  tilt_pitch 24/24, video confirms fast lurch-to-belly) — ACQ FAIL,
  now 4/4 original-recipe seeds share this fingerprint, fully
  confirming the reward-misalignment diagnosis; the cell's fate rides
  entirely on the already-running `remcost-s0`/`remcost-s1` fix pair.
  Separately found `sde-s3-c1` KILLED 30s after launch (auto-placed on
  a CPU-contended pod by another cycle) then REFUSED on retry (W&B
  names are append-only) — relaunched clean as `sde-s3-c1b` on a
  confirmed-idle pod, VERIFIED RUNNING on train-9. At the 80M/2-launch
  normal per-cycle cap after these two relaunches (both corrected
  retries of already-designed continuations, not fresh discretionary
  arms); 5 pods still free for the next cycle (`base-s3`/`halfgrav-s1`
  also just finished but their gate evals aren't synced yet — left for
  whoever's watching next). CURRENT_TRUTHS.md updated.
- 09-05 ~08:5x: all four 2M canaries CANARY PASSed (mechanism-health
  scope): finite losses, real motion (walk_speed 0.11–0.28 m/s), motor
  contract 360 deg/s verified in-log, reward bank-consistent, ep_rew
  decline shown to be an ep_len artifact (100→486 ticks) with per-tick
  reward improving and v_along_cmd rising through zero (+0.008 to
  +0.017 m/s). gSDE note: realized action amplitude >> Gaussian at the
  same annealed log_std (action_delta charge 10x base, some falls).
- Now: full-fleet allocation — 4 own-checkpoint 40M acquisition
  continuations (base-s0/base-s1/sde-s0/halfgrav-s0 -c1; strip
  --activation-fn/--use-sde on plain --init-from, PPO.load preserves
  ELU/gSDE) + 7 fresh 40M seeds completing the 2x2 family grid
  (base-s2/s4, halfgrav-s2/s3, sde-s1/s2, sdehalfgrav-s0/s1) +
  6 backlog spares (halfgrav-s1, sde-s0-c1, base-s3, sde-s3,
  sdehalfgrav-s2/s3; meta 09-05 restock) so the drain refills slots.
- Acquisition milestone (own physics, unchanged): 20 s held-out
  fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det
  episodes, six-leg lift/place on video, no belly drag; report sto.
- Judged by the 08-21 ruling: learning-but-not-yet-walking at 40M =
  continue/realign, not auto-fail; hard 2x2 family comparisons (sde
  vs Gaussian, 1g vs 0.5g) decide which families get deeper budget.
- 09-05 ~10:3x TOOLING GOTCHA found+fixed: `sde-s1-c1`/`sde-s2-c1`
  continuations both died in ~2s (wandb `exit_code 0`/`runtime 0`,
  looks clean unless you check for zero steps) — root cause
  `train_ppo_mjx.py`'s own `SystemExit` guard on `--activation-fn`/
  `--use-sde` + a plain `--init-from` (PPO.load already restores the
  checkpoint's own activation/gSDE; `respec --init-from-source` wrongly
  clones those flags for a gSDE-family source). Fixed by respec'ing
  from the matching-seed non-gSDE sibling with `--activation-fn=`
  (blank) + `--init-from=<sde ckpt>` only, mirroring the already-
  working base-s0-c1/base-s1-c1/halfgrav-s0-c1 pattern. Relaunched as
  `sde-s1-c2` (train-4) + `sde-s2-c2` (train-11), both confirmed past
  the crash point and genuinely training. Recorded in
  `CURRENT_TRUTHS.md` Known Tooling Gotchas.
- 09-05 ~10:2x FIRST 40M PASSES — `base-s2` + `base-s4` (plain
  base family, full 1g, no gSDE) both ACQ PASS: fwd_dist_m median
  3.2-4.8m/20s (0.16-0.24 m/s net, >>0.03 bar) across all 4 eval
  scenarios (walk/sto x startjitter), 0/24 falls each (roll_class
  leaning/recovered only), no sacrificed leg (min per-leg duty_cycle
  0.07-0.48), video-confirmed six-leg cycling with real net
  translation. Caveat: slip/prog 2.6-3.4 (elevated, ~teacher-band
  ceiling) and realized speed 3-5x the 0.06 m/s freeprog reference —
  paddle/skate quality, not gate-blocking (gate silent on slip at this
  rung). First confirmation the easy-sim diet CAN clear its own
  acquisition bar from scratch. `sde-s1`+`sde-s2` both separately read
  ACQ CONTINUE (not FAIL): both fail every det trial on falls (TERM
  tilt_pitch 6/6), `sde-s2`'s `walk/det` shows gait_valid 6/6 but only
  0.08m net (marching-in-place, not progress) — but unlike
  `sdehalfgrav-s0`'s genuine flat plateau, both `rollout/ep_len_mean`
  (111->231 ticks / 102->214 ticks) and `rollout/ep_rew_mean`
  (2.8->38.7 / -2.1->30.1) are still climbing with no plateau at the
  40M cutoff, and `env/v_along_cmd_m_s` holds ~0.15-0.17 m/s (speed
  skill retained while survival duration is still being learned);
  own-checkpoint continuations `sde-s1-c2`/`sde-s2-c2` running (see
  tooling-gotcha entry above for the `-c1` crash+fix). Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_base_s{2,4}_gate/`,
  `cw_walkscratch_easy0905_sde_s{1,2}_gate/`.
- 09-05 ~10:4x HALFGRAV FAMILY CONFIRMS 2/2 — `halfgrav-s3` (10:2x,
  by a concurrent cycle, missing from this file until now) and
  `halfgrav-s2` (this cycle) both ACQ PASS at 0.5g, matching the
  `base` family's 2/2 (s2/s4). `halfgrav-s3`: fwd_dist_m median
  2.18-3.44m/20s (0.11-0.17 m/s net), 0/24 terms (roll_class
  `leaning` only), min per-leg duty_cycle 0.09-0.13, slip/prog
  1.9-3.2. `halfgrav-s2`: fwd_dist_m median 3.3-3.6m/20s (0.19-0.21
  m/s net, the fastest of the whole grid so far), 0/24 terms across
  BOTH walk and the start-jitter (perturbed-init) panel, gait_valid
  6/6 and all six legs' duty_cycle 0.13-0.33 (swing_count 100+ each,
  none stuck) every episode, height_err_end_mm 5.5-21.9 (no belly
  drag), slip_per_m 1.7-2.3 — inside the joystick teacher's <=2.9
  band, tighter than the base family's own 2.6-3.4. Soft note:
  `roll_peak_deg` reaches 18-28 under start-jitter+stochastic (once
  27.9, near the 30 trip bar) though nothing tripped — a stability
  margin worth watching, not a fail. **Net: both `base` and
  `halfgrav` families are now 2/2 clean at 40M from scratch; `sde` is
  ACQ CONTINUE (both seeds); `sdehalfgrav` is 2/2 ACQ FAIL** (below) —
  (09-05 ~11:1x update: `halfgrav-s1`, the backlog-spare seed, ALSO
  ACQ PASSed — same fingerprint, 0/24 terms, gait_valid 6/6, fwd
  2.82-4.24m/20s, slip/m 1.53-2.15 — closing the cell at 3/3. Its
  post-training gate eval was orphaned by a prestage race: the ledger's
  recorded pod (`train-11`) got reassigned to `sde-s2-c2` before the
  eval finished, so it hung silently ~34min. Fixed by `launch_run.py
  update --set pod=<free-pod>` + re-running `ops.sh podeval` on the
  idle pod — kill any stale duplicate `pod_eval.py` process for the
  run first, the log path is shared by run name. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_halfgrav_s1_gate/report.json`,
  `rl_docs/SKILLS.md`.) —
  gravity doesn't look like the deciding lever so far, gSDE looks
  like the harder one. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_halfgrav_s{2,3}_gate/report.json`.
- 09-05 ~11:4x EARLY READS on 4 open cells, gate evals still computing
  (not verdicts — training curves only, recorded so no cycle re-derives
  them; `ops.sh podeval` confirmed each already had a real
  `eval_checkpoint` process alive on its own pod, so none were
  duplicated): (1) `sdehalfgrav-remcost-s0` (the term-cost survival-
  pricing fix cell) — `rollout/ep_len_mean` clearly ESCAPES the
  65-84-tick flat plateau that failed the bare recipe: 116 (2.5M) ->
  202 (10M) -> 324 (25M) -> 712 (35M) -> 1033 (40M, still climbing, no
  re-plateau), `terminations/tilt_pitch` falling in the back half
  (764->741->308), `env/walk_speed` steady ~0.24-0.28 (NOT the ~0
  park-recapture pattern), `env/v_along_cmd_m_s` rising 0.010->0.10.
  `rollout/ep_rew_mean` is deeply negative and getting MORE negative
  (-649->-1025) — expected, not contradictory: longer episodes rack up
  more ticks of the (pre-existing, unchanged) freeprog cross-track
  penalty and the fix's own per-death term_cost is large by design;
  per the gate's own text this reads as escaping the plateau with real
  motion, not park-recapture — leans PASS-shaped but withholds the
  formal verdict for the gate eval's gait_valid/falls numbers.
  `remcost-s1` gate eval also in flight, not yet inspected. (2)
  `sde-s1-c2` (40M own-checkpoint continuation) — `rollout/ep_rew_mean`
  climbs cleanly 188 (Q1) -> 884 -> 1460 -> 1861, ending 2023 at 40M,
  no plateau; `sde-s2-c2` gate eval also in flight, not yet inspected.
  (3) `headset-base-c1` (the heading-generalization canary) FINISHED
  clean: `ep_rew_mean` climbs 38->82->109->141 across the 2M budget,
  monotonic, no plateau — matches the canary's own PASS criterion
  ("reward_walk trending up"); its gate/spot-check eval had not been
  started by anyone (unlike the other 3) so this cycle launched it
  (`ops.sh podeval`), still computing at cycle end. All 5 pods
  (train-1/2/4/7/11) left with their real eval processes running
  in-flight for the next cycle/watcher sync to read — do not
  re-launch, poll `logs/ckpt_eval/*_gate/report.json`.
- 09-05 ~11:2x HEADING BANK BUILT + FIRST CANARIES LAUNCHED (closes
  the "unstarted" item below): `test_walkscratch_easy_pilot.py` now
  has an `EASY_HEADING` section (`_heading_rollout`, 5 new tests,
  22/22 total green) proving the ranking RESEARCH_RULES requires
  (heading-tracking > off-heading/standing > wrong-heading > death)
  under a SMALL DISCRETE heading set (`{0, +45, -45} deg`, resampled
  every 6s in the 20s episode) — following the operator's own staged-
  heading-curriculum ruling (fb_20260822T032514: small set first,
  never full range). **No new reward keys**: `k_walk_freeprog`'s
  existing along/cross decomposition already prices live heading
  tracking correctly once `goal.walk_heading_set`/`walk_cmd_resample_s`
  are turned on — same mechanism the fixed-forward rung already
  trained under. 2M mechanism-health canaries launched warm-started
  from each winning family's champion: `headset-base-c1` (from
  `base-s2`, train-1) + `headset-halfgrav-c1` (from `halfgrav-s2`,
  concurrently launched, train-0) — mirrors the campaign's own
  canary-then-acquisition pattern; 40M acquisition budget is a
  separate follow-up decision after both read healthy. Snapshot
  `2098e983`. Do NOT spend more from-scratch seeds/budget on the
  fixed-forward rung — diminishing returns, both winning cells already
  proven (base 5/5, halfgrav 3/3).
- 09-05 ~09:5x FIRST 40M FAIL — `sdehalfgrav-s0` (sde x halfgrav
  cell) ACQ FAIL: fast 2-leg lurch straight into tilt_pitch, gait_valid
  0/24 across every eval scenario, fwd 0.07-0.26m (bar: 20s sustained).
  `env/walk_speed`/`v_along_cmd` and `rollout/ep_len_mean` (flat
  67-77 ticks) plateau from ~13M on; the late scalar ep_rew creep is a
  per-tick reward-per-burst hack, not survival learning. Root-cause
  hypothesis: freeprog EMA reward pays more per tick than the one-time
  -24 term_penalty costs, so "sprint then fall" out-earns walking —
  reward misaligned with the eval, not a dead lineage (08-21). Do NOT
  generalize to the still-training single-lever siblings until each
  reports its own ep_len/gait_valid fingerprint; if several share this
  plateau, the fix is pricing survival duration directly (raise
  term_penalty and/or a small per-tick alive bonus) before funding
  another sde+halfgrav arm. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_sdehalfgrav_s0_gate/`.
- 09-05 ~10:3x SECOND SEED CONFIRMS — `sdehalfgrav-s1` ACQ FAIL,
  same fingerprint as s0: `ep_len_mean` rose 112->186 (by 4M) then
  COLLAPSED to a 65-84-tick plateau the entire back half (20M:83.6,
  30M:71.9, 36M:65.2, 40M:68.0) while `ep_rew_mean` crept -222->-5.6
  and `v_along_cmd` rose to +0.19 m/s — the same reward-per-burst
  hack, not survival learning. gait_valid 0/24, every episode TERM
  tilt_pitch, 2 legs sacrificed every time ([0,5]), fwd 0.13-0.29m.
  **2/4 sde+halfgrav seeds now share the flat-ep_len fingerprint** —
  per the plan above this is the trigger to design the survival-
  duration pricing fix before funding more of this cell (s2/s3 still
  training, left alone). `reward.alive` already exists as a per-tick
  knob in `env.py` (default 0.0) but was historically zeroed because a
  flat alive bonus on the tracking-kernel reward caused a "freeze and
  collect" stand exploit — dosing it (or raising `term_penalty`) for
  the freeprog walk reward needs its own `test_task_semantics.py`
  bank proof before launch, so this is flagged as a DIG-IN design
  item rather than hand-launched. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_sdehalfgrav_s1_gate/`.
- 09-05 DIG-IN RESOLVED — survival-duration pricing fix designed +
  bank-proven (`test_walkscratch_easy_pilot.py`, 17/17 incl. 4 new):
  the chosen lever is `reward.term_cost_per_remaining_s=100` +
  `term_cost_max=450` (08-15 early-fall horizon cost, default-off,
  MJX-parity via the shim envs, bit-exact for survivors) — death at
  the observed 0.65-0.85 s burst point now costs ~444-464 vs a
  2/tick-capped burst-take ceiling of ~170, decaying to the flat 24
  near truncation so late stumbles while genuinely walking stay
  cheap. `reward.alive` REJECTED: a per-tick bonus re-prices the
  park/statue basin (15+ walkcurr classes died there) from ~0 to
  strongly positive — the documented freeze-and-collect exploit
  class; a raised FLAT penalty rejected as second choice (charges a
  tick-490 stumble like a tick-70 suicide; 08-17 critic-EV lesson).
  Bank evidence: new scripted `sprint_fall` twin (3x lurch 0.7 s ->
  fold -> tilt death) REPRODUCES the exploit under the launched diet
  (+64.7 vs park +0.2) and is priced out under the fix (-385.3 <<
  park), park/gait returns bit-identical with the keys on. Fix arms:
  `cw-walkscratch-easy0905-sdehalfgrav-remcost-s0/s1` (fresh 40M,
  cell recipe + the two keys). If they walk: the cell's failure was
  pricing, extend the fix cell; if they park-pin at ~0 income with
  full ep_len: exploration (gSDE x 0.5g), stop funding the cell.
- 09-05 ~10:5x BASE + HALFGRAV FAMILIES FULLY CLOSED — 4/4 base-family
  arms now ACQ PASS (`base-s2`,`base-s4` earlier + `base-s0-c1`,
  `base-s1-c1` this cycle: 0/24 falls each, fwd 2.1-4.8m/20s, no
  permanently sacrificed leg, video-confirmed six-leg cycling) and
  halfgrav 2/2 continuations ACQ PASS (`halfgrav-s3` + `halfgrav-s0-c1`:
  0/24 falls, fwd 2.5-3.5m/20s; `halfgrav-s0-c1`'s pure-det block alone
  shows a repeatable leg-1 underuse — duty 0.09 vs 0.3+ siblings — that
  vanishes under sto/jitter, flagged as a 0.5g gait-quality item, not
  gate-blocking). **No further budget on either cell** — both answer
  their own acquisition milestone; remaining budget goes to sde/
  sdehalfgrav. sde family: 4/4 seeds (s0-c1,s1,s2,s3) now read ACQ
  CONTINUE, not FAIL — every one falls every det trial but shares a
  "dip-then-recover" `ep_len_mean` + monotonically-rising (ending
  POSITIVE) `ep_rew_mean` fingerprint, distinct from sdehalfgrav's
  flat-plateau FAIL signature; all 4 now have (or are getting) their
  own 40M own-checkpoint continuation (`sde-s0-c3`, `sde-s1-c2`,
  `sde-s2-c2`, `sde-s3-c1b` — several `-c1` attempts on this lineage
  died from the same `--use-sde`+`--init-from` gotcha via a bad respec
  SOURCE, not just a leftover flag; always respec sde continuations
  from a non-gSDE sibling like `base-sN`). sdehalfgrav: 3rd from-scratch
  seed (`sdehalfgrav-s3`) independently confirms the flat-`ep_len`-
  plateau FAIL fingerprint (62-74 ticks steady 23M-40M) — reinforces
  funding the remcost fix cell above rather than more bare sdehalfgrav
  seeds. Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_{base_s0_c1,
  base_s1_c1,halfgrav_s0_c1,sde_s0_c1,sde_s3,sdehalfgrav_s3}_gate/`.
- 09-05 ~12:1x REMCOST FIX CONFIRMED, NEW PATHOLOGY FOUND —
  `sdehalfgrav-remcost-s1` gate eval: ACQ CONTINUE, not PASS/FAIL. The
  `term_cost_per_remaining_s=100`/`term_cost_max=450` survival-duration
  fix worked on its target failure mode — 0/12 det falls (walk/det +
  walk_startjitter/det), fwd med 2.17-2.60m/20s (0.11-0.13 m/s, clears
  the >=0.03 m/s bar), `ep_len_mean` climbed 110->1088 ticks with no
  plateau (escapes the pre-fix 65-84-tick fingerprint cleanly). BUT a
  NEW pathology blocks six-leg-validity: legs [1,4] show
  `duty_cycle=0.0`/`swing_count~2` in EVERY one of the 12 det episodes
  — a fully idle prop-leg pair, not minor underuse — so `gait_valid`
  False 12/12 (walking on 4 legs, 2 held rigid). Also fragile: BOTH
  stochastic scenarios fall 6/6 via tilt_roll/tilt_pitch with
  near-zero forward (0.14-0.65m) — no margin against action noise.
  Sibling `sdehalfgrav-remcost-s0` (concurrent cycle, unverdicted at
  time of writing) shows the IDENTICAL fingerprint (legs [1,4]
  sacrificed det, [0,2] sacrificed sto, 0/12 gait_valid, 6/6 sto
  falls, even better fwd 3.3-4.0m) — this is a reproducible RECIPE
  fingerprint, not seed noise, and recurs even in the ORIGINAL
  pre-fix FAIL seeds (sdehalfgrav-s0/s1 sacrificed legs [0,5]) — the
  2-idle-leg pattern looks structural to this action-box/0.5g
  combination, independent of the survival-cost fix. Per 08-21: not
  park-recapture, not flat — fix confirmed, but the cell needs a
  per-leg-utilization lever (not just more seeds at this recipe)
  before it can clear six-leg-validity. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_sdehalfgrav_remcost_s{0,1}_gate/`.
- 09-05 ~12:0x HEADING RUNG: BOTH 2M CANARIES PASS, 40M ACQUISITION
  LAUNCHED — `headset-base-c1` (1g) and `headset-halfgrav-c2` (0.5g)
  both finished healthy: `ep_rew_mean` climbed monotonically every
  quarter (38->82->109->141 and 26->54->64->99), `ep_len_mean` rose
  108->488 (near the 2000-tick full-episode length, no early
  collapse) for both, `env/v_along_cmd_m_s` held positive +0.11-0.15
  m/s throughout (real heading-command tracking, not marching in
  place) — CANARY PASS, mechanism-health scope, on W&B evidence (gate
  eval with video still running at verdict time, contention from
  concurrent standwalk mixed-session evals sharing the fleet). Per the
  campaign's own canary->acquisition follow-up, launched both 40M
  continuations: `headset-base-acq1` (train-1) + `headset-halfgrav-acq1`
  (train-0), both `--init-from-source` warm-started from their own 2M
  checkpoint, VERIFIED RUNNING. Also found 2 more own-checkpoint
  continuations finished-but-unverdicted this cycle with striking
  results: `sde-s0-c4` (ep_rew_mean 1780.9, quarters 53->307->1004->1614)
  and `sde-s3-c1b` (ep_rew_mean 2197.98, quarters 249->1009->1513->1989,
  `ep_len_mean` maxed at 2000/2000 — full-episode survival) — both
  climbing hard with no plateau, gate evals in flight, left for the
  next triage pass (contention-slowed, not stuck).

- 09-05 ~12:1x CROSS-FAMILY SYNTHESIS (connects two independent findings
  this hour) — the 2-leg-sacrifice/`gait_valid=False`-despite-rising-
  reward pathology is NOT specific to `sdehalfgrav`: a concurrent
  cycle's `sde-s1-c2`/`sde-s2-c2` (plain `sde`, full 1g, no
  survival-cost fix) independently show the SAME shape — 0/24 falls
  but `gait_valid` False every episode, 1-3 sacrificed legs,
  elevated slip (3.46-6.49, above the whole grid's 2.6-3.4 band),
  `ep_rew_mean` climbing to +2000s while `env/walk_speed`/
  `v_along_cmd` DECLINE through the back half. My `sdehalfgrav-
  remcost-s0/s1` fix arms show the mirror pattern (2 legs at
  duty_cycle=0.0, `gait_valid` False 12/12, reward climbing to
  -1230..+huge depending on sign convention) despite the pricing fix
  working on its OWN target (episode length). Common thread: every
  affected arm uses **gSDE** (`sde`, `sdehalfgrav`); the plain `base`/
  `halfgrav` families (Gaussian, no gSDE) are the ONLY cells that
  closed clean with real six-leg `gait_valid=True` gaits. Working
  hypothesis for the next design pass: gSDE's per-episode-correlated
  action noise may make a fixed 4-leg stable stance cheaper to hold
  through stochastic bursts than a genuine 6-leg swing cycle, so PPO
  converges on "ride out the episode on 4 planted legs" once reward
  correlates with survival duration (true both for the plain
  freeprog reward AND the remcost fix). Do not fund more bare
  gSDE-family seeds at this recipe; the next lever is either (a) a
  per-leg-utilization/swing-count reward term, bank-proven before
  launch, or (b) an A/B of gSDE vs Gaussian holding everything else
  fixed to confirm gSDE is the causal variable (not just correlated
  with these particular seeds). Flagged for a dedicated design pass,
  not a same-recipe relaunch.

- 09-05 ~12:2x `headset-halfgrav-c2` gate eval SYNCED, corroborating the
  earlier CANARY PASS (was pending at verdict time): 24/24 walk +
  walk_startjitter det+sto episodes gait_valid=True, 0 sacrificed legs,
  0 terminations, fwd_dist_m med 3.32-3.58m/20s (0.17-0.18 m/s),
  slip_per_m med 2.22-2.41 — inside/near the teacher's <=2.9 band,
  the TIGHTEST of the whole heading rung so far. Already
  acquisition-grade at 2M steps, a strong leading signal for the
  in-flight `headset-halfgrav-acq1` 40M follow-up. Re-verdicted
  PASS with FORCE=1 to attach the corroborating numbers.
- 09-05 ~12:2x FOURTH gSDE-FAMILY INSTANCE + A REAL TOOLING BUG FOUND —
  `sde-s3-c1b` (40M own-checkpoint continuation, huge reward climb
  2198 ep_rew_mean, full 2000-tick ep_len, no plateau) gate eval:
  0/24 gait_valid, EVERY episode sacrifices legs [1,3] (one sto
  episode: just [1]), slip_per_m 3.79-5.38 (worse than the sde-s1-c2/
  sde-s2-c2 pair's 3.46-6.49 range but the SAME class), fwd only
  0.9-1.6m/20s (~0.05-0.08 m/s, barely clears the 0.03 m/s freeprog
  bar), 0 terminations. This is a 4th independent seed sharing the
  identical gSDE frozen-leg-subset fingerprint already flagged for
  `sde-s1-c2`/`sde-s2-c2` (11:5x entry) and the `sdehalfgrav-remcost`
  pair (12:1x entry) — reinforcing the cross-family synthesis
  (gSDE, not halfgrav/remcost specifically, is the common thread).
  **NOT independently re-escalated** (the design question — a
  per-leg-utilization pricing lever, or a clean gSDE-vs-Gaussian A/B —
  is already being root-caused by a concurrent deep-model dig-in
  cycle on the sde-s1-c2/sde-s2-c2 pair); flagged DIG-IN anyway per
  the standing-prompt rule that every triggering run gets its own
  flag, left UNVERDICTED so the watcher can fold it into that same
  design pass rather than pre-empting it with an inconsistent verdict.
  **Bonus finding while investigating**: `walk/det` AND `walk/sto`
  each read numerically IDENTICAL across all 6 episodes (same prog/
  slip/fwd to 2 decimals) — expected for `det` (fixed-forward walk has
  no per-episode init randomization, matches every other clean arm's
  own det pattern, e.g. `base-s2`) but NOT expected for `sto`, which
  should sample fresh action noise every episode. Root-caused: SB3's
  `model.predict()` never calls `policy.reset_noise()` — that only
  happens inside `OnPolicyAlgorithm.collect_rollouts` during TRAINING
  — so a loaded gSDE checkpoint's exploration matrix is frozen for
  the whole eval process; under any mode without its own init
  randomization (confirmed: `walk_startjitter_sto_*`, which DOES
  randomize the start pose, varied normally / had different MD5s),
  every "stochastic" episode replays the identical noise draw
  end-to-end (all six `walk_sto_*.mp4` shared one MD5, confirmed by
  hand). This silently made every gSDE "sto" panel campaign-wide
  (`sde`/`sdehalfgrav`/`sdehalfgrav-remcost`, every gate read cited
  above) an n=1 noise-draw report dressed up as n=6 — read their
  "6/6 sto fail" claims as "one noise draw failed," not "robust
  failure across draws" (their det-pass `gait_valid`/sacrificed-leg
  reads are UNAFFECTED — deterministic mode never touches gSDE
  noise). Fixed same cycle: `_maybe_reset_gsde_noise()` in
  `eval_checkpoint.py`, called at the top of every `run_episode`,
  resamples once per episode for any `use_sde=True` model (direct or
  through an inner-`.model` wrapper like `Rot60Policy`); bit-exact
  no-op for the non-gSDE default. 4 new tests
  (`test_eval_checkpoint_gsde_reset_noise.py`, all green), snapshotted
  + pushed (`b4259414`). `sde-s3-c1b`'s report above is PRE-FIX (the
  remote eval had already started before the fix landed) — any FUTURE
  gSDE gate re-read will get genuine per-episode noise variation.
  CURRENT_TRUTHS.md gotcha entry added.

## Easy-sim pilot recipe (superseded for scale by the campaign above)

Recipe/proof/gates for the original 4-arm bounded pilot (base-s0,
base-s1, sde-s0, halfgrav-s0) that the full-fleet wave grew from,
including the `test_walkscratch_easy_pilot.py` 13/13 preflight and
full boundaries (no teacher/BC/phase/motion prior, no hardware claims,
defaults untouched): `rl_docs/tracks/walkcurr/EASY_PILOT_20260905.md`.
halfgrav arms are read at their own gravity first; full-gravity is a
later diagnostic, never an automatic promotion.

## RETIRED for real-physics prior-free discovery (2026-08-31 ~06:4x — honest DONE-negative scope finding)

Both pre-committed final-wave seeds now read park-stand/no-gait at
150M: `cw-walkcurr-litrep-box-s0` (FAIL, 08-31 ~02:5x) and
`cw-walkcurr-litrep-box-s1` (FAIL, this cycle) — identical
fingerprint both seeds: det walk 0/6 gait_valid, progress_ratio med
0.01-0.02 (bar 0.35), 2-3 sacrificed legs, `env/walk_speed` plateaued
0.011-0.014 m/s the entire 150M budget (never clears the 0.02
static-floor litmus), `env/reward_walk` flat ~0.06-0.11 after the
first noisy step, frame strips on both showing a textbook static
stand (zero net travel, identical pose frame-to-frame). Per the
operator's own 08-30 pre-commitment ("if this wave also lands
park-stand/no-gait, RETIRE walkcurr as an honest DONE-negative scope
finding"): **this track is RETIRED.**

Plain English: 15+ independently designed non-BC mechanism/
architecture/reset-diversity/action-space classes across the whole
campaign (14 pre-08-30 classes tallied in
`OPERATOR_QUESTIONS.md` q_20260824T0233Z + this final
literature-informed action-box wave, 2 seeds, 100-150M each) all
converge on the same static-stand/quiver-to-over_current local
optimum under a from-scratch/prior-free PPO diet on this sim/reward
stack. The scope finding is that prior-free discovery alone does not
escape the initial-standing basin at this budget scale on this
hardware model — not that hexapod walking itself is unreachable: the
`joystick`/`standwalk` tracks' BC-anchored/teacher-distilled lineages
already walk (`stotight45-seed13`, `cw-walkteach-*`). No further
walkcurr rung-1/litrep-style/population-sweep arms will be launched
by the agent fleet. `STATUS.md` and `rl_move/orchestrator/tracks.json`
updated the same cycle.

Evidence: `logs/ckpt_eval/cw_walkcurr_litrep_box_s0_gate/`,
`cw_walkcurr_litrep_box_s1_gate/report.json`; RL_LOG 08-31 lines;
full campaign journal (every rung, every mechanism/architecture class,
every population-sweep arm, 08-23 -> 08-31) preserved verbatim in
`archive/walkcurr_STATUS_journal_2026-08-30_trim.md` +
`archive/walkcurr_STATUS_journal_2026-08-31_pre_retire_trim.md`.

## Goal (DONE gate — UNMET, track retired before reaching it)

A prior-free policy passes a held-out C-env contextual walking panel
(fixed forward + heading set + irregular direction changes) with zero
falls, directions actually followed, low slip/m, all-six-leg gait
validity, on video. Speed obedience is secondary throughout.

## Binding track rules (operator, 08-23 — historical record)

- **Walk-only diet**: every rung trained with `goal.walk_pure=1`.
- **Bank before launch**: WALKCURR_PF/WALKCURR_SV ranking banks in
  `test_task_semantics.py` proved before any reward-mechanism launch.
- **Rule (a)**: no gait clock, no BC teacher, no motion prior,
  including at init (BC-kickstart ruled OUT OF BOUNDS 08-29,
  q_20260824T0233Z).
- **Triage rule**: reward trend AND walk-eval trend logged together;
  reward rising while walk eval flat/down = MISALIGNED, stop same-
  recipe sweeps and audit first.

## Key facts (kept for any future reopening)

- The RAW kawawa2022 reward stack was bank-REFUTED 08-23: park (+387)
  out-earned clean walking (+325) under the walk goal alone.
- Harsh SLIPWALK doses (idle 20 / loadslip 6 / gait_gate) refuted for
  from-scratch discovery (8 statue arms).
- Every non-BC mechanism/architecture/reset-diversity lever tried
  (14 classes pre-08-30) plus the final operator-ruled literature
  action-box wave (tight joint box + plain velocity reward + clamped
  over-current, 2 seeds x 150M) converge on the same static-stand
  basin — see archived journal for the full per-arm evidence trail.

## WAITING-ON

- None. Real-physics line stays closed (08-31); the ONLY live work is
  the bounded 09-05 easy-sim pilot cohort above (operator focus note
  09-05 = the explicit operator reopening this file required).
