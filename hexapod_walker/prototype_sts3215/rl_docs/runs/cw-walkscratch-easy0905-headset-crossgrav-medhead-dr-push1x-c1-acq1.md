# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-push1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T07:19:01+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-push1x-c1

**wandb_id**: se7v9ygs

**hypothesis**: Plain English: does the joystick DONE-gate's own mid-walk push-recovery axis (dr.walk_push_prob restored to 30%/episode) stay durable with real training, not just a 2M canary glance? push1x-c1's own 2M canary was 20/24 (majority, no chronic leg, scattered non-chronic sac across legs 0/2/4/5) -- the LEAST clean of the individually-tested realism axes so far (excluding kick1x's genuine fall), making it the most informative ACQ durability check: does more budget consolidate the scatter into a chronic pattern (like s3acq's own entrenchment) or resolve it?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg pattern (repeat scattered non-chronic flags are fine) and 0 falls. FAIL/ENTRENCHES if it drops below half (<12/24), the scatter consolidates into a chronic single-leg pattern, or a fall appears.

**verdict**: ACQ PASS/HOLDS (found as an unverdicted orphan -- ledger stuck RUNNING, training+gate both finished). Push-perturbation DR axis at 1x holds at 40M within the gate's own pre-registered 'scattered non-chronic flags are fine' clause: gait_valid 20/24 (walk/det 5/6, walk/sto 5/6, walk_startjitter/det 5/6, walk_startjitter/sto 5/6), 0 falls/terminations across all 24 episodes. Sacrificed-leg flags scatter across 3 different modes/episodes (leg5 x3: walk/det/4, walk/sto/2, walk_startjitter/sto/4; leg0 x1: walk_startjitter/det/4) rather than one leg out in every episode of one mode -- video (walk_det_4 frame strip) shows all six legs still visibly cycling stance/swing through the clip, not a rigid/dragged leg. slip/m med 3.3-4.3 (in-family with sibling per-axis PASSes). Per QUEUE AIM's own STOP on further per-axis spend, no cont40m continuation follows -- recorded for SKILLS.md/ledger hygiene only.

