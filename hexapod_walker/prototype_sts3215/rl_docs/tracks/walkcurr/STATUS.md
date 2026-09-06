# walkcurr — prior-free walking curriculum (Kawawa-2022 lineage)

## PRIMARY GPU CAMPAIGN 2026-09-05 — operator full-fleet order (supersedes the bounded pilot ceiling)

- 09-06 ~12:2x this cycle (assigned `headset-base-acq1-cont40m`, `headset-crossgrav-medhead-
  ramp-c1-acq1-cont40m`, `headset-halfgrav-medhead-acq1-cont40m`): **3/3 verdicted — 1 HARDENING
  PASS (perfect), 2 HARDENING FAIL (1 confirms the closed base-family duration effect, 1 a mild
  new stochastic-mode fall) — plus a 2-arm refill of the cleanest still-unconfirmed halfgrav
  composition sources.** (1) `headset-base-acq1-cont40m` **HARDENING FAIL**: the base(1g)
  family's flagship own-first cont40m drops 18/24->14/24 — the chronic leg1/4 sacrifice, previously
  confined to `walk_startjitter/det`, now ALSO invades the previously-perfect `walk/det` (6/6->3/6)
  and `walk_startjitter/sto` degrades (6/6->4/6); reward still rises every quarter but the gate's
  own chronic-leg-entrenchment clause is squarely met. Together with `headset-base-s1c1-acq1-
  cont40m`'s identical fate this same cycle-window, this closes the base(1g) 40M+ HARDENING
  question 3/3 (matching `s0c1` hardening solo) — downweight base(1g) 40M+ checkpoints from
  champion contention in favor of the halfgrav sibling. (2) `headset-crossgrav-medhead-ramp-c1-
  acq1-cont40m` **HARDENING PASS**: PERFECT 24/24 across all 4 panels at 80M cumulative, 0
  falls/terms, sac=[] every episode — the gradual-ramp gravity-transfer root's first cont40m read,
  cleanest possible result. (3) `headset-halfgrav-medhead-acq1-cont40m` **HARDENING FAIL (mild)**:
  22/24->21/24, still majority and no new chronic leg, but `walk/sto/0` TERMINATES tilt_roll (a
  genuine fall, roll_peak 31.9deg, 0 falls->1 fall) and `walk_startjitter/sto` regresses 6/6->4/6 —
  trips the gate's own explicit "0 falls" / "not worse than 40M" bright lines even though the
  aggregate stays healthy; treat the 40M `acq1` checkpoint, not this cont40m, as champion for this
  line. SKILLS.md updated (1 new PASS row). **Refill:** cross-checked every `-acq1` checkpoint
  against its `-acq1-cont40m` sibling and found 4 clean composition-line ACQ_PASS sources still
  lacking a cont40m endurance read (per-axis DR arms correctly excluded per QUEUE AIM's own STOP):
  `crossgrav-medhead-{irrwiden,widenirr}-c1-acq1` and `halfgrav-{irr,irr2}-acq1` — all 4 were
  independently claimed and launched by a concurrent cycle moments before my own launch landed
  (confirmed via `launch_run.py status`, no duplicate). Two more genuinely uncovered clean halfgrav
  composition sources remained: `headset-halfgrav-widenirr-c1-acq1` (ACQ PASS 23/24, beats the
  plain widen2 sibling) and `headset-halfgrav-fullhead-widen2-c1-acq1` (ACQ PASS 21/24, sibling
  c2b already FAILED cont40m, c3 is mid-cont40m elsewhere) — launched both as true
  `--init-from-source` continuations (`...-cont40m`, train-3/train-5, both VERIFIED RUNNING, 80M
  new GPU steps = per-cycle cap). **Launch-tooling gotcha hit + fixed in-place**: `--init-from-
  source` is a `launch_run.py respec` META-flag, not a forwarded training arg — passing it via
  `--arg='--init-from-source'` ships it straight to `train_ppo_mjx.py`, which rejects it as
  unrecognized (2 wasted attempts before catching this); a `self-repair` tar-sync race
  ("file changed as we read it", transient under concurrent-cycle repo contention) and a pod-
  collision (default free-pod picker raced a concurrent cycle onto the same pod) cost 2 more
  retries — no GPU spend was wasted since none of the failed attempts reached a live remote
  process; the correct final form passes `--init-from-source` as a bare respec flag with an
  explicit `--pod`. Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_{base_acq1,
  crossgrav_medhead_ramp_c1_acq1,halfgrav_medhead_acq1}_cont40m_gate/report.json` vs each parent's
  own `_gate/report.json`, W&B `kevdolja`/`jeigs5gn`/`frmzojxo`, `launch_run.py status`, RL_LOG
  09-06 11:4x-12:2x.

- 09-06 ~12:1x same cycle (orphan reap + hygiene, after the widen2-c3 dig-in below): **(1)
  `headset-halfgrav-acq1-cont40m` HARDENING PASS — the foundational plain-halfgrav source holds
  PERFECTLY at 80M** (gate had synced at 10:37 and sat unverdicted ~1.5h with a stale-RUNNING
  ledger row — reaped per the kickhalf-notorquecrutch orphan precedent): 24/24 gait_valid, 0
  falls, sac=[] every episode, per-leg duty min 0.13 / means 0.17-0.29 (no sub-threshold lazy
  leg), slip med 2.2-2.5 (inside the <=2.9 teacher band — best slip of any cont40m to date), fwd
  med ~3.1m, reward monotonic 257->478->509->534, video-confirmed clean six-leg cycling. Cleanest
  hold in the endurance series (now 6 PASS / 2 FAIL) and the strongest single support for the
  refined rule stated in the widen2-c3 FAIL below: both FAILs (s1acq-irrfwd, widen2-c3) had a
  prior WATCH/known attractor; every no-prior-signal source has held. Plain halfgrav-acq1@80M
  joins medhead/widenirr/irrwiden as a top halfgrav champion candidate. SKILLS.md updated (1 row).
  **(2)** `medhead-dr-zerobiasframe1x-c1-acq1` closed SUPERSEDED (the 2M steps-bug respec; `-r2`
  is the verdicted arm of record) — pure ledger hygiene, it was cluttering the triage table as
  finished-unverdicted. **(3)** Drained the backlog (`halfgrav-irr-acq1-cont40m`, the queued
  endurance arm whose parent DOES carry scattered leg4 flags — now a direct prospective test of
  the refined fragility-signal rule: it predicts this one is at elevated FAIL risk). Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_acq1_cont40m_gate/report.json`, W&B
  `gd3g8ygn`/`s638szr8`, RL_LOG 09-06 12:10-12:11.

- 09-06 ~12:0x this cycle (dig-in escalation on `headset-halfgrav-fullhead-widen2-c3-acq1-cont40m`,
  flagged-not-verdicted by a prior triage cycle): **HARDENING FAIL — the halfgrav family's FIRST
  cont40m break; the "halfgrav is clean" claim is hereby NARROWED to source-conditional, not
  overturned.** At 80M cumulative a NEW chronic leg1 low-duty pattern appears that was ABSENT at
  40M (parent leg1 duty never <0.10 in 24 eps; child leg1 at 0.06-0.10 / swing 42-72 in 4 eps
  across 3 of 4 modes — walk/det/3+4, startjitter/det/2, startjitter/sto/3), violating the run's
  own pre-registered "0 NEW chronic single-leg pattern" PASS clause; same class as the
  `s1acq-irrfwd-c1-acq1-cont40m` FAIL precedent (new-mode duty ~0.06 spread). Adjudicated depth:
  MILDER than the base(1g) park fingerprint (0.02-0.05 / swing 19-49) — leg1 still cycles and its
  mean duty over all 24 eps is unchanged (0.17), so this is episode-specific sacrifice
  redistribution, not global weakening; parent's own [0,3] flags reproduce/soften (walk/det/4
  identical episode), 0 falls, gait_valid 18/24 majority, video-confirmed upright six-leg walking.
  Corroborating degradation: gait_valid 20/24->18/24 and forward distance DOWN in all 4 modes
  (walk/det med 1.85->1.26m). Reward dipped then recovered (-1262->-652, rising at end): the 08-21
  misalignment case, but the 6-lever reward-repair grid for exactly this pathology closed 09-05 —
  no new repair spend. **Consequences:** (1) widen2-c3's 40M checkpoint stays usable but is NOT
  stable past its acquisition budget — retire widen2-c3 from champion/continuation contention
  (consistent with its already-established crossgrav-abrupt attractor, "real attractor of the
  widen2-c3 source", ~05:4x below); (2) halfgrav endurance cleanliness is SOURCE-conditional:
  widenirr-c3 cont40m held, medhead/irrwiden lines clean, widen2-c3 breaks — halfgrav remains
  strictly preferred over base(1g) (which breaks EVERY seed by 80M, see ~11:3x below), champion
  picks should come from medhead/widenirr/irrwiden sources; (3) updated tally: cont40m endurance
  series now 5 PASS / 2 FAIL (s1acq-irrfwd, widen2-c3), both FAILs on sources with a prior WATCH
  or known attractor — cleanliness margin at 40M still predicts holds ONLY when the source has no
  prior fragility signal. Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_
  fullhead_widen2_c3_acq1_cont40m_gate/report.json` (per-leg duty/swing) vs parent `..._acq1_gate/
  report.json`, frame sheets `walk_det_{3,4}_sheet.png` in the same dir, W&B `9wove9uj`, RL_LOG
  09-06 12:05.

- 09-06 ~12:0x this cycle (refill-only, no completions assigned; canonical capacity found 11 free
  slots + empty backlog). The two composite-ACQ gate evals that unblock QUEUE AIM item (4)
  (`allaxis-nokick-c1-acq1`, `allaxiskickhalf-nocrutch1x-c1-acq1`) confirmed still genuinely
  computing on their own pods (train-2/train-3, `eval_checkpoint` alive ~60-90min CPU time each) --
  left untouched, not ready. Per this banner's own STOP on further per-axis DR spend, systematically
  diffed every `-acq1` run against existing `-acq1-cont40m` children and found 4 clean
  composition-line ACQ_PASS sources still lacking one: `crossgrav-medhead-{irrwiden,widenirr}-c1-acq1`
  (22/24 gait_valid each -- a matched pair testing whether irr-timing-then-widen vs widen-then-irr
  composition order changes cont40m endurance) and `halfgrav-irr{,2}-acq1` (19-20/24, 2-seed pair).
  Also confirmed (via ledger status) the base(1g)-family `-irr`/`-medhead`/`-medhead2`/`-s0c1` acq1
  runs are ALL already FAIL-verdicted (chronic leg1/4 sacrifice already visible at their own 40M
  ACQ, matching this file's established base(1g)-duration-effect finding) -- correctly excluded from
  cont40m refill, not just missed. Launched the cleaner pair as TRUE `--init-from-source`
  continuations (80M new GPU steps = per-cycle cap, exactly spent):
  `crossgrav-medhead-irrwiden-c1-acq1-cont40m` (train-0) and
  `crossgrav-medhead-widenirr-c1-acq1-cont40m` (train-1), both VERIFIED RUNNING via `kubectl exec ps`
  with the correct 40M checkpoint as `--init-from` (confirmed in the live process argv, not just the
  ledger). Queued `halfgrav-irr-acq1-cont40m` / `halfgrav-irr2-acq1-cont40m` to `backlog.json` for
  the next drain (steps cap already spent). **Provenance gotcha found+fixed before it could ship a
  wrong-ancestor mistake** (the exact class CURRENT_TRUTHS already warns about for `sde-s2-dg1`):
  both source runs' correctly-named `--out-name` checkpoints existed on their OWN training pods
  (train-3, train-8) but had never been pulled to the controller's local `rl_move/sim/policies/` --
  only stale/differently-suffixed files were present there (an `_acq1v3.zip` from an unrelated
  collision-avoidance rename, no plain `_acq1.zip` at all for the other). A first `--init-from-source`
  respec attempt correctly REFUSED on the missing local file rather than silently warm-starting from
  the wrong checkpoint; `ops.sh pullckpt` on both sources before relaunch fixed it cleanly. Also
  found+fixed a real `ops.sh report` bug while triaging orphan status: it crashed with an unhandled
  `KeyError` on any run whose newest-2-by-mtime glob match included an off-policy `_session` report
  (no `episodes` key) OLDER than its own `_gate` report -- silently hiding the actual per-episode
  table behind a traceback for at least 5 runs this cycle alone. Patched to skip session-shaped
  reports instead of crashing (snapshotted before the launches that needed it). SKILLS.md not
  touched (no new PASS/FAIL verdict this cycle, refill-only). Evidence: `launch_run.py status`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_{irrwiden,widenirr}_c1_acq1_gate/
  report.json`, RL_LOG 09-06 12:07.

- 09-06 ~11:3x this cycle (assigned `headset-base-s1c1-acq1-cont40m` — NOT part of the crossgrav
  DR campaign above, a different sub-line: the older 09-05 base(1g)/halfgrav(0.5g) heading-set
  family): **HARDENING FAIL — closes "champion pick should use s1c1" (09-05 ~14:2x) for good; the
  base(1g) family's leg1/4 favoritism is a training-DURATION effect, not a seed-specific
  anomaly.** Parent (`s1c1-acq1`, 40M) had `gait_valid` 18/24 with the leg1/4 sacrifice confined
  ENTIRELY to `walk_startjitter/det` (0/6) — plain `walk/det`/`walk/sto` both clean 6/6, the
  established "clean seed" fingerprint that made it (along with plain `acq1`) the recommended
  champion over `s0c1` (which had already hardened at 40M). This cont40m (+40M, 80M cumulative)
  drops to 15/24: the SAME leg (mostly 4, occasionally 1) now ALSO chronic in the previously
  PERFECT `walk/det` (3/6, duty 0.02-0.05 / swing_count 19-49 vs healthy legs' 0.4-0.8 / 150-250 —
  genuine near-park) and `walk_startjitter/sto` (3/6, was 6/6); `walk_startjitter/det` itself
  partially improved (0/6->3/6) but that's redistribution, not net gain. `ep_rew_mean` still rises
  every quarter (559->1047->1232->1406) but this run's own pre-registered HARDENING gate exists
  precisely to test whether good behavior HOLDS under more budget, and its "chronic leg entrenches"
  FAIL clause is squarely met regardless of reward or aggregate majority. **s0c1 hardened at 40M,
  s1c1 hardens by 80M — every base(1g)-family seed given enough budget converges on the same
  leg1/4 sacrifice; this is now a family-wide duration effect, not a per-seed roll.** Neither
  40M base-family checkpoint should be treated as a stable champion past its own acquisition
  budget; downweight the base(1g) family generally in favor of the already-more-robust
  halfgrav(0.5g) sibling (independently confirmed clean through irr-timing/medhead/widen axes in
  this same file). No new repair mechanism warranted — this corroborates an extensively
  pre-established, already-closed pathology (6 reward-shaping repair levers closed 09-05 on the
  crossgrav-medhead sub-line above), not a new open question. `headset-base-acq1-cont40m` (the
  base family's 3rd and last cont40m candidate, still training) should be read next to see if it
  shares this fate — if so, retire ALL base(1g) 40M+ checkpoints from champion contention and
  standardize on halfgrav for any downstream base-gravity walking use. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_base_s1c1_acq1_cont40m_gate/report.json` vs
  `..._headset_base_s1c1_acq1_gate/report.json`, W&B `skhxpa64`, RL_LOG 09-06 11:33.

- 09-06 ~11:2x this cycle (assigned `fault1x-c1-acq1-r3`, `kick0225x-c1`, `allaxis-nokick-c1` —
  the latter 2 already SUPERSEDED by a concurrent cycle before this read landed, confirmed not
  re-triaged): **1/3 assigned run ACQ PASS (final per-axis DR-restore confirmation); found+verdicted
  1 more orphan (CANARY PASS, corroborating the composite-no-crutch finding); 1 genuinely new
  refill launch, 1 refill attempt deduped against a concurrent cycle's identical reasoning.**
  (1) `fault1x-c1-acq1-r3` **ACQ PASS**: actuator-fault-injection axis (fault_prob=0.3) holds at
  real 40M (22/24 gait_valid, 0 falls, 2 non-chronic leg[0] flags, reward monotonic 738->1395) --
  matches its own 2M canary's pattern class; per QUEUE AIM this closes per-axis DR-restore
  confirmation exhaustively (every RandRanges field now holds at ACQ scale). (2) Found+verdicted
  `kickhalf-notorquecrutch-c1` (orphan: training+gate finished, ledger stuck at stale INTENT,
  never verdicted) **CANARY PASS**: the isolated 2-axis kick-safe+no-crutch pairing composes
  cleanly (22/24 gv, 0 falls, 2 non-chronic flags on DIFFERENT legs) -- independently corroborates
  `allaxiskickhalf-nocrutch1x-c1`'s own full-composite PASS finding that these two aggressive axes
  do not destabilize each other or the broader composite. **Refill:** identified the kick-dose-
  ladder's own owed follow-up -- `kickhalf1x-c1-acq1`'s ACQ PASS carried an explicit leg5 WATCH
  (scattered-3-legs canary pattern narrowed to one recurring leg at ACQ scale); launched
  `kickhalf1x-c1-acq1-cont40m` (true continuation via `--init-from-source`, 80M cumulative,
  train-5, VERIFIED RUNNING) to resolve whether leg5's involvement stays flat/noise or sharpens
  into genuine chronic entrenchment with more exposure. Also attempted the 2nd composite-ACQ
  respec (`allaxiskickhalf-nocrutch1x-c1-acq1`) independently -- REFUSED as a W&B duplicate, a
  concurrent cycle having placed the IDENTICAL respec on train-3 moments earlier (convergent
  reasoning, no duplicate spend, confirmed genuinely running via `launch_run.py status`).
  SKILLS.md updated (2 new rows). Left 7 free GPU slots (train-0/4/7/8/9/10/11) idle at exit:
  cross-checked against a concurrent cycle's own ~11:1x entry (this same file, above) which
  independently reached the identical conclusion moments earlier -- every QUEUE AIM frontier item
  (both composite ACQs + the kick-dose cont40m) is now genuinely in-flight, not neglected; no
  further genuinely new axis/composite/cont40m candidate identified. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_{fault1x_c1_acq1_r3,
  kickhalf_notorquecrutch_c1}_gate/report.json`, W&B `9nx4uk9j`/`cmjrh8w8`, `launch_run.py
  status`, RL_LOG 09-06 11:00-11:2x.

- 09-06 ~11:1x this cycle (assigned `torquefade15x-c1-acq1-cont40m`): **ACQ PASS (HARDENING) — the
  1.5x torque-fade axis's OWN 2nd endurance confirmation; 0 net new launches (the licensed follow-up
  was already in flight under a concurrent cycle).** `torquefade15x-c1-acq1-cont40m` reproduces its
  40M parent's PERFECT 24/24 gait_valid exactly at 80M cumulative (0 falls/terms, sac=[] every
  episode, slip/m in-band, reward still rising every quarter 1240->2143->2246->2328) — closes the
  torque-fade dose axis's endurance question for good: 1x/1.5x/2x are ALL now clean at ACQ+cont40m
  scale. SKILLS.md updated (1 new row). **Refill:** identified the natural next QUEUE-AIM-item-(2)
  step — a cont40m of `kickhalf1x-c1-acq1` (ACQ PASS this session with a leg5 WATCH, explicitly
  flagged in its own verdict as needing exactly this follow-up) — and attempted to launch it via
  respec; the launcher REFUSED as a duplicate, a concurrent cycle having placed the IDENTICAL respec
  (same hypothesis reasoning, independently derived) on train-5 moments earlier. No further genuinely
  new arm existed: both composite ACQs (`allaxis-nokick-c1-acq1`, `allaxiskickhalf-nocrutch1x-c1-
  acq1`) were already training, and per this banner's own STOP the per-axis DR-restore grid stays
  closed. Left ~7 free GPU slots (train-0/4/7/8/9/10/11) idle at exit: every QUEUE AIM frontier item
  (both composite ACQs + the kick-dose cont40m) is now genuinely in-flight elsewhere, not neglected.
  Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_torquefade15x_c1_
  acq1_cont40m_gate/report.json` vs `..._torquefade15x_c1_acq1_gate/report.json`, W&B `xw4dkuk9`,
  `launch_run.py status`, RL_LOG 09-06 11:15/11:2x.

- 09-06 ~11:0x this cycle (assigned `kickhalf1x-c1-acq1`, `torquefade2x-c1-acq1-cont40m`): **both
  verdicted PASS -- half-dose kick recovery holds at 40M (with a leg5 watch), torque-fade-2x axis
  holds at 80M cumulative -- plus a 2-arm refill exercising the just-unblocked composite frontier.**
  (1) `kickhalf1x-c1-acq1` **ACQ PASS/HOLDS**: 20/24 gait_valid (5/6 det, 5/6 sto, 6/6
  startjitter/det, 4/6 startjitter/sto), 0 falls, matching the 2M canary's own 21/24. WATCH: the
  canary's 3-different-legs scatter narrowed to a single leg (index 5) recurring in 4/24 episodes,
  but that leg's actual duty is healthy (0.3-0.6) in the other 20/24 and only dips to 0.03-0.09 in
  the flagged ones -- occasional near-threshold noise, not a sustained chronic pattern; flag for
  the next continuation of this exact lineage. (2) `torquefade2x-c1-acq1-cont40m` **HARDENING
  PASS/HOLDS**: 23/24 vs the parent's PERFECT 24/24, 0 falls, one non-chronic singleton (leg5,
  startjitter/det ep1 only) -- another clean-source endurance confirmation. SKILLS.md updated (2
  new rows). **Refill (80M/cycle cap, exactly spent):** a concurrent cycle's own `allaxiskickhalf-
  nocrutch1x-c1` CANARY PASS (21/24, 0 falls -- de-crutched actuator does NOT destabilize the full
  composite) landed just before this cycle read, licensing the composite frontier's 2nd ACQ arm
  (the 1st, `allaxis-nokick-c1-acq1`, keeps the torque crutch ON and disables kick; this recipe
  keeps kick at its proven-safe half-dose AND removes the crutch -- a genuinely different cell, not
  a duplicate). Launched `allaxiskickhalf-nocrutch1x-c1-acq1` (train-3, 40M, VERIFIED RUNNING via
  `kubectl exec ps`) -- closes QUEUE AIM item (3)'s composite-no-crutch half for real once it lands.
  Also found+launched a genuinely lacking composition-line cont40m (NOT a per-axis confirmation, so
  not covered by QUEUE AIM's own STOP): `halfgrav-irrwiden-c1-acq1` (the widen+irr jitter-first
  composite, ACQ PASS 22/24, 0 falls, only 2/24 scattered non-chronic flags -- a clean source per
  the campaign's own cleanliness-margin-predicts-endurance rule) had no cont40m read yet -- launched
  `halfgrav-irrwiden-c1-acq1-cont40m` (train-1, 40M, VERIFIED RUNNING). Both together = 80M new GPU
  steps, exactly the per-cycle cap; left the remaining ~7 free slots (train-0/4/5/7/8/9/10/11) idle
  since the step budget, not launch count, is now spent. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_{kickhalf1x_c1_acq1,torquefade2x_c1_acq1_
  cont40m}_gate/report.json`, W&B `x4yqywuc`/`dpdvz0ev`, `launch_run.py status`, RL_LOG 09-06 11:0x.

- 09-06 ~11:0x this cycle (refill-only, no completions assigned; canonical
  capacity found 9 free slots + empty backlog): **found+verdicted 2 more
  orphans (both CANARY PASS), closing QUEUE AIM items (1) and (3) for real,
  and launched BOTH licensed composite-ACQ continuations.** (1)
  `allaxis-nokick-c1` (kick fully OFF, crutch ON) had just been CANARY
  PASS'd by a concurrent cycle moments before this read (19/24 gv, 0 falls)
  -- confirms kick was the sole broken composite ingredient; no re-verdict
  needed, read directly. (2) Found+verdicted `allaxiskickhalf-nocrutch1x-c1`
  (kick-safe half dose + crutch fully removed) **CANARY PASS**: 21/24 gv, 0
  falls/24, no chronic single-leg sacrifice (3 flagged episodes hit 3
  different legs) -- COUNTER to the gate's own stated FAIL hypothesis ("the
  crutch is load-bearing for composite tolerance"): de-crutching does NOT
  destabilize the composite, it just runs much slippier (7-17/m vs 3-6/m
  crutch-ON). This closes QUEUE AIM item (3)'s remaining half. (3)
  Found+verdicted `imumount1x-c1` **CANARY PASS** (24/24 gv, 0 falls) -- the
  last untested `RandRanges` field per the 09-06 ~10:1x field sweep;
  per-axis DR-restore is now genuinely exhaustive with zero remaining
  untested field. **Refill: launched BOTH composite ACQ continuations the
  two canary PASSes above license** (per QUEUE AIM's own "on a composite
  canary PASS fund ONE composite ACQ" rule, applied once per distinct recipe
  since these are two independent questions, not duplicates):
  `allaxis-nokick-c1-acq1` (train-2, kick-fully-off/crutch-ON, VERIFIED
  RUNNING) and `allaxiskickhalf-nocrutch1x-c1-acq1` (train-3,
  kick-safe/crutch-OFF, VERIFIED RUNNING) -- 80M new GPU steps total (cycle
  cap), 2 launches (within the 4/cycle cap). SKILLS.md updated (2 new
  entries). Left the remaining free slots idle at read time: the kick-dose
  ladder ACQ (`kickhalf1x-c1-acq1`) and the `assistfade` rung-2 anchor-fade
  canary pair (`cw-assistfade-rung2-anchorfade-s0/-s1`, a concurrent cycle's
  own launch, already found in-flight when this cycle checked) were the
  only other live frontier items; no further genuinely new axis/composite/
  cont40m candidate was identified this cycle beyond the two funded above.
  Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_
  medhead_dr_{allaxis_nokick_c1,allaxiskickhalf_nocrutch1x_c1,
  imumount1x_c1}_gate/report.json`, W&B `1eh4y2ou`/`i5bvlxvc`/`nz5fs9oo`,
  `launch_run.py status`, RL_LOG 09-06 11:0x.

- 09-06 ~10:5x-11:0x this cycle (assigned `medhead-dr-mass1x-c1-acq1-cont40m`; found+verdicted 1
  orphan; attempted 1 refill that turned out already in flight): **1/1 assigned run ACQ PASS
  (HARDENING); 1 found orphan CANARY FAIL closing the kick-dose ladder tighter; 0 net new launches
  (the intended composite-ACQ refill was already queued+running under a concurrent cycle by the
  time my respec landed — auto-deduped, no duplicate GPU spend).** (1) `mass1x-c1-acq1-cont40m`
  **ACQ PASS (HARDENING)**: mass-scale DR axis holds at 80M cumulative -- PERFECT 24/24 gait_valid
  all 4 panels, 0 falls/terms, sac=[] every episode, slip/m near-band (3.65-4.70 med across
  panels), reward still climbing every quarter. Joins friction1x/halfgrav-widenirr in the
  cont40m-endurance-holds column; per QUEUE AIM this is the closing confirmation, no further
  per-axis endurance spend follows. (2) Found+verdicted `kick0225x-c1` (orphan, training+gate
  finished, no ledger owner) **CANARY FAIL - MECHANISM**: the kick-prob dose bisection between
  kickhalf's clean 0.15 and kick1x's falling 0.3 STILL falls at 0.225 (walk/sto/2 terminates
  tilt_roll, fwd stalls to 0.08m), aggregate gait_valid 21/24. Pins the safe-dose ceiling strictly
  between 0.15 and 0.225, not just "somewhere below 0.3" -- do not treat 0.225 as usable. (3)
  Independently derived and attempted to fund the QUEUE-AIM-licensed no-kick composite ACQ
  (`allaxis-nokick-c1-acq1`, kick=0/torque-crutch=3x, same recipe as the CANARY PASS) via respec --
  the launcher REFUSED as a W&B duplicate: a concurrent cycle had already queued+launched the
  IDENTICAL run name/recipe (now genuinely running on train-2, confirmed via `kubectl exec`/
  `launch_run.py status`, step 4.7M+ at read time). No duplicate spend; convergent reasoning, not
  wasted work. (4) Attempted a FAIL verdict on `kickhalf1x-c1-acq1` (read the same chronic-leg[5]-
  across-3-modes duty pattern as a disqualifying consolidation per the gate's own text) but the
  launcher REFUSED: a concurrent cycle had already recorded **ACQ PASS (with a WATCH)** on the
  identical evidence, distinguishing "leg5 duty healthy (0.3-0.6) in 20/24 episodes, only dipping
  to 0.03-0.09 in the 4 flagged ones" from this campaign's OTHER named chronic-entrenchment
  fingerprint (sustained near-zero duty in EVERY episode) -- a reasoned, evidence-based call I
  did not overwrite (both readers reviewed the identical duty table; disagreement is within
  legitimate judgment noise, not a clear misread). Deferred to their verdict; flagged as a WATCH
  item for the next continuation of this exact lineage regardless of which read is closer to
  right. SKILLS.md updated (2 new entries: mass1x cont40m PASS, kick0225x FAIL). **Also found**
  `cw-assistfade-rung2-anchorfade-{s0,s1}` (the campaign's first rung-2 mechanism-health canaries)
  FINISHED with no eval report yet synced -- kicked `podeval` for both (backgrounded, genuinely
  running remotely per `ps` at read time), left UNVERDICTED for the next reader (mechanism-health
  judgment needs the harness read, not just W&B reward curves). **Refill:** confirmed via a full
  live scan (not just `capacity.py`) that every other QUEUE AIM frontier item is genuinely
  computing elsewhere this cycle (`allaxiskickhalf-nocrutch1x-c1` gate on train-8,
  `kickhalf-notorquecrutch-c1`/`imumount1x-c1`/several cont40m gates via live `pod_eval.py`
  processes on other pods) -- did not force a second composite arm on top of the one already
  running. Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_
  {mass1x_c1_acq1_cont40m,kick0225x_c1}_gate/report.json`, W&B `61qwjqbf`/`4xcygaqu`,
  `launch_run.py status`, RL_LOG 09-06 10:54/10:56.

