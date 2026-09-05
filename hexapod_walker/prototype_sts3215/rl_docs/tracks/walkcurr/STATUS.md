# walkcurr — prior-free walking curriculum (Kawawa-2022 lineage)

## PRIMARY GPU CAMPAIGN 2026-09-05 — operator full-fleet order (supersedes the bounded pilot ceiling)

Operator order 09-05 ("Make sure the orchestrator dedicates the
available hardware for this — it's not really using the hardware"):
teacher-free easy-sim walking is now the PRIMARY GPU campaign. The
earlier bounded four-lineage/80M pilot-only paragraphs below and in
`EASY_PILOT_20260905.md` are SUPERSEDED for scale (boundaries — no
teacher/BC/AMP/CPG/phase/motion prior, no robot access, easy fixed
physics/no DR/no amps gate — all still bind). Keep every ready GPU
slot supplied with pre-registered easy-campaign work + a stocked
backlog; idle slots next to this unmet priority are the failure state.

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
