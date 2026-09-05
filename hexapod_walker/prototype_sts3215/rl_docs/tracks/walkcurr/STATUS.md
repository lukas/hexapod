# walkcurr — prior-free walking curriculum (Kawawa-2022 lineage)

## PRIMARY GPU CAMPAIGN 2026-09-05 — operator full-fleet order (supersedes the bounded pilot ceiling)

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
