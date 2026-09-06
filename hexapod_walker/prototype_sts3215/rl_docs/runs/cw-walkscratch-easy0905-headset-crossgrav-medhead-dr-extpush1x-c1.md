# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-extpush1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T05:53:28+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-tiltnoise1x-c1

**wandb_id**: 7rjjhtyv

**hypothesis**: Restore a moderate (1x, matching the sibling push1x/kick1x dose convention) mid-episode EXTERNAL PUSH probability (ext_push_prob=0.3) -- distinct from the walk-takeoff dr.walk_push_* axis already tested (push1x): this fires a random-direction horizontal force pulse at a random point LATER in the episode, on a policy that is already walking, the AMP-brief-style push-recovery test. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive being shoved mid-stride without retraining collapse? Isolated single-axis diagnostic, same template as the sibling DR-restoration arms.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait recovers from mid-stride pushes. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows push-recovery realism is a binding constraint the DR-rung must budget real training time against.

**verdict**: CANARY PASS (mechanism-health, informative-positive): restoring nominal mid-stride external-push realism (dr.ext_push_prob=0.3, random-direction horizontal shove after the policy is already walking -- distinct from the walk-takeoff dr.walk_push_* axis already tested as push1x) on the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps) does NOT collapse the gait. Evidence: harness gait_valid 22/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 4/6), 0 falls/terminations across all 24 episodes, the only 2 flagged episodes are single-episode non-repeating legs (leg5 ep0, leg0 ep1 in walk_startjitter/sto) -- not the campaign's recurring chronic leg[1,4] fingerprint. Slip/m 3.4-5.2, forward_dist 1.1-2.1m/20s, all within band. Clears the gate's own >=18/24 + no-new-chronic-leg + 0-falls bar. This completes push-recovery realism (mid-stride, not just at gait onset) as a clean single-axis DR-restore on the flagship champion, alongside actionnoise1x -- both of the 2 extra (beyond guardrails' named mass/geometry/friction/compliance/gravity/gains) axes registered last cycle now PASS. SKILLS.md updated. Next: no ACQ (40M) durability read exists yet for extpush1x specifically -- a candidate for the next DR-restore-axis ACQ-continuation batch once GPU capacity frees (fleet is 0/12 FREE this cycle, all reachable pods busy on in-flight ACQ/cont40m work; train-6 Pending on CoreWeave scheduling, not assignable).

