# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~06:3x (**Two more teacher-side geometry
candidates built + REFUTED zero-training, no RL spend — the "reshape
the commanded yaw ANGLE without changing physical stride magnitude"
lever family is now closed, not just the uniform-scale corner of it.**)

Built the per-leg instrumentation the prior Next item called for
(`rl_move/sim/probe_leg_yaw_rate.py`, drives the real `TripodGait`,
reports per-leg commanded-yaw RATE vs. the 37.5deg/s SafetyLayer clip
plus a foot-placement-direction-consistency check) and used it to
design and screen TWO new candidates before touching any RL budget:

- **Candidate "detangle the vx cross term out of the yaw numerator"
  — REFUTED zero-training, never wired into TripodGait.** The
  derivation (tangential foot-velocity projection per leg,
  `omega*r - vx*sin(leg_angle)`) shows the vx term partially cancels
  omega's contribution for 3 of 6 legs and reinforces it for the
  other 3. Removing the cancelling cross term from the yaw-angle
  numerator sounds like a clean fix, but at any dose that meaningfully
  reduces the worst legs' rate it FLIPS THE SIGN of the previously
  near-cancelled legs' commanded yaw (up to ~12deg foot-target
  direction error) and, at full dose, creates a brand-new saturated
  leg (4/6 over clip vs. the legacy 3/6) — worse, not better. Not
  built into production code at all, just measured and discarded.
- **Candidate (iii) `TripodGait.combined_yaw_amplify_scale`
  (SELECTIVE per-leg sibling of the already-tried uniform
  `combined_yaw_arm_scale`) — mechanically built, tested, and
  REFUTED zero-training.** Only multiplies the atan2 denominator for
  legs the vx cross term AMPLIFIES past their own pure-omega
  magnitude (the other 3 legs stay bit-exact, unlike the uniform
  lever). `probe_leg_yaw_rate.py` confirms dose 3.0 fully
  de-saturates ALL SIX legs' commanded-yaw rate (0/6 over clip, was
  3/6) — but `probe_turn_authority.py`'s scripted-teacher body
  `wz_med` at the SAME command (vx=0.08, wz_cmd=0.25) gets WORSE at
  that dose, not better (0.0723 -> 0.0295 rad/s, and 0.0104 at dose
  4.0), monotonically past ~dose 2.0. Pinned as a regression test
  (`test_yaw_amplify_scale_desaturates_clip_but_REGRESSES_real_wz`)
  so nobody wires it into BC-anchor training or spends an RL canary
  on it. 5 new TripodGait-level tests + 2 new probe-level tests, all
  green; full bc_anchor/tripod_gait/probe_turn/joint_tracking subset
  (142 tests) rerun clean (1 pre-existing unrelated failure,
  confirmed identical on unmodified main via git stash).

**Net finding (generalizes the 09-04 05:35 result): shrinking a
leg's COMMANDED yaw excursion via ANY atan2-denominator trick shrinks
the PHYSICAL rotation it produces right along with it — there is no
"de-saturate the clip proxy without losing real torque" regime for
this family of fixes, whether applied uniformly (`combined_yaw_arm_
scale`, refuted at RL) or selectively (`combined_yaw_amplify_scale`,
now refuted before even reaching RL) or via cross-term cancellation
(new "detangle" idea, refuted before being wired in at all). The
commanded-yaw-RATE-vs-clip metric that motivated this whole geometry
sub-axis (09-03 22:2x) is a RED HERRING for real turn authority; do
not propose another candidate that scores itself on that metric
alone — cross-check `probe_turn_authority.py`'s actual body `wz_med`
every time (now spelled out in `probe_leg_yaw_rate.py`'s own
docstring).**

Prior banner (confound-isolation pair closing the architecture-split
axis) moved VERBATIM to `archive/standwalk_STATUS_journal_
2026-09-04z_trim.md`.

## Next (updated 09-04 ~06:3x)

1. **Rise-stall branch: CLOSED 09-03 ~19:1x.** See archive
   `standwalk_STATUS_journal_2026-09-03o_trim.md` for the full write-
   up. No reward code changed; a future fix should price sustained
   near-ceiling current directly (`over2A_s`-style), not a
   stall-vs-partial-height framing.
