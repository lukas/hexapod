# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf-notorquecrutch-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T09:51:48+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1

**hypothesis**: Plain English: do the campaign's two riskiest realism axes -- kick-safe dose (walk_kick_prob=0.15, already individually clean) and full torque-crutch removal (torque_scale 1.0 vs the idealized 3x, already individually clean at canary+ACQ for 1.5x/2x and awaiting its own 1x ACQ gate) -- still compose cleanly TOGETHER, isolated from the other ~28 benign axes already confirmed composable via alldrconf1x-c1? This is a sharper 2-axis interaction probe than jumping straight to the full ~30-axis composite (allaxis1x-c1 FAILED there, but confounded by full-dose kick at 0.3, not 0.15), and gives an early read on the torque-crutch x kick interaction while the single-axis torquefade1x-c1-acq1 gate is still computing.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if the full 4-panel harness reaches 0 falls with aggregate gait_valid majority (>=18/24) and no new chronic single-leg sacrifice -- these two aggressive axes don't interact badly. FAIL/INFORMATIVE-NEGATIVE if a fall or gait_valid collapse appears -- pins the interaction specifically to kick x no-crutch, not the full composite's other ~28 axes.

**verdict**: CANARY PASS/INFORMATIVE-POSITIVE (mechanism-health): the campaign's two riskiest realism axes -- kick at the proven-safe half dose (walk_kick_prob=0.15) AND full torque-crutch removal (torque_scale 1.0, the real unassisted servo spec) -- compose cleanly together in isolation from the other ~28 axes. Aggregate gait_valid 22/24 (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 5/6, walk_startjitter/sto 6/6), 0 falls/terms. 2 non-chronic singleton flags on DIFFERENT legs (leg2 in walk/det, leg4 in walk_startjitter/det) -- no chronic single-leg pattern. slip/m runs elevated (4.9-8.9, consistent with the no-crutch penalty already seen standalone on torquefade1x-c1-acq1) but gait validity untouched. Contact sheet confirms clean upright six-leg cycling with genuine forward translation. Found as a genuine orphan: training + gate finished (W&B state=finished, 2.1M steps) but the ledger was stuck at stale INTENT (never reached RUNNING/VERIFIED, the launch-verification step apparently raced/dropped) and was never verdicted. Why: matches the gate's own pre-registered PASS branch. What's next: this 2-axis isolated probe independently corroborates the full-composite finding from allaxiskickhalf-nocrutch1x-c1 (also CANARY PASS) that kick-safe + no-crutch do not destabilize each other or the broader composite -- both composite ACQ recipes (allaxis-nokick-c1-acq1 and allaxiskickhalf-nocrutch1x-c1-acq1) are now the live frontier reads; no further isolated 2-axis probes are needed on this exact pairing.

**refused_reason**: hexapod-mjx-train-0 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf-notorquecrutch-c1 — GPU pods host exactly one run; pick a free GPU pod.

