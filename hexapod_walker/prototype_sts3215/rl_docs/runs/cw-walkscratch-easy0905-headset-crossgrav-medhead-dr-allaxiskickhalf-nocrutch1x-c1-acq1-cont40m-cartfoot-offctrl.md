# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-offctrl

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T05:36:00+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: 8tv5njiz

**hypothesis**: Plain English: matched zero/off control for cartfoot-c1 -- the byte-identical +2M continuation of the cont40m champion with NO cart keys (source recipe, decode, RNG2 all unchanged), measuring what 2M of ordinary extra training does to gait/slip so the cartfoot arm's read is causal rather than 'more training helped'. Also re-verifies source-lineage reproduction under snapshot b24c2ffa's new default-off code path (keys absent = bit-exact legacy decode, enforced by test_cart_foot_decode.py::test_default_off_bit_exact).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Standard 24-ep walk/walk_startjitter det+sto gate: PASS = retention of the source's fingerprint (0 falls/terminations, gait_valid in the source's 21-24/24 band, slip/m in the 5-6/m det band, no new chronic single-leg sacrifice). Serves as the comparison baseline for cartfoot-c1's slip/gait read; if THIS control itself regresses, read the pair as inconclusive rather than crediting/blaming the mechanism.

**verdict**: CANARY PASS (matched zero/off control, retention verified): byte-identical +2M continuation of the cont40m champion under snapshot b24c2ffa's new default-off code path lands squarely in the source band -- 22/24 gait_valid (det 6/6, sto 5/6 [sac leg2 x1], sj/det 5/6 [sac leg2 x1], sj/sto 6/6), 0 falls/terminations, slip/m 5.34/5.18/6.27/5.90, progress 1.54-1.71 -- no new chronic single-leg sacrifice, source-lineage reproduction confirmed (keys absent = bit-exact legacy decode, also test-enforced). Serves as the causal baseline for the cartfoot-c1 read: at equal +2M the ON arm's slip is 3-10x worse in all 4 groups, so the foot-space parameterization gets no slip credit at this depth. Evidence: logs/ckpt_eval/..._cartfoot_offctrl_gate/report.json (train-0), W&B 8tv5njiz.

