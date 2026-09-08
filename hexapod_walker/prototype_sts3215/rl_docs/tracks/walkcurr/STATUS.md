## 2026-09-08 ~10:3x (refill cycle, no completion assigned) — closes the legduty-ratio-target045 s1 half a concurrent cycle deferred; completes the seed10/seed11 halfgrav acquisition cohort's two missing OFF/ON halves alongside that same concurrent cycle

One plain sentence: two loose ends the concurrent cycle's own entries
explicitly named as "pending elsewhere" both got closed this cycle —
seed1's half of the `walk_leg_duty_ratio_charge` 0.45-dose canary
(matching seed0's already-closed FAIL), and the seed10 ON +
seed11 OFF halves of the halfgrav cart_foot acquisition cohort (the
concurrent cycle independently took seed10 OFF + seed11 ON at almost
the same moment — no duplication, verified via live `launch_run.py
status`).

**`cw-walkscratch-crutchoff-s1-widen8-legdutyratio-target045` ->
CANARY FAIL - MECHANISM:** vs its own matched 0.30-dose
`legdutyratiofresh-guardfix1` sibling, gait_valid is identical in all
4 groups (5/6, 6/6, 6/6, 4/6) but slip_per_m/progress_ratio only
jointly improve in 2/4 groups (walk_startjitter/det and /sto: slip
-8%/-18%, progress +8%/+6%) while both ordinary walk/{det,sto} groups
get WORSE on both metrics (slip +7%/+7%, progress -3%/-12%) — needs
>=3/4, clears only 2/4. Same shape as s0's independently-closed FAIL
(2/4 groups also). **Both seeds now agree: the 0.45-dose escalation
of `walk_leg_duty_ratio_charge` does not buy a real net quality gain,
matching the 0.30-dose result exactly** — do not fund a further dose
step or continuation of this exact mechanism without a genuinely new
pricing design (e.g. charge against absolute duty deficit, or paired
with a swing-count floor).

**Halfgrav cart_foot seed10/seed11 40M acquisition cohort — all 4
CANARY->ACQ launches now in flight, none duplicated:** verdicted all
4 seed10/seed11 2M canaries CANARY PASS first (healthy machinery,
same near-zero-det/real-sto-progress shape as seed7's canary; 0
falls/24 episodes each, gait_valid 6/6 every group). Launched
`cartfoot-halfgrav-s10-acq1` (ON, respec of `s7-acq1`, `--init-from`
the seed10 canary ckpt) on train-2 before discovering the concurrent
cycle had simultaneously launched `offctrl-s10-acq1` (train-1) and
`s11-acq1` ON (train-0) — so this cycle's second launch instead
filled the one remaining gap, `offctrl-s11-acq1` (OFF, train-3),
completing all 4 arms of the n=3 (seed7/10/11) cohort with zero
duplicate spend. All 4 VERIFIED RUNNING at cycle end. Gate for both
new pairs: >=0.03 m/s median net forward in >=1 of walk/det,sto (0
falls in det), read together with its ON/OFF sibling at the same
budget; slip/m ratio is the headline comparison, 08-21 ruling applies
if reward is still rising at cutoff.

Capacity: this cycle's 2 launches (`s10-acq1` ON 40M +
`offctrl-s11-acq1` OFF 40M) use exactly the 80M-step/cycle cap; no
further GPU launches this cycle. 7 pods remained free at cycle end
(train-4,5,7,8,9,10,11) — idle-within-cap, not idle-next-to-runnable-
work: no other track has a launch-ready item (todaypolicy/assistfade/
standwalk are each blocked on unbuilt reward-mechanism/design work,
cpg/amp are DONE-or-maintenance), and the walkcurr fresh-init/
narrowhead/torqueretain bisection lines are already closed pending a
genuinely new DR-curriculum mechanism.

Evidence: `ops.sh review cw-walkscratch-crutchoff-s1-widen8-legdutyratio-target045`;
`logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_halfgrav_{s10,s11,offctrl_s10,offctrl_s11}_gate/report.json`;
W&B notes on all 5 verdicted runs; `launch_run.py status` confirming
all 4 acq1 pods RUNNING with advancing step counts. RL_LOG 09-08
~10:1x-10:3x. CYCLE_WORKED touched.

--- prior entry below ---

## 2026-09-08 ~10:2x (triage cycle; assigned `cartfoot-halfgrav-s11` canary) — assigned canary was already CANARY PASSed (a concurrent cycle triaged the whole seed10/seed11 cohort together while this cycle was reading it); launched the seed11 40M acquisition continuation the PASS calls for

One plain sentence: the seed11 halfgrav cart_foot (ON) canary this
cycle was assigned to triage already had its CANARY PASS verdict
recorded (`0 falls/24, gait_valid 6/6 every group, reward quarters
-133/-338/-483/-645 monotonic-not-exploding, same shape as seed7/
seed10`) — a concurrent cycle triaged the full seed10/seed11 ON+OFF
cohort together and had already moved on to launching `s10-acq1` and
`offctrl-s10-acq1` by the time this cycle's triage started (mechanical
state confirmed via `experiments.json` timestamps and the git snapshot
log) — so rather than duplicate the verdict, this cycle read/confirmed
it independently (matches) and did the one thing the PASS still
called for that nobody had launched: the seed11 ON acquisition
continuation, mirroring the seed10 respec exactly (same `s7-acq1`
config template, own seed11 canary checkpoint as `--init-from`, seed
11).

