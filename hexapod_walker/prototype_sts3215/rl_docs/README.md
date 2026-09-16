# rl_docs — index (read this first, then only what you need)

Small, single-purpose files so no one (human or LLM) has to dig
through a 5,000-line log to answer a question. Each file says what
it is for; keep them SHORT when you edit them.

The two walking goals, each demonstrated in sim and physically, are defined
in `RL_GOALS.md` of https://github.com/lukas/hexapod-orchestrator (the
autonomous orchestrator, its rules and its state live there): progress
by any effective means, alongside walking learned entirely through RL with
no demonstrations. Eight method tracks live in
`orchestrator/tracks.json` (hexapod-orchestrator): `joystick`, `amp`, `cpg`, `standwalk`,
`assistfade`, `todaypolicy`, `speed` serve `any_means`; `walkcurr` serves
`rl_only`.
Method PASS is not parent-goal completion. Superseded docs were retired 2026-09-14 (git history before that commit).

| File | What it answers | When to read |
|------|-----------------|--------------|
| `RL_GOALS.md` (hexapod-orchestrator root) | The two goals, sim demos, physical evidence, demonstration boundary and priorities | Every cycle, first |
| `CURRENT_TRUTHS.md` (orchestrator state) | Accepted facts and run verdicts; RL_GOALS owns purpose/priorities | Every cycle |
| `RL_PLAN.md` (hexapod-orchestrator root) | The plan for physical delivery and demonstration-free research in parallel | Every cycle |
| `STATUS.md` (hexapod-orchestrator root) | Operator-facing digest: how it's going, what's waiting | Catching up; after any story-changing verdict (update it!) |
| `tracks/<track>/STATUS.md` | Per-track Goal/Now/Next journals: orchestrator STATE (`.state/rl_docs/tracks/` in lukas/hexapod-orchestrator); design notes and bundles stay here | Working that track |
| `AMP_LOCOMOTION.md` | The AMP method charter within any_means (incl. repo adaptations — no Isaac Lab) | Before any amp-track design decision |
| `DOWNLOAD_ANSWER.md` | The current deployable answer + gate evidence | When a verdict might change what we'd put on the robot |
| `HYBRID_DEMO.md` | How to compose stand/walk/lower controllers with explicit states and compare transfer-shaped MuJoCo demos | When judging policy+state bundles for robot transfer |
| `DEPLOYABLE_POLICY_EXPORT.md` | W&B/SB3 checkpoint to portable MLP or persistent dual-GRU JSON; exact obs-75/81 layouts and parity checks | Exporting or reviewing a model for MuJoCo/robot runtime |
| `HARDWARE.md` | Real-robot evidence, sim2real findings | When a decision hinges on real-world data |
| `../docs/GAIT_SIM_VS_HARDWARE_2026-09-11.md` | Every gait run on hexapod 1 and 2 vs its MuJoCo version: speed, stride Hz, amplitude, tracking, tilt; per-row sim model family | Before claiming anything about sim-to-real transfer of a gait; pair with `sysid/gait_metrics.py` |
| `SIM.md` | What the physics sim models, actuator numbers, DR coverage | Before touching sim params/DR or judging sim-vs-real gaps |
| `REWARD.md` | Every reward term: cfg key, default, what it pays/charges, income-gate design rules | Before adding/changing any reward term |
| `EVALS.md` | Every eval metric: `SCORE/*` names, `eval/*` details, harnesses, caveats | Reading a W&B page or wiring a new metric |
| `GAIT.md` | Anti-paddle gait quality: lift-and-place metrics, known exploits | Judging walking video; designing gait rewards |
| `FAST_PROFILE.md` | Raised servo profile facts + command-tracking prep | Fast-gait arms on the joystick track |
| `COMPLIANCE.md` | Structural-compliance measurement + sim hook | Sim-fidelity questions |
| `EXPERIMENT_LOGS.md` | Per-run `logs/experiments/<run>/` convention (dig-ins) | When digging into a run |
| `WANDB.md` | How W&B is wired: project/creds, ops.sh readers, gotchas | First time touching W&B or on auth failure |
| `RESEARCH_RULES.md` + `RUN_INTERPRETATION_RULES.md` (hexapod-orchestrator root) | How to design, launch, continue, and judge runs (incl. the 08-21 reward/eval ruling) | Before launch/triage |
| `orchestrator/guardrails.yaml` (hexapod-orchestrator) | Hard limits you must obey | Every cycle |

Standing rule: if you had to FIGURE OUT a command (it failed, was
slow, or took several tries) and then got it right, promote it —
add an `ops.sh` subcommand or a snippet to `COMMANDS.md` in lukas/hexapod-orchestrator, in the
same cycle, and keep this index accurate. The next agent should
never have to rediscover it.
