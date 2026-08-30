# cw-walk-allheading-mlp-singleframe-acq1-stdanneal

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T05:14:22+00:00

**pod**: hexapod-mjx-train-0

**steps**: 15000000

**parent**: cw-walk-allheading-mlp-singleframe-acq1

**wandb_id**: m9x82ujn

**hypothesis**: Plain English: does annealing the runaway action-noise (train/std) down to a fixed target repair this checkpoint's collapsed stochastic-mode walking and crashed late-training reward, the same way it already fixed the two sibling hist64 mlp/tf all-heading acq1 checkpoints? Single new lever vs the PARTIAL-verdicted source: --log-std-final -3.0 --log-std-anneal-frac 1.0 (anneal starts from the checkpoint's own current mean log_std ~1.62/std 5.05, per the tool's documented warm-start behavior), everything else byte-identical, +15M steps off the finished 40M checkpoint. This is the 3rd confirmed instance of the identical bug on this recipe family (mlp/tf all-heading acq1 already fixed this way) so no new bank is owed -- it is a mechanism repair, not a reward-design change.

**gate**: Fresh DR-0 gate (n=6 det+sto x walk/walk_startjitter, same panel as the source): PASS = sto-mode recovers toward the det numbers (prog med >=0.15, slip med <=6.0, gait_valid>=5/6, no new sacrificed leg) WITHOUT eroding det (prog med stays >=0.35, slip med stays <=3.0, gait_valid 6/6, zero terminations) AND train/std actually lands near the -3.0 target (not still climbing). If PASS: run eval_cmd_suite balanced 8-heading panel (completion >=0.19 every heading, zero falls) then the formal 60s eval_joystick_gate stress_mix script; if that also passes, immediately retry distill_gru.py --dual (single-frame both sides) as the zero-code-change smoke test. FAIL (sto still collapsed, or det erodes) means the anneal target/start needs retuning before any further single-frame walk-source funding.

