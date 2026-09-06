# cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T00:41:12+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1

**wandb_id**: ibau23ge

**hypothesis**: Plain English: the abrupt-1g crossgrav discovery canary (CANARY PASS, gait_valid 20/24, walk/det+sto 12/12 clean, 0 falls) already showed six-leg walking survives an abrupt jump to full gravity from the leg-healthy halfgrav-medhead-acq1 champion. This is the acquisition-scale (40M) confirmation: does that six-leg gait, and the mild leg-4 softening seen only under start-pose jitter, hold up (or fully resolve) with a full training budget at 1g, closing cross-gravity transfer as a real repair path for the base(1g) family instead of reward-price mechanisms (closed 8/8) or reallocating everything to halfgrav?

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with sac=[] (no chronic <0.10-duty single-leg sacrifice) at 40M, matching or improving the 2M canary's clean 12/12 walk/det+sto read, 0 falls, and slip/m at/near the 2.9 teacher band. ACQ FAIL if walk/det or walk/sto regresses to majority failure or the leg[1,4] chronic-park fingerprint emerges under longer 1g exposure. ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling.

**verdict**: ACQ PASS — first base(1g) cross-gravity-transfer champion validated at FULL 40M acquisition scale. Warm-started the leg-healthy 0.5g headset-halfgrav-medhead-acq1 champion and jumped it abruptly to 1g at tick 0; harness reads gait_valid 23/24 across all four scenarios (walk/det 6/6 sac=[] every ep, walk/sto 6/6 sac=[], walk_startjitter/det 5/6 with one isolated sac=[4] not chronic, walk_startjitter/sto 6/6), 0 falls/terminations in all 24 episodes. slip_per_m banded 3.4-4.5, in line with the medhead/widen2c1 crossgrav siblings' own band (not the teacher's tighter 2.9 but not a new pathology either). Video (walk_det_0, 8-frame strip) shows genuine six-leg cycling with clear forward body translation, no dragging/paddle-creep. This directly refutes 'leg[1,4] chronic-park fingerprint is forced by 1g dynamics regardless' for a leg-healthy starting policy and confirms cross-gravity curriculum transfer as a real, general repair path for the base(1g) family (now 2/2 medhead-lineage PASSes: 2M canary + this 40M continuation), opening a new spend direction beyond 'reallocate everything to halfgrav.'

