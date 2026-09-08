## 2026-09-08 ~09:1x (refill cycle; no completion assigned, canonical capacity found 9-11 GPU pods free across the cycle, backlog empty) -- built + wired the foot-pad-contact-radius structural lever named unbuilt at 03:5x; zero-shot probe shows the FIRST consistent slip improvement in this whole investigation, with a new-fall caveat; no training launched (train-side wiring didn't exist yet, so dosing it blind would have been a silent train/eval physics mismatch)

One plain sentence: the 03:5x torsional-friction closure named "foot-pad
geometry" as the one remaining unbuilt structural-lever candidate for
walkcurr's own closed 9-arm slip-pricing family; this cycle built it,
found every other queued line already claimed or closed by concurrent
cycles (torque1x zero-shot recovery is root-owned, cont10m/durability
closed per their own gates, every DR-hardening axis already has a
verdict), and spent the free capacity on this tool instead of idling.

**Built:** `sim_env.set_foot_geom_radius` (cfg `env.foot_geom_radius_m`,
0 = XML default 4.5mm sphere per foot, bit-exact off) -- mutates ONLY
`geom_size[:,0]` on the `L{i}_foot` geoms, same pattern as the existing
`set_foot_ground_torsion_friction`. Regression test in
`test_sim_env.py` (default-off bit-exact + dosed + survives a no-DR
reset). **Then found and closed a real gap before using it**: this new
cfg key was ONLY wired into the C eval env (`sim_env.py`), never into
the GPU/warp training stack (`mjx_host.prepare_shared_model` + its 3
call sites in `mjx_vec_env.py`/`mjx_sharded_vec_env.py`) -- exactly the
kind of silent train/eval mismatch this campaign has repeatedly caught
elsewhere. Wired `foot_geom_radius_from_cfg` + a `foot_geom_radius`
kwarg through all 3 call sites, matching the existing `foot_mu`
plumbing exactly. New `test_mjx_host.py` (3 tests, host-side only, no
jax/torch needed) proves `prepare_shared_model` is bit-exact at default
and correctly dosed/scoped when set. Full `test_sim_env.py` +
`test_mjx_host.py` + `test_mjx_vec_env.py` suites green (1 pre-existing
unrelated failure, `test_drag_charges_loaded_translation`, confirmed
failing on unmodified `main` too). Snapshotted (swept into a concurrent
cycle's own snapshot commit while landing, `ba683ec9` -- confirmed
pushed, `git log -- rl_move/sim/mjx_host.py` shows the diff live at
HEAD; no separate snapshot needed since the code is already on
`origin/main`).

**Zero-shot diagnostic (frozen checkpoint, NO training, mirrors the
03:5x torsion-friction probe method exactly):** re-ran the champion
`allaxiskickhalf_nocrutch1x_c1_acq1_cont40m` checkpoint's own-DR 24-
episode panel (det+sto x nominal+startjitter, same seed) with ONLY
`env.foot_geom_radius_m` dosed 0(4.5mm)->0.0135m (a plausible "rubber
pad" foot size, 3x the point-like default). **Slip/m improves in ALL 4
groups** -- walk/det 4.98->4.05 (-19%), walk/sto 5.17->4.09 (-21%),
startjitter/det 5.10->3.77 (-26%), startjitter/sto 5.42->4.62 (-15%) --
the FIRST structural lever in this entire investigation (torsional
friction, full-cone contact accounting, twist-consistency, three
turn-authority dials) to move this floor consistently in the improving
direction on every panel, not flat/mixed/null. `gait_valid` stays
5-6/6 in 3/4 groups (walk/det gains a NEW non-chronic sac[5] in one
episode it didn't have before; sto and startjitter/det keep the exact
SAME episode/leg sacrifice as baseline, same seed -> same hard
episode). **Caveat, not free**: `walk_startjitter/sto` picks up ONE NEW
termination (episode 1 now falls) that the baseline (0 falls in this
mode) didn't have -- a real safety-relevant cost alongside the slip
win, on a mode the campaign's other structural probes left untouched.

**Why this doesn't license a training launch yet**: this is a
zero-shot eval-time probe on a policy that never saw the larger foot
during training -- it says "if the physical foot pad were bigger, this
SAME policy slips less (mostly) and falls once more (sometimes)", not
"a policy trained with this foot walks better." Now that the train-side
wiring exists, the honest next step is a matched 2M canary trained
WITH `env.foot_geom_radius_m` baked in from step 0 on this exact
champion lineage (own-DR, same panel) -- gate: PASS if slip improves
>=10% in >=3/4 groups without a NEW chronic single-leg sacrifice or a
net INCREASE in fall count vs the champion's own baseline; FAIL if
slip is flat/worse (closes the lever, joining torsional friction) or a
policy trained with the bigger pad falls MORE than this zero-shot
read's +1 (would mean the geometry change destabilizes training
itself, not just this frozen policy's zero-shot response). **Launched
this cycle** (after the housekeeping below):
`cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-
nocrutch1x-c1-footgeom0135-c1` (respec of the champion `..._cont40m`,
`--init-from-source`, only `env.foot_geom_radius_m=0.0135` added, 2M
canary, VERIFIED RUNNING train-4, gate pre-registered as above). Read
its gate report next cycle before any further foot-geometry spend
either direction.

**Housekeeping this cycle**: two of my own `git stash`/`git stash pop`
round-trips (used only to isolate pre-existing test failures from my
edits, confirmed both were pre-existing on unmodified `main`) raced a
concurrent cycle's own git operation on this SHARED working tree and
left real `<<<<<<<`/`=======`/`>>>>>>>` conflict markers at the top of
this file (both sides were legitimate concurrent-cycle content -- the
corrected torque zero-shot closeout and the halfgrav-cartfoot/widen8
entry now above). Resolved by hand, keeping BOTH entries in their
self-stated chronological order, no content dropped -- verified no
other file in the repo carries a stray conflict marker
(`grep -rl '^<<<<<<<\|^>>>>>>>'` clean repo-wide). Lesson for future
cycles: prefer `git diff`/`git show`/a scratch worktree over `git
stash` for a same-tree before/after comparison when many concurrent
cycles share this clone -- stash is not race-safe here the way
`snapshot.sh` is designed to be.

**Refill:** re-checked capacity at cycle end (11/11 GPU pods
reachable, several free at various points through the cycle) -- no
other non-duplicative, launch-ready arm was identified after the
extensive audit above (torque1x zero-shot is root-owned per
`fb_20260908T083233_3a41e3`; cont10m/durability closed per their own
gates with no new hypothesis licensed; every named DR-hardening axis
already has a verdict; assistfade/standwalk both explicitly blocked on
the SAME unbuilt per-leg/structural-mechanism design this cycle just
took one step on). CYCLE_WORKED touched (real code + a real, if
zero-training, diagnostic result -- not a re-verify no-op).

Evidence: `rl_move/sim/sim_env.py` (`set_foot_geom_radius`),
`rl_move/sim/mjx_host.py`/`mjx_vec_env.py`/`mjx_sharded_vec_env.py`
(train-side wiring), `rl_move/tests/test_mjx_host.py`,
`rl_move/tests/test_sim_env.py::test_foot_geom_radius_override_
default_off_and_dosed`; probe report
`logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_
allaxiskickhalf_nocrutch1x_c1_acq1_cont40m_footgeom0135_probe/
report.json` vs the existing `..._cont40m_gate/report.json` baseline;
W&B `v6wmk0lv`. RL_LOG 09-08 ~09:1x.

--- prior entry below ---

