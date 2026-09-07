# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180-legdutyterm1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-07T21:16:48+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180

**wandb_id**: dnpmd5tp

**hypothesis**: Plain English: same repair test as the widen8 trio, on the OTHER already-entrenched instance of this pathology -- the widenbis180 lineage (base5+ONLY the 180deg heading, 40M ACQ, chronic leg-0 sacrifice). Does the new per-LEG minimum-duty TERMINATION (safety.walk_leg_duty_terminate_s, end the episode like a fall if any leg's ground-contact EMA stays below floor for N seconds -- not another per-tick price) repair it? Continuation (--init-from-source) off this seed's own widenbis180 checkpoint, single lever added (safety.walk_leg_duty_terminate_s=4.0, floor=0.05, tau=1.0s, grace=3.0s, dedicated reward.walk_leg_duty_terminate_penalty=150 -- everything else byte-identical). New mechanism bank-proven this cycle (WALKCURR_LEGDUTY_TERM, 4/4 green).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM/BEHAVIOR CANARY (2M continuation): PASS (repair candidate validated) if leg-0 duty recovers to a genuinely used level (>=0.10 sustained) in the majority of episodes, gait_valid improves vs this seed's own widenbis180 baseline (18/24), 0 new falls, and walk_leg_duty_terminate stops firing by the END of the 2M. FAIL - MECHANISM if the leg stays chronically parked despite the termination, terminations stay frequent at the end, or training destabilizes.

**verdict**: CANARY FAIL - MECHANISM: walk_leg_duty_terminate does NOT repair this seed's entrenched leg-0 sacrifice on the OTHER lineage (widenbis180, base5+180deg heading) within the 2M canary. Evidence: gait_valid WORSENS vs this seed's own widenbis180 baseline (18/24 -> 13/24 total: walk/det 4/6, walk/sto 2/6, startjitter/det 5/6, startjitter/sto 2/6), and the termination is still firing in 15/24 episodes at the END of training (4/6 det, 4/6 sto, 2/6 startjitter/det, 5/6 startjitter/sto). Reward still rising (quarters 63->137->235->278) so per 08-21 this alone would license more budget, but the pre-registered FAIL branch is met, matching all 3 widen8 seeds' identical shape. Why: same mechanism-too-late diagnosis -- a hard per-leg duty termination on an already-entrenched 40M exploiter raises cost without removing the incentive gradient; the policy repeatedly re-pays the termination tax rather than escaping within 2M. **This closes the 4-arm legdutyterm1 repair batch 4/4 FAIL, consistent shape across both widen8 (3 seeds) and widenbis180 (1 seed) lineages: walk_leg_duty_terminate, like the 11 prior per-tick price mechanisms before it, does not repair an already-entrenched chronic-leg-sacrifice checkpoint within a 2M budget.** Open question the batch does NOT answer: whether the mechanism would prevent the sacrifice from entrenching in the first place if dosed FROM SCRATCH (before 40M steps of habit forms) rather than retrofitted onto an already-exploiting checkpoint -- untested, and per the 09-07 04:4x diagnostic a heading-conditioned role-aware mechanism is still the more principled fix; a from-scratch legdutyterm1 canary is the next cheap disambiguating test before either abandoning the termination approach or funding the heavier role-aware design.

