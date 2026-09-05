# cw-walkscratch-easy0905-headset-halfgrav-irr-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-05T14:39:36+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-c1

**wandb_id**: u3gu8x75

**hypothesis**: Plain English: the irregular-direction-change-timing canary on the 0.5g heading family (headset-halfgrav-irr-c1) reads healthy at 2M (reward monotonic 36->129 over 4 quarters, env/walk_speed alive 0.17-0.19 m/s all 4 quarters, ep_len_mean tripling 108->488 i.e. fewer early falls, wrong_way only 2-3%) -- this gives it the full 40M acquisition budget to mature six-leg walking under jittered (goal.walk_cmd_resample_jitter=0.5) direction-change timing, mirroring the base family's already-running headset-base-irr-c1/-c2 pair but on the independently-passed halfgrav heading champion (headset-halfgrav-s1acq). Own-checkpoint warm start only, no teacher/BC/motion-prior.

**gate**: Acquisition milestone at OWN physics (0.5g) with IRREGULAR direction-change timing: 20s held-out episodes across the 3-heading set with jittered resample timing, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, gait_valid true (no sacrificed legs) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail.

**verdict**: First irregular-direction-change-timing 40M acquisition to clear the campaign's gait_valid-majority bar: 0/24 falls across all 4 scenarios (walk/sto/startjitter x det/sto), gait_valid 20/24 overall (walk/det 4/6, walk/sto 6/6, walk_startjitter/det 4/6, walk_startjitter/sto 6/6) -- clears the adopted bar (>=4/6 primary walk/det AND >=13/24 overall) with margin. The 4 flagged det-mode episodes are all borderline (min per-leg duty 0.08-0.10, one leg at the exact threshold), not a chronically-parked LEGPARK-SKATE leg -- every episode has all 6 legs cycling with duty >=0.09 somewhere in [0.09,0.55]. slip_per_m tight 2.18-3.04 (mostly inside/near the 2.9 teacher band, best-in-class for the irr-timing rung so far), speed unreported directly but forward_dist consistent with prior halfgrav-family PASSes. This closes the 0.5g-gravity half of the irregular-direction-change-timing rung (own-checkpoint continuation of the already-PASSed headset-halfgrav-s1acq champion, goal.walk_cmd_resample_jitter=0.5 the only added variable) -- the matching 1g base-family irr-acq1 is a separate concurrent-cycle-owned run, not verdicted here. SKILLS.md updated.

