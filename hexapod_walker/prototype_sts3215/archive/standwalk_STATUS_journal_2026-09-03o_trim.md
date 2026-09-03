# standwalk STATUS journal archive — 2026-09-03o

VERBATIM copy of the two most-recent Update blocks (19:1x rise-stall
close + branch-(a) refute, and the pointer to 09-03n) as they stood
before the 2026-09-03 ~20:2x idle-kick cycle that built the
combined-tick yaw-boost harness and launched its canary batch.

Update, 2026-09-03 ~19:1x (**Next item 2, branch (a) 4-ARM CANARY
BATCH COMPLETE — ALL 4 FAIL; branch (a) REFUTED. Next item 1
(rise-stall faithful replay) CLOSED same cycle, with a mesh/primitive
model-family test-harness bug fixed along the way.**)

**Item 2 (steering, top item):** all 4 omega-boost canary cells now
read (`cap29-stdwalklohi-omegaboost{1p5,2p0}{,-s1}`, 2 doses x 2
seeds, concurrent cycles): FAIL/FAIL/FAIL/FAIL. Every cell reproduces
the SAME sign-asymmetric signature already seen in `combskip`: the
negative-wz combined-tick side clearly beats the pre-registered
comparator (+57-61% magnitude) but the positive side falls short
(does not beat +0.145 rad/s), AND pure-turn wz_med regresses >10% vs
the matched control on BOTH signs in every cell (10-25%, not dose-
monotonic — 1.5-s1 regressed worse than 2.0-s0). Conclusion: the
scripted-teacher-level authority gain from `train.bc_anchor_
teacher_omega_boost` (proven zero-training on the SCRIPTED teacher
itself) does NOT survive PPO fine-tuning into a real, symmetric
combined-tick wz gain on the RL checkpoint — it trades pure-turn
authority for a lopsided partial gain, 4/4 cells, 2 independent
mechanisms now (`combskip`, `omegaboost`). **Branch (a) is REFUTED.**
Per the pre-registered fallback, the remaining candidates are (i) the
`tripod_gait.py` class-level combined vx+omega foot-target geometry
edit (shared hardware-adjacent code — needs its own before/after
validation harness before any launch) or (ii) a combined-tick-
targeted course/yaw reward term (needs a `test_task_semantics.py`
bank entry pinning the exploit before any launch, per RESEARCH_RULES).
Neither is launch-ready yet — this is the track's next NEW-CODE item.
Evidence: `logs/ckpt_eval/probe_turn_authority_omegaboost{1p5,2p0}_
{s0,s1}_combined_09-03.json`, `..._cap29_stdwalklo_hi{,_s1}_combined_
09-03.json`; ledger verdicts on all 4 run names.

**Item 1 (rise-stall, CLOSED):** finished the faithful-replay twin
(`test_task_semantics.py::test_rise_stall_replay_*`, built off the
real `yawdensity_s1_riseAB_cap29cf` silent-stall trace). Two findings:
(1) **A REAL BUG, now FIXED**: the replay ran on `conftest.py`'s
session-pinned `HEXAPOD_MODEL_SOURCE=primitive` the whole time,
silently ignoring its own `env.model_source: mesh` cfg override
(`resolve_model_source()` checks the env var first, unconditionally)
— the hand-built bank above it had the SAME latent bug but happened
to still pass qualitatively either way since it's purely comparative;
the faithful replay diverged wildly (wrong mass family) until wrapped
in a new `_mesh_family_env()` context manager (now applied to both
banks). (2) Once genuinely mesh-family, the replay **does not fully
confirm the hand-built twin's story**: the real recorded "stall" ends
up HIGHER (h_end 29.3mm) than an early-frozen "partial" hold
(19.4mm) — the opposite of the synthetic +40deg-offset twin's height
ranking — because the real fight keeps inching upward the whole
episode while a frozen hold sags. The TRUE distinguishing signature
is duration at dangerous current, not final height: real stall
sustains >2A for ~25/30s vs partial's ~1s (`over2A_s`), and the
pricing gap survives but shrinks (partial beats stall by ~82pts/30s,
not the hand-built twin's larger margin). Tests recalibrated to match
measured reality (not re-inflated to match the synthetic version), per
the twin's own pre-written instruction to trust the faithful replay
over the hand-built one on disagreement. Net effect: the height-
ranking half of the rise-stall reward-fix motivation is retracted;
the current-duration half still stands. No reward change made yet —
a future rise-stall fix should price sustained near-ceiling current
directly (matching `over2A_s`), not a stall-vs-partial-height
framing. 4/4 replay tests green; full `-k rise`/`-k steer` reruns
green (18 tests). Snapshot `54cb4765`
(`exp/standwalk-risestall-replay-mesh-family-fix-09-03`).