**Launched: `cw-walkscratch-easy0905-cartfoot-halfgrav-s11-acq1`**
(respec of `cartfoot-halfgrav-s7-acq1`, `--init-from
rl_move/sim/policies/ppo_goal_cw_walkscratch_easy0905_cartfoot_halfgrav_s11.zip`,
`--seed 11`), VERIFIED RUNNING on `hexapod-mjx-train-0`. Completes the
n=3 (seed7/10/11) halfgrav acquisition-continuation cohort matching
the 1g fork(b) cell's practice. Gate: `>=0.03 m/s` median net forward
in `>=1` of walk/det,sto (0 falls in det), read together with the
matched `offctrl-s11-acq1` (concurrent cycle's to launch/read) at the
same budget; 08-21 ruling applies if reward is still rising at cutoff.
The matching `offctrl-s11` canary and `s10-acq1`/`offctrl-s10-acq1`
launches are the concurrent cycle's own work and are not re-verdicted
or re-launched here.

Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_halfgrav_s11_gate/report.json`;
`experiments.json` entries for `cartfoot-halfgrav-{s10,s11,offctrl-s10,offctrl-s11}`
(all CANARY PASS, timestamps 09:56-10:01 UTC) and `cartfoot-halfgrav-s10-acq1`
(concurrent launch, 10:19 UTC). RL_LOG 09-08 ~10:2x. CYCLE_WORKED touched.

--- prior entry below ---

## 2026-09-08 ~10:2x (triage cycle; assigned `crutchoff-s0-widen8-legdutyratio-target045`) — dose-escalation branch CLOSES negative; reaped 2 orphaned 09-06 DR-restore ACQ evals that never made it back to the controller; exhaustive board check finds no further unclaimed GPU lever this window

One plain sentence: the 0.30->0.45 legduty-ratio dose the 03:3x closure
named as the one open branch also fails its own gate (only 2/4 groups
clear gait_valid-AND-slip/progress vs the matched 0.30-dose sibling,
needed >=3/4), reproducing the SAME single-episode "gait_valid
recovers, that episode's slip gets worse" trade already flagged at
0.30 -- two independent doses now show the identical artifact, which
looks like a property of the mechanism's form (rebalancing duty
without pricing the slip that rebalancing costs), not a dose-tuning
gap.

**`cw-walkscratch-crutchoff-s0-widen8-legdutyratio-target045` ->
CANARY FAIL - MECHANISM:** vs the exact matched 0.30-dose
`legdutyratiofresh-guardfix1` sibling (same seed/init-from/panel,
only target differs): `walk/sto` and `walk_startjitter/det` both
improve (mean slip -2.7%/-0.7%, gait_valid held 6/6 both).
`walk/det` reproduces the 03:3x-flagged pattern exactly: gait_valid
ticks 5/6->6/6 (ep0's sacrifice flips to gv=True) but that same
episode's own slip jumps 21.4->27.3, worsening the group MEAN slip
+8.4% despite the gait_valid gain -- "a bare gait_valid uptick
alongside worse slip... does not count" per the pre-registered gate
text, and this is that exact shape. `walk_startjitter/sto` regresses
outright on both axes (slip +6.9%, progress -3.8%, same 2 chronic
legs [0,5] unchanged). Net 2/4 groups clear both bars, short of the
required >=3/4 majority. Video (contact sheet + `walk_det_0` frame
strip) matches the numbers -- no dig-in trigger. Reward quarters fall
hard `[33,65,-1894,-6678]`, the family's already-documented
ep_len-growth artifact (episodes surviving longer under a
non-decaying charge), not a fresh red flag. Per gate text, no further
dose step or continuation follows from a FAIL. **This closes the
"different dose/target" branch pending s1's own result** (a different training seed using the
same recipe; training has completed, with triage owned separately) -- with
0.30 and 0.45 now showing the identical within-episode trade, the
practical read is that this charge form does not buy a real net
quality gain at either tested dose.

**Reaped 2 orphaned 09-06 single-axis DR-restore ACQ evals that never
synced back to the controller** (found via a live-capacity discrepancy:
ledger said RUNNING, W&B said `finished` 2 days ago on 2026-09-06,
their pods showed FREE in `capacity.py` -- classic prestage gap, not
active training):
- **`tiltnoise1x-c1-acq1` -> CANARY PASS**: PERFECT 24/24 gait_valid,
  0 falls/terms, slip/m med 3.88-4.80 (in-band), reward rising every
  quarter `[789,1393,1464,1560]`, still climbing at 40M.
- **`gyronoise1x-c1-acq1` -> CANARY PASS**: 23/24 (1 non-chronic
  singleton leg-0 flag, walk_startjitter/sto), 0 falls/terms, slip/m
  med 3.88-4.55, reward rising every quarter `[791,1386,1449,1531]`.

Both `ops.sh podeval`-reaped (copy-back only, no relaunch needed --
the gate harness had already finished on-pod). Both close pending
reads inside the single-axis DR-restore sweep that 09-06 ~10:1x-10:24
already declared exhaustively closed ("every RandRanges field
covered") -- this is mop-up of stale unverdicted evidence, not new
frontier information; no launch follows from either.

**No new GPU launch this cycle despite 10-11/11 pods free at read
time.** Exhaustive board check before concluding: (1) the sampled widen8/narrowhead
fresh-init recipes missed their finite gates; no unchanged retry is
justified, but these tests do not isolate DR breadth or close all
fresh learning. A distinct staged-DR design remains agent-doable work; (2) the halfgrav/1g cart_foot fork(b) cohort
is at n=3 replicated + a fresh cont10m depth-read just launched by a
concurrent cycle on the one seed (halfgrav-s7) that lacked one -- the
1g cont10m depth cohort (s7/s10/s11) was already complete
(SKILLS.md, cart_foot fork(b) n=3 COMPLETE); halfgrav's s10/s11
canaries have not yet reached their own 40M ACQ read, so a cont10m
depth-read there would be premature (skipping the ACQ step) -- not a
line for this cycle to jump ahead of; (3) the legduty-ratio charge
mechanism now has 2/2 doses (0.30, 0.45) showing the identical
non-improving trade -- no further dose step is licensed by either
gate, and the "retrofit-onto-entrenched" question is ALREADY verdicted
CANARY FAIL - MECHANISM (01:5x below, telemetry-confirmed: charge
firing but shortfall RISING not declining, reward flat -- does not
meet its own pre-registered CONTINUE bar); (4) joystick/amp/cpg are
DONE/closed, standwalk/assistfade/todaypolicy are each blocked on
their own genuinely-new-mechanism-design prerequisite (assistfade's
09-08 comparator correction explicitly hands formal resolution to
root; todaypolicy's tested steering candidates are closed, while
new diagnostics/design within the existing motor contract remain
authorized without waiting for a fleet-contract decision).
Every live thread is either in-flight under a concurrent cycle or
closed pending design work nobody has built yet -- inventing a filler
run here would duplicate or jump ahead of that work, not add a real
question. CYCLE_WORKED touched (3 verdicts recorded + 2 stale evals
reaped is real completed work, even with no new launch).

Evidence: `logs/ckpt_eval/cw_walkscratch_crutchoff_s0_widen8_legdutyratio_target045_gate/report.json`
vs `..._legdutyratiofresh_guardfix1_gate/report.json`; `logs/ckpt_eval/
cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_{tiltnoise1x,
gyronoise1x}_c1_acq1_gate/report.json`; W&B `s52ddexm`/`7ejprgld`/
`mfxo6gt4`. SKILLS.md updated (legduty-ratio row appended, 1 new
DR-restore mop-up row). RL_LOG 09-08 ~10:2x.

--- prior entry below ---

## 2026-09-08 half-gravity acquisition and narrow-heading read — corrected 10:21 heartbeat

The seed7 half-gravity pair clears each arm's registered acquisition
movement gate, but their six-leg gait outcomes differ substantially.
The exact 40M gates report ON 6/6, 6/6, 4/6, 6/6 = **22/24** versus
OFF 0/6, 5/6, 0/6, 5/6 = **10/24** in ordinary det/sto and
start-jitter det/sto order. Both have zero terminations. OFF legs
[1,4] are repeatedly flagged in deterministic episodes; its stochastic
groups also each contain a failure. Calling this symmetric or saying
both stochastic panels are clean is incorrect. The exact 2M source
counts were ON 23/24 and OFF 24/24; both source models had negligible
forward movement, so source gait validity alone did not mean useful walking.

Median slip/m is ON 1.556/1.7215/1.6635/1.794 and OFF
1.898/1.9085/1.8345/1.931. The ON/OFF ratios are approximately
0.820/0.902/0.907/0.929; the previous 1.22/1.11/1.10/1.08 values
were the inverse (OFF/ON). This supports lower measured ON slip
in this one seed, while gait quality differs; it is not a broad
equivalence result. Each existing **ACQ PASS** and its original
>=0.03 m/s forward-movement/fall/reward gate are preserved. This is
0.5g, 3x torque and relaxed motor speed, not joystick or hardware
qualification. The registered seed10/11 acquisitions provide additional
training seeds; their results must be read before generalizing.

The seed40 narrow-heading ON/OFF pair **failed its registered finite
2M test**: reward was flat/noisy, command-aligned velocity near zero,
speed declined, and gait counts were 22/24 with zero terminations.
Shrinking eight headings to five did not rescue this recipe at this
budget. That does not uniquely identify DR breadth as the cause, rule
out torque/heading/DR interactions, or close all fresh learning.
The prior torque-only rescue likewise failed only its sampled recipe.
Keep both negative verdicts and avoid unchanged retries. A staged DR
curriculum is a possible new design to justify and register, not a
demonstrated explanation or an automatic extension.

Cycle 20260908T095611 launched the matched seed7 +10M continuations
from each own 40M checkpoint. They subsequently completed naturally at
10,485,760 steps each; exact gate comparison is pending normal artifact
staging. Preserve those jobs/checkpoints and follow their existing
result owners rather than duplicate them.

Evidence: repository-root
`artifacts/rl_watchdog/fleet_20260908T093214Z/halfgrav_comparison.json`
(exact gate selectors and per-episode leg flags),
`narrowhead_quarters.json`, and the original gate reports.
The superseded summary is retained in
`artifacts/rl_watchdog/guidance_correction_20260908T102114Z/`.
No historical raw data, gate, ledger verdict status or training recipe
was changed by this interpretation correction.

--- prior entry below ---

## 2026-09-08 ~09:5x (triage cycle) — halfgrav cartfoot seed7 ON arm ACQ PASS on its own read; extended the halfgrav cohort to seed10/seed11 canaries to match the 1g n=3 practice

One plain sentence: the seed7 halfgrav cart_foot 40M acquisition ON
arm clears its gate cleanly by itself (0 falls, gait_valid majority
every mode, speed >>0.03 m/s floor, slip/m actually LOWER than the 1g
cohort), and since the matched OFF sibling was still mid-prestage
under a concurrent cycle, this cycle used the free fleet capacity to
launch the seed10/seed11 halfgrav ON+OFF canary pairs the 1g cell
already has, rather than wait idle.

**`cw-walkscratch-easy0905-cartfoot-halfgrav-s7-acq1` (ON) -> ACQ
PASS (own read):** 0 falls/terminations in 24/24 gate episodes across
all 4 groups; speed_mean_m_s 0.189-0.238 in every episode; gait_valid
6/6 in walk/det, walk/sto, walk_startjitter/sto, 4/6 in
walk_startjitter/det (2 episodes sacrifice one leg -- same startjitter/
det fragility already precedented on the 1g OFF control). slip/m med
1.56 (det) / 1.72 (sto), well under the 1g cartfoot pair's 2.79-3.41
band. Reward quarters rise monotonically [-710.9, 106.6, 888.5,
1143.1], still climbing at 40M. Contact-sheet frames show a level
body translating with real alternating leg swing, no flag-leg/skate.
The matched `cartfoot-halfgrav-offctrl-s7-acq1` control (launched the
same cycle by a different cycle) finished training (wandb
state=finished, 40370176 steps) but its gate eval was still
mid-prestage at read time ("holding triage until prestage evals
sync" in orchestrator.log) -- this is an ON-ONLY read, NOT a closed
ON/OFF PARITY pair; whichever cycle reads the OFF control closes that.

**Refill: launched the seed10/seed11 halfgrav canary cohort.** With
10/12 GPU pods free and the OFF-s7 read pending elsewhere, respec'd
the proven `cartfoot-halfgrav-s7`/`-offctrl-s7` 2M-canary recipe onto
seed 10 and seed 11 (byte-identical except seed), mirroring exactly
how the 1g fork(b) cell built its n=3 (seed7/10/11) cohort. All 4
VERIFIED RUNNING/FINISHED: `cw-walkscratch-easy0905-cartfoot-halfgrav-
{s10,s11}` (ON, train-2/train-0) and `...-offctrl-{s10,s11}` (OFF,
train-1/train-3). At ~17-35k fps a 2M canary finishes in ~1-2 min, so
by cycle end several had already handed off to their CPU finalizers;
leave their gate evals for the next reader.

Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_halfgrav_s7_acq1_gate/report.json`;
`logs/experiments/cw-walkscratch-easy0905-cartfoot-halfgrav-s7-acq1/wandb_history.csv`;
W&B `traypy7y`. RL_LOG 09-08 ~09:5x.

--- prior entry below ---

## 2026-09-08 ~10:0x (refill cycle, no completion assigned) — launched the `walk_leg_duty_ratio_charge` "different dose/target" pair the 03:3x closure named as the only untried branch

One plain sentence: the 03:3x closure below found continuing the
existing 0.30-target/150-charge legduty-ratio charge past its shared
2M exposure buys no real quality (a lone gait_valid flip that comes
with worse slip/progress in every replication), and explicitly named
"a different dose/target" as the one still-open branch (not more
continuation) — that branch had sat unclaimed for ~6h while the
narrowhead/torqueretain thread ran, so this cycle launched it.

Recipe: respec each seed's own already-PASSED
`-legdutyratiofresh-guardfix1` 2M canary (checkpoint-initialized widen8, charge
150, byte-identical `--init-from`/heading-set/DR/motor cfg) with
ONLY `reward.walk_leg_duty_ratio_target` raised 0.30 -> 0.45 (the
09-07 ~23:4x calibration's passing-population MEDIAN worst-leg ratio
instead of its p10) — one lever, same mechanism (bank already 9/9
green, no new mechanism so no new bank pass owed).
`cw-walkscratch-crutchoff-{s0,s1}-widen8-legdutyratio-target045`,
both VERIFIED RUNNING (train-4/train-5 at launch; s0 already
finished its 2M GPU steps and hair-triggered the CPU finalizer within
the same cycle). Gate requires a JOINT improvement vs each seed's own
matched 0.30-dose sibling (gait_valid AND slip/progress
equal-or-better in >=3/4 groups) — a bare gait_valid uptick alone
does not count, per the 03:3x lesson. Read those before funding a
3rd dose step or a longer continuation.

Capacity: 10-11/11 GPU pods free, backlog empty. Other in-flight
walkcurr lines (halfgrav cartfoot acq1 pair, footgeom, narrowhead
pair) are concurrent-cycle-owned and untouched. Other tracks stay
non-launchable this cycle: cpg/amp are DONE-or-maintenance,
standwalk/assistfade/todaypolicy are each blocked pending a
genuinely new mechanism design (not a launchable queue item).
Evidence: `ops.sh review cw-walkscratch-crutchoff-{s0,s1}-widen8-legdutyratio-target045`
once gates land; source closure `logs/ckpt_eval/cw_walkscratch_crutchoff_s0_widen8_legdutyratio_{on10m,offctrl10m}_gate/report.json`.
RL_LOG 09-08 10:0x.

--- prior entry below ---

## 2026-09-08 ~09:3x (triage cycle) — offctrl-s41 confirms OFF-arm n=2; torqueretain bisection pair BOTH FAIL (torque restoration alone did not ignite this recipe); launched the narrowhead heading-breadth bisection

One plain sentence: closed out the widen8-cartfoot-freshinit seed41
pair and the torque-crutch-restore bisection (both symmetric FAILs),
then designed and launched the next single-variable test the FAIL
verdicts themselves called for -- does the widen8 heading breadth
specifically (vs DR/crossgrav breadth in general) block fresh-init
ignition?

**`...-freshinit-offctrl-s41`** -> CANARY FAIL - MECHANISM, matching
`...-c1-s41` almost exactly (0/24 falls, gait_valid majority every
mode, `env/reward_walk` flat 0.177/0.185/0.185/0.173, `env/
v_along_cmd_m_s` pinned near zero, `env/walk_speed` DECLINES
0.094->0.081, slip/m med 74-187). Closes the OFF-arm read at n=2,
matching the ON arm: **both action spaces fail to ignite this
composite fresh, at 2 seeds each.**

**`...-freshinit-{c1,offctrl}-torqueretain`** (the bisection launched
last cycle to test whether restoring the 3x torque crutch, removed in
the widen8 recipe, was the blocker) -> **BOTH CANARY FAIL -
MECHANISM.** Same healthy-machinery / flat-reward fingerprint as the
crutch-off arms: `env/reward_walk` flat on both (ON 0.185/0.171/
0.173/0.179, OFF 0.177/0.191/0.188/0.192), `env/walk_speed` DECLINES
on both (ON 0.148->0.120, OFF 0.135->0.105), `env/v_along_cmd_m_s`
stays pinned near zero on both. 0 falls in 47/48 gate episodes (one
tilt_roll term on OFF), gait_valid majority every mode, no chronic
single-leg-sacrifice. **This finite torque-only rescue test failed**:
restoring torque did not ignite this seed40 recipe within 2M steps.
It does not isolate heading/DR as the unique cause or exclude interactions.

**Refill: launched the next bisection.** The 5-way `medhead` heading
set (this composite's pre-widen8 heading set) plus the same full
crossgrav/medhead DR matrix already ignites fine from a WARM START
(`cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-
crutchoff-s{0,1,2}` -> acq1 lineage) but was never tried fresh-init.
Respec'd the seed40 widen8-cartfoot-freshinit ON/OFF pair with ONLY
`goal.walk_heading_set` shrunk from widen8's 8-way set back to the
5-way medhead set (drops the 135/-135/180 backward headings widen8
added) -- torque_scale stays at 1,1, with the remaining recipe fixed.
A pass would support this heading reduction for the sampled recipe;
a fail means the five-heading variant also missed this finite test.
Neither result alone identifies a unique DR cause or closes every
fresh-init curriculum. Keep the original gates and the scoped correction
in feedback fb_20260908T093937_58528c. Launched: `cw-walkscratch-easy0905-headset-
crossgrav-medhead-dr-widen8-cartfoot-freshinit-{c1,offctrl}-
narrowhead`, both VERIFIED RUNNING (train-0/train-3), gate evals
in-flight at cycle end (2M steps complete in ~2 min at this fps; CPU
finalizer running).

Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_
medhead_dr_widen8_cartfoot_freshinit_offctrl_s41_gate/report.json`,
`..._c1_torqueretain_gate/report.json`, `..._offctrl_torqueretain_
gate/report.json`; `wandb_history.csv` for all 3; W&B `tn101miy` /
`lqeww3mi` / `ammkxcg3`. RL_LOG 09-08 ~09:3x-09:4x.

--- prior entry below ---

## 2026-09-08 ~09:2x (triage cycle) — widen8-cartfoot-freshinit-c1-s41 CONFIRMS seed40 pair: 2nd seed closes the n=2 agreement bar, no DIG-IN

One plain sentence: the seed-41 replicate of the widen8-cartfoot-
freshinit ON canary (below) reproduces the seed40 pair's fingerprint
almost exactly, so the "composite too hard to ignite from fresh init"
mechanism read is now confirmed on 2 independent seeds, not just 1.

`cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1-s41`
-> **CANARY FAIL - MECHANISM** (matches seed40's `...-c1` verdict).
Machinery healthy (loss 498->378, value_loss 1057->810, std anneals
0.368->0.218 on schedule). 0 falls in all 24 gate episodes (2 safety
terms, both in walk_startjitter/sto only), gait_valid majority every
mode (6/6,6/6,6/6,4/6), no chronic single-leg-sacrifice (duty spread
0.54-0.99 across all six legs, leg0 does the most swinging -- same
identity as seed40). Anticipated PASS signal absent: `env/reward_walk`
flat/noisy across all 4 quarters (0.181/0.197/0.186/0.171), `env/
v_along_cmd_m_s` near zero all run and ends NEGATIVE (-0.00066),
`env/walk_speed` DECLINES (0.102->0.105->0.099->0.091) -- opposite of
the halfgrav/1g canaries' rising signal at this budget. `ep_rew_mean`'s
apparent collapse (-115->-528) is fully explained by `ep_len_mean`
growing 105->488 (surviving longer just accumulates more of the same
near-zero/negative per-tick total). Gate: slip/m med 94.07 det /
156.51 sto (3-10x the easy-rung cart_foot band), stride_m_mean
~0.001; the `walk_startjitter/sto` contact sheet shows the body
essentially stationary while legs buzz -- video matches the eval, no
DIG-IN trigger. Per this pair's own pre-registered gate text, two
seeds agreeing is sufficient for a canary-level mechanism verdict:
this closes the ON-arm read at n=2. The matched `...-offctrl-s41`
(OFF) sibling was still training at read time and is left for its
own reader/cycle to close the pair. Unchanged from the seed40 entry:
do not relaunch this exact fresh-init widen8 recipe at either action
space without a milder fresh-init entry point first.

Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_widen8_cartfoot_freshinit_c1_s41_gate/report.json`,
`logs/experiments/cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1-s41/wandb_history.csv`,
W&B `gafez8n2`.

--- prior entry below ---

## 2026-09-08 09:13 UTC — corrected radius probe complete: this dose fails; no replacement training

The earlier 15–26% slip-improvement claim used an invalid size-only
sphere mutation: collision bounds/BVH retained the original 4.5 mm
radius. That probe and its 2,097,152-step child remain preserved as
invalid-method evidence. Child `cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-footgeom0135-c1`
is **INVALID_PHYSICS**; it finished naturally, with no kill issued.

Repair `d54506ef2` compiles positive radii before private/shared model
use, retaining pristine inertials/friction; 28 tests passed locally
and on the controller. Default zero retains the original model.
The exact original parent (SHA256 `e92377d6e133cb68051b71738845ce2c6419fc308fe19836df8466f338696ca0`)
was re-evaluated at 0.0135 m under the repaired method, original seed,
cfg and 24-episode protocol. All 24 reported randomization dictionaries
match baseline. Corrected median slip/m increases **13.82%, 16.62%,
8.50%, 8.20%** (walk det/sto, start-jitter det/sto); gait remains
22/24, with zero terminations. **0/4 groups** meets the original
≥10% improvement criterion (required ≥3/4). Recovery is complete;
**no replacement 2M PPO or continuation from the invalid child** follows.
This fixed dose/checkpoint result does not close all foot geometry.

Canonical report: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxiskickhalf_nocrutch1x_c1_acq1_cont40m_footgeom0135_probe_compilefix1/report.json`.
Reproducible comparison: repository-root
`artifacts/rl_watchdog/footgeom_recovery_20260908T084713Z/compare.py`;
repair and source evidence are alongside it. Superseded current prose
is preserved in `artifacts/rl_watchdog/guidance_correction_20260908T093214Z/superseded_radius_status.md`.

--- prior entry below ---

## 2026-09-08 ~09:0x (triage cycle) — halfgrav cartfoot 2x2 cell ignites cleanly (both arms CANARY PASS, near-parity slip) + widen8 fresh-init pair CANARY FAIL - MECHANISM symmetrically (composite too hard fresh, not a cart_foot effect)

One plain sentence: two fresh questions closed this cycle -- does the
Cartesian-foot-target action space ignite at half gravity the way it
already did at 1g (yes, cleanly, both arms), and does it explain why a
much harder heading+DR composite can't bootstrap from a fresh random
init (no -- the joint-space control fails identically, so the
composite's difficulty is the driver, not the action space).

**`cartfoot-halfgrav-offctrl-s7` (OFF, my assigned run) + `cartfoot-
halfgrav-s7` (ON, its sibling, found already finished mid-cycle and
untouched by anyone else -- verdicted together) -- both CANARY PASS:**
finite/decreasing losses, std anneals on schedule, 0 falls in all 24
episodes both arms. `ep_rew_mean` falls (the usual ep_len-growth
artifact) but per-tick `env/reward_walk` clearly RISES across all 4
quarters on both arms (OFF 0.178->0.218, ON 0.164->0.229) and
`env/v_along_cmd_m_s` turns positive by the last quarter (OFF +0.011,
ON +0.010) -- the same healthy shape already proven at 1g
(`cartfoot-freshinit-offctrl-s7`). Slip is near-parity at this early
stage (det 0.83 OFF / 1.03 ON, sto 28.16 OFF / 21.79 ON) -- the 1g
cohort's eventual 3-10x cart_foot slip gap only emerged after a long
continuation chain (`cartfoot-c1-cont10m`), so a 2M canary can't see
that divergence yet either way. The 0.5g cell of the base/halfgrav x
joint/cartfoot 2x2 matrix now ignites for BOTH action spaces, same as
the 1g cell -- **funding a matched 40M acquisition pair this cycle**
(`cw-walkscratch-easy0905-cartfoot-halfgrav-{c1,offctrl}-s7-acq1`).

**`headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1` (ON, my
assigned run) + its matched `...-offctrl` sibling (OFF, found already
finished mid-cycle, unowned -- verdicted together) -- both CANARY FAIL
- MECHANISM:** this pair tested whether a fresh (never warm-started)
cart_foot init can bootstrap real progress on the much harder widen8
8-way-heading + crossgrav + medhead-DR composite, isolating the
action-space question from the "only ever reached via a long
continuation chain" confound the ~06:2x/~06:3x entries below flagged.
Machinery is healthy on both arms (finite/decreasing losses, std
anneal on schedule, no blowup) and both clear the no-fall / no-
chronic-single-leg-sacrifice floor (0/24 falls, gait_valid majority
every mode, duty spread 0.29-1.0 across all six legs -- no leg parked
at duty~1.0 with near-zero swings). But neither shows the anticipated
PASS signal: per-tick `env/reward_walk` stays flat/noisy (~0.17-0.21,
no trend) on BOTH arms, `env/v_along_cmd_m_s` hovers near zero and
ends slightly negative on the ON arm, and `env/walk_speed` actively
DECLINES across the run on both (ON 0.101->0.092, OFF 0.093->0.082) --
the opposite of the clearly-rising signal the halfgrav/1g pairs above
show at the identical budget. Video/eval instead shows an
unproductive high-frequency limb buzz (swing counts up to 268/20s per
leg, stride_m_mean 0.001, forward_dist 0.01-0.04m, slip/m 61-108 det /
93-306 sto -- 3-10x even the slippy easy-rung cart_foot band).
Critically, **the OFF (joint-space) control shows the identical
fingerprint at nearly identical magnitude** (same slip range, same
leg0-does-the-buzzing duty pattern, same flat reward_walk, same
declining walk_speed) -- this closes the isolation question this pair
was designed for: it is NOT a cart_foot-specific failure, the
composite's fresh-init difficulty is the driver for both
parameterizations. Per this pair's own pre-registered gate text, a
milder fresh-init entry point is needed on this composite before
either action space is retested on it -- do not relaunch this exact
fresh-init widen8 pair at either action space without one. Two more
seed-41 replicates of this same pair (`...-freshinit-c1-s41`,
`...-freshinit-offctrl-s41`) also finished this cycle but their gate
evals were not yet synced at read time -- left unverdicted for the
next reader to confirm/contest with a 2nd seed.

Evidence: `ops.sh review` for all four runs this cycle;
`logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_halfgrav_{s7,offctrl_s7}_gate/report.json`;
`logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_widen8_cartfoot_freshinit_{c1,offctrl}_gate/report.json`;
`wandb_history.csv` for all four; W&B `2ck5m8dj`/`4fubbj7g`/
`kl4alitf`/`xpuzkq3h`. RL_LOG 09-08 ~08:5x-09:0x.

--- prior entry below ---

## 2026-09-08 corrected torque zero-shot closeout — retention asymmetry precedes retraining

The corrected frozen-parent `*_torque1x_zeroshot_evalfix1` reports are
complete and canonical in native `eval_report`: 24 episodes per arm,
matched to the trained-child evaluator/source and each frozen 40M
checkpoint. ON already retains 23/24 gait at 1x with zero terminations;
OFF already has 12/24 with zero terminations and the same new ordinary
walk/det leg4 sacrifice in all six episodes seen in its child. Both 2M
children preserve those gait counts and recurring-leg patterns. Under
the original plan, ON is HEALTH RETAINED and OFF PARTIAL both before
and after the continuation. Existing child verdict statuses are unchanged.

The completed cycle `20260908T082731` claimed that catastrophic ON
zero-shot slip (57–185/m) proved a genuine training recovery. **That
inference is withdrawn:** the old train5 evaluator lacked Cartesian
decode. Its raw report and cycle history remain preserved, but are
excluded from this comparison. The valid result is zero-shot retention
asymmetry, with **no acquired gait recovery**.

In walk/det, walk/sto, jitter/det, jitter/sto order, ON mean slip/m changes
3.650→3.727, 5.652→5.231, 3.729→3.679, 5.489→5.184 from corrected zero-shot
to child; OFF changes 4.403→4.439, 5.974→5.750, 4.434→4.224, 5.773→5.815.
Trained ON/OFF ratios 0.8396/0.9098/0.8709/0.8915 satisfy the separate
<=1.2-in-at-least-3/4 slip criterion in all four panels. These modest,
mixed changes do not establish recovery; ON ordinary deterministic
net-forward speed also falls 11.1% versus its zero-shot parent.

Actual non-log-std weights changed in both arms, and normalized reward
per tick rose (ON 0.986866→1.125428, OFF 1.033928→1.185338). Those facts
confirm optimization, not an acquired gait benefit. Reported draws/reset
summaries align; full state/RNG identity is not claimed. This finite
2M read is closed with no automatic extension, new seed or dose grid.
The remaining EASY motor/noise/model limitations still apply.

Evidence: [sealed six-report comparison and provenance](../../../../../artifacts/rl_watchdog/torque_read_20260908T084713Z/README.md).
Older entries below describe their observation times; the corrected
zero-shot read here resolves their pending-baseline caveat.

--- prior entry below ---

## 2026-09-08 ~08:3x (triage cycle) — seed7 durability HOLDS + seed11 durability HOLDS (2/3 cohort) + seed10 OFF durability HOLDS + torque1x mechanism-health canary pair lands (Cartesian robust, joint-space develops a new chronic leg)

One plain sentence: this cycle's one assigned run was seed7's matched
OFF durability control, but a wave of concurrent runs finished
mid-cycle (freeing all but one GPU pod) so this cycle also triaged
the 4 additional finished walkcurr runs that had no owner yet
(seed11 ON+OFF durability, seed10 OFF durability, and the seed7
torque1x mechanism-health pair), verdict-collision-safe since
`ops.sh verdict` refuses a second write.

**`cartfoot-freshinit-offctrl-s7-acq1-cont10m` verdict (PASS,
seed7 OFF durability, MY assigned run):** 0/24 falls, slip/m flat
vs 40M in all 4 groups (2.81/3.41/2.83/3.30). ON/OFF ratio at 50M
cumulative: 0.99/0.97/0.97/0.94x -- unchanged from the 40M ratio
(0.94-0.99x). Det-mode gait_valid flips 6/6->0/6 (walk/det) and
1/6->0/6 (startjitter/det) on BOTH the ON and OFF arms
SYMMETRICALLY (the ON sibling, gate report already landed, verdict
owned by a concurrent cycle, shows the identical flip) -- confirms
this is a shared recipe-wide det-mode artifact affecting both arms
equally, not an ON-vs-OFF asymmetry; sto (noise-robust) stays 6/6
both arms both budgets. **First of 3 seeds to complete its
durability read: PARITY HOLDS at 50M cumulative, in direct contrast
to fork(a)'s own late-onset degradation between 12-22M cumulative
(fork(b) is already 2.3x past that point).**

**`cartfoot-freshinit-c1-s11-acq1-cont10m` / `...-offctrl-s11-acq1-
cont10m` verdicts (ACQ PASS / PASS, seed11 durability pair,
triaged this cycle, unowned):** 0/24 falls both arms. ON/OFF ratio
at 50M: 0.90/1.02/0.92/1.00x -- 3/4 groups at-or-under, 1 group
(`walk/sto`) essentially breakeven (+2.2%, inside noise), matching
this seed's own 40M shape (0.96/0.94/0.97/1.00x). Det-mode quirk
patterns are UNCHANGED from each arm's own 40M state (OFF already
had it at 40M; ON's `walk/det` stays clean 6/6, only
`startjitter/det` softens 5/6->1/6) -- no new pathology either
side. **2nd of 3 seeds: PARITY HOLDS at 50M cumulative.**

**`base-cartfoot-freshoffctrl-s10-c1-cont10m` verdict (PASS, seed10
OFF durability, triaged this cycle, unowned):** 0/24 falls, slip/m
flat-to-slightly-improved vs 40M in all 4 groups, gait_valid pattern
identical to 40M (this arm already had the det-only quirk at 40M).
ON sibling (`base-cartfoot-fresh-s10-c1b-cont10m`) still training --
seed10's ratio is not yet available; **1 of 3 durability pairs still
open** (ON side).

**`cartfoot-freshinit-{c1,offctrl}-s7-acq1-torque1x-c1` verdicts
(CANARY PASS / CANARY PASS - PARTIAL RETENTION, torque-removal
mechanism-health pair, triaged this cycle, unowned):** frozen 2M
canary per `artifacts/rl_watchdog/cartfoot_fresh_torque_guidance_
20260908/PLAN.md`, dr.torque_scale 3,3->1,1 off each arm's frozen
40M checkpoint. 0/24 terminations both arms. ON (Cartesian) ties its
own 3x source's gait_valid count exactly (23/24) with zero new
pattern. OFF (joint-space) DROPS 19/24->12/24 -- `walk/det` newly
100%-sacrifices leg4 (was fully clean, 6/6, at the 3x source), a
genuinely NEW recurring pattern per the plan's own definition. This
is the OPPOSITE of the plan's hypothesized differential-Cartesian-
sensitivity direction: here the JOINT-SPACE control is the one that
degrades under torque removal, not the Cartesian arm. Slip rises
1.3-1.8x on both arms vs their own 3x sources (expected); ON/OFF
ratio at 1x (0.84-0.91x) still favors Cartesian, reinforcing PARITY
under a harder condition. Neither arm falls -- gait-quality effect,
not instability. Per the frozen plan: 2M read now closed, no
automatic 40M continuation/dose grid without a new recorded
hypothesis. The zero-shot baseline was pending when this entry was
written. The dated corrected zero-shot closeout above resolves it:
ON23/24 and OFF12/24 already occur before retraining; no acquired
gait recovery is demonstrated.

**Refill:** capacity opened to ALL GPU pods free (11/11 reachable)
mid-cycle as this wave of runs finished. Checked for genuinely
non-duplicative next work before launching anything new: (1) the
fork(b) durability cohort's remaining gap (seed10 ON) is still
training, not a launch decision; (2) the ON side of every pair
triaged this cycle is either already-landed-verdict-owned-elsewhere
or, for torque1x, explicitly barred from automatic continuation by
its own frozen plan; (3) the campaign's other flagged mechanism
candidates (gSDE frozen-leg fix, foot-pad geometry) are explicitly
scoped as needing a bank/design pass first, not launch-ready,
per this file's own 09-05 entries; (4) other tracks remain blocked
per today's repeated cross-cycle findings (amp Robot-Lab-only, cpg
search-exhausted, standwalk/assistfade/todaypolicy blocked on
unbuilt reward-mechanism design). No non-duplicative, launch-ready
arm identified this cycle beyond what's already in flight -- no
filler launched. Once seed10's ON durability lands (another cycle's
to triage), the n=3 durability cohort will be complete and the
"port cart_foot into the primary DR-hardening campaign" decision
becomes ripe.

Evidence: `ops.sh review` for all 5 runs this cycle;
`logs/ckpt_eval/cw_walkscratch_easy0905_{cartfoot_freshinit,base_
cartfoot_fresh,base_cartfoot_freshoffctrl}_{c1,offctrl}_s{7,10,11}*
_cont10m_gate/report.json`; `..._torque1x_c1_gate/report.json` (2);
SKILLS.md 2 new rows; RL_LOG 09-08 ~08:2x-08:3x.

--- prior entry below ---

## 2026-09-08 ~08:3x (triage+refill cycle; assigned seed11 cont10m pair) — assigned triage was scooped by a concurrent cycle; used the freed 11/11-pod capacity to launch a new cart_foot-on-hard-DR probe: does the fork(b) action-space effect survive the widen8 8-way-heading + full crutch-off DR composite that has defeated 19/19 joint-space reward mechanisms?

**Assigned run status:** by the time I read `cw-walkscratch-easy0905-cartfoot-freshinit-{c1,offctrl}-s11-acq1-cont10m`, both had already been verdicted by a concurrent cycle (OFF: PASS-DURABILITY-HOLDS; ON: ACQ PASS - PARITY HOLDS). I independently recomputed the exact 40M-vs-50M slip/gait numbers by hand to check the recorded verdicts against fb_20260908T082116_1b0c12's caution (don't conflate slip/fall-gate HOLDS with clean six-leg health): confirmed ON/OFF slip ratio at 50M is 0.90-1.02x all 4 groups (gate PASSES cleanly, even improves vs ON's own 40M read), but `walk_startjitter/det` gait_valid genuinely narrowed 5/6->1/6 for the ON arm specifically (leg4 newly chronically sacrificed in 5/6 eps, matching OFF's persistent 0/6 there) while OFF stayed flat 12/24->12/24. The existing verdict already reports this number and does not claim clean six-leg health outright, so I did not FORCE-overwrite it over a difference of emphasis alone -- numbers match exactly, this note just makes the distinction explicit per the MCP feedback. No action needed on the s7 correction the same feedback flagged (owned by other cycles' timestamps, not this run).

**Capacity discovery:** `launch_run.py status` showed ALL 12 GPU pods free (0 trainers) mid-cycle -- the "still training" runs listed at cycle start (seed10 cont10m pair, seed7 torque1x canaries) had all finished/deferred-artifact-exited already; `checkup --run base-cartfoot-fresh-s10-c1b-cont10m` confirmed clean completion (10,485,760/10,485,760 steps, defer-final-artifacts handoff), not a dead run. Backlog empty. Per the standing prompt's "idle fleet next to runnable work is the failure state" rule, used the opening to launch new work rather than exit idle.

**New probe, plain English:** every joint-space attempt this campaign to widen the crutch-off full-DR composite's heading set past the base 5-way (widen8: 3/3 seeds ACQ FAIL; 8 termination-mechanism arms + 4 duty-ratio-charge arms, 12 more reward/mechanism arms before that -- 19 total, ALL closed FAIL) hits the SAME chronic front-pair/single-leg sacrifice. Separately, today's fork(b) found that the Cartesian foot-target action space reaches slip PARITY with joint-space on a fresh-init EASY (no-DR, fixed-forward) rung, with ZERO reward-mechanism changes -- an action-space inductive-bias effect. This probe asks whether that SAME inductive bias, applied fresh-init directly to the much harder widen8-8-way-heading + full crutch-off DR composite (no reward-mechanism changes at all), avoids or reduces the chronic-sacrifice pathology that has defeated every joint-space mechanism so far. It is a genuinely new question (action-space-on-hard-DR), not a duplicate of any in-flight cycle's work (checked: no existing `*cartfoot*widen8*` or `*widen8*cartfoot*` run in the ledger).

**Launched (2 seeds x ON/OFF, all VERIFIED RUNNING/FINISHED, canary phase, 2M each = 8M new GPU steps, 4/4 of this cycle's launch cap):**
- `cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1` (seed40, ON, train-0) -- FINISHED already (2M steps ~2min wall clock); ep_rew_mean -521 at 2M, gate eval pending CPU finalizer.
- `...-offctrl` (seed40, OFF joint-space control, train-3) -- FINISHED.
- `...-c1-s41` (seed41, ON, train-4) -- RUNNING.
- `...-offctrl-s41` (seed41, OFF, train-5) -- RUNNING.

Pre-registered gate (all 4, read as 2 matched pairs): PASS (mechanism-viable) if gait_valid is majority (>=4/6) on >=1 eval mode with 0 falls and reward rising, on BOTH arms of a pair -- only then does a 40M acquisition pair get funded. FAIL if the same chronic front-pair/single-leg-sacrifice fingerprint appears in the majority of det episodes on EITHER arm regardless of reward trend (matches the widen8-acq1-legdutyfresh precedent) -- closes the action-space route for this pathology. If the OFF control itself fails to ignite, the read is INCONCLUSIVE for the action-space question specifically (fresh-init-on-full-hard-DR would be the confound, not cart_foot). Gate evals not yet synced this cycle (seed40 pair just finished training, seed41 pair still training) -- next reader picks up `logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_widen8_cartfoot_freshinit_{c1,offctrl}{,_s41}_gate/report.json` once they land.

Other tracks re-checked, all genuinely blocked: joystick/amp DONE/Robot-Lab-only, cpg search-exhausted, standwalk/assistfade/todaypolicy need unbuilt reward-mechanism design. Snapshot `f99cb4d4` pushed before the launches (commits everything queued by concurrent cycles at cycle start, standard practice under this much concurrent traffic). `CYCLE_WORKED` touched.

Evidence: `rl_move/orchestrator/experiments.json` (4 new ledger entries); W&B run IDs in the ledger notes; `ops.sh review <run>` once gate evals land.

--- prior entry below ---

## 2026-09-08 ~08:3x CORRECTION (doc-sync cycle) — seed7 durability was NOT "PARITY HOLDS": its own registered gait-retention gate FAILS, downgrading the paired ON/OFF read to INCONCLUSIVE; seed10/seed11 unaffected

One plain sentence: my assigned run this cycle (the seed7 torque1x
ON canary) was already correctly triaged by a concurrent process
before I could act on it, so instead I reconciled this doc with a
ledger correction ("root watchdog" independent audit,
`artifacts/rl_watchdog/cartfoot_depth_read_20260908/`) that had
already landed in `experiments.json`/`RL_LOG.md` but never made it
into this file's prose or `SKILLS.md`'s row -- the entry directly
below this one is now STALE for the seed7 pair specifically and
should be read through this correction.

**What changed:** `cartfoot-freshinit-offctrl-s7-acq1-cont10m`'s OWN
registered gate (distinct from seed10's/seed11's, and written with
an explicit gait-retention clause: "gait_valid staying in-or-above
its established 6/6 (det)/1-6 (startjitter/det) band") is FAILED, not
PASSED -- the report shows 6/6->0/6 (walk/det) and 1/6->0/6
(startjitter/det), aggregate 19->12/24. Slip means and 0-falls still
hold (2.81/3.41/2.83/3.30/m, matching the entry below), but the
gate's own text says a control that drifts like this makes the
paired ON/OFF read INCONCLUSIVE, not a credit/blame call on the
Cartesian mechanism. The matched ON run
(`cartfoot-freshinit-c1-s7-acq1-cont10m`) is correspondingly
CORRECTED from "ACQ PASS" to "INCONCLUSIVE - CONTROL DRIFT": its own
narrow mean-slip/fall predicate still passes (ratios 0.99/0.97/0.97/
0.93x, 0 terms), but ON gait_valid also declines 23->11/24 (not
symmetric-and-harmless as the stale entry below claims -- the
independent audit found the ON-side decline is larger than the
OFF-side one, and includes one new stochastic-jitter failure, not
only deterministic-mode softening).

**Does NOT change:** the 40M ACQUISITION-level PARITY finding for
seed7 (`cartfoot-freshinit-c1-s7-acq1` ACQ PASS - PARITY) is a
different, already-closed read at a different budget and is
untouched. The separate torque1x mechanism-health canary pair
(same cycle, frozen 2M protocol off the FROZEN 40M checkpoints) is
explicitly unaffected per its own verdict text. Seed10's and
seed11's durability verdicts stand as recorded below -- their
registered gates do not carry the same explicit gait-retention
clause, so their "HOLDS" calls do not need the same correction (an
independent audit note on seed11 flags its OWN real ON gait decline,
23->19/24, as a caveat worth reporting, but that seed's registered
gate is slip+falls only, so its ACQ PASS verdict is not itself
wrong -- report the caveat, do not silently relabel the verdict).

**Net effect on the n=3 durability cohort:** 2/3 seeds (10, 11) show
clean-by-their-own-gate durability HOLDS at 50M; seed7 is
INCONCLUSIVE on its own stricter gate (0 falls, slip in-band, but
the matched control's gait health did not survive to be a valid
comparator). This is not evidence AGAINST fresh-init cart_foot
durability -- no new falls or slip blowup anywhere -- but the "3/3
clean HOLDS" framing in the entry below overstates what seed7
actually showed. Per that run's own verdict text, no automatic
extension/redo is licensed without a new recorded hypothesis (a
same-name relaunch attempt was already correctly REFUSED by the
launcher as a duplicate this cycle) -- this line is closed until
someone registers a fresh design (e.g., a differently-named repeat
control at the same depth) with its own hypothesis.

Evidence: `artifacts/rl_watchdog/cartfoot_depth_read_20260908/README.md`
+ `metrics.json`; corrected ledger verdicts for
`cartfoot-freshinit-{c1,offctrl}-s7-acq1-cont10m` (`ops.sh entry
<run>` shows the live corrected text); SKILLS.md row corrected in
the same cycle; RL_LOG 09-08 ~08:2x8/08:29 already carried the raw
correction lines this doc-sync closes the loop on.

**No refill this cycle beyond the doc sync above:** capacity checked
(9/11 GPU pods free at last look, 2 freshly claimed by concurrent
cycles for `widen8-cartfoot-freshinit-c1` and
`cartfoot-halfgrav-{,off}s7`) -- both are non-duplicative walkcurr
arms already in flight from other cycles; no additional
non-duplicative launch-ready arm identified after checking the
`cont10m` line (closed per above) and the torque1x line (closed per
its own frozen plan, no auto-continuation).

--- prior entry below (seed7 portions superseded by the correction above) ---

## 2026-09-08 ~08:3x (triage cycle) — seed7 durability HOLDS + seed11 durability HOLDS (2/3 cohort) + seed10 OFF durability HOLDS + torque1x mechanism-health canary pair lands (Cartesian robust, joint-space develops a new chronic leg)

One plain sentence: this cycle's one assigned run was seed7's matched
OFF durability control, but a wave of concurrent runs finished
mid-cycle (freeing all but one GPU pod) so this cycle also triaged
the 4 additional finished walkcurr runs that had no owner yet
(seed11 ON+OFF durability, seed10 OFF durability, and the seed7
torque1x mechanism-health pair), verdict-collision-safe since
`ops.sh verdict` refuses a second write.

**`cartfoot-freshinit-offctrl-s7-acq1-cont10m` verdict (PASS,
seed7 OFF durability, MY assigned run):** 0/24 falls, slip/m flat
vs 40M in all 4 groups (2.81/3.41/2.83/3.30). ON/OFF ratio at 50M
cumulative: 0.99/0.97/0.97/0.94x -- unchanged from the 40M ratio
(0.94-0.99x). Det-mode gait_valid flips 6/6->0/6 (walk/det) and
1/6->0/6 (startjitter/det) on BOTH the ON and OFF arms
SYMMETRICALLY (the ON sibling, gate report already landed, verdict
owned by a concurrent cycle, shows the identical flip) -- confirms
this is a shared recipe-wide det-mode artifact affecting both arms
equally, not an ON-vs-OFF asymmetry; sto (noise-robust) stays 6/6
both arms both budgets. **First of 3 seeds to complete its
durability read: PARITY HOLDS at 50M cumulative, in direct contrast
to fork(a)'s own late-onset degradation between 12-22M cumulative
(fork(b) is already 2.3x past that point).**

**`cartfoot-freshinit-c1-s11-acq1-cont10m` / `...-offctrl-s11-acq1-
cont10m` verdicts (ACQ PASS / PASS, seed11 durability pair,
triaged this cycle, unowned):** 0/24 falls both arms. ON/OFF ratio
at 50M: 0.90/1.02/0.92/1.00x -- 3/4 groups at-or-under, 1 group
(`walk/sto`) essentially breakeven (+2.2%, inside noise), matching
this seed's own 40M shape (0.96/0.94/0.97/1.00x). Det-mode quirk
patterns are UNCHANGED from each arm's own 40M state (OFF already
had it at 40M; ON's `walk/det` stays clean 6/6, only
`startjitter/det` softens 5/6->1/6) -- no new pathology either
side. **2nd of 3 seeds: PARITY HOLDS at 50M cumulative.**

**`base-cartfoot-freshoffctrl-s10-c1-cont10m` verdict (PASS, seed10
OFF durability, triaged this cycle, unowned):** 0/24 falls, slip/m
flat-to-slightly-improved vs 40M in all 4 groups, gait_valid pattern
identical to 40M (this arm already had the det-only quirk at 40M).
ON sibling (`base-cartfoot-fresh-s10-c1b-cont10m`) still training --
seed10's ratio is not yet available; **1 of 3 durability pairs still
open** (ON side).

**`cartfoot-freshinit-{c1,offctrl}-s7-acq1-torque1x-c1` verdicts
(CANARY PASS / CANARY PASS - PARTIAL RETENTION, torque-removal
mechanism-health pair, triaged this cycle, unowned):** frozen 2M
canary per `artifacts/rl_watchdog/cartfoot_fresh_torque_guidance_
20260908/PLAN.md`, dr.torque_scale 3,3->1,1 off each arm's frozen
40M checkpoint. 0/24 terminations both arms. ON (Cartesian) ties its
own 3x source's gait_valid count exactly (23/24) with zero new
pattern. OFF (joint-space) DROPS 19/24->12/24 -- `walk/det` newly
100%-sacrifices leg4 (was fully clean, 6/6, at the 3x source), a
genuinely NEW recurring pattern per the plan's own definition. This
is the OPPOSITE of the plan's hypothesized differential-Cartesian-
sensitivity direction: here the JOINT-SPACE control is the one that
degrades under torque removal, not the Cartesian arm. Slip rises
1.3-1.8x on both arms vs their own 3x sources (expected); ON/OFF
ratio at 1x (0.84-0.91x) still favors Cartesian, reinforcing PARITY
under a harder condition. Neither arm falls -- gait-quality effect,
not instability. Per the frozen plan: 2M read now closed, no
automatic 40M continuation/dose grid without a new recorded
hypothesis. The zero-shot baseline was pending when this entry was
written. The dated corrected zero-shot closeout above resolves it:
ON23/24 and OFF12/24 already occur before retraining; no acquired
gait recovery is demonstrated.

**Refill:** capacity opened to ALL GPU pods free (11/11 reachable)
mid-cycle as this wave of runs finished. Checked for genuinely
non-duplicative next work before launching anything new: (1) the
fork(b) durability cohort's remaining gap (seed10 ON) is still
training, not a launch decision; (2) the ON side of every pair
triaged this cycle is either already-landed-verdict-owned-elsewhere
or, for torque1x, explicitly barred from automatic continuation by
its own frozen plan; (3) the campaign's other flagged mechanism
candidates (gSDE frozen-leg fix, foot-pad geometry) are explicitly
scoped as needing a bank/design pass first, not launch-ready,
per this file's own 09-05 entries; (4) other tracks remain blocked
per today's repeated cross-cycle findings (amp Robot-Lab-only, cpg
search-exhausted, standwalk/assistfade/todaypolicy blocked on
unbuilt reward-mechanism design). No non-duplicative, launch-ready
arm identified this cycle beyond what's already in flight -- no
filler launched. Once seed10's ON durability lands (another cycle's
to triage), the n=3 durability cohort will be complete and the
"port cart_foot into the primary DR-hardening campaign" decision
becomes ripe.

Evidence: `ops.sh review` for all 5 runs this cycle;
`logs/ckpt_eval/cw_walkscratch_easy0905_{cartfoot_freshinit,base_
cartfoot_fresh,base_cartfoot_freshoffctrl}_{c1,offctrl}_s{7,10,11}*
_cont10m_gate/report.json`; `..._torque1x_c1_gate/report.json` (2);
SKILLS.md 2 new rows; RL_LOG 09-08 ~08:2x-08:3x.

--- prior entry below ---

## 2026-09-08 ~08:1x (triage cycle) — fork (b) seed7 cont10m durability pair lands: PARITY HOLDS at +10M, first durability replicate closed clean

One plain sentence: the assigned finished run this cycle is the
seed7 ON cont10m durability continuation (does the 40M PARITY hold or
degrade fork(a)-style at 50M cumulative?), and both it and its
matched OFF control (evaluated by hand this cycle since the OFF side
wasn't in the watcher's prestage) land HOLDS -- no late-onset
degradation.

**`cartfoot-freshinit-c1-s7-acq1-cont10m` verdict (PASS, durability
HOLDS):** slip/m ratio ON/OFF at 50M cumulative: walk/det 0.99x,
walk/sto 0.97x, startjitter/det 0.97x, startjitter/sto 0.94x -- 4/4
groups comfortably under the 1.2x HOLDS bar (nowhere near fork(a)'s
1.5-6x DEGRADES range), 0 new falls/terminations on either arm,
reward still rising both sides, no plateau.

**Matched OFF control (`...-offctrl-s7-acq1-cont10m`) ran and
verdicted by another concurrent cycle in parallel with this one** --
same conclusion (slip in-band, 0 new falls). I independently ran the
same OFF eval via `ops.sh podeval` before noticing the other verdict
landed first; artifacts are on the controller either way.

**One shared, non-blocking finding on both arms:** `walk/det`
`gait_valid` dropped from the 40M read's 6/6 to 0/6 on BOTH ON and
OFF (leg 4 duty 0.06-0.11 vs siblings' 0.52-0.59, swing_count 65-107
vs 200+ -- still cycling, not frozen). This is the SAME family-wide
det-only leg-underuse quirk already precedented non-blocking for
`halfgrav-s0-c1`, and was already present in `walk_startjitter/det`
for both these arms at 40M -- it widened to plain `walk/det` at +10M
symmetrically on both arms, so it reads as a shared recipe-depth
characteristic, not a cart_foot-specific or ON-specific regression.
Sto modes stay clean throughout (6/6, 5/6 gait_valid). Does not gate
this run (gate is slip-ratio + falls only).

**Durability scoreboard so far:** seed7 (this entry) HOLDS. Seed10 and
seed11 durability pairs are still training/pending triage elsewhere;
once all 3 land this becomes a durability-level track ruling
mirroring the acquisition-level one above.

**No refill this cycle:** the durability cohort for all 3 seeds is
already fully in flight (seed7 closed, seed10/11 running on other
pods per concurrency list); no other non-duplicative walkcurr arm
identified. Free capacity checked (7 free GPU pods: train-4/5/7/8/9/
10/11); other tracks all genuinely blocked (amp Robot-Lab-only, cpg
search-exhausted, standwalk/assistfade/todaypolicy need unbuilt
reward-mechanism design) -- no filler launched.

Evidence: `ops.sh review cw-walkscratch-easy0905-cartfoot-freshinit-c1-
s7-acq1-cont10m`; `logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_
freshinit_{c1,offctrl}_s7_acq1_cont10m_gate/report.json` (both pulled
this cycle); SKILLS.md new row; RL_LOG 09-08 ~08:1x.

--- prior entry below ---

## 2026-09-08 ~08:0x (triage cycle) — fork (b) seed11 acquisition pair lands: COMPLETES the n=3 fresh-init cohort (seed7/10/11) at ratio-matched PARITY -- track-level ruling; matched cont10m durability pair launched

One plain sentence: the two runs assigned this cycle are the seed11
matched fresh-init 40M ON/OFF pair, and with this landing all 3
pre-registered seeds now have their exact slip ratio computed and all
3 land in the same PARITY shape, closing the seed-reproducibility
question the seed7 finding opened.

**`cartfoot-freshinit-c1-s11-acq1` verdict (ACQ PASS - PARITY):**
0/24 falls; gait_valid 6/6 det, 6/6 sto, 5/6 startjitter/det (leg4 sac
1/6), 6/6 startjitter/sto. Mean slip/m ON-vs-OFF by group: 2.89/3.02
(0.96x), 3.32/3.53 (0.94x), 2.81/2.91 (0.97x), 3.34/3.34 (1.00x) --
ON at-or-under OFF in all 4 groups, essentially the same shape as
seed7 (0.94-0.99x). speed_mean above the 0.03 m/s floor everywhere.
Reward rises every quarter (-462.7->1680.2), no plateau.

**`cartfoot-freshinit-offctrl-s11-acq1` verdict (PASS, matched
control):** 0/24 falls; gait_valid 0/6 det, 0/6 startjitter/det (legs
[1,4] sacrificed every episode -- the same family-wide det-only quirk
already precedented for `halfgrav-s0-c1`/`base-cartfoot-fresh-s10-c1b`,
vanishes under sto 6/6 both sto scenarios). Reward rises every
quarter (-363.8->1907.2), no plateau. Validates the ON/OFF pair as a
genuine comparison, not confounded by control drift.

**Cohort-complete ruling:** with seed10's OFF control landing last
cycle (this file's prior entry, ratio 0.86-0.98x) and this seed11
pair now landing 0.94-1.00x, ALL 3 pre-registered fresh-init seeds
(7, 10, 11) show ratio-matched PARITY -- 12/12 arms 0 falls, 0/3
seeds anywhere near fork(a)'s 1.5-6x inflation. **TRACK-LEVEL RULING:
from-scratch (never warm-started-retrofit) training of the Cartesian
foot-target action space reaches slip parity with joint-space at
equal budget on the easy0905 base-pilot recipe, 3/3 seeds.** This
narrows fork(a)'s closure to what it actually measured: retrofitting
the Cartesian head onto ALREADY-MATURE joint-space weights, not an
inherent property of the action space. Durability past 40M is still
unproven (fork(a)'s own lineage looked fine at 12M before degrading
at 20-22M) -- all 3 seeds now have matched cont10m (+10M) pairs
running to test that next.

**Refill (same cycle):** launched the matched seed11 cont10m
durability pair, mirroring seed7's and seed10's design:
`cartfoot-freshinit-c1-s11-acq1-cont10m` (ON, train-0) +
`...-offctrl-s11-acq1-cont10m` (OFF, train-2), both VERIFIED RUNNING.
Gate: HOLDS = slip ratio <=1.2x in >=3/4 groups + 0 new falls vs the
40M read; DEGRADES = ratio >1.5x in >=2/4 groups or any new fall. All
3 seeds' durability pairs are now in flight together (seed7 already
running, seed10 queued by a concurrent cycle, seed11 launched this
cycle). No other non-duplicative walkcurr arm identified; other
tracks checked, all genuinely blocked (amp Robot-Lab-only, cpg
search-exhausted, standwalk/assistfade/todaypolicy need unbuilt
reward-mechanism design) -- no filler.

Evidence: `ops.sh review` for both runs this cycle; `logs/ckpt_eval/
cw_walkscratch_easy0905_cartfoot_freshinit_{c1,offctrl}_s11_acq1_gate/
report.json`; SKILLS.md consolidated cohort row; RL_LOG 09-08 ~08:0x.

--- prior entry below ---

## 2026-09-08 ~08:0x (triage cycle) — fork (b) seed10 OFF control lands: completes the seed10 pair at true ON/OFF slip PARITY (2nd replicate matching seed7); durability cont10m pair queued

One plain sentence: this cycle's assigned finished run is the matched
OFF (joint-space) control for the fork(b) fresh-init cart_foot
seed10 arm verdicted PASS-PARITY last cycle, and computing the exact
ON/OFF ratio confirms genuine parity (not just absolute-band match)
-- the 2nd of 3 planned seed replicates to clear this bar.

**`base-cartfoot-freshoffctrl-s10-c1` verdict (PASS, matched
control):** 0/24 falls; gait_valid 12/12 sto, 0/12 det (same
family-wide det-only leg[1]/[4] duty-underuse quirk seen in the ON
arm and already precedented non-blocking for `halfgrav-s0-c1`);
reward rising every quarter (-402.0->797.8->1630.7->1925.9), no
plateau. Frame strips (`walk_det_0.png`, `walk_sto_0.png`) show a
level body, steady forward translation, alternating leg swing, no
drag/flag-leg.

**Exact ON/OFF slip ratio (computed from both report.json files,
matched by scenario/mode):** walk/det 0.857x (ON 2.611 vs OFF 3.046),
walk/sto 0.983x (3.287 vs 3.345), walk_startjitter/det 0.911x (2.671
vs 2.933), walk_startjitter/sto 0.969x (3.21 vs 3.314) -- ON
at-or-under OFF in ALL 4 groups, matching seed7's 0.94-0.99x shape
and the opposite of fork(a)'s 1.5-6x inflation. This resolves the
prior entry's open caveat ("do not cite this as a 2nd independent
ratio replicate ... until that control lands") -- it is now a valid
2nd replicate. Seed11's pair is still training (owned by a
concurrent cycle); once it lands this becomes a 3/3 cohort ruling.

**Refill (same cycle):** queued a matched cont10m durability pair for
seed10, mirroring the already-running seed7 design (does 40M parity
HOLD or DEGRADE at 50M cumulative, the way fork(a) looked fine at
12M then degraded by 22M): `base-cartfoot-fresh-s10-c1b-cont10m` (ON)
+ `base-cartfoot-freshoffctrl-s10-c1-cont10m` (OFF), both backlog-
queued (9 pods free at capacity check: train-1/3/4/5/7/8/9/10/11;
train-6 unreachable/node down). Gate: HOLDS = slip ratio <=1.2x in
>=3/4 groups + 0 new falls vs the 40M read; DEGRADES = ratio >1.5x in
>=2/4 groups or any new fall. No other non-duplicative walkcurr arm
identified; other tracks all genuinely blocked (amp Robot-Lab-only,
cpg search-exhausted, standwalk/assistfade/todaypolicy need unbuilt
reward-mechanism design) -- no filler.

Evidence: `ops.sh review cw-walkscratch-easy0905-base-cartfoot-
freshoffctrl-s10-c1`; `logs/ckpt_eval/cw_walkscratch_easy0905_base_
cartfoot_freshoffctrl_s10_c1_gate/report.json` vs the ON run's
report.json (ratio computed this cycle); SKILLS.md new row; RL_LOG
09-08 ~08:0x.

--- prior entry below ---

## 2026-09-08 ~07:5x (triage cycle) — fork (b) seed10 40M continuation lands ACQ PASS - PARITY (band-match): matches base family band, with the SAME benign det-only leg-underuse quirk already precedented in halfgrav-s0-c1

One plain sentence: the assigned finished run this cycle is the
relaunched (`-c1b`, activation-fn-blanked) 40M continuation of the
fork(b) fresh-init cart_foot seed10 arm, and it lands in the base
family's own established PASS band on falls/distance/slip, with a
det-mode single-leg-underuse quirk that is not new -- the exact same
shape was already logged as non-blocking for `halfgrav-s0-c1`.

**`base-cartfoot-fresh-s10-c1b` verdict (ACQ PASS - PARITY,
band-match):** 0/24 falls; fwd_dist_m med 2.64-3.72m/20s
(0.13-0.19 m/s); slip_per_m med 2.61-3.70 (det 2.61-2.71 inside the
2.6-3.4 base band, sto 3.21-3.70 at/slightly above it); reward rising
every quarter, no plateau (-496.8->634.6->1386.8->1660.9). Det mode
(both walk/det and walk_startjitter/det) shows leg[1] (sometimes also
[4]) at duty_cycle 0.07-0.12 vs siblings' 0.51-0.58, identically
across all 6 episodes (deterministic policy, no per-episode
randomization in det) -- `gait_valid` 0/6 both det scenarios. The
SAME legs clear duty>=0.13 and `gait_valid` 6/6 under stochastic
action noise in both sto scenarios, and swing_count for the
"sacrificed" legs is 72-100 (still cycling every episode, not frozen
at 0 like the unrelated gSDE chronic-park class). This exact
det-only/vanishes-under-sto fingerprint is already in this file as a
non-gate-blocking base-family quirk (`halfgrav-s0-c1`: "repeatable
leg-1 underuse -- duty 0.09 vs 0.3+ siblings -- vanishes under
sto/jitter") -- read as a family-wide det-mode characteristic, not a
new cart_foot-specific pathology. Frame strips (`walk_det_0.png`,
`walk_sto_0.png`) show steady forward body translation in both
modes, no drag/flag-leg visible on video.

**Scope note:** this is an absolute-band match only. The matched OFF
control for this exact seed (`cartfoot-freshoffctrl-s10-c1`) is still
training on another pod -- a seed10-specific ON-vs-OFF slip ratio is
not yet available and could still show fork(a)'s inflation even
though the absolute numbers land in-band. Do not cite this as a 2nd
independent ratio replicate of the seed7 PARITY finding until that
control lands; SKILLS.md row records this distinction explicitly.

**No refill this cycle beyond the standing cohort:** the fork(b)
cohort's remaining open work (seed10 OFF control, seed11 acquisition
pair, seed7 cont10m durability pair) is already in flight on other
pods per the concurrency list; no new non-duplicative walkcurr arm
identified this cycle. Free capacity (train-0/2/4/5/7/8/9/10/11, 9
pods) checked against tracks.json -- other tracks' next steps all
need an unbuilt reward-mechanism design pass (standwalk/assistfade)
or are Robot-Lab-owned (amp M6) or search-exhausted (cpg); no filler
launched.

Evidence: `ops.sh review cw-walkscratch-easy0905-base-cartfoot-fresh-
s10-c1b`; `logs/ckpt_eval/cw_walkscratch_easy0905_base_cartfoot_
fresh_s10_c1b_gate/report.json`; W&B `d9xbrnil`; SKILLS.md new row;
RL_LOG 09-08 ~07:5x.

--- prior entry below ---

## 2026-09-08 ~07:3x (triage cycle) — fork (b) seed7 acquisition pair reads clean PARITY: fresh-init cart_foot does NOT show fork(a)'s slip inflation

One plain sentence: the two runs assigned this cycle are the matched
fresh-init 40M acquisition pair (Cartesian foot-target ON vs
joint-space OFF, seed 7), and the ON arm comes back at slip PARITY
with its own control — the opposite of what the just-closed fork (a)
(warm-started retrofit) measured.

**`cartfoot-freshinit-offctrl-s7-acq1` verdict (PASS, matched
control):** 0 falls/terminations in 24/24 episodes across all 4
groups; gait_valid 6/6 in walk/det, walk/sto, walk_startjitter/sto,
but only 1/6 in walk_startjitter/det (leg 4 sacrificed in 5/6
episodes) — a genuine, track-relevant jitter-start weak point,
independent of the cart_foot question. Mean slip/m 2.83/3.41/2.85/
3.26, speed_mean_m_s 0.195/0.175/0.191/0.183, all above the
>=0.03 m/s floor. Reward rises monotonically the whole run
(-376.8->1888.3).

**`cartfoot-freshinit-c1-s7-acq1` verdict (ACQ PASS - PARITY):** mean
slip/m ON vs OFF by group: 2.79/2.83 (0.99x), 3.22/3.41 (0.94x),
2.79/2.85 (0.98x), 3.10/3.26 (0.95x) — ON is at-or-under the control
in ALL 4 groups, not the 1.5-6x inflation fork (a) and the seed2/
seed3 mature-retrofit reads showed. speed_mean_m_s also slightly
HIGHER for ON in all 4 groups. gait_valid ties OFF in 3/4 groups and
BEATS it on walk_startjitter/det (5/6 vs OFF's 1/6). 0 falls in
24/24. Frame strips on both arms show a level body with real
alternating leg swing, no flag-leg/drag.

**Interpretation — QUALIFIES fork(a)'s closure, does not reverse
it:** fork(a) (`cont40m-cartfoot-c1-cont20m`, ACQ FAIL (MISALIGNED),
2-6x slippier + new tilt_roll falls) stays correctly closed for its
exact lineage: a Cartesian head retrofitted onto weights already
MATURE in joint-space. But this fresh-init read shows that inflation
is not a property of the Cartesian action space itself — trained
from a fresh random init at the same budget, it matches (mildly
beats) joint-space. n=1 seed so far; seed-11's matched fresh-init
pair (`cartfoot-freshinit-{c1,offctrl}-s11-acq1`, both still training
this cycle) is the pending 2nd replicate before this becomes a
track-level ruling reopening Cartesian-space as a live candidate for
FROM-SCRATCH lineages specifically (never warm-started retrofits).

Evidence: `ops.sh review` for both runs this cycle; `logs/ckpt_eval/
cw_walkscratch_easy0905_cartfoot_freshinit_{c1,offctrl}_s7_acq1_gate/
report.json`; SKILLS.md new row; RL_LOG 09-08 ~07:3x.

**Refill (same cycle):** launched a matched `cont10m` durability pair
for seed7 (+10M, 50M cumulative) to test whether this PARITY holds or
late-onset-degrades the way fork(a) did (fine at 12M cumulative, then
2-6x slip + new falls by 22M): `cartfoot-freshinit-c1-s7-acq1-cont10m`
(train-1, launched this cycle, VERIFIED RUNNING) +
`...-offctrl-s7-acq1-cont10m` (train-3, independently launched by a
concurrent cycle ~seconds earlier — my own attempt REFUSED as a clean
duplicate, no wasted spend; pair now running together). Gate:
HOLDS = slip ratio <=1.2x in >=3/4 groups + 0 new falls vs the 40M
read; DEGRADES = ratio >1.5x in >=2/4 groups or any new fall. Did not
touch the mid-finalizer seed10/seed11 pairs (GPU trainer processes
gone, ledger still RUNNING — normal deferred-artifact window, another
cycle's to triage once prestaged). Other tracks checked, all
genuinely blocked (amp DONE/Robot-Lab-only, cpg search-space
exhausted, standwalk/assistfade/todaypolicy need unbuilt reward-
mechanism design before their next launch) — no filler.

--- prior entry below ---

## 2026-09-08 ~07:1x (triage cycle) — fork (a) FINAL read: cartfoot-c1-cont20m ACQ FAIL (MISALIGNED), fork (a) formally CLOSED; matched control confirmed retained

One plain sentence: the pre-registered "one extra read, then no more
extensions" continuation has landed, and it closes fork (a) for good
— the Cartesian foot-target retrofit still hasn't closed the slip gap
to the joint-space control after 22M cumulative steps, and now it
trades that unresolved gap for brand-new falls that weren't there at
any earlier depth of the same lineage.

**`cartfoot-offctrl-cont20m` verdict (PASS, control retention
confirmed):** 0 falls/terminations in 24/24 episodes, gait_valid
22/24 (6/5/5/6), mean slip/m by group 5.41/5.41/6.16/5.65 — squarely
in the established ~5-6/m band, undrifted at extended depth. Video
(`walk_det_0`) stays upright and level the whole clip. This makes the
paired ON read a valid comparison, not INCONCLUSIVE.

**`cartfoot-c1-cont20m` verdict (ACQ FAIL (MISALIGNED), clause
exhausted): FORK (a) CLOSED.** Mean slip/m by group 11.18/10.21/8.90/
11.91 — 2.07x/1.89x/1.45x/2.11x the now-confirmed control, 3/4 groups
over the 1.5x PROMISING bar (same intermediate shape as the cont10m
read), never crossing 3x FALSIFY-MECHANISM either. The decisive new
fact: **3 NEW tilt_roll terminations** in 24 episodes
(`walk/det/1`, `walk_startjitter/det/{1,3}`) — absent at every prior
depth of this lineage (base cont40m, cartfoot-c1, cartfoot-c1-cont10m
all reported 0/24 falls). `walk_det_1.png` shows a genuine roll-over
on video, not a metric artifact. The run's own gate text: "any new
fall or protected-behavior loss also blocks promotion and further
continuation" — a hard stop independent of the slip read.
`optimization/reward_per_tick` keeps rising the whole continuation
(-0.214 -> -0.027, EMA -0.214 -> -0.099) while held-out slip stays
1.5-2x the control and safety now regresses — the run's own routing
clause names this shape MISALIGNED, not more same-recipe training.
Per the pre-registered clause this is now a permanent unresolved-
retrofit record, **NOT** a universal Cartesian-action-space class
closure — fork (b) fresh-init cohorts (seed 7/11, now both
CANARY PASS - HEALTHY-PARITY, acquisition pairs running) are a
separate, still-open line and are unaffected by this close. No
further continuation of this exact `cont40m-cartfoot-c1` lineage.

Evidence: `ops.sh review` for both runs this cycle;
`logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_
allaxiskickhalf_nocrutch1x_c1_acq1_cont40m_cartfoot_{c1,offctrl}_
cont20m_gate/report.json`; `walk_det_1.png` (ON fall) vs
`walk_det_0.png` (control, stable); RL_LOG 09-08 ~07:1x.

--- prior entry below ---

## 2026-09-08 ~07:1x (refill cycle; no completion assigned, canonical capacity read 8 free slots, backlog empty) — completed the fork (b) n>=3 fresh-init seed cohort: launched the missing matched 40M acquisition pair for seed 11

One plain sentence: seed 7 already had its ON/OFF acquisition pair
running and seed 10 already had its own continuation running, but
seed 11 — the third leg of the fresh-init reproducibility cohort —
still only had its 2M canary, so this cycle closed that gap instead
of inventing new work.

**Capacity double-check (worth recording):** the canonical capacity
read listed `hexapod-mjx-train-0`/`hexapod-mjx-train-4` as free, but
`kubectl exec` + `nvidia-smi` showed both still running the
`artifact_finalizer`/`eval_checkpoint` CPU-side tail (0% GPU
utilization) for the fork (a) `cont20m` ON/OFF pair from the prior
entry — genuinely idle GPU, but a live CPU process mid-publish. Left
both alone (per the "still training" list); treated only
`train-2/5/8/9/10/11` as truly free.

**Launched (both `--init-from-source` off their own CANARY PASS 2M
checkpoints, byte-identical to the already-running `s7-acq1` pair —
same recipe, same gate, only the seed differs):**
- `cartfoot-freshinit-c1-s11-acq1` (train-2, ON — 3 cart_foot box keys)
- `cartfoot-freshinit-offctrl-s11-acq1` (train-8, OFF — matched control)

Both VERIFIED RUNNING with real step progression (7.9M/2.1M at verify
time). Gate: ACQUISITION, >=0.03 m/s median net forward in >=1 of
walk/det,sto with 0 falls in det, read together with the sibling at
the same budget; slip/m vs the matched OFF control is the headline
comparison per the fork (b) design, not a hardening bar. 2
launches/80M steps — this cycle's normal cap. 4 pods (5/9/10/11)
remain genuinely idle; backlog stays empty — no further
non-duplicative walkcurr arm identified beyond the fork (a)/(b) lines
already in flight.

Evidence: `launch_run.py status` before/after; ledger entries for both
new runs; RL_LOG 09-08 ~07:1x.

--- prior entry below ---

## 2026-09-08 ~06:5x (triage cycle) — fork (b) seed-7/seed-11 quad all CANARY PASS - HEALTHY-PARITY (4/4); matched 40M acquisition pair launched for seed 7 fresh-init (ON+OFF, own-checkpoint)

One plain sentence: every arm of the fork (b) fresh-init ignition
question now reads clean (cart_foot cold-starts exactly like
joint-space, both seeds), so the next honest question — does a
FRESH-init cart_foot lineage actually learn to walk, and how slippy
is it vs a FRESH-init (not warm-started-onto-mature) joint-space
sibling at the same budget — is now running.

**Quad verdicts (all this cycle):** `cartfoot-freshinit-offctrl-s7`,
`cartfoot-freshinit-c1-s11`, `cartfoot-freshinit-offctrl-s11` CANARY
PASS - HEALTHY-PARITY (`c1-s7` was independently verdicted, near-
identical text, by a concurrent cycle before I reached it). All four
share the same fingerprint: `rollout/ep_len_mean` rises ~100->~490
ticks over 4 quarters, per-tick `env/reward_walk` RISES the whole
time, `env/v_along_cmd_m_s` crosses zero upward, `env/walk_speed`
holds 0.11-0.15 m/s — identical to the `base-s0`/`base-s1` reference
canaries that established this bar. Frame strips (`walk_sto_2`/
`walk_sto_1`) show real leg lift/place pose change, not statues. No
walking-quality claim at 2M (gate scope): all four still show 0/6
`gait_valid` on `walk/det` with 2-3 sacrificed legs, expected/
non-blocking.

**Refill:** launched the matched 40M acquisition pair off the seed-7
canaries' own checkpoints (`--init-from-source`, VERIFIED RUNNING):
`cartfoot-freshinit-c1-s7-acq1` (train-1, ON) +
`cartfoot-freshinit-offctrl-s7-acq1` (train-3, OFF) — 2 launches/80M
steps, at this cycle's normal cap. This is a same-fresh-init-depth
slip/gait_valid comparison, distinct from the existing mature
`cartfoot-c1-s3`/`offctrl-s3` comparison (which reached maturity via
a long continuation chain, not fresh-init).

**Same-window launch race, self-resolved:** a concurrent cycle
independently launched `cartfoot-freshinit-c1-s7-c1` (train-2) ~3 min
after my `-acq1` launch — same source checkpoint, same steps, same
warm start (framed as a cross-seed replicate against `s10-c1b`
rather than an ON/OFF comparison, but the actual training job was
identical). That cycle detected the collision on its own next status
check and killed its duplicate, keeping my `-acq1` pair as the
surviving arm (RL_LOG 09-08 ~06:5x: "killed the duplicate on
detection ... s7-acq1 is the surviving arm") — confirmed via
`launch_run.py status`: train-2 free, train-1/train-3 running the
`-acq1` pair. No action needed from this entry; noted for the
record.

Evidence: `ops.sh review`/`ops.sh report` for all 4 quad runs;
`logs/experiments/cw-walkscratch-easy0905-cartfoot-freshinit-{c1,
offctrl}-s{7,11}/wandb_history.csv`; RL_LOG 09-08 ~06:4x/~06:5x/~06:6x.

--- prior entry below ---

## 2026-09-08 ~07:0x (operator-kick cycle) — fork (a) closure CORRECTED to intermediate/PARTIAL (gate misread: medians-for-means + duration-confounded reward quarters); the gate's own one-extra-read clause EXECUTED as a final matched +10M pair (cont20m)

One plain sentence: the "ACQ FAIL" that closed the Cartesian
foot-decode continuation at 12M used the wrong statistics — by the
run's own pre-registered gate the result is INTERMEDIATE, and its
"one more read only if reward is RISING" clause applies, so exactly
one final matched +10M pair is now training; whatever it says is
final (no further automatic extensions).

**Scope correction on `cartfoot-c1-cont10m`** (status ACQ FAIL ->
ACQ PARTIAL, original verdict text preserved; operator-directed audit,
fb_20260908T061840_eb16f8 +
`artifacts/rl_watchdog/cartfoot_acquisition_read_20260908/`):
1. The registered gate statistic is MEAN slip, not median. ON/OFF
   mean ratios: 2.418/3.084/2.522/3.097 (walk-det/sto/sj-det/sj-sto)
   — only 2/4 groups exceed 3x, so the FAIL-MECHANISM line (>3x in
   >=3/4) was never crossed; <=1.5x promising unmet either =
   registered in-between band.
2. "Reward never reverses" read raw episode-return quarters while
   ep_len ramped 980->1962 ticks. Duration-normalized
   `optimization/reward_per_tick` RISES near-monotonically
   -0.4413 -> -0.1667 (EMA -0.409 -> -0.274; re-verified from cached
   W&B history this cycle), so the rising-reward escape clause DOES
   apply.
Supporting health: all 4 held-out ON groups improved slip AND
progress 2M->12M (progress .505/.370/.308/.322 -> .710/.535/.636/.505),
19/24 gait-valid, 0 falls; all 8 actor tensors moved (rel L2 .0114);
video strip upright, varied legs, no stable exploit — still visibly
slippy, nobody is calling this good walking yet.

**Final one-extra-read pair (LAUNCHED, both RUNNING-verified with
real step progression):**
- `...cont40m-cartfoot-c1-cont20m` (train-4, from cont10m's OWN 12M
  ckpt, RNG2, identical recipe, 3 cart keys)
- `...cont40m-cartfoot-offctrl-cont20m` (train-0, from offctrl-cont10m's
  OWN ckpt, RNG2, no cart keys)
Pre-registered bounded gate (in both ledger entries): PROMISING =
mean slip <=1.5x control in >=3/4 groups + gait_valid >=18/24 + 0
falls; retrofit FALSIFIED = >3x in >=3/4 or gait_valid <18/24; any
fall/protected-behavior loss blocks promotion; any remaining
intermediate = unresolved-retrofit record and END of automatic
extensions (clause exhausted) — explicitly NOT a universal Cartesian
class closure. Rising reward + stalled held-out slip/progress routes
to the MISALIGNED audit branch, not more same-recipe training.
No new seeds/doses/torque/reward. Fork-(b) fresh-init cohorts
(s7/s10/s11, owners 061618/061641) untouched per operator focus note.
Evidence: corrected ledger entry + W&B `qay6bggy` mirror; launch
verifications this cycle; RL_LOG 09-08 ~07:0x.

--- prior entry below ---

## 2026-09-08 ~06:5x (triage cycle) — s7 ON arm CANARY PASSes (completes the seed7 HEALTHY-PARITY pair); s10 continuation crash root-caused and relaunched; a self-caused duplicate launch caught and killed same cycle

One plain sentence: this cycle's two assigned finished runs were the ON
arm of the seed-7 fresh-init pair (now verdicted, matching its already-
passed OFF control) and a continuation launch that had actually crashed
in under a second on a known tooling gotcha — both are now cleanly
resolved, plus a self-inflicted duplicate launch was caught and killed
before it wasted a training budget.

**`cartfoot-freshinit-c1-s7` verdict (CANARY PASS, HEALTHY-PARITY):**
same ep_len-growth/reward-rising ignition shape as its own OFF control
(`cartfoot-freshinit-offctrl-s7`, already CANARY PASS) — `rollout/
ep_len_mean` 101->488, `env/reward_walk` 0.171->0.248 rising every
quarter, `env/v_along_cmd_m_s` crossing zero upward. Gate: det stuck
(0/6 gait_valid, 3 legs sacrificed, matching the OFF control's own
settled-pose det table) but sto shows real progress at high slip
(same shape as OFF). No cold-start inductive-bias handicap for the
Cartesian foot-target decode; too early for any slip/quality claim.
This completes the seed-7 HEALTHY-PARITY pair (seed-11 pair already
completed ~06:45/06:46 per the entries below).

**`cw-walkscratch-easy0905-base-cartfoot-fresh-s10-c1` verdict (SKIP,
launch-mechanics crash, not a research result):** pod log on
`hexapod-mjx-train-7` shows it died in <1s printing the documented
`--activation-fn only applies to from-scratch/transplant builds`
`SystemExit` (CURRENT_TRUTHS.md: any non-blank `--activation-fn` on a
plain `--init-from` continuation trips this guard) — confirmed via
W&B (`1fk8b959`, state=finished, `_runtime`=1s, zero logged steps).
The parent's own args carry `--activation-fn elu` (correct for its
from-scratch launch) and the continuation cloned it verbatim without
blanking. Relaunched immediately as `-c1b` with `--activation-fn=`
blanked, otherwise identical (40M budget, same PASS-BAND gate) —
VERIFIED RUNNING `hexapod-mjx-train-7`.

**Self-caught duplicate:** also launched a 40M continuation of the
`cartfoot-freshinit-c1-s7` ON arm (`-c1`) to pair with the s10-c1b
relaunch, but a re-check of `launch_run.py status` after the fact
showed the concurrent cycle handling `cartfoot-freshinit-offctrl-s7`
had independently launched `cartfoot-freshinit-c1-s7-acq1` (same
parent, same question) 34s before my respec finished — a race, not a
duplicate name the launcher could catch. Killed my copy immediately
on detection (`hexapod-mjx-train-2` freed, ledger marked KILLED with
the duplicate explanation); `cartfoot-freshinit-c1-s7-acq1` (train-1)
and its own matched `cartfoot-freshinit-offctrl-s7-acq1` (train-3) are
the surviving 40M pair — no information lost, no wasted GPU spend
beyond the ~2s kill latency. Lesson: re-check `launch_run.py status`
between EACH sequential launch in a cycle, not just once at the start.

Evidence: `ops.sh review` both assigned runs; pod log
`/tmp/train_cw-walkscratch-easy0905-base-cartfoot-fresh-s10-c1.log`
on `hexapod-mjx-train-7`; `launch_run.py status` before/after the
kill; RL_LOG 09-08 ~06:5x.

--- prior entry below ---

## 2026-09-08 ~06:4x (triage cycle) — seed3 pair CLOSES (matched control lands in-band, formally confirming the 4-6x slip loss); fork (b) offctrl-s7 mechanism-health canary CANARY PASSes, matching the base-s0/s1 ep_len-artifact pattern

One plain sentence: the two runs assigned this cycle finish the
seed3 cross-seed replication (the control came in clean, so the ON
arm's slip deficit is no longer "not in doubt but unstamped" — it's
formally closed) and confirm the OFF half of the seed7 fresh-init
fork (b) pair ignites exactly like the proven base family.

**`cartfoot-offctrl-s3` verdict (CANARY PASS, matched control):** 0
falls/terminations in 24/24 episodes, gait_valid 22/24 (6/5/5/6),
slip/m median 4.93/4.95/4.98/5.72 — squarely inside the established
5-6/m det band, not regressed at 40M continuation depth. This
completes the seed3 pair: `cartfoot-c1-s3` (ON, already CANARY
PASSed ~06:3x) measured slip/m 20.55/20.57/31.61/27.15 against this
now-confirmed control, i.e. **4.2-6.3x slippier at matched gait_valid
(20/24 vs 22/24)** — the same fingerprint the seed2 pair showed almost
exactly. Cross-seed replication against a matched control is now
**complete twice** (seed2, seed3): cart_foot-space is mechanism-viable
but materially slippier than joint-space, not a seed-lottery artifact
either direction.

**`cartfoot-freshinit-offctrl-s7` verdict (CANARY PASS, mechanism-
health):** rollout/ep_len_mean rises 101->223->353->488 ticks across
the 4 quarters while per-tick `env/reward_walk` RISES 0.167->0.195->
0.216->0.236 and `env/v_along_cmd_m_s` crosses zero (-0.0002->+0.0042
->+0.0069->+0.0089) — the total `ep_rew_mean` decline (-140->-551) is
the SAME ep_len-growth artifact the 09-05 ~08:5x `base-s0`/`base-s1`
canaries showed, not reward regression. `env/walk_speed` holds
0.11-0.14 m/s throughout and the `walk_sto_1` frame strip shows real
leg excursion, not a statue. This is the byte-identical joint-space
(OFF) control for fork (b) seed 7 — it ignites exactly like the
already-proven base family, so seed 7 itself is not unlucky. The
comparative ON-vs-OFF PARITY read for this seed still needs
`cartfoot-freshinit-c1-s7` (still training this cycle, untouched);
next reader pairs them once it finishes. Same open question for the
seed-11 half of the pair (`c1-s11`/`offctrl-s11`, both still
training).

Evidence: `ops.sh review` for both runs this cycle; `logs/ckpt_eval/
cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxiskickhalf_
nocrutch1x_c1_acq1_cont40m_cartfoot_offctrl_s3_gate/report.json`;
`logs/experiments/cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-
s7/wandb_history.csv`; RL_LOG 09-08 ~06:4x.

--- prior entry below ---

## 2026-09-08 ~06:3x (triage cycle) — cartfoot-c1-s3 verdicted (seed3 reproduces the seed2 VIABLE-but-slippy fingerprint almost exactly); fork (b) DESIGNED and LAUNCHED as a matched n=2 fresh-init seed pair (s7, s11), concurrent with another cycle's independent s10 replicate

One plain sentence: the seed-reproducibility question from the prior
entry is answered (this is a real mechanism property, not a seed-
lottery fluke), and fork (b) — the fresh-init test the ~06:2x entry
below flagged as needing a design pass before anyone could launch it
— is now designed, banked and running.

**cartfoot-c1-s3 verdict (CANARY PASS):** 0 falls/terminations across
all 24 episodes, `gait_valid` 20/24 (6/4/4/6 det/sto/sjdet/sjsto) —
clears MECHANISM-VIABLE. slip/m by group 20.55/20.57/31.61/27.15,
essentially the SAME 20-30/m range seed2's `cartfoot-c1` showed
(19.1/25.0/68.4/32.8), both far above the matched joint-space
control's established 5-6/m band. Contact sheet + walk_det frame
strip: all six legs upright, cycling stance/swing, no flag leg. The
matched `offctrl-s3` control was still finalizing on another cycle's
pod at read time (not touched, per this cycle's own "still training"
list) so PROMISING/not isn't formally stamped, but given offctrl
consistently lands at 5-6/m regardless of seed, the 4-6x loss is not
in doubt. Cross-seed replication closes the reproducibility question:
**VIABLE-but-3-10x-slippier is a genuine property of the mechanism,
not an n=1 seed-lottery artifact.**

**Fork (b) design + launch:** the blocker flagged below (naive fresh
pair at the mature `cont40m` multi-axis recipe would conflate "neither
parameterization learns this from scratch" with a mechanism-specific
result, since `cont40m` was itself only ever reached via a long
continuation chain) is resolved by using the ONE recipe in this
campaign actually PROVEN to learn walking from a random policy: the
`easy0905` base pilot (`base-s0..s4`, fixed 0.06 m/s, no heading, no
DR, gamma .995/lam .97, 256,256,128 ELU). Built two byte-identical-
except-seed matched pairs (ON = 3 cart_foot box keys 0.06/0.035/
0.04 m added to the SAME bank-proven decode; OFF = no keys) at
seeds 7 and 11, queued via `backlog add` (new configs, not a respec)
and drained onto free GPU pods (9/11 were idle at read time). All 4
runs (`cartfoot-freshinit-{c1,offctrl}-s{7,11}`) finished their full
2,097,152-step canary within the cycle (~2-3 min each at GPU speed);
ledger reconciled via `checkup --run` + `update --set wandb_id=...`
for each (mechanical status only, no manual edits). W&B:
`7poujbfm`/`xlzhnck1` (s7 on/off), `b3piakh6`/`c2vthugj` (s11 on/off).
Gate (2M MECHANISM-HEALTH CANARY, same bar `base-s0` itself used —
NOT a walking gate): finite losses, real joint/foot excursion beyond
settled stance, reward agrees with the WALKSCRATCH_EASY bank;
no-walk-at-2M is not a failure for either arm (base-s0 itself needed
continuation past 2M to actually walk). Gate evals not yet read this
cycle (just finished; next reader's to triage). A CONCURRENT cycle
independently designed and launched the same question as a single
ON-only arm, different seed (`cw-walkscratch-easy0905-base-cartfoot-
fresh-s10`, W&B pending) — not a duplicate to undo, a welcome 3rd
seed for the same n>=3 discipline this campaign uses elsewhere; left
unverdicted (its owner's line).
Evidence: `ops.sh review` for `cartfoot-c1-s3`; ledger entries for
all 4 new fork-(b) runs; RL_LOG 09-08 ~06:3x.

--- prior entry below ---

## 2026-09-08 ~06:2x (triage cycle) — fork (a), the cartfoot-c1 10M continuation, verdicted CLOSED: slip stays 2.6-3.3x the matched control after 10M more steps, reward never reverses its decline

Triaged the pair the ~06:1x entry below found already RUNNING
(launched by a different cycle) but left unverdicted: both hit
`state=finished` on W&B while the ledger still said RUNNING (pods had
gone fully idle — `launch_run.py status` showed all 12 GPU pods
free); `checkup --run` on each mechanically reconciled the ledger to
FINISHED (no manual status edit) and completed the deferred-artifact
finalize/sync.

- `cartfoot-offctrl-cont10m` (matched control, W&B `x46hb1dy`):
  **PASS**, retains the source band at 10M — gait_valid 22/24 (6/5/5/6
  across walk-det/sto/startjitter-det/sto), 0 falls/terms in 24/24,
  slip/m median 5.09/5.32/5.29/5.77 (the ~5-6/m source band), reward
  rising the whole continuation (quarters 288→847→1503→1771). Valid,
  undrifted comparator.
- `cartfoot-c1-cont10m` (ON, fork (a), W&B `qay6bggy`): **ACQ FAIL**
  against its own pre-registered gate. gait_valid 19/24 (5/4/4/6),
  0 falls/terms in 24/24 — clears the gait/no-fall floor — but
  slip/m median 13.22/17.35/14.11/17.03 is 2.6-3.3x the matched
  control in ALL 4/4 groups (PROMISING needed <=1.5x in >=3/4 groups;
  0/4 clear it). Train reward fell the ENTIRE continuation (quarters
  -150.6 → -397.1 → -521.0 → -576.3): decelerating but never
  reversing, so the gate's own "one more read only if reward is
  RISING" clause (08-21 ruling) does not license a further read. It
  does not literally cross the numeric FAIL-MECHANISM line either
  (only 1/4 groups, not >=3/4, exceed 3x slip; gait_valid stays above
  18/24) — an honest in-between reading, not a clean threshold hit —
  but with no rising-reward escape and slip still 2.6-3.3x worse than
  the matched control after 10M extra steps of the identical retrofit
  recipe, further spend on this exact form is not justified.

**Fork (a) is now CLOSED: the Cartesian-foot-target retrofit recovers
0-fall six-leg walking after action-semantics scramble (mechanism
"works" in the narrow re-acquisition sense) but does not close the
slip gap to the matched joint-decode control even after 10M
additional steps, and the reward signal that would license patience
(08-21) is absent — it degrades throughout.** Per the pre-registered
OPEN FORK, the remaining option is fork (b): a genuinely fresh-init
cart-foot arm vs a fresh-init joint-decode control at equal budget,
so neither parameterization carries this retrofit's warm-start/
scramble handicap. That still needs its own design pass first (the
`cont40m` recipe was itself only ever reached via a long continuation
chain, never trained from scratch directly, so a naive fresh pair at
this exact recipe risks conflating "neither parameterization can
learn this hard task from scratch" with a mechanism-specific result)
— not pre-licensed here, flagged for whichever cycle takes it up next.
The concurrent seed3 replicate pair (`cartfoot-c1-s3`/
`cartfoot-offctrl-s3`) is a different cycle's line; not read or
verdicted here.
Evidence: `ops.sh review` output for both runs this cycle; W&B notes
`qay6bggy`/`x46hb1dy`. RL_LOG 09-08 ~06:2x.

--- prior entry below ---

## 2026-09-08 ~06:1x (triage cycle) — cartfoot pair verdicts confirmed already recorded (no re-triage); launched a second-seed replicate pair (seed3) to test reproducibility, concurrent with another cycle's own fork-(a) 10M continuation

Read `ops.sh review` on both `cartfoot-c1`/`cartfoot-offctrl`: both
ALREADY VERDICTED CANARY PASS by a concurrent cycle (verdict text
matches the ~05:5x entry below exactly) — no new evidence, did not
re-triage. Found a concurrent cycle had ALSO already launched fork
(a) from the open-fork list below: `cartfoot-c1-cont10m` (ON, W&B
`qay6bggy`, RUNNING then FINISHED train-4) + matched
`cartfoot-offctrl-cont10m` (OFF, W&B `x46hb1dy`, train-0) — my own
attempt at the identical experiment (`-acq10m` naming) was correctly
REFUSED by the launcher as a pod double-book; left that pair for its
own owner to triage, not duplicating.

Instead launched the OTHER open, non-duplicate question the ~05:5x
entry's own "OPEN FORK" flagged but left unaddressed: **is the
cartfoot-c1 fingerprint (0-fall re-acquisition, 3-10x worse slip)
seed-reproducible, or an n=1 seed-lottery artifact** (per this
campaign's own n>=3 seed-pass-rate discipline used elsewhere,
e.g. longrun/legdutyratio). Launched a byte-identical seed3 replicate
pair, both warm-started from the SAME `cont40m` checkpoint as
`cartfoot-c1`/`cartfoot-offctrl` (RNG3 instead of RNG2), 2M each:
- `cartfoot-c1-s3` (ON, W&B `axh4szza`, train-1): cart_foot keys
  identical to `cartfoot-c1` (0.06/0.035/0.04 m box).
- `cartfoot-offctrl-s3` (OFF, W&B `a2o71f5o`, train-2): matched
  control, no cart_foot keys.
Both FINISHED full 2,097,152 steps within the cycle (2M trains in
~2-3 min at 12.5-16k fps); gate evals pre-staged for the next reader.
Gate: same MECHANISM-HEALTH CANARY bar as the original pair, read
`cartfoot-c1-s3` against `cartfoot-offctrl-s3` — VIABLE if 0 falls/
gait_valid>=18/24; PROMISING additionally if slip beats offctrl-s3 in
>=3/4 groups; FAIL-MECHANISM if it cannot re-acquire. A launcher
subprocess got SIGTERM'd by my own shell timeout mid-verification on
`cartfoot-offctrl-s3` (`--now` snapshot/sync/verify overran a 180s
wrapper) — training had already completed on-pod by then;
`launch_run.py checkup --run ...` mechanically reconciled the ledger
to FINISHED (no manual status edit), and `update --set wandb_id=...`
backfilled the run id checkup doesn't set. Evidence: this STATUS
entry + W&B ids above; ledger `cw-walkscratch-easy0905-headset-
crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-
cartfoot-{c1,offctrl}-s3`. RL_LOG 09-08 ~06:1x.

Fork (b) (fresh-init competing on equal footing) is NOT launched this
cycle — it needs its own design pass first: the mature `cont40m`
recipe (multi-heading, full DR pack) was itself only ever REACHED via
a long continuation chain, never trained from scratch directly, so a
naive fresh-init pair at this exact recipe risks conflating "neither
parameterization can learn this hard task from scratch" with a
mechanism-specific result — flagged for the next owner, not
pre-registered blind.

--- prior entry below ---

## 2026-09-08 ~05:5x (same cycle; pair triage) — cartfoot pair read: ON re-acquires 0-fall walking through fully reinterpreted actions (VIABLE) but slip is 3-10x the matched control in 4/4 groups — foot-space inductive bias UNSUPPORTED at 2M retrofit depth

Gates landed within the cycle (2M trains in ~2 min at 14.5-17.5k fps).
- `cartfoot-c1` (ON): 19/24 gait_valid (5/4/4/6 across det/sto/sjdet/
  sjsto), ZERO falls/terms in 24/24, upright six-leg stepping on the
  contact sheet — clears its pre-registered MECHANISM-VIABLE bar.
  slip/m 19.1/25.0/68.4/32.8 and progress 0.31-0.51. train
  ep_rew_mean fell monotonically (-61 -> -224) while eval improved to
  0-fall — divergence unresolved at this depth.
- `cartfoot-offctrl` (OFF): 22/24 gv, 0 falls, slip 5.34/5.18/6.27/
  5.90, progress 1.54-1.71 — clean source-band retention, valid
  causal baseline (and live source-lineage reproduction under the new
  default-off code).
PAIRED READ per the pre-registered bars: VIABLE yes, PROMISING no
(slip must beat OFF in >=3/4 groups; it loses 4/4 by 3-10x). The
"Cartesian action space makes low-slip placement easier to learn"
hypothesis is UNSUPPORTED at 2M retrofit depth — but 2M after action-
semantics scramble mostly measures re-acquisition, so this is NOT a
class closure. OPEN FORK for the next owner (not pre-licensed, pick
ONE): (a) +10M ON continuation (duty-charge 10M protocol shape) to
separate re-acquisition transient from asymptotic slip — the 08-21
reward-rising clause does NOT apply (reward was falling), fund only
with an explicit new gate; (b) close the retrofit form and run the
parameterization FRESH-INIT vs a matched fresh-init joint-decode
control at equal budget, where neither arm carries a scramble
handicap. Verdicts on both runs (W&B gzyvhnzt / 8tv5njiz). Reports:
train-4/train-0 `logs/ckpt_eval/..._cartfoot_{c1,offctrl}_gate/`.
RL_LOG 09-08 05:5x.

--- prior entry below ---

## 2026-09-08 ~05:4x (operator-kick cycle; focus note 20260908T042629Z) — BUILT + banked + launched the foot-placement mechanism itself: Cartesian foot-target action decode, matched 2M on/off pair on the exact cont40m lineage/RNG2

One plain sentence: the one structural lever left standing after the
9-arm slip-pricing closure, the DR-band/torsion exonerations and the
clip-controllability falsification — "a genuine foot-placement policy
change" — is now a real, banked, default-off mechanism, and its first
matched 2M on/off pair has already finished training and is awaiting
its gate reads.

MECHANISM (`goal.walk_cart_foot_box_{x,y,z}_m`, all default 0.0 = OFF,
bit-exact legacy): with any key > 0 the SAME 18 actions are decoded
per leg as a Cartesian foot target in the leg-root frame (box around
the source decode's exact a=0 stance-foot point (0.0718, -0.0015,
-0.1357) m) through exact model-derived analytic yaw+planar-2R IK
(FK parity 1.8e-16 m vs MuJoCo sites), then the UNCHANGED SafetyLayer/
servo/reward. Prior-free: kinematic reparameterization only, no
clock/teacher/prior. Code `rl_move/sim/cart_foot_decode.py` +
`joint_task.py` branch; snapshot `b24c2ffa`
(exp/walkcurr-cartfoot-pair-20260908).

CORRECTION CREDIT: my first frame derivation used the zero-pose foot
direction (which carries a 1.5 mm lateral offset) and misread the
resulting 2.08 mm FK error as an "irreducible CAD axis tilt"; root's
copy-only review (`artifacts/rl_watchdog/cart_foot_frame_review_20260908/`)
found the bug, applied the pitch-plane frame fix, tightened the FK bar
to 1e-9 m and replaced my false primitive-family geometric rejection
with a genuine nonparallel-axis guard. Root's GPU/Warp environment
bank (`artifacts/rl_watchdog/cart_foot_gpu_bank_20260908/`, PASS,
cuda:0, real worker `_act_to_q`, exact cont40m recipe + the 3 box
keys, decode parity 0.0 rad under model DR/pool restore, source hashes
== this snapshot) closed the CPU-Warp/runtime item without a training
spend.

BANKS/TESTS: 12/12 mechanism bank (test_cart_foot_decode.py 8 +
root's test_cart_foot_frame.py 4: FK exactness, zero-action parity
~4e-16 rad with the source stance, totality/axis limits, IK
self-consistency <1e-9 m, default-off bit-exactness, runtime/reset +
SafetyLayer slew contract with mechanism ON, determinism, fail-closed
guards). Full walk semantics bank: 353 passed / 35 failed — failure
set verified PRE-EXISTING on clean HEAD (4/4 tail-named failures
reproduce identically on a clean worktree; full two-tree comparison
recorded this cycle), all in retired-mechanism semantics families
untouched by this diff.

BOX SIZING (zero-spend measurement): launch box (0.06, 0.035, 0.04) m
= rounded joint-box foot-space image (x [-0.071,+0.068], y [±0.034],
z [-0.029,+0.052] m) so exploration scale matches the source's own
action box. Corners beyond the yaw cone/annulus project to the
closest reachable point (decode is total).

LAUNCHED (both VERIFIED RUNNING then FINISHED full 2,097,152 steps):
- `...cont40m-cartfoot-c1` (ON, W&B gzyvhnzt, fps 14.5-16k — the ~10%
  host-IK cost): warm-start from the cont40m champion with the new
  action semantics; ep_rew starts scrambled and DECLINES
  (-61 -> -224 over 2M) — mechanism engaged beyond doubt; whether
  this is failure-to-reacquire or length/penalty confounds is the
  GATE's question, not answerable from reward alone (08-21 ruling).
- `...cont40m-cartfoot-offctrl` (OFF control, W&B 8tv5njiz): byte-
  identical, no cart keys; ep_rew 34 -> 388 (normal retention shape).
Gate evals pre-staged by the watcher; read the pair TOGETHER per the
pre-registered gates (viable >= 18/24 gv 0 falls; promising = slip
beats OFF in >=3/4 groups; FAIL-MECHANISM = no re-acquisition with
reward flat). A 2M read is mechanism evidence, not class closure.
Evidence: artifacts/rl_watchdog/walkcurr_cartfoot_20260908/.
RL_LOG 09-08 ~05:4x.

--- prior entry below ---

## 2026-09-08 ~04:30 — action-clip review: target sensitivity measured; dynamic authority remains untested

The six deterministic20s cells of nocrutch1x-c1-acq1-cont40m retain broad
safe-target sensitivity: ±0.05 applied-action changes move95.7% of channels
per sign. Mean saturation is1.091/18 joints per tick. This does not show
actual dynamic foot response or refute an entire learned-residual class.
The specific conditional2M clipping-correction pair remains unjustified.

All78 cfg overrides and all55 common per-episode report fields match the
original gate, including randomization. This is report-summary parity,
not a comparison of recorded original trajectories. The trace hook copies
realized actions and pre-filter state without consuming RNG; the nominal
decoder/slew/limit replica agrees over12,000 recorded ticks.

The original foot-space calculation mixed absolute robot targets with
relative MuJoCo knee coordinates. The repaired probe uses
knee_rel=knee_abs-hip_abs for Jacobian perturbations and target error.
Its version2 output is a nominal kinematic projection-support proxy,
not independently reachable dynamic foot displacement. The original
probe_summary.json is retained as uncorrected historical evidence.
Four independent analytic-Jacobian/frame tests and four trace tests pass.

The original margin denominator was also misstated:37.82% of saturated
samples need an action change>0.05, equivalent to2.293% of all joint/tick
samples. The six-cell raw ANY-joint saturation is57.13%;86.65% is the
median across the earlier full24-cell panel. Pooling these quantities
does not establish transition-specific behavior.

Evidence and limits: artifacts/rl_watchdog/walkcurr_clipprobe_20260908/.
Reuse saved traces for corrected reanalysis; a new simulation gate is
unnecessary for this bookkeeping repair. Separately, cycle20260908T042639
owns a distinct learned foot-placement design and conditional matched
acquisition pair. It must preserve prior-free lineage, reward, plant,
motor/safety contract and original evaluation gates.

The prior torsion dose0.1→0.005m did not improve this checkpoint's slip
under the tested panel. This is dose-specific sensitivity, not measured
calibration or a universal class refutation. The analogous steering dose
reduced yaw magnitude while increasing forward speed; it did not improve
steering authority. Subsequent entries below are historical and must be
read under these corrections.

--- prior entry below ---

## 2026-09-08 ~03:5x (same cycle; refill) — measured the cross-track torsional-friction candidate against walkcurr's OWN closed 9-arm slip floor: REFUTED for straight walking (unlike the turning case)

The 09-07 ~20:3x closure (below) demanded a STRUCTURAL (non-reward)
lever before any 10th slip-pricing design; the top-of-file cross-
track note nominated the todaypolicy traction diagnostic's finding
(mesh foot torsional mu_t=0.1 m ~20x a physical boot estimate) as a
candidate and asked walkcurr to check its own ~5-6/m floor against
it. Built the probe-local tool (`env.foot_friction_torsion`, default
0 = bit-exact off, `sim_env.set_foot_ground_torsion_friction` +
regression test, snapshotted `67ebc152`) and re-ran the EXACT
`crossgrav_medhead_dr_allaxiskickhalf_nocrutch1x_c1_acq1_cont40m`
gate panel/seed/checkpoint with ONLY that one cfg key dosed
0.1->0.005 (physical estimate).

Result: slip/m is FLAT-TO-SLIGHTLY-WORSE in all 4 groups (det
4.98->5.19, sto 5.17->5.41, sj/det 5.10->5.14, sj/sto 5.42->5.93 —
+1% to +9%, none improve), `gait_valid` identical 22/24 with the SAME
2 sacrificed episodes (sto/4 leg2, sj/det/1 leg2), 0 falls/
terminations either way — near-identical episode-by-episode
fingerprint. **The torsional-friction fidelity gap does NOT explain
walkcurr's straight-walk slip floor** (unlike the turning-authority
deficit, where the same dose measurably helped) — refuted as a
structural lever for THIS floor specifically. No canary (negative
diagnostic, not a lever). The 9-arm family's escalation demand still
stands unanswered: remaining candidates (foot-pad geometry, a genuine
foot-placement policy change) are unbuilt/unscoped. Evidence:
`logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_
allaxiskickhalf_nocrutch1x_c1_acq1_cont40m_{gate,torsion005_probe}/
report.json`, W&B `v6wmk0lv`. CURRENT_TRUTHS.md updated same cycle.
RL_LOG 09-08 ~03:5x.

--- prior entry below ---

## 2026-09-08 ~03:3x (triage cycle; assigned `crutchoff-s0-widen8-legdutyratio-offctrl10m`) — s0/RNG2's matched control lands: 2nd independent replication CLOSES the continued-charge study negative on BOTH tested lineages

`offctrl10m` (charge=0, same corrected 2M s0/RNG2
`legdutyratiofresh-guardfix1` source, +10M) landed `gait_valid` 21/24
(det 5/6, sto 6/6, sj/det 6/6, sj/sto 4/6), 0 falls — the EXACT SAME 3
failing episodes/chronic legs as the pre-continuation 2M source
(det/0 leg5, sj/sto ep2 leg5, sj/sto ep3 leg0): flat retention, no new
chronic sacrifice, no regression from withdrawal.

Paired against the matched charge-on sibling `on10m` (same
source/RNG2/panel, only the charge differs): ON is `gait_valid` 22/24
(+1, exactly the det/0 episode) but mean `slip_per_m` is HIGHER for ON
in **all 4 groups** (nominal-det 11.26 vs 10.07, nominal-sto 8.00 vs
7.67, jitter-det 9.87 vs 9.49, jitter-sto 12.84 vs 12.78) and mean
`progress_ratio` is LOWER for ON in 3/4 groups (nominal-det 0.817 vs
0.863, nominal-sto 1.107 vs 1.118, jitter-det 0.995 vs 1.013; only
jitter-sto ticks up, 0.707 vs 0.668). **This is the IDENTICAL shape
already read on the s1/RNG3 pair** (offctrl10m PASS, 02:35 below): a
lone gait_valid flip that is NOT a clean win once slip/progress are
read alongside it.

**Net for the mechanism, across BOTH independently-seeded
replications (s1/RNG3, s0/RNG2)**: `walk_leg_duty_ratio_charge` is
mechanism-HEALTHY (bank-proven, telemetrically live, zero new falls/
chronic legs in 4/4 canaries) but has demonstrated ZERO causal
walking-quality benefit from continuing it past a 2M shared exposure
to 10M depth — in both cases the only apparent gain (a single
gait_valid flip) comes with broad-group slip regression and mostly-
lower progress. Do not fund a 3rd replication or a longer continuation
of this exact recipe on this pretext; if the mechanism is revisited,
it needs either a different dose/target or a different
question (e.g. applied fresh-init instead of retrofit-onto-trained,
already separately tracked as OPEN above) — not more of this cell.
Evidence: `logs/ckpt_eval/cw_walkscratch_crutchoff_s0_widen8_
legdutyratio_{on10m,offctrl10m}_gate/report.json` vs `..._
legdutyratiofresh_guardfix1_gate/report.json` (2M source). W&B
`pyrugqjw`. RL_LOG 09-08 03:33.

--- prior entry below ---

## 2026-09-08 03:31 UTC — contact sensitivity is not measured calibration

Contact-wrench accounting passed the substep angular-momentum closure check.
Opposing yaw moments and contact-couple contributions are measured, but do not
uniquely establish inconsistent commanded stance paths. The original cone
statistic was a planar slide projection. The completed 12-cell rerun preserves
all original behavior and uses valid condim6 elliptic full-cone accounting:
a contact is near the boundary in 48.0-58.5% of slipping-foot samples versus
4.1-8.4% with the planar projection. Mixed sub-boundary/boundary behavior
remains; this does not establish a unique cause. Evidence:
artifacts/rl_watchdog/root_fullcone_20260908/. The isolated torsion dose0.1->0.005 m
reduced scripted arc yaw magnitude9-14%, increased forward speed about17-20%,
and changed straight drift, with zero observed falls in its six cells.
The lower coefficient assumes a uniform-pressure contact patch; it is not
measured calibration, an established physical cap, or proof that the original
coefficient is unphysical. Modified-contact sensitivity is separate from
frozen-plant qualification. No original both-signs/straight-health preflight
passed, so no canary or fleet-model change follows from this evidence.
Continue authorized simulation diagnostics without waiting for an operator
reply on the separate fleet-calibration question.
See artifacts/rl_watchdog/full_cone_review_20260908/CORRECTION.md.

A bounded frozen-checkpoint slip-sensitivity probe can inform contact
calibration; it cannot satisfy qualification under the original plant.

## 2026-09-08 ~03:0x (triage cycle; assigned `crutchoff-s0-widen8-legdutyratio-on10m`) — s0/RNG2 charge-on arm CANARY PASSes its own retention gate (22/24, +1 over the 21/24 source, 0 new falls/chronic legs) — same shape as the s1 twin, causal efficacy still pending its matched control

`on10m` (charge=150, same corrected 2M s0/RNG2
`legdutyratiofresh-guardfix1` source, +10M) landed its 24-episode
det+sto walk/startjitter gate: `gait_valid` 22/24 (det 6/6, sto 6/6,
sj/det 6/6, sj/sto 4/6), 0 falls/terminations in every mode —
flat-or-BETTER than the source's own 21/24 (source's sole det/0
sacrifice [leg5] flips to `gv=True` here; the same 2 startjitter/sto
episodes remain the only fails [leg5 ep2, leg0 ep3] — no NEW chronic
leg). Peer-excluded duty ratio for the formerly-weak legs (0,5)
clears >=0.22 in 23/24 episodes each, unchanged from source.
`ep_rew_mean` falling to -32008 (quarters monotonically more
negative) is fully explained by `rollout/ep_len_mean` rising
108->1235->1999->2000/2048 under a persistent ~0.10-0.15 charge
shortfall that never zeroes (unlike the `assistfade` rung3-s0 sibling,
where the same charge DID decay to ~0) — not behavioral collapse.

This is the SAME shape already read on the s1/RNG3 twin
(`guardfix-acq10m`, PASS): a lone gait_valid flip (+1) with the charge
mechanically engaged and no new chronic sacrifice. **The s1 pair's own
closure (below) found that +1 flip was noise, not a causal win** — ON
had HIGHER `slip_per_m` in all 4 groups and LOWER `progress_ratio` in
3/4 vs its matched OFF control, despite the gait_valid edge. s0's own
matched control (`offctrl10m`) is still mid-gate-eval on train-1
(root-owned by another cycle, not duplicated here) — until it reads,
treat this as RETENTION ONLY, not a second independent efficacy
result; the s1 prior says expect the same "no demonstrated advantage,
possibly net-worse-on-slip" outcome unless offctrl10m's own numbers
say otherwise. Evidence: `logs/ckpt_eval/cw_walkscratch_crutchoff_s0_
widen8_legdutyratio_on10m_gate/report.json` vs `..._legdutyratiofresh_
guardfix1_gate/report.json` (2M source). W&B `tojgpbb4`. RL_LOG 09-08
02:57.

--- prior entry below ---

## 2026-09-08 ~02:35 (triage cycle; assigned `crutchoff-s1-widen8-legdutyratio-offctrl10m`) — matched charge-off control lands: CLOSES the s1/RNG3 continued-charge study, NO demonstrated efficacy for `walk_leg_duty_ratio_charge` past the shared 2M exposure

`offctrl10m` (same corrected 2M s1 source, RNG3, only
`walk_leg_duty_ratio_charge` 150->0) landed its own 24-episode
det+sto walk/startjitter gate: `gait_valid` 21/24 (det 5/6, sto 6/6,
sj/det 6/6, sj/sto 4/6), 0 falls/terminations — the EXACT SAME 3
failing episodes/chronic legs as the pre-continuation 2M source
(det/0 leg5, sj/sto ep2 leg5, sj/sto ep3 leg0): flat retention, no
new chronic sacrifice, no regression from withdrawing the charge.

Comparative read against the matched charge-on sibling
(`guardfix-acq10m`, same source/RNG3/panel, only the charge differs):
ON is `gait_valid` 22/24 (+1, exactly the det/0 episode that stays
failed here) but that is not a clean win. Mean `slip_per_m` is HIGHER
for ON in **all 4** groups (nominal-det 11.34 vs 10.02, nominal-sto
7.60 vs 6.89, jitter-det 9.04 vs 8.65, jitter-sto 12.79 vs 12.18) and
mean `progress_ratio` is LOWER for ON in 3/4 groups (nominal-sto 1.159
vs 1.248, jitter-det 1.064 vs 1.099, jitter-sto 0.691 vs 0.725; only
nominal-det ticks up marginally, 0.898 vs 0.888). The pre-registered
gate credits the continued-charge hypothesis "only if on beats off ...
without command/slip regression" — ON fails that bar (broad slip
regression, mixed progress for a single gait-valid flag). **Verdict:
CANARY PASS (matched-control, health scope) but NO demonstrated
efficacy for continuing the charge past 2M at this 10M depth** — the
21->22 flip reads as noise, not a charge-causal recovery.

**Net for this pair**: the s1/RNG3 continued-charge-vs-withdrawal
study is CLOSED with a negative efficacy result. No further budget
funded from this arm. The independent s0/RNG2 pair (`on10m`/
`offctrl10m`, root-registered per fb_20260908T021004/021655) is the
cross-lineage replication check — both FINISHED training but neither
has synced gate artifacts yet (no `logs/ckpt_eval/..._s0_widen8_
legdutyratio_*` dirs as of this cycle); next reader picks those up
once the watcher stages them, not a fresh launch. Evidence:
`logs/ckpt_eval/cw_walkscratch_crutchoff_s1_widen8_legdutyratio_
offctrl10m_gate/report.json` vs `..._guardfix_acq10m_gate/report.json`
vs `..._legdutyratiofresh_guardfix1_gate/report.json` (2M source).
W&B `0gfv9tv8`. RL_LOG 09-08 02:35.

--- prior entry below ---

## 2026-09-08 ~01:57 (triage cycle; assigned `crutchoff-s1-widen8-legdutyratio-guardfix-acq10m`) — the +10M charge-on acquisition CANARY PASSes its own retention/duration gate; matched charge-off control (`offctrl10m`) evaluating, causal efficacy at 10M depth still pending

`s1-widen8-acq1-legdutyratio-guardfix-acq10m` (charge=150 from the
corrected 2M `legdutyratiofresh-guardfix1` source, RNG3, `--seed 3`,
unchanged 8-way heading/DR/motor contract) landed: held-out 24-episode
det+sto walk/startjitter panel `gait_valid` 22/24 (walk/det 6/6,
walk/sto 6/6, sj/det 6/6, sj/sto 4/6), **0 falls/terminations in every
mode** — flat-or-BETTER than the source's own 21/24 (the source's sole
`det/0` sacrifice, leg5, flips to `gait_valid=True` here; the same 2
`startjitter/sto` episodes — leg5 ep2, leg0 ep3 — remain the only
fails, no NEW chronic leg). Direct per-leg peer-excluded duty-ratio
check: both formerly-weak legs (0, 5) still clear >=0.22 in 23/24
episodes each — same magnitude as the source's 22-23/24, no
regression. `ep_rew_mean` -32103 at 10M (quarters monotonically more
negative) must be interpreted alongside `rollout/ep_len_mean` rising
483->1638->1970->1982 (out of a 2048-step episode cap): longer episodes
can accumulate a larger negative per-tick charge. This alone does not
prove either improvement or collapse; the held-out gait/fall results
provide the behavioral evidence. **Verdict: CANARY PASS (acquisition-duration/
retention scope)** — the charge-on recipe survives a 5x-longer
acquisition with zero new falls and no new chronic sacrifice.

This does NOT by itself prove the charge (vs. duration alone) is the
active ingredient of the +1-episode improvement — that needs the
matched charge=0 control, `offctrl10m` (same 2M source, RNG3, only
`walk_leg_duty_ratio_charge` 150->0), which finished training at
01:55:25 UTC and is evaluating under normal watcher ownership. Next
reader: pull `offctrl10m`'s own gate against this identical panel
before claiming the charge itself (not just continued training) drives
the improvement. Both arms share 2M of prior charge exposure, so this
tests continued charging versus withdrawal, not never-exposed training.
If the control matches or beats 22/24, continued charging has no
demonstrated advantage on that aggregate at this duration; this does
not prove duration is the sole cause. Check paired leg-use, progress
and slip as well. Root registered a second matched +10M pair on the
already-existing s0/RNG2 lineage at 02:10 UTC (feedback
`fb_20260908T021004_7f1d28`), providing an independent bounded comparison
without adding a new seed. SKILLS.md retains the acquisition result.
Evidence: `logs/ckpt_eval/cw_walkscratch_crutchoff_s1_widen8_legdutyratio_
guardfix_acq10m_gate/report.json` vs `..._crutchoff_s1_widen8_acq1_
legdutyratiofresh_guardfix1_gate/report.json`, W&B `xy81bl5d`.

## 2026-09-08 ~01:5x (refill cycle; 11/11 GPU free at start, backlog empty, no completion assigned) — triaged 3 orphaned FINISHED `walk_leg_duty_ratio_charge` guardfix1 canaries no other cycle had claimed: 2 fresh-init CANARY PASS + 1 retrofit CANARY FAIL-MECHANISM (self-corrected from a wrong first read)

Found 3 finished-but-unverdicted canaries with ready gate reports
(`s0-widen8-acq1-legdutyratiofresh-guardfix1`, `s0-widen8-acq1-
legdutyratio1-guardfix1`, `s0-widenbis180-legdutyratiofresh-
guardfix1`) alongside the already-in-flight `s1-widen8-acq1-
legdutyratio-guardfix-acq10m` (+matched `offctrl10m` control, both
owned by a concurrent cycle/root per fb_20260908T013619 — left
untouched). Verdicted all 3:

- **`s0-widen8-acq1-legdutyratiofresh-guardfix1` CANARY PASS**: init
  from the already-trained `s0_acq1`, with headings widened 5->8;
  `gait_valid` 21/24, sacrifice in 3/24 episodes, 0 terminations.
  The 2/24 sacrifice count belonged to the inert predecessor.
  Matches sibling `s1`'s
  independently-recorded PASS.
- **`s0-widenbis180-legdutyratiofresh-guardfix1` CANARY PASS**: init
  from the same `s0_acq1`, with headings widened 5->6; `gait_valid`
  18/24 (exactly clears its own bar), sacrifice in 6/24 episodes.
- **`s0-widen8-acq1-legdutyratio1-guardfix1` CANARY FAIL - MECHANISM**
  (self-corrected mid-cycle): this is a RETROFIT onto the already-
  entrenched 40M widen8-acq1 exploiter. First pass wrongly verdicted
  it PASS ("material improvement") without reading the undosed
  baseline first. Direct episode-by-episode diff against `s0-widen8-
  acq1`'s own undosed gate report shows the same `gait_valid`=20/24
  and the same 4 failing episodes/legs. This does not establish
  identical policies or numerical rollouts. Telemetry confirms the
  charge fires correctly
  (shortfall 0.14-0.17, not the earlier activation-guard bug). 2M
  steps of retrofit produced no improvement in those gate fields on
  an already-entrenched checkpoint — retention, not repair. Corrected
  same cycle (FORCE=1), W&B `nh3lt3o3`.

**Methodological finding, applies to every arm of this mechanism**:
all 4 guardfix1 canaries show `ep_rew_mean` crashing hard through
training (e.g. quarters 31.1->63.4->-903.4->-3589.9), while
`rollout/ep_len_mean` rises (108.7->228->359->488). Longer episodes
can accumulate more negative per-tick charge, so raw episode return
alone cannot identify behavioral collapse or gait improvement.
Inspect normalized reward and held-out gait/fall/progress/slip metrics;
survival duration is not a substitute for those measurements. The
acq10m report subsequently scored 22/24 gait-valid with zero falls.

**Net read**: three corrected 2M canaries PASS their mechanism-health
bars across two training RNGs and two heading envelopes. Causal gait
recovery is not established. Both s0 arms start from `s0_acq1`, already
21/24 on its own 5-way gate, which is not a matched baseline for the
new 8-/6-way tasks. The s1 arm starts from `s1_widen8`, already 21/24
on the same 8-way panel. Their matching inert 2M predecessors scored
22/24, 22/24 and 18/24 versus the corrected 21/24, 21/24 and 18/24;
all had zero terminations. Preserve the health verdicts, but replace
the earlier “first real recovery from a naive init” claim with
activation and short-budget compatibility. See
`artifacts/rl_watchdog/fresh_init_claim_review_20260908.md`.
The retrofit-onto-entrenched question stays OPEN
(1 arm, 2M budget, unchanged — not proof the mechanism can never cure
an entrenched exploiter, just that this one short dose didn't). SKILLS.md
updated. No new GPU launch this cycle: the natural next step (longer
acquisition on the fresh-PASS recipe, matched charge-off control) is
already running (`acq10m`/`offctrl10m`, not mine to duplicate); the
retrofit's own next step (a longer single continuation, or preferring
fresh-init over retrofit) is a call for whoever reads the acq10m/
offctrl10m pair, not a fresh launch here. Evidence: `logs/ckpt_eval/
cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxis_nokick_
crutchoff_{s0,s1}_widen8_acq1_legdutyratiofresh_guardfix1_gate/
report.json`, `..._s0_widenbis180_legdutyratiofresh_guardfix1_gate/
report.json`, `..._s0_widen8_acq1_legdutyratio1_guardfix1_gate/
report.json` vs `..._s0_widen8_acq1_gate/report.json`.

--- prior entry below ---

## 2026-09-08 ~00:4x (same cycle, self-correction) — CORRECTION: all 4 original `walk_leg_duty_ratio_charge` canaries below were silently INERT (activation-guard bug); operator-fixed same cycle; all 4 relaunched as `-guardfix1`

**The bug**: the new `walk_leg_duty_ratio_charge` contact-bookkeeping
block (EMA update) was gated behind the SAME shared activation
condition every other per-leg gate in `sim_env.py`'s step() shares
(`g_gait > 0.0 or g_duty > 0.0 or g_swing > 0.0 or g_dband > 0.0 or
k_drag > 0.0 or k_park > 0.0 or ...`) — but I never added `g_ratio >
0.0` to that list. On the ACTUAL launched recipe (the widen8-acq1/
widenbis180 cfg_set: `k_park_duty=0`, `k_step_event=0`, no other gate
armed) that whole block never ran, so `self._legduty_ratio_ema` never
updated past its `[1.0]*6` seed — the charge computed a shortfall of
0.0 EVERY tick regardless of actual behavior, silently bit-identical
to `walk_leg_duty_ratio_charge=0.0`. My own bank tests never caught
this because `WALK_LEGDUTY_RATIO_OVERRIDES` inherits `WALK_OVERRIDES`,
which already sets `k_step_event=1.0`/`k_drag_loaded=10.0`/
`k_park_duty=1.0` — those kept the shared block alive in every bank
test regardless of my own bug, masking it completely.

**Caught by the operator** (commit `ebad6d0d`, "Activate standalone
leg-duty ratio reward contact tracking", ~15 min after my snapshot
`e24a2ab6`): one-line fix (`or g_dband > 0.0 or g_ratio > 0.0` in
`sim_env.py`) + a new regression test
(`test_walk_leg_duty_ratio_charge_sparse_launch_activation`) that
reproduces the EXACT sparse-activation configuration (every other
gate zeroed) the real launches use and proves the charge now fires
correctly. Pulled + reconfirmed: 16/16 leg_duty_ratio+adjacent bank
tests green. A concurrent orchestrator cycle had already caught this
independently and relaunched `s0-widen8-acq1-legdutyratiofresh` as
`-guardfix1`; verdicted all 4 original bugged runs `CANARY FAIL -
INFRASTRUCTURE` (ledger + W&B notes) and relaunched the remaining 3
(`s1-widen8-acq1-legdutyratiofresh`, `s0-widen8-acq1-legdutyratio1`,
`s0-widenbis180-legdutyratiofresh`) as their own `-guardfix1` twins,
same hypotheses/gates, fixed code. Spot-confirmed the fix engages in
real training: `s0-widen8-acq1-legdutyratiofresh-guardfix1`'s own
`wandb_history.csv` shows `env/reward_walk_leg_duty_ratio` genuinely
non-zero (-18.9, -22.8) with real `walk_leg_duty_ratio_shortfall`
(0.13-0.15) — the charge is live this time. All 4 `-guardfix1` arms
VERIFIED RUNNING/FINISHED as of this entry (2M canaries train fast);
read those, not the original 4, for the mechanism's real first read.

Lesson for the next per-leg reward-shaping mechanism in this file:
the shared activation-guard list at the top of the contact-
bookkeeping block is EASY to forget a new gate's flag from, and the
bank's own inherited `WALK_OVERRIDES` baseline (which already arms
several older gates) will not expose the omission — a sparse/minimal
override dict (every other gate explicitly zeroed, matching the REAL
launch recipe) needs its own dedicated bank test, not just the
standard `WALK_OVERRIDES`-inherited one.

## 2026-09-08 ~00:2x (refill cycle; 11/11 GPU free, backlog empty) — BUILT + BANK-PROVED `reward.walk_leg_duty_ratio_charge`, the "duty-balance reward TARGET" scoped since 09-07 ~23:2x, and launched the first 4-canary test batch

**Plain English**: a brand-new per-leg reward charge that ADDS a
penalty (never multiplies existing walking income, and never ends
the episode) whenever one leg's ground-contact time falls too far
below its five teammates' own average. Built to answer the exact
question every one of the 19 prior mechanisms in this file (11
income-multiplying price gates + 8 hard safety-terminations, all
CLOSED FAIL against the chronic front-pair/middle-pair leg sacrifice)
left open in its own closure note: **can ANY per-tick mechanism flip
a leg-sacrifice cheat's full-episode return below the honest gait's
own return, not just shrink it toward zero?** Answered empirically
this cycle, decisively YES for this design.

**Design**: per-leg EMA of ground-contact duty (own independent
state, `_legduty_ratio_ema`, does not touch the termination feature's
own `_walk_legduty_ema`); each tick, `ratio_i = duty_ema_i /
peer-excluded-mean(other 5 legs)`; charge = `-walk_leg_duty_ratio_
charge * max(0, target - min_i(ratio_i))`, added directly to reward
(never multiplies `r_walk`/`r_prog`/`r_cmd_track`, so it cannot be
"simply outbid" by a fatter income term the way every closed
multiplicative gate could be) with no episode cutoff (so there is
nothing to "pay off as ambient cost" the way the termination class
was). Default `target=0.30` is the 09-07 ~23:4x calibration's own
passing-population p10 worst-leg ratio. Default 0 = off, bit-exact
(verified: the ONLY reward-path change when off is adding a `r_ratio`
local initialized to `0.0`, which is a numerically exact no-op).

**Bank proof** (`test_task_semantics.py`, 9 new tests + the 5 adjacent
legduty tests re-confirmed green, 14/14 total): using the SAME
scripted honest-six-leg/flag-leg actors every prior mechanism in this
file was validated against, PLUS a new SOFT/MARGINAL starvation actor
(`_gait_gate_walk_rollout_softleg`, periodic ~10% duty taps instead of
a permanent 0%-duty raise — the shape real 40M-trained checkpoints
actually show, not just the hard synthetic cheat every prior bank only
ever tested). At a modest dose (150.0): the honest gait's return is
BIT-EXACT untouched (its own worst-leg ratio never dips below 0.30);
the hard flag-leg cheat's return flips from 1323.9 (undosed, already
below the honest gait's 3113.8) to -14785.3 (dosed) — net NEGATIVE,
decisively below the honest gait's own dosed return (3113.8,
unchanged); the soft 10%-duty starvation cheat does the same
(1261.1 -> -47064.4). Confirmed the ordering-flip holds across a
50x-3000x dose sweep (return scales roughly linearly with dose, sign
never flips back). Direct calibration check: a leg at the flagged-
sacrifice population's own p90 ratio (0.179) reads a real shortfall;
a leg at the passing population's own p10 (0.302) reads ~zero — the
shipped default sits exactly where the data says it should.

**Launched** (all VERIFIED RUNNING, 2M canaries, phase=canary, single
new lever vs each source's own already-FAIL baseline):
1. `s0-widen8-acq1-legdutyratiofresh` (train-2, FINISHED already —
   fresh provenance, same recipe as the undosed `widen8-acq1` FAIL,
   charge from step 0)
2. `s1-widen8-acq1-legdutyratiofresh` (train-0, RUNNING — 2nd-seed
   replication)
3. `s0-widen8-acq1-legdutyratio1` (train-2, RUNNING —
   `--init-from-source` RETROFIT onto the actual entrenched 40M
   widen8-acq1 checkpoint, tests repair-of-baked-in-habit)
4. `s0-widenbis180-legdutyratiofresh` (train-1 — fresh provenance on
   the milder 6-way-heading lineage)

Pre-registered gate (all 4): PASS if the chronic leg's held-out
duty_cycle recovers to a genuinely-used level (peer-relative ratio
>=0.22) in the majority of episodes and `gait_valid` materially
improves (>=18/24, the pre-widen8 clean band) with 0 new falls;
CONTINUE per the 08-21 ruling if reward+gait_valid are both trending
up but short at 2M (fund a longer acquisition, not a new variant);
FAIL if the same sacrifice persists regardless of whether the charge
is measurably firing. Read these before funding any further
`walk_leg_duty_ratio_charge` dose/lineage variant.

Full board re-confirmed unchanged otherwise: joystick/amp DONE, cpg
closed, standwalk/assistfade closed pending their own unscoped
mechanism designs (this IS that design, for walkcurr's instance of
the same shared per-leg-utilization gap), todaypolicy delivered/
Codex-owned turn-authority repair in progress. Snapshot `e24a2ab6`
pushed (`rl_move/sim/walk_task.py`, `rl_move/tests/
test_task_semantics.py`). `CYCLE_WORKED` touched (new mechanism
built+bank-proved+snapshotted, 4 canaries launched — not a re-verify
no-op).

Evidence: `rl_move/sim/walk_task.py` (search
`walk_leg_duty_ratio`), `rl_move/tests/test_task_semantics.py`
(`test_walk_leg_duty_ratio_charge_*`, `test_walk_leg_duty_ratio_
charge_matches_calibration_threshold`), `ops.sh review
cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-
crutchoff-{s0,s1}-widen8-acq1-legdutyratiofresh` /
`...-s0-widen8-acq1-legdutyratio1` /
`...-s0-widenbis180-legdutyratiofresh`, W&B `x6d04iaz`/`xvrxw7t3`.

> Older journal (2026-09-01..09-07: legduty/transwin/widen8/DR-hardening
> waves, QUEUE AIM history) preserved VERBATIM in
> `archive/walkcurr_STATUS_journal_2026-09-07_trim.md`; pre-09-01 in the
> 08-30/08-31 archives cited below. Don't act on archived Next items.

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