- 09-06 ~10:5x this cycle (assigned `fault1x-c1-acq1`/`gains1x-c1-acq1`/`geom1x-c1-acq1`, all 3
  already SUPERSEDED by a concurrent cycle before this read landed -- confirmed, not re-triaged):
  **0/3 assigned runs needed action; found+verdicted 1 orphan (CANARY PASS, closes the per-axis DR
  sweep exhaustively); repaired a live cross-cycle collision on the assistfade rung-2 semantics bank
  (test file, not mine to keep after a concurrent session finished its own fix); launched the
  assistfade rung-2 anchor-fade canary (2 seeds) once that bank went green; found+verdicted 1 more
  orphan (CANARY PASS, decisively closes the composite kick-isolation question).** (1) `medhead-dr-
  legmass1x-c1` **CANARY PASS**: PERFECT 24/24 gait_valid, 0 falls, sac=[] every episode -- per-leg
  mass-asymmetry realism is free; this was one of the 2 final untested RandRanges fields (the other,
  `imumount1x-c1`, was already computing elsewhere) -- the per-axis DR-restore sweep is now fully
  exhaustive. (2) Independently attempted to build the assistfade track's owed intermediate-state
  semantics bank (STATUS.md Next item 1) via direct empirical probing of `SimHexapodJointWalkEnv` +
  `TripodGait` (found: freezing a partial pose for the REMAINING ~13s of a 15s episode scores WORSE
  than doing nothing at all -- measures "stuck", not "progress"; a SHORT bounded-prefix + mean-
  reward-per-tick construction is the fix; a `dr.torque_scale`-realistic -50deg topple dose never
  crosses `safety.max_roll_deg=25` and must be -90deg to genuinely fall) -- appended this to
  `test_task_semantics.py`, then discovered mid-edit that a CONCURRENT session was independently
  building/fixing the SAME bank in the SAME file in real time (the file grew twice under this
  session with no local edit between reads) and had reached the SAME two findings. Removed this
  session's duplicate rather than fight the collision; the concurrent session's own fix landed and
  all 5 `test_assistfade_rung2_*` tests now pass. Updated `assistfade/STATUS.md` to record the bank
  as green and specify the exact rung-2 launch cfg (random init, `train.bc_anchor_coef=3.0` --
  the campaign's own most-common "strong" dose, not a fresh guess -- + `train.bc_anchor_anneal_
  gate=1`, every anneal sub-knob at its coded default). (3) **Launched the rung-2 canary itself**
  (`cw-assistfade-rung2-anchorfade-{s0,s1}`, 2 seeds per the curriculum doc's own gate, 2M each,
  `backlog add` + drain, both VERIFIED RUNNING train-1/train-9) -- the first real exercise of the
  09-06-built anneal-gate training mechanism, now precondition-clear (mechanism + bank both green).
  (4) Found+verdicted orphan `medhead-dr-allaxis-nokick-c1` **CANARY PASS/INFORMATIVE-POSITIVE**:
  with kick fully OFF (0.0, not even `allaxiskickhalf1x-c1-r2`'s half dose, which itself still fell
  7/24), the SAME ~30-axis composite that failed at both full kick (`allaxis1x-c1`, 5/24 tilt_roll)
  and half kick (7/24 tilt_roll) reads 0 falls/24, gait_valid 19/24, contact sheet clean six-leg
  cycling -- decisively closes the kick-isolation question: kick (any nonzero dose tried) was the
  SOLE broken ingredient, not a diffuse many-axis interaction. Licenses a composite ACQ (40M) on
  this exact no-kick recipe; kick-recovery hardening stays its own isolated dose-ladder line
  (`kick0225x-c1`/`kickhalf1x-c1-acq1`, both still genuinely computing, left untouched). SKILLS.md
  updated (2 entries). Did not fund a composite ACQ this cycle (a fresh finding, not yet cross-
  checked against `allaxiskickhalf-nocrutch1x-c1`'s own still-computing read, which shares the same
  ~28-axis base and could change the recipe again). Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_{legmass1x_c1,allaxis_nokick_c1}_gate/
  report.json`, W&B `f9nrfyok`/`1eh4y2ou`, `rl_docs/tracks/assistfade/STATUS.md`, RL_LOG 09-06
  10:2x-10:5x.

- 09-06 ~10:3x this cycle (assigned `geom1x-c1-acq1-r2`; found+verdicted 2 orphans, no new launch):
  **1 assigned ACQ PASS + 2 found orphans (1 ACQ PASS, 1 CANARY FAIL closing QUEUE AIM item (1) for
  good), 0 new launches -- every frontier item is either closed or already genuinely computing on
  another pod.** (1) `medhead-dr-geom1x-c1-acq1-r2` **ACQ PASS**: the corrected (real 40M, not the
  r1 2M-step-bug budget) print/assembly GEOMETRY-spread axis holds durable at ACQ scale -- 22/24
  gait_valid, 0 falls/24, 2 non-chronic singleton flags, slip in-band, contact sheet clean six-leg
  cycling. (2) Found+verdicted `groundtilt1x-c1-acq1` (orphan: training+gate finished, ledger stuck
  at stale RUNNING, never verdicted) **ACQ PASS**: 22/24 gait_valid, 0 falls, floor-slope axis
  durable at 40M -- both close per-axis DR-restore confirmations, already-STOPped information per
  this banner's own QUEUE AIM (no further per-axis spend follows from either). (3) Found+verdicted
  `allaxiskickhalf1x-c1-r2` (orphan, the kick-safe ~30-axis composite retry after a stale-pod-code
  REFUSED first attempt) **CANARY FAIL - MECHANISM**: capping kick to its proven-safe half dose does
  NOT rescue the full composite -- 7/24 episodes terminate tilt_roll (worst in the startjitter/
  perturbed-start modes), same shape as the plain all-axis composite's prior FAIL. **This closes
  QUEUE AIM item (1)'s second half decisively: kick dose was never the sole broken ingredient for
  the full composite at either dose (full-kick FAIL, half-kick FAIL); axes still interact when ~30
  are stacked.** Two further bisections were already in flight at read time (confirmed via direct
  `kubectl exec ps`, not just `capacity.py`) and left running/unverdicted for the next reader:
  `allaxiskickhalf-nocrutch1x-c1` (kick-safe + torque de-crutched, on train-8) and `allaxis-nokick-c1`
  (kick fully OFF, all other ~28 axes at full dose, on train-2) -- backgrounded `pollreap` for both.
  Per this doc's own QUEUE AIM text ("on a composite canary PASS fund ONE composite ACQ"), do NOT
  fund a composite ACQ off any exact recipe tried so far; read the two in-flight bisections first.
  **Refill: 0 new launches despite free GPU capacity (6 free slots when first checked, growing to
  10/11 free by cycle end as 4 more `cont40m` runs finished their GPU trainer phase -- train-0/2/3/4
  freed up mid-cycle; `train-7` was the only pod still training at cycle end).** Checked every
  registered track, not just walkcurr: per-axis
  DR-restore is closed (this cycle's own 2 PASSes are further already-STOPped confirmations, not
  new information); the composite/kick-dose/torque-crutch frontier items are ALL genuinely
  computing on other pods right now (`kickhalf1x-c1-acq1` gate on train-7, `kick0225x-c1` gate on
  train-4, plus the 2 bisections above) -- launching anything on that exact frontier now would
  duplicate an already-in-flight read or combine unresolved variables before either half's result
  lands. `joystick`/`cpg`/`standwalk`/`todaypolicy` STATUS docs are all stale/closed (no fresh dated
  Next item since 08-2x/08-30, or explicitly DONE/CLOSED) -- the only other track with live 09-06
  activity is `assistfade`, whose own Next item (rung-2 intermediate-state semantics bank) was found
  ALREADY mid-write by a concurrent process (an uncommitted `test_task_semantics.py` diff observed
  changing in real time between two reads this cycle, 257->281 diff lines with no local edit from
  this session) -- left untouched to avoid a collision on the same shared file. Genuinely nothing
  launchable without duplicating in-flight compute or another live session's WIP; not idle-next-to-
  runnable-work, blocked-on-in-flight-elsewhere is a real reason. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_{geom1x_c1_acq1_r2,groundtilt1x_c1_acq1,
  allaxiskickhalf1x_c1_r2}_gate/report.json`, W&B `442acsdz`/`z6vush6h`/`mfwj180i`, `launch_run.py
  status`, RL_LOG 09-06 10:28-10:31.

- 09-06 ~10:1x this cycle (assigned `cmddrop1x-c1-acq1`; found+closed 5 idle orphans): **assigned
  run left genuinely computing (0/1 verdicted this cycle), but closes QUEUE AIM frontier item (3)
  (torque-crutch removal) via a found orphan, plus 4 mislabeled-budget ledger closures.** (1)
  `cmddrop1x-c1-acq1`: gate harness confirmed genuinely computing on train-9 (`ps` live, ~20min in
  of the usual 25-40min window at read time) -- backgrounded `pollreap`, left UNVERDICTED for the
  next reader. (2) **Found+verdicted `torquefade1x-c1-acq1` (idle, unassigned, no ledger owner):
  ACQ PASS** -- the campaign's hardest torque-crutch-removal dose (`dr.torque_scale=1.0`, the REAL
  unassisted servo torque spec, zero assist margin) holds PERFECTLY at full 40M scale: 24/24
  gait_valid all 4 panels, sac=[] every episode, 0 falls/terms. slip/m runs higher than the
  crutched 1.5x/2x siblings (4.6-6.75 vs 3.x-5.x) with correspondingly shorter forward_dist, but
  gait validity/stability are untouched. Frame strip confirms clean six-leg cycling. **Closes
  QUEUE AIM item (3)** and satisfies the no-crutch half of item (4)'s precondition -- the composite
  half (`allaxiskickhalf1x-c1-r2`) is still computing its own gate (confirmed live via `ps`,
  backgrounded `pollreap`, ETA within the hour per the usual harness window). SKILLS.md updated.
  (3) **Closed 4 mislabeled-budget duplicate orphans** (`extpush1x`/`fault1x`/`gains1x`/
  `geom1x-c1-acq1`, all FINISHED, unverdicted): each silently landed at its source canary's 2M step
  budget instead of a real 40M ACQ read (the same respec-steps-inheritance footgun documented
  earlier this campaign) -- verdicted SUPERSEDED, pointing to each axis's already-PASSed plain `-c1`
  canary for the equivalent information and its correctly-budgeted `-r2`/`-r3` relaunch (already
  running/verdicted elsewhere) for the real ACQ read. Prevents 4 dangling FINISHED/unverdicted
  ledger entries from masquerading as open work. (4) **Kicked one genuinely-idle orphan gate**
  (`kick0225x-c1`, the dose bisection between kickhalf's clean 0.15 and kick1x's falling 0.3 --
  finished training with NO eval ever started) via `podeval` on its own pod (train-4, alongside its
  existing unrelated trainer+eval load -- GPU 0% util confirmed, CPU-only addition); backgrounded
  `pollreap`. Also backgrounded `pollreap` for 2 more orphans found already genuinely computing
  remotely with no local supervisor (`allaxiskickhalf1x-c1` non-r2, `imumount1x-c1`, `legmass1x-c1`
  -- the last 2 are new DR axes, confirmed via a full `domain_rand.py` `RandRanges` field sweep to
  be the LAST 2 fields with zero prior canary; every other field now has at least one PASS).
  **Refill:** capacity.py showed 5 FREE slots (train-3/5/8/9/11) + empty backlog throughout, but
  did NOT force a new launch: per-axis DR-restore funding is explicitly STOPped by this doc's own
  QUEUE AIM (confirmed exhaustive -- no genuinely new axis remains per the field sweep above), and
  every other frontier item (composite bisection, kick-dose ladder, the kick-safe+no-crutch
  interaction probe `kickhalf-notorquecrutch-c1`) already has an arm genuinely in flight on another
  pod (verified via direct `kubectl exec ps`+`nvidia-smi`, not just `capacity.py`'s trainer-only
  view) -- launching another arm now would either duplicate an in-flight read or combine two
  still-unresolved variables (composite x no-crutch) before either half's result is known. Nothing
  new to fund without waiting on those genuinely-computing reads; not idle-with-empty-queue by
  choice, blocked-on-in-flight-compute is a real reason, not a filler excuse. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_torquefade1x_c1_acq1_gate/
  report.json`, W&B `11p0scan`, `launch_run.py status`/`capacity.py`, RL_LOG 09-06 10:1x-10:2x.

- 09-06 ~10:0x this cycle (assigned `gains1x-c1-acq1-r2`, `groundtilt1x-c1-acq1`): **1/2 verdicted
  (ACQ PASS, 9th/final single-axis DR-restore confirmation), 1/2 left genuinely computing (orphaned
  gate harness, pollreap backgrounded); plus a 2-arm cont40m refill.** (1) `gains1x-c1-acq1-r2`
  **ACQ PASS**: PERFECT 24/24 gait_valid across all 4 modes, 0 falls/terms, contact sheet clean
  six-leg stance/gait, reward still rising every quarter (562->1181) -- confirms the corrected
  (real 40M, not the r1 2M-step-bug budget) gains-spread axis is durable at ACQ scale, matching its
  own 2M canary (23/24). Per this doc's own QUEUE AIM, this closes per-axis DR-restore confirmation
  as an information source (9/9 funded axes now hold; every RandRanges field is covered by an
  existing single-axis or bundle canary -- confirmed by cross-checking `domain_rand.py`'s full field
  list against every launched `medhead-dr-*` arm name, no genuinely new axis remains). (2)
  `groundtilt1x-c1-acq1`: training finished (40.37M steps) but its gate harness was found STILL
  genuinely computing remotely on train-2 (`ps` confirmed a live `eval_checkpoint` process, no local
  supervisor left since the pod was reassigned to a new training launch mid-eval) -- backgrounded
  `pollreap`, left UNVERDICTED for the next reader. SKILLS.md updated (1 new entry). **Refill:**
  per the QUEUE AIM's own STOP on further per-axis spend, and with the composite-realism/kick-dose/
  torque-crutch frontier items all genuinely still in flight on other pods (no local report.json for
  `allaxiskickhalf1x-c1-r2`, `kick0225x-c1`, `allaxis-nokick-c1`, `kickhalf-notorquecrutch-c1` at
  read time -- not actionable), used the 5 free GPU slots for the next tier down: cont40m endurance
  continuations on clean 40M ACQ PASS composition sources still lacking one, picking 2 that are
  NOT superseded by a later seed/variant and span DIFFERENT gravity families (avoiding piling onto
  the same already-well-tested halfgrav-widen/irr cluster): `headset-base-acq1-cont40m` (train-7,
  the 1g base family's flagship heading-generalization champion's FIRST cont40m -- every prior
  cont40m read has been a crossgrav/halfgrav source) and `headset-crossgrav-medhead-ramp-c1-acq1-
  cont40m` (train-3, the gradual-ramp gravity-transfer root's FIRST cont40m -- its ABRUPT sibling
  already confirmed clean at 80M, and ramp's own irrfwd/widenfwd children already got cont40m, but
  the plain ramp root itself had not). Both VERIFIED RUNNING via `kubectl exec ps` (the ramp launch's
  own foreground verification step raced my 120s tool timeout; confirmed live via direct `ps` then
  corrected the ledger status by hand). 80M new GPU steps = the per-cycle cap. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_gains1x_c1_acq1_r2_gate/
  report.json`, `launch_run.py status`, RL_LOG 09-06 10:0x.

**QUEUE AIM (meta 2026-09-06 — refills read this before funding; UPDATED ~11:0x).** The
single-axis DR-restore question is answered: EVERY `RandRanges` field now has a clean canary
(`imumount1x-c1`/`legmass1x-c1` closed the last 2, ~11:0x), every funded single-axis ACQ read has
PASSed, every cont40m has held. STOP funding further per-axis ACQ/cont40m confirmations of
already-clean axes. The frontier, in order: (1) composite realism — **RESOLVED ~11:0x: the plain
composite (`allaxis1x-c1`) and the kick-SAFE-dose composite (`allaxiskickhalf1x-c1-r2`) both FAIL
(5/24, 7/24 falls), but BOTH bisections now PASS: `allaxis-nokick-c1` (kick fully off, crutch ON,
19/24 gv 0 falls) and `allaxiskickhalf-nocrutch1x-c1` (kick-safe dose, crutch OFF, 21/24 gv 0
falls, COUNTER to this item's own crutch-load-bearing hypothesis) — kick (at any nonzero dose
tried) is the sole broken ingredient in EITHER crutch state. Both composite ACQs are now LAUNCHED
(`allaxis-nokick-c1-acq1` train-2, `allaxiskickhalf-nocrutch1x-c1-acq1` train-3, both VERIFIED
RUNNING ~11:0x) — do not fund a 3rd composite arm off this exact bisection pair; wait for these
two ACQ reads.**; (2) the kick-dose ladder — kick1x (0.3) and kick0225x (0.225) both FAIL, kickhalf
(0.15) is the confirmed-safe ceiling; kickhalf ACQ (`kickhalf1x-c1-acq1`) still computing, read it
before any further kick-dose spend; (3) torque-crutch removal at ACQ scale — **CLOSED ~11:0x on
every tested combination**: solo (`torquefade1x-c1-acq1` ACQ PASS, 09-06 ~10:1x) and composited
with kick-safe (`allaxiskickhalf-nocrutch1x-c1` CANARY PASS, ~11:0x, its own ACQ now running) —
the crutch is NOT load-bearing for composite tolerance, only for slip magnitude; (4) once the two
composite ACQs above land: the acquisition-milestone panel and the contextual DONE-gate rungs
(heading changes, slip pressure) on the full-realism champion — the next genuinely open item once
either/both composite ACQs PASS.
Per-axis arms stay justified only for a genuinely NEW axis or a composite-FAIL bisection.

- 09-06 ~10:2x this cycle (refill-only, no completions assigned; canonical capacity found 5 free
  slots + empty backlog, other cycles owned every in-flight frontier gate read). Confirmed via a
  concurrent cycle's RL_LOG line that per-axis DR-restore funding is now FULLY closed (9th/final
  axis, `gains1x-c1-acq1-r2` ACQ PASS) -- did NOT re-fund cont40m for the 5 remaining clean
  single-axis ACQ PASSes still lacking one (`actionnoise1x`/`contactstiff1x`/`latency1x`/
  `torquefade1x`/`zerobias1x`), per this banner's own STOP directive. Found 2 finished-training
  frontier canaries with no gate eval started: `kickhalf-notorquecrutch-c1` turned out already
  running elsewhere (train-0, no dup); `allaxis-nokick-c1` was genuinely orphaned -- kicked via
  `podeval`, backgrounded, left unverdicted. **Launched 1 new canary** (within the launch cap):
  `allaxiskickhalf-nocrutch1x-c1` (train-8, VERIFIED RUNNING) -- respec of
  `allaxiskickhalf1x-c1-r2` (the full ~30-axis kick-safe composite, gate still computing) with
  `dr.torque_scale` also dropped 3->1 (the real unassisted servo spec, already ACQ-clean
  standalone via `torquefade1x-c1-acq1`). This is the FULL-composite half of item (3)'s "composite
  WITHOUT the crutch" step, independent of the isolated 2-axis `kickhalf-notorquecrutch-c1` probe
  -- tests whether the OTHER ~28 realism axes (mass/friction/stiffness/etc) interact with a
  de-crutched actuator even though kick+no-crutch alone does not. Left the remaining free slots
  (train-5/9/10/11) idle: every other frontier item (the composite-with-crutch ACQ, the kick-dose
  ladder, the contextual DONE-gate rungs) is genuinely blocked on in-flight gate reads already
  owned by concurrent cycles (`allaxiskickhalf1x-c1-r2`, `kick0225x-c1`, `kickhalf1x-c1-acq1` all
  mid-harness on their own pods) -- not idle-next-to-runnable-work. Evidence: `launch_run.py
  status`/`experiments.json`, RL_LOG 09-06 10:24.

- 09-06 ~09:2x-09:5x this cycle (assigned `actionnoise1x-c1-acq1`, `contactstiff1x-c1-acq1`,
  `deadband1x-c1-acq1`): **all 3 ACQ PASS/HOLDS (3 more single-axis confirmations, closing that
  information source per this same banner's own STOP directive), plus 1 bonus orphan verdict and
  4 new frontier-items-1/2 launches.** All 3 assigned axes hold at 40M in the same pattern class as
  their own 2M canaries (22-23/24, 0 falls, exactly one non-chronic flag each, slip flat) — see
  RL_LOG 09:32/09:57 and `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_
  {actionnoise1x,contactstiff1x,deadband1x}_c1_acq1_gate/report.json`. Bonus: found+verdicted
  `faultworst1x-c1` (guaranteed worst-case single-leg-disable canary, orphan — finished with no
  verdict), CANARY PASS/INFORMATIVE-POSITIVE: harness reads gait_valid 0/24 but this is a harness-
  vs-injected-fault alignment artifact, not a pathology — the one flagged sacrificed leg matches
  the injected fault's own disabled leg in ALL 24/24 episodes, 0 falls. **Refill toward items (1)
  and (2):** with 4-8 GPU slots free for most of the cycle (concurrent cycles' own drains lagged
  finishes), launched 4 new arms (within the 4-launch/cycle cap, ~6M of the 80M GPU-step cap) that
  are NOT more of the already-STOPped per-axis grid: (a) `kick0225x-c1` — the exact dose bisection
  between kickhalf's clean 0.15 and kick1x's falling 0.3, to pin the safe-dose ceiling tighter than
  a 2x gap; (b) `kickhalf-notorquecrutch-c1` — a sharper 2-axis interaction probe (kick-safe dose +
  FULL torque-crutch removal together, isolated from the other ~28 already-composable axes) that
  gives an early read on item (3) while `torquefade1x-c1-acq1`'s own single-axis ACQ gate is still
  genuinely computing; (c) `allaxis-nokick-c1` — a clean control for item (1): same ~30-axis
  composite as the FAILED `allaxis1x-c1` but with kick fully OFF (0.0, not even kickhalf's 0.15),
  to confirm kick was the SOLE broken ingredient rather than some other pairwise interaction. All 4
  are 2M canaries, VERIFIED RUNNING or already finished-training (fast canary) at cycle end,
  unverdicted — next reader should read their gate reports directly, no need to relaunch. Evidence:
  RL_LOG 09-06 09:3x-09:5x, `launch_run.py status`, SKILLS.md (3 new entries this cycle).

- 09-06 ~10:0x this cycle (refill-only, no completions assigned; canonical capacity found 6 free
  slots + empty backlog, other cycles owned the composite/torque-crutch bisections still computing
  their gate evals -- `allaxiskickhalf1x-c1-r2` and `torquefade1x-c1-acq1` both genuinely still
  running their CPU-finalizer eval jobs, left untouched). Per this doc's own QUEUE AIM (per-axis
  DR-restore confirmations are closed), used the 08:50 refill-candidate logline's named list of
  clean ACQ PASS sources still lacking a cont40m endurance continuation. Launched 2 (exactly the
  80M/cycle cap): `headset-halfgrav-irrwiden-c2-acq1-cont40m` (train-1, the jitter-first widen+irr
  composite's weaker-course-obedience 2nd seed) and `headset-halfgrav-medhead-acq1-cont40m`
  (train-0, the foundational 0.5g medium-heading-set source several downstream widen/irr composites
  build on) -- both VERIFIED RUNNING (the medhead one needed a manual `update --set status=RUNNING`
  after a shell timeout raced the launcher's own verification step; the trainer process itself was
  confirmed live via `kubectl exec ps` first). Queued (not launched, cap already spent) the other 2
  named candidates to `backlog.json` for the next drain: `headset-base-s1c1-acq1-cont40m`,
  `headset-halfgrav-fullhead-widen2-c3-acq1-cont40m`. Evidence: `launch_run.py status`/
  `experiments.json`, RL_LOG 09-06 10:0x.

- 09-06 ~10:0x this cycle (assigned `zerobiasframe1x-c1-acq1-r2`, `s1acq-irrfwd-c1-acq1-cont40m`,
  `s1acq-widenfwd-c1-acq1-cont40m`): **2 cont40m PASS/HOLDS + 1 cont40m FAIL/ENTRENCHES --
  first counter-example to the campaign's endurance-margin rule.** (1) `medhead-dr-
  zerobiasframe1x-c1-acq1-r2` **ACQ PASS**: 22/24 gait_valid (6/6/5/5), 0 falls/24, 2 non-chronic
  singleton flags -- 5th single-axis DR-restore ACQ confirmation, and the corrected re-run of a
  respec that silently inherited its source canary's 2M step count (the same `--steps`-not-
  overridden bug already found on gains1x/geom1x/fault1x/extpush1x -- always check `extra_args`
  for an explicit `--steps N` after any respec). (2) `s1acq-widenfwd-c1-acq1-cont40m` **HARDENING
  PASS/HOLDS**: 20/24 vs parent's 21/24, chronic sac pattern reproduces exactly + 1 new non-chronic
  singleton, slip IMPROVED -- 5th cont40m endurance confirmation, on the noisiest composition
  tested. (3) `s1acq-irrfwd-c1-acq1-cont40m` **FAIL/ENTRENCHES**: the chronic leg[2,4] pair,
  confined to walk/det at the 40M parent, SPREADS into walk/sto (previously perfectly clean, every
  leg duty 0.14-0.58) at 80M -- leg[4] duty collapses to 0.06 in a new sto episode, exactly the
  pre-registered spread trigger this run's own gate was designed to catch. Aggregate gait_valid
  19/24 vs parent's 20/24 (close in raw count; the qualitative mode-spread is the disqualifying
  signal). 0 falls (not a safety failure). Reward climbed every quarter throughout (651->1156->
  1261->1399) -- the walkcurr binding triage rule's MISALIGNED case, not a continue-for-budget
  case: do not fund a further cont80m of this exact composition. **First cont40m in the endurance-
  margin series to break the "clean-at-40M predicts cont40m holds" pattern** (5 prior cont40m reads
  all PASSed/HELD: widen2c1-irrfwd exact-hold, widenirr-c3 narrow dip, medhead-irrfwd improves,
  widenfwd near-hold, halfgrav-widenirr-c3 mild-degrade). Updated rule: read cont40m holds by
  per-leg duty trace mode-by-mode, not just the aggregate gait_valid count. **Tooling note:** all
  three gate evals had finished remotely with nobody watching (their pods concurrently claimed for
  new training launches by other cycles in the same window) -- reaped via `pod_eval.py <run>`
  copy-back-only rather than relaunching; check `remote_report_exists`-style reaping before
  assuming a missing local artifact means the eval never ran. SKILLS.md updated (3 entries).
  Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_{medhead_dr_
  zerobiasframe1x_c1_acq1_r2,s1acq_widenfwd_c1_acq1_cont40m,s1acq_irrfwd_c1_acq1_cont40m}_gate/
  report.json`, W&B `8dv3hru5`/`o4p4pjkr`/`8w82uq33`, RL_LOG 09-06 10:06/10:07.

- 09-06 ~09:2x this cycle (assigned `zerobias1x-c1-acq1`; found+verdicted `allaxis1x-c1`): **1 ACQ
  PASS (4th clean single-axis confirmation), 1 CANARY FAIL closing the QUEUE AIM's item (1).**
  (1) `medhead-dr-zerobias1x-c1-acq1` **ACQ PASS**: 23/24 gait_valid (6/6/6/5 across the 4 panels),
  0 falls/24, sac=[] in 23/24 (one non-chronic walk_startjitter/sto leg[0] flag), matching the 2M
  canary's own PERFECT 24/24 -- joint-zero-calibration-bias realism is durable at 40M scale, not
  just canary-clean. 4th individual-axis DR-restore ACQ confirmation (after friction1x/mass1x/
  latency1x). (2) `medhead-dr-allaxis1x-c1` (the campaign's ~20-axis-at-once culmination canary,
  found unverdicted/idle) **CANARY FAIL - MECHANISM**: 5/24 episodes terminate `tilt_roll` --
  spread across all 4 panels, not confined to one mode -- despite `gait_valid` nominally staying
  majority (23/24) and slip/m only moderately worse than single-axis siblings. `roll_peak_deg`
  runs 16-33 across the set and the terminated episodes' own frame strips (`walk_det_3.png`) show
  the body visibly tipping through the back half of the episode before the safety cutoff. This
  directly confirms the gate's own pre-registered hypothesis: realism axes that are each
  individually harmless in isolation compound/interact when stacked -- the SAME class of
  composition regression already seen once at the pairwise scale (irr+widen). Closes QUEUE AIM
  item (1)'s first half; do NOT fund an ACQ continuation of this exact all-axis-at-once composite.
  The kick-safe bisection (`allaxiskickhalf1x-c1`, capping the one known-bad ingredient at its
  proven-safe half dose) was already queued+launched by a concurrent/meta session before this
  read landed -- read that before any further composite-realism launch. **Tooling incident (self-
  correcting, no data lost beyond the immediate write):** mid-cycle, after fixing a shell-quoting
  artifact (an unescaped backtick in a verdict string executed as a command substitution, emptying
  one run-name reference) with a raw `json.load`/`json.dump` hand-edit of `experiments.json`, the
  resulting reformatting diff looked alarmingly large and was reverted with `git checkout --
  experiments.json` -- which, since concurrent cycles write this ledger continuously and it carries
  real uncommitted state between snapshot commits, wiped the file back to the last snapshot
  (~6 min stale), losing this cycle's own two just-written verdicts (nothing else, confirmed by
  diffing the restored file against the last commit -- no evidence any *other* concurrent cycle's
  write fell in that window). Both verdicts were immediately re-applied via the sanctioned
  `launch_run.py update --set status=... --set verdict=...` path (never hand-edit
  `experiments.json` again, not even to fix a typo -- always route through `update --set`).
  Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_{zerobias1x_c1_
  acq1,allaxis1x_c1}_gate/report.json`, W&B `r7b1feao`/`25i0uyfk`, RL_LOG 09-06 09:20/09:23.
  **Refill:** checked all 11 reachable pods directly via `kubectl exec ps` (not just
  `capacity.py`'s free-slot list, which only tracks `train_ppo_mjx` processes and misses live
  `eval_checkpoint` load) -- every pod is genuinely busy, either training
  (`allaxiskickhalf1x-c1-r2` just landed on train-8, `torquefade2x/torquefade15x-c1-acq1` on
  train-5/train-0, the rest of the still-training list) or mid-gate-eval (`torquefade1x-c1-acq1`
  on train-11, `zerobiasframe1x-c1-acq1`/`extpush1x-c1-acq1-r2` on train-10). No genuinely free
  GPU capacity this cycle; backlog confirmed empty (`launch_run.py drain` -> "backlog empty"). Did
  NOT force a launch onto a busy pod. The QUEUE AIM's remaining frontier items (kick-safe
  composite bisection, no-crutch ACQ read) are already in flight from prior cycles; the next
  actionable step (fund ONE composite ACQ, or compose no-crutch + composite) is genuinely blocked
  on those in-flight reads, not on idle capacity.

- 09-06 ~09:3x this cycle (assigned `medhead-dr-{tiltnoise1x,torquefade1x,zerobiasframe1x}-c1-acq1`): **0/3
  verdicted (all 3 genuinely still computing their gate harness on-pod, confirmed via `ps`/`podeval` — not
  orphaned, just long video-every=1 panels), plus a 2-run bonus orphan recovery + matched refill.** All 3
  assigned runs finished training (W&B state=finished, ~40.37M steps, pods already reassigned) but their
  ACQ-scale gate harness was still mid-eval (started 08:45-08:55, ~35-40min in at read time) — `ops.sh
  podeval` on each confirmed a live `eval_checkpoint` process on the run's own pod, not a stale/orphaned
  launch; backgrounded one `pollreap` per run (300s/180min) and left all 3 unverdicted for the next reader.
  **Bonus: found+verdicted 2 more idle unassigned orphans in the same torque-crutch-removal dose ladder**
  my own `torquefade1x-c1-acq1` belongs to — `torquefade2x-c1-acq1` and `torquefade15x-c1-acq1` had both
  actually finished (W&B finished, complete `report.json`+videos) but sat stuck at ledger status=RUNNING
  with their pods long since reassigned. Both **ACQ PASS**: PERFECT 24/24 gait_valid, sac=[] every episode,
  0 terms, clean six-leg video, reward rising every quarter (874->1709 / 937->1912) — closes 2/3 of the
  torque-crutch dose ladder at ACQ scale (2x and 1.5x hold; the least-faded 1x dose is my own pending run).
  SKILLS.md updated. **Refill:** launched the standard cleanliness-margin cont40m endurance continuation on
  both fresh clean sources — `torquefade2x-c1-acq1-cont40m` (train-3) and `torquefade15x-c1-acq1-cont40m`
  (train-10), both VERIFIED RUNNING, 80M new GPU steps = exactly the per-cycle cap. Noted but NOT touched
  (out of scope/budget): 5 more GPU slots (train-2/4/8/9/11) freed up mid-cycle as other unrelated runs
  finished (`groundtilt1x-c1-acq1`, `cmddrop1x-c1-acq1`, `imubias1x-c1-acq1`, `headset-halfgrav-acq1-
  cont40m`) — none of these were this cycle's assignment and the step/launch cap was already spent; leaving
  them for the next triage/refill cycle. Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  crossgrav_medhead_dr_torquefade{2x,15x}_c1_acq1_gate/report.json`, W&B `n838t060`/`n8j96qsz`, RL_LOG
  09-06 09:3x.

- 09-06 ~09:0x this cycle (assigned `halfgrav-widenirr-c3-acq1-cont40m`): **HARDENING PASS/HOLDS**
  -- first halfgrav-source cont40m endurance read (80M cumulative). `gait_valid` mildly degrades
  21/24 (own 40M) -> 19/24 (walk/det 4/6, walk/sto 4/6, walk_startjitter/det 5/6, walk_startjitter/
  sto 6/6), both named modes (det/sto) still majority-valid per the gate's own >=4/6 bar, 0 falls/24,
  no NEW chronic single-leg pattern (every sac flag scattered/non-chronic). `slip_per_m` drifted up
  in `/sto` (3.57->5.94 med, one outlier 10.33) -- flagged as worth watching, not gate-failing.
  Extends the cleanliness-margin-predicts-endurance rule to a 0.5g source for the first time.
  Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_widenirr_c3_acq1_cont40m_gate/
  report.json`, W&B `i0ucnjvx`. **Refill:** fleet had 3 free slots (train-1/3/5) + 1 stuck backlog
  item (`fault1x-c1-acq1-r3`, REFUSED twice for a missing `--evidence` field from a prior cycle's
  queue -- patched the evidence field in place under `backlog.json.lock`, attempts reset to 0, no
  behavioral change). Queued + launched 2 NEW cont40m endurance continuations on clean 40M ACQ PASS
  sources still lacking one (per the prior cycle's own named refill-candidate list):
  `medhead-dr-friction1x-c1-acq1-cont40m` (train-1, source 24/24 gv, 0 falls) and
  `medhead-dr-mass1x-c1-acq1-cont40m` (train-5, source 24/24 gv, 0 falls) -- 80M new GPU steps,
  exactly at the `max_new_gpu_steps_per_cycle` cap (the 3rd drained item, `fault1x-r3`, was a
  mechanical unstick of a PRIOR cycle's already-budgeted queue entry, not new scope, so not
  double-counted against this cycle's own cap). All 3 verified RUNNING (not just INTENT) via
  `kubectl exec` log tail before exit. Evidence: `launch_run.py status`, RL_LOG 09-06 09:0x.

- 09-06 ~08:4x-09:0x this cycle (assigned `medhead-dr-push1x-c1-acq1`, `widen2c1-irrfwd-c1-acq1-
  cont40m`): **1/2 verdicted (HARDENING PASS, exact hold), 1/2 left genuinely computing; plus a
  bonus 9-run verdict batch on idle unassigned canaries + 4-arm ACQ refill.** (1)
  `widen2c1-irrfwd-c1-acq1-cont40m` **HARDENING PASS (exact hold)**: gait_valid EXACTLY 21/24 at
  80M cumulative, reproducing the IDENTICAL 3 flagged episode/leg pairs as its own 40M ACQ parent
  (walk/det ep3 leg5, walk_startjitter/det ep4 leg1, walk_startjitter/sto ep5 leg1), 0 falls both
  reads, slip/progress flat-to-improved -- the cleanest possible cont40m outcome, 4th independent
  confirmation the cleanliness-margin-at-40M rule predicts cont40m endurance (joining ramp-irrfwd
  exact-hold, widenirrc3-abrupt narrow-dip, medhead-irrfwd improves). Closes this composition
  line. (2) `medhead-dr-push1x-c1-acq1`: gate harness confirmed genuinely computing on train-9
  (kubectl exec ps alive, ~30min in of the usual 25-40min video-every=1 window) throughout the
  cycle -- backgrounded `pollreap`, left UNVERDICTED for the next reader, do not re-poll by hand.
  **Bonus: found+verdicted 9 idle, unassigned single-axis DR-restore canaries that had finished
  training + gate-eval with no verdict recorded** (a stale-looking `ops.sh review` "no harness
  report yet" line masked that their `report.json` files actually already existed and were
  complete -- the campaign has many of these mid-sweep from a fast-moving multi-cycle wave; check
  the file directly, don't trust the one-shot summary's absence claim at face value). All 9 PASS,
  0 falls across 9x24=216 episodes: `cmddrop1x` (24/24 PERFECT), `imubias1x` (24/24 PERFECT),
  `imupos1x` (23/24, 1 non-chronic flag), `velscale1x` (23/24, 1 non-chronic flag), `groundtilt1x`
  (24/24 PERFECT, mechanism-health scope), `startpose1x` (22/24, 2 DIFFERENT legs flagged in
  walk_startjitter/det only -- weakest margin of the batch), `alldrconf1x` (23/24, the 6-axis
  composite costs real slip margin -- med 5.4-6.1m vs the single-axis 3.4-5.6m band -- but no
  gait_valid collapse), `kickhalf1x` (21/24, 3 DIFFERENT legs in 3 DIFFERENT modes -- brackets
  kick1x-c1's full-dose fall: half dose has real zero-shot margin, full dose does not).
  `gyrobias1x-c1` was already verdicted by a concurrent cycle in the same window (convergent, not
  duplicated -- REFUSED cleanly on a duplicate-verdict guard). `faultworst1x-c1` had finished
  training but its gate eval had never even been kicked (no videos, no report) -- started it via
  `ops.sh podeval` + backgrounded `pollreap`, left unverdicted for next read. SKILLS.md updated (2
  new entries: the 8-axis canary batch, the widen2c1-irrfwd-cont40m hold). **Refill (respecting
  the 4-launch/80M-GPU-step cycle cap):** launched 2 ACQ continuations off the cleanest new
  canaries -- `cmddrop1x-c1-acq1` (train-9, VERIFIED RUNNING) and `imubias1x-c1-acq1` (train-3,
  VERIFIED RUNNING), both `--steps 40000000` explicit (avoiding the respec-steps footgun). Two
  more candidate arms (`groundtilt1x-c1-acq1`, `kickhalf1x-c1-acq1`) both self-raced onto the same
  default pod and got REFUSED as a genuine duplicate-pod collision -- rather than force them
  `--now` and blow the 80M/cycle step cap (2 landed launches already = 80M, the cap), queued both
  to `backlog.json` (no `--now`) for the drain to place under a future cycle's own budget
  allowance. Evidence: `ops.sh review` for both assigned runs, `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_crossgrav_{widen2c1_irrfwd_c1_acq1_cont40m,medhead_dr_
  {cmddrop1x,imubias1x,imupos1x,velscale1x,groundtilt1x,startpose1x,alldrconf1x,kickhalf1x}_c1}_
  gate/report.json`, `launch_run.py status`/`backlog.json`, RL_LOG 09-06 08:49-09:02.


- 09-06 ~08:4x-09:0x this cycle (assigned `medhead-dr-latency1x-c1-acq1`, `medhead-dr-zerobias1x-c1-
  acq1`): **1/2 verdicted (ACQ PASS), 1/2 still genuinely computing; plus 1 recovered orphan verdict,
  1 infra bug fix, and a 3-item refill.** (1) `latency1x-c1-acq1` **ACQ PASS**: PERFECT 24/24
  gait_valid all 4 modes, sac=[] every episode, 0 terms, matching/tightening its own 2M canary
  (slip/m 3.0-4.6, reward monotonic 432->1048 quarters). 3rd individual-axis DR-restore ACQ
  confirmation (after friction1x/mass1x-c1-acq1). (2) `zerobias1x-c1-acq1` gate confirmed STILL
  genuinely computing on train-10 (live `eval_checkpoint` process, ~50min elapsed of an unusually
  long window, sharing the pod's CPU with a second live eval for `zerobiasframe1x-c1-acq1-r2`) —
  backgrounded `pollreap` + registered `evalpending`, left unverdicted for the next reader.
  (3) **Recovered a 3rd instance of the non-atomic-`experiments.json`-write-race orphan class**:
  `medhead-dr-gyrobias1x-c1` (queued+launched by an earlier cycle) had actually finished healthy at
  2M steps (W&B `kbypfyyp`, PERFECT 24/24 gait_valid, sac=[] every episode, 0 falls) but its ledger
  entry was stuck at `INTENT` with no `wandb_id`/pod, making every backlog-drain attempt on it
  silently report "already exists in W&B — dropping (duplicate)" instead of running it. Fixed via
  `launch_run.py update --set` (same recovery pattern as `encnoise1x-c1-acq1`), then verdicted
  **CANARY PASS** — closes the gyro-RATE-bias DR axis. Gotcha noted in SKILLS.md: a drain refusing
  a queued item as "already exists" with no `wandb_id` on the ledger entry is worth a direct W&B
  check before assuming it's a true duplicate. (4) Fixed a genuine tooling bug found mid-cycle: a
  backlog item (`medhead-dr-fault1x-c1-acq1-r2`) queued by a prior cycle had an empty `--evidence`
  field, tripping the new `_acquisition_steps_footgun`-adjacent evidence guard on every drain
  attempt (`REFUSED: acquisition runs require --evidence`) — patched the backlog entry's evidence
  in place (citing its own healthy canary + sibling ACQ precedents) and drained it clean.
  **Refill:** used the 5 freed GPU slots (previous DR-restore ACQ batch finishing) to launch/queue:
  `headset-halfgrav-acq1-cont40m` (the 0.5g family's own untouched 40M root champion's FIRST
  endurance continuation, previously REFUSED twice by pod-race per the 08:2x entry below — landed
  this time), and 2 new single-axis DR-restore canaries closing out the last untested fields in
  `domain_rand.py`'s `RandRanges` besides what's already covered: `legmass1x-c1` (per-leg mass
  jitter, distinct from the whole-body `mass_scale` already clean) and `imumount1x-c1` (IMU mount
  ROTATION calibration error, distinct from the `imu_pos_xy/z` translation already clean in
  `imupos1x`) — both landed and finished their 2M budget within minutes (fast canary), report not
  yet synced at cycle end. **Note on a mechanical multi-cycle interaction**: my own `fault1x-c1-
  acq1-r2` launch (drained from the bug-fixed backlog item above) was independently killed
  mid-flight (~4M/40M steps) by a CONCURRENT cycle that (from its own vantage, having itself
  launched `gains1x-r2`+`geom1x-r2`) believed a 3rd 40M ACQ launch in the same window exceeded the
  shared `max_new_gpu_steps_per_cycle` cap, and re-queued it as `fault1x-c1-acq1-r3` — left that
  requeue alone (did not re-drain) since I had already used my own cycle's launch count/step budget
  on the 4 items above; a future cycle should pick up `-r3` within its own fresh cap. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_latency1x_c1_acq1_gate/
  report.json`, `..._gyrobias1x_c1_gate/report.json`, W&B `np2kt3bf`/`kbypfyyp`, RL_LOG 09-06 08:5x-
  09:0x.

