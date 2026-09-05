# cw-walkscratch-easy0905-headset-base-s0c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-05T13:00:21+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1

**wandb_id**: 6n31rtzj

**hypothesis**: Plain English: headset-base-s0c1's 2M canary just proved the heading-tracking gradient is live on a THIRD base-family seed (same recipe as headset-base-c1/acq1) -- this gives it the full 40M acquisition budget to see if it learns to walk toward the commanded heading set (straight/+45/-45deg) as cleanly as base-s2/s4/s0-c1/s1-c1 walked straight. Warm-started from its own 2M checkpoint (own-track, not teacher/BC/motion-prior). If true: gait_valid=True six-leg walk on all 3 headings, 0 falls, slip near the base family's own 2.6-3.4 band. If false: sacrificed-leg/flag-leg pattern or falls under heading commands, same as the gSDE family's LEGPARK-SKATE (ruled out here since this is plain Gaussian, no --use-sde).

**gate**: Acquisition milestone (own physics, unchanged): 20s held-out heading-set (0/+45/-45deg), >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto.

**verdict**: ACQ FAIL (MISALIGNED, 08-21 class): this 3rd base-family heading seed walks fast with zero falls but chronically parks leg 4 in every deterministic episode, so it is not valid six-leg walking and cannot be a champion. Evidence (gate report, DR-0, mesh_mjx): 0/24 falls, fwd 2.1-3.4 m/20s (0.14-0.19 m/s, well above the 0.03 bar), no belly drag -- but gait_valid only 9/24 (walk/det 0/6, startjitter/det 0/6, startjitter/sto 3/6; walk/sto 6/6), leg-4 duty 0.03-0.07 in ALL det episodes with 29-71 airborne paddle-swings/20s (swinging, never load-bearing); video confirms one right-side leg held aloft/curled while the other five carry the body. This HARDENED with budget: the parent canary s0c1 at 2M had walk/det 6/6 valid with leg-4 duty 0.10-0.15 (marginal), and wandb_history shows ep_rew_mean climbing 342->724 while env/walk_speed sat flat at 0.161 the entire 40M -- reward paid out while the marginal leg slid under the 0.10 sacrifice bar, the LEGPARK misalignment class (milder paddle variant) previously seen only on gSDE seeds. Why FAIL not CONTINUE: more budget demonstrably worsens the exploit (19/24 -> 9/24 canary->acq), the mechanism repair (walk_gait_gate) is already closed 2/2 as gameable, and the family holds 2 clean PASS seeds at identical recipe/budget (headset-base-acq1 18/24, s1c1-acq1 18/24) so the seed adds nothing champion-worthy. Consequences: (1) base heading family closes at 2/3 ACQ PASS -- champions are headset-base-acq1 / s1c1-acq1, NEVER s0c1-acq1; campaign-best remains headset-halfgrav-s1acq (24/24). (2) LEGPARK is now confirmed family-wide (1/3 plain-Gaussian seeds), not gSDE-specific -- raises priority of a hard per-leg min-duty price (non-gameable, unlike the completion-window gate). (3) Acquisition gates now carry an explicit gait_valid-majority bar (>=4/6 walk/det AND >=13/24 overall; persistent single-leg sacrifice in walk/det disqualifies regardless of speed/falls) -- recorded in OPERATOR_QUESTIONS.md. hardware-ready: no.

