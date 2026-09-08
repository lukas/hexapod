# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1-cont20m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL (MISALIGNED) - clause exhausted, fork (a) CLOSED

**created**: 2026-09-08T06:41:27+00:00

**pod**: hexapod-mjx-train-4

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1-cont10m

**wandb_id**: xcn1obp9

**hypothesis**: Plain English: the corrected 12M read of the Cartesian foot-decode retrofit landed in its registered INTERMEDIATE band (ON/OFF mean-slip ratios 2.42/3.08/2.52/3.10 — neither <=1.5x promising nor >3x-in-3/4 failure), with all four held-out groups improving slip AND progress from 2M->12M and duration-normalized per-tick reward rising -0.44->-0.17; this run executes the gate's own one-extra-read clause: does slip keep converging toward the joint-decode control band with exactly 10M more steps, or is ~2.5-3x the control this parameterization's asymptote? Exact continuation of cartfoot-c1-cont10m from its OWN 12M checkpoint, RNG2, identical PPO/physics/reward/noise/motor cfg; only the 3 goal.walk_cart_foot_box_* keys differ from the matched control.

**gate**: FINAL one-extra-read (clause exhausted after this — no further automatic extensions): 24-ep walk/walk_startjitter det+sto exact gate at 22M cumulative vs matched cartfoot-offctrl-cont20m at equal depth, arithmetic MEAN slip_per_m per group. PROMISING = mean slip <=1.5x control in >=3/4 groups AND gait_valid >=18/24 AND 0 falls. FALSIFIES the retrofit = >3x control in >=3/4 groups OR gait_valid <18/24; any new fall or protected-behavior loss also blocks promotion and further continuation. Any remaining intermediate result = record unresolved-retrofit outcome and STOP automatic extensions — NOT a universal Cartesian class closure. If per-tick reward rises but held-out slip/progress stalls or worsens, route to the MISALIGNED audit branch instead of more same-recipe training. No new seeds, doses, torque, or reward changes.

**verdict**: FINAL one-extra-read (clause exhausted, no further extensions per its own gate). Against the confirmed-retained control (cartfoot-offctrl-cont20m, PASS, 5.4-6.2/m): this ON arm's mean slip/m by group is 11.18/10.21/8.90/11.91, i.e. 2.07x/1.89x/1.45x/2.11x the control -- 3/4 groups exceed the 1.5x PROMISING bar (never reached >3x FALSIFY-MECHANISM either), an honest slip intermediate same as the prior cont10m read. The DECISIVE new fact: 3 NEW tilt_roll terminations appeared in 24 eval episodes (walk/det/1, walk_startjitter/det/1, walk_startjitter/det/3) that were absent at every earlier depth of this same lineage (cont40m base, cartfoot-c1, cartfoot-c1-cont10m all reported 0/24 falls) -- video (walk_det_1) shows a genuine roll-over, not a metric artifact. The run's own pre-registered gate text is explicit that 'any new fall or protected-behavior loss also blocks promotion and further continuation', so this is a hard stop independent of the slip read. optimization/reward_per_tick keeps rising the whole continuation (-0.214 -> -0.027 EMA -0.214 -> -0.099) while held-out slip stays 1.5-2x worse than the matched control and safety now regresses -- textbook MISALIGNED shape per the run's own routing clause ('reward rises but held-out slip/progress stalls or worsens -> MISALIGNED audit, not more same-recipe training'). Per the pre-registered clause this closes fork (a) for good: the Cartesian foot-target-decode retrofit re-acquires 0-fall walking after the action-semantics scramble but never closes the slip gap to the joint-space control across three separate reads (2M/12M/22M cumulative) and now trades that unresolved gap for new stability regressions at extended budget -- record as an unresolved-retrofit outcome, NOT a universal Cartesian-action-space class closure (fork (b) fresh-init cohorts are a separate, still-open line). No further continuation of this exact cont40m-cartfoot-c1 lineage; any future foot-space work needs a new mechanism or reward fix, not more steps on this recipe.

