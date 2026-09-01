# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-01 ~09:0x (triage cycle — JOINT CLOSE 2/2 on the
matched-actor-training-steps confound test, PLUS a flagged DIG-IN on
the tighter-cap dose-bracket arm that finished unclaimed in the same
window). Plain English: **the freeze-vs-total-actor-steps confound is
now closed with real confidence: freeze only delays turn-authority
erosion, it does not add durable protection beyond what the same
number of actor-training-steps produces anyway — closing the whole
actor-freeze/value-warmup mechanism line for good.** Built the own
4-point `probe_turn_authority` curve (2M/4M/6M/8M elapsed = 32M/34M/
36M/38M actor-training-steps, own TURNCAP_CFG_SET) myself, on-pod, for
BOTH training seeds (my assigned `...-klrolldriftmatch-acq1-s1` PLUS
its seed0 twin `...-klrolldriftmatch-acq1`, which had also finished
training but was still mechanically flagged RUNNING/unclaimed in the
ledger — claimed and closed jointly since the gate is explicitly a
joint n=2 read). Seed0 final: pos 0.0897/0.0637, neg -0.1122/-0.1028.
Seed1 final: pos 0.0891/0.0639, neg -0.1029/-0.1091. Combined (n=4)
final pos avg 0.0766 vs the guard-only sibling's own 38M-actor-step
floor avg 0.0749 (diff 0.0017, within noise) and neg avg -0.1068 vs
-0.1179 (diff 0.0111, at/within the ~0.01-0.02 seed-to-seed scatter
this campaign has shown throughout). Both seeds show a slow CONTINUED
decline from the shared 0M-elapsed start (pos avg 0.078, neg avg
-0.1153) toward that floor, not a held-flat plateau at the higher
starting value — the gate's own FREEZE-PROTECTS clause (pos staying
>=0.078, no material neg decline) is missed on both seeds. No
gait-collapse confound (`eval/walk/survived_frac`=1.0 both seeds, all
probe rollouts `fell=false`). Verdicted both **ACQ PARTIAL - MATCHED-
DRIFT CONFIRMED, JOINT CLOSE 2/2**. **This closes the entire
freeze-based mechanism line: no further freeze-only or periodic-
re-freeze work is funded on this axis** — the durable ceiling this
whole 3-dose (0.05/0.02/~0.01) x freeze-or-not campaign has produced
tops out around pos 0.075-0.09 / neg -0.10 to -0.12, never durably
clearing the >=0.10-both-signs PASS bar on the positive sign. Evidence:
`logs/ckpt_eval/turn_authority_dualbc6_turncap_mirroraug_klrolldriftmatch_acq1{,_s1}_curve.json`
(built this cycle, on-pod, pushed to controller).

**DIG-IN FLAGGED (not verdicted this cycle): `cw-standwalk-stage2-
dualbc6-turncap-mirroraug-valuewarmup-klrolltight2-acq1`** (the
`--kl-rollback=0.01` notch below the 0.02 sibling, also finished
training this window, also unclaimed) — its own `probe_turn_authority`
curve is a genuine anomaly, not a clean dose-response read. Ran the
same 7-snapshot curve (2M/8M/12M/20M/30M/36M/final=38M) on-pod:
**every single snapshot from 2M through the 38M final reads BIT-
IDENTICAL** (pos 0.1345/0.0886, neg -0.1649/-0.1658, to 4 decimal
places, every checkpoint). Root-caused with a direct actor/critic
weight diff (`load_checkpoint_auto` + `state_dict()` comparison,
2M-snapshot vs final): the ACTOR tensors (mlp_extractor.policy_net,
action_net, `lstm_actor`/core_a+core_b actor paths, `log_std_a`) are
**exactly 0.0 max-abs-diff** between 2M and 38M — the actor never
moved a single float after the explicit 8M freeze released — while
the CRITIC tensors (value_net*, lstm_critic.core_a/core_b,
mlp_extractor(_b).value_net) show large diffs (0.03-0.57), proving the
checkpoints are genuinely distinct saves, not a duplicate-file bug.
`train/kl_rollback_count`=457 (vs ~24-35 for the 0.02 siblings) and
`train/kl_rollback`=1 (the LATEST recorded update was itself rolled
back) — this is consistent with `--kl-rollback=0.01` being BELOW this
policy family's normal realized-approx_kl operating range (the
campaign's own earlier root-cause: every run in this family realizes
approx_kl ~0.08-0.15 per raw update pre-guard) tightly enough that
**every post-unfreeze actor update gets rejected and rolled back,
making this an accidental 38M-step CRITIC-ONLY run, not a genuine
tighter-dose test of actor learning under a tighter cap.** The
wz_med reads would nominally CLEAR the >=0.10-both-signs PASS bar
(pos avg 0.1116, neg avg -0.1654) — but that number is very likely
just the untouched `turnpay-canary` init's own already-good turn
authority carried forward unchanged by an actor that never trained,
not evidence of durable RL-preserved authority. Trusting it as a PASS
would be a **methodology-invalidating false positive**: the run's own
gate text was written to test "does a tighter cap improve the durable
outcome," not "does a policy that never updates keep its initial
skill" (trivially yes). Per the model-tiering protocol this decides a
real fork (is the guard's hard reject-and-skip broken at low
thresholds, warranting a partial-step-scale-down fix, vs. is 0.01
simply below a hard floor and the axis should stop at 0.02) and is
left UNVERDICTED for the deep-model dig-in pass. Evidence: `logs/
ckpt_eval/turn_authority_dualbc6_turncap_mirroraug_valuewarmup_klrolltight2_acq1_curve.json`,
`logs/ckpt_eval/klrolltight2_acq1_weightdiff_2Mvfinal.json` (both
built this cycle, on-pod).

