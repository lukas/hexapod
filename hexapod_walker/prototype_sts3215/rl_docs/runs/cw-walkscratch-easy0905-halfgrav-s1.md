# cw-walkscratch-easy0905-halfgrav-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T09:48:06+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-halfgrav-s0

**wandb_id**: x5jft1sp

**hypothesis**: Plain English: independent seed 1 of the half-gravity family, seed-MATCHED to base-s1 for the paired 1g-vs-0.5g comparison (operator 09-05 matched-seed directive). From-scratch 40M, identical to halfgrav-s0 except --seed 1.

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family 2M CANARY PASS; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

**verdict**: ACQ PASS — halfgrav family now 3/3 clean at 40M from scratch (joins s2/s3). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_halfgrav_s1_gate/report.json — 0/24 terminations across all 4 eval scenarios (walk/sto x det/startjitter), gait_valid 6/6 every scenario, fwd_dist_m median 2.82-4.24m per 20s episode (0.14-0.21 m/s net, well above the 0.03 m/s bar), all 6 legs' duty_cycle 0.16-0.33 (none stuck/sacrificed), height_err_end_mm 9.9-15.4 (no belly drag), roll_class recovered/leaning only (roll_peak 15-18deg, well under the 30deg trip bar). slip_per_m 1.53-2.15, inside the joystick teacher's <=2.9 band and tighter than the base family's 2.6-3.4. Video (walk_det_0) confirms upright six-leg cycling with real net translation, no drag/skate collapse. Note: this run's post-training gate eval was orphaned by a prestage race (its pod hexapod-mjx-train-11 was reassigned to sde-s2-c2 before the eval finished; original eval process silently died after ~34min stuck, ledger pod field was stale) — fixed by pointing the ledger pod field at a free pod (train-0) via launch_run.py update --set and re-running ops.sh podeval there; ran clean in ~3min. Why: matches base/halfgrav 2x2-grid confirmation already logged in STATUS.md — gravity does not look like the deciding lever, this is the 3rd confirming halfgrav seed. What's next: per STATUS's own 09-05 ~10:5x note, no further fixed-forward seeds/budget for base/halfgrav — the remaining acquisition gap is heading generalization, which needs its own test_task_semantics.py ranking bank before any launch.