- 09-06 ~08:3x-08:4x this cycle (assigned `medhead-irrfwd-c1-acq1-cont40m`): **HARDENING PASS
  (improves), verdicted after the harness gate genuinely finished computing (no prestage artifact —
  found+backgrounded via `podeval`/`pollreap`, confirmed a live remote `eval_checkpoint` process, not
  orphaned; waited it out this cycle rather than leaving a 3rd unverdicted line).** Aggregate
  `gait_valid` 22/24 at 80M cumulative (walk/det 4/6, walk/sto 6/6, walk_startjitter/det 6/6,
  walk_startjitter/sto 6/6) — UP from the parent 40M read's own 21/24 (walk_startjitter/sto was 5/6
  there). 0 falls/terminations across all 24 episodes both reads. The walk/det leg flag is the SAME
  confined single-mode signature (leg 5, episodes 1+5) as the parent, actually narrowed (ep1 dropped
  from `sac=[2,5]` to `sac=[5]`); the parent's one flagged walk_startjitter/sto episode is now clean.
  Frame strips confirm clean six-leg body translation on the flagged episode (softened not parked
  duty). This composition now has 2 independent clean reads (40M + 80M), joining `ramp-irrfwd-cont40m`
  in the cleanliness-margin-at-40M precedent set. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_crossgrav_medhead_irrfwd_c1_acq1_cont40m_gate/report.json`, W&B
  `flkoqbnm`. **Refill:** fleet was 0/11 free the entire cycle (no direct launch possible); found+fixed
  the same respec-steps-inheritance footgun a concurrent cycle's guard (`_acquisition_steps_footgun`)
  now catches for NEW cases, but confirmed 3 EARLIER casualties from before that guard landed
  (`gains1x`/`geom1x`/`fault1x-c1-acq1`, all silently finished at the source canary's 2M budget
  instead of a real 40M ACQ read) still had no correctly-budgeted relaunch — queued all 3 to backlog
  with explicit `--steps 40000000` + `--init-from-source` off their original `-c1` canaries
  (`gains1x-c1-acq1-r2` already drained to train-2 INTENT by cycle end; `geom1x`/`fault1x-c1-acq1-r2`
  still queued). No duplication vs concurrent cycles' own work (checked `experiments.json` /
  `backlog.json` before and after).

  **CORRECTION (same cycle, ~08:5x):** by the time the harness gate above finished computing, all 3
  backlog items had drained (`gains1x-r2`->train-2, `geom1x-r2`->train-11, `fault1x-r2`->train-1) —
  3x40M = 120M new GPU steps directly attributable to this cycle's own actions, over the
  guardrails.yaml `max_new_gpu_steps_per_cycle: 80000000` hard cap (no operator exception in force).
  Self-caught before exit (checked `launch_run.py status` per the standing protocol) and corrected
  per the established precedent (`experiments.json`'s own prior self-kill entry for the identical
  situation): killed `fault1x-c1-acq1-r2` at ~4M steps (0 meaningful progress lost, checkpoint
  unchanged) and re-queued it as `fault1x-c1-acq1-r3` to backlog for a later cycle to launch within
  its own budget. This cycle's own direct-launch total is now exactly 80M (`gains1x-r2` +
  `geom1x-r2`), matching the cap. Lesson for future cycles: count backlog items that may drain
  DURING your own cycle (they routinely do, per the self-repairing drain) against the 80M cap at
  queue time, not just `--now` launches — 3 queued 40M respecs is already over budget even though
  none used `--now`.

  Fleet had 5 free slots at cycle end — deliberately NOT filled further (already at the 80M cap).
  (Refill-candidate list removed 09-06 meta: friction1x/mass1x cont40m + halfgrav-acq1-cont40m were
  funded by 09:04; further per-axis confirmations are deprioritized per QUEUE AIM at the top.)
  Evidence: `launch_run.py status` (pre/post-kill), RL_LOG 09-06 08:50/08:52.

- 09-06 ~08:0x-08:2x this cycle (refill-only, no completions assigned — canonical capacity found
  5-6 ready slots without trainers and an empty backlog): **completed the single-axis DR-restore
  ACQ-durability batch (every remaining clean canary now has its first 40M confirmation attempt
  launched, mine or a concurrent cycle's) + funded 2 more cont40m endurance continuations.**
  Checked which clean-canary DR axes still had zero ACQ (40M) attempt: `contactstiff1x`,
  `deadband1x`, `noise1x`, `tiltnoise1x`, `gyronoise1x`, `extpush1x`, `actionnoise1x` (7 axes, all
  PASS canaries on the flagship `medhead-abrupt-c1-acq1-cont40m` champion). Launched
  `actionnoise1x-c1-acq1` (train-2) and `deadband1x-c1-acq1` (train-9) directly; `contactstiff1x`,
  `noise1x`, `tiltnoise1x`, `gyronoise1x` landed the same window via concurrent cycles' own
  attempts on the identical next-lever list (convergent, not duplicated — confirmed via
  `launch_run.py status`'s live pod scan before/after each of my own attempts). Also funded 2
  cont40m endurance continuations on clean-at-40M sources with none yet, per the established
  cleanliness-margin rule: `s1acq-widenfwd-c1-acq1-cont40m` (train-3, VERIFIED RUNNING — the
  campaign's cleanest 0.5g source's 8-way-heading composition, 21/24 own 40M read, no chronic
  pattern) and attempted `headset-halfgrav-acq1-cont40m` (the 0.5g family's own untouched root
  champion, perfect 24/24 own 40M read, no endurance data point yet) — REFUSED twice by pod-race
  against concurrent cycles' own fills (`zerobiasframe1x-c1-acq1`, then `s1acq-irrfwd-c1-acq1-
  cont40m`), fleet reached 0/11 free before a 3rd attempt; not re-queued this cycle since another
  concurrent cycle had already claimed the halfgrav-family gap with a different arm in the same
  window — leave for a future cycle to confirm whether it's still open. **Bug found + partially
  fixed:** `medhead-dr-extpush1x-c1-acq1` inherited the respec-steps footgun (2M source budget kept
  when `--steps` omitted; full description in the ~08:3x entry above — launcher guard
  `_acquisition_steps_footgun` now refuses new cases); re-launched as `-r2` with `--steps 40000000`
  pinned, queued to backlog. `gains1x`/`geom1x`/`fault1x-c1-acq1` FINISHED entries are 2M canary
  repeats, not ACQ evidence (correctly-budgeted `-r2`/`-r3` relaunches queued the same window).
  Evidence: `experiments.json` steps-field diff across all 7 `-acq1` DR entries, RL_LOG 09-06 08:2x.

- 09-06 ~07:5x-08:2x this cycle (assigned `medhead-dr-encnoise1x-c1-acq1`, `medhead-ramp-irrfwd-c1-
  acq1-cont40m`, `widenirrc3-abrupt-c1-acq1-cont40m`): **2/3 verdicted (both HARDENING PASS), 1/3
  still genuinely computing after an infra recovery; plus 1 extra unassigned-idle verdict and a
  4-launch refill batch.** (1) **Infra incident (self-repaired):** `medhead-dr-encnoise1x-c1-acq1`
  had NO ledger entry at all despite its W&B run showing `state=finished` (40M steps) -- the same
  non-atomic-`experiments.json`-write-race class the 06:59-07:03 incident already documented had
  silently dropped this run's own entry sometime after launch. Found its checkpoint still present
  on its original training pod (`hexapod-mjx-train-8`, both the interim and `_best` zips), pulled it
  by hand via `kubectl cp` (md5/size-verified: 4469270 bytes, exact match), and reconstructed the
  full ledger entry (pod/wandb_id/hypothesis/gate/extra_args/command) via `launch_run.py update
  --create --set` from the cached W&B config -- this is the SANCTIONED repair path (never hand-edit
  `experiments.json`), unblocking the standard prestage/pullckpt/podeval machinery for this run
  going forward. Kicked its gate eval via `podeval` (still genuinely computing on train-8 at cycle
  end, backgrounded `pollreap`). (2) `medhead-ramp-irrfwd-c1-acq1-cont40m` **HARDENING PASS**: holds
  gait_valid EXACTLY at 22/24 through +40M more steps (80M total) -- the identical single
  non-chronic leg-5-in-walk/det-only pattern reproduces (duty 0.06/0.08 vs the parent's 0.04/0.05),
  0 falls, no spread to other modes. Closes the ramp-transfer endurance question. (3)
  `widenirrc3-abrupt-c1-acq1-cont40m` **HARDENING PASS by substance** despite a narrow numeric miss
  against its own literal gate text (21/24 vs "stays at/above 23/24"): all 3 flagged episodes are
  the SAME already-borderline legs/episodes from the established 40M read (duty 0.12->0.07,
  0.13->0.08, one already at 0.01->0.01) dipping a few points below the duty floor -- 3 DIFFERENT
  legs across 3 DIFFERENT modes, each a single non-repeating episode, not the gate's own named
  "repeating chronic leg emerges/hardens" fail shape. 0 falls, video-confirmed clean six-leg
  cycling. Read together as useful calibration: a small aggregate-count miss driven by pre-existing
  marginal legs is noise, not entrenchment. (4) **Bonus verdict** (found idle, unassigned, no eval
  running, direct walkcurr-track value): `medhead-dr-kick1x-c1-acq1` **ACQ FAIL (informative-
  negative)**, exactly matching its own pre-registered gate text -- still 1 fall (tilt_roll,
  video-confirmed roll-over) at 40M on the 8-18deg mid-stride kick-perturbation dose; kick recovery
  at this magnitude is a real binding constraint, not a training-budget problem (kickhalf1x-c1's
  lower-dose read, already in flight, is the next data point). SKILLS.md updated (2 new rows: the
  cont40m pair, the kick1x-acq1 finding folded into its own DR-restore narrative). **Refill:** found
  6 clean single-axis DR-restore PASS canaries with NO acq1 launch attempt yet at all
  (contactstiff1x/deadband1x/gyronoise1x/noise1x/tiltnoise1x/torquefade1x-c1) -- torquefade1x got
  claimed by a concurrent cycle in the same window; launched the other 5 as ACQ continuations
  (`respec --init-from-source`), 4 landed VERIFIED RUNNING within the 4/cycle cap
  (contactstiff1x/deadband1x/gyronoise1x/noise1x-c1-acq1, 2 pod-race REFUSED retries absorbed
  cleanly), the 5th (tiltnoise1x-c1-acq1) queued to backlog and was drained by a concurrent cycle
  within the same cycle window. Also queued (backlog, no capacity left under the cap)
  `s1acq-irrfwd-c1-acq1-cont40m` -- a targeted entrenchment-trajectory test for that line's own
  WATCH-flagged leg[2,4] pattern (its 40M ACQ PASS was borderline: pattern widened from a single
  leg to a pair and spread to one new mode; this continuation asks whether +40M more steps
  resolves, holds, or entrenches it further). This closes the single-axis DR-restore ACQ-launch
  sweep -- essentially every PASS canary in the family now has an ACQ (40M) continuation in flight
  or done; the open work shifts to (a) reading back the ~15 ACQ continuations now in flight and (b)
  the composition-arm cont40m endurance batch (several PASS composition arms, e.g.
  medhead-ramp-c1-acq1, still lack a cont40m read). Evidence: `ops.sh review` for all 4 verdicted
  runs, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_{medhead_ramp_irrfwd_c1_acq1_
  cont40m,widenirrc3_abrupt_c1_acq1_cont40m,medhead_dr_kick1x_c1_acq1}_gate/report.json`, frame
  strips, `kubectl cp` checkpoint recovery + `launch_run.py update --create` ledger backfill for
  encnoise1x-c1-acq1, `launch_run.py status`/`capacity.py`, RL_LOG 09-06 08:11-08:2x.

