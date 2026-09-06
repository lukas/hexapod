# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-cmddrop1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T08:55:40+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-cmddrop1x-c1

**wandb_id**: 43tw8r40

**hypothesis**: Does the campaign's PERFECT single-axis DR-restore canary (medhead-dr-cmddrop1x-c1: nominal cmd_drop_prob~=0.022, 24/24 gait_valid at 2M, 0 falls, sac=[] every episode) hold up at a real acquisition-scale (40M) training budget on top of the 80M champion, matching the friction1x/mass1x precedent that individual-axis DR-restore canaries need their own ACQ confirmation, not just a 2M glance?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg pattern and 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show even a PERFECT canary is not safe to assume durable.

**verdict**: ACQ PASS/HOLDS (found as an unverdicted orphan -- ledger stuck RUNNING, training+gate both finished). Command-dropout DR axis (dr axis: goal command occasionally stale/dropped) holds cleanly at 40M: gait_valid 23/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 5/6, walk_startjitter/sto 6/6), 0 falls/terminations across all 24 episodes, only 1 scattered non-chronic sacrificed-leg episode (leg5, walk_startjitter/det/1 only -- not repeated elsewhere), slip/m med 3.4-4.3 (elevated vs the 2.9 teacher band but in-family with sibling per-axis PASSes, not gated at this scale), video (walk_startjitter_det_1 frame strip) shows all six legs still visibly cycling through stance/swing, no dragged/rigid leg. Matches the same PASS shape as every other per-axis DR confirmation this campaign (majority gait_valid, 0 falls, 1 scattered flag). Per QUEUE AIM's own STOP on further per-axis spend (single-axis question already exhaustively answered), no cont40m continuation follows from this PASS -- recorded for SKILLS.md/ledger hygiene only.

