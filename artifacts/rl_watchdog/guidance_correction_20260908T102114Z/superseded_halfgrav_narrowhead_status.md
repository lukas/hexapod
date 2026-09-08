## 2026-09-08 ~10:0x (triage cycle) — halfgrav cartfoot seed7 pair CLOSES as PARITY (both arms ACQ PASS); widen8-narrowhead bisection CLOSES the fresh-init line (DR breadth, not heading count, is the blocker); launched matched cont10m durability pair on the halfgrav PASS

One plain sentence: three runs closed this cycle -- the halfgrav OFF
arm confirms PARITY with its already-PASSed ON sibling (closing that
gravity cell's seed7 pair), and both narrowhead bisection arms FAIL
identically to their widen8-freshinit predecessors, which answers the
pending question cleanly: shrinking the heading set back to medhead's
5-way does NOT rescue fresh-init ignition, so the DR breadth itself
(not the widen8 backward headings) is what blocks this composite from
a random-weight start.

**`cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7-acq1` (OFF)
-> ACQ PASS - PARITY, closing the seed7 halfgrav pair:** 0 falls in
24/24 gate episodes across all 4 groups, fwd speed ~0.16 m/s (well
above the 0.03 m/s floor), reward quarters rising monotonically
[-678.2, 232.5, 1044.7, 1346.7]. Slip/m vs the ON sibling (1.56/1.72/
1.66/1.79): OFF comes in at 1.90/1.91/1.83/1.93 -- ratios 1.22x/1.11x/
1.10x/1.08x, 3/4 groups inside the cohort's ~1.2x parity band. Det-
mode gait_valid is degraded (0/6 walk/det, legs [1,4] low-duty) but
this is the SAME family-wide "det-only leg-underuse, still cycling
not frozen" quirk already precedented as shared/non-blocking across
this cohort (base/halfgrav, seeds 7/10/11) -- sto stays clean. Video
matches the eval: level body actually translating, no flag-leg/skate
pathology. **Closes halfgrav seed7 as PARITY, mirroring the already-
established 1g fork(b) result.**

**`cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-
cartfoot-freshinit-{c1,offctrl}-narrowhead` -> both CANARY FAIL -
MECHANISM, closing the fresh-init bisection line:** this pair tested
whether widen8's 8-way heading set (vs the pre-widen8 5-way medhead
set) was the fresh-init blocker for the full crossgrav+medhead-DR
composite, torque_scale left at 1,1 (crutch-off already ruled out by
the prior torqueretain bisection). Both arms reproduce the exact
flat/declining fingerprint of every prior widen8-freshinit arm:
env/reward_walk flat/noisy (c1 0.168/0.194/0.181/0.184, offctrl
0.162/0.201/0.183/0.182), env/v_along_cmd_m_s pinned near zero,
env/walk_speed DECLINES on both (0.100->0.091, 0.092->0.082).
gait_valid looks nominally "majority" (6/6,6/6,6/6,4/6) but that is
trivial here: fwd med is 0.02-0.18m over a 20s episode (no net
translation) while slip/m med is 74-216 -- legs buzzing in place. The
walk_det_0 frame strip confirms it visually on both arms: robot stuck
in the same spot while legs cycle. 0 falls, no dig-in trigger (gate
and video agree). **CONCLUSION: narrowing the heading set does NOT
rescue ignition -- the full crossgrav+medhead DR breadth itself is
too hard for this composite to bootstrap from a random-weight fresh
init, regardless of heading-set width. This closes the fresh-init
bisection line for this DR-hardened composite family; its only proven
ignition path remains warm-start/curriculum
(`...-allaxis-nokick-crutchoff-s{0,1,2}` -> acq1). Do not relaunch
this composite fresh-init at any heading-set width or torque setting
without a genuinely new mechanism (e.g. a staged DR-breadth
curriculum rather than full-breadth-from-scratch).**

**Refill: launched the halfgrav seed7 cont10m durability pair**
(`cw-walkscratch-easy0905-cartfoot-halfgrav-{s7,offctrl-s7}-acq1-
cont10m`, both VERIFIED RUNNING on train-2/train-1), mirroring the
1g fork(a)/fork(b) depth-read practice: does the halfgrav pair's clean
40M parity hold or degrade at 50M cumulative, the way fork(a) degraded
late (12-22M window) at 1g while fork(b) held through 50M? This is
the first depth read at halfgrav; nothing precedented yet either way.
9-10/11 GPU pods were free at cycle end (only train-3 busy on the
concurrent cycle's seed11 canary); the widen8-narrowhead line is
closed pending a genuinely new DR-curriculum mechanism (design work,
not a same-recipe relaunch), so this cont10m pair is the next honest
question with an existing precedent recipe. CYCLE_WORKED touched.

Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_halfgrav_offctrl_s7_acq1_gate/report.json`,
`logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_widen8_cartfoot_freshinit_{c1,offctrl}_narrowhead_gate/report.json`;
`wandb_history.csv` for all 3; W&B `1myxq3am` / `pr966vo3` / `cihv6dse`.
SKILLS.md row updated (halfgrav pair). RL_LOG 09-08 ~09:5x-10:0x.

