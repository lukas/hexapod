# standwalk STATUS journal archive — 2026-09-04w (verbatim, pre-triplecore-r2-verdict trim)

Update, 2026-09-04 ~03:5x (**`TripleGruActorCriticPolicy` (the 3rd-GRU-
core protected turn-tick lever item 2's banner scoped last cycle) is
now BUILT, fully unit-tested (26 new tests: architecture + CLI
validator + `--log-std-anneal-core turn`, all green; zero regressions
in `test_gru_policy.py`/`test_bc_anchor.py`/`test_gru_triple_cli.py`),
and LAUNCHED as a 2-seed canary against the `cap29-stdwalklo-hi`
control. First launch attempt crashed at 0 training steps on a
self-inflicted net_arch-derivation bug (caught cleanly by the
transplant's own shape check, no corruption); fixed same-cycle,
re-launched as `-r2`, both seeds VERIFIED RUNNING. Unread.**)

Built exactly per last cycle's scoped design
(`gru_policy.TripleGruActorCriticPolicy`: `core_a` walk/quad unchanged,
new `core_t` pure-turn with its own actor/critic/log_std head, `core_b`
stance byte-for-byte unchanged from Dual's contract; 3-way gate off the
frozen `MODE_ONEHOT_ORDER` tail). `gru_policy.dual_to_triple_transplant`
copies `core_b` verbatim and `core_a` into BOTH `core_a` and `core_t`
(turn starts as a copy of the current combined-tuned walk core, fresh
optimizer state). `bc_anchor._dual_core_param_groups` extended to a
generic 3-way `"a"/"t"/"b"/"shared"` classifier (both call sites —
`_gradnorm_diag_ctx`/`_percore_clip_ctx` — reworked to iterate an
arbitrary group set instead of a hardcoded `{a,b,shared}` dict, so
`bc_anchor_isolate_update`/`bc_anchor_percore_clip` stay correct on a
Triple policy without a silent misclassification). New CLI
`--gru-triple` (`train_ppo_mjx.py`): warm-start-only (requires
`--init-from` a Dual checkpoint + `obs.mode_onehot=1,
obs.mode_onehot_turn_cmd=1`; refuses `--gru-dual`/`--gru-experts`/
actor-only/policy-backbone transplants), builds a fresh Triple policy
and calls the transplant. Per the banner's own mitigation, `yaw_critic.py`
was NOT touched — the first canary drops `train.yaw_credit_coef`/
`_vf_coef`/`_grad_clip` and the Dual-only `log_std_split`/
`--log-std-anneal-core` mechanism entirely (warm-starting FROM a
yaw-credit-trained checkpoint is fine, yaw_credit is training-time
only) so this read isolates the core-split's own effect. Test bank:
`test_gru_policy.py` (slots/routing/3-way gradient isolation/save-load/
bptt/bc_anchor+detach_trunk/log_std_core targeting/transplant
correctness incl. a byte-equality + forward-match check) +
`test_gru_triple_cli.py` (validator + `--help` wiring +
`--log-std-anneal-core turn` parsing).

**Self-inflicted bug, caught and fixed same cycle:** the first launch
(`cap29-stdwalklohi-triplecore{,-s1}`) crashed at 0 steps —
`dual_to_triple_transplant`'s own shape check refused cleanly
(`mlp_extractor.policy_net.0.weight (64,256) -> (128,256)`): this
specific Dual lineage's checkpoints were built with `net_arch=None`
(SB3's own pre-`--net-arch`-flag default, `{'pi':[64,64],'vf':[64,64]}`)
while the fresh Triple construction blindly used the CLI's `--net-arch`
default `[128,128]`. Root cause: the new `--gru-triple` branch built a
FRESH policy using CLI defaults instead of the loaded checkpoint's OWN
resolved geometry (a plain `--init-from` warm start gets this for free
via `algo_cls.load()`; this branch builds a different policy class so
must reproduce it explicitly). Fixed: derive both `net_arch` and
`lstm_hidden_size` from the already-loaded `old.policy` object, never
from CLI defaults. Both entries marked FAILED in the ledger (0 GPU
budget lost beyond ~1 min of vec-env compile); relaunched as `-r2`,
both VERIFIED RUNNING within the same cycle. No corruption, no
retraining from a bad state — the transplant's fail-closed shape check
did exactly its job.

Gate (unread, 2M-step canary each):
`probe_turn_authority.py --vx-cmds` combined-tick `wz_med` must beat
`cap29-stdwalklo-hi{,-s1}`'s own combined comparator on BOTH signs
WITHOUT a pure-turn `wz_med` regression >10% vs the same control and
without new DR-0 walk-only terminations — the identical bar the whole
8/8-FAIL open-loop family was held to, so this is apples-to-apples
with that closed family. A PASS here would be the first mechanism in
this whole campaign to win combined-tick turn authority without
blowing the pure-turn cap.

Prior banner (the full `combdose0p6-s1-r3` FAIL verdict closing the
whole 8/8 open-loop lever family, plus the `TripleGruActorCriticPolicy`
design this cycle executed) moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-04v_trim.md`.
