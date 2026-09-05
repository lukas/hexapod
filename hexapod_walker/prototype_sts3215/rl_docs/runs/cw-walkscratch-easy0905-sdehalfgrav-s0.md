# cw-walkscratch-easy0905-sdehalfgrav-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-05T09:02:40+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: t9z4rzy2

**hypothesis**: Plain English: combine the two most promising easy-campaign levers — gSDE temporally-correlated exploration and half gravity — to complete the 2x2 family grid (base / sde / halfgrav / sde+halfgrav) the operator's 09-05 controlled-comparison directive asks for. From-scratch 40M, identical to sde-s0 except ease.gravity_scale=0.5; seed 0 matched to both parents. Question: do the exploration and gravity-easing effects compose (interaction term of the 2x2), or is one sufficient/dominant?

**gate**: Acquisition milestone at OWN 0.5g physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Both parent levers carry a 2M CANARY PASS (sde-s0, halfgrav-s0) but this COMBINATION is new — treat the first ~2M in W&B as its own mechanism spot-check (finite losses, real actions, bank-consistent reward) before trusting the rest. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

**verdict**: Fast face-plant, not walking -- and the reward is paying for the crash. Video (both walk and walk_startjitter clips, det+sto) shows the robot lurching forward hard on legs 1+4 only and pitching straight into the ground within the first ~0.5-0.7s of every single eval episode (24/24: walk/det 6/6, walk/sto 6/6, startjitter det+sto 12/12, ALL terminate tilt_pitch except one tilt_roll). Same 4 legs [0,2,3,5] sacrificed on every det episode -- a flag-leg two-leg-lurch gait, not a six-leg walk. gait_valid 0/6 everywhere, net forward displacement only 0.07-0.26m over a 20s held-out episode (bar was 20s sustained, >=0.03 m/s median, 0/12 falls -- missed on every axis). This is the first full-40M return from the 09-05 full-fleet 2x2 family wave (sde x halfgrav interaction cell), so it matters for the sibling arms sharing this reward config. 08-21 ruling check: scalar ep_rew_mean does creep up late in training (-12 @32M -> +5 @40M) but that's a per-tick reward hack, not learning to walk -- env/walk_speed (~0.27) and env/v_along_cmd_m_s (~0.19) both PLATEAU flat from ~13M steps to 40M (final quarter noise-only), and rollout/ep_len_mean is FLAT at 67-77 ticks (0.7-0.8s) for the entire back half of training -- the policy never learns to survive longer, it just extracts slightly more per-tick reward_walk (0.70->0.87) from the same short violent burst before falling. Root cause hypothesis: the freeprog/EMA velocity reward pays out every tick during the lurch and outweighs the one-time -24 term_penalty (roughly 0.4/tick net x ~70 ticks approx 28 vs -24), so the optimum is 'sprint hard, fall fast' rather than sustained gait -- reward misaligned with the eval per the 08-21 ruling, not a dead lineage. Task metrics (survival ticks, gait validity) genuinely flat at full 40M budget = the FAIL condition, distinct from the still-training single-lever siblings (sde-s1/s2/s3, halfgrav-s0-c1/s1/s2) which should be read on their own evidence, not assumed to share this fingerprint until they return. Next: when the single-lever siblings report in, compare fingerprints; if they show the same plateaued-ep_len signature, the fix is reward realignment (raise term_penalty and/or price survival duration directly, e.g. a small per-tick alive bonus scaled to gate distance) before spending more budget on any further sde+halfgrav combination arm -- root-cause chain + bank update belongs to that follow-up, not this triage.

