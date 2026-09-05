# cw-walkscratch-easy0905-sde-s1-dg1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS (scope-corrected)

**created**: 2026-09-05T15:10:23+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sde-s1-c2

**wandb_id**: lvdirvti

**hypothesis**: Plain English: sde-s1-c2 learned to survive by parking legs and skating (LEGPARK-SKATE, ACQ FAIL misaligned) -- the recency-based walk_gait_gate repair already closed 4/4 (gamed by a rare token swing). This is the brand-new duty-FRACTION gate (reward.walk_duty_gate=1.0, MIN over support legs of trailing-3s contact-duty vs a 0.15 floor) built+bank-verified this cycle (5/5 test_walkscratch_easy_pilot.py duty_gate tests green) -- it prices TIME FRACTION not recency, so a rare touch cannot dodge it. Cheap 2M canary (own-checkpoint continuation) before any 40M acquisition spend, single lever (k_step_event and walk_gait_gate both left at 0 to isolate this mechanism alone).

**gate**: MECHANISM-HEALTH CANARY: watch env/walk_duty_gate_factor climb toward 1.0 (not stay saturated at ceiling like the closed gait_gate lever did) alongside ep_rew_mean/env/walk_speed not collapsing, 0 blowups. PASS funds a 40M acquisition continuation with the real gate: gait_valid majority in walk/det (>=4/6), duty_cycle>=0.10 all 6 legs. FAIL (reward+speed collapse, or factor pinned again while harness would flag sacrifice) closes this lever too and forecloses cheap-repair options on the sde family.

**verdict**: walk_duty_gate mechanism-health canary: walk/det is a genuine six-leg escape from LEGPARK-SKATE -- 6/6 gait_valid, 0 falls, per-leg duty [0.84,0.28,0.26,0.48,0.22,0.82] (min 0.22, every leg well above the 0.10 sacrifice bar; the parent lineage had legs pinned at 0.00-0.04), slip/m 3.33, fwd 0.137 m/s. BUT this canary did NOT test what it was registered to test: TOOLING BUG FOUND -- the launch's --init-from resolves to rl_move/sim/policies/ppo_goal_cw_walkscratch_easy0905_sde_s1.zip (the ORIGINAL pre-LEGPARK 2M canary checkpoint), not sde_s1_c2.zip (the actual 40M LEGPARK-SKATE FAIL checkpoint this arm's own hypothesis/parent field says it continues). A plain respec --from <c2> without --init-from-source clones the source's cloned arg vector VERBATIM, including c2's OWN --init-from sde_s1.zip, and nothing in the follow-up overrides it -- so this ran duty_gate from-early rather than curing an entrenched skate policy. Same bug confirmed on sibling sde-s2-dg1 (init-from=sde_s2.zip, its grandparent, not sde_s2_c2.zip) and WORSE on sdehalfgrav-remcost-{s0,s1}-dg1 (no --init-from arg in the live command at all -- fully FRESH-SCRATCH, since the remcost source itself carries no --init-from to inherit). CURRENT_TRUTHS.md updated with this gotcha; those 3 sibling runs are owned by a concurrent cycle, left untouched/unverdicted, flagged only. Net verdict on THIS run: real positive evidence that walk_duty_gate prevents/escapes LEGPARK-SKATE from an early undifferentiated checkpoint in the primary det mode, but does NOT yet answer whether it cures an ALREADY-entrenched skate policy (open question, relaunching correctly this cycle) -- and reveals a NEW caveat: 13/24 falls (all tilt_pitch) across walk/sto (5/6), walk_startjitter/det (5/6), walk_startjitter/sto (3/6), i.e. real six-leg gait is fragile under stochastic action noise / start-pose jitter at just 2M steps post-switch-on, unlike the LEGPARK parent which had 0/24 falls everywhere. Funding the CORRECTED entrenched-checkpoint test (sde-s1-c2-dgatefix, explicit backlog add off sde_s1_c2.zip) plus a proper 40M acquisition continuation of this checkpoint to see if the sto/startjitter fragility clears with budget.

