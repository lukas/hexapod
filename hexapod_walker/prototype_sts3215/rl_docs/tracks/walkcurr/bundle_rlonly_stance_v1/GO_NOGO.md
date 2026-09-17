# walkcurr-rlonly-stance-currentcap29-s5-klrollback05-acq15m — GO/NO-GO (2026-09-17)

## Verdict: GO for sim-demo + export readiness of the STANCE role only (rise-from-floor + hold). NOT a physical-acceptance verdict, NOT a full lifecycle bundle.

One plain sentence: this packages the first clean-`rl_only` checkpoint that
consolidates BOTH rise-from-floor and hold-standing at the full 15M-step
acquisition budget with a perfect own-cfg gate (hold 12/12, rise-flat
12/12) — a real, previously-uncaptured piece of Goal 2 evidence that had
gate/eval artifacts sitting on disk with no transfer manifest — while being
explicit that `lower` and `walk` are NOT part of this checkpoint's weights.

## Why this cycle did this (gap it closes)

`walkcurr`'s own 2026-09-17 ~10:1x STATUS refresh closed `lower` entirely
(all 16 agent-doable RL mechanism classes refuted, parks on Robot Lab
achievability review) and separately noted rise-flat+hold consolidation is
"2/3 seed-general at the full 15M budget" with the best seed
(`s5-klrollback05-acq15m`, hold 12/12 + rise-flat 12/12, actually beating
the `s3` sibling's own 10/12 rise-flat precedent) never packaged into a
transfer artifact — every prior `rl_only` packaging effort
(`bundle_rlonly_v1`/`v2`) covers the WALK role only. With 15/15 GPU slots
free, an empty backlog, and every other track independently closed pending
either Robot Lab or a genuinely new structural design idea (re-surveyed via
`ops.sh board` + each track's own latest STATUS entry this cycle), this
cycle packaged the already-validated checkpoint (plus a small corroborating
read on the concurrently-closed seed question, see below) rather than
leaving it sitting unclaimed.

## What shipped this cycle

1. **Read (not re-litigated) a concurrent 2026-09-17 ~11:0x cycle's
   closure of the `s1-acq15m-lowlr` root-cause thread**: a new tool
   (`rl_move/sim/probe_currentcap29_flatonly.py`) and corrected-physics
   re-eval of 5 intermediate snapshots found `s1` sits persistently
   near-zero/marginal for essentially its whole continuation — not
   smoothly declining from a good mid-run state — and closed the thread
   as "2/3-seed-general with large margins on the 2 passing seeds," `s1`
   a per-seed outlier not worth further GPU absent a new mechanism idea.
   This cycle independently pulled `s1`'s own raw training-time reward
   curves (zero-GPU, `wandb_history.csv`) as a smaller corroborating
   data point: a real anti-correlation between `env/max_current_a`
   (1.27A->1.58A over steps 9-13M) and `env/reward_task` (0.27->0.21),
   3-5x sharper than `s3`'s own drift over the identical window — a
   supporting signal for "persistently marginal," not a competing
   narrative, and not license for a new single-lever guess on its own.
2. **Exported both healthy full-budget checkpoints** (`s5-klrollback05-
   acq15m`, `s3-acq15m-lowlr`) to the robot's torch-free np-JSON runtime
   format (`export_policy_np.py --training-hz 50 --control-hz 50`, the
   SAFE 50Hz motor contract matching `bundle_50hz_v1`) — parity
   7.63e-08 / 9.45e-08 over 200 random obs (bar 1e-5), both green.
3. **`rl_docs/tracks/walkcurr/bundle_rlonly_stance_v1/transfer_manifest.json`**:
   names the candidate, checksums, the export, the SAFE motor contract,
   the own-cfg flat-only n=12 det+sto gate numbers (already on disk,
   `..._s5_klrollback05_acq15m_probe/report.json`, no new eval spend),
   and every open gap (no lower, no walk, s1's un-adopted third-seed
   drift) plainly.

## TODAY bars

- Clean `rl_only` training lineage (no BC/AMP/demo anywhere): PASS — every
  lever in this checkpoint's chain (`goal.joint_action_bias_*`,
  `--kl-rollback=0.05`, `--actor-lr/--critic-lr=1e-4`, `hold_grace_
  curriculum`) is task-reward/optimizer-stability/curriculum plumbing, not
  a demonstration, teacher target, or motion prior, per `tracks.json`'s
  walkcurr contract and RL_GOALS.md's Goal 2 allowances.
- Reproducible non-interactive sim video, 0 falls, no dragged/sacrificed
  legs: PASS for hold+rise (`..._probe/{hold,rise}_{det,sto}_*.mp4`,
  already on disk). NOT CLAIMED for lower (same clips show the known
  partial-descend-then-freeze pathology, included honestly, not hidden).
- Held-out gate (own-cfg flat-only n=12 det+sto): PASS for hold (12/12)
  and rise-flat (12/12) — both clear this track's own `hold>=10/12`/
  `rise-flat>=8/12` bar with margin. lower reads 0/12 (closed floor,
  matches every sibling — not part of this bundle's claim).
- Exportable to the robot's torch-free runtime: PASS, parity 7.63e-08.
- Seed generality: PARTIAL, now SETTLED not open — 2/3 seeds (s3, s5)
  consolidate at full budget with large reproducible margins; the third
  (s1) is CLOSED as a persistently marginal per-seed outlier (concurrent
  2026-09-17 ~11:0x finding, corroborated by this cycle's own reward-term
  read) and excluded from this bundle, not chased further absent a new
  mechanism idea.
- Single sit/rise/walk/lower bundle: NOT CLAIMED — stance role
  (rise+hold) only. `lower` is CLOSED pending Robot Lab achievability
  review; `walk` is a SEPARATE clean-RL lineage (`bundle_rlonly_v2`), not
  composed with this checkpoint. RL_GOALS.md explicitly allows composing
  separately-trained clean RL roles instead of requiring one monolithic
  actor — that composition (rise+hold handoff to walk-ready, then to the
  walk role) is untried and is the concrete next step, not built this
  cycle (a genuinely new integration piece, not a same-cycle add-on).
- Physical acceptance: NOT CLAIMED — no robot access from this process;
  any physical trial needs a manual/gantry lower/catch since this role
  cannot sit back down on its own.

## Next

1. **Cloud, agent-doable:** design and build the rise+hold -> walk-ready
   handoff (analogous to `todaypolicy`'s existing learned-stand -> walk
   -> learned-lower composition pattern, but chaining two independently
   trained `rl_only` roles instead of one `any_means` bundle) — this is
   the concrete integration step that would let a single joystick session
   demonstrate rise -> walk -> (manual/gantry catch) end to end on a
   fully clean-RL lineage. Not started this cycle (a real design/build
   task, not a launch).
2. **Cloud, agent-doable, lower priority:** if a genuinely new mechanism
   idea for `s1`'s current-creep or for `lower` itself is ever conceived
   (none is, as of this note — re-dosing anything already closed is
   prohibited), test it against the correlate captured here.
3. **Robot Lab:** the read-only preflight, then a bounded manual-start
   (hold from a hand-placed rise_flat pose) / manual-catch trial of this
   stance role alone, once queued through the guarded runner — this is
   NOT ordered by this cycle (physical work is Robot Lab's own serialized
   queue), just named as the natural next hands-on step.