2. **Steering branch — TOP ITEM, teacher-side ONLY. The
   "reshape/shrink the commanded yaw ANGLE" geometry sub-axis is now
   CLOSED (uniform `combined_yaw_arm_scale` FAILED at RL 4/4;
   selective `combined_yaw_amplify_scale` and the unwired "detangle"
   idea both REFUTED zero-training, this cycle — see banner).** The
   one lever proven to move REAL physical wz at the scripted-teacher
   level, `train.bc_anchor_teacher_omega_boost` (uniform, all 6
   legs), still failed 4/4 at the RL stage on pure-turn regression —
   that failure is a BC-anchor/PPO training-dynamics issue, not a
   geometry defect, so a genuinely NEW candidate must change WHICH
   legs get boosted, not just re-try uniform magnitude tricks:
   **untried candidate — SELECTIVE per-leg omega boost**, applying
   `bc_anchor_teacher_omega_boost`-style extra omega ONLY to the 3
   legs `probe_leg_yaw_rate.py` identifies as ATTENUATED by the vx
   cross term (restoring their own pure-turn capability) while
   leaving the 3 already-AMPLIFIED legs at dose 1.0 — the mirror
   image of this cycle's selective-scale idea, using the SAME per-leg
   classification machinery (`_yaw_frame_xy` + a pure-omega
   reference) but targeting the physically-effective boost lever
   instead of the physically-null angle-reshape lever. Validate zero-
   training with `probe_turn_authority.py --policy scripted` (extend
   with a `--scripted-omega-boost-legs`-style selective variant)
   BEFORE any RL canary — if the scripted-level combined wz gain
   survives a check against the SAME clip/direction-consistency
   instruments this cycle used, THEN it's worth spending an RL
   canary; if it reproduces the uniform boost's sign-asymmetric RL
   failure anyway, that closes the ENTIRE geometry-fix axis for good
   and the honest next move is a gait-STRUCTURE change (per-leg
   period/tripod-grouping during combined ticks — not yet tried at
   all) or escalating a DONE-gate turn-authority renegotiation. Do
   not re-open the architecture-split axis (Triple/yaw_critic.py) —
   it is done.
3. **Closed (archives 09-02{,b..h}, 09-03{a..u}, 09-04{v,w,x,y,z}):**
   architecture-split (`TripleGruActorCriticPolicy`, 2/2 FAIL +
   confound-isolation pair explaining it, 09-04); yaw-arm-scale
   candidate (i)-v2 dose x seed grid (4/4 FAIL); candidate (iii)
   `combined_yaw_amplify_scale` (selective per-leg scale, fully
   de-saturates the clip proxy but REGRESSES real scripted-teacher
   wz, 09-04); "detangle the vx cross term" idea (foot-placement
   direction-consistency REFUTED before being wired in, 09-04);
   update-size/reward/exploration/anchor/turn-skip/yaw-credit/diet/
   duration/switch-jump/frame-blend/current-confound/combined-tick-
   anchor-skip/omega-boost (both directions)/combined-yaw-boost
   sweeps; cap29 acquisition (PARTIAL); log_std anneal dose grid (`hi`
   PASS, `mild` FAIL); item 0 sto/det convergence-at-scale (PASS);
   resamplematch diet-match-rate hypothesis (refuted both doses/
   seeds); rise over_current dig-in (genuine lineage fragility, not
   an instrument defect); rise-stall faithful replay (CLOSED, see
   item 1); steering/rise-stall semantics-bank twins (both PASS);
   candidate (i) IK-feasibility + naive slew-saturation groundwork
   (superseded).

> Journal archives (VERBATIM, oldest->newest, `archive/standwalk_
> STATUS_journal_<date>_trim.md`): 2026-08-30, 09-01, 09-02{,b..h},
> 09-03{a..i,n,o,p,q,r,s,t,u}, 09-04{v,w,x,y,z}. Current state = newest
> Update at the TOP; don't act on archived Next.

## Fleet capacity note (updated 09-04 ~06:3x)

No GPU launch this cycle either: this cycle's two zero-training
candidates (selective-scale + detangle) were BOTH refuted before
reaching the RL stage — exactly the outcome the validate-first
discipline is for (a wasted canary avoided, not a stall). The next
candidate (Next item 2, selective per-leg omega boost) still needs
its own zero-training probe extension + validation before it's a
pre-registered arm. Every OTHER track remains non-launchable by
design (`joystick`/`amp`/`cpg` DONE or maintenance-only; `walkcurr`
RETIRED; `todaypolicy` DELIVERED). All 11 reachable GPU pods free.
