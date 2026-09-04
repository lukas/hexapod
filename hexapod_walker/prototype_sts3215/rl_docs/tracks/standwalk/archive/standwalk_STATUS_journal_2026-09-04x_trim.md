# standwalk STATUS journal archive — 2026-09-04x (verbatim)

Moved verbatim from the top of STATUS.md when the seed1 twin
(`triplecore-s1-r2`) verdict closed the 2-seed `TripleGruActorCriticPolicy`
canary at 2/2 FAIL.

---

Update, 2026-09-04 ~04:2x (**`cap29-stdwalklohi-triplecore-r2` (seed0)
CANARY FAIL - MECHANISM vs the `cap29-stdwalklo-hi` control — the
isolated-turn-core architecture did NOT fix combined-tick turn
authority; it made BOTH halves of the pre-registered gate worse.
Seed1 twin (`-s1-r2`) is being triaged by a concurrent cycle —
unread here, do not average across seeds without reading it too.**)

`probe_turn_authority.py --vx-cmds` (`logs/ckpt_eval/
probe_turn_authority_triplecore_r2_combined_09-04.json` vs control
`..._cap29_stdwalklo_hi_combined_09-03.json`): combined-tick (vx=0.08)
`wz_med` worse on BOTH signs — wz_cmd=+0.25: 0.084/0.087 (r2) vs
0.111/0.109 (control), ~23% lower; wz_cmd=-0.25: -0.124/-0.122 (r2) vs
-0.171/-0.169 (control), ~28% weaker. Pure-turn (vx=0) ALSO regressed
>10% vs control on both signs (+0.25: 0.190/0.199 vs 0.222/0.222,
~13% down; -0.25: -0.187/-0.182 vs -0.250/-0.251, ~26% down) — the
same signature the whole 8/8-FAIL open-loop lever family was closed
on. Plus a NEW termination type absent from the control:
`terminations/tilt_roll=1` vs the control's 0 (`wandb_summary.json`),
alongside matching `truncated=16`/`hold_min_load=1` baseline noise.
All three pre-registered FAIL triggers hit. Training reward followed
the family's known Q3-collapse-then-recover shape (quarters 21.9/
67.3/-75.1/91.8) so this is not a not-learning/instrument failure —
the architecture converged to a genuinely worse turn policy than the
shared-core Dual control. Full verdict text: ledger entry / W&B notes
for `cw-standwalk-stage2-dualbc6-turncap-mirroraug-cap29-stdwalklohi-
triplecore-r2`.

**Reading:** isolating the turn representation into its own GRU core
did NOT resolve the combined-tick interference signature — on seed0
it's *worse* on every axis than sharing one core. This weakens the
representational-interference hypothesis itself: the 09-03 16:1x
finding that the SCRIPTED teacher already loses 67% of its own turn
authority combined with forward motion (an upstream, shared
BC-anchor-teacher-reference problem, not a policy-capacity problem)
is now the better-supported explanation. Do not build the
`yaw_critic.py`-on-Triple follow-up from the prior Next item until the
seed1 twin confirms this isn't a seed-0-only fluke — build/dose
decisions belong to whichever cycle reads both seeds together.

Build details for `TripleGruActorCriticPolicy` (architecture, CLI,
tests, the self-inflicted net_arch-derivation bug + same-cycle fix)
moved VERBATIM to `archive/standwalk_STATUS_journal_2026-09-04w_trim.md`
(prior banner already in `..._2026-09-04v_trim.md`).
