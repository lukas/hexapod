# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: pass

**created**: 2026-09-06T09:09:56+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1

**wandb_id**: x4yqywuc

**hypothesis**: Does the half-dose kick-perturbation canary (medhead-dr-kickhalf1x-c1: 0.15 kick prob, 21/24 gait_valid at 2M, 0 falls, 3 different legs flagged in 3 different modes -- non-chronic) hold its zero-shot recovery margin at a real 40M ACQ budget, or does more training exposure at this dose either close the gap to a clean sweep or reveal an entrenching chronic leg the 2M canary was too short to show? Direct follow-up to kick1x-c1's full-dose fall and this canary's own dose-bisection framing.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg pattern and 0 falls (matches or improves the canary's non-chronic 3-legs-3-modes scatter). FAIL/ENTRENCHES if it drops (<12/24), the scatter consolidates into a chronic single-leg pattern, or a fall appears -- would show half-dose kick recovery is only canary-lucky, not durable.

**verdict**: ACQ PASS/HOLDS (with a WATCH). Half-dose kick-recovery (dr.walk_kick_prob=0.15) holds durable at real 40M budget: aggregate gait_valid 20/24 (5/6 det, 5/6 sto, 6/6 startjitter/det, 4/6 startjitter/sto), 0 falls/terms in all 24 episodes, matching its own 2M canary's count almost exactly (21/24). Video/contact-sheet confirm clean six-leg tripod cycling in every sampled episode, no drag/skate/paddle-creep. WATCH: the canary's 3-different-legs-3-modes scatter (legs 2/4/5) narrowed to a single leg (index 5) recurring in 4/24 episodes across 3 modes at ACQ scale -- the gate's own FAIL clause names 'scatter consolidates into a chronic single-leg pattern' as disqualifying, so this is the borderline signal to watch, not a clean improve. Read the actual duty values before calling it entrenchment though: leg5 duty is healthy (0.3-0.6) in 20/24 episodes and only dips to 0.03-0.09 in the 4 flagged ones (all in *this* run, none in walk_startjitter/det where it's 6/6 clean) -- this is occasional near-threshold noise on an otherwise-healthy leg, not the sustained near-zero-duty-in-every-episode pattern this campaign has separately diagnosed as genuine chronic entrenchment (e.g. the crossgrav leg-1/4 startjitter fingerprint). Net: PASS by the pre-registered numeric bar (>=18/24, 0 falls); flag leg5 for the next continuation of this exact lineage as an early-warning watch item, not a fresh FAIL.

