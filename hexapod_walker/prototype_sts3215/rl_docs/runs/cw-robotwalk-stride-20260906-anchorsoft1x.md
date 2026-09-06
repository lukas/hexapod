# cw-robotwalk-stride-20260906-anchorsoft1x

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-06T20:29:21+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-robotwalk-stride-20260906

**wandb_id**: xswk9620

**hypothesis**: Plain English: fully removing the imitation anchor (coef 3.0->0.0, arm cw-robotwalk-stride-20260906) did not free up stride -- it destroyed the gait outright (rigid tripod lock, legs 1/3/5 permanently planted at duty=1.0, near-zero forward travel, 4/24 falls). That FAIL verdict's own text names the untried repair: a SOFTER anchor reduction (partial coef, not exactly 0), not a repeat of the same ablation or a jump to a from-scratch cadence/CPG redesign. This arm tests coef=1.0 (1/3 of Candidate B's full 3.0), warm from the SAME Candidate B checkpoint (never from the destroyed stride run's own end), everything else byte-identical to the failed arm (log-std reopen/anneal, mesh/100Hz, 0.08 m/s fixed command, safety limits). Prediction-if-true: gait stays healthy (no leg pinned near duty 0 or 1 across most episodes), 0 falls, slip/m<=2.9, and det h000 prog_m is at or above Candidate B's own 0.31-0.33 m/12s band -- meaning a nonzero anchor floor is enough to keep coordinated six-leg timing while still measurably loosening the teacher's stride ceiling. Prediction-if-false: the same rigid duty-lock/fall fingerprint reappears even with 1/3 of the anchor still active (implicating the log-std reopening or another confound as the real destabilizer, not anchor dose per se), or gait stays clean but progress is flat at Candidate B's exact band (closing the anchor-dose axis entirely -- any coef between 0 and 3 just reproduces Candidate B). Strongest alternative: the log-std reopening (-3.0 warm-override, re-annealed to -4.0) rather than the anchor removal is what destabilized the original arm; if this arm ALSO collapses identically, that confound becomes the next thing to isolate before blaming anchor dose again.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M, mechanism-health only -- do not judge skill acquisition or clone to 8M without a clean read first). Fresh own-pod det+sto walk gate (n>=24, DR-0, same cmdsuite/joygate as Candidate B/arm A). PASS-worth-an-8M-ACQ: no chronic single-or-multi-leg duty-lock fingerprint (no leg pinned <=0.06 or >=0.94 duty across most episodes), 0 falls, slip/m<=2.9, det h000 prog_m not worse than Candidate B's 0.31-0.33 m/12s baseline (ideally higher, closer to the un-met 0.40 target). FAIL-STILL-COLLAPSES if the same rigid tripod-lock / fall pattern from arm A's coef=0.0 reappears at coef=1.0 -- do not try yet another coef value next; instead isolate the log-std-reopen confound (rerun at Candidate B's original final log-std with the anchor still off) before touching anchor dose again. FAIL-NO-GAIN if gait stays clean and safe but prog_m sits flat at Candidate B's exact band (no measurable stride gain from loosening the anchor at this dose) -- if the sibling anchorsoft2x (coef=1.5) arm reads the same, this closes the anchor-dose axis for stride and the next lever is the hypothesis's own named alternative (a faster motion source / cadence-CPG harvest), not another dose point.

**verdict**: CANARY PASS: softened anchor (bc_anchor_coef=1.0, 1/3 of Candidate B's 3.0) does NOT reproduce arm A's coef=0.0 tripod-lock collapse. Fresh own-pod gate (n=24, DR-0, det+sto x walk/walk_startjitter): 0 falls, 0 sacrificed legs, gait_valid 24/24, no duty-lock fingerprint (duty_cycle ~0.56-0.62 per leg every episode, no leg pinned <0.08 or >0.92), slip/m 2.07-2.32 (all under the 2.9 cap). Progress vs Candidate B's own same-4-mode baseline (walk/det 0.314, walk/sto 0.180, walk_startjitter/det 0.234, walk_startjitter/sto 0.296 m/12s): this arm reads 0.343(+9%), 0.220(+22%), 0.224(-4%), 0.326(+10%) -- a consistent same-direction uptick in 3/4 modes, not noise-level wiggle. Clears PASS-worth-an-8M-ACQ (prog_m at/above the 0.31-0.33 band on det h000 AND generalizes across modes). Not FAIL-NO-GAIN (that required flat-at-band on all cells). Next: continue this lineage (warm from THIS run's own checkpoint, not Candidate B) to the full 8M ACQ budget.

