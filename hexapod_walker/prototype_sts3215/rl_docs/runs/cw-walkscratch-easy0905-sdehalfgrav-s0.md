# cw-walkscratch-easy0905-sdehalfgrav-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T09:02:40+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: t9z4rzy2

**hypothesis**: Plain English: combine the two most promising easy-campaign levers — gSDE temporally-correlated exploration and half gravity — to complete the 2x2 family grid (base / sde / halfgrav / sde+halfgrav) the operator's 09-05 controlled-comparison directive asks for. From-scratch 40M, identical to sde-s0 except ease.gravity_scale=0.5; seed 0 matched to both parents. Question: do the exploration and gravity-easing effects compose (interaction term of the 2x2), or is one sufficient/dominant?

**gate**: Acquisition milestone at OWN 0.5g physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Both parent levers carry a 2M CANARY PASS (sde-s0, halfgrav-s0) but this COMBINATION is new — treat the first ~2M in W&B as its own mechanism spot-check (finite losses, real actions, bank-consistent reward) before trusting the rest. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