**Campaign-level conclusion (regardless of how the klrolltight2
artifact resolves): the entire single-update-size-constraint mechanism
family — actor-freeze, value-warmup, kl-rollback guard at 3 doses
(0.05/0.02/~0.01) — is now exhausted.** Best CONFIRMED clean result
remains `valuewarmup-klrolltight-acq1`'s own final (pos 0.0803/0.0756,
neg -0.1131/-0.1175), which never durably exceeded that band under
further training. The campaign's own repeatedly-named next lever —
a reward-decomposed / command-conditioned critic (separate value
head(s) trained on the yaw-reward component's own discounted return,
summed into the advantage, so the yaw channel's credit signal is not
drowned by the dominant walk-forward reward) — is genuine new-code
architecture work, NOT YET BUILT. Rough scope for whoever picks this
up: (1) `RewardComponentCollector` (built 08-31 for `probe_yaw_credit`)
already exposes per-tick reward components — reuse it inside the
rollout buffer to log a yaw-component reward stream alongside the
total; (2) add a second value head (`value_net_yaw`/`value_net_b_yaw`,
mirroring the existing dual-core `_b` head pattern already in
`gru_policy.py`) trained via its OWN GAE computed off the yaw-component
reward only; (3) sum `advantage = advantage_total_normalized +
lambda * advantage_yaw_normalized` (or a config-gated coefficient) for
the PG loss, keep the value loss as two independent MSE terms; (4) new
cfg key defaults OFF, bit-exact when off, per RESEARCH_RULES; (5) a
canary-scale (2M) test on the SAME `turnpay-canary` init before any
acquisition-scale spend. Did NOT start implementing this in-cycle: a
correct GAE-per-component change touches the rollout buffer and PPO
loss core and deserves a dedicated build+test pass, not a rushed
half-implementation late in a triage cycle that would then get
trained on before being properly verified (RESEARCH_RULES: never
change shared default behavior without green tests). No other track
has runnable work (joystick/amp/cpg DONE-or-maintenance, todaypolicy
delivered, walkcurr RETIRED — re-confirmed fresh this cycle). 12/12
GPU pods free at cycle end but the one live open question
(klrolltight2's own artifact — fix-the-guard vs. accept-0.02-as-the-
ceiling vs. escalate) is a fork that should decide the next launch,
not be preempted by more launches on the same compromised axis; the
real next architecture build needs a dedicated pass, not a rushed
one. CYCLE_WORKED.


## Next (meta 09-01 — current queue, in order)

1. **Resolve the flagged klrolltight2 DIG-IN** (deep-model cycle,
   already flagged 09-01 09:1x, unverdicted): `--kl-rollback=0.01`
   rejected EVERY post-unfreeze actor update (rollback_count=457,
   actor tensors bit-identical 2M->38M) — an accidental critic-only
   run. Decide the fork: (a) guard should scale the step down and
   retry instead of reject-and-skip when the cap sits below the
   family's realized-KL floor (~0.08-0.15), vs (b) 0.01 is simply
   unusable and the dose axis stops at 0.02. Its nominal wz 'PASS'
   is a false positive (the actor never trained) — never cite it.
2. **Build the reward-decomposed critic** (the campaign's named next
   lever; full 5-point scope in the 09-01 ~09:0x head above). New cfg
   keys default OFF, bit-exact when off, semantics bank + unit tests
   green BEFORE any launch (RESEARCH_RULES). Then pre-register and
   launch the pair in ONE batch off the `turnpay-canary` base:
   decomposed-critic arm + matched control, 2M canary first, gate
   final probe_turn_authority wz_med>=0.10 both signs with purewalk
   det progress_ratio in the 0.40-0.48 band.
