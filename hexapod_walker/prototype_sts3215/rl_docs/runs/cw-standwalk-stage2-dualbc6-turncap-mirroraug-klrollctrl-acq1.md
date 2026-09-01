# cw-standwalk-stage2-dualbc6-turncap-mirroraug-klrollctrl-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PARTIAL

**created**: 2026-09-01T01:00:28+00:00

**pod**: hexapod-mjx-train-1

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-canary

**wandb_id**: loa21si2

**hypothesis**: Is bounded-KL alone (no actor freeze) sufficient to stop turn-authority erosion, isolating kl-rollback from the value-warmup freeze it was paired with in the sibling klroll-acq1 arm?

**gate**: PASS if final probe_turn_authority wz_med>=0.10 both signs at 38M AND gait_valid>=5/6 zero falls AND purewalk det progress_ratio in/above 0.40-0.48 (kl-rollback alone sufficient). PARTIAL if authority holds above the prior mechanism-class floor (>0.05 both signs) but under 0.10 (helps but insufficient alone). FAIL if authority erodes to the same <=0.05 floor as every prior refuted mechanism (kl-rollback alone refuted, decision falls to the paired klroll-acq1 sibling read).

**verdict**: Joint sibling of valuewarmup-klroll-acq1 (this cycle's assigned run) -- also finished this cycle, untriaged, no other cycle had claimed it, read jointly since the pair's own gate is explicitly joint ('guard sufficient alone / both needed / hypothesis refuted'). Plain English: bounding the PPO update size alone (no actor-freeze) reaches the SAME good mid-run turn-authority plateau as freeze+guard together, just faster -- but that plateau is NOT durable by itself and resumes eroding in the back half of training. Mechanism: train/kl_rollback_count fired 3x within the first 262k steps of training (this run has no freeze, so this is the FIRST post-init PPO update, approx_kl 2.05 -- confirms the oversized-update shock is a generic 'first update against a good BC/canary init' phenomenon, not specific to the unfreeze transition), then realized approx_kl stays bounded ~0.01-0.03 for the ENTIRE remaining 38M budget (same bound as the freeze+guard sibling) -- guard clearly engaged, generalizes the mechanism. probe_turn_authority (own TURNCAP_CFG_SET, 10-point curve built on-pod train-1, logs/ckpt_eval/turn_authority_dualbc6_turncap_mirroraug_klrollctrl_acq1_*.json): 2M already at 0.104-0.109 pos/-0.112 to -0.157 neg (below canary-init since no freeze means the actor has been training since step 0); 8-20M plateau 0.060-0.089 pos, -0.083 to -0.124 neg -- matches the freeze+guard sibling's own 10-22M plateau almost exactly, reached ~2M steps faster (no 8M critic-only wait needed). BUT from 24M onward the plateau breaks and authority resumes eroding: 24M (0.075-0.086/-0.073 to -0.083), 28M (0.072-0.089/-0.087 to -0.089), 32M (0.061-0.069/-0.068 to -0.073), 36M (0.054-0.056/-0.065 to -0.069), final 38M pos 0.055/0.055, neg -0.065/-0.070 -- ends up much closer to the UNGUARDED parent valuewarmup-acq1's own floor (pos 0.029/0.032, neg -0.069/-0.065; neg is nearly identical) than to the freeze+guard sibling's held final (pos 0.068/0.068, neg -0.109/-0.110). In-training clean: eval/walk survived_frac=1, walk_startjitter survived_frac=1, no gait-collapse (eval/raise survived_frac=0.5 is the rise submode, uses a separate GRU core, not part of the turn probe). Verdict for THIS run (own scope): ACQ PARTIAL -- mechanism engaged and generalizes beyond the freeze case, real mid-run improvement over the unguarded baseline, but the guard-only recipe is NOT durable to the full 38M budget on its own. JOINT conclusion (see valuewarmup-klroll-acq1's own verdict for the full writeup): the pair's fork answers BOTH NEEDED -- kl-rollback defends authority fastest without freeze, but only the freeze+guard combination holds it durably through the full acquisition budget. Next (launched this cycle): klrolltight-acq1 (this recipe, guard-only, but tighter cap 0.02 -- tests whether tightening alone fixes the late-stage re-erosion) + valuewarmup-klrolltight-acq1 (freeze+tighter-guard 0.02, the combination most likely to close the remaining positive-sign gap to the >=0.10 PASS bar).

