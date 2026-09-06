# cw-robotwalk-stride-20260906-anchorsoft2x

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T20:32:41+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-robotwalk-stride-20260906

**wandb_id**: 0q2s6rbo

**hypothesis**: Plain English: fully removing the imitation anchor (coef 3.0->0.0, arm cw-robotwalk-stride-20260906) destroyed the gait (rigid tripod lock, legs 1/3/5 permanently planted, near-zero forward travel, 4/24 falls) instead of freeing up stride. That FAIL verdict names the untried repair: a SOFTER anchor reduction (partial coef), not another zero-coef repeat or a straight jump to a from-scratch cadence/CPG redesign. This is the 2nd point of a 2-arm dose bracket (sibling: anchorsoft1x at coef=1.0): tests coef=1.5 (half of Candidate B's full 3.0), warm from the SAME Candidate B checkpoint (never the destroyed stride run's own end), everything else byte-identical to the failed arm (log-std reopen/anneal, mesh/100Hz, 0.08 m/s fixed command, safety limits). Prediction-if-true: gait stays healthy (no leg pinned near duty 0 or 1), 0 falls, slip/m<=2.9, det h000 prog_m at/above Candidate B's 0.31-0.33 m/12s band. Prediction-if-false: same rigid duty-lock/fall fingerprint even at half anchor strength (points at the log-std reopening as a confound, not anchor dose), or clean-but-flat progress (anchor dose isn't the stride lever at all). Strongest alternative: same log-std-reopen confound named in the anchorsoft1x hypothesis.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M, mechanism-health only). Fresh own-pod det+sto walk gate (n>=24, DR-0, same cmdsuite/joygate as Candidate B/arm A). PASS-worth-an-8M-ACQ: no chronic duty-lock fingerprint, 0 falls, slip/m<=2.9, det h000 prog_m not worse than Candidate B's 0.31-0.33 m/12s baseline. FAIL-STILL-COLLAPSES if the arm A tripod-lock/fall pattern reappears even at coef=1.5 -- do not try a 3rd coef value; isolate the log-std-reopen confound instead. FAIL-NO-GAIN if gait stays clean/safe but prog_m sits flat at Candidate B's band -- read together with the anchorsoft1x (coef=1.0) sibling: if BOTH read FAIL-NO-GAIN, the anchor-dose axis is closed for stride and the next lever is the hypothesis's own named alternative (cadence/CPG harvest), not another dose point.