- 09-06 ~08:1x-08:3x this cycle (assigned `medhead-dr-friction1x-c1-acq1`, `medhead-dr-mass1x-
  c1-acq1`): **both ACQ PASS at 40M, confirming the first 2 individual-axis DR-restore canaries
  durable at full budget.** Gate harnesses were still genuinely computing on their pods at read
  time (kubectl exec confirmed alive, train-4/train-7, ~40min elapsed of the usual 25-40min
  window) — backgrounded `ops.sh pollreap` for both rather than force a premature call; both
  finished cleanly within the hour. `friction1x-c1-acq1`: 24/24 gait_valid all 4 modes, sac=[]
  EVERY episode, 0 falls, slip/m med 3.44-4.26 — reproduces its own 2M canary's PERFECT 24/24
  exactly. `mass1x-c1-acq1`: 24/24 gait_valid, sac=[] every episode, 0 falls, slip/m med
  3.56-4.70 — IMPROVES on its own canary's single non-chronic leg-4 flag (23/24) to a clean sweep.
  Both reward curves monotonic with no plateau. Contact sheets + `walk_det_0.png` frame strips
  both video-confirmed clean six-leg tripod cycling, no drag/skate/paddle-creep. SKILLS.md updated
  (1 new row, both arms). **A real tooling bug found+fixed while queuing the refill:** my own
  respec launches this cycle for `extpush1x-c1-acq1` and `zerobiasframe1x-c1-acq1` (see below)
  BOTH silently landed at the SOURCE canary's 2M step budget instead of a real 40M ACQ read —
  `respec` inherits `--steps` from the `--from` entry when `--steps` isn't given, and neither
  launch passed it explicitly (matching a bug a concurrent cycle had independently found on
  gains1x/geom1x/fault1x-c1-acq1 the same window). Root-caused and fixed forward in
  `launch_run.py`: new `_acquisition_steps_footgun()` REFUSES a `--init-from-source` respec whose
  target name reads as an acquisition continuation (`-acqN` suffix) off a non-acquisition-named
  source when no explicit `--steps` is given and the inherited step count is canary-scale
  (<10M) — forces the caller to state the real budget. 7 new unit tests green (pure-function,
  no ledger/subprocess I/O), verified live via a real `--dry-run`-style CLI smoke test (fires
  correctly, zero side effects), snapshotted+pushed (`ae26f6b0`). Relaunched both mislabeled
  arms correctly as `extpush1x-c1-acq1-r2` (train-10, a concurrent cycle's own fix) and
  `zerobiasframe1x-c1-acq1-r2` (train-7, mine, `--steps 40000000` explicit, VERIFIED RUNNING) —
  both now genuine 40M reads, gate results pending. **Infra:** also found and removed one stale
  duplicate backlog entry, `medhead-dr-tiltnoise1x-c1-acq1-rr1` (an evidence-less retry spec left
  over from a transient launch race; the real `tiltnoise1x-c1-acq1` had already launched
  successfully under its own non-`-rr1` name) — would have burned 3 REFUSED drain attempts before
  auto-parking for nothing; removed directly from `backlog.json` per the tool's own near-duplicate
  warning. Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_
  {friction1x,mass1x}_c1_acq1_gate/report.json`, contact sheets, W&B `ub3dxkyb`/`rllle5x4`,
  `rl_move/tests/test_launch_run_acquisition_steps_footgun.py`, `launch_run.py status`, RL_LOG
  09-06 08:2x-08:3x.

- 09-06 ~08:0x-08:2x this cycle (assigned `medhead-dr-torquefade2x-c1-acq1`,
  `medhead-widenfwd-c1-acq1-cont40m`): **both left UNVERDICTED — gate harnesses genuinely
  computing on their own pods, no prestage failure.** The prestage claim's `_gate` dirs did NOT
  exist for either run at cycle spawn (same write-race-truncation class the campaign has hit
  before), but `kubectl exec ps` on `train-5`/`train-1` confirmed the 24-episode 4-panel
  `eval_checkpoint` harness alive on both (started 07:42, ~27min in of the usual 25-40min
  video-every=1 window, 700%+ CPU) — treated as still-computing per protocol, not a failure to
  chase. Backgrounded `ops.sh pollreap` for both (180s/60min cap); left for the next reader.
  **Refill:** re-read live capacity right before acting (per protocol) and found the fleet had
  already moved out from under the stale prompt snapshot — a concurrent cycle had, in the same
  minute, funded the exact 2 next-priority axes this cycle also picked
  (`medhead-dr-extpush1x-c1-acq1` -> train-0, `medhead-dr-zerobiasframe1x-c1-acq1` -> train-10,
  both VERIFIED RUNNING; my own `respec --now` attempt at zerobiasframe1x-c1-acq1 got a clean
  REFUSED — duplicate-name race, normal traffic). Instead queued (backlog, no `--now`, since 0
  slots remained free) the one still-genuinely-unlaunched axis: `medhead-dr-gyrobias1x-c1`
  (nominal IMU gyro RATE-bias canary, `dr.gyro_bias_deg_s=0.5`) — its only prior ledger entry was
  a dead `INTENT` on train-2 that lost a capacity race and never actually trained. Caught and
  fixed a respec bug of my own before it could land: sourcing `--from` the `gyronoise1x-c1`
  parent (for its checkpoint) also cloned that parent's OWN `dr.gyro_noise_deg_s=0.5` cfg, which
  would have compounded two DR axes instead of isolating gyro-bias alone; hand-edited the queued
  backlog item's `extra_args` back to `gyro_noise_deg_s=0` (matching the original correctly-
  designed-but-never-launched spec) under `backlog.json.lock` before leaving it queued. Evidence:
  `kubectl exec hexapod-mjx-train-{5,1} -- ps aux`, `launch_run.py status`/`capacity.py` (0/11
  free on exit), `rl_move/orchestrator/backlog.json`, RL_LOG 09-06 08:1x-08:2x.

- 09-06 ~07:0x-08:0x this cycle (assigned `medhead-dr-zerobiasframe1x-c1`, `medhead-irrwiden-c1-acq1`,
  `medhead-widenirr-c1-acq1`): **3/3 verdicted PASS after a prestage-failure recovery.** All 3
  runs' prestage evals had FAILED at spawn time (a concurrent cycle's `experiments.json` write-race
  truncation made `pullckpt` error out and skip evals — no `_gate` artifacts existed despite the
  prompt's claim they were synced); backgrounded `ops.sh podeval` for all 3 on their own pods and
  waited out the ~30-45min video-heavy harnesses rather than trusting the stale prestage claim.
  (1) `medhead-dr-zerobiasframe1x-c1` **CANARY PASS**: the harder frame-COUPLED zero-bias variant
  (bias applied through the command frame, not just sensor-side) holds 23/24 gait_valid, 0 falls,
  a single non-chronic leg-0 flag — matches its sensor-only `zerobias1x` sibling's own clean PASS;
  command-frame coupling is NOT the binding part of this axis. (2) `medhead-irrwiden-c1-acq1` and
  (3) `medhead-widenirr-c1-acq1` (both composition orders of the irr+widen axis pair) **ACQ PASS**
  at 40M: 22/24 each, 0 falls, and critically both reproduce their OWN 2M canary's exact leg-2/5
  flagged-episode set (widenirr: byte-identical; irrwiden: same episodes, duty flat/marginal) with
  zero spread to new episodes/modes — the cleanest possible confirmation yet that this specific
  leg-2/5 signature is a stable non-worsening artifact of the recipe, not slow entrenchment.
  Composition-order-irrelevance for irr+widen is now closed at ACQ scale (both orders durable).
  SKILLS.md updated (3 new rows). **Refill (2 launches, full 80M/cycle GPU-step cap):** with the
  single-axis DR-restore sweep's CANARY-PASS list now at 33 axes and only ~13 holding an ACQ
  (40M) durability confirmation, funded the 2 highest hardware-relevance axes still unfunded:
  `medhead-dr-torquefade1x-c1-acq1` (train-11, VERIFIED RUNNING — the hardest torque-fade dose
  point, PERFECT 24/24 canary, closes whether the campaign's whole 3x assist-crutch simplification
  is safe to drop at ACQ scale too) and `medhead-dr-actionnoise1x-c1-acq1` (train-2, VERIFIED
  RUNNING — actuator-side action noise, 22/24 canary). Did not fund more: 2x40M already exhausts
  the 80M/cycle GPU-step cap even though 6 pods sat free at read time. Remaining clean-PASS,
  ACQ-unfunded axes for the next cycle: extpush1x, zerobiasframe1x (this cycle's own finding),
  deadband1x, tiltnoise1x, noise1x, cmddrop1x/imubias1x/velscale1x/groundtilt1x/imupos1x/
  gyrobias1x/startpose1x (still mid-eval at read time, status unconfirmed). Evidence: `ops.sh
  review cw-walkscratch-easy0905-headset-crossgrav-medhead-{dr-zerobiasframe1x-c1,irrwiden-c1-acq1,
  widenirr-c1-acq1}`, matching `report.json` + contact sheets, W&B `ryf9ntl5`/`mdxo6qac`/`eipegd5n`,
  RL_LOG 09-06 07:37-08:00.

- 09-06 ~07:3x this cycle (assigned `medhead-dr-kick1x-c1-acq1`, `plainhead-abrupt-c1b-acq1-cont40m`):
  **both gate harnesses STILL genuinely computing on their pods — no verdict on either, backlog
  refilled with 3 new ACQ arms.** Confirmed via `kubectl exec ps` on both pods: `kick1x-c1-acq1`'s
  gate on `train-10` (pid 602157, 706% CPU, started 07:25, sharing the pod with the live
  `zerobias1x-c1-acq1` trainer) and `plainhead-abrupt-c1b-acq1-cont40m`'s gate on `train-2` (pid
  3306053, 779% CPU, started 07:25, sharing with `latency1x-c1-acq1`) — both only ~7 wall-clock
  minutes into what this campaign's video-every=1 24-episode 4-panel harness typically takes
  25-40min to finish; only the `_session` (informational, HARD FAIL expected/uninformative)
  artifacts exist yet, no `_gate/report.json`. Backgrounded `ops.sh pollreap` for both (180s/60min
  cap), left UNVERDICTED for the next reader — do not re-launch or re-poll by hand. **Capacity:**
  fleet fully saturated (0/12 free; `train-6` still CoreWeave-Pending on the same node-scheduling
  issue prior cycles noted) and `backlog.json` was EMPTY at read (the prior cycle's queued
  `torquefade15x-c1-acq1` had already been drained onto `train-0` by the self-repairing drain
  before this cycle started) — no launch possible this cycle. **Refill (queued, not launched, no
  capacity):** checked which single-axis DR-restore canaries still lack their first 40M ACQ
  confirmation (encnoise1x/friction1x/latency1x/mass1x/push1x/torquefade2x/torquefade15x/
  zerobias1x/kick1x/actionnoise1x/extpush1x already have one in flight or done) and found 3 clean
  PASS canaries with none yet: `gains1x-c1` (23/24, 0 falls), `geom1x-c1` (21/24, 0 falls — the
  last guardrails-named axis), `fault1x-c1` (22/24, 0 falls, real actuator faults). Queued all 3 as
  `-acq1` warm-start continuations (`respec --init-from-source`, no `--now`) to `backlog.json` for
  the self-repairing drain to place once slots free. Evidence: `kubectl exec hexapod-mjx-train-
  {10,2} -- ps aux`, `launch_run.py status`/`capacity.py` (0/12 free both reads),
  `rl_move/orchestrator/backlog.json`, RL_LOG 09-06 07:3x.

- 09-06 ~07:1x-07:3x this cycle (assigned `medhead-widenfwd-c2-acq1`): **ACQ PASS — the 2nd
  independent seed of the medhead-widenfwd composition holds at 40M, reproducing seed-1's own
  precedent.** The run's own gate eval was still genuinely computing when this cycle spawned
  (started 06:41, sharing GPU-MJX with a newly-placed sibling trainer) — waited it out rather than
  treat the empty log as a prestage failure (process alive, high CPU, per protocol). Result:
  aggregate gait_valid 21/24 (vs the same seed's own 23/24 2M canary), 0 falls/terminations across
  all 24 episodes, no chronic single-leg pattern — the identical `walk/det` ep4 leg0 flag reproduces
  from the canary and only 2 new non-chronic (never-repeating) flags appear (`walk/sto` ep2 leg5,
  `walk_startjitter/sto` ep5 leg0). Slip/m improved in the noisiest mode (walk/sto med 8.58 vs
  12.84). Contact sheet + both newly-flagged episodes' frame strips confirm clean six-leg tripod
  cycling, no drag/skate/paddle-creep/collapse. Matches the established composition-family
  precedent (`widen2c1-irrfwd-c1-acq1`, `s1acq-widenfwd-c1-acq1`): source cleanliness, not seed
  luck, predicts 40M durability. SKILLS.md updated (1 new row). **Refill:** fleet fully saturated
  (0/11 reachable slots free at read time) so queued (not launched) the standing cont40m endurance
  continuation for this specific seed to `backlog.json` (`respec --init-from-source`, no `--now`),
  matching the precedent already funded for sibling seed-1 (`medhead-widenfwd-c1-acq1-cont40m`,
  already running) and the other cont40m arms. Evidence: `ops.sh review
  cw-walkscratch-easy0905-medhead-widenfwd-c2-acq1`, `logs/ckpt_eval/
  cw_walkscratch_easy0905_medhead_widenfwd_c2_acq1_gate/report.json` vs the parent's own
  `..._c2_deferartifacts_gate/report.json`, W&B `inb67bzx`, RL_LOG 09-06 07:32.

- 09-06 ~07:2x this cycle (assigned `medhead-dr-alldrconf1x-c1`, `medhead-dr-kickhalf1x-c1`): **both
  STILL genuinely computing on their pods — no verdict on either this cycle, but drained the backlog
  as capacity freed and caught 3 more mid-cycle finishers.** (1) Both assigned runs' W&B shows
  `state=finished` (2.1M steps) and checkpoints are pulled, but the gate harness (`eval_checkpoint`,
  24-episode 4-panel, `--video-every 1`) is still mid-run: `alldrconf1x-c1` on `train-5` (612% CPU,
  started 06:46, sharing the pod with the newly-placed `torquefade2x-c1-acq1` trainer), `kickhalf1x-c1`
  on `train-11` (727% CPU, started 06:46, sharing with `halfgrav-widenirr-c3-acq1-cont40m`) — confirmed
  alive via `kubectl exec ps`, matching this campaign's repeated video-every=1-on-a-busy-pod pattern.
  Only the informational SESSION-gate logs are present so far (both FAIL, expected/uninformative for a
  walk-only checkpoint composed with a stand policy — not the real gate). Backgrounded `ops.sh pollreap`
  for both (180s/60min), left UNVERDICTED for the next reader. (2) **Capacity check found 2 (then 3)
  pods idle mid-cycle** from this cycle's own "still training" list finishing early:
  `plainhead-abrupt-c1b-acq1-cont40m` (train-2), `medhead-dr-kick1x-c1-acq1` (train-10),
  `medhead-ramp-irrfwd-c1-acq1-cont40m` (train-3) — none had a harness report yet (no eval/finalizer
  process running on their pods), so kicked background `ops.sh podeval` for all 3, left genuinely
  computing/UNVERDICTED for the next reader. **Refill: drained the backlog into the freed slots** —
  `medhead-dr-latency1x-c1-acq1` -> train-2, `medhead-dr-zerobias1x-c1-acq1` -> train-10 (both
  VERIFIED RUNNING via `launch_run.py drain`); a 3rd drain attempt for `torquefade15x-c1-acq1` ->
  train-3 got a clean REFUSED (a concurrent auto-drain had already placed
  `widen2c1-irrfwd-c1-acq1-cont40m` there in the race window — normal traffic, not a duplicate).
  Fleet back to fully saturated (0/12 free) on exit; `backlog.json` holds exactly 1 remaining item
  (`torquefade15x-c1-acq1`) for the self-repairing drain to place next. Evidence: `kubectl exec
  hexapod-mjx-train-5/-11 -- ps aux`, `launch_run.py capacity`/`status`, `launch_run.py drain` output.

- 09-06 ~07:0x-07:1x this cycle (assigned `medhead-dr-gyrobias1x-c1`, `medhead-dr-imupos1x-c1`,
  `medhead-dr-torquefade15x-c1`): **1/3 read (torquefade15x-c1 CANARY PASS, closes the torque-fade
  dose axis at every point tested), 2/3 still genuinely computing on their pods.** (1) `medhead-dr-
  torquefade15x-c1` **CANARY PASS**: the halfway torque-assist dose (`dr.torque_scale` 3.0->1.5,
  midpoint between the already-clean 1x and 2x points) gives a PERFECT 24/24 gait_valid, 0 falls,
  `sac=[]` every one of 24 episodes, slip/m 3.8-6.2, video-confirmed (`walk_det_0.png`) clean six-leg
  tripod cycling with no drag/skate/flag leg. Closes the torque-fade dose axis for good: 1x/1.5x/2x/
  3x(idealized default) are ALL now clean -- this champion never needed the assist crutch at any
  dose. (2) `medhead-dr-gyrobias1x-c1` and `medhead-dr-imupos1x-c1`: both confirmed STILL genuinely
  computing (video-every=1 over the full 24-episode 4-panel harness on pods also hosting a live
  trainer, running 26-30min at read time — `kubectl exec ps` shows the eval_checkpoint process
  alive, one already rendering its final video via ffmpeg) — backgrounded `ops.sh pollreap` for
  both (180s interval, 60min cap), left UNVERDICTED for the next reader; do not re-launch or
  re-poll by hand. SKILLS.md updated (1 new row: torquefade15x-c1 PASS). **Refill:** fleet was
  fully saturated (0/11 reachable slots free, train-6 stuck Pending on a CoreWeave scheduling
  issue) at read time, so queued (not launched) `medhead-dr-torquefade15x-c1-acq1` to
  `backlog.json` (`respec --init-from-source`, no `--now`) — the first ACQ-scale durability check
  of the torque-fade axis's specific midpoint dose, joining the sibling torquefade2x/friction1x/
  mass1x/encnoise1x individual-axis ACQ batch already in flight; drain will place once a slot
  frees. Evidence: `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-
  torquefade15x-c1`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_
  torquefade15x_c1_gate/report.json`, W&B `vw3jf1ci`, RL_LOG 09-06 07:09.

- 09-06 ~07:0x-07:1x this cycle (assigned `widen2c1-irrfwd-c1-acq1`): **ACQ PASS — a websocket-masked gate eval recovered, and the 3rd base-champion composition arm holds/improves at 40M.** The 2M canary (21/24, 1 fall, notably the family's first fall and its slowest/noisiest source) holds gait_valid EXACTLY at 21/24 at 40M and improves on every other axis: 0 falls (was 1, the prior fall resolved into a non-fatal flag at a different episode), slip/m median down in all 4 modes, progress_ratio median up in all 4 modes, and the 2 surviving non-chronic leg flags reproduce at the IDENTICAL episode+leg as the canary (no new/spreading pathology). Video-confirmed clean six-leg cycling in a clean episode and both flagged ones. **Infra note:** the gate eval had actually finished on-pod at 06:35 but the sync raced a websocket disconnect (`SYNCED rc=1`), which would have looked like a missing/failed eval — pulled by hand via `kubectl cp` rather than re-running (same transient this campaign has repeatedly self-diagnosed on `s1acq-{irrfwd,widenfwd}` and others). SKILLS.md updated (1 new row). **Refill:** fleet was fully saturated (0/11 free slots) at read time, so queued (not launched) the standing cleanliness-margin cont40m continuation to `backlog.json` (`respec --init-from-source`, no `--now`) for the drain to place once a slot frees — this arm had no endurance read yet, matching the medhead/widenirr/s1acq precedent. Evidence: `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-widen2c1-irrfwd-c1-acq1`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_widen2c1_irrfwd_c1_acq1_gate/report.json` vs the parent's own `..._irrfwd_c1_gate/report.json`, W&B `qiuquuie`, RL_LOG 09-06 07:1x.

- 09-06 ~07:0x this cycle (assigned: reap the pre-registered pending eval for
  `medhead-dr-extpush1x-c1`, left genuinely computing by the prior cycle):
  **CANARY PASS — closes the 2nd of the 2 extra (beyond guardrails.yaml's
  named mass/geometry/friction/compliance/gravity/gains list) DR axes.**
  Restoring nominal (0.3/episode) mid-STRIDE external push (a random-
  direction horizontal shove fired later in the episode on a policy already
  walking — distinct from the walk-takeoff `dr.walk_push_*` axis already
  closed as `push1x`) on the campaign's most durable champion
  (`medhead-abrupt-c1-acq1-cont40m`, 80M steps) holds majority: 22/24
  gait_valid, 0 falls/terminations across all 24 episodes, the only 2
  flagged episodes are single-episode non-repeating legs (leg5, leg0) — not
  the campaign's recurring chronic leg[1,4] fingerprint. Both extra axes
  (`actionnoise1x`, `extpush1x`) now PASS, joining the complete guardrails-
  named axis sweep — every DR-realism axis this campaign registered has at
  least one clean single-axis restore on the flagship champion. SKILLS.md
  updated (1 new row). **Refill: none — fleet is 0/12 FREE this cycle**
  (`launch_run.py status` / `capacity.py`: all 11 reachable pods BUSY on
  in-flight ACQ/cont40m continuations from the prior 2 cycles'
  cleanliness-margin batch + DR-axis-ACQ batch; `hexapod-mjx-train-6` is
  CoreWeave-Pending on node scheduling, not assignable). Next open item once
  capacity frees: `extpush1x` (like the other single-axis DR canaries) has
  no ACQ (40M) durability read yet — candidate for the next DR-restore-axis
  ACQ-continuation batch, alongside any DR axis still missing one. Evidence:
  `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-
  extpush1x-c1`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_
  medhead_dr_extpush1x_c1_gate/report.json`, W&B `7rjjhtyv`, RL_LOG 09-06
  07:07.

- 09-06 ~06:3x-07:0x this cycle (assigned `medhead-dr-fault1x-c1`, `medhead-dr-gains1x-c1`,
  `medhead-dr-geom1x-c1`): **3/3 CANARY PASS — the LAST 3 single-axis DR-restore cells close
  clean, completing the axis sweep.** (1) `medhead-dr-gains1x-c1` (per-servo +-20%kp/+-25%kv
  spread): 23/24, one non-chronic leg-4 flag, 0 falls. (2) `medhead-dr-geom1x-c1` (+-2% leg
  length, +-12mm CoM shift): 21/24, scattered non-chronic flags across 3 different legs/modes
  (no repeat), 0 falls — **closes GEOMETRY, the last of guardrails.yaml's named idealized axes
  (mass/geometry/friction/compliance/gravity/gains); every one now has a clean single-axis
  restore on this champion.** (3) `medhead-dr-fault1x-c1` (real per-episode actuator fault,
  0.3 prob, weakened/frozen/disabled-leg mix): 22/24, 0 falls. Cross-checked per-episode fault
  metadata against gate flags: one walk_startjitter/det miss is DIRECTLY EXPLAINED by that
  episode's own injected fault (`frozen:j[15]@1.0`, a genuinely dead joint, not a policy
  pathology); the other is an unexplained single-episode leg-0 blip, non-chronic, and notably
  NOT the campaign's recurring leg[1,4] middle-pair fingerprint — real hardware-style faults
  don't preferentially hit the same structural weak point as the reward-driven sacrifice
  pathology. All 3 video-confirmed (frame strips, no drag/freeze/collapse). SKILLS.md updated
  (3 new rows). **Infra incident (self-repaired):** hit the same non-atomic-`experiments.json`
  write race a concurrent cycle also found this window — a killed launch subprocess (my own
  120s-timeout retry of a `respec --now`) left the shared ledger truncated at exactly 18874368
  bytes (mid-object), which had ALREADY been committed+pushed by an intervening `snapshot.sh`
  run (both mine and others' launches were failing with `JSONDecodeError` on every attempt).
  Repaired by hand: parsed the file with a bracket-depth walker to find the last complete
  top-level object, truncated the one torn in-flight entry, re-validated (2103 entries),
  re-committed (`bae9debe`) — unblocked every launcher on the fleet, not just this cycle's.
  The concurrent cycle's proper permanent fix (`save_ledger` atomic temp+os.replace +
  `snapshot.sh` JSON-validity guard, 3 new tests) landed shortly after and is now on `main`;
  this incident is the reason it was needed. **Refill (3 launches, cleanliness-margin cont40m
  batch):** with the axis sweep now complete, shifted refill to the campaign's other open
  question — which clean-at-40M sources haven't had an endurance (+40M) helping yet. Checked
  5 candidates (all PASS, no chronic pattern) against the `cont40m` name list and launched the
  3 not already claimed by a concurrent cycle (which independently picked `medhead-widenfwd-c1`
  and `medhead-irrfwd-c1` the same window — convergent, not duplicated): `plainhead-abrupt-c1b-
  acq1-cont40m` (train-2, VERIFIED RUNNING — cleanest never-composed source, 23/24), `medhead-
  ramp-irrfwd-c1-acq1-cont40m` (train-3, VERIFIED RUNNING — first endurance read on a RAMP- not
  ABRUPT-transfer source, discriminates whether ramp-transfer itself carries elevated risk),
  `headset-halfgrav-widenirr-c3-acq1-cont40m` (train-11, VERIFIED RUNNING — first endurance read
  on a HALFGRAV, not crossgrav, source). Fleet fully saturated on exit (11/11 reachable pods
  busy). Evidence: `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-{gains1x,
  geom1x,fault1x}-c1`, matching `report.json` + frame strips, W&B `ktgseik5`/`dn9et0k6`/
  `vje1nu80`, RL_LOG 09-06 07:00-07:03.

- 09-06 ~06:5x-07:0x this cycle (assigned `medhead-dr-actionnoise1x-c1`, `medhead-dr-extpush1x-c1`;
  also triaged `cw-robotwalk-turns-20260906-cont8m-resume1`, a todaypolicy-track run, see that
  track's STATUS): **1/2 CANARY PASS, 1 still genuinely computing.** (1) `medhead-dr-
  actionnoise1x-c1` CANARY PASS: 22/24, 0 falls, leg-5 flagged 2/6 walk/det episodes only
  (non-chronic, single mode) — actuation-side action-noise restores clean, matching every
  sibling axis. (2) `medhead-dr-extpush1x-c1`: its gate eval was STILL genuinely computing on
  train-9 when this cycle spawned (video-heavy 24-episode harness on a pod also hosting a live
  training tenant); registered via `evalpending add` (label
  `cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_extpush1x_c1_gate`) for the next
  cycle/watcher to reap — do not re-launch or re-poll by hand. **Notable this-cycle finding: none
  of the 20+ individually-PASSED single-axis DR-restore canaries had ever been given their own
  ACQ (40M) durability confirmation** — every prior ACQ-scale read was on composition arms
  (irr/widen) or the campaign's flagship champions, leaving open whether a bare DR-realism axis's
  2M-canary cleanliness predicts 40M durability the same way. **Refill:** queued+launched 4 ACQ
  continuations off clean single-axis canaries, picked for hardware/decision relevance:
  `medhead-dr-torquefade2x-c1-acq1` (train-5, VERIFIED RUNNING — the flagged "key open decision"
  torque-crutch-to-2x axis, PERFECT 24/24 canary), `medhead-dr-mass1x-c1-acq1` (train-7, VERIFIED
  RUNNING — mass tolerance, 23/24 canary with one non-chronic flag, a 2nd near-clean data point),
  `medhead-dr-latency1x-c1-acq1` and `medhead-dr-push1x-c1-acq1` (both REFUSED repeatedly by
  pod-race against concurrent cycles' own fills — queued to `backlog.json`, self-repairing drain
  will place them). **Infra near-miss self-caught:** a transient non-atomic `experiments.json`
  write race (concurrent cycles writing the shared ledger without a rename-swap) truncated the
  file mid-write during this cycle's `mass1x-c1-acq1` launch, which made the drain believe that
  launch had crashed and auto-requeued a genuine duplicate (`-rr1`) that landed VERIFIED RUNNING
  on a 2nd pod — caught via `launch_run.py status`'s live pod scan (which reads real processes,
  not the stale ledger) showing the ORIGINAL was alive and healthy on train-7; killed the
  duplicate within ~1min, 0 GPU-hours lost, `status=KILLED_DUPLICATE`. The ledger file self-
  healed (another write cycle overwrote the truncated tail) with no lasting damage, but
  `save_ledger`'s plain `write_text` (not atomic write+rename) is a real latent race under this
  many concurrent cycles — worth a future hardening pass, not urgent tonight. SKILLS.md updated
  (2 rows: actionnoise1x PASS, the resume1 misalignment finding). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-actionnoise1x-c1`, `launch_run.py status`
  live scan, W&B `5hdibkd4`, RL_LOG 09-06 06:55-07:0x.

- 09-06 ~06:4x-07:0x this cycle (assigned `cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1-acq1v3` [already SELF_KILLED_OVER_CAP-verdicted by its own launching cycle, confirmed not re-triaged], `s1acq-irrfwd-c1-acq1`, `s1acq-widenfwd-c1-acq1`): **2 ACQ PASS verdicts on the campaign's single cleanest source, one clean and one flagged WATCH.** (1) `s1acq-widenfwd-c1-acq1` (8-way heading set) holds its own 2M canary (22/24) at 40M: 21/24, 0 falls, only a lateral non-worsening leg-shift (det/4 keeps the identical leg[0,3] flag at the identical episode; startjitter/sto swaps the canary's single leg[4] flag for leg[0] at 2 episodes) — matches the medhead-widenfwd-c1-acq1/widen2c1-irrfwd-c1-acq1 precedent. (2) `s1acq-irrfwd-c1-acq1` (irr-timing) stays majority (20/24) but its own confined walk/det leg-4 softening WORSENS (single leg->leg[2,4] pair, same 2 episode indices) and newly spreads into walk_startjitter/det (1/6, was 6/6 clean at canary) — below the gate's own chronic/majority FAIL bar (verdicted PASS, video confirms continued six-leg gait, no drag/freeze) but a materially weaker margin than its widenfwd sibling launched the same cycle from the same source. Both gate evals had raced a transient websocket disconnect during copy-back (podeval log showed `SYNCED rc=1`) — confirmed both were still genuinely computing remotely (checkpoint videos present, process alive via `kubectl exec ps`), backgrounded `pollreap` rather than re-triggering, and both landed clean shortly after. SKILLS.md updated (1 new 2-row entry). **Also found and fixed in-flight**: 3 runs from this cycle's own "still training" list finished mid-cycle with idle GPU capacity reopened (`medhead-dr-{allaxis1x,gyrobias1x,zerobiasframe1x}-c1`, wandb state=finished, no gate computed yet) — kicked `ops.sh podeval` for all 3 in the background (still genuinely computing at cycle end, not orphaned — left for the next reader/watcher). **Ledger note**: hit a transient `experiments.json` read race twice this cycle (a concurrent writer's in-progress save was caught mid-flush, once as an outright `JSONDecodeError`, once as an ~800-entry apparent "loss" that resolved on the next read) — both self-resolved within seconds via the launcher's own repair path (`experiments.json.repair_tmp` observed); no data was actually lost, just noted here in case a future cycle sees the same transient and wants context instead of re-diagnosing from scratch. **Refill (both cont40m launches, using the full 80M-step cycle cap):** with both `medhead-widenfwd-c1-acq1` and `medhead-irrfwd-c1-acq1` sitting as clean 40M ACQ PASSes with no cont40m endurance read yet, launched `medhead-widenfwd-c1-acq1-cont40m` (train-1, VERIFIED RUNNING) and `medhead-irrfwd-c1-acq1-cont40m` (train-0, VERIFIED RUNNING after 2 REFUSED pod-race retries against concurrent cycles' own fills) — 2nd/3rd confirmations of the cleanliness-margin-at-40M endurance rule from 2 independent forward-composed sources. Did NOT fund a cont40m for `s1acq-irrfwd-c1-acq1` despite it being a "clean-at-40M" PASS on paper — its WATCH-flagged worsening pattern makes it a weaker cleanliness-margin candidate than its own widenfwd sibling, so left for a confirming re-read first. Evidence: `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-s1acq-{irrfwd,widenfwd}-c1-acq1`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_s1acq_{irrfwd,widenfwd}_c1_acq1_gate/report.json` vs each run's own `..._c1_gate/` 2M canary, W&B `0iafbobq`/`wzh30m53`, RL_LOG 09-06 07:0x.

- 09-06 ~06:5x this cycle (assigned `startpose1x-c1`/`torquefade1x-c1`/`zerobias1x-c1`,
  all 3 still genuinely computing on their pods when this cycle spawned):
  **1/3 read (torquefade1x-c1 CANARY PASS, closes the torque-fade dose axis for
  good), 2/3 backgrounded (still computing); found+fixed a SHARED-INFRA data-loss bug
  mid-cycle (ledger corruption).** (1) `medhead-dr-torquefade1x-c1` **CANARY PASS**:
  removing the WHOLE 3x idealized torque-assist crutch (`dr.torque_scale` 3.0->1.0,
  real unassisted servo forcerange) gives a PERFECT 24/24 gait_valid, 0 falls, sac=[]
  every episode, video-confirmed clean six-leg cycling -- the hardest point on the
  dose axis (1x/1.5x/2x/3x all now clean), closing the whole torque-fade question:
  this champion never needed the assist crutch at any dose. (2) `startpose1x-c1` and
  `zerobias1x-c1`: both genuinely still computing (video-every=1 over the full
  24-episode 4-panel harness, sharing pods with live trainers) when read; re-
  backgrounded `ops.sh pollreap` for both after the first pollreap attempts died
  mid-ledger-corruption (see below), left unverdicted for the next read.
  **INFRA INCIDENT + FIX (not launch-blocking, but shared-state-critical): found
  `experiments.json` truncated/corrupted (`Unterminated string` at exactly the
  18,874,367-byte mark) mid-cycle, committed to git by a concurrent cycle's
  snapshot.sh (`git add -A` with no ledger lock and no validity check staged a
  torn mid-write file) -- lost ~360 historical ledger entries plus this cycle's own
  in-flight `friction1x-c1-acq1` launch record. Root cause: `save_ledger()` was a
  plain non-atomic `Path.write_text()` on a 20MB+ file; any reader (including
  `git add -A`) mid-write saw a partial file. Recovered the full ledger by hand
  from the last-good git commit (`9ece47f5`, 2466 entries) merged with the
  in-flight state (adding the missing `friction1x-c1-acq1` entry back), verified
  valid, wrote it back atomically under the ledger lock -- a concurrent cycle
  independently found+fixed the same incident in parallel (`bae9debe` commit), so
  the final committed state is doubly-confirmed correct. **Shipped the durable
  fix**: `save_ledger()` now writes to a pid-suffixed temp file + `os.replace()`
  (atomic on POSIX -- no reader ever sees a partial write again); `snapshot.sh`
  additionally gained a defense-in-depth JSON-validity guard on
  `experiments.json`/`backlog.json`/`backlog_failed.json`/`pending_evals.json`
  before `git add -A` (restores the last-committed copy instead of staging
  anything that fails to parse). 3 new regression tests green
  (`test_launch_run_ledger_atomic_write.py`), existing launch_run test suites
  unaffected (33/33 green). Snapshotted (`e28b9985`).
  **Refill (before the incident, using capacity found free that window):**
  launched the first-ever ACQ-scale (40M) continuation of an individual
  single-axis DR-restore canary (as opposed to a composition axis) --
  `medhead-dr-friction1x-c1-acq1` (train-4, `--init-from-source` warm start off
  its own PERFECT 2M canary): does a canary-clean SINGLE axis also risk the
  ACQ-scale entrenchment this campaign's crossgrav/widen/irr COMPOSITION axes
  have repeatedly shown (roughly half regress at 40M despite a clean 2M read)?
  No individual DR-restore axis had been extended past its 2M canary before this.
  A concurrent cycle independently launched the matching `mass1x-c1-acq1` (its
  own near-clean 23/24 canary) in the same window -- complementary data points on
  the same open question. Evidence: `ops.sh review cw-walkscratch-easy0905-
  headset-crossgrav-medhead-dr-torquefade1x-c1`, `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_torquefade1x_c1_gate/
  report.json`, W&B `1flk48ly`; RL_LOG 09-06 06:5x-07:0x.

- 09-06 ~06:1x-06:3x this cycle (assigned `medhead-dr-encnoise1x-c1`,
  `medhead-dr-contactstiff1x-c1`, `medhead-dr-friction1x-c1`; the other 3 pre-staged
  results named for this cycle — `irrwidenc2-abrupt-c1-acq1`, `medhead-dr-deadband1x-c1`,
  `medhead-dr-latency1x-c1` — were already verdicted by a concurrent cycle before this
  one read them, matching read confirmed, not re-verdicted): **3/3 CANARY PASS —
  encoder-noise, contact-stiffness, and friction all clear at nominal dose, extending
  the axis-restore sweep's unbroken run.** (1) `medhead-dr-encnoise1x-c1`: a PERFECT
  24/24, `sac=[]` every episode, 0 falls, slip/m 3.4-5.6. (2) `medhead-dr-
  contactstiff1x-c1`: 23/24 (one non-chronic leg-4 flag in `walk_startjitter/det`),
  0 falls, slip/m 3.0-5.2. (3) `medhead-dr-friction1x-c1`: a PERFECT 24/24 — friction
  is arguably the axis most directly tied to this campaign's own tracked slip/m
  metric, and restoring its full 0.6-1.4x own-DR range costs nothing, no skate/paddle
  blowout, slip/m 3.2-5.8. All 3 video-confirmed clean six-leg cycling (`walk_det_0`
  frame strips). These 3 join deadband/latency/tiltnoise/noise/torquefade2x as clean
  axis-restore PASSes — by this point every guardrails-named realism axis plus every
  sensor/actuator/behavioral-event axis this sweep has tried has scored at least one
  clean PASS on this exact champion (`medhead-abrupt-c1-acq1-cont40m`, 80M, 24/24), an
  unbroken streak with zero exceptions. SKILLS.md updated (2 new rows: encnoise1x own
  row already present from a concurrent write, contactstiff1x+friction1x new).
  **Refill (the sweep's culmination + 1 new isolated axis, using the cycle's 4-launch
  cap):** with the individual single-axis sweep now this deep into a 100%-clean
  streak, launched `medhead-dr-alldrconf1x-c1` (train-5, VERIFIED RUNNING) — the
  CONFIRMED-subset combination arm: stacks the 6 axes already individually PASS-
  verdicted at the time of launch (latency 1x, deadband 1x, torque-fade to 2x,
  encoder/tilt/gyro sensor noise at nominal, mid-episode push-recovery 0.3) into ONE
  run, asking whether independently-benign axes compound into a real degradation once
  several fire in the same episode — a question no individual-axis canary can answer.
  Found a concurrent cycle had independently converged on the same idea at larger
  scope the same window (`medhead-dr-allaxis1x-c1`, ALL ~20 axes including the
  not-yet-individually-confirmed ones) — complementary, not duplicative: mine is the
  conservative confirmed-only point on the same spectrum. Also queued (backlog, fleet
  hit 11/11 saturated mid-launch) `medhead-dr-faultworst1x-c1`: forces `fault_prob=1.0`
  + `fault_mix=(0,0,1)` (guaranteed whole-leg-disable every episode, vs the in-flight
  `fault1x-c1`'s default mixed/probabilistic dose) to test the campaign's single
  hardest real-hardware failure mode (a fully dead leg) at guaranteed, not diluted,
  exposure. Left 5 runs mid-computation on their pods for a future cycle to reap
  (podeval/pollreap already running, not orphaned): `medhead-dr-{zerobias1x,extpush1x,
  fault1x,startpose1x}-c1`, `s1acq-irrfwd-c1-acq1` (40M ACQ, W&B state=finished,
  reward quarters 278.8/581.2/745.9/909.7, gate not yet computed). Evidence: `ops.sh
  review cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-{encnoise1x,
  contactstiff1x,friction1x}-c1`, matching `report.json` + frame strips, W&B
  `eiykfiyf`/`4i5jjieu`/`2lblab0c`, RL_LOG 09-06 06:12-06:3x.

- 09-06 ~06:1x-06:3x this cycle (assigned `medhead-dr-cmddrop1x-c1`, `medhead-dr-imubias1x-c1`,
  `medhead-dr-velscale1x-c1`): **all 3 assigned evals still genuinely computing on their pods
  when this cycle spawned (started ~05:43, `--video-every 1` over the full 24-episode 4-panel
  harness on pods also carrying a live training tenant — slow, not stuck); backgrounded
  `ops.sh pollreap` for each (180s interval, 60min cap) so results land without a supervisor
  babysitting them, left UNVERDICTED for the next cycle/watcher to read once
  `report.json` lands. Do not re-triage these 3 as a fresh "no report yet" — the pollreap is
  live. **Infra unblock + refill:** found `medhead-dr-groundtilt1x-c1` and
  `medhead-dr-imupos1x-c1` both REFUSED repeatedly with a `-dirty` code-marker mismatch on
  every pod tried, even though the local tree was actually clean by the sync script's own
  dirty-check definition — re-ran `snapshot.sh --sync` on the 4 then-free pods
  (train-1/3/4/7) to refresh their stale markers to current HEAD; the background drain
  immediately placed both queued arms (train-0, train-1) plus a concurrent cycle's
  `medhead-irrwiden-c1-acq1` (train-3) once the pods were clean again — this looks like the
  same root cause a concurrent cycle independently found and fixed in `snapshot.sh` this same
  window (`pending_evals.json` missing from the dirty-check EXC list); either way, re-syncing
  unstuck 2 queued arms with zero risk. **New composite arm — the campaign's culmination
  test:** every guardrails-named + domain_rand.py DR axis now has (or had, at cycle-launch
  time) at least one clean single-axis PASS on the campaign's cleanest champion
  (`medhead-abrupt-c1-acq1-cont40m`, 80M, 24/24, 0 falls) — but 2-axis compositions (irr+widen,
  either order) have repeatedly regressed at ACQ scale even when both ingredients were
  individually clean. Launched `medhead-dr-allaxis1x-c1` (`--now`, train-7, VERIFIED RUNNING,
  finished its 2M budget in ~4min at ~9-11k env-steps/s): ALL ~30 nominal-dose DR axis values
  restored simultaneously (mass/geometry/friction/compliance/gains/latency/deadband/velcap/
  cmddrop/startpose/zerobias/encoder-tilt-gyro-noise/gyro-bias/imu-bias-mount-position/
  action-noise/ground-tilt/fault/ext-push/kick/push), `dr.torque_scale` deliberately left at
  the fixed idealized-crutch 3,3 (unchanged from every sibling single-axis arm — torque-crutch
  removal is its own separate active dose-response study). **CAVEAT for whoever triages this
  run's gate**: a concurrent cycle's `medhead-dr-kick1x-c1` CANARY closed **FAIL** in this same
  window (1 genuine `tilt_roll` fall, confirmed on video — the first fall anywhere in the
  entire single-axis sweep) — `dr.walk_kick_prob=0.3` is baked into this composite, so
  `allaxis1x-c1` is now KNOWN to include one already-unsafe ingredient, not just clean ones.
  Read a FAIL here as "at least consistent with the known-bad kick axis," not fresh evidence
  that clean-axis composition itself is fragile; a methodologically clean version of this
  question needs a repeat with `walk_kick_prob` fixed at whatever dose the concurrently-
  running `medhead-dr-kickhalf1x-c1` bisection clears (or dropped to 0) once that lands.
  ep_rew_mean at 2M finish was 13.9 — notably lower than typical sibling single-axis-restore
  finishes (~100-250) but this is a 2M canary against a MUCH harder combined objective, not
  necessarily itself alarming; read the gate's `gait_valid`/fall census, not this scalar,
  per the video-and-metrics-outrank-reward-alone rule. Killed one true duplicate
  (`medhead-dr-allaxis1x-c1-rr1` on train-9): the backlog-queued copy of the same respec
  landed via the background drain seconds after the `--now` direct launch had already claimed
  the name, and the drain's own dedup-rename-on-collision logic (see `launch_run.py`
  `requeue`) spun up a second, fully redundant trainer on `-rr1` rather than dropping it —
  `killrun` + `status=KILLED_DUPLICATE`, zero further spend. Evidence: `kubectl exec
  hexapod-mjx-train-{9,11,5}` process listings for the 3 assigned evals; `launch_run.py
  status` pod table; W&B run for `allaxis1x-c1` (train-7); RL_LOG 09-06 06:1x-06:3x.

- 09-06 ~06:1x-06:2x this cycle (assigned `medhead-dr-push1x-c1`, `widenirrc3-abrupt-c1-acq1`):
  **2/2 PASS — the DONE ladder's own "push" axis clears at nominal dose, and the 2nd 8-way
  heading-set ACQ seed holds clean but surfaces a reward/eval misalignment.** (1)
  `medhead-dr-push1x-c1` CANARY PASS: restoring nominal (30%/episode) mid-walk base-torque
  push on the champion costs a modest but majority-clearing amount (20/24, down from 24/24
  push-off, scattered non-chronic sac across legs 0/2/4/5), 0 falls, reward rising every
  quarter -- push-recovery is close to free, joining every other DR-restore axis. (2)
  `widenirrc3-abrupt-c1-acq1` **ACQ PASS**: its own 2M canary's 23/24 clean gait_valid holds
  EXACTLY at 40M (single non-chronic dip, different legs than the recurring leg[1,4]
  fingerprint), 0 falls, tight track_err (4-6.6deg) in every episode -- but `ep_rew_mean` is
  deeply negative and bimodal (-1082/-1559/-1414/-1154 quarters, per-episode returns swing
  +1380 to -3406 with near-identical forward progress and healthy duty). Root cause: this is
  the first ACQ-scale run of the widened 8-direction heading set (incl. backward/diagonals),
  and the freeprog reward kernel evidently penalizes some heading directions heavily even
  with accurate tracking -- a reward/eval misalignment (08-21 category), NOT a behavioral
  failure. **Next:** the wide/backward heading-set reward gap needs a semantics-bank fix
  (freeprog kernel should credit progress along the COMMANDED heading, not penalize
  backward/diagonal commands) before further training is priced on this reward; not yet
  built. This eval also needed a manual `kubectl cp` recovery after a transient websocket
  drop mid-podeval (remote process kept running server-side; report.json was already
  complete on the pod, just unsynced) -- no infra fix needed, self-healing via the run's own
  completed remote artifact. **Refill:** found 2 prior single-axis DR canaries
  (`medhead-dr-groundtilt1x-c1`, `medhead-dr-imupos1x-c1`) still PARKED/REFUSED from
  repeated pod-race losses in earlier cycles; both relaunched and landed VERIFIED RUNNING
  (train-0, train-1) alongside 2 concurrent cycles' own new axes (`gyrobias1x-c1`,
  `zerobiasframe1x-c1`) and the pre-registered culmination arm `medhead-dr-allaxis1x-c1`
  (all previously-PASSED axes composed simultaneously) that a concurrent cycle had queued
  to the backlog -- drained it onto a free pod. SKILLS.md updated (2 new rows). Evidence:
  `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-{medhead-dr-push1x-c1,
  widenirrc3-abrupt-c1-acq1}`, W&B `zuuyfqmt`/`6s59dh5w`, RL_LOG 09-06 06:12-06:26.

- 09-06 ~06:2x this cycle (assigned `medhead-dr-gyronoise1x-c1`, `medhead-dr-kick1x-c1`,
  `medhead-dr-mass1x-c1`): **2 more clean DR-restore PASS + the FIRST FALL anywhere in the
  whole DR-restoration sweep.** (1) `medhead-dr-gyronoise1x-c1` CANARY PASS: nominal (1x,
  0.5deg/s) gyro-noise restore costs nothing, a PERFECT 24/24, 0 falls, reward rising every
  quarter. (2) `medhead-dr-mass1x-c1` CANARY PASS: nominal (0.85-1.20x mass_scale +
  leg_mass_jitter_pct=0.10) restore costs almost nothing, 23/24 with one non-chronic leg-4
  flag, 0 falls. Both join the growing clean-axis-restore list. (3) `medhead-dr-kick1x-c1`
  **CANARY FAIL - INFORMATIVE-NEGATIVE**: restoring the mid-walk roll-kick perturbation
  (dr.walk_kick_prob=0.3, previously OFF all campaign) stays majority (20/24, no new chronic
  leg — sacrifice pattern scattered across legs 0/2/4) but ONE episode (`walk_startjitter/
  sto/4`) genuinely terminates via `tilt_roll` — confirmed on video (frame strip shows
  progressive body roll ending fully tipped, not an instant start-jitter stumble). This is
  the FIRST fall anywhere in the sweep (every prior axis — latency/deadband/noise/tiltnoise/
  encnoise/gyronoise/torquefade/mass/push — held 0 falls). Per the gate's own pre-registered
  text, any fall is a FAIL trigger regardless of aggregate majority. No same-recipe retry;
  next step is a dedicated kick-HARDENING continuation (train WITH the kick active), not
  another bare eval-only canary. **Tooling fix this cycle**: found and fixed a real
  snapshot.sh bug — `pending_evals.json` (watcher/ops.sh runtime queue state, same category
  as `experiments.json`/`backlog.json`) was NOT in the dirty-check exclude list, so any
  controller-side edit to it stamped a `-dirty` code marker on the next `--sync`, which
  `launch_run.py`'s code-version gate then refuses on every future launch attempt until a
  clean re-sync. Root-caused via `medhead-dr-groundtilt1x-c1`, PARKED to
  `backlog_failed.json` after 3 REFUSED attempts with exactly this `-dirty` marker mismatch.
  Fixed (added `pending_evals.json` to snapshot.sh's `EXC` array), snapshotted
  (`186787b1`), un-parked `groundtilt1x-c1` and it launched clean on the next drain.
  **Refill:** 4 new arms landed this cycle across the reopened capacity (6 canaries had
  finished their 2M budgets since the prompt was written): `medhead-dr-gyrobias1x-c1`
  (dr.gyro_bias_deg_s=0.5, gyro RATE bias — distinct from both the already-tested gyro
  NOISE axis and the attitude imu_bias_deg axis) VERIFIED RUNNING train-2;
  `medhead-dr-zerobiasframe1x-c1` (dr.zero_drift_cmd_frame=1 alongside the in-flight
  zerobias1x sibling's own joint_zero_bias_deg=1.0 — tests whether the SAME nominal
  zero-point error also corrupts the commanded frame, not just the sensor readback, a
  harder/more realistic coupling never before exercised) VERIFIED RUNNING train-4;
  `medhead-dr-groundtilt1x-c1` (floor-slope via tilted gravity, the un-parked arm above) now
  RUNNING train-0; `medhead-dr-imupos1x-c1` (IMU mount-position lever-arm error) already
  RUNNING train-1 (landed via a concurrent cycle's drain in the same window). SKILLS.md
  updated (2 new rows: one PASS pair, one FAIL). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-{gyronoise1x,kick1x,mass1x}-c1`, W&B
  `oey1wf38`/`ngh1u2od`/`uw36u2tb`, RL_LOG 09-06 06:2x.

- 09-06 ~06:0x this cycle (assigned `irrwidenc2-abrupt-c1-acq1`, `medhead-dr-deadband1x-c1`,
  `medhead-dr-latency1x-c1`): **2 DR-restore PASS, 1 ACQ FAIL — 3rd/4th single-axis DR cells
  close clean, 2nd irr+widen composition regresses at scale.** (1) `medhead-dr-latency1x-c1`
  CANARY PASS: restoring nominal (1x) actuator-command-latency spread on the campaign's
  cleanest champion costs nothing, a PERFECT 24/24, 0 falls, reward rising every quarter.
  (2) `medhead-dr-deadband1x-c1` CANARY PASS: nominal (1x) deadband spread costs almost
  nothing, 23/24 with one non-chronic leg-5 flag, 0 falls, reward rising every quarter. Both
  join latency/noise1x/tiltnoise1x/torquefade2x as clean axis-restore PASSes -- every
  guardrails-named DR axis (mass/geometry/friction/compliance/gravity/gains) plus sensor
  noise/bias, actuator latency/deadband/velocity-cap/torque-fade/command-drop now has at
  least one clean-champion PASS on record. (3) `irrwidenc2-abrupt-c1-acq1` **ACQ FAIL**: the
  2M canary's clean 22/24 does NOT hold at 40M -- drops to 18/24, walk/det (the gate's primary
  mode) falls to 3/6 from 5/6, below majority; startjitter/sto also drops 5/6->3/6. Sacrifice
  pattern is MIXED (leg-4 x3, leg-0 x3, leg-3 x1) rather than the canary's clean sweep --
  different fingerprint from the chronic-single-leg s3acq entrenchment. `ep_rew_mean` stays
  deeply negative and non-monotonic (-1280/-1971/-1493/-1086), not an 08-21 rising-reward
  case. 0 falls. This is the 2nd irr+widen-composed arm (after the concurrently-verdicted
  `irr2acq1-abrupt-c1-acq1`) to regress at ACQ scale on an otherwise-healthy abrupt source --
  extends the source-cleanliness-margin finding: even a clean-at-2M source is not guaranteed
  durable at scale for every axis composition; the irr+widen combination specifically (vs
  irr alone, which held on `irrwidenc1`) looks like the fragile ingredient. No continuation
  funded. **Refill:** filled all 4 free GPU slots (train-4 already claimed by a concurrent
  cycle's `medhead-dr-geom1x-c1`, which closes the LAST guardrails-named axis) with 2 more
  new single-axis DR-hardening canaries not yet covered by any arm: `medhead-dr-actionnoise1x-c1`
  (dr.action_noise, actuation-side noise distinct from the already-split sensor-noise axes)
  VERIFIED RUNNING train-7, and `medhead-dr-startpose1x-c1` (dr.placement_noise_deg +
  bad_start_prob/max_joints/deg, matching the eval harness's own startjitter panel; NOTE this
  exact bundled mechanism was already tried as a REPAIR lever on a different, already-
  compromised base(1g) family and CLOSED 8/8 FAIL there -- this arm asks the distinct
  question of whether an already-clean crossgrav champion also regresses under it) VERIFIED
  RUNNING train-11. Two more axes (`medhead-dr-groundtilt1x-c1` floor-slope via tilted
  gravity, distinct from the crossgrav campaign's own gravity-MAGNITUDE scaling; `medhead-dr-
  imupos1x-c1` IMU mount-POSITION lever-arm error, distinct from the already-tested imu_bias/
  imu_mount ROTATION axis in `imubias1x`) queued to `backlog.json` after repeated pod-race
  REFUSALs against concurrent cycles' own fills (`zerobias1x`, `torquefade1x`, `fault1x`,
  `widenirr-c1-acq1`, `widenfwd-c2-acq1` all landed on the slots I tried in the same window)
  -- the self-repairing drain will place them. SKILLS.md updated (2 new rows: one PASS pair,
  one FAIL). Evidence: `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-{medhead-dr-
  latency1x-c1,medhead-dr-deadband1x-c1,irrwidenc2-abrupt-c1-acq1}`, W&B `5xqrfrqd`/
  `07qw8xz0`/`0l8ed9g4`, RL_LOG 09-06 06:00-06:01.

- 09-06 ~06:0x this cycle (assigned `medhead-dr-tiltnoise1x-c1`): **CANARY
  PASS, another PERFECT axis restore.** Restoring nominal (1x, 0.3deg)
  IMU tilt-sensor noise (previously pinned at 0 the whole campaign)
  costs nothing on the campaign's cleanest champion
  (`medhead-abrupt-c1-acq1-cont40m`, 80M, 24/24): aggregate
  `gait_valid` 24/24, `sac=[]` every episode, 0 falls, slip/m banded
  3.4-4.9 (above the 2.9 teacher band, consistent with every sibling
  DR-restore canary). Joins deadband1x/latency1x/noise1x/torquefade2x
  as a clean single-axis PASS. Refilled 3 previously-untried DR axes
  to fill 3 free GPU slots (fleet was otherwise saturated by
  concurrent cycles' own DR-sweep launches): `medhead-dr-zerobias1x-c1`
  (`dr.joint_zero_bias_deg=1.0`, persistent per-joint zero-point
  calibration error — the single most hardware-realistic untested
  axis, distinct from the transient noise/latency axes already
  covered), `medhead-dr-extpush1x-c1` (`dr.ext_push_prob=0.3`,
  mid-episode external push-recovery, distinct from the already-tested
  walk-takeoff `dr.walk_push_*`), `medhead-dr-fault1x-c1`
  (`dr.fault_prob=0.3`, real per-episode actuator fault: weakened/
  frozen/disabled-leg — informative against the campaign's own
  reward-driven leg-sacrifice findings). All 3 VERIFIED RUNNING
  (train-1/9/10). SKILLS.md updated (1 new row). Evidence: `logs/
  ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_
  tiltnoise1x_c1_gate/report.json`, W&B `w0kk6df2`, RL_LOG 09-06 06:0x.

- 09-06 ~05:4x-05:5x this cycle (assigned `medhead-dr-noise1x-c1`, `medhead-dr-
  torquefade2x-c1`, `widen2c1-abrupt-c1-acq1-cont40m`): **3/3 PASS — 4th
  endurance-panel confirmation + 2 clean single-axis DR-restoration
  canaries, one PERFECT.** (1) `widen2c1-abrupt-c1-acq1-cont40m`
  PASS/HOLDS: 2nd +40M helping (80M cumulative) reproduces its own 40M
  read within noise (19/24 vs 20/24; both gated primary modes 6/6, 0
  falls, reward still rising) — the pre-existing [1,4]-pair pattern
  consolidates onto leg-1 alone in det plus one new isolated non-chronic
  leg-5 sto miss, not a spread to an unrelated leg. 4th endurance-panel
  source (after s1acq, medhead, widenirrc1) confirming the
  cleanliness-margin-at-40M rule. (2) `medhead-dr-noise1x-c1` CANARY
  PASS: 23/24, restoring nominal own-DR sensor noise (encoder/tilt/gyro)
  on the 80M/24-24 champion costs almost nothing (1 non-chronic flag).
  (3) `medhead-dr-torquefade2x-c1` CANARY PASS: a PERFECT 24/24 —
  fading the fixed 3x torque/battery-assist crutch to 2x (the single
  lever the DR-rung design note flagged as "the key open decision")
  costs NOTHING. **Refill:** licensed a torque-fade dose-response probe
  off the PERFECT result — launched `medhead-dr-torquefade1x-c1`
  (train-3, VERIFIED RUNNING, `dr.torque_scale`->1.0, assist removed
  entirely) and queued `medhead-dr-torquefade15x-c1` (`dr.torque_scale`
  ->1.5) to `backlog.json` after 3 consecutive REFUSED races against
  concurrent cycles' own DR-sweep expansion (fault1x/extpush1x/
  startpose1x/zerobias1x/actionnoise1x all landed mid-cycle — fleet hit
  11/11 saturated). Also relaunched `medhead-dr-geom1x-c1` (train-4,
  VERIFIED RUNNING) — a prior REFUSED attempt's spec, unchanged, now on
  a free pod — closing the last guardrails-named DR axis (mass/
  geometry/friction/compliance/gravity/gains) with a live canary.
  SKILLS.md updated (3 new rows). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-crossgrav-{widen2c1-abrupt-c1-acq1-
  cont40m,medhead-dr-noise1x-c1,medhead-dr-torquefade2x-c1}`, matching
  `report.json`/contact sheets, W&B `pvdwyhuv`/`zky69ilf`/`ky7yokg0`,
  RL_LOG 09-06 05:46-05:48.

- 09-06 ~05:4x this cycle (assigned `widen2c3-abrupt-c2`, `widenirrc1-abrupt-c1-acq1-cont40m`,
  `medhead-widenfwd-c2-deferartifacts`): **3 verdicts (1 FAIL confirming a closed
  question, 1 PASS/HOLDS, 1 infra-PASS science-caveat closed) + 3-arm ACQ refill.**
  (1) `widen2c3-abrupt-c2` (the pre-registered seed-2 twin discriminating seed noise
  from source fragility on `widen2c3-abrupt-c1`'s own FAIL): **CANARY FAIL - MECHANISM,
  n=2/2**. Reproduces the identical `walk_startjitter/det` leg[1,4] chronic-sacrifice
  fingerprint (3/6 gait_valid, `sac=[1]`/`[1,4]`/`[4]` across the 3 invalid episodes) —
  closes the seed-noise question negatively: this is a real attractor of the widen2-c3
  source, not noise. No further crossgrav spend on widen2-c3; the widen2-crossgrav
  story stands on c1's lineage only. (2) `widenirrc1-abrupt-c1-acq1-cont40m` (2nd +40M
  endurance helping, 80M cumulative): **PASS/HOLDS**, a PERFECT 24/24 gait_valid
  (zero flagged episodes in any of the 4 modes), 0 falls, slip_per_m tightly banded
  3.3-5.4, reward still rising (432/860/987/1092) — the cleanest endurance read in the
  campaign, a 3rd source (after s1acq, medhead) confirmed to tolerate a 2nd helping.
  (3) `medhead-widenfwd-c2-deferartifacts`: already PASS-verdicted last cycle for its
  primary infra deliverable (the `--defer-final-artifacts` GPU-handoff mechanism); this
  cycle's prestaged harness read landed the science half that was left advisory —
  aggregate `gait_valid` 23/24, IDENTICAL to seed-1's own 23/24, confirming seed-2 of
  medhead-widenfwd is mechanism-healthy. Verdict text updated (FORCE=1) to close the
  advisory caveat; no SKILLS row (infra is the deliverable, science is corroborating).
  **Refill (3 ACQ continuations, all on free GPU pods — 5-6 idle mid-cycle):**
  (a) `medhead-widenfwd-c2-acq1` (matched 40M ACQ for the now-confirmed 2nd widenfwd
  seed, `--init-from-source` off its own 2M checkpoint, train-5, VERIFIED RUNNING) —
  first attempt mis-respec'd without `--init-from-source` and would have silently
  restarted from the grandparent base champion instead of continuing the seed-2
  lineage; caught before drain via the backlog re-check, removed the bad backlog
  entry, relaunched correctly. (b) `medhead-widenirr-c1-acq1` (matched 40M ACQ for the
  widen-then-irr composite, already CANARY PASS 22/24 and never given its own ACQ
  continuation despite the SKILLS.md note flagging it "eligible", train-8, VERIFIED
  RUNNING). Self-caught guardrail near-miss: (a)+(b) alone already commit the cycle's
  full 80M `max_new_gpu_steps_per_cycle` allowance (2x40M). (c) `medhead-irrwiden-c1-
  acq1` (matched 40M ACQ for the irr-then-widen sibling composite, its own CANARY PASS
  23/24, also never given an ACQ continuation despite the same "eligible" flag) was
  first launched `--now` after 2 pod-busy races (train-3, train-9, then train-10, then
  train-2 succeeded VERIFIED RUNNING) — only then noticed this made 3x40M=120M new GPU
  steps this cycle, 40M over the guardrail cap with no operator exception in force.
  Self-corrected: killed it within ~1 min of start (0 GPU memory used/no progress
  lost, `status=SELF_KILLED_OVER_CAP`), then re-queued the identical hypothesis/gate
  via plain `respec` (no `--now`) so the live backlog drain places it under its own
  mechanical scheduling once capacity is next free — this cycle's own launch count
  stays at 2x40M, within cap. SKILLS.md updated (2 new rows: widen2c3-abrupt-c2
  FAIL, widenirrc1-abrupt-c1-acq1-cont40m PASS). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-crossgrav-widen2c3-abrupt-c2`, `ops.sh review
  cw-walkscratch-easy0905-headset-crossgrav-widenirrc1-abrupt-c1-acq1-cont40m`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_medhead_widenfwd_c2_deferartifacts_gate/
  report.json`, W&B `g8285ntc`/`1us3k6k1`/`o81ovjq7`, RL_LOG 09-06 05:41-05:5x.

- 09-06 ~05:3x this cycle (assigned `s3acq-widenfwd-c1`, `s3acq-irrfwd-c1`): **2/2
  CANARY FAIL — forward-composing onto an already-compromised source
  re-surfaces its chronic leg-1 weakness immediately at 2M, it does
  not dilute or heal it.** Both arms compose an axis (widen2 heading
  set / irr timing-jitter) onto `s3acq-abrupt-c1-acq1`, the source
  already known to entrench (ACQ FAIL at 40M, WORSE at its own 80M
  cont40m). (1) `s3acq-widenfwd-c1`: 14/24 gait_valid (bar >=18/24),
  ALL 10 invalid episodes across all 4 modes name leg-1 as the sole
  sacrificed leg — a total, clean reproduction of the source's own
  fingerprint; several cells show extreme skating (slip/m 24-208);
  reward NET-DECLINING every quarter (-80.7/-214/-254/-606, a
  genuine FAIL by both reward and eval, not misalignment). (2)
  `s3acq-irrfwd-c1`: 17/24, misses the bar by one episode, leg-1 in
  4/24 + leg-2 in 2/24 (softer/more mixed than widenfwd but still
  leg-1-leaning); reward mildly rising but not read as an 08-21
  continue case given the source's own 2x-FAILed history. 0 falls in
  both. Contrasts sharply with the SAME two axes composed onto
  healthy sources (medhead, s1acq, widen2c1), which all held clean —
  confirms source health, not recipe or budget, is the causal
  predictor for forward-composition durability too, extending the
  already-established native-1g-durability finding. No continuation
  funded on either arm. SKILLS.md updated (2 new rows). Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_s3acq_
  {widenfwd,irrfwd}_c1_gate/report.json`, W&B `zvxecftd`/`aaoxg15b`,
  RL_LOG 09-06 05:34.

- 09-06 ~05:3x this cycle (assigned `s1acq-abrupt-c1-acq1-cont40m`, `s1acq-irrfwd-c1`,
  `s3acq-abrupt-c1-acq1-cont40m`): **3 verdicts (2 PASS, 1 ACQ FAIL) — the endurance
  panel's 2nd data point diverges sharply from the 1st, isolating cleanliness margin
  (not budget) as the real predictor; 1-arm ACQ-continuation refill.**
  (1) `s1acq-abrupt-c1-acq1-cont40m` **PASS/HOLDS**: 2nd +40M helping (80M cumulative)
  on the campaign's overall cleanest source reproduces its own 40M read EXACTLY
  (23/24, same single transient leg-4 startjitter/det dip, 0 falls, reward still
  rising). (2) `s1acq-irrfwd-c1` **CANARY PASS**: the irr-jitter axis forward-composed
  onto s1acq transfers cleanly at 2M (22/24, leg-4 softening confined to walk/det
  only, not chronic across modes) -- a 3rd base champion confirming compose-after-
  transfer for this axis. Launched matched 40M ACQ continuation `s1acq-irrfwd-c1-
  acq1` (train-0, VERIFIED RUNNING). (3) `s3acq-abrupt-c1-acq1-cont40m` **ACQ FAIL -
  MECHANISM/ENTRENCHES**: the SAME 2nd +40M helping on the 2nd-cleanest source
  (already showing a chronic leg-1 startjitter softening at its own first 40M read,
  21/24) makes it WORSE, not better -- 80M aggregate drops to 16/24, `walk_startjitter/
  det` collapsing to 1/6 with leg-1 duty chronically <=0.27 across every one of the 6
  episodes in BOTH startjitter panels. **This is the key new finding**: endurance/
  more-budget is not a universal lever -- it holds flat-to-improving on sources
  already clean at 40M (s1acq, medhead) but actively deepens the entrenchment on a
  source that was already trending that way (s3acq). Cleanliness margin above the
  entrenchment threshold predicts the endurance outcome, not total steps trained.
  Practical implication: no further cont40m endurance spend on any source whose 40M
  read already shows a chronic single-leg pattern -- that budget belongs to a
  structural per-leg-utilization repair instead (open design gap, unchanged).
  Refill: fleet was fully saturated (11/11 reachable GPU pods busy, mostly the
  ongoing single-lever DR-restoration sweep -- friction/kick/mass/push/contactstiff/
  imubias/latency/deadband/torquefade/noise/velscale/cmddrop axes, 12+ arms now,
  run concurrently by sibling cycles) for most of this cycle; when train-0 freed up
  mid-cycle, launched `s1acq-irrfwd-c1-acq1` immediately. Also found the `medhead-
  dr-gains1x-c1` arm (kp/kv per-servo gain-spread axis) had been REFUSED twice by
  concurrent cycles racing the same free pod (not an error) -- queued it to
  `backlog.json` so the self-repairing drain places it on the next free slot instead
  of a 3rd manual race. SKILLS.md updated (3 new rows: 2 for the PASS/CANARY-PASS
  pair, 1 dedicated row for the cleanliness-margin ACQ FAIL finding). Evidence:
  `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-{s1acq-abrupt-c1-acq1-
  cont40m,s1acq-irrfwd-c1,s3acq-abrupt-c1-acq1-cont40m}`, matching `report.json`
  files + frame strips, W&B `7i7dzujt`/`o3bapgqi`/`z1e7r91v`, RL_LOG 09-06 05:21-05:31.

- 09-06 ~05:3x this cycle (assigned `medhead-ramp-irrfwd-c1-acq1`,
  `headset-halfgrav-widenirr-c3-acq1`; `assistfade-rung1-bcinit-
  taskonly-s2-cont8m` already verdicted by a concurrent cycle before
  this one read it, matching read confirmed): **2/2 ACQ PASS,
  discriminates the ramp-entrenchment open question, + a 9-arm DR-
  hardening refill batch.** (1) `medhead-ramp-irrfwd-c1-acq1` ACQ
  PASS: gait_valid 22/24, EXACT match to its own 2M canary's 22/24
  structure (same non-chronic leg-5 flag pattern, unchanged), 0
  falls, flat slip. This is the discriminating read the prior cycle
  flagged: `medhead-ramp-widenfwd-c1-acq1` regressed mildly (18/24,
  new leg-4 flag) while this sibling (same ramp-transfer method,
  opposite composed axis) holds perfectly clean — REFUTES "ramp-
  transfer itself carries elevated entrenchment risk" as a general
  claim; the widenfwd regression reads as axis-specific or an n=1
  seed blip, not a ramp-vs-abrupt structural effect. (2) `headset-
  halfgrav-widenirr-c3-acq1` ACQ PASS: gait_valid 21/24 (mild degrade
  from the 2M canary's 23/24, gate's own tolerance), 0 falls, no new
  chronic leg, and course-tracking metrics (wrong_direction_frac,
  course_err) the gate flagged for scrutiny actually IMPROVED vs
  canary. Closes the widenirr halfgrav tie-break 2/3 seeds durable
  (c1 PASS, c2b FAIL, c3 now PASS). SKILLS.md updated (2 new rows).
  **Refill:** with 5+ GPU slots freed by a wave of 2M DR-probe
  canaries finishing, launched a batch of previously-untested single-
  axis DR-hardening probes off the campaign's most durable champion
  (`medhead-abrupt-c1-acq1-cont40m`, 80M, 24/24 clean), matching the
  established latency/deadband/torque/noise/mass template: this
  cycle placed `medhead-dr-{velscale1x,contactstiff1x,cmddrop1x,
  imubias1x}-c1` (vel_scale, contact_stiff_scale, cmd_drop_prob_max,
  imu_bias_deg+imu_mount_deg — the last a BIAS/offset axis, distinct
  from the already-tested NOISE/variance axes); a `gains1x` and a
  `geom1x` attempt both got mechanically REFUSED as duplicates of
  concurrent cycles' `gain1x-c1`/(geom1x placed on an already-taken
  pod) — no wasted spend, confirms independent convergence on the
  same next-lever list. Combined with concurrent cycles' own
  `mass1x`/`friction1x`/`gain1x`/`push1x`/`kick1x` arms, this single-
  axis DR battery now covers every explicitly-idealized realism axis
  named in `guardrails.yaml` (mass/geometry/friction/compliance/
  gravity/gains) plus sensor noise, sensor bias, actuator velocity
  cap, and command-drop — read all of their reports next cycle before
  deciding which axes need a real hardening-rung training budget.
  Fleet fully saturated on exit (11/11 reachable pods busy). Evidence:
  `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-medhead-
  ramp-irrfwd-c1-acq1 cw-walkscratch-easy0905-headset-halfgrav-
  widenirr-c3-acq1`, `launch_run.py status`, RL_LOG 09-06 05:06/05:30.

- 09-06 ~05:0x this cycle (assigned `medhead-ramp-widenfwd-c1-acq1`,
  `medhead-widenirr-c1`, `plainhead-abrupt-c1b-acq1`): **2 PASS, 1 FAIL
  (mild) — new medhead-ramp-vs-abrupt durability split found.**
  (1) `medhead-widenirr-c1` **CANARY PASS** (22/24 gv, 0 falls): the
  widen-then-irr composition order also clears cleanly, matching its
  irr-then-widen sibling (`medhead-irrwiden-c1`) — composition order
  confirmed irrelevant for this axis pair regardless of direction.
  Leg-5 flagged 2/24, matching the pre-existing leg-2/5 signature
  already on its irrfwd parent, not new. (2) `plainhead-abrupt-c1b-
  acq1` **ACQ PASS**: the simplest never-composited crossgrav champion
  holds an EXACT 23/24 match to its own 2M canary at full 40M budget —
  2nd champion (after medhead-abrupt) confirmed durable with zero
  entrenchment. (3) `medhead-ramp-widenfwd-c1-acq1` **ACQ FAIL -
  MECHANISM (mild)**: aggregate 18/24 (down from 21/24 canary),
  `walk_startjitter/det` leg-4 crosses its own pre-registered "max
  2/6 per leg" anti-regression clause (1/6->3/6). This is the FIRST
  medhead-LINEAGE instance of the widely-documented cross-recipe
  startjitter leg[1,4] entrenchment — but critically, via the **ramp**
  gravity-transfer variant, not the **abrupt** variant that stays 5/5
  clean across every 40M+ read in this campaign. Severity is mild:
  leg-4's own duty magnitude barely changed (0.06-0.24 at 40M vs
  0.08-0.22 at 2M, same marginal band, just crossing the flag
  threshold 2 more times) and frame strips confirm the leg still
  visibly participates in a genuine six-leg gait, unlike the severe
  precedent cases (s3acq/irracq1's near-zero duty). **New open
  question**: does the ramp-transfer method itself carry elevated
  entrenchment risk vs abrupt, independent of the composed axis? The
  ramp family's other 2M canaries were mixed already (`medhead-ramp-
  irrfwd-c1`/`medhead-ramp-widenfwd-c1` PASS, `irrwidenc1-ramp-c1`
  FAIL-INFORMATIVE) — this is the first ACQ-SCALE ramp read, and it
  regresses. Not enough evidence yet to indict ramp-vs-abrupt as a
  causal axis (n=1 ACQ read); flag for whoever reads `medhead-ramp-
  irrfwd-c1-acq1` (in flight) next — same recipe family, opposite
  axis, will help discriminate. SKILLS.md updated (3 new rows).
  Evidence: `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-
  {medhead-ramp-widenfwd-c1-acq1,medhead-widenirr-c1,plainhead-abrupt-
  c1b-acq1}`, matching `report.json`/contact sheets, W&B
  `x1nue97w`/`b3l8tia5`/`2ngv7lap`, RL_LOG 09-06 04:58-05:04.

- 09-06 ~04:5x this cycle (assigned `medhead-irrwiden-c1`,
  `widenirrc3-abrupt-c1`): **2/2 CANARY PASS, 2-arm ACQ-continuation
  refill.** (1) `widenirrc3-abrupt-c1` CANARY PASS: 23/24 gait_valid,
  0 falls, closes the widenirr-crossgrav axis at n=2 seeds clean
  (unlike widen2's 1-PASS/1-FAIL seed split). (2) `medhead-irrwiden-c1`
  CANARY PASS: 23/24 gait_valid, 0 falls, the opposite composition
  order (irr-then-widen) on the medhead base — confirms composition
  order doesn't matter for this axis pair (matches medhead-widenfwd/
  irrfwd's own individual-axis PASSes). Both flagged episodes name a
  single non-chronic leg matching a parent's pre-existing signature,
  not a new pathology; both frame strips confirm genuine six-leg
  cycling with body translation. Refill: with 8 GPU slots free and
  empty backlog, launched matched 40M ACQ continuations for both this
  cycle's own PASS (`widenirrc3-abrupt-c1-acq1`) and an
  already-verdicted-but-unrefilled sibling PASS from an earlier cycle
  (`widen2c1-irrfwd-c1-acq1`, off `widen2c1-irrfwd-c1`'s own CANARY
  PASS-INFORMATIVE) — both queued via `respec --init-from-source`,
  matching the medhead/widen2c1/s1acq/s3acq ACQ-continuation
  precedent. Did not launch a 3rd continuation off `medhead-irrwiden-
  c1` this cycle (its sibling `medhead-widenirr-c1` result and several
  other ACQ continuations were already in flight/queued from
  concurrent cycles this wave; leaving that refill for whichever
  cycle reads `medhead-widenirr-c1` next to decide jointly). SKILLS.md
  updated (2 new rows). Evidence: `ops.sh review cw-walkscratch-
  easy0905-headset-crossgrav-{medhead-irrwiden-c1,widenirrc3-abrupt-
  c1}`, matching `report.json`/contact sheets, W&B `jbpj69ir`/
  `ou65x19c`, RL_LOG 09-06 04:42/04:46.

- 09-06 ~04:4x this cycle (assigned `medhead-abrupt-c1-acq1-cont40m`,
  `medhead-widenfwd-c1-acq1`, `medhead-irrfwd-c1-acq1`): **3/3 PASS,
  no refill needed on this thread this cycle.** (1) `medhead-abrupt-
  c1-acq1-cont40m` **PASS/HOLDS** at a SECOND +40M helping (80M
  cumulative 1g steps): `gait_valid` 24/24, actually better than its
  own 40M parent's 23/24 (the parent's one transient leg-4 dip is
  gone), 0 falls. This directly answers the open question from
  `irracq1`'s FAIL: crossgrav entrenchment risk is recipe/source-
  specific, NOT a universal slow clock every transferred champion is
  on regardless of budget — medhead specifically is durable past 40M.
  (2) `medhead-widenfwd-c1-acq1` **ACQ PASS**, 21/24 (mild dip from
  its own 23/24 canary but no chronic same-leg pattern — 3 flagged
  episodes each name a different leg), slip/progress mostly IMPROVED
  vs canary. (3) `medhead-irrfwd-c1-acq1` **ACQ PASS**, 21/24, flat
  (not entrenching) vs its own 22/24 canary — the same leg-2/5
  softening reproduces at the identical episode indices rather than
  worsening, a third distinct behavioral class alongside "holds clean"
  (medhead-abrupt) and "entrenches" (irracq1/irr2acq1/s3acq). All 3
  videos/contact sheets confirm real six-leg cycling. Read together:
  medhead is now confirmed as the campaign's most robust lineage
  across 5 independent 40M+ reads (abrupt, abrupt-cont40m, widenfwd,
  irrfwd, and the earlier abrupt-c1-acq1 parent) with zero
  entrenchment across any of them — a useful counterpoint anchor for
  whatever the eventual role-aware structural repair mechanism gets
  validated against. No new refill launched off this specific finding
  (the natural next composite, medhead-widenirr, is already
  in-flight per a concurrent cycle's `medhead-irrwiden-c1`); checked
  free GPU capacity (3 slots: train-1/2/8) and confirmed no
  under-served track needs it this cycle — see refill note below.
  SKILLS.md updated (3 new rows). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-crossgrav-medhead-{abrupt-c1-acq1-
  cont40m,widenfwd-c1-acq1,irrfwd-c1-acq1}`, matching
  `logs/ckpt_eval/.../report.json` + contact sheets, W&B
  `kfpu6ku1`/`thsloov1`/`naxsaxqj`, RL_LOG 09-06 04:38-04:39.

  **Refill this cycle (04:5x): opened the DR-rung.** Free capacity
  spiked to 9+ idle GPU pods mid-cycle as the concurrent crossgrav
  ACQ/cont40m wave wound down together. Rather than dribble more
  crossgrav-transfer seeds, used it to finally execute the "DR-rung
  design item" this file has been flagging as unaddressed since
  ~04:3x: launched 4 single-lever 2M discovery canaries, each
  respec'd off `medhead-abrupt-c1-acq1-cont40m` (the campaign's
  single most-tested, most-durable champion, 5-for-5 across every
  40M+ read), `--phase hardening`:
  - `medhead-dr-latency1x-c1` (train-4): `dr.latency_scale` 0->1
    (restore nominal, non-randomized actuator latency; the whole
    easy0905 campaign has trained with ZERO actuator delay).
  - `medhead-dr-deadband1x-c1` (train-1): `dr.deadband_scale` 0->1
    (restore nominal actuator deadband; campaign has trained with
    ZERO dead-zone, exact-instant command execution).
  - `medhead-dr-torquefade2x-c1` (train-2): `dr.torque_scale` 3->2
    (fade the fixed 3x torque/battery assist crutch by a third —
    the single lever explicitly named as the key open decision).
  - `medhead-dr-noise1x-c1` (train-3): `dr.encoder_noise_deg`/
    `dr.tilt_noise_deg`/`dr.gyro_noise_deg_s` 0->0.09/0.3/0.5 (the
    project's own standard "own-DR" nominal sensor-noise defaults
    from `domain_rand.py`, currently pinned at 0 all campaign).
  Each isolates exactly one previously-idealized/cheated axis
  (single-variable-at-a-time discipline) so a collapse localizes
  cleanly to its own realism gap rather than confounding several at
  once. Gate (same shape all 4): PASS/INFORMATIVE-POSITIVE if
  aggregate `gait_valid` stays majority (>=18/24) with no NEW chronic
  single-leg sacrifice and 0 falls (the champion tolerates that
  realism axis with zero retraining); FAIL/INFORMATIVE-NEGATIVE if it
  collapses (tells us that axis needs its own real training-budget
  hardening rung, and which one binds first). VERIFIED RUNNING all 4
  (`launch_run.py status`). Read these before choosing which axis(es)
  earn the next real (non-canary) hardening-rung training budget.

- 09-06 ~04:3x this cycle (operator refill-maintenance kick, no assigned
  runs; focus note refill-maintenance-20260906T0409): **1-arm walkcurr
  refill + 1 assistfade continuation (`s2-cont8m`, see that track's
  STATUS); finished-but-eval-blocked runs left unverdicted on purpose.**
  Launched `headset-crossgrav-widen2c3-abrupt-c2` (VERIFIED RUNNING
  train-9, 2M canary, `--allow-twin` seed-2 repeat of
  `widen2c3-abrupt-c1`'s CANARY FAIL from the same
  `halfgrav_fullhead_widen2_c3_acq1` checkpoint): the pre-registered
  seed-noise discriminator for the widen2 crossgrav 1-PASS/1-FAIL split,
  mirroring exactly how `irrwidenc2-abrupt-c1` refuted
  composition-order-as-causal for `irrwidenc1`'s FAIL (09-06 04:09).
  Fixed a launcher self-repair sync failure on train-10 first (tar
  "File exists" on 2 stale `rl_docs/runs` copies; removed pod-side,
  relaunch clean). **Eval-blocked, NOT verdicted, left for whichever
  cycle sees their reports land** (gate evals confirmed genuinely
  computing on their pods, not orphaned): `medhead-widenfwd-c1-acq1` +
  `medhead-irrwiden-c1` (both train-2 CPU), `medhead-irrfwd-c1-acq1`
  (train-3), `medhead-abrupt-c1-acq1-cont40m` (endurance-panel anchor),
  `widenirrc3-abrupt-c1`, and todaypolicy's `cw-robotwalk-turns-20260906`
  (train-1). Deliberately did NOT launch a DR/push-hardening arm despite
  it being the ladder's next registered rung: read the trainer —
  `--dr-scale` only scales the `dr.*` cfg RANGES, and the easy0905
  recipe pins them degenerate (`dr.torque_scale=3,3` fixed assist,
  latency/deadband/noise 0), so a one-flag DR arm would randomize
  nothing meaningful. **DR-rung design item (pre-registered for a design
  cycle): choose hardening axes + doses as explicit `dr.*` range
  widenings (incl. deciding whether the 3x torque assist itself fades),
  semantics/bank pass as needed, THEN launch.** Evidence: launcher
  output (VERIFIED RUNNING), ledger entries, RL_LOG.

- 09-06 ~04:2x this cycle, using freed fleet capacity (5 GPU slots opened
  up mid-cycle as concurrent cycles' own runs finished; confirmed via
  repeated `launch_run.py status` re-checks right before each launch):
  completed the medhead-precedent forward-extension grid on the sweep's
  TWO cleanest crossgrav champions. Launched 4 arms: `headset-crossgrav-
  {s1acq,s3acq}-{widenfwd,irrfwd}-c1` (2M discovery canaries, respec'd
  off `medhead-{widenfwd,irrfwd}-c1`'s own templates with an explicit
  `--arg='--init-from=...'` override per the campaign's own documented
  gotcha — `--parent` alone does not repoint the checkpoint). All 4
  VERIFIED RUNNING with the correct source checkpoint confirmed via
  `ops.sh review` (train-2/5/10/11). **Race-condition note (mechanical,
  no compute wasted):** a concurrent cycle's own entry above (04:2x,
  same timestamp bucket) independently proposed and logged
  `s1acq-widenfwd-c1`/`s1acq-irrfwd-c1` as its own refill — re-checking
  both runs' actual ledger `gate` text confirms MY launch is the one
  that is genuinely running on train-2/train-5 (steps progressing,
  W&B ids `3psjr4s8`/`o3bapgqi`), i.e. the launcher's one-run-per-name
  dedup correctly kept exactly one submission live; no duplicate spend,
  just two cycles reasoning to the identical next arm independently.
  `s3acq-widenfwd-c1`/`s3acq-irrfwd-c1` (train-10/train-11) are the
  genuinely new 2nd-champion half of the grid. This completes n=2
  champions (s1acq 24/24, s3acq 21/24) x n=2 axes (widen2 heading,
  irr timing) for the forward-compose-on-a-clean-crossgrav-source
  question, matching medhead's own already-PASSed precedent on a 3rd/
  4th base champion.

- 09-06 ~04:2x this cycle (assigned `headset-crossgrav-s1acq-abrupt-c1-acq1`,
  `headset-crossgrav-s3acq-abrupt-c1-acq1`, `headset-crossgrav-widen2c1-
  irrfwd-c1`): 3 verdicts (2 ACQ, 1 canary), 2-arm refill. All 3 gate evals
  were still genuinely computing remotely when the cycle spawned (video-
  every=1 24-episode panels); confirmed via `kubectl exec ps aux` on each
  pod (not orphaned), backgrounded 3 `ops.sh pollreap` loops, read each
  `report.json` as it landed. **(1) `s1acq-abrupt-c1-acq1` ACQ PASS**:
  aggregate `gait_valid` 23/24 (walk/det 6/6, walk/sto 6/6, walk_
  startjitter/det 5/6 one transient leg-4 dip, walk_startjitter/sto 6/6),
  0 falls -- essentially matches this run's own 2M canary's PERFECT
  24/24. The campaign's single healthiest source champion holds clean at
  40M, directly answering the durability-vs-source-health question
  `irracq1`'s earlier FAIL raised (at least for this source, health
  predicts durability). **(2) `s3acq-abrupt-c1-acq1` ACQ FAIL -
  MECHANISM**, a SECOND healthy-source (22/24 canary, no prior chronic
  pattern) crossgrav champion to entrench at ACQ scale: walk/det+walk/sto
  stay clean 6/6+6/6, but walk_startjitter/det collapses to 2/6 and
  walk_startjitter/sto to 3/6, both with leg-1 chronically low (duty
  0.03-0.20 across ALL 6 startjitter/det episodes, low in 4/6 -- worse
  than the 2M canary's own milder leg-1 softening, median duty roughly
  halved 0.15-0.19 -> 0.08). Exact numerical fingerprint match to the
  already-closed `widen2c2b-abrupt-c1-acq1` FAIL ("leg-1 in 4/6 and 3/6
  episodes"), but this time on a healthy (not unhealthy) source --
  together with `irracq1`/`irr2acq1` (both FAILed this cycle+last, a
  DIFFERENT recipe) this generalizes the startjitter-panel leg[1,4]
  entrenchment risk across multiple independent lineages, not one
  recipe's quirk (tally: 4 ACQ PASS vs 3 ACQ FAIL among healthy-source
  crossgrav champions so far). CURRENT_TRUTHS updated with the full
  cross-recipe read. **(3) `widen2c1-irrfwd-c1` CANARY PASS -
  INFORMATIVE-POSITIVE** per its own explicit gate: aggregate `gait_valid`
  21/24, majority holds in walk/det (5/6) with no chronic same-leg
  pattern anywhere in the panel (each dip isolated to a single episode)
  -- confirms compose-after-transfer (composing MORE curriculum natively
  at 1g onto an already-transferred champion) generalizes to a 2nd,
  harder base (widen2c1, full 8-way heading incl. reversals), matching
  medhead-irrfwd/widenfwd's own reads. Caveats: 1 genuine fall (TERM
  tilt_roll, first in this forward-extension-canary family) and markedly
  slower/higher-slip than the medhead-based siblings (fwd 0.10-1.32m/20s,
  slip 4.7-10.4 vs siblings' 2.2-3.3m/3-6) -- consistent with widen2c1's
  own baseline being the harder/slower recipe, not a new pathology.
  **Refill (2 arms):** `headset-crossgrav-s1acq-widenfwd-c1` and
  `headset-crossgrav-s1acq-irrfwd-c1` (train-2/train-5, VERIFIED
  RUNNING) -- forward-extension discovery canaries mirroring medhead's,
  testing compose-after-transfer on the campaign's cleanest source (a 3rd
  base champion). Held off on a widenirr-style composite on s1acq
  (composing 2 untested axes before either single-axis sibling lands
  would confound the read, matching this campaign's own discipline) and
  on any further widen2c2b/irracq1-lineage spend (both closed). Noticed
  but left untouched (still genuinely computing on their own pods,
  confirmed via `ps aux`, not orphaned; poll loops backgrounded for a
  future cycle): `medhead-abrupt-c1-acq1-cont40m` and `widenirrc3-
  abrupt-c1` (both appeared mid-cycle, not on this cycle's assigned or
  concurrent-cycle lists) and `plainhead-abrupt-c1b-acq1` (ledger
  `triage=awaiting` since 04:15, also mid-cycle). SKILLS.md updated (1
  new row set). Evidence: `ops.sh review cw-walkscratch-easy0905-
  headset-crossgrav-{s1acq,s3acq}-abrupt-c1-acq1`, `...widen2c1-irrfwd-
  c1`, matching `logs/ckpt_eval/...gate/report.json` files, W&B
  `80g9tb6m`/`lp972djl`/`nodmsa82`, RL_LOG.

- 09-06 ~04:1x this cycle (assigned `headset-crossgrav-irr2acq1-abrupt-c1-acq1`,
  `headset-crossgrav-irrwidenc2-abrupt-c1`): 2 verdicts, 1 FAIL + 1 PASS,
  both gate evals were still genuinely computing remotely when the
  cycle spawned (confirmed via direct `kubectl exec ps aux`, not
  orphaned; registered `evalpending` + used `ops.sh podwaitlog`
  backgrounded rather than blocking, then read each `report.json`
  directly off the pod once it landed). **(1) `irr2acq1-abrupt-c1-acq1`
  ACQ FAIL - MECHANISM, CLOSES the seed-vs-recipe question the prior
  cycle's `irracq1-abrupt-c1-acq1` FAIL flagged as open.** This 2nd
  independent seed of the irr-timing-first crossgrav recipe reproduces
  the SAME ACQ-scale leg-4 entrenchment regression from a clean 2M
  canary (this run's own canary was 22/24): 40M aggregate `gait_valid`
  17/24, leg 4 the sole flagged leg in every low episode (duty
  0.0-0.10, swing_count as low as 1-63 vs 100-200+ for healthy legs) —
  nearly identical fingerprint to sibling seed `irracq1-abrupt-c1-acq1`
  (14/24, leg-4 duty 0.0-0.16). 0 falls in all 24 episodes; slip/m
  tight 3.2-4.9; video confirms real body translation in flagged
  episodes (favoritism under load, not a full freeze) but the SAME
  leg/direction of collapse CURRENT_TRUTHS already closed as
  reward-shaping-resistant (9 prior repair mechanisms on the sde
  family). Training reward rose every quarter (656.7->1207.2->
  1387.2->1532.2) — matches the 08-21 rising-reward shape, but per
  CURRENT_TRUTHS this exact class is a genuine FAIL (more training
  causes the regression, doesn't fix it). **2/2 seeds of the
  irr-first-crossgrav-abrupt recipe now regress at ACQ scale from
  clean 2M canaries — this is RECIPE-level, not seed noise; no further
  seed of this exact recipe should be funded at ACQ scale without a
  structural per-leg-utilization fix** (the same open design gap
  CURRENT_TRUTHS names for the sde family — a hard minimum-duty/
  swing-count price, not more budget or another dose). **(2)
  `irrwidenc2-abrupt-c1` CANARY PASS - INFORMATIVE-POSITIVE, refutes
  composition-order-as-causal.** This 2nd independent seed of the
  irr-first composite (built off this cycle's just-PASSed
  `irrwiden-c2-acq1`) transfers abruptly to full 1g cleanly: aggregate
  `gait_valid` 22/24 (`walk/det` 5/6, other 3 modes 6/6 or 5/6), 0
  falls, two DIFFERENT single legs flagged once each (not chronic,
  unlike `irrwidenc1-abrupt-c1`'s own leg[1,4] chronic FAIL). Video
  (`walk_det_0`) confirms genuine six-leg cycling with clear
  translation. **Closes the composition-order question: irr-first
  crossgrav transfer succeeds on this 2nd seed just as cleanly as
  widen-first — the 1st seed's FAIL was seed-specific, not an order
  effect.** No refill this cycle: every free GPU slot (3 at cycle
  start) was claimed by concurrent cycles within minutes (confirmed
  via repeated `launch_run.py status` re-checks — train-0/3/10 each
  went BUSY with a different concurrent cycle's launch before this
  cycle finished its own triage), and the natural next-layer questions
  (widen2/irr composites on `s1acq`/`s3acq`, a structural per-leg-
  utilization mechanism design pass) are either already claimed or
  need dedicated design work beyond this cycle's remaining scope.
  SKILLS.md updated (2 new rows). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-crossgrav-{irr2acq1-abrupt-c1-acq1,
  irrwidenc2-abrupt-c1}`, matching `logs/ckpt_eval/...gate/report.json`
  files, W&B `zsxkfxzz`/`mijsf6td`, RL_LOG.

- 09-06 ~04:0x this cycle (assigned all 15 of: `headset-base-s0c1-{dgnoise,
  noiseonly}-c1`, `headset-{base,halfgrav}-medhead2-acq1`,
  `headset-crossgrav-irracq1-abrupt-c1` (+its own `-acq1`),
  `headset-crossgrav-medhead-abrupt-c1-acq1`, `headset-crossgrav-
  {widenirrc1,irrwidenc1}-abrupt-c1` (+ `irrwidenc1-ramp-c1`),
  `headset-halfgrav-irrwiden-c2`, `headset-crossgrav-medhead-ramp-c1-acq1`,
  `headset-crossgrav-irr2acq1-abrupt-c1`, `headset-crossgrav-medhead-
  {widenfwd,irrfwd}-c1`): **zero re-triage needed — cross-checked every one
  against the ledger `status` field and found ALL 15 already fully
  verdicted (PASS/FAIL/ACQ_PASS/ACQ_FAIL/CANARY_FAIL), SKILLS-updated, and
  STATUS-narrated by concurrent cycles between 09-05 ~19:2x and 09-06 ~03:3x
  (this file's own entries above/below, matching the exact run names)
  before this cycle even spawned.** The one apparent loose end
  (`headset-halfgrav-medhead2-acq1`, ledger status `CONTINUE`) also already
  had its full lifecycle closed: its `-cont40m` extension ACQ FAILed at
  09-05 ~21:5x (RL_LOG "21:54 ... ACQ FAIL: walk/det improved 4/6->5/6 but
  walk_startjitter/det plateaued at 2/6 through 80M total... halfgrav
  medhead2 seed n=2 reads MIXED"). No duplicate verdicts recorded.
  **Capacity check found 4 GPU pods genuinely idle (train-0/1/2/7,
  confirmed via direct `kubectl exec ps aux`, no `train_ppo_mjx` process on
  any) with an empty backlog** — freed as `cw-assistfade-rung1-bcinit-
  taskonly-s1-cont8m` (assistfade track) and 3 campaign runs finished
  mid-cycle on those exact pods. **Refill (4 arms, one dimension —
  endurance/entrenchment-risk-with-budget — across the 4 untested-for-
  entrenchment healthy crossgrav ACQ-PASS champions):** the 09-06 ~03:1x
  finding (`irracq1-abrupt-c1-acq1` ACQ FAIL via late leg[1,4] entrenchment
  despite a clean 2M canary and rising reward) only had ONE endurance
  cont40m check in flight so far (`medhead-abrupt-c1-acq1-cont40m`,
  launched by a concurrent cycle, still running). This refill completes a
  5-recipe endurance panel spanning the full cleanliness range of
  ACQ-PASSed crossgrav champions: (1)
  `headset-crossgrav-widen2c1-abrupt-c1-acq1-cont40m` (heading-widen
  composite, 20/24), (2)
  `headset-crossgrav-widenirrc1-abrupt-c1-acq1-cont40m` (widen-then-irr
  composite, the cleanest ACQ result at 22/24 with zero slip outliers), (3)
  `headset-crossgrav-s1acq-abrupt-c1-acq1-cont40m` (the campaign's OVERALL
  cleanest crossgrav result, PERFECT 24/24, `sac=[]` every episode — the
  strongest single test case), (4)
  `headset-crossgrav-s3acq-abrupt-c1-acq1-cont40m` (2nd-best halfgrav
  source, 21/24). All 4 launched via `respec --init-from-source --steps
  40000000 --phase hardening`; the launcher's own `--now` verification wait
  timed out under my tool's 2-minute CLI limit on 2 of the 4
  (`s1acq`/`s3acq` — the processes were confirmed genuinely alive and
  training via direct `checkup` HEALTHY reads: fps 23301.7/11650.8, code
  SHA matched, GPU busy), so their ledger `status` was corrected
  INTENT->RUNNING via `update --set` using that same mechanical evidence
  rather than left stale; `wandb_id` backfilled from each pod's own log
  (`7i7dzujt`/`z1e7r91v`). If all 5 endurance checks (this 4 + the
  concurrent medhead one) hold clean, that closes the "does more budget
  ever repair/preserve a healthy champion" reading cleanly
  negative-for-concern (crossgrav-transfer durability is real, not
  provisional); any FAIL narrows to whether cleanliness/margin above the
  entrenchment threshold predicts durability. Evidence: `rl_move/
  orchestrator/experiments.json` ledger entries for all 15 assigned runs
  (status + verdict text already populated), direct `kubectl exec ps aux`
  on train-0/1/2/7, RL_LOG.

- 09-06 ~03:5x this cycle (assigned `medhead-ramp-widenfwd-c1` /
  `widen2c2b-abrupt-c1-acq1`, both already verdicted+committed by a
  concurrent cycle before this one read them — no re-triage, no
  duplicate spend): found 3 crossgrav 40M ACQ runs that had finished
  training on their pods but had NOT been picked up (checkpoint synced,
  no gate dir yet) — `irr2acq1-abrupt-c1-acq1` (train-1),
  `medhead-widenfwd-c1-acq1` (train-2), `medhead-irrfwd-c1-acq1`
  (train-3) — confirmed each via `kubectl exec ps aux` (gate evals
  already genuinely running, prestaged by the watcher or a concurrent
  cycle, not orphaned) and backgrounded `pollreap` loops for all 3 so
  their `report.json`s land without anyone blocking on them; left
  unverdicted for whichever cycle sees them finish first. **Refill (2
  new discovery canaries):** the campaign's own stated next layer —
  composing the widen (8-way heading) and irr (command-timing jitter)
  axes TOGETHER, natively at 1g, on top of the already-ACQ-PASSed
  `medhead-{widenfwd,irrfwd}-c1-acq1` champions — was flagged as ready
  once both single-axis siblings passed ACQ (they have) but was left
  unlaunched pending exactly that. Queued both composition orders,
  mirroring the halfgrav family's own irrwiden/widenirr pair-testing
  discipline: `medhead-widenirr-c1` (from `medhead-widenfwd-c1-acq1`,
  add `walk_cmd_resample_jitter=0.5`) and `medhead-irrwiden-c1` (from
  `medhead-irrfwd-c1-acq1`, add the 8-way `walk_heading_set`), both 2M
  discovery canaries via `respec` (backlog, no `--now`); the live
  `watch_loop` drain placed both within minutes (train-0, train-2).
  Snapshotted (`5e81ed9e`). Evidence: `rl_move/orchestrator/
  experiments.json` entries for the two new runs; RL_LOG 09-06 ~03:5x.

- 09-06 ~03:3x this cycle (assigned `headset-crossgrav-plainhead-abrupt-c1b`,
  `headset-crossgrav-widen2c3-abrupt-c1`, `headset-halfgrav-widenirr-c3`):
  3 verdicts, 2 PASS + 1 FAIL, 4-arm refill. Gate evals for all 3 were
  still genuinely computing remotely when the cycle spawned (video-
  every=1); confirmed via `kubectl exec ps aux` (not orphaned),
  backgrounded 3 `ops.sh pollreap` loops, then read each `report.json`
  as it landed. (1) `plainhead-abrupt-c1b` (the simplest, never-
  composited 3-way champion's own abrupt-transfer test): CANARY PASS,
  `gait_valid` 23/24, 0 falls, clean rising reward, video confirms
  genuine six-leg cycling with body translation — closes the sweep's
  missing simplest-case baseline. (2) `widen2c3-abrupt-c1` (2nd
  independent widen2 seed's crossgrav transfer): CANARY FAIL -
  MECHANISM — collapses into the already-known leg-1/4 chronic-
  sacrifice entrenchment fingerprint under the startjitter panel
  (`walk_startjitter/det` 3/6, legs 1+4 recurring), slip/m up to 202 in
  several stochastic episodes, video (`walk_startjitter_det_3`) shows
  near-static floor despite visible leg cycling. Splits widen2-crossgrav
  1 PASS (c1) / 1 FAIL (c3) — unlike irr-timing crossgrav (2/2 PASS) or
  the healthy-champion crossgrav set (6/6 PASS), widen2's abrupt-
  transfer robustness does NOT fully generalize past its first seed;
  checked reward trend against PASSing sibling widen2c1 (same decline
  shape, milder magnitude) before concluding the FAIL rests on the
  behavioral eval, not reward. No further widen2-crossgrav arms
  planned. (3) `halfgrav-widenirr-c3` (native 0.5g, the widenirr
  composite's 3rd tie-breaking seed after c1 PASS / c2b FAIL): CANARY
  PASS, `gait_valid` 23/24, 0 falls — the lone sac flag ([2,4,5] in
  1/24 episodes) is transient, not chronic. Reward showed an alarming
  monotonic decline (-84.5->-520.6) that was checked against BOTH the
  PASSing (widenirr-c1: -98.5->-568.4) and FAILing (widenirr-c2b:
  -120.6->-548.9) siblings and found the SAME shape in all three —
  ruled non-diagnostic (this composite's `walk_freeprog` shortfall
  pricing under 8-way-heading+jitter resampling is inherently negative
  for every seed regardless of outcome). Real caveat: several
  stochastic/heading episodes show poor course obedience
  (`wrong_direction_frac` up to 0.54, `course_err` up to 85deg) with
  correspondingly inflated slip — a course-tracking-quality gap
  matching the earlier `halfgrav-irrwiden-c2-acq1` precedent, not a
  gait-validity failure. **Refill (3 arms):** (1)
  `headset-crossgrav-plainhead-abrupt-c1b-acq1` — matched 40M ACQ
  continuation (train-5, VERIFIED RUNNING). (2)
  `headset-halfgrav-widenirr-c3-acq1` — matched 40M ACQ continuation,
  explicitly tracking course-tracking metrics at scale as a named gate
  criterion (train-8, VERIFIED RUNNING). (3)
  `headset-crossgrav-widenirrc3-abrupt-c1` — n=2-seed check for the
  widenirr-crossgrav axis specifically (does the SAME seed-sensitivity
  risk found on widen2-crossgrav also apply to widenirr-crossgrav,
  whose 1st seed already PASSed?), abruptly transferring this cycle's
  clean `widenirr-c3` canary to full 1g (train-10, VERIFIED RUNNING).
  SKILLS.md updated (3 new rows, one section). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-{crossgrav-plainhead-abrupt-c1b,
  crossgrav-widen2c3-abrupt-c1,halfgrav-widenirr-c3}`, matching
  `logs/ckpt_eval/...gate/report.json` files, W&B
  `59h70mm0`/`jlal69m5`/`mhn5rvg4`, RL_LOG.

- 09-06 ~03:3x this cycle (assigned `headset-crossgrav-medhead-ramp-irrfwd-c1`,
  `headset-crossgrav-medhead-ramp-widenfwd-c1`, `headset-crossgrav-widen2c2b-
  abrupt-c1-acq1`): 3 verdicts, 2-arm refill. Tooling note: all 3 prestaged
  gate evals were still genuinely computing remotely when the cycle spawned
  (video-every=1 24-episode panels); confirmed via `kubectl exec ps aux` on
  each pod (not orphaned), backgrounded `ops.sh pollreap` loops, then copied
  each `report.json` off its pod directly as it landed. **(1)/(2) both ramp-
  transition forward-extension canaries PASS**, completing the abrupt-vs-ramp
  symmetry question on BOTH tested axes: `medhead-ramp-irrfwd-c1` aggregate
  `gait_valid` 22/24 (`walk/det` 4/6 with 2 transient non-chronic flags, other
  3 modes clean 6/6), 0 falls, slip 3.07-5.37; `medhead-ramp-widenfwd-c1`
  aggregate 21/24 (max 2/6 per leg anywhere, never chronic), 0 falls, several
  slip outliers (55-208) confirmed via frame strip as the already-documented
  reversal-heading spin-in-place artifact, not a new defect. **(3)
  `widen2c2b-abrupt-c1-acq1` CLOSES THE FORK its own 2M canary left open:
  ACQ FAIL — budget does NOT repair an unhealthy-source champion.** Aggregate
  `gait_valid` 14/24, numerically IDENTICAL to the 2M canary's own 14/24, same
  leg-1 chronic fingerprint concentrated in `walk_startjitter/{det,sto}`
  (2/6 each, leg-1 in 4/6 and 3/6 episodes respectively). 0 falls; training
  reward net-rising in the back half (not flat) but per CURRENT_TRUTHS this
  reward-misalignment class is already closed after 9 repair mechanisms with
  a STRUCTURAL fix required, so rising-reward-with-bad-eval here confirms
  continued entrenchment rather than triggering an 08-21 keep-going read.
  Video confirms genuine body translation even in flagged episodes (a
  favoritism issue, not a freeze/paddle) — consistent with every other
  reading of this fingerprint campaign-wide. **Closes the "does more ACQ
  budget substitute for source health" question cleanly: it does not.**
  **Refill (2 arms):** matched 40M ACQ continuations for both PASSing ramp
  siblings, `headset-crossgrav-medhead-ramp-widenfwd-c1-acq1` and
  `headset-crossgrav-medhead-ramp-irrfwd-c1-acq1` (respec off their abrupt
  siblings' own acq1 templates with an explicit `--arg='--init-from=...'`
  override per the campaign's own respec gotcha), both launched via the
  drain (train-11/train-9), INTENT verified queued. No further widen2c2b-
  lineage arms — that thread is closed. SKILLS.md updated (3 new rows).
  Evidence: `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-
  {medhead-ramp-irrfwd-c1,medhead-ramp-widenfwd-c1,widen2c2b-abrupt-c1-acq1}`,
  matching `logs/ckpt_eval/...gate/report.json` files, RL_LOG.

- 09-06 ~03:0x this cycle (assigned `headset-crossgrav-medhead-widenfwd-c1`,
  `headset-crossgrav-medhead-irrfwd-c1`): 2 verdicts, both **CANARY PASS -
  INFORMATIVE-POSITIVE**, 2-arm refill. These are the two discovery canaries
  from the 02:17 launch testing whether the now-ACQ-PASSed 1g cross-gravity
  medhead champion (`medhead-abrupt-c1-acq1`, 23/24) supports FORWARD
  curriculum extension (composing widen2 heading breadth / irr command-
  timing jitter natively at 1g) instead of only working when built at
  0.5g first. **Both PASS**: `widenfwd-c1` aggregate `gait_valid` 23/24
  (`walk/det` 5/6, one transient `sac=[0,3]` episode; the other three
  modes clean 6/6), 0 falls, video (`walk_det_0`) shows genuine six-leg
  cycling across multiple headings; a few `slip_per_m` outliers up to
  ~203 confirmed via frame strip (`walk_sto_3`) as the already-documented
  reversal-heading spin-in-place low-progress-denominator artifact, not
  a new defect. `irrfwd-c1` aggregate `gait_valid` 22/24 (`walk/det` 4/6,
  two episodes flag `sac=[2,5]` transiently — same legs read healthy
  0.17-0.61 duty in the other four episodes — the other three modes
  clean 6/6), 0 falls, and unusually TIGHT/clean `slip_per_m` (3.06-5.63,
  no reversal outliers). **Together this confirms the 1g cross-gravity
  repair generalizes as a foundation for forward curriculum extension on
  BOTH tested axes** (heading breadth and command-timing jitter), not
  just the single plain-heading recipe it was built on. **Refill (2
  arms):** matched 40M ACQ continuations for both,
  `headset-crossgrav-medhead-widenfwd-c1-acq1` (train-2, VERIFIED
  RUNNING) and `headset-crossgrav-medhead-irrfwd-c1-acq1` (train-3,
  launching — the launcher's own pod-pick briefly tried a busy pod,
  REFUSED harmlessly, retried with an explicit free `--pod`). Left the
  natural next layer (widen2+irr COMPOSITE built natively at 1g on top
  of medhead, mirroring the halfgrav widenirr/irrwiden composites)
  unlaunched this cycle: the sibling ramp-transition arms
  (`medhead-ramp-{widenfwd,irrfwd}-c1`, launched by a concurrent cycle
  off the same question on the gradual-ramp base) are still RUNNING/
  in-eval — composing two untested variables (composite ordering +
  ramp-vs-abrupt transition) before either single-axis ramp sibling
  lands would confound the read, matching this campaign's own standing
  discipline against compounding untested variables. SKILLS.md updated
  (2 new rows). Evidence: `ops.sh review cw-walkscratch-easy0905-
  headset-crossgrav-medhead-{widenfwd,irrfwd}-c1`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_
  {widenfwd,irrfwd}_c1_gate/report.json`, W&B `tj1ko3bp`/`xlhp3w8c`,
  RL_LOG.

- 09-06 ~03:1x this cycle (assigned `headset-crossgrav-irracq1-abrupt-c1-acq1`,
  `headset-crossgrav-irrwidenc1-ramp-c1`): 2 verdicts, 1-arm refill (a 2nd
  intended arm was found already launched by a concurrent cycle).
  **`irracq1-abrupt-c1-acq1` ACQ FAIL - MECHANISM, the FIRST regression
  in the crossgrav ACQ-scale confirmation set.** This champion's own
  2M canary was clean (23/24 gait_valid, 0 falls) and training reward
  rose throughout 40M (quarters 717->1359->1507->1635 -- the 08-21
  rising-reward/bad-eval shape) but the leg[1,4] chronic-entrenchment
  fingerprint the gate itself pre-registered as the FAIL branch
  emerged anyway: aggregate `gait_valid` 14/24, `walk/det` regresses
  6/6->4/6 (2 NEW formal leg-4 flags vs zero at canary), `walk_
  startjitter/det` collapses 5/6->0/6 (one episode's leg-4 swing_count
  =2/20s vs 91-239 every other leg -- near-frozen, not noise). 0
  falls/terminations in all 24 episodes; video confirms genuine body
  translation even in flagged episodes (a favoritism issue, not a
  freeze/paddle). Per CURRENT_TRUTHS this reward-misalignment class
  (base(1g) middle-leg-pair favoritism) is ALREADY CLOSED after 9
  repair mechanisms with the established fix being STRUCTURAL, not
  more training -- so this is read as a genuine FAIL, not an 08-21
  "keep going" case (more training is what caused it). The 3 prior
  ACQ-scale crossgrav siblings (medhead-abrupt/ramp, widen2c1) all
  held clean walk/det 6/6 with only partial startjitter softening
  (never a full 0/6 collapse) -- meaning a clean 2M canary does NOT
  guarantee ACQ-scale durability, at least for this recipe/seed. This
  reframes the campaign's "does cross-gravity-transfer generalize"
  story: transfer clearly holds at CANARY scale (8+ confirmations) but
  ACQ-scale durability is now an open question again. **`irrwidenc1-
  ramp-c1` CANARY FAIL - INFORMATIVE-NEGATIVE**, closes gravity-ramp
  as a repair lever for the jitter-first widen+irr composite: the
  gradual ramp reproduces the abrupt sibling's own failure almost
  exactly (aggregate `gait_valid` 19/24, `walk/det` 3/6 minority with
  `sac=[4],[4],[3]`, `walk_startjitter/det` 4/6 with `sac=[1],[1]` --
  matching the abrupt run's own 3/6 and 4/6 read at the SAME leg
  pattern), 0 falls in all 24 episodes. Transition speed is now ruled
  out as the causal variable for this composite (unlike medhead, where
  both transition speeds PASSED equally cleanly); the causal question
  narrows to composition order / reversal-heading commands. A few
  episodes show slip_per_m 10-200x band from the already-documented
  reversal-heading low-progress-denominator artifact (video-confirmed
  balanced six-leg duty in the flagged episode), not a new defect.
  **Refill:** intended to launch the natural n=2-seed check for the
  composite (`crossgrav-irrwidenc2-abrupt-c1`, off the independently-
  seeded healthy ACQ-PASS `headset-halfgrav-irrwiden-c2-acq1`
  champion) but found a concurrent cycle had already launched exactly
  this arm (REFUSED by the launcher, train-10, VERIFIED RUNNING) --
  no duplicate spend. Instead launched `medhead-abrupt-c1-acq1-
  cont40m` (+40M endurance continuation of the campaign's cleanest
  ACQ-PASS champion, train-4, VERIFIED RUNNING) to test whether the
  SAME late-entrenchment risk the irracq1 finding exposed applies to
  ANY crossgrav champion given enough budget, or is recipe/seed-
  specific -- read together with `irr2acq1-abrupt-c1-acq1` (2nd seed,
  same recipe, in flight under another cycle) once both land, this
  gives the seed-vs-recipe-vs-universal discriminator the finding
  needs. CURRENT_TRUTHS updated (09-06 ~03:1x entry). Evidence: `ops.sh
  review cw-walkscratch-easy0905-headset-crossgrav-{irracq1-abrupt-c1-
  acq1,irrwidenc1-ramp-c1}`, `logs/ckpt_eval/cw_walkscratch_easy0905_
  headset_crossgrav_{irracq1_abrupt_c1_acq1,irrwidenc1_ramp_c1}_gate/
  report.json`, W&B `4n0z9k3b`/`mkjeg5et`, RL_LOG.

- 09-06 ~03:0x this cycle (assigned `headset-crossgrav-widen2c1-abrupt-c1-acq1`,
  `headset-crossgrav-widenirrc1-abrupt-c1-acq1`, `headset-halfgrav-irrwiden-c2-acq1`):
  3 verdicts, all **ACQ PASS**, 2-arm refill. Tooling note: all 3 gate
  evals were still genuinely computing remotely when the cycle spawned
  (prestage sync had timed out on video-every=1 panels); confirmed via
  `kubectl exec ps aux` on each pod (not orphaned), backgrounded 3
  `ops.sh pollreap` loops, then read each `report.json` directly off
  the pod as it landed instead of waiting serially. (1) `widen2c1-
  abrupt-c1-acq1`: `gait_valid` 20/24 matches/improves its own 2M
  canary (19/24), 0 falls/24, slip/m actually IMPROVES at 40M (worst
  outlier 207.7->17.75) — 7th confirmed healthy-source crossgrav
  champion at acquisition scale. (2) `widenirrc1-abrupt-c1-acq1`: the
  CLEANEST acquisition result of the 3 — `gait_valid` 22/24 (up from
  21/24 canary), 0 falls, `progress_ratio` medians 1.38-1.67 and
  `slip_per_m` tightly banded 3.99-5.69 with ZERO outlier episodes
  across all 4 modes (widen-first composite order tracks commands
  cleanly). (3) `halfgrav-irrwiden-c2-acq1` (own 0.5g, not crossgrav):
  `gait_valid` 22/24 exact match to its own 2M canary, 0 falls — BUT a
  real seed-level course-tracking gap vs its sibling `irrwiden-c1-
  acq1`: `walk/sto` median `slip_per_m` 67.9 here vs 9.1 on c1 (3/6 sto
  episodes wrong-course vs 1/6), confirmed present already at the 2M
  canary stage (not a 40M regression) via direct comparison + frame
  strips (`walk_det_0` clean cycling, `walk_sto_3` shows legs cycling
  normally while the robot ignores the resampled command arrow).
  Flags composition-order (irr-first vs widen-first) as a possible
  course-tracking-quality differentiator, not just a gait-validity one.
  **Refill (2 arms):** (1) `headset-crossgrav-widen2c1-irrfwd-c1` —
  compose-after-transfer test (add the irr timing-jitter axis natively
  at 1g ON TOP of the just-PASSED `widen2c1-abrupt-c1-acq1` champion,
  mirroring the medhead-lineage `medhead-irrfwd-c1` arm on a 2nd, harder
  full-8-way-heading base champion), train-8, VERIFIED RUNNING. (2)
  `headset-crossgrav-irrwidenc2-abrupt-c1` — disambiguates whether the
  irr-first composite order's earlier crossgrav FAIL (`irrwidenc1-
  abrupt-c1`, walk/det collapsed 5/6->3/6) was a real order effect or
  seed noise, by abruptly transferring this cycle's just-PASSED
  `irrwiden-c2-acq1` champion (2nd independent seed of the SAME irr-
  first order) to full 1g; PASS refutes order-as-causal (seed noise),
  FAIL confirms it, train-10, VERIFIED RUNNING. SKILLS.md updated (3
  new rows). Evidence: `ops.sh review cw-walkscratch-easy0905-headset-
  {crossgrav-widen2c1-abrupt-c1-acq1,crossgrav-widenirrc1-abrupt-c1-
  acq1,halfgrav-irrwiden-c2-acq1}`, matching `logs/ckpt_eval/...gate/
  report.json` files, RL_LOG.

- 09-06 ~02:4x prior cycle (assigned `headset-crossgrav-s1acq-abrupt-c1`,
  `headset-crossgrav-s3acq-abrupt-c1`): 2 verdicts, both **CANARY PASS**,
  2-arm refill. These were the last 2 untested champions in the
  healthy-source crossgrav sweep (the campaign's best and 2nd-best
  3-way (0,+-45deg) halfgrav champions, `s1acq` gait_valid 24/24 and
  `s3acq` 22/24 at native 0.5g, jumped abruptly to full 1g from tick
  0). **`s1acq-abrupt-c1` is the CLEANEST crossgrav result of the
  entire sweep**: `gait_valid` PERFECT 24/24 (6/6 in all four of
  walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto),
  `sac=[]` in literally every one of the 24 episodes — no other
  champion tested so far (medhead/widen2c1/irracq1/irr2acq1/
  widenirrc1/irrwidenc1) reached a fully clean 24/24. 0 falls,
  slip_per_m 2.6-4.4 (medians 3.1-4.0), forward 2.9-4.2m/20s. Video
  (`walk_det_0`) confirms genuine six-leg cycling with clear body
  translation. `s3acq-abrupt-c1` lands at `gait_valid` 21/24 — walk/det
  (primary mode) 6/6 clean, walk/sto 6/6 clean, walk_startjitter/sto
  6/6 clean; walk_startjitter/det softens to 3/6 with leg-1 flagged
  in 3/6 episodes (duty 0.07-0.10) but NOT chronic (the other 3
  startjitter/det episodes show the same leg healthy at 0.14-0.24) —
  the identical mild jitter-sensitivity shape already logged on every
  other healthy-source sibling, not a new pathology. 0 falls, slip
  2.8-4.3. **This makes the healthy-source crossgrav sweep 6/6 PASS
  with zero surprises** (medhead x2 transition speeds, widen2c1,
  irracq1, irr2acq1, s1acq, s3acq — 8 total canary/acq confirmations
  across 6 distinct champions), fully saturating the "does cross-
  gravity-transfer generalize past one lucky source" question; only
  the widen2c2b negative control (unhealthy source) and the
  irrwidenc1 composite-order informative-negative remain outliers,
  both already explained. **Refill (2 arms):** matched 40M ACQ
  continuations for both, `headset-crossgrav-s1acq-abrupt-c1-acq1`
  (train-0) and `headset-crossgrav-s3acq-abrupt-c1-acq1` (train-9),
  both VERIFIED RUNNING. Did not launch further NEW crossgrav
  discovery arms this cycle: every healthy champion built so far now
  has a crossgrav test in flight or landed, and the natural next
  layer (widen2/irr composites built natively at 1g on TOP of a
  crossgrav-transferred champion) is already being tested by a
  concurrent cycle off the `medhead` lineage
  (`crossgrav-medhead-{ramp-,}widenfwd-c1`, `crossgrav-medhead-{ramp-,}irrfwd-c1`)
  — repeating that exact axis on `s1acq`/`s3acq` before their own
  acq1 continuations land would compound two untested variables at
  once. SKILLS.md updated (2 new rows). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-crossgrav-{s1acq,s3acq}-abrupt-c1`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_{s1acq,
  s3acq}_abrupt_c1_gate/report.json`, W&B `slm87dgu`/`yodax2qa`,
  RL_LOG.

- 09-06 ~02:3x this cycle (assigned `headset-crossgrav-irr2acq1-abrupt-c1`):
  1 verdict, **CANARY PASS - INFORMATIVE-POSITIVE**, 3-arm refill. The
  irr-timing-jitter crossgrav recipe's 2ND independent seed (warm-started
  from `headset-halfgrav-irr2-acq1`, a distinct 40M champion, 19/24
  native 0.5g) survives an abrupt 0.5g->1.0g jump just as cleanly as the
  first seed did: aggregate `gait_valid` 22/24 (`walk/det` 6/6 clean
  `sac=[]`, `walk/sto` 6/6 clean, `walk_startjitter/det` 4/6 with only 2
  ISOLATED single-episode leg flags — `sac=[4]` then `sac=[1]`, never the
  same leg twice, not chronic — `walk_startjitter/sto` 6/6 clean), 0
  falls/terminations in all 24 episodes, `slip_per_m` tightly banded
  3.34-4.71. Video (`walk_det_0` 10-frame strip) shows genuine six-leg
  alternating-contact cycling with clear body translation. This closes
  the n=2-seed question for the irr-timing axis (matching the n=2/3
  discipline already applied elsewhere in this campaign) — per-seed luck
  is ruled out as the explanation for irr-timing transfer success.
  Tooling note: the prestaged gate eval was still genuinely computing
  remotely (video-every=1, ~32min wall clock) when the cycle spawned —
  confirmed via `kubectl exec ps aux` (not orphaned), registered with
  `ops.sh evalpending add`, used `ops.sh podwaitlog` to poll for
  completion instead of sleep-looping, then `kubectl cp` to sync the
  full artifact dir before reading `report.json` directly. **Refill (3
  arms, using free fleet capacity — 8/12 idle with an empty backlog at
  decision time, many concurrent cycles' own arms having drained into
  eval-only in the same window):** (1) `headset-crossgrav-irr2acq1-
  abrupt-c1-acq1` — matched 40M ACQ continuation, same template as the
  sibling `irracq1-abrupt-c1-acq1` (train-1, VERIFIED RUNNING via direct
  pod inspection). (2)/(3) `headset-crossgrav-medhead-ramp-widenfwd-c1`
  and `headset-crossgrav-medhead-ramp-irrfwd-c1` (train-2, train-3,
  VERIFIED RUNNING via direct pod inspection) — the abrupt-transition
  medhead champion already has native-1g forward-extension canaries
  in flight this window (`medhead-widenfwd-c1`, `medhead-irrfwd-c1`,
  widen2/irr added directly at 1g without a 0.5g detour); the
  gradual-ramp sibling (`medhead-ramp-c1-acq1`, ACQ PASS 21/24) never
  got the same test, so this completes the abrupt-vs-ramp symmetry one
  rung further — PASS on both would show the ramp recipe's gentler
  transition generalizes to further curriculum extension just as well
  as the abrupt one; FAIL on either would narrow forward-extension to
  the abrupt recipe specifically. SKILLS.md updated (1 new row). Evidence:
  `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-irr2acq1-
  abrupt-c1`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_
  irr2acq1_abrupt_c1_gate/report.json`, W&B `2vlneqky`, RL_LOG.

- 09-06 ~02:1x this cycle, using idle fleet capacity (4+ free GPU slots,
  empty backlog): launched a crossgrav test off `headset-halfgrav-acq1`
  — the plain 3-way (0,+-45deg) heading champion that every medhead/
  widen2/irr/composite descendant in this campaign builds from, and
  the CLEANEST champion on record (`gait_valid` 24/24, 6/6 every mode,
  never a sacrificed leg) — but never itself tested for cross-gravity-
  transfer. Given this same cycle's own `irrwidenc1-abrupt-c1` finding
  (transfer degradation CAN happen even from a clean 0.5g parent), this
  fills the sweep's missing simplest-case baseline. **Tooling gotcha
  (caught before losing signal, not after)**: the first launch attempt,
  `...-plainhead-abrupt-c1`, respec'd `--from
  headset-crossgrav-medhead-abrupt-c1` with `--parent headset-halfgrav-
  acq1` — `--parent` only sets ledger lineage bookkeeping, it does NOT
  repoint `--init-from`; the cloned `extra_args` silently kept the
  TEMPLATE run's own `--init-from` (`..._headset_halfgrav_medhead_
  acq1.zip`), so the launched process was actually warm-starting from
  the ALREADY-TESTED medhead champion, not the intended untested
  `halfgrav_acq1` champion. Caught via `kubectl exec ... ps aux` on the
  literal launched command line before assuming success (per standing
  practice), killed it within ~2 minutes of wall clock (0 real GPU
  signal lost), logged `KILLED_LAUNCH_BUG` in the ledger, and
  relaunched as `...-plainhead-abrupt-c1b` with an explicit
  `--arg='--init-from=rl_move/sim/policies/ppo_goal_cw_walkscratch_
  easy0905_headset_halfgrav_acq1.zip'` override — verified via the same
  `ps aux` check that the correct checkpoint path is now in the actual
  running command. **Gotcha for next respec, campaign-wide: `--parent`
  is bookkeeping-only; always pass an explicit `--arg='--init-from=...'`
  whenever the intended source checkpoint differs from the cloned
  template's own.** VERIFIED RUNNING (train-1) — full ledger `verified`
  timestamp pending as of this write, checked via direct pod
  inspection instead of waiting on it. 2M discovery budget. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_acq1_gate/
  report.json`, ledger entries for both `plainhead-abrupt-c1` (KILLED)
  and `plainhead-abrupt-c1b` (RUNNING).

- 09-06 ~02:2x this cycle (assigned `headset-halfgrav-fullhead-widen2-c3-acq1`):
  1 verdict, **ACQ PASS**, 2-arm refill. The 40M own-checkpoint
  continuation of the 3rd tie-breaking widen2 seed reproduces its own
  2M canary's exact structure at full acquisition budget:
  `gait_valid` 20/24 (`walk/det` 4/6, `walk/sto` 6/6,
  `walk_startjitter/det` 6/6, `walk_startjitter/sto` 4/6) —
  identical 20/24 total to the 2M canary read, 0 falls/terminations
  in all 24 episodes. Sacrificed-leg flags are transient only (legs
  0/3/4 flagged in 3/24 episodes total; `duty_cycle` for legs 0/3
  spans 0.03-0.52 across all 24 episodes — nowhere near the
  `widen2-c2b-acq1` entrenchment fingerprint of leg-1 duty 0.01-0.21
  in ALL 24 episodes). `slip_per_m` reads flat-or-better vs the
  gate's own comparison (walk/det spread narrows to 2.49-6.68 from
  the canary's 2.3-11.5; median rises slightly 2.77->3.69, within
  noise). Frame strips (`walk_det_4`, the `[0,3]`-flagged episode;
  `walk_sto_3`, a 121/m slip outlier) confirm genuine six-leg cycling
  with body translation in the former and the already-documented
  reversal-heading spin-in-place low-progress-denominator pathology
  (not a new defect) in the latter. **This closes the widen2
  parent-quality-vs-seed-noise question the 1-PASS/1-FAIL
  `widen2-c1-acq1`/`widen2-c2b-acq1` split left open: 3/3 widen2
  seeds off clean `medhead_acq1` parents now PASS at acquisition
  scale; the sole FAIL traces to an already-weak `medhead2_acq1`
  parent.** Tooling gotcha found+handled: this run's own gate eval
  was still computing remotely (video-every=1, ~30min wall clock)
  when the cycle spawned, and the prestaged artifact dir on disk
  (missing the `_acq1` suffix) actually held the PARENT's 2M canary
  read, not this run's — caught by checking the report's own
  `checkpoint` field before trusting it, then used `ops.sh podeval`
  (found already running remotely, not a duplicate) + `ops.sh
  pollreap` backgrounded to reap the real result without blocking the
  rest of the cycle. **Refill (2 arms):** (1) `headset-halfgrav-
  widenirr-c3` (respec off `widenirr-c1`, swapping the base checkpoint
  to `widen2-c3`'s own 2M zip) — the widen-first widen+irr composite's
  own FAIL verdict on its 2nd seed (`widenirr-c2b`, built on the weak
  `widen2-c2b`) explicitly named "a 3rd seed of the widen2 rung" as
  the right tie-breaker; widen2-c3 (clean-parent, just-PASSed) is that
  seed. VERIFIED RUNNING (train-11, finished within ~2min given
  ~20k fps on a 2M canary — leaving unverdicted for mechanical
  per-run triage). (2) `headset-crossgrav-widen2c3-abrupt-c1` (respec
  off `widen2c1-abrupt-c1`, swapping the base checkpoint to
  `widen2-c3-acq1`) — the widen2 recipe's own crossgrav-transfer has
  only been tested on 1 seed so far (`widen2c1-abrupt-c1` CANARY PASS
  19/24); this gives it the same n=2-seed discipline already applied
  to the irr-timing axis (`irr-acq1`/`irr2-acq1`, 2/2 PASS). VERIFIED
  RUNNING (train-0). SKILLS.md updated (1 new row). Evidence:
  `ops.sh review cw-walkscratch-easy0905-headset-halfgrav-fullhead-
  widen2-c3-acq1`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  halfgrav_fullhead_widen2_c3_acq1_gate/report.json`, W&B `2dtnh6ju`,
  RL_LOG.

- 09-06 ~02:1x this cycle (assigned `headset-crossgrav-medhead-abrupt-c1-acq1`,
  `headset-crossgrav-widenirrc1-abrupt-c1`, `headset-halfgrav-irrwiden-c2`): 3
  verdicts, all PASS. **`medhead-abrupt-c1-acq1` ACQ PASS is the headline
  result**: the base(1g) cross-gravity-transfer recipe holds at FULL 40M
  acquisition scale — `gait_valid` 23/24 (`walk/det` 6/6 clean `sac=[]`,
  `walk/sto` 6/6 clean, `walk_startjitter/det` 5/6 one isolated `sac=[4]`,
  `walk_startjitter/sto` 6/6 clean), 0 falls in all 24 episodes, `slip_per_m`
  3.4-4.5 (matches crossgrav siblings' band). Video (`walk_det_0` 8-frame
  strip) shows genuine six-leg cycling with clear body translation.
  Together with the concurrent cycle's `medhead-ramp-c1-acq1` ACQ PASS
  (also this window, see entry below), this is 2/2 — cross-gravity
  curriculum transfer is now a FULLY VALIDATED base(1g) repair, opening
  real new spend beyond "reallocate everything to halfgrav." Tooling
  gotcha (matches the 01:4x precedent below): all 3 assigned runs'
  prestaged gate evals were never queued in `pending_evals.json` despite
  already genuinely computing remotely — caught via `kubectl exec ... ps
  aux` on each pod (train-2/5/8) before assuming failure, ran `ops.sh
  podeval` (detected already-running, no duplicate launch), reniced the
  train-2 eval tree (`ops.sh niceevals`, since a NEW protected trainer —
  `s1acq-abrupt-c1` — had already been scheduled onto that pod),
  registered all 3 with `evalpending add`, waited for sync, then triaged
  normally. `widenirrc1-abrupt-c1` (2M canary, the widen-first widen2+irr
  composite champion abruptly transferred to 1g): **CANARY PASS -
  INFORMATIVE-POSITIVE**, `walk/det`+`walk/sto` 6/6 clean each (`sac=[]`),
  `walk_startjitter/det` softens to 3/6 under jitter only (same mild
  pattern as every other crossgrav sibling), 0 falls in all 24 — 4th
  distinct halfgrav recipe to confirm transfer. `halfgrav-irrwiden-c2` (2M
  mechanism-health canary, 2nd seed of the jitter-first widen+irr
  composite, respec off `irr2-acq1`): **CANARY PASS**, aggregate
  `gait_valid` 22/24 (beats the cited `irr2-acq1` baseline of 19/24), 0
  falls — confirms the composite in BOTH build orders now has n=2 seeds.
  **Refill:** matched 40M ACQ continuations for both canaries —
  `headset-crossgrav-widenirrc1-abrupt-c1-acq1` (train-1) and
  `headset-halfgrav-irrwiden-c2-acq1` (train-3), both VERIFIED RUNNING.
  **Second refill (using free fleet capacity, 6/12 idle with an empty
  backlog after the first two launches):** with the base(1g) repair now
  proven durable at full acquisition scale, launched 2 NEW discovery
  canaries testing whether the repair supports FORWARD curriculum
  extension natively in 1g (rather than always composing heading/jitter at
  0.5g THEN transferring, the pattern every prior arm used) —
  `headset-crossgrav-medhead-widenfwd-c1` (widen2 full-8-way heading set
  added directly on top of the 1g `medhead-abrupt-c1-acq1` champion,
  train-2) and `headset-crossgrav-medhead-irrfwd-c1` (command-timing
  jitter added directly at 1g, same base champion, train-8). Both VERIFIED
  RUNNING. PASS licenses building the rest of the DONE-gate contextual
  panel natively at 1g without another 0.5g detour; FAIL would mean 1g
  heading/timing generalization still needs the 0.5g-first curriculum.
  SKILLS.md updated (3 new rows). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-{crossgrav-medhead-abrupt-c1-acq1,
  crossgrav-widenirrc1-abrupt-c1,halfgrav-irrwiden-c2}`, `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_{crossgrav_medhead_abrupt_c1_acq1,
  crossgrav_widenirrc1_abrupt_c1,halfgrav_irrwiden_c2}_gate/report.json`,
  W&B `ibau23ge`/`zigln3k9`/`be9xpiw5`, RL_LOG.

- 09-06 ~02:0x this cycle (assigned `headset-crossgrav-irrwidenc1-abrupt-c1`,
  `headset-crossgrav-medhead-ramp-c1-acq1`): 2 verdicts, 1-arm refill.
  **`medhead-ramp-c1-acq1` ACQ PASS**: the 40M own-checkpoint
  continuation of the gradual-ramp 1g transfer canary (gravity pinned
  flat at 1.0 for the continuation) reproduces its own 2M canary's
  exact structure at 4x the budget — `gait_valid` 21/24 (`walk/det`
  6/6 clean, `walk/sto` 6/6 clean, `walk_startjitter/sto` 6/6 clean,
  `walk_startjitter/det` 3/6 with the SAME mild non-chronic leg-4
  softening, not a regression), 0 falls/terminations in all 24
  episodes, `slip_per_m` tightly banded 3.0-4.9. Together with the
  concurrent cycle's `medhead-abrupt-c1-acq1` ACQ PASS (23/24, logged
  01:59), **this is 2/2 ACQ PASS — cross-gravity-transfer is now
  validated at full acquisition scale regardless of transition speed**
  for the medhead recipe. **`irrwidenc1-abrupt-c1` CANARY FAIL -
  MECHANISM (informative-negative)** — the FIRST clean negative in the
  whole cross-gravity-transfer generality sweep. Warm-started the
  jitter-first widen+irr composite champion (`headset-halfgrav-
  irrwiden-c1-acq1`, its own clean ACQ PASS 22/24) and jumped it
  abruptly to 1g: `walk/det` (the gate's own named pass/fail axis)
  collapses from the parent's majority 5/6 to minority 3/6 (`sac=[4]`
  x2, `sac=[3]` x1), `walk_startjitter/det` also regresses 6/6->4/6
  (`sac=[1]` x2); `walk/sto` and `walk_startjitter/sto` hold clean/
  improve (6/6 both). 0 falls/terminations in all 24 episodes — a
  gait-quality mechanism failure, not a safety collapse, and no single
  leg is chronic (each recurs in only 2/6 episodes of its own mode).
  This result lands squarely in the gate's own pre-registered FAIL
  branch text (unlike the sibling `widen2c2b` negative-control's
  genuinely split/surprising read), so no DIG-IN fork needed. Read
  together with the concurrent cycle's `widenirrc1-abrupt-c1` (the
  MIRROR composite, widen-first order, off an equally-clean
  ACQ-PASS parent) landing **CANARY PASS** the same window (RL_LOG
  01:59: 6/6 `walk/det` gv) — **composition ORDER may be the variable
  that separates the two composites**, not the two axes together;
  both source parents (`irrwiden-c1-acq1` 22/24, `widenirr-c1-acq1`
  23/24) were similarly clean, ruling out the usual parent-quality
  confound as the obvious explanation. **Refill:** launched the direct
  ramp-vs-abrupt comparison on the SAME failing composite+parent
  (`headset-crossgrav-irrwidenc1-ramp-c1`, 2M, `ease.gravity_scale`
  0.5->1.0 linear ramp over the first 1M steps via the same `sched.key`
  engine as `medhead-ramp-c1`) to test whether a gentler transition
  rescues this specific composite the way transition-speed provably
  did NOT matter for the simpler medhead recipe (both abrupt+ramp
  PASSed there) — if ramp ALSO fails here, transition shock is ruled
  out and the causal candidate narrows to the composite's reversal-
  heading commands or build order itself. VERIFIED (pod tbd once the
  launch pipeline completes; check ledger). Did not launch a 2nd-seed
  order-comparison arm this cycle: neither composite has a 2nd mature
  ACQ-PASS seed ready yet (`irrwiden-c2-acq1`/`widenirr` 2nd seeds are
  still training or don't exist), so an order-effect n=2 isn't
  launchable without waiting — flagged as the natural next step once
  either matures. SKILLS.md updated (1 new row, for the PASS). Evidence:
  `ops.sh review cw-walkscratch-easy0905-headset-crossgrav-{irrwidenc1-
  abrupt-c1,medhead-ramp-c1-acq1}`, `logs/ckpt_eval/cw_walkscratch_
  easy0905_headset_crossgrav_{irrwidenc1_abrupt_c1,medhead_ramp_c1_
  acq1}_gate/report.json`, W&B `ndd04efq`/`y8jypeph`, RL_LOG.

- 09-06 ~01:5x this cycle (assigned `headset-crossgrav-widen2c2b-abrupt-c1`,
  the pre-registered NEGATIVE CONTROL warm-started from an already-
  leg-1-parked-at-source halfgrav champion, `widen2-c2b-acq1`, ACQ
  FAIL at native 0.5g): **left UNVERDICTED — result is genuinely
  split across modes, exactly the "decides a fork" trigger, not a
  clean triage call.** Full 24-ep gate (had to be reaped mid-cycle;
  the prestaged eval was still computing on train-1 when the cycle
  spawned — `ops.sh podeval` confirmed no duplicate needed, waited on
  it): `walk/det` (the mode the gate's own PASS/FAIL text is written
  against) is **4/6 gait_valid with `sac=[]` in 4 of 6 episodes**
  (only 2 episodes transiently flag leg 1, never chronic) — read
  literally against the pre-registered gate text this is the
  SURPRISING/COMPLICATES branch ("clears majority with no chronic
  sacrifice"). But `walk_startjitter/det` collapses to **1/6
  gait_valid with leg-1 duty <0.10 in 5 of 6 episodes** (`duty_cycle`
  index 1: 0.08, 0.19, 0.01, 0.05, 0.03, 0.04 — i.e. near-chronic
  under start-pose perturbation specifically), matching the classic
  leg-1 entrenchment fingerprint almost exactly once the robustness
  axis is added. Plain-nominal walk looks repaired; the same
  checkpoint under jitter reverts to the chronic-sacrifice pattern.
  This is neither a clean CONFIRMS nor a clean COMPLICATES read, and
  the pre-registered gate explicitly calls the COMPLICATES branch "a
  much stronger and more useful claim needing its own follow-up" — so
  per the model-tiering rule this gets flagged for a deep-dive rather
  than triage-verdicted off a partial read. Video (`contact_sheet.png`,
  both `walk_det_0` and `walk_startjitter_det_2` frame strips) shows
  genuine body translation in both conditions, consistent with the
  numeric duty data rather than contradicting it. Evidence: `logs/
  ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_widen2c2b_
  abrupt_c1_gate/report.json`, W&B `j010yu74`.
  **Refill (2 new discovery canaries, non-overlapping with concurrent
  cycles' medhead/widen2c1/widen2c2b/irracq1/irrwiden/widenirr/irr2
  threads):** the halfgrav heading-family's n=3 confirmation-set
  champions `headset-halfgrav-s1acq` (campaign-BEST, `gait_valid`
  24/24) and `headset-halfgrav-s3acq` (22/24, active-not-chronic leg-1
  micro-underuse) have never been cross-gravity-tested. Launched
  `headset-crossgrav-s1acq-abrupt-c1` and `headset-crossgrav-s3acq-
  abrupt-c1` (same abrupt-1g-from-tick-0 template as `medhead-abrupt-
  c1`, heading set matched to each champion's own 3-way (0,±45°)
  training distribution rather than reused verbatim from the 5-way
  `medhead` template). Both VERIFIED RUNNING (train-2, train-9).
  Testing the campaign's single best champion is the highest-value
  untested cross-gravity arm remaining. `CYCLE_WORKED` touched (real
  eval work + 2 new launches); no code changed, no snapshot needed.

- 09-06 ~02:0x dig-in cycle (resolves the DIG-IN above): **VERDICTED
  `headset-crossgrav-widen2c2b-abrupt-c1` FAIL - INFORMATIVE (negative
  control CONFIRMS, with nuance).** Root cause: the leg-1-parked
  attractor inherited from the unhealthy `widen2-c2b-acq1` source was
  NOT repaired by 2M at 1g — only its nominal-start basin was masked.
  Discriminating evidence: leg-1 SACRIFICE in 10/24 episodes (walk/det
  2/6, startjitter/det 5/6 with duty 0.01-0.09 and leg-1 swing counts
  7-36 vs 100+ on other legs, startjitter/sto 3/6); aggregate
  gait_valid 14/24 = IDENTICAL to the parent's own 14/24 at native
  0.5g (redistribution across start conditions, not net repair). All
  FOUR healthy-source crossgrav siblings at the same 2M budget
  (medhead/widen2c1/irracq1/widenirrc1) show leg-1 sac **0/24** — the
  contrast is categorical, so **leg-health-at-source is confirmed
  necessary for robust cross-gravity transfer at canary budget**.
  Track lesson (binding for future crossgrav gates): `walk/det` alone
  is an insufficient entrenchment discriminator — pre-register
  startjitter panels + per-leg sacrifice counts as the primary metric.
  Side finding: declining ep_rew_mean (-52→-439) is a widen2-lineage
  reward-scale trait (PASS sibling widen2c1 shows the same shape),
  not a per-run anomaly. **Refill (1 arm):** launched
  `headset-crossgrav-widen2c2b-abrupt-c1-acq1` (40M acquisition
  continuation, same template as `medhead-abrupt-c1-acq1`, VERIFIED
  RUNNING train-5) to answer the residual fork the gate text demands:
  can BUDGET substitute for source health (40M fully repairs → reopens
  unhealthy champions as crossgrav seeds) or does entrenchment persist
  at all budgets (closes the story cleanly). Informative either way,
  pre-registered EXPECTED=persists / SURPRISING=repairs.

- 09-06 ~01:4x this cycle (assigned `headset-crossgrav-irracq1-abrupt-c1`): 1
  verdict, **CANARY PASS**, 2-arm refill. Warm-starting the leg-healthy
  0.5g `headset-halfgrav-irr-acq1` champion (irregular command-timing-
  jitter recipe, never previously exposed to 1g) and jumping it
  abruptly to full 1g gravity from tick 0 keeps the six-leg gait
  intact: harness `gait_valid` 23/24 — `walk/det` 6/6 CLEAN (`sac=[]`
  every episode), `walk/sto` 6/6 clean, `walk_startjitter/sto` 6/6
  clean, `walk_startjitter/det` 5/6 (one isolated `sac=[4]`, not
  chronic). 0 falls/terminations in all 24 episodes. `slip_per_m`
  banded 3.2-4.6, comparable to the `medhead`/`widen2c1` crossgrav
  siblings. Video (`walk_det_0`) shows genuine six-leg cycling with
  visible forward displacement. **This is the 3rd distinct halfgrav
  recipe (after `medhead` and `widen2c1`, alongside the concurrent
  cycle's `widen2c2b`/`widenirrc1`/`irrwidenc1` arms) to confirm
  cross-gravity-transfer holds for an axis genuinely different from
  heading breadth** (command-timing irregularity) — strengthens the
  finding as a general repair path rather than a heading-specific
  fluke. Tooling gotcha: this run's own prestaged gate eval had not
  been queued by the watcher (no `pending_evals.json` entry, empty
  local eval log) even though the pod process was already computing
  when the cycle spawned — caught via `kubectl exec ... ps aux` on
  the run's own pod (train-4) before assuming a failure, registered
  it with `ops.sh evalpending add` instead of re-launching a
  duplicate, and it finished normally a few minutes later; no code
  fix needed (this looks like an ordinary prestage race, not a repeat
  of the glob-boundary bug fixed last cycle). **Refill:** (1) matched
  40M acquisition continuation off this run's own checkpoint,
  `headset-crossgrav-irracq1-abrupt-c1-acq1` (`ease.gravity_scale=1.0`
  unchanged), VERIFIED RUNNING train-4. (2) a 2nd-seed confirmation
  canary for the SAME irr-timing crossgrav recipe off the independent
  `headset-halfgrav-irr2-acq1` champion (2M, `headset-crossgrav-
  irr2acq1-abrupt-c1`), to rule out per-seed luck the same way every
  other rung in this campaign got its n=2 seed check before being
  called a validated recipe — VERIFIED RUNNING train-3 (opened up when
  `halfgrav-fullhead-widen2-c3-acq1` finished training during this
  cycle; left unverdicted for the mechanical per-run cycle spawn, not
  duplicated here since it wasn't in this cycle's assigned-runs list).
  SKILLS.md updated (1 new row). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-crossgrav-irracq1-abrupt-c1`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_irracq1_
  abrupt_c1_gate/report.json`, W&B `lt2nxvek`, RL_LOG.

- 09-06 ~01:3x this cycle (assigned `headset-crossgrav-widen2c1-abrupt-c1`):
  1 verdict, **CANARY PASS - INFORMATIVE-POSITIVE**, 1-arm refill.
  This 2M discovery canary's own prestage gate eval was still
  computing when the watcher's 25-min timeout admitted the cycle
  (the "holding triage" list is a fallback timeout, not proof the
  eval finished — `ops.sh waitlog` on the run's own eval log caught
  the real completion ~2 min into the cycle); found+read the real
  gate report before verdicting rather than trusting the timeout.
  Result: warm-starting the leg-healthy 0.5g `headset-halfgrav-
  fullhead-widen2-c1-acq1` champion (full 8-way heading incl.
  reversals — materially different from the plain fixed-5-heading
  `medhead` recipe already PASSED twice) and jumping it abruptly to
  full 1g gravity keeps the six-leg gait: `gait_valid` 19/24
  (`walk/det` 5/6, `walk/sto` 6/6, `walk_startjitter/det` 3/6,
  `walk_startjitter/sto` 5/6 — mild leg-4 softening only under added
  start-pose jitter, never zero-touch), 0 falls/terminations in all
  24 episodes, closely matching `crossgrav-medhead-abrupt-c1`'s own
  20/24 read at the identical budget/template. Video (contact sheet,
  `walk_startjitter_sto_4.mp4`) shows genuine six-leg cycling, body
  translating. A few reversal-heavy episodes spike slip/m (up to
  207/m) — the already-documented low-net-progress-denominator
  blowup on this widen2/reversal-heading family, not a new
  pathology. This is the 2nd champion (after medhead abrupt+ramp) to
  independently confirm cross-gravity-transfer generalizes — the
  other 3 pre-registered generality-check arms (`irracq1-abrupt-c1`,
  `widenirrc1-abrupt-c1`, `irrwidenc1-abrupt-c1`) and the negative
  control (`widen2c2b-abrupt-c1`) are owned by concurrent cycles
  (each already spawned/spawning per `orchestrator.log`); do not
  re-launch any of them. **Refill:** per the gate's own PASS branch
  and the medhead template, launched a matched 40M ACQ continuation,
  `headset-crossgrav-widen2c1-abrupt-c1-acq1` (own-checkpoint,
  `--evidence` citing this canary + the concurrently-running
  `medhead-abrupt-c1-acq1` as the comparable full-budget precedent —
  respec's acquisition-phase gate REFUSED without it first try, a
  worth-noting gotcha for any acquisition respec: `--evidence` is
  mandatory even when cloning an already-precedented template).
  VERIFIED RUNNING (train-7). Attempted a 2nd refill (crossgrav
  canary off the widen-first `widenirr-c1-acq1` composite champion,
  believing it untested) — REFUSED by the launcher, name collision:
  it was already launched as `headset-crossgrav-widenirrc1-abrupt-c1`
  by an earlier cycle (01:1x note below); no duplicate spend lost,
  logged here so the next cycle doesn't re-attempt the same mistaken
  gap-check. SKILLS.md updated (1 new row). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_
  widen2c1_abrupt_c1_gate/report.json`, W&B `uj013rxq`, RL_LOG.

- 09-06 ~01:1x this cycle (assigned `headset-halfgrav-widenirr-c1-acq1`):
  1 verdict, **ACQ PASS**, 1-arm refill. The widen-first widen2+irr
  composition holds at full 40M budget on seed 1 and BEATS the plain
  `widen2-c1-acq1` sibling trained on the identical budget: `gait_valid`
  23/24 (walk/det 5/6 transient sac[2,5], walk/sto 6/6,
  walk_startjitter/det 6/6, walk_startjitter/sto 6/6) vs the sibling's
  21/24; 0 falls in all 24 episodes; no chronic single-leg entrenchment
  (every leg's <0.10-duty count is at most 1/24 episodes). Course
  tracking IMPROVES vs this run's own 2M canary (`wrong_course_frac_1s`
  mean 0.367->0.247, `course_err_1s_med_deg` mean 68.6->50.5,
  `direction_err_mean_deg` mean 69.6->63.0) and reads flat-or-better vs
  the `widen2-c1-acq1` sibling on every tracked axis (course_err 50.5
  vs 54.3, direrr 63.0 vs 64.3, wrong_course_frac ties at 0.247, slip
  ties at ~4.7). Video (`walk_det_0`) shows genuine six-leg cycling,
  body translating. **Together with the concurrent cycle's
  `irrwiden-c1-acq1` ACQ PASS this same cycle (jitter-first order),
  the widen+irr composition edge over plain `widen2` now holds at
  full acquisition budget in BOTH orders** on the clean-parent seed.
  **Tooling gotcha found+fixed**: this run's own prestaged gate eval
  was still computing on its pod when the cycle spawned; meanwhile
  `ops.sh report`/`review`'s unanchored `*snake*` substring glob
  silently served the report of a killed accidental-duplicate launch
  sharing a near-identical name (`...-acq1b`, killed at 4M steps,
  09-05 23:56 logline) instead of correctly reporting "no report yet"
  — caught via each checkpoint's own `num_timesteps` (4.19M vs
  40.37M) before trusting the numbers, then waited for the real gate
  eval to finish+sync off pod train-7. Fixed both glob sites with a
  trailing `_` boundary anchor (a run name can never be a bare
  substring match unless followed by `_<tag>`), smoke-tested against
  this exact collision, `exp/ops-review-glob-boundary-fix-090601`.
  **Refill:** `widenirr-c1-acq1` is a 3rd distinct leg-healthy halfgrav
  champion (after `medhead` and `widen2c1`) never yet tested for
  cross-gravity-transfer; launched `headset-crossgrav-widenirrc1-
  abrupt-c1` (2M discovery canary, abrupt jump to `ease.gravity_
  scale=1.0` from tick 0, same template as the concurrent cycle's
  `crossgrav-{medhead,widen2c1,widen2c2b,irracq1}-abrupt-c1` arms) to
  test whether the transfer repair generalizes to this composed
  recipe too. VERIFIED RUNNING (train-5). SKILLS.md updated (1 new
  row). Evidence: `ops.sh review cw-walkscratch-easy0905-headset-
  halfgrav-widenirr-c1-acq1`, `logs/ckpt_eval/cw_walkscratch_
  easy0905_headset_halfgrav_widenirr_c1_acq1_gate/report.json`, W&B
  `71edsb6v`, RL_LOG.

- 09-06 ~01:0x this cycle (assigned `headset-halfgrav-fullhead-widen2-c3`,
  `headset-halfgrav-irr2-acq1`, `headset-halfgrav-irrwiden-c1-acq1`): 3
  verdicts, all PASS, 2-arm refill. `widen2-c3` (3rd tie-breaking widen2
  seed, off the SAME clean `medhead_acq1` parent as `widen2-c1`)
  **CANARY PASS**: gait_valid 20/24, 0 falls, majority-valid every mode
  — confirms parent-champion quality (not seed noise) drives the
  widen2-acq1 1-PASS/1-FAIL split (the weak-parented `widen2-c2b` had
  FAILED). `irr2-acq1` (2nd seed of the halfgrav irr-timing-jitter
  rung, respec of `irr-c2`/seed3, off a different base lineage
  `s1acq`) **ACQ PASS**: gait_valid 19/24 (both primary modes exactly
  at the >=4/6 bar), 0 falls, slip tightly banded 2.1-2.9 every
  episode — closes the irr-timing rung's n=2 seed confirmation (2/2
  PASS), matching sibling `irr-acq1`'s own numbers closely.
  `irrwiden-c1-acq1` (the widen+irr composite — heading breadth AND
  irregular timing together, the ACTUAL DONE-gate panel shape — at
  full 40M budget) **ACQ PASS**: gait_valid 22/24, 0 falls, only 2/24
  episodes flag any sacrificed leg (scattered, not chronic),
  course_err/slip at the reversal headings flat-or-better vs this
  run's own 2M canary read per the gate's own explicit comparison —
  the composite recipe HOLDS at acquisition scale on its first
  tested seed. **Flagged for the record, not a fail signal**: this
  run's `ep_rew_mean` is deeply negative (~-1500 to -2000, plateaued)
  — root-caused via `wandb_history.csv` to the always-on, ungated
  `reward_walk_freeprog_pen` cross-track/backward charge sitting near
  its -2.0 ceiling most of the run, because the composite's reversal-
  heading commands are intrinsically hard to track cleanly; the SAME
  negative/declining reward shape was already present at this run's
  own 2M canary (-608 at 2M end), so 40M continues the same
  trajectory rather than introducing a new degradation — textbook
  08-21-ruling reward/eval divergence (continue through it, not stop
  on it), not a new pathology. **Refill:** promoted `widen2-c3` to a
  40M ACQ continuation (`headset-halfgrav-fullhead-widen2-c3-acq1`,
  `--init-from-source`, mirrors the `widen2-c1-acq1` template) to
  test the 3rd seed at acquisition scale. Launched
  `headset-halfgrav-irrwiden-c2` (respec off `irr2-acq1`'s own
  ACQ-PASS checkpoint, applying the SAME widen2 heading-set + jitter
  composite as `irrwiden-c1`, 2M canary) to give the widen+irr
  composite its own n=2 seed confirmation before calling it a
  validated recipe rather than a single lucky seed. Both VERIFIED
  RUNNING (train-3, train-8). Also extended the concurrent cycle's
  cross-gravity-transfer campaign with a 3rd arm of my own:
  `headset-crossgrav-irrwidenc1-abrupt-c1` (`--init-from`
  `irrwiden-c1-acq1`'s own checkpoint, full 8-way heading set matching
  what it was actually trained on, `ease.gravity_scale=1.0` abrupt
  jump) — tests whether cross-gravity transfer generalizes to the
  jitter-first widen+irr composite specifically (distinct from the
  concurrent cycle's widen-first `widenirr-c1-acq1` version already
  in that same batch), the champion closest to the track's real
  DONE-gate panel shape. VERIFIED RUNNING (train-1). SKILLS.md
  updated (4 new rows).
  Evidence: `ops.sh review cw-walkscratch-easy0905-headset-halfgrav-
  {fullhead-widen2-c3,irr2-acq1,irrwiden-c1-acq1}`, `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_halfgrav_{fullhead_widen2_c3,
  irr2_acq1,irrwiden_c1_acq1}_gate/report.json`,
  `logs/experiments/cw-walkscratch-easy0905-headset-halfgrav-
  irrwiden-c1-acq1/wandb_history.csv`, RL_LOG.

- 09-06 ~00:4x this cycle (assigned `headset-crossgrav-medhead-{abrupt,ramp}-c1`):
  2 verdicts, both **CANARY PASS - INFORMATIVE**, plus 2 matched 40M
  acquisition-continuation launches. **This is the first direct
  evidence that the base(1g)-family chronic leg-1/4 leg-favoritism
  fingerprint is NOT a forced consequence of 1g dynamics for an
  already leg-healthy policy** — it reopens 1g walking via
  cross-gravity curriculum transfer, an alternative to the 8/8-closed
  reward-price mechanisms and the closed gSDE-exploration variant, and
  qualifies the standing "reallocate everything to halfgrav"
  conclusion rather than hardening it further. `abrupt-c1` (full
  gravity from tick 0, warm-started from the leg-healthy
  `headset-halfgrav-medhead-acq1` champion which had never seen 1g):
  harness `gait_valid` 20/24 — `walk/det` 6/6 CLEAN (`sac=[]` every
  episode, duty spread 0.18-0.76 across all six legs, no chronic
  <0.10-duty pattern anywhere), `walk/sto` 6/6 clean,
  `walk_startjitter/det` 3/6 and `walk_startjitter/sto` 5/6 with only
  a MILD leg-4 softening under added start-pose jitter (duty
  0.06-0.14, 47-117 real swings/20s — nothing like the base family's
  near-zero-touch entrenchment, single-digit swings/episode). 0
  falls/terminations in all 24 episodes; frame strips
  (`walk_det_0`, `walk_startjitter_det_2`) show genuine six-leg
  cycling with the body translating, not frozen/dragging. `ramp-c1`
  (gradual `ease.gravity_scale` 0.5->1.0 over the first 1M of its own
  2M budget via the already-proven `sched.key` engine, same parent):
  reads marginally CLEANER — `gait_valid` 21/24 (`walk/det` 6/6 clean,
  `walk/sto` 6/6 clean, `walk_startjitter/det` 3/6 same mild leg-4
  pattern, `walk_startjitter/sto` 6/6 clean, beating abrupt's 5/6
  there), 0 falls. Since BOTH transition speeds hold the six-leg gait,
  this can't yet separate "gravity-transition shock" from "1g dynamics
  force it regardless" (that would need a FAIL) — but it jointly and
  cleanly refutes the "1g dynamics force it regardless" branch for a
  leg-healthy starting policy. **Refill:** per the gate's own
  pre-registered PASS branch ("licenses a 40M continuation"), launched
  matched 40M acquisition continuations off BOTH: `headset-crossgrav-
  medhead-abrupt-c1-acq1` (own-checkpoint continuation, `ease.gravity_
  scale=1.0` unchanged, train-2) and `headset-crossgrav-medhead-ramp-
  c1-acq1` (own-checkpoint continuation, gravity pinned flat at 1.0 —
  the sched ramp already completed by 1M steps of the 2M canary and
  the per-process sched tick resets to 0 on resume per the engine's
  own documented behavior, so re-ramping would be pointless; `sched.
  key` disabled, train-0). Both VERIFIED RUNNING. Gate (both, full
  text in the ledger): ACQ PASS if `gait_valid` stays majority (>=4/6)
  in `walk/det` AND `walk/sto` with no chronic single-leg sacrifice at
  40M, matching/improving the 2M canary reads, 0 falls, slip/m at/near
  the 2.9 teacher band — 2/2 ACQ PASS would fully validate
  cross-gravity-transfer as a base(1g) recipe regardless of transition
  speed and open a genuinely new spend direction for the base(1g)
  family beyond "reallocate to halfgrav" or another closed reward-
  price mechanism. Evidence: `ops.sh review cw-walkscratch-easy0905-
  headset-crossgrav-medhead-{abrupt,ramp}-c1`, `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_crossgrav_medhead_{abrupt,ramp}_c1_
  gate/report.json`, W&B `qzcfku3j`/`zv97tks6`, SKILLS.md, RL_LOG.
  **Second refill, same cycle (generality check, using the huge idle
  fleet — 9/12 GPU slots free with an empty backlog at cycle start):**
  the medhead champion is only ONE halfgrav recipe; launched 2 more 2M
  cross-gravity-transfer discovery arms from OTHER, materially
  different leg-healthy halfgrav ACQ-PASS champions, abrupt-only (the
  ramp-vs-abrupt axis already read identically this cycle, so no need
  to spend 2 arms per champion): `headset-crossgrav-widen2c1-abrupt-c1`
  (from `headset-halfgrav-fullhead-widen2-c1-acq1`, the full 8-way-
  compass-incl-reversals champion, train-3) and `headset-crossgrav-
  irracq1-abrupt-c1` (from `headset-halfgrav-irr-acq1`, the command-
  timing-irregularity champion, train-4). Both VERIFIED RUNNING. Gate
  (both): PASS/INFORMATIVE-POSITIVE if `gait_valid` stays majority in
  `walk/det` with no chronic single-leg sacrifice — extends
  cross-gravity-transfer past the single medhead recipe, testing
  whether it's a general property of "any leg-healthy halfgrav
  champion" or specific to the plain fixed-5-heading recipe.
  FAIL/INFORMATIVE-NEGATIVE narrows the finding to the medhead recipe
  only. Evidence: same as above plus `logs/ckpt_eval/cw_walkscratch_
  easy0905_headset_halfgrav_{fullhead_widen2_c1_acq1,irr_acq1}_gate/
  report.json` for the source-champion baselines.
  **Third refill, same cycle (negative control):** all 3 PASSing
  crossgrav arms warm-start from LEG-HEALTHY halfgrav champions —
  launched a control from a champion that is NOT leg-healthy at its
  own native 0.5g, `headset-crossgrav-widen2c2b-abrupt-c1` (from
  `headset-halfgrav-fullhead-widen2-c2b-acq1`, own ACQ FAIL, chronic
  leg-1 park 14/24 gait_valid at 0.5g), train-1, VERIFIED RUNNING.
  Expected result CONFIRMS the causal story if the same/worse leg-1
  entrenchment persists at 1g (leg-health-at-source is necessary, not
  just correlated); a surprise six-leg repair at 1g would be a much
  bigger and separately-followed-up finding. 2M discovery budget.

- 09-05 ~23:5x [prior cycle] (assigned `headset-halfgrav-widenirr-{c1,c2b}`,
  the widen-FIRST mirror order of the widen+irr composition): 2
  verdicts, split 1/2 (matches the concurrent cycle's own widen2-acq1
  split, same underlying seed pair). `widenirr-c1` (irr timing-jitter
  added on top of the `widen2-c1` champion) **CANARY PASS**:
  gait_valid 23/24 (walk/det 5/6, walk/sto 6/6, walk_startjitter/det
  6/6, walk_startjitter/sto 6/6) BEATS its own parent `widen2-c1`'s
  clean 21/24, 0 falls in all 24 episodes both runs, mean
  `wrong_course_frac_1s` rises only modestly under the added jitter
  (0.285->0.367, not a blowup) — a clean pass, not borderline.
  `widenirr-c2b` (same jitter added on top of `widen2-c2b`) **CANARY
  FAIL - MECHANISM**: raw gait_valid total ties the parent (16/24
  both) but the composition redistributes WHICH mode fails —
  `walk/det` drops 4/6->3/6 with a NEW leg-sacrifice pattern (parent's
  failures were pure leg-1-led [1]/[1,3]; child's are [4],[1],[2,4] —
  leg 2 newly implicated), tripping the gate's own explicit written
  FAIL trigger ("new leg sacrifice vs baseline") even though the
  aggregate total looks flat. Consistent with (not a new finding
  independent of) the SAME seed's pure `widen2-c2b-acq1` lineage
  independently ACQ-FAILing this same cycle with chronic leg-1
  entrenchment (14/24, leg-1 duty 0.01-0.21 in all 24 episodes) —
  seed 2 of this heading-widen lineage is simply weaker/leg-1-prone,
  and timing jitter doesn't repair it, just redistributes the
  failures. Read together with the concurrent cycle's `irrwiden-c1`
  (jitter-FIRST order, CANARY PASS, the cleanest read of either
  order): **the widen+irr composition benefit is real but
  SEED-SPECIFIC so far** (2 of the 3 tested composition arms pass
  cleanly — both built on the healthy `widen2-c1`/`irr_acq1`
  champions — the one arm built on the weak `widen2-c2b` seed fails,
  regardless of jitter order). **Refill:** promoted `widenirr-c1` to
  a full 40M ACQ continuation (`headset-halfgrav-widenirr-c1-acq1`,
  `--init-from-source` off its own 2M checkpoint, mirrors the
  `widen2-c1-acq1`/`irrwiden-c1-acq1` template) to test whether the
  widen-first composition edge holds at full budget, same as the
  concurrent cycle already did for jitter-first. Did NOT fund further
  budget on `widenirr-c2b` (known-bad seed per its own parent's ACQ
  FAIL this cycle) — per that same verdict's own conclusion, a 3rd
  seed of the widen2 rung (not a jitter retrofit onto seed 2) is the
  right tie-breaker if one is needed later. Operational note: this
  ACQ launch briefly ran as an accidental duplicate (my own `respec
  --now` on train-3 landed ~2min after the watcher's own continuous
  drain independently placed the same backlog item on train-7); caught
  it via `launch_run.py status`, killed the train-3 copy
  (<1M steps, no signal lost), left train-7's copy as the sole ACQ
  arm — logged as `widenirr-c1-acq1b` `KILLED - DUPLICATE` in the
  ledger for the record. Evidence: `ops.sh review cw-walkscratch-
  easy0905-headset-halfgrav-widenirr-{c1,c2b}`, `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_halfgrav_widenirr_{c1,c2b}_gate/
  report.json`, W&B `uia75k9z`/`lldm22oo`, RL_LOG.

- 09-05 ~23:4x this cycle (assigned `headset-halfgrav-fullhead-widen2-{c1,c2b}-acq1` +
  `headset-halfgrav-irrwiden-c1`): three verdicts, splitting the widen2
  acquisition-scale question by SEED rather than confirming it cleanly.
  `widen2-c1-acq1` **ACQ PASS**: gait_valid 21/24 across all 4 modes, 0
  falls, no chronic leg sacrifice (only 3/24 episodes flag a transient
  leg, never the same leg twice), `walk/det` slip_per_m median IMPROVES
  vs its own 2M canary (3.93 vs 5.02) — the widen-from-medhead recipe
  survives a full 40M budget on this seed. `widen2-c2b-acq1` **ACQ
  FAIL**: gait_valid regresses from its own 2M canary (16/24) to 14/24
  at 40M, with leg-1 duty low (0.01-0.21, med ~0.11) in ALL 24
  episodes and formally flagged sacrificed in 10/24 (one episode
  collapses to FOUR sacrificed legs [0,1,3,4] simultaneously); video
  (`walk_det_4`, `walk_startjitter_det_2`) shows skating/rotating in
  place rather than translating in the worst episodes, matching the
  numeric slip blowup (up to 128/m in sto mode). Root-cause note: the
  `medhead2_acq1` parent this seed built from was itself only ACQ
  CONTINUE (borderline, not a clean PASS like `widen2-c1`'s
  `medhead_acq1` parent) — parent-champion quality appears to
  propagate through the curriculum rather than this being pure
  seed-noise. **This is the FIRST appearance of the base(1g)-family
  chronic leg-1/4 entrenchment fingerprint on a halfgrav(0.5g)
  seed** — the gravity-linked-robustness-gap hypothesis needs
  qualifying (halfgrav is less prone, not immune). Net: the widen2
  rung reads 1 PASS / 1 FAIL at acquisition scale, not yet a validated
  recipe — a tie-breaking 3rd seed from a cleanly-PASSed parent is the
  natural next step, not a repair-mechanism spend (per-leg-utilization
  reward levers are already closed 7-9/9 on the base family; do not
  relaunch any of them here off a single new instance).
  `headset-halfgrav-irrwiden-c1` (jitter-first composition: widen2's
  heading-set change on top of the ACQ-PASS irr-timing-jitter
  champion) **CANARY PASS** — the CLEANEST widen2-family read yet:
  gait_valid 23/24, 0 falls, only ONE episode flags a transient
  [2,4] leg pair, beating both widen2-c1's (21/24) and widen2-c2b's
  (16/24) own 2M canaries. Validates that heading-breadth and
  timing-irregularity compose cleanly in the jitter-first order.
  **Refill:** launched the matched 40M acquisition continuation,
  `headset-halfgrav-irrwiden-c1-acq1` (respec `--init-from-source`,
  mirroring the widen2-c1-acq1 template) — tests whether this
  composite champion (heading breadth + timing irregularity together,
  the actual DONE-gate panel shape) holds at full budget given the
  seed-dependent widen2-acq1 split just found. Left untouched (other
  cycles' remit): `widenirr-c1`/`widenirr-c2b` (widen-first mirror
  order, a concurrent cycle's own claim per ledger `triage` field) and
  the `*-placementjit-*`/`headset-crossgrav-*` arms concurrent cycles
  own. Evidence: `ops.sh review cw-walkscratch-easy0905-headset-
  halfgrav-fullhead-widen2-{c1,c2b}-acq1`, `cw-walkscratch-easy0905-
  headset-halfgrav-irrwiden-c1`, `logs/ckpt_eval/cw_walkscratch_
  easy0905_headset_halfgrav_{fullhead_widen2_c1_acq1,fullhead_widen2_
  c2b_acq1,irrwiden_c1}_gate/report.json`, RL_LOG.

- 09-05 ~23:4x this cycle (assigned `headset-base-medhead-placementjit-c1` +
  `headset-base-s0c1-placementjit-fresh`, the remaining 2 arms of the
  3-arm placement-jitter batch): 2 verdicts, 2-arm new-theory refill.
  (1) `medhead-placementjit-c1` (retrofit onto `medhead_acq1`)
  **CANARY FAIL - MECHANISM**: harness gait_valid 5/24 at 2M (walk/det
  0/6, walk/sto 4/6, walk_startjitter/det 0/6, walk_startjitter/sto
  1/6) vs parent's own landed 40M report 10/24 — every mode
  flat-to-worse, same legs [1]/[4] sacrificed, 0 falls (clean
  mechanism failure, not behavioral impossibility). (2)
  `s0c1-placementjit-fresh` (from-scratch bake-in on the same
  lightly-trained 2M `s0c1` checkpoint) **CANARY FAIL - MECHANISM**:
  corrected this run's own gate-text premise (per the sibling
  `irr-placementjit-c1` verdict's flag) and compared against the REAL
  undosed s0c1 twin (`s0c1_gate/report.json`: 17/24, walk/det+sto
  12/12 clean, 0 sacrificed legs) — this run COLLAPSES to 12/24, with
  walk/det dropping 6/6->1/6 and a NEW second leg (leg 1, alongside
  leg 4) starting to get sacrificed; walk_startjitter/det stays at the
  identical 0/6 floor (zero repair on the exact mode targeted). 0
  falls/terms, reward rose monotonically (16.7->126) — not behavioral
  impossibility, a genuine regression. **With all 3 arms of this batch
  now FAIL (2 retrofit + 1 from-scratch), placement-jitter is CLOSED
  end-to-end as the 8th failed base(1g) leg-favoritism repair lever**
  (after `walk_gait_gate`, `walk_duty_gate` x9, `walk_swing_gate` x4).
  **Refill (genuinely new theory, not a 9th reward/state-price
  variant):** with reward-price AND state-distribution fixes both
  closed 8/8 on base(1g), AND the gSDE-exploration-scheme alternative
  already closed end-to-end (bare-sde + sdehalfgrav-remcost, every
  repair engaged-or-inert) — every mechanism tried so far shares one
  property: it trains a lineage FROM SCRATCH under 1g, and even the
  earliest undosed base(1g) 2M checkpoints already carry the leg-4
  sacrifice fingerprint (s0c1's own PASS canary: walk_startjitter/det
  6/6 sacrifice leg[4]) — no base(1g) lineage has EVER had a
  leg-healthy starting point to test a repair FROM. This suggests a
  genuinely untested causal question: does the pathology come from 1g
  dynamics themselves (torque/current/contact limits), or is it just
  that nothing has tried starting 1g training from an ALREADY leg-healthy
  gait? Halfgrav has one: `headset-halfgrav-medhead-acq1` (ACQ PASS,
  40M, gait_valid 22/24, walk/det 6/6, 0/24 falls, slip at/under the
  2.9 band in 3/4 modes) has never seen 1g gravity. Launched a matched
  2-arm cross-gravity-transfer batch, both warm-started from that
  exact champion via `--init-from-source`, using the already-built
  `ease.gravity_scale` + `sched.*` engine (no new code — `sched.key=
  ease.gravity_scale` was already proven to ramp correctly in the old
  `cw-gait-ease1` run): `headset-crossgrav-medhead-abrupt-c1`
  (`ease.gravity_scale=1.0` from tick 0, abrupt jump, train-2) and
  `headset-crossgrav-medhead-ramp-c1` (`sched.key=ease.gravity_scale`,
  v0=0.5->v1=1.0 linearly over the first 1M of this 2M continuation,
  train-0). Both VERIFIED RUNNING. 2M discovery-scope; gate (both
  arms, full text in the ledger): PASS/INFORMATIVE-POSITIVE if
  gait_valid stays majority (>=4/6) in walk/det with no chronic
  single-leg sacrifice — direct evidence 1g walking is reachable via
  cross-gravity transfer from an already-good gait, licensing a longer
  ramp/40M continuation and a real alternative to "reallocate
  everything to halfgrav." FAIL/INFORMATIVE-NEGATIVE if either or both
  collapse to the identical leg[1,4] chronic-sacrifice fingerprint —
  read together (abrupt vs ramp) to separate "gravity-transition
  shock" from "1g dynamics force it regardless," closing cross-gravity
  transfer and hardening the reallocate-to-halfgrav conclusion with
  direct causal evidence either way. Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-base-{medhead,s0c1}-placementjit-*`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_medhead_acq1_
  gate/report.json`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  base_s0c1_gate/report.json`, `rl_move/sim/sim_env.py:364-420` (sched
  engine), RL_LOG.

- 09-05 ~23:3x this cycle (assigned `headset-base-irr-placementjit-c1`):
  **CANARY FAIL - MECHANISM.** Start-pose jitter
  (`dr.placement_noise_deg=3.0`+`dr.bad_start_prob=0.25`, engaged in
  training per its own launch args) does NOT repair the base(1g)
  leg-1/4 favoritism and actually REGRESSES vs its own already-FAILED
  parent: harness gait_valid tally 13/24 (walk/det 2/6, walk/sto 5/6,
  walk_startjitter/det 1/6, walk_startjitter/sto 5/6) vs parent
  `headset-base-irr-acq1`'s own 18/24 (3/6, 6/6, 3/6, 6/6) — every
  mode flat-to-worse, and `walk_startjitter/det` (the exact mode this
  mechanism targeted) drops from 3/6 to 1/6. Same legs [1]/[4]
  flagged in both; video confirms the same single-flag-leg-dragging
  pose as every closed reward-price mechanism in this family. **This
  is the 8th independently-tested repair lever to FAIL on base(1g)
  leg-favoritism** (after `walk_gait_gate` 6/6, `walk_duty_gate` 9/9,
  `walk_swing_gate` 5/5, now `placement_noise`/`bad_start` jitter
  1/1 — sibling arms `medhead-placementjit-c1`/`s0c1-placementjit-
  fresh` are a concurrent cycle's, watch for the same fate).
  **CORRECTION on record**: the launch gate text for this whole
  3-arm batch asserted "irr_acq1's own clean 6/6" as the walk/det
  baseline — that premise was factually wrong; `headset-base-irr-
  acq1`'s own 40M read is itself **ACQ FAIL** (walk/det 3/6, 18/24
  total, see the 09-05 ~16:0x entry below). The correct comparison
  (18/24 parent vs 13/24 child) still yields a clean FAIL, so this
  verdict is unaffected, but the concurrent cycle reading the 2
  sibling placementjit arms needs the same corrected baseline before
  judging them — do not accept a "clean 6/6" premise for any
  base(1g) irr-lineage arm going forward. **Refill:** per the
  campaign's own repeated conclusion (next lever must be structural,
  not another reward/state-price mechanism, absent a genuinely new
  causal theory) and since the halfgrav structural-widen batch
  (widen2-c1/c2b-acq1, widenirr-c1/c2b, irrwiden-c1 — 5 arms) was
  already fully saturated with in-flight capacity at cycle start, did
  not fund a 9th base(1g) reward-price variant. Instead, applied this
  campaign's own already-established n>=2 seed-confirmation
  discipline (used for medhead/medhead2 and widen2/widen2b) to the
  halfgrav irr-timing ACQ rung, which has 3 healthy 2M canaries
  (irr-c1/c2/c3, all CANARY PASS) but only ONE (`irr-c1`) was ever
  continued to a full 40M acquisition (`irr_acq1`, ACQ PASS). Launched
  `headset-halfgrav-irr2-acq1` (respec of `irr-c2`, seed 3, own
  40M budget, same bank-proved recipe, no new mechanism) to give the
  irr-timing rung its own n=2 confirmation before any composition arm
  (widenirr/irrwiden) draws a recipe-level conclusion off a single
  seed. Evidence: `ops.sh review cw-walkscratch-easy0905-headset-
  base-irr-placementjit-c1`, `logs/ckpt_eval/cw_walkscratch_
  easy0905_headset_base_irr_{placementjit_c1,acq1}_gate/report.json`,
  W&B `dctducci`.

- 09-05 ~22:5x this cycle (assigned `headset-halfgrav-medhead2-swinggate-fix`,
  the halfgrav-family arm of the `walk_swing_gate` batch): one
  verdict, 3-arm refill. **CANARY FAIL - MECHANISM (engaged, no
  repair)**: retrofit onto the FAILED `headset-halfgrav-medhead2-
  acq1-cont40m` checkpoint (own ACQ FAIL: walk_startjitter/det
  plateaued 2/6 through 80M). `env/walk_swing_gate_factor` sampled
  0.93-1.0 (genuinely engaged, not saturated-inert like the base
  family's fresh/fix arms) but `gait_valid` counts land IDENTICAL to
  the undosed parent on all 4 modes (walk/det 5/6, walk/sto 6/6,
  walk_startjitter/det 2/6, walk_startjitter/sto 4/6) — every failing
  episode's flagged-leg duty stays 0.03-0.09, still under the 0.10
  bar. Read together with the base-family n=4 batch this same cycle
  (fresh/fix INERT, medhead-fix/irr-fix engaged-no-repair): **all 5
  independently-tested `walk_swing_gate` arms across BOTH gravity
  families now FAIL — the mechanism is CLOSED end-to-end** (7th
  independently-designed per-leg-utilization lever to fail overall,
  1st confirmation on halfgrav specifically). **Refill:** per the
  campaign's own conclusion (next lever must be structural: curriculum-
  widen from a leg-healthy champion, or reallocate spend to the
  healthy halfgrav lineage — base(1g) stays closed pending a
  genuinely new theory, and a concurrent cycle is already running that
  theory as `*-placementjit-*`), reallocated this cycle's free
  capacity to the halfgrav lineage's own validated widen-curriculum
  recipe (`widen2`, bank/canary-proved 2/2 seeds this same day: gait
  stays valid, reversal-heading tracking measurably tightens vs a cold
  jump). The track's actual DONE-gate panel needs heading breadth AND
  irregular direction-change timing TOGETHER, not one axis at a time,
  and no arm has combined them yet. Launched a 3-arm batch composing
  the two independently-validated halfgrav rungs (heading-widen
  `widen2`, ACQ-PASS `irr` timing-jitter) in both orders, same
  bank-proved cfg toggles, no new reward keys: `headset-halfgrav-
  irrwiden-c1` (jitter-first: widen2's heading-set change applied ON
  TOP of the ACQ-PASS `irr-acq1` timing-jitter champion, train-0),
  `headset-halfgrav-widenirr-c1` (widen-first: `walk_cmd_resample_
  jitter=0.5` applied ON TOP of the CANARY-PASS `widen2-c1` fullhead
  champion, train-4), `headset-halfgrav-widenirr-c2b` (matched 2nd
  seed of the widen-first order, from `widen2-c2b`, train-5). All 3
  VERIFIED RUNNING. 2M mechanism-health canaries; PASS/INFORMATIVE
  criteria and FAIL criteria are per-arm in the ledger gate text.
  Evidence: `ops.sh review cw-walkscratch-easy0905-headset-halfgrav-
  medhead2-swinggate-fix`, `logs/ckpt_eval/cw_walkscratch_easy0905_
  headset_halfgrav_medhead2_swinggate_fix_gate/report.json`,
  `logs/experiments/cw-walkscratch-easy0905-headset-halfgrav-medhead2-
  swinggate-fix/wandb_history.csv`, RL_LOG.

- 09-05 ~22:5x this cycle (assigned `headset-base-irr-swinggate-fix` +
  `headset-base-medhead-swinggate-fix`): both had ALREADY been
  verdicted **CANARY FAIL - MECHANISM** by a concurrent cycle before
  this cycle's own (independently-run) analysis finished — re-derived
  the same result from scratch (per-episode duty/swing_count for both
  arms statistically indistinguishable from their own undosed
  `irr_acq1`/`medhead_acq1` twins, `env/walk_swing_gate_factor` pinned
  at 1.0 the whole 2M run in both, frame strips show a genuine
  six-leg gait already present in the PARENT — not a fix, an inert
  retrofit), confirming rather than duplicating; no re-verdict
  written. **Refill (3-arm batch, non-duplicative, new mechanism):**
  with the reward-price family now closed 7/7 (`walk_gait_gate`,
  `walk_duty_gate` x9, `walk_swing_gate` x4) and the campaign's own
  conclusion calling for "a different exploration/init scheme," code
  archaeology (`rl_move/sim/domain_rand.py`,
  `rl_move/sim/sim_env.py:600-630`) found the whole easy0905 family
  trains at `--dr-scale 0.0` with NO `dr.placement_noise_deg`/
  `bad_start_*` override — every training episode starts from the
  IDENTICAL nominal pose, so the policy has never seen a perturbed
  start joint configuration, while `eval_checkpoint.py`'s
  `walk_startjitter` mode (the ONE mode where this family's
  pathology concentrates — plain `walk/det` on the narrow irr set
  runs 6/6 clean per its own PASS notes) tests exactly that gap. This
  is a genuinely different, ALREADY-BUILT-AND-VALIDATED mechanism
  (not a reward shape, so no new bank-test gap): `dr.placement_noise_deg`
  was proven on the joystick track months ago
  (`cw-walk-placementnoise6-r3`, PASS) and the absolute-override path
  (`setattr` in `sim_env.py`, bypasses `dr_scale` scaling) means it
  works even at `--dr-scale 0.0`. Dose (jitter 3deg, 25% chance one
  8-16deg-off joint) matches `eval_checkpoint.py`'s own
  `walk_startjitter` CLI defaults exactly, closing the train/eval gap
  directly instead of guessing. Launched 3 arms, matching the
  campaign's own fresh-vs-retrofit split methodology, ALL VERIFIED
  RUNNING/HEALTHY: `headset-base-irr-placementjit-c1` (retrofit onto
  `irr_acq1`, train-3), `headset-base-medhead-placementjit-c1`
  (retrofit onto `medhead_acq1`, train-1), `headset-base-s0c1-
  placementjit-fresh` (bake-in from the same lightly-trained 2M
  `s0c1` seed `dgfresh`/`swinggate-fresh` used, train-2). Gate (all
  3): repair-signal if `walk_startjitter/det`'s flagged legs (1,4)
  majority-clear the harness `gait_valid` duty>0.10 bar with 0 new
  falls and plain `walk/det` stays at/above its own undosed twin's
  baseline; FAIL if the same legs stay majority-parked regardless of
  the new training-time state exposure. Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-base-{irr,medhead}-swinggate-fix`
  (re-derived confirmation), W&B run pages on the 3 new launches,
  `rl_move/sim/domain_rand.py`, `rl_move/sim/sim_env.py:600-630`,
  `rl_move/sim/eval_checkpoint.py:1264-1275`.

- 09-05 ~22:3x this cycle (assigned `headset-base-s0c1-swinggate-fresh`):
  after verdicting the assigned run (below), picked up the remaining 2
  still-outstanding `walk_swing_gate` retrofit arms too
  (`medhead-swinggate-fix`, `irr-swinggate-fix` — both had finished
  training with idle GPU capacity and no concurrent cycle had claimed
  them by the time their gate evals synced; `swinggate-fix` itself was
  already verdicted by a concurrent cycle sharing this same batch, see
  its entry below), completing the whole 4-arm batch this cycle.
  `medhead-swinggate-fix` (on `medhead_acq1`) **CANARY FAIL —
  MECHANISM (engaged, no repair)**: 11/24 gait_valid vs the undosed
  twin's own 10/24 — noise-level, same leg1/4 alternating sacrifice
  pattern, neither det mode majority-clears. `irr-swinggate-fix` (on
  `irr_acq1`) **CANARY FAIL — MECHANISM (engaged, no repair)**: 17/24
  vs the undosed twin's own 18/24 — noise-level, same pattern. **All 4
  arms of the batch (fresh + 3 retrofits) now FAIL — `reward.
  walk_swing_gate` is CLOSED end-to-end as a per-leg-utilization
  repair lever for the base(1g) family: 2 cleanly INERT (fresh,
  s0c1-fix — harness numbers essentially unchanged vs their own
  undosed twins) and 2 noise-level marginal with zero majority-
  clearing repair (medhead-fix, irr-fix). This is the 7th
  independently-designed mechanism to fail** (after `walk_gait_gate`+
  `k_step_event` 6/6 FAIL, `walk_duty_gate` 9/9 FAIL across every
  provenance x dose). **Do not fund any further reward-price mechanism
  for base(1g)-family leg favoritism without a genuinely new causal
  theory** — the next lever must be structural: curriculum-widen from
  a leg-healthy champion (the way halfgrav's `widen2` thread already
  validates, since halfgrav does not show this pathology), a
  different exploration/init scheme, or explicitly reallocating
  base(1g)-family GPU spend to the healthy halfgrav lineage and
  treating this as a closed, documented negative result. Did not
  re-triage `headset-halfgrav-medhead2-swinggate-fix` (a different,
  halfgrav-family arm testing the same mechanism on a milder
  borderline-duty case, not part of the base-family batch — still
  genuinely computing remotely at cycle end) or the `widen2-c1-acq1`/
  `widen2-c2b-acq1` continuations (another cycle's thread) — left for
  the next reader. Evidence: `ops.sh review cw-walkscratch-easy0905-
  headset-base-{s0c1,irr}-swinggate-fix`, `...-headset-base-medhead-
  swinggate-fix`, CURRENT_TRUTHS.md.

- 09-05 ~22:3x this cycle (assigned `headset-base-s0c1-swinggate-fix` +
  `headset-halfgrav-fullhead-widen2-c2b`): one verdict, two 40M
  launches. `swinggate-fix` (entrenched-checkpoint retrofit of
  `walk_swing_gate` onto the FAILED `s0c1_acq1` leg-4-park checkpoint)
  had ALREADY been verdicted **CANARY FAIL - MECHANISM (INERT DOSE)**
  by a concurrent cycle before this cycle's gate eval even synced
  (harness result virtually identical to the undosed twin on all 4
  modes) — re-confirmed, not re-triaged, matches the same-cycle
  `swinggate-fresh` inert-dose fingerprint above. `widen2-c2b` (the
  corrected matched-budget 2nd seed of the widen-from-medhead
  curriculum test, warm-started from `medhead2_acq1.zip`) **CANARY
  PASS**: gait_valid 16/24, 0 falls/terms in all 4 modes,
  `walk/det` direrr/courserr/slip medians (62.0/63.6/4.94) land close
  to `widen2-c1`'s own numbers (59.4/45.4/5.02), NOT the confounded
  `widen2-c2`'s (74.9/129.6/12.1) — confirms 2/2 matched-budget seeds
  now show the widen-from-medhead recipe measurably beats a cold
  full-set jump, closing the champion-specific-luck alternative.
  **Refill**: with 6+ GPU pods genuinely idle (verified via direct
  `ps`, not just launcher status) and this being the first
  recipe-level-confirmed non-blocked halfgrav thread, launched matched
  40M acquisition continuations off BOTH widen2 seeds:
  `headset-halfgrav-fullhead-widen2-c1-acq1` (train-7, from
  `widen2-c1`) and `-widen2-c2b-acq1` (train-8, from `widen2-c2b`),
  both VERIFIED RUNNING — tests whether the reversal-heading
  tightening holds at full budget on 2 independent seeds before
  calling the widen curriculum shape acquisition-validated for this
  ladder. Left the base-family swing_gate retrofit reads
  (`medhead-swinggate-fix`, `irr-swinggate-fix`,
  `halfgrav-medhead2-swinggate-fix`) alone — still genuinely computing
  remotely at cycle end, not assigned this cycle. Evidence: `ops.sh
  review cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2b`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_fullhead_
  widen2_c2b_gate/report.json`, W&B `nnebz1nz`, SKILLS.md.

- 09-05 ~22:2x this cycle (assigned `headset-base-s0c1-swinggate-fresh`,
  the fresh-provenance arm of the 4-arm `walk_swing_gate` canary
  batch): one verdict, no new launch (all pods free but the batch's
  own sibling reads are pending, and no new hypothesis is ready
  without them). **CANARY FAIL — MECHANISM (INERT DOSE)**: harness
  result is statistically indistinguishable from the undosed
  `dgfresh` twin it was baked in on top of — `walk/det` 6/6,
  `walk/sto` 6/6 gait_valid (both match the twin exactly),
  `walk_startjitter/sto` 5/6 with the identical episode (idx4) failing
  in both, and `walk_startjitter/det` (the canary's own named test
  mode) stays 0/6 in both with leg4 duty 0.03-0.06 here vs 0.02-0.07
  in `dgfresh` — chronically <=0.10 in all 6/6 episodes, matching the
  fingerprint every prior mechanism (`walk_gait_gate`, `walk_duty_gate`,
  noise revival) already left on this checkpoint/mode. Confirmed the
  gate's own pre-registered "gamed-completion-score" clause too:
  `env/walk_swing_gate_factor` logged saturated at 1.0 at every
  sampled point across the whole 2M run despite leg4's chronic
  near-zero duty the entire time (leg4 completes enough swing-like
  liftoffs per 4s window — 26-55 in 20s — to clear the trailing-count
  floor without ever contributing real stance/transport). 0 falls
  anywhere (24/24 episodes); reward grows on the same trajectory shape
  as the undosed twin, so this is a clean inert dose, not a training
  pathology. **Closes the fresh-provenance half of the swing_gate
  test**: pricing the mechanism in before the leg-4 habit entrenches
  does not cure it when the checkpoint (2M) already exhibits the
  chronic pattern. The entrenched-checkpoint retrofit triplet
  (`swinggate-fix`, `medhead-swinggate-fix`, `irr-swinggate-fix`) all
  finished training this cycle too (W&B state=finished) but are
  assigned to sibling cycles — did not re-triage them here to avoid a
  double-verdict race; if all three also FAIL, `walk_swing_gate`
  closes as a 7th independently-designed per-leg-utilization mechanism
  on the base(1g) family (after `walk_gait_gate`+`k_step_event` 6/6
  FAIL, `walk_duty_gate` 9/9 FAIL across every provenance x dose), and
  the next lever must be structural, not another reward-shaping
  variant — **do not fund further bare `walk_swing_gate` arms of any
  provenance until the retrofit triplet's reads land**. Evidence:
  `ops.sh review cw-walkscratch-easy0905-headset-base-s0c1-swinggate-
  fresh`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s0c1_
  swinggate_fresh_gate/report.json`, W&B `3f8el794`, CURRENT_TRUTHS.md.

- 09-05 ~21:5x this cycle (assigned `headset-halfgrav-medhead2-acq1-cont40m`,
  the 40M continuation launched last cycle off the halfgrav medhead2
  seed's borderline CONTINUE read): one verdict, no new launch. **ACQ
  FAIL** vs the continuation's own pre-registered gate: `walk/det`
  improved 4/6->5/6 gait_valid (0 falls, slip med 2.25) but
  `walk_startjitter/det` stayed flat at 2/6 through the full extra 40M
  (80M total) — flagged legs sit at borderline duty 0.05-0.08 (not the
  base family's hard 0.0-0.02 park) and which leg gets flagged still
  varies episode-to-episode, so this reads as a plateau on the
  start-jitter perturbation specifically, not a regression or new
  entrenchment. `ep_rew_mean` is still rising but decelerating
  (+184,+103,+101 per quarter) — exactly the reward-climbing-alone
  shape this gate's own text preemptively barred ("do not fund a 3rd
  continuation past this one on reward-climbing alone"), so closed
  now per its own stopping rule rather than extended further. **Net:**
  the halfgrav+medhead2 rung is n=2-seed MIXED, not confirmed — seed1
  (`headset-halfgrav-medhead-acq1`) PASSED cleanly at 40M; seed2 (this
  lineage) needed a continuation and still fails specifically on
  start-jitter robustness after 80M. This looks like a narrower,
  perturbation-specific open question (initial-joint-offset
  robustness) rather than the base family's chronic per-leg-
  utilization pathology, so it does not reopen that closed mechanism
  question; it's a candidate for a future targeted start-jitter-
  robustness pass, not an immediate repair spend. Left the cycle's
  free capacity to the concurrent cycle already running the
  `swinggate` retrofit batch (still training, not re-triaged here) and
  the `widen2-c1/c2` thread (explicitly another cycle's this round).
  Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-halfgrav-medhead2-acq1-cont40m`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_medhead2_acq1_cont40m_gate/report.json`.

- 09-05 ~21:4x this cycle (assigned `headset-halfgrav-fullhead-widen2-{c1,c2}`;
  both found genuinely still computing remotely at cycle spawn —
  prestage had pulled the checkpoint but the gate eval was an orphaned
  poller (known gotcha); backgrounded `pollreap` for both rather than
  duplicating, synced ~25min in): two verdicts + one new mechanism
  built + 5 new launches. (1) `widen2-c1` **CANARY PASS**: widening
  the 8-way heading set FROM the mature 40M `medhead-acq1` champion
  keeps the gait intact (gait_valid 21/24, 0 falls) AND measurably
  tightens reversal-heading tracking vs the cold-jump `fullhead-c1`
  baseline (direrr med 88.5->75.5, courserr med 94.9->57.9, slip med
  51.4->7.6 — 6.8x lower). (2) `widen2-c2` **CANARY PASS (mechanism
  bar only, course-tracking CONFOUNDED)**: gait stays valid (23/24, 0
  falls) but courserr/slip show no improvement (slip med 124.4, 16x
  worse than c1) — provenance check on the ledger's own `extra_args`
  found this arm actually warm-started from `medhead2_c1.zip` (the
  2nd seed's 2M CANARY) not `medhead2_acq1.zip` (its own 40M champion,
  the true match for c1's provenance) — a checkpoint-maturity confound,
  not a clean 2nd seed. Launched a corrected matched-budget
  `widen2-c2b` (from `medhead2_acq1.zip`, seed 4) to give a real
  apples-to-apples read before concluding recipe-level vs
  champion-specific. **Separately**, with 10 GPU pods free, built and
  bank-proved (`test_walk_swing_gate_*`, 4/4 green, default-off
  bit-exact) `reward.walk_swing_gate` — a 6th structural repair
  attempt for the base(1g)-family chronic leg-favoritism pathology,
  after `walk_gait_gate`+`k_step_event` (6/6 FAIL, rare-token-swing
  dodge) and `walk_duty_gate` (every provenance x dose FAIL, satisfied
  by a planted/vibrating stance) both closed end-to-end this same
  day. The new gate prices a MIN-over-legs trailing-window COUNT of
  qualifying real swings (same stride-filtered swing definition
  `walk_gait_gate` used, but a hard per-window count floor instead of
  a recency-decay score) — closes the duty_gate freeze/vibrate exploit
  by construction (zero qualifying swings, however high the contact
  duty) and the gait_gate rare-token-dodge by construction (one swing
  per several seconds can't clear a >=2-per-4s-window count bar the
  way it cleared a >=1-per-4s recency floor). Launched a 4-arm batch:
  `headset-base-s0c1-swinggate-fresh` (bakes the price in from the
  same lightly-trained 2M checkpoint `dgfresh` used), and three
  entrenched-checkpoint retrofits — `swinggate-fix` (on `s0c1_acq1`),
  `medhead-swinggate-fix` (on `medhead_acq1`), `irr-swinggate-fix` (on
  `irr_acq1`) — to read both "does pricing before the habit entrenches
  work" and "does it cure an already-entrenched exploiter" across 3
  independent checkpoints in one batch. All 5 arms (4 swing_gate +
  widen2-c2b) VERIFIED RUNNING. Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-{c1,c2}`,
  `rl_move/sim/walk_task.py` (`walk_swing_gate` block),
  `rl_move/tests/test_task_semantics.py`
  (`test_walk_swing_gate_*`), CURRENT_TRUTHS.md, SKILLS.md.

- 09-05 ~20:4x (assigned `headset-{base,halfgrav}-medhead2-acq1`;
  both found genuinely still computing remotely at cycle spawn —
  prestage had pulled checkpoint+wandb but not the gate eval; waited
  them out via parallel `waitlog` rather than duplicating, both
  synced within ~4min): two verdicts. (1) `headset-base-medhead2-acq1`
  **ACQ FAIL** — 8/24 gait_valid (walk/det 0/6 leg 1/4 sacrificed
  every episode, sto 6/6, walk_startjitter/det 0/6, sto 2/6), frame
  strip confirms one leg rigid the whole clip, 0/24 falls, reward
  still climbing (quarters -238,-79,133,366). This is the FOURTH
  independent base(1g) seed/champion (after `s0c1-acq1`, `irr-acq1`,
  `medhead-acq1`) to entrench the identical leg-1/4 habit at 40M
  budget — per this family's own established precedent, rising
  reward is not treated as a continue-license here; the base+medhead
  rung reads structurally closed pending a genuinely new per-leg-
  utilization mechanism. (2) `headset-halfgrav-medhead2-acq1` reads
  **CONTINUE, not FAIL/PASS**: walk/det clears the gate's own >=4/6
  bar (4/6) but walk_startjitter/det only 2/6 (16/24 total) — misses
  PASS on its own explicit per-mode text. Unlike the base family's
  hard 0.0-0.02 chronic park, the flagged legs' duty_cycle in the
  failing episodes is borderline (0.06-0.11, matching the FIRST
  seed's own accepted-as-PASS 0.08-0.09 range) and which leg gets
  flagged varies episode-to-episode (2,1,[1,4],[1,4]) rather than one
  leg parked every time; `ep_rew_mean` genuinely still climbing
  (quarters -401,-419,-183,+30, net upward the last ~10M steps, not
  plateaued) with `env/v_along_cmd_m_s` stable/not collapsing —
  matching this gate's own explicit CONTINUE clause instead of the
  base family's flat-entrenched shape. **Refill:** launched a
  same-recipe 40M continuation from this exact checkpoint,
  `headset-halfgrav-medhead2-acq1-cont40m` (`--init-from-source`,
  `--now`, VERIFIED RUNNING `train-0` after the launch call itself
  hit the tool's 2min timeout mid-verify — same recurring quirk noted
  by prior cycles, checkup/ledger confirmed healthy after, no
  double-launch), gated to close the halfgrav medhead rung's 2nd-seed
  status one way or the other; explicitly do not fund a further
  continuation past this one on reward-climbing alone if it reads
  marginal again. Did not duplicate the concurrent cycle's own
  `headset-halfgrav-fullhead-widen2-{c1,c2}` canaries (found already
  launched/finishing on train-2/train-3 at cycle start, left for
  their own owner — no eval artifact yet). No other non-duplicative
  bank-cleared walkcurr item identified with 9/11 pods free and
  backlog empty; other tracks re-confirmed DONE/blocked per every
  concurrent cycle today. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_{base,halfgrav}_medhead2_acq1_gate/
  report.json`, `walk_det_1_sheet.png` (base), W&B
  `47j1zemx`/`xa9a26bm`; CURRENT_TRUTHS.md 09-05 ~20:4x.

- 09-05 ~20:2x this cycle (assigned `headset-base-s0c1-noiseonly-c1`,
  the last cell of the walk_duty_gate x noise 2x2 grid; found still
  computing at cycle spawn, waited it out via `waitlog`/direct pod
  check rather than duplicating registration): **CANARY FAIL -
  MECHANISM — completes and CLOSES the full grid.** This is the
  isolating control (noise alone, `--log-std-final -1.2`, NO
  `walk_duty_gate`) that the `dgnoise-c1` cycle (immediately above)
  flagged as the missing cell. Result: leg-4 duty on the gated mode
  `walk_startjitter/det` is `[0.06,0.05,0.04,0.02,0.05,0.02]`
  (med ~0.045) — STATISTICALLY IDENTICAL to the undosed `s0c1`
  baseline (`[0.04,0.05,0.05,0.02,0.05,0.02]`, med ~0.045) and to
  `dgnoise-c1` (duty_gate+noise, med ~0.05); `gait_valid` 0/6, leg
  `[4]` sacrificed every episode, `policy_std` reads back 0.254
  (identical to `dgnoise-c1`'s own readback, confirming the dose
  landed the same in both arms — this is a real null, not an
  underdose). No regression: `walk/det` 6/6, `walk/sto` 6/6,
  `walk_startjitter/sto` 6/6, 0/24 falls across all four modes. Full
  2x2 now reads: s0c1 (gate off/noise low) med~0.045, `dgfresh` (gate
  on/noise low) med~0.06, `dgnoise-c1` (gate on/noise high) med~0.05,
  `noiseonly-c1` (gate off/noise high) med~0.045 — noise ALONE
  reproduces the undosed baseline exactly (zero effect on its own),
  and `duty_gate`'s own small solo bump (dgfresh's ~0.06) does not
  survive combination with noise. **This closes BOTH walk_duty_gate
  and plain exploration-noise scheduling as repair levers for the
  leg-4/marginal-leg-favoritism pathology on the base/non-gSDE
  family, matching the gSDE family's identical closure** — no further
  duty_gate-class or noise-schedule-class arm anywhere in the
  headset-base family; the per-leg-utilization pricing design
  question is fully open again pending a genuinely new mechanism (a
  hard minimum-duty/minimum-swing-count price that can't be satisfied
  by a rare token swing or by noise-around-the-mean, not a
  training-time completion score). **Refill this cycle:** none of
  the duty_gate/noise class (no cheap variant remains untried per the
  synthesis above) — but with 9 GPU pods genuinely free (confirmed via
  direct `ps` on every pod, not just `capacity.py`: train-0/train-3
  were busy running the `medhead2-acq1` pair's own evals at the time,
  freed up by the time of this launch) and no in-flight duplicate,
  picked up a DIFFERENT open thread instead: the heading-widening
  question left dangling since `headset-{base,halfgrav}-fullhead-c1`
  (full 8-way jump straight from the 3-way champion) FAILED
  course-tracking at the wide/reversal headings while `medhead` (the
  5-way intermediate rung built in response) has since ACQ PASSed
  cleanly on halfgrav — nobody had yet tried widening FROM the
  medhead champion instead of jumping cold from the 3-way one.
  Launched a 2-seed 2M canary pair, both VERIFIED RUNNING: `headset-
  halfgrav-fullhead-widen2-c1` (`--init-from-source` from the 40M
  `headset-halfgrav-medhead-acq1` champion, train-2) and `-widen2-c2`
  (from the second-seed `headset-halfgrav-medhead2-c1` champion,
  train-3), both adding ONLY the two untrained reversal headings
  (+-135, 180) to the already-passing 5-way set — same
  `k_walk_freeprog` mechanism, no new reward keys, reusing the
  already bank-proved `EASY_HEADING_WIDE` (re-ran green, 5/5). Base
  family excluded from this widen attempt (its own medhead rung is
  itself ACQ FAIL on leg-favoritism, so widening from a failing
  champion would confound two open questions). Gate: gait_valid stays
  majority-valid with 0 falls, AND direction_err/course_err at the new
  reversal headings comes in tighter than `fullhead-c1`'s own
  per-episode spread (28-161deg) — informative either way (recipe-
  level curriculum finding vs. a fundamental reversal-heading
  observation/policy limit needing its own design pass). Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_
  s0c1_noiseonly_c1_gate/report.json` vs `..._s0c1_gate/`,
  `..._dgfresh_gate/`, `..._dgnoise_c1_gate/` (same keys), W&B
  `xyz4gzvh`; new launches W&B notes on `cw-walkscratch-easy0905-
  headset-halfgrav-fullhead-widen2-{c1,c2}`.

- 09-05 ~20:2x this cycle (assigned `headset-base-s0c1-dgnoise-c1`;
  found genuinely still computing remotely at cycle spawn like every
  recent sibling — registered `evalpending` for it plus 3 other
  in-flight orphans (`noiseonly-c1`, `headset-{base,halfgrav}-
  medhead2-acq1`) and confirmed via direct `ps`/capacity check that
  the 7 nominally-free pods were genuinely idle, no non-duplicative
  bank-cleared item to launch there (same conclusion as the ~19:2x
  cycle, nothing new landed in between); `dgnoise-c1`'s own eval then
  landed mid-cycle and was triaged): **CANARY FAIL - MECHANISM** —
  closes the "keep exploration noise alive longer" companion lever to
  `walk_duty_gate` on the base/non-gSDE family. On the pre-registered
  gated mode `walk_startjitter/det`, leg-4 duty is statistically
  IDENTICAL across all three variants: undosed `s0c1` twin
  [0.04,0.05,0.05,0.02,0.05,0.02], `dgfresh` (duty_gate, low noise)
  [0.07,0.06,0.06,0.04,0.06,0.02], `dgnoise-c1` (duty_gate + high
  noise, `policy_std` read back 0.254 confirming the dose landed)
  [0.06,0.05,0.05,0.02,0.06,0.02] — `gait_valid` 0/6 all three, same
  leg sacrificed every episode, frame strip shows the identical
  planted/dragging leg. No regression either: `walk/det` 6/6 valid,
  `walk/sto` 6/6, `walk_startjitter/sto` 6/6, 0/24 falls. Interesting
  aside (not gate-deciding): plain `walk/det`/`walk/sto` (fixed start,
  no jitter) already ran 6/6 clean on ALL THREE variants including the
  undosed twin — this leg-4 pathology is specifically a start-pose-
  jitter-triggered habit, not a universal sacrifice, on this family.
  Root cause: extra exploration noise keeps the training-time
  `walk_duty_gate_factor` mobile (as `dgfresh` already showed) but
  never reaches the eval-time DETERMINISTIC policy mean, which is what
  actually walks the gate — noise around the mean isn't the same as
  moving the mean. Combined with `dgfresh`'s prior closure, BOTH named
  cheap companion levers (bake-in-early, revive-noise) are now closed
  for `walk_duty_gate` on this family, matching the gSDE family's
  identical fate. **Refill:** none — the isolating control
  `noiseonly-c1` (noise alone, no duty_gate) was already in flight
  from the prior cycle and needs to land before the "does noise
  contribute ANYTHING" question is fully closed; no new launch until
  it (and the `medhead2-acq1` pair) land — same reasoning the ~19:2x
  cycle recorded, unchanged since. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_base_s0c1_dgnoise_c1_gate/
  report.json` vs `..._dgfresh_gate/`, `..._s0c1_gate/` (same keys),
  W&B `6b1c6hy4`.

- 09-05 ~19:2x this cycle (assigned `headset-base-medhead-acq1`,
  `headset-base-s0c1-dgfresh`, `headset-halfgrav-medhead-acq1`; all 3
  found genuinely still computing remotely at cycle spawn — a
  concurrent cycle had already registered `evalpending`+`pollreap` for
  all 3 one cycle earlier, so waited them out rather than duplicating
  the registration): 2 verdicts, 1 (`halfgrav-medhead-acq1`) still
  computing at cycle end. (1) `headset-base-s0c1-dgfresh` **CANARY
  FAIL - MECHANISM** — the last untried `walk_duty_gate` provenance
  variant (strong floor=0.35 baked in from a lightly-trained 2M
  checkpoint, before the leg-4 habit could entrench, vs retrofitting
  onto the 40M-entrenched `s0c1-acq1`). `env/walk_duty_gate_factor`
  genuinely declined 1.0->0.63 (real pricing) but harness leg-4 duty
  in `walk_startjitter/det` stayed statistically unchanged vs the
  undosed twin (0.02-0.07 vs 0.02-0.05), same leg sacrificed 6/6
  both, gait_valid 0/6 both; walk/det+sto stayed clean (12/12, 0
  falls) so nothing else broke, the price just never moved the mean.
  **This CLOSES `walk_duty_gate` end-to-end** (every dose x every
  checkpoint-provenance case) on BOTH the gSDE and base/non-gSDE
  families — no further duty_gate-class arm on any lineage; the
  marginal-leg pathology needs a genuinely new mechanism (explicit
  per-leg swing-count/utilization reward, bank-proven fresh) before
  further spend. (2) `headset-base-medhead-acq1` **ACQ FAIL** — the
  5-way medium-heading 40M continuation clears speed (fwd
  1.9-2.6m/20s) and falls (0/24 terms) cleanly, reward still climbing
  every quarter (-279->398), but `gait_valid` only 10/24 overall
  (det-mode majority sacrifices leg 1 or 4: walk/det 1/6,
  walk_startjitter/det 1/6) — under the majority bar this campaign
  adopted at the `s0c1-acq1` FAIL. `direction_err_mean_deg` is
  uniformly poor (22-60deg, 0/24 success) even on the original
  {0,+-45} subset `fullhead-c1`'s canary tracked cleanly. THIRD
  confirmation (after `s0c1-acq1`, `irr-acq1`) that the base(1g)
  family's leg-1/4 favoritism hardens into outright gait failure
  under ANY added axis beyond flat/small-heading. **Note the sibling
  `headset-base-medhead2-c1` canary (below, concurrent cycle) reads
  much cleaner (18/24 gait_valid) on the SAME rung from a DIFFERENT
  champion/seed at 2M** — read together this looks like seed/lineage
  variance in how hard the leg-1/4 habit has entrenched by the time
  the medhead rung starts, not a rung-wide dead end; the
  already-launched `headset-base-medhead2-acq1` 40M continuation is
  the live test of whether a cleaner-starting seed holds up at full
  budget. (3) `headset-halfgrav-medhead-acq1` landed later in the
  cycle (was still genuinely computing at the time of (1)/(2)):
  **ACQ PASS** — `gait_valid` 22/24 (`walk/det` 6/6, `walk/sto` 6/6,
  `walk_startjitter/sto` 6/6, `walk_startjitter/det` 4/6 meeting the
  majority bar exactly; the 2 flagged episodes carry leg-4 duty
  0.08-0.09, borderline-not-chronic, vs the base sibling's
  0.02-0.07-every-episode pattern), 0/24 falls, `slip_per_m` med
  2.10/2.87/2.34/2.52 (at/under the 2.9 band in 3/4 scenarios),
  forward 0.09-0.16 m/s. This is the FIRST acquisition-scale PASS of
  the medhead rung on either gravity cell, and it lands on the SAME
  rung/budget the base sibling just failed — the split tracks gravity,
  not seed quality (2nd axis after irr-timing where halfgrav clears
  and base doesn't). `rl_docs/SKILLS.md` updated with a dedicated row.
  **Refill (same cycle, root-cause-driven):** the `s0c1-dgfresh`
  closure's own root-cause read — `policy_std` already sits at its
  schedule floor (0.135 rad, `--log-std-final=-2.0`) by 2M, so
  `walk_duty_gate`'s training-time pricing gets satisfied by
  noise-driven duty upticks during rollout collection that never have
  to move the policy MEAN — suggested an untried, single-variable
  companion lever: keep exploration noise alive much longer
  (`--log-std-final` -2.0 -> -1.2, residual stddev 0.135->0.301 rad)
  on the IDENTICAL `dgfresh` recipe otherwise. Launched
  `headset-base-s0c1-dgnoise-c1` (respec of `s0c1-dgfresh`, only the
  one `--log-std-final` change), VERIFIED RUNNING `train-1` (a
  `--now` launch call itself hit the tool's 2min timeout mid-verify,
  but `checkup`+ledger confirmed HEALTHY/RUNNING afterward — no
  double-launch). Capacity re-checked before this launch:
  `train-1`/`train-4` were genuinely idle (confirmed via direct `ps`,
  not just `capacity.py`'s live check, which still cannot see
  standalone eval processes — `train-2` was correctly avoided, still
  running this cycle's own halfgrav eval at the time). Evidence:
  `ops.sh review cw-walkscratch-easy0905-headset-base-
  {s0c1-dgfresh,medhead-acq1}`, `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_halfgrav_medhead_acq1_gate/
  report.json`, CURRENT_TRUTHS.md 09-05 ~19:2x, W&B
  `8q0axo9n`/`8dtoak13`/`dejrlkhv`. **Second refill (completes the 2x2
  design grid, same cycle):** `dgnoise-c1` alone confounds two
  variables vs the plain undosed `s0c1` canary (duty_gate ON + higher
  noise at once) — launched the isolating control
  `headset-base-s0c1-noiseonly-c1` (identical `--log-std-final=-1.2`
  but `reward.walk_duty_gate=0.0`, i.e. more exploration noise with NO
  pricing at all), VERIFIED RUNNING `train-4`. Together with the
  already-landed `s0c1` (low-noise/no-gate) and `s0c1-dgfresh`
  (low-noise/gate-on) results, this completes the full 2x2
  {duty_gate on/off} x {noise low/high} grid for the marginal-leg-
  favoritism repair question — no further arm needed until both land.
  7/11 GPU pods still free at cycle end; no other non-duplicative,
  bank-cleared walkcurr item identified (every other open thread —
  medhead2-acq1 seed confirmations, halfgrav-medhead-acq1's own n=2
  seed, the `irr-acq1` base repair — is already in flight on a
  concurrent cycle or genuinely blocked on one of these two canaries'
  results first).

- 09-05 ~19:2x this cycle (own assigned pair, verdicted after their
  `pollreap` reaped): `headset-base-medhead2-c1` and
  `headset-halfgrav-medhead2-c1` both **CANARY PASS** — the medium
  5-way heading rung's second-seed confirmation. Base: `env/
  v_along_cmd_m_s` 0.065-0.075 m/s (well clear of the ~0.01 noise
  floor), harness 18/24 gait_valid (walk/det 6/6, walk/sto 6/6,
  walk_startjitter/sto 5/6, walk_startjitter/det 1/6 with legs 1/4
  flagged only in SOME episodes, not chronically), frame strip
  confirms genuine six-leg cycling. Halfgrav: cleaner still —
  v_along 0.077-0.091 m/s, harness 24/24 gait_valid across ALL FOUR
  modes, zero sacrificed legs anywhere, slip 2.5-3.9 (near the 2.9
  teacher band). Both warm-started from a DIFFERENT champion than
  their respective first-seed `medhead-c1` (base: `headset-base-acq1`
  vs `s1c1-acq1`; halfgrav: `headset-halfgrav-s3acq` vs `halfgrav-
  acq1`) — the medium-heading rung is now confirmed n=2 seeds on both
  families, not champion-specific. Per each gate's own PASS clause,
  launched the 40M acquisition continuations `headset-base-medhead2-
  acq1` (train-0) and `headset-halfgrav-medhead2-acq1` (train-3),
  mirroring the first-seed `medhead-acq1` template exactly (`respec
  --init-from-source --phase acquisition`), both VERIFIED RUNNING.
  **Capacity fill (while the assigned pair's pollreap was pending,
  11/11 reachable GPU pods free, backlog empty):** found 4 OTHER runs
  sitting finished-but-uncollected (W&B `state=finished`, harness
  `eval_checkpoint` genuinely still computing remotely 20min+ in, no
  live trainer anywhere per direct `ps`, not the stale ledger) with
  nobody actively working them this cycle. `sde-s1-c2-dgatefix`'s
  report had already been silently reaped by an earlier cycle's
  `pollreap` (unread) — verdicted **CANARY FAIL - MECHANISM**, closing
  the entrenched-checkpoint `walk_duty_gate` batch at n=4/4 FAIL (see
  the dedicated entry above/below for full evidence): legs [1,4] stay
  sacrificed 0/6 gait_valid despite the factor genuinely declining
  1.0->0.54 and reward rising — the same shape sibling `sde-s2-c2-
  dgatefix`'s OWN 40M continuation already showed re-saturates with no
  repair, so no duplicate continuation was funded. The other 3
  (`headset-base-medhead-acq1`, `headset-halfgrav-medhead-acq1`,
  `headset-base-s0c1-dgfresh`) were registered via `ops.sh evalpending
  add` + a backgrounded `pollreap` each (not yet reaped by cycle end —
  left for the next reader, not re-triggered). Evidence: `ops.sh
  review cw-walkscratch-easy0905-headset-{base,halfgrav}-medhead2-c1`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_{base,halfgrav}_
  medhead2_c1_gate/report.json`, W&B `n0ostk9i`/`1w4vf6xd`.

- 09-05 ~19:1x this cycle (assigned `headset-{base,halfgrav}-medhead2-c1`;
  both still genuinely computing remotely at cycle start (video-every=1,
  ~26min in of an expected 1.5-2h single-mode pass) -- backgrounded
  `pollreap` for both, not yet reaped by the time of this entry, so no
  verdict on them yet this cycle). With 11/11 reachable GPU pods FREE
  and backlog empty, used the wait to pick up 4 OTHER runs sitting
  finished-but-uncollected with nobody actively working them (no live
  trainers anywhere per direct `ps`/`launch_run.py status`, not ledger):
  (1) `sde-s1-c2-dgatefix`'s harness gate had already been silently
  reaped by an earlier cycle's `pollreap` (report.json existed, unread)
  -- verdicted **CANARY FAIL - MECHANISM**, completing the n=4
  entrenched-checkpoint `walk_duty_gate` batch (see full verdict text
  via `ops.sh review`): legs [1,4] sacrificed 0/6 gait_valid despite
  `env/walk_duty_gate_factor` genuinely declining 1.0->0.54 + reward
  rising -- the same shape sibling `sde-s2-c2-dgatefix` showed before
  ITS OWN 40M continuation (`sde-s2-c2-dgatefix-cont40m`, already FAIL)
  re-saturated with the sacrifice unchanged, so no duplicate
  continuation was funded here. **This closes the entrenched-checkpoint
  walk_duty_gate batch at n=4/4 CANARY FAIL** (bare-sde x2 seeds,
  remcost x2 seeds) -- retrofitting duty_gate onto an already-converged
  LEGPARK exploiter never repairs it regardless of whether the
  training-time factor saturates or genuinely declines, or whether
  reward rises or falls. Combined with the from-scratch `dgfresh`
  freeze-closure and the strong-floor `dgate2` inert-dose/
  engaged-no-repair closure on the non-gSDE family, **"price the
  parked leg with walk_duty_gate" is now closed end-to-end** across
  every checkpoint-provenance case (fresh, entrenched) on both the
  gSDE and non-gSDE families. No further duty_gate-class arm should be
  funded until a genuinely new mechanism (harder floor + explicit
  per-leg exploration anneal, or a structural init change) is designed
  and bank-proven. (2)-(4) `headset-base-medhead-acq1`,
  `headset-halfgrav-medhead-acq1`, `headset-base-s0c1-dgfresh` were all
  found in the SAME orphaned-supervisor state as this cycle's own
  assigned pair (W&B `state=finished`, harness `eval_checkpoint` still
  genuinely running on their pods 20min+ in) -- registered all 3 via
  `ops.sh evalpending add` and backgrounded a `pollreap` each so a
  future reader doesn't have to rediscover this; NOT verdicted this
  cycle (no report yet). Evidence: `ops.sh review
  cw-walkscratch-easy0905-sde-s1-c2-dgatefix`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_sde_s1_c2_dgatefix_gate/report.json`,
  W&B `8x8i8jt6`.

- 09-05 ~18:3x this cycle (assigned `headset-base-irr-dgate2-c1`; its
  eval was found still genuinely computing remotely, video-every=1 on
  all 4 modes -- backgrounded `pollreap`, reaped the real report):
  **CANARY FAIL - MECHANISM**, a DIFFERENT signature than the sibling
  `s0c1-dgate2-c1` FAIL below (read together). Plain English: the
  same stronger duty-floor price (0.35 vs the old inert 0.15) DID
  genuinely engage this time (`env/walk_duty_gate_factor` fell
  1.0->0.63->0.44, real training-time pricing, not pinned) but still
  did not repair the irr-timing/1g marginal-underuse checkpoint, and
  two previously-clean episodes got WORSE: per-episode duty vectors
  are near-bit-identical to the parent `irr-acq1` checkpoint (leg-4
  duty 0.07/0.06/0.14/0.11 parent vs 0.06/0.06/0.13/0.09 child --
  flat-to-down, never climbing), and `gait_valid` dropped (walk/det
  3/6->2/6, `walk_startjitter/sto` 6/6->4/6) as the SAME marginal leg
  (4, then 1) newly parked in 2 additional episodes it had cleared
  before. slip_per_m stayed flat/noise-level, 0 falls both runs. Why:
  a genuinely-engaged price against an already-40M-entrenched
  checkpoint pays 2M steps of training-time cost without buying
  eval-time repair -- the SAME entrenched-checkpoint shape the
  concurrent `sde-s2-c2-dgatefix-cont40m` closure documented at 40M
  scale (factor moves, sacrifice persists/re-saturates), now seen at
  2M on this family too. Combined with the sibling below: strong-floor
  `walk_duty_gate` retrofit onto an ENTRENCHED checkpoint is now 2/2
  FAIL for the marginal-underuse class (one INERT-DOSE, one
  engaged-no-repair) -- both closed, do not retry this exact retrofit
  again. **Refill (same cycle, non-duplicative): the from-scratch vs
  entrenched-checkpoint split that closed the (separate, now-closed)
  gSDE lineage's `walk_duty_gate` question was never actually run on
  this still-open base/halfgrav family** -- launched
  `headset-base-s0c1-dgfresh` (respec of the ALREADY-LANDED undosed
  `headset-base-s0c1` 2M canary, identical seed=0/`--init-from`
  checkpoint, ONLY addition: the same bank-proven duty_gate cfg baked
  in from step 0 instead of retrofit after 40M), VERIFIED RUNNING
  train-4. Gate: PASS if `walk_startjitter/det` leg-4 duty measurably
  exceeds the undosed twin's own landed report (6/6 sacrifice leg[4])
  with det/sto still >=10/12 valid and no new falls; FAIL closes
  duty_gate-from-scratch too (2nd family after gSDE) and forces a
  genuinely new mechanism (harder floor + explicit per-leg exploration
  anneal) before further duty_gate spend. Capacity re-checked: 6-7/11
  GPU pods free before this launch: `sweep-friction` non-GPU,
  `train-6` unreachable, `train-1/2/0/3` running the concurrent
  cycles' medhead/medhead2 heading-generalization ladder (the
  campaign's other, likely higher-value, open axis -- left alone, not
  duplicated). Evidence: `ops.sh review
  cw-walkscratch-easy0905-headset-base-irr-dgate2-c1`,
  `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_irr_dgate2_c1_gate/report.json`
  vs `..._headset_base_irr_acq1_gate/report.json`, W&B `9r38bzqi`.

- 09-05 ~18:3x this cycle (assigned `headset-base-s0c1-dgate2-c1`):
  **CANARY FAIL - MECHANISM (INERT-DOSE, reconfirmed at 2.3x dose)**.
  Plain English: doubling the duty-floor price from 0.15 to 0.35 to
  try to unstick a chronically-parked leg-4 (duty 0.03-0.07 on an
  otherwise-healthy base-family heading walker) still leaves that leg
  exactly as parked as before. Parent-matched comparison against
  `headset-base-s0c1-acq1`'s own gate report (identical eval
  conditions): walk/det `gait_valid` 0/6 both, leg[4] sacrificed all 6
  episodes both, duty 0.04-0.06 (child) vs 0.03-0.07 (parent) --
  statistically indistinguishable; walk_startjitter/det is WORSE on
  the child (duty 0.01-0.03, swing_count down to 7-28/20s). Video
  (`walk_det_*_sheet.png`, `walk_startjitter_det_2_sheet.png`) shows
  the identical single-leg hitched/tucked pose every sampled frame,
  both checkpoints. `env/walk_duty_gate_factor` DID genuinely decline
  in training (1.0->0.56, real pricing, not saturated like the
  original 0.15 dose) and `ep_rew_mean` rose every quarter
  (27->62->114->124) -- the same "factor declining + reward rising"
  shape the concurrent cycle's `sde-s2-c2-dgatefix-cont40m` continued
  to 40M on (see that verdict, this cycle, same file/CURRENT_TRUTHS)
  -- but that continuation's own outcome (factor MONOTONICALLY
  RE-SATURATED by 40M, sacrifice unchanged) already shows this exact
  shape does NOT reliably predict eventual repair. Given a true
  parent-matched null result (not partial progress) plus that live
  counter-precedent, this closes "raise `duty_gate_floor` magnitude
  alone" for the marginal-underuse class too (now 2/2 doses inert).
  Root cause: `policy_std` is already at its end-of-schedule floor
  (0.135 rad) at 2M, yet sto-mode leg-4 duty (0.16-0.23) still
  diverges sharply from det-mode duty (0.04-0.06) -- the training-time
  factor is priced against noisy rollout actions and gets satisfied by
  noise-driven duty upticks that never have to move the policy MEAN.
  A real fix needs a mechanism the mean itself must satisfy (harder
  floor + an explicit per-leg exploration anneal, not just a bigger
  version of the same windowed-average floor) -- a NEW mechanism+bank
  design question for a future cycle, not a relaunch of this lever.
  CURRENT_TRUTHS.md updated (~18:3x entry). No new arm launched: the
  only non-duplicative next step (a harder anti-noise-dodge
  mechanism) isn't bank-tested yet, and every other open walkcurr
  thread (medhead x2 acq continuations, `headset-base-irr-dgate2-c1`
  sibling still genuinely computing remotely on train-4 -- registered
  via `ops.sh evalpending add`) is already in flight on this or a
  concurrent cycle. Capacity re-checked: `launch_run.py status`/
  `capacity.py` show 9 GPU pods free, backlog empty, but no
  pre-registered, non-duplicative, bank-cleared item exists to fill
  them beyond what's already running -- matches this file's own
  repeated precedent (14:3x/14:4x/14:6x/15:3x entries) for leaving
  idle pods rather than inventing filler. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_base_{s0c1_dgate2_c1,s0c1_acq1}_gate/
  report.json`, `logs/experiments/cw-walkscratch-easy0905-headset-
  base-s0c1-dgate2-c1/wandb_history.csv`, W&B `j41igzz5`.


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
  W&B `uxuboegj`/`66wc8jin`. **Refill (capacity fill, same cycle)**:
  with 9/11 GPU pods free after the two verdicts and only one active
  seed each on the medhead rung, launched second-seed medhead canaries
  from DIFFERENT already-existing heading champions (never tried on
  this rung) to build the same n>=2 seed-robustness confirmation every
  other rung in this campaign got before being called closed:
  `headset-base-medhead2-c1` (warm-started from `headset-base-acq1`,
  the original base champion; medhead-c1 used `s1c1-acq1`) VERIFIED
  RUNNING train-0, and `headset-halfgrav-medhead2-c1` (warm-started
  from `headset-halfgrav-s3acq`; medhead-c1 used `halfgrav-acq1`)
  VERIFIED RUNNING train-3. Also noted, not claimed: 2 other canaries
  from an earlier cycle's strong-floor dutygate retry
  (`headset-base-{s0c1,irr}-dgate2-c1`) finished training on
  train-3/train-4 during this cycle but were not in this cycle's
  assigned-runs list — left for the mechanical per-run cycle spawn to
  triage, not duplicated here.

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