3. **Standing bar (unchanged):** every new dual distillation must
   pass pre-RL probe_turn_authority >=0.10 both signs (mirror-augment
   is the known fix); RL arms on this line are funded as turn
   RETENTION only, never turn discovery.
4. **Closed lines — do not refund:** update-size constraints (actor-
   freeze, value-warmup, kl-rollback 0.05/0.02/~0.01; matched-drift
   confirmed n=2), reward pricing (turnpay 1x/5x, yawscale 5x/15x,
   k_yaw_still, turn density), exploration magnitude (log_std -0.8/
   -0.2, ent-coef), anchor dose/isolate-update, turn-skip. Evidence:
   archive/standwalk_STATUS_journal_2026-09-01_trim.md.


> Journal archives (VERBATIM, meta trims): pre-08-30 in
> `archive/standwalk_STATUS_journal_2026-08-30_trim.md`; 08-30 ~03:1x
> through 09-01 ~07:4x in
> `archive/standwalk_STATUS_journal_2026-09-01_trim.md`.
> Current state lives in the newest Update at the TOP of this file;
> do not act on archived Next items.

## Goal (operator, 08-24 evening)

Retrain the best rising-and-lowering (stance) model on the NEW mesh
MuJoCo model at 100 Hz, then use it as a teacher to distill rise/lower
plus the best walking behavior into one policy. Product: a single
mesh-family 100 Hz policy that, starting from sit, rises, follows a
randomized 60 s joystick session with zero falls, and lowers back.

## Binding constraints (why this is a retrain, not a resume)

- Families do NOT transfer (CURRENT_TRUTHS "SIM MODEL FAMILIES"): the
  legacy stance champion `ppo_goal_cw_stance_dr10` and walk champion
  `ppo_goal_cw_dep_bcgait4_phasedir9_stotight45_seed13` are
  primitive-family 25 Hz policies. NO `respec --from` / warm-start of
  them onto mesh — stage 1 is a recipe rerun on the new model.
- New launches already get `control.hz=100` (launcher-injected) and
  `env.model_source=mesh` (the default) — do not pin legacy values
  here, and never pin `model_source=primitive` in this track.
- Legacy champions MAY be queried as teachers (same obs layout), but
  they carry 25 Hz action scale and primitive dynamics: any
  distillation mechanism must handle the 25->100 Hz gap (query at
  25 Hz + interpolate, distill trajectories, DAgger with rate
  conversion, ...) and must MEASURE whether primitive-trained advice
  is good on mesh dynamics before trusting it.

## Stage 1 — mesh/100 Hz stance retrain (rise + lower)

Recipe basis: the `stance_dr10` lineage recipe (exact cfg in the
ledger/W&B). The rise-reference machinery (`extract_rise_ref.py`,
rise bank) is green as of 08-24. Bank/semantics-check the stance
reward ON MESH before the first launch (mass went 2.104 -> 3.50 kg;
thresholds calibrated on primitive may rank behaviors differently).

GATE (pre-registered): stance panel rise/hold/lower (pod_eval stance
modes), n>=12, det+sto, DR-0 + own-DR: zero falls/tips, quiet hold
(no creep), rise/lower height tracking comparable to the legacy
champion's band. Absolute numbers shift with the +66% mass — the
first passing run's numbers become the recorded mesh reference band.

## Stage 2 — teacher distillation into the best walking model

Use the stage-1 policy as the rise/lower TEACHER. Walking source: the
joystick champion lineage (`stotight45-seed13`) or its mesh-era
successor if the joystick track's in-flight mesh arms produce one
first — either adoption is PRE-REGISTERED here, never a silent
teacher swap (cpg containment rule applies). Mechanism is
cycle-designed (BC clone + RL fine-tune a la bcgait, KL-to-teacher,
phase-scheduled multi-teacher, ...); every mechanism arm pre-registers
its gate and a matched control.

DONE GATE (the track's): ONE mesh-family 100 Hz policy, from sit:
rise -> randomized 60 s joystick command script -> lower to sit.
Zero falls, directions followed, slip/m within the joystick band
(<=~2.9), held-out panel n>=12, det+sto, DR-0 + own-DR.
`eval_joystick_gate` covers the walk segment; the sit->rise->walk->
lower session harness is stage-2 tooling to build.


## Landmines

- Sim only — hardware stand/plant transfer stays operator-owned.
- No stage-2 arm may warm-start from a primitive checkpoint.
- The joystick track owns generic mesh walking; this track owns
  rise/lower + the unification. Coordinate via STATUS, don't
  duplicate its mesh conversion arms.

