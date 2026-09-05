# cw-walkscratch-easy0905-headset-base-s0c1-swinggate-fix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-05T21:34:31+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1-dgate2-c1

**wandb_id**: 2vlzxnoh

**hypothesis**: Entrenched-checkpoint retrofit twin of swinggate-fresh: does the new reward.walk_swing_gate mechanism (MIN-over-legs trailing-window COUNT of qualifying real swings, bank-proved this cycle 4/4 green) cure the leg-4 marginal-underuse habit AFTER it has already entrenched over a full 40M acquisition (headset-base-s0c1-acq1), the same way walk_duty_gate's entrenched-checkpoint retrofit (dgate2-c1/dgatefix batch) was tried and found genuinely-pricing-but-too-late on this family? Warm-starts from the same headset_base_s0c1_acq1.zip 40M champion dgate2-c1 used.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M): PASS/repair-signal if walk_startjitter/det leg duty on the chronically-parked leg moves meaningfully off its 0.02-0.07 baseline (matching or beating the first-seed medhead champion's accepted-PASS 0.08-0.09 range) in a majority of episodes, with 0 new falls. FAIL - MECHANISM if the same leg stays chronically <=0.07 in a majority of episodes despite walk_swing_gate_factor showing real (non-saturated) decline -- the 'genuinely pricing but too late against an entrenched checkpoint' pattern the duty_gate retrofit batch already established, this time for a different mechanism. Read together with swinggate-fresh: if fresh cures it but this retrofit doesn't, budget the fresh recipe as the winning provenance; if both fail, swing_gate needs a longer acquisition budget or a genuinely new lever.

**verdict**: CANARY FAIL - MECHANISM (INERT DOSE, entrenched-checkpoint retrofit): 2M of walk_swing_gate=1.0 on top of the entrenched s0c1_acq1 checkpoint produces a harness result virtually IDENTICAL to the undosed s0c1_acq1 twin across ALL FOUR modes -- walk/det 0/6 gait_valid both (leg4 duty 0.03-0.07 twin vs 0.04-0.06 here), walk/sto 6/6 both, walk_startjitter/det 0/6 both (leg4 duty 0.00-0.04 twin vs 0.01-0.06 here), walk_startjitter/sto 3/6 both (identical count). This is an even cleaner null result than the fresh-provenance sibling (swinggate-fresh, also FAIL-INERT) since this compares directly against its OWN true parent checkpoint, not a similar sibling: 2M steps of the new price produced no measurable behavior change on any of the 4 modes. env/walk_swing_gate_factor logged saturated at 1.0 at all 4 sampled points across training (same sparse-logging caveat as fresh -- likely an eval-instant snapshot, not a trailing average, so treat as weak corroboration not primary evidence); the harness duty numbers are the real signal and they show zero movement. 0 falls anywhere. Matches the CANARY's own pre-registered comparison instruction ('read together with swinggate-fresh: if both fail, swing_gate needs a longer budget or a genuinely new lever') -- BOTH arms of this cycle's read now FAIL-INERT. Read together with sibling retrofits medhead-swinggate-fix/irr-swinggate-fix (checked same cycle) this closes walk_swing_gate as a 7th independently-designed per-leg-utilization mechanism on the base(1g) family if those two also FAIL -- do not fund any further walk_swing_gate arm (fresh or entrenched, any checkpoint) without a genuinely new formulation; the next lever must be structural. Evidence: ops.sh review cw-walkscratch-easy0905-headset-base-s0c1-swinggate-fix, logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s0c1_swinggate_fix_gate/report.json vs logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s0c1_acq1_gate/report.json, W&B 2vlzxnoh.

