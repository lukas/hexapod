# cw-walkscratch-easy0905-sde-s3-c1b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-05T11:05:15+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s3

**wandb_id**: e05si4ue

**hypothesis**: Own-checkpoint 40M continuation of sde-s3 (ACQ CONTINUE verdict this cycle: ep_len_mean dipped from a 333 peak to 47-57 mid-run then genuinely recovered to 184-193 in the last two logged points, ep_rew_mean climbed monotonically -522->+28.3 ending positive, v_along_cmd held ~0.17 m/s throughout -- same still-learning fingerprint sde-s0/s1/s2 already earned continuations for. Respec'd from base-s3 (never carries --use-sde) with blank --activation-fn + --init-from only, per the CURRENT_TRUTHS.md gotcha. RENAMED from sde-s3-c1: that name is burned (first attempt auto-placed on a CPU-contended pod and was killed at fps=91; the identical-vector retry was then REFUSED because W&B names are append-only). This is that same retry, new name, pinned to a confirmed-idle pod.

**gate**: Acquisition milestone at own easy physics: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: FAIL only if v_along_cmd/reward_walk go flat or ep_len re-collapses without recovery; continue further if still climbing at cutoff.

**verdict**: ACQ FAIL — reward-misaligned local optimum, 4th independent gSDE seed of the frozen-leg-subset exploit; do NOT continue this recipe. Plain words: the policy learned to ride out the full episode parked on a leg subset instead of walking. Evidence (gate report + dig-in): 0/24 gait_valid, EVERY episode sacrifices legs [1,3] (one sto: [1]) — per-leg duty [0.96,0.00,0.98,0.00,0.64,0.93] with legs 1/3 parked airborne (1-4 swings/20s), legs 0/2/5 dragged anchors, leg 4 micro-paddling at ~11Hz (215-249 swings); slip_per_m 3.79-5.38 (above teacher <=2.9 and base/halfgrav 2.6-3.4); fwd only 0.9-1.6m/20s; video strips confirm right-side legs tucked with near-identical pose creep. W&B e05si4ue: ep_rew_mean climbs 7.5->2198 and ep_len saturates 1996/2000 while env/walk_speed monotonically DECLINES 0.238->0.132 and v_along_cmd 0.169->0.112 — reward is buying survival income, not walking, so more budget moves AWAY from the gate (08-21 continuation clause does not apply when the task metric is declining). Why FAIL not CONTINUE: matched Gaussian control base-s3 (same recipe/seed minus gSDE) is a clean six-leg ACQ PASS — gSDE is the isolated causal variable across 4 sde + 2 sdehalfgrav-remcost seeds vs 8 clean Gaussian seeds. Next: no more bare-gSDE seeds at this recipe (per 12:1x cross-family synthesis); any gSDE revival goes through the sde-s1-c2/sde-s2-c2 design pass (bank-proven per-leg-utilization pricing), which this verdict feeds but does not pre-empt. Caveat: this gate read is PRE gsde-reset-noise fix (b4259414), so the sto panel is one frozen noise draw dressed as n=6 — det reads and the verdict are unaffected.

