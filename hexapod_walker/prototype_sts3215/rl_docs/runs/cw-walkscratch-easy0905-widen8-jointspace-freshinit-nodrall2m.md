# cw-walkscratch-easy0905-widen8-jointspace-freshinit-nodrall2m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T15:39:40+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl

**wandb_id**: p5bj0esp

**hypothesis**: Plain English: with the entire dose-ladder (1.0x/0.5x/0.25x uniform magnitude), both single-axis knockouts (bad_start/fault/push), the discrete-vs-continuous group split, AND the staged 0->1 DR ramp all now CLOSED FAIL on this exact widen8 8-way-heading fresh-init composite, does the composite ignite AT ALL with essentially NO domain randomization (true environmental zero -- every dr.* axis at its scaled(0) nominal value, i.e. the calibrated nominal sim; sensor-noise floors unaffected per the mechanism's own design), or does it still fail to walk even in the easiest possible physics? Uses the already-built+tested env.dr_stage_ramp_steps mechanism (commit bc8643f2, 8/8 unit-tested, already CANARY-PASSed for mechanism health on this family) pinned at a ramp span (5e10 steps) far longer than this run's 2M budget so frac stays ~4e-5 (effectively 0) the entire run -- cleaner and less error-prone than hand-copying 25 scaled cfg values. If it STILL fails to ignite, DR breadth is conclusively ruled out as the blocker (even literally near-zero DR fails identically), pointing at the composite/reward/action-box/8-way-heading task design itself as the true obstacle -- not more DR tuning of any kind. If it DOES ignite, that reopens the staged-ramp idea with a much longer/gentler ramp than the already-tried 20M full-budget-fraction one, or points to a much-lower-than-0.25x floor as the actual minimum effective dose.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY: PASS (ignition confirmed possible) if walk/det gait_valid majority (>=4/6) AND net forward speed median >=0.03 m/s AND 0 falls -- this does NOT close the walkcurr DONE gate (near-zero DR is not a deployable recipe) but it reopens a milder-dose/longer-ramp branch. FAIL (still flat/thrashing, near-zero net displacement, matching the closed fingerprint) means the composite itself (reward shape / action box / 8-way heading / termination penalties) cannot ignite from fresh random init regardless of DR -- closes the ENTIRE DR-breadth investigation on this composite and forces a genuinely different lever (composite simplification -- e.g. narrower heading set or looser action box for fresh-init specifically -- or a structurally new mechanism), not any further DR axis/dose/stage variant.

