# assistfade — pragmatic assistance-removal walking curriculum

## 09-07 ~04:3x (refill; 11/11 GPU free, backlog empty) — `s0-longbudget` VERDICTED, closes rung 3's budget/schedule lever family 2/2 (6 arms total): rung 3 is now FULLY CLOSED

The `s0-longbudget` DIG-IN had sat FINISHED-but-unverdicted since
09-06 ~19:36 (flagged ambiguous/fork-deciding at ~19:6x, re-flagged at
~20:1x, still open as of the ~20:2x doc-sync — no deep-model cycle
had actually landed a verdict on it across many subsequent
cycles). Read it fresh myself (report.json + the `walk_det_0_sheet.png`
frame strip): `walk/det` `progress_ratio` medians **0.274, BELOW the
0.35 bar** (the earlier "closer than any prior lever" framing compared
it only to worse siblings, not to the bar itself), `gait_valid` FALSE
with leg-5 chronically sacrificed in every episode (identical
`duty_cycle`/`swing_count` fingerprint across all 6), and EVERY
`walk/det` episode terminates via `over_current` at `forward_dist_m`
=0.024 (near-zero net translation) with `roll_class=fell`. The frame
strip confirms a stall: body stays essentially planted while legs
shuffle, until the current cutoff on the last sampled frame — the
"partial improvement" read was real relative to worse siblings but
does not cross the ignition bar. **Verdicted CANARY FAIL - MECHANISM,
matching its `s1` twin — rung 3's budget/schedule lever family is now
closed 2/2 (stdslow 2/2, latehandover 2/2, longbudget 2/2 = 6 arms,
zero clean passes).** Per the ladder's own retreat rule (rung 1 and
rung 2 already closed, rung 3 now closed too), the next licensed step
is rung 4 (phase/contact only), which this doc's own binding rule
gates on building "a reverse curriculum + matched intermediate-state
bank" FIRST — not started this cycle (out of scope for a single
refill pass), named here as the concrete next design/build task for
whoever picks this track back up. No new launch on this track this
cycle (the gap is a build task, not a same-cycle-relaunchable arm).
Evidence: `ops.sh review cw-assistfade-rung3-residualfade-s0-longbudget`,
`logs/ckpt_eval/cw_assistfade_rung3_residualfade_s0_longbudget_gate/
{report.json,walk_det_0_sheet.png}`, W&B `1nt19pgb`, RL_LOG 09-07 04:36.

## 09-06 ~20:2x — doc-sync only: all 3 assigned rung3-fallback reports already verdicted by concurrent cycles, no duplicate written

**Assigned this cycle**: `cw-assistfade-rung3-residualfade-s1-latehandover_gate`, `-s0-latehandover_gate` (explicitly another concurrent cycle's, per brief — not touched), `-s1-longbudget_gate` (also explicitly another concurrent cycle's — not touched). Independently re-pulled the ledger entry for the one in-scope run (`ops.sh entry cw-assistfade-rung3-residualfade-s1-latehandover`) fresh: it already carries `status: FAIL`, verdict text word-for-word matching RL_LOG 09-06 20:03 (`CANARY FAIL - MECHANISM`, prog med 0.01-0.06 across modes, essentially unchanged from the un-fixed parent despite rising reward, t1_steps=1.7M lever closed 2/2 seeds) — confirmed against the `report.json` figures named in that verdict, no discrepancy, **no re-verdict written (would duplicate)**. The other two named reports are likewise already landed and verdicted (`-s0-latehandover` FAIL - MECHANISM RL_LOG 20:04, `-s1-longbudget` FAIL - MECHANISM RL_LOG 20:06) — left untouched per the brief's explicit ownership note, spot-confirmed via `ops.sh entry` only to make sure nothing regressed, not re-verdicted.

**Refill check (no duplicate launch)**: rung 3's fallback grid is now 3/4 arms cleanly closed (stdslow 2/2, latehandover 2/2, longbudget-s1) with exactly one open thread — `cw-assistfade-rung3-residualfade-s0-longbudget` — still sitting `status: FINISHED`, no verdict field, per its own `ops.sh entry` re-check this cycle (still the pre-existing DIG-IN: ambiguous partial pass, chronic leg-5 sacrifice riding on genuinely-better progress numbers). Per the standing rule ("do not treat longbudget as a refuted lever until s0's dig-in lands"), no 5th rung-3 arm is licensed yet. Full board re-confirmed fresh (all 6 STATUS docs read this cycle, not just assistfade's): joystick/amp/cpg DONE/maintenance-only, standwalk blocked on fresh design thinking, todaypolicy delivered with its own open arcaware bug already a different track's lead, walkcurr's only open item (footslip-c1 tangent-charge) already closed pending unscoped contact-independent-mechanism design — none of these are a same-cycle-relaunchable arm. `launch_run.py status`: 11/11 reachable GPU pods free, zero live trainers; `backlog.json` empty. Genuinely idle-with-one-open-DIG-IN, not idle-next-to-runnable-work — no launch made this cycle, `CYCLE_WORKED` not touched (pure confirmation, no triage/launch/code landed).

Evidence: `ops.sh entry cw-assistfade-rung3-residualfade-s1-latehandover`, `ops.sh entry cw-assistfade-rung3-residualfade-s0-longbudget`, `launch_run.py status`, RL_LOG 09-06 20:03/20:04/20:06 (prior cycles' verdicts, confirmed not duplicated).

## 09-06 ~20:1x (previous cycle) — `-s1-longbudget` landed + VERDICTED CANARY FAIL - MECHANISM (clean, unambiguous); budget lever now reads 1 clean FAIL + 1 still-open DIG-IN, NOT 2/2 closed

**This cycle's assigned run** (`cw-assistfade-rung3-residualfade-s0-stdslow`'s gate) arrived already fully verdicted by a concurrent cycle before this cycle started (`CANARY FAIL - MECHANISM`, RL_LOG 09-06 19:31, doc-synced 19:41) — independently re-read `ops.sh review` fresh and confirmed the match (walk/det gait_valid 0/6, leg 1 chronically sacrificed, prog med 0.06 vs bar 0.35), no re-verdict written (would duplicate). Also found the leave-alone list stale by the time this cycle actually ran: `-s1-latehandover` and `-s1-longbudget` (marked "still training" in this cycle's brief) had both already finished their full budgets and handed off to the deferred-artifacts CPU finalizer (confirmed via `ops.sh handoff` — `phase: evaluated`, 3/3 snapshots delivered — and via `kubectl exec ps`, zero trainer processes on train-0/1/2, `launch_run.py status` showing all 11 reachable GPU pods free). Kicked `ops.sh podeval` for the 3 arms that had no eval running yet (`-s0-latehandover`, `-s1-latehandover`, `-s1-longbudget` — `-s0-longbudget`'s eval was already running, started by a concurrent cycle); `-s0-latehandover`/`-s1-latehandover` landed and were verdicted by a concurrent cycle in parallel (see the ~20:1x entry directly below, already in this file) before this cycle's own eval finished — no duplicate written for those two, confirmed by fresh re-read.

**`-s1-longbudget` (this cycle's own read, verdicted CANARY FAIL - MECHANISM):** held-out gate progress_ratio med 0.10/0.09/0.10/0.14 across walk/det, walk/sto, startjitter/det, startjitter/sto — every mode 2.5-3.5x short of the 0.35 bar, no submode median close (contrast with the `s0` twin, where `startjitter/det` med individually crosses 0.48). Paddle-creep signature (gait_valid mostly True, slip/m 17-18, fwd only ~0.05-0.06m/10s) in walk/det+sto; startjitter reintroduces chronic leg sacrifice + over_current in 2/6 det, 2/6 sto (one high-progress episode, sto/1 at 0.73, is the SAME episode that sacrifices 2 legs and terminates over_current — a transient pre-failure burst, not sustained translation, not a partial pass). Reward quarters `[146.5,76.3,32.7,31.3]` are a clean Q1->Q4 decline, matching the collapse-with-more-budget shape, so 08-21's continue-reading does not apply. **This closes the budget lever for seed 1** — but the s0 twin remains DIG-IN (ambiguous partial improvement, `startjitter/det` genuinely crossing the bar on one submode while gait_valid/over_current still fail hard), so **the pair reads 1 clean FAIL + 1 unresolved DIG-IN, not a closed 2/2** — do not treat "longbudget" as a refuted lever until s0's dig-in lands. **Re-flagging `cw-assistfade-rung3-residualfade-s0-longbudget` for DIG-IN** (already flagged by a concurrent cycle at ~19:6x below, still unverdicted as of this cycle's end) since it is the one genuinely open, fork-deciding read left in rung 3: does the chronic single-leg (leg 5) sacrifice on an otherwise-improving budget lever indicate a fixable per-leg-utilization defect (worth a targeted per-leg pricing fix) or does it confirm the mechanism itself needs re-examination now that all 3 named schedule-hyperparameter levers (stdslow x2, latehandover x2, longbudget-s1) are refuted.

No code changes this cycle. Full board re-checked fresh: joystick/amp/cpg DONE/maintenance-only, standwalk blocked pending fresh design thinking (no agent-doable next step), todaypolicy DELIVERED with its own Next list closed, walkcurr's only open item (foot-slip magnitude, item(4)) closed for the tangent-charge lever with next step unscoped contact-independent mechanism design (not a relaunchable arm). `backlog.json` empty; all 11 reachable GPU pods free at cycle end (own-pod CPU evals just finished, no GPU trainers running) — genuinely idle-with-empty-queue for any NEW arm this cycle could responsibly launch (the two open threads — s0-longbudget's DIG-IN and walkcurr item(4)'s fresh mechanism design — are not substitutable by a same-cycle relaunch). `CYCLE_WORKED` touched (verdict + eval kicks landed).

Evidence: `ops.sh review cw-assistfade-rung3-residualfade-s1-longbudget`, `logs/ckpt_eval/cw_assistfade_rung3_residualfade_s1_longbudget_gate/report.json`, `ops.sh handoff cw-assistfade-rung3-residualfade-{s0,s1}-latehandover cw-assistfade-rung3-residualfade-s0-longbudget`, W&B `j8l8va6k`, RL_LOG 09-06 20:06.

## 09-06 ~20:1x — BOTH `-latehandover` seeds landed and VERDICTED: CANARY FAIL - MECHANISM 2/2, `t1_steps=1.7M` lever CLOSED; surviving fork is budget (`-longbudget`)

Both gates finished mid-cycle (shortly after being registered via `evalpending` below) and were verdicted fresh: **`-s0-latehandover`** (prog med 0.09-0.12 across all 4 modes, essentially unchanged from the un-fixed parent's own 0.11-0.12; walk/det gait_valid 6/6 but only 0.05m/10s forward with slip/m ~20 -- a near-static shuffle, not real translation; startjitter still shows chronic 1-2-leg sacrifice + over_current in 4/6 det, 2/6 sto) and **`-s1-latehandover`** (prog med 0.01-0.06, if anything *worse* than its own parent's 0.03-0.06; video `walk_det_0_sheet.png` confirms the body stays essentially in the same on-screen position across all 6 sampled frames while legs shuffle/slip in place; startjitter same chronic-sac+over_current fingerprint, 4/6 det terms). **Both CANARY FAIL - MECHANISM.** Reward-trend note (checked per 08-21 before verdicting, not overridden): `-s0-latehandover` rose then mildly declined ([101.4,189.8,293.2,228.3]), `-s1-latehandover` genuinely kept RISING through Q4 ([100.9,180.6,244.7,249.7]) -- unlike `-stdslow`'s clean declines, this is NOT an unambiguous collapse-shape. But the held-out numbers are the deciding evidence, not the reward shape: neither seed shows ANY measurable held-out improvement over the already-failed parent despite the rising curve, so rising reward here is not converting into progress at all (closer to "misaligned/still doesn't move the gate" than "just needs longer") -- especially telling since the SAME schedule-collision root cause's OTHER named lever (`-longbudget`, 3x the steps) already produced a real partial gain on `s0` (prog 0.27) at matched effort, so budget -- not handover timing -- is the lever that's actually moving the needle. **This closes `sched.t1_steps=1.7M` (later handover) as a repair lever for rung 3, 2/2 seeds each seed independently, 4 total data points on this schedule-collision problem now refuted by the two schedule-shape levers (`stdslow` 2/2, `latehandover` 2/2)** -- do not relaunch either schedule-shape tweak again. The one surviving, not-yet-closed fork is the budget lever: `s0-longbudget` (DIG-IN flagged, partial improvement, unread) and `s1-longbudget` (gate still computing on train-0, registered via evalpending) -- read both before deciding rung 3's next step (accept the budget lever if it holds 2/2, or escalate to a genuinely new mechanism if it doesn't). No new arm licensed this cycle (rung 3's grid isn't fully read yet -- `s1-longbudget` pending). Evidence: `logs/ckpt_eval/cw_assistfade_rung3_residualfade_s{0,1}_latehandover_gate/{report.json,walk_det_0_sheet.png}`, W&B `pk0m0c97`/`50v1xsls`, RL_LOG 09-06 20:03/20:04.

## 09-06 ~20:0x — assigned run `-s1-latehandover`: gate still computing on-pod, registered via evalpending (not idle-next-to-runnable-work)

**This cycle's assigned run** (`cw-assistfade-rung3-residualfade-s1-latehandover`, finished training, W&B `50v1xsls`, reward quarters `[100.9,180.6,244.7,249.7]` — a real Q1->Q4 RISE, unlike every prior rung-3 lever's decline, worth flagging for whoever reads its gate) had only the informational SESSION eval prestaged (INCOMPATIBLE, expected for this exotic-obs candidate) — the DR-0 held-out ignition gate was not yet synced. `ops.sh podeval` confirmed it (and the checkpoint) already correctly picked up by a concurrent cycle's earlier launch and was already RUNNING remotely on train-2 (started ~19:48, still mid-panel at cycle time, `video-every=1` x 24 episodes). Per the no-blocking rule, did not poll/sleep on it — registered it (plus its two still-computing siblings, `-s0-latehandover` on train-0 and `-s1-longbudget` also on train-0, neither of which had a `pending_evals.json` entry yet despite both confirmed live via `kubectl exec ps`) via `ops.sh evalpending add` so the watcher auto-spawns the next reader the moment each report.json lands, instead of leaving them to rot uncollected. This completes mechanical tracking for all 4 rung-3 fallback arms (`s0-longbudget` already DIG-IN-flagged/unverdicted per the ~19:6x entry below; these 3 are the remaining reads).

No verdict possible yet (gate not landed), no code changed, no new launch: rung-3's own fallback grid is fully in flight (4/4 arms, this cycle's contribution was closing the "orphaned, uncollected eval" gap on 2 of them) and licenses no 5th arm until at least the DIG-IN'd `s0-longbudget` gets its deep read. Full board re-confirmed: joystick/amp/cpg DONE/maintenance, standwalk blocked on design, todaypolicy delivered (its own open arcaware course-tracking bug is a different lead, not this track's), walkcurr's only open item (item(4) foot-slip) closed pending unscoped contact-independent-mechanism design (RL_LOG 09-06 19:14) — not a relaunchable arm. 11/11 reachable GPU pods free, backlog empty — genuinely idle-with-in-flight-arms, not idle-next-to-runnable-work. `CYCLE_WORKED` not touched (bookkeeping/registration only, no triage/launch/code landed).

Evidence: `ops.sh review cw-assistfade-rung3-residualfade-s1-latehandover`, `logs/experiments/cw-assistfade-rung3-residualfade-s1-latehandover/wandb_summary.json`, `rl_move/orchestrator/pending_evals.json`, W&B `50v1xsls`.

## 09-06 ~19:6x — `-s0-longbudget` gate landed: PARTIAL IMPROVEMENT over every prior lever, NOT a clean pass -- DIG-IN flagged, left UNVERDICTED (gate/video read is ambiguous, a fork-deciding result)

`-s0-longbudget`'s held-out gate (`logs/ckpt_eval/cw_assistfade_rung3_residualfade_s0_longbudget_gate/report.json`, dr=0.0) landed mid-cycle: walk/det prog med **0.27** (bar 0.35 -- closer than any prior lever: stdslow's 0.03-0.06, the original pair's 0.03-0.12), `walk_startjitter/det` prog med **0.48** (ACTUALLY CROSSES the 0.35 bar on its own), individual episodes up to 0.67. But `gait_valid` is still 0/6 in walk/det AND walk/sto (only 2/6 in startjitter/sto) -- EVERY walk/det episode identically shows leg **5** chronically sacrificed (same deterministic single-leg-parked signature across all 6 episodes, not course-dependent), and over_current fires in 22/24 episodes total (down from 24/24 stdslow but still near-universal). Contact sheet: body visibly translates/rotates with real forward+turning motion (unlike the frozen-splayed stdslow pose), but one rear leg stays rigidly extended off the ground the whole clip.

**This is neither a clean pass nor the same failure shape as the two already-closed levers** -- raw progress numbers roughly DOUBLED-TO-QUADRUPLED and one sub-mode now individually exceeds the bar, but the gate's chronic-single-leg-sacrifice and over_current bars still fail hard. Reward quarters `[161.5, 70.4, -96.1, -34.5]` are a decline-then-partial-recovery, not a clean rise, so the 08-21 "continue" reading isn't a clean fit either. This is exactly a fork-deciding, gate/video-partial-disagreement result (the pre-registered gate text's "if this ALSO fails the same way" branch does NOT cleanly apply -- it isn't the same way) -- **flagged DIG-IN rather than snap-verdicted**; a deep read should trace whether leg 5's chronic parking is a fixable per-leg-utilization artifact (same family as the walkcurr sde leg-sacrifice diagnosis) riding on top of an otherwise-improving budget lever, before deciding whether rung 3 needs a 4th schedule tweak, a per-leg pricing addition, or the mechanism itself re-examined. `-s1-longbudget` finished training this cycle too (reward quarters `[146.5,76.3,32.7,31.3]`, same decline-then-partial-recovery shape) -- its own gate eval was still computing on train-0 as this cycle closed; read both together, not this one alone.

Evidence: `logs/ckpt_eval/cw_assistfade_rung3_residualfade_s0_longbudget_gate/{report.json,contact_sheet.png}`, W&B `1nt19pgb`/`j8l8va6k`.

## 09-06 ~19:5x — rung-3 longbudget PAIR now both mechanically launched (s0 already FINISHED its 6M budget, s1 running); gate eval kicked on-pod for s0

**This cycle's own assigned run** (`cw-assistfade-rung3-residualfade-s1-stdslow`) verdicted first: **CANARY FAIL - MECHANISM** (std-anneal-frac lever REFUTED, 24/24 eval episodes over_current, prog med 0.03 vs bar 0.35 -- RL_LOG 09-06 19:31). Found its sibling `-s0-stdslow` still unverdicted (status=FINISHED, no verdict field) despite the parent-pair verdict already covering the mechanism-collision story; verdicted it too rather than leave a same-question sibling hanging: **CANARY FAIL - MECHANISM** (walk/det gait_valid 0/6, leg 1 chronically sacrificed every episode, prog med 0.06 vs bar 0.35; contact sheet shows a frozen splayed pose, zero forward translation -- RL_LOG 09-06 19:31/19:29 order). Confirms std-anneal-frac CLOSED 2/2 seeds -- the note a concurrent cycle's ~19:4x entry above already independently reached reading the same two reports.

**Per the pre-registered fallback (do not repeat log-std-anneal-frac; retreat is either later `t1_steps` or a longer total budget), launched the BUDGET half of that fork** (a different concurrent cycle independently launched the `t1_steps`-later half as `-{s0,s1}-latehandover`, see the ~19:4x entry above -- both named options are now covered, not a duplicate): `cw-assistfade-rung3-residualfade-{s0,s1}-longbudget`, `respec --from` the ORIGINAL failed pair (not the refuted stdslow variants), single lever `--steps` 2M->6M with `--log-std-anneal-frac` reverted to the original default 1.0/-3.0 (the refuted lever, not compounded) and every other byte (blend schedule `sched.t1_steps=1.4M`, reward stack, random-weight init) unchanged. First attempt correctly REFUSED by the launcher (canary phase caps at 2M); re-launched `--phase acquisition` with `--evidence` naming the mechanism's own bank-proof (`test_assistfade_rung3_*`) plus both original canaries' real mid-training six-leg gait as the justification for more budget, same MECHANISM-HEALTH ignition gate text (not graded as skill acquisition).

- `-s0-longbudget`: VERIFIED RUNNING on train-1, then **FINISHED its full 6.05M-step budget within this same cycle** (W&B `1nt19pgb`, fps~18k) -- reward quarters `[161.5, 70.4, -96.1, -34.5]`, a Q1->Q4 DECLINE (161.5 down to -34.5), the same qualitative collapse-with-more-budget shape as the stdslow retry, not a rising-reward "needs to go longer" case. No harness gate report yet (finished mid-cycle, watcher hasn't prestaged it) -- kicked `ops.sh podeval` on train-1 myself this cycle; left UNVERDICTED for the next reader (own eval still computing as this entry is written, do not re-run).
- `-s1-longbudget`: VERIFIED RUNNING on train-0, still training (~4.87M/6M at last check, reward quarters so far `[141.3, 115.6, 20.4, ...]` -- same declining shape emerging). Leave for the next reader once it finishes; do not duplicate-launch.

**Reward-quarter shape is already a bad early sign** (declining, not rising, through the extended budget) -- per the 08-21 ruling this would need rising reward to license a "continue" read; a declining reward through 3x the settling budget instead points toward the SAME schedule-collision reasserting itself once blend saturates, regardless of how much settling time follows, rather than budget being the missing ingredient. Held for the harness verdict (progress/gait_valid/over_current), not prejudged here.

No code changes this cycle. Capacity re-checked after both launches: 10/11 reachable GPU pods free (`train-0` busy with `-s1-longbudget`), `backlog.json` empty -- every other track re-confirmed unchanged from the concurrent ~19:4x entry's read (joystick/amp/cpg DONE/maintenance, standwalk blocked on design, todaypolicy delivered/closed, walkcurr's only open item already closed for its tangent-slip lever with next step unscoped design work) -- not idle-next-to-runnable-work, the genuinely open next step (rung 3's 3rd/4th fallback verdicts) is real compute already in flight, not a same-cycle relaunch substitute. `CYCLE_WORKED` touched (two verdicts + two launches landed).

Evidence: RL_LOG 09-06 19:29/19:31, `ops.sh entry cw-assistfade-rung3-residualfade-{s0,s1}-longbudget`, `logs/experiments/cw-assistfade-rung3-residualfade-s0-longbudget/wandb_summary.json`, W&B `1nt19pgb`/`j8l8va6k`.

## 09-06 ~19:4x — doc-sync only: stdslow pair confirmed FAIL 2/2 (already verdicted by a concurrent cycle before this one started); BOTH named fallback levers (later handover, longer budget) now mechanically verified launched, one already finished

**Assigned this cycle**: triage `cw-assistfade-rung3-residualfade-s0-stdslow` (finished; `-s0-latehandover` on the leave-alone list as still-training; `-s1-stdslow` owned by a concurrent cycle). Found the ledger already carried a full verdict (`CANARY FAIL - MECHANISM`, RL_LOG 09-06 19:31) written by a concurrent cycle before this one started — independently re-read `ops.sh review` fresh (walk/det gait_valid 0/6, leg 1 chronically sacrificed in every episode; walk/sto 0/6 with 5/6 over_current terms; startjitter partial-recovery 3-4/6 same as parent) and confirm it matches: std-anneal-frac REFUTED 2/2 seeds (s1-stdslow also FAIL, RL_LOG 19:29), no new evidence, no re-verdict written (would be a duplicate).

**Both of the track's own pre-registered fallback levers for this schedule-collision are now mechanically confirmed in flight, not just claimed** (`launch_run.py status` + `kubectl exec ps`, not ledger status alone):
- `-s0-latehandover` (single lever: `sched.t1_steps` 1.4M->1.7M, later/gentler handover, canary-phase 2M cap) — already **finished its full budget** (train-0 freed up mid-cycle) and is now past the trainer into the deferred-artifacts CPU finalizer (`artifact_finalizer --handoff-dir .../cw-assistfade-rung3-residualfade-s0-latehandover`, confirmed live via `ps`). Gate eval not yet kicked — next reader: `ops.sh handoff` then `ops.sh podeval` once the finalizer completes.
- `-s0-longbudget` (single lever: total budget 2M->6M, graduated to `--phase acquisition` after a first `--phase canary` attempt was correctly REFUSED by the launcher for exceeding the canary step cap) — confirmed **RUNNING** on train-1 (global_step climbing, ~2.26M/6M at last check).
- `-s1-latehandover` (same later-handover lever, seed 1) — confirmed **RUNNING** on train-2, launched/owned by the concurrent cycle handling the `-s1` side; no `-s1-longbudget` counterpart exists yet (not this track's gap to fill without risking a duplicate — leave to whichever cycle reads `-s1-latehandover`'s result).

No code changed, no new run launched by this cycle (everything above was already actioned by concurrent activity before/during this cycle; duplicating any of it would violate the launcher's own dedup and waste GPU-cycle bookkeeping). Full board rechecked fresh: joystick/amp/cpg remain DONE (sim scope)/maintenance-only per their own STATUS banners; standwalk closed pending a genuinely new design (no agent-doable next step logged); todaypolicy DELIVERED, its own Next list closed; walkcurr's only open item (item(4) foot-slip magnitude) is closed for the tangent-charge lever and its next step is unscoped contact-independent mechanism design, not a relaunchable arm (RL_LOG 19:14). 9 of 11 reachable GPU pods free (0 mid-finalize, 3/4/5/7/8/9/10/11 idle) with an empty `backlog.json` — genuinely idle-with-in-flight-arms-and-no-ready-new-lever, not idle-next-to-runnable-work: the two genuinely open next steps (rung-3's 3rd fallback verdict once `-latehandover`/`-longbudget` land, and walkcurr item(4)'s fresh mechanism design) are real work already owned by in-flight compute or unscoped design, not something a same-cycle relaunch can substitute for. CYCLE_WORKED not touched (no new triage/launch/code landed).

Evidence: `ops.sh entry cw-assistfade-rung3-residualfade-s0-stdslow`, `logs/ckpt_eval/cw_assistfade_rung3_residualfade_s0_stdslow_gate/report.json`, `launch_run.py status`, RL_LOG 09-06 19:29/19:31.

## 09-06 ~19:3x — RUNG 3 CANARY PAIR VERDICTED (2/2 FAIL - MECHANISM, schedule collision root-caused); RETRY LAUNCHED with a single-lever schedule fix

**Assigned this cycle**: read the registered on-pod gate evals for `cw-assistfade-rung3-residualfade-{s0,s1}` (both FINISHED their 2M canary budget and left unread, per the ~19:2x/~18:1x entries below). **Both VERDICTED CANARY FAIL - MECHANISM — ignition gate NOT MET, 2/2 seeds, same fingerprint:**

- `-s0`: walk/det+sto gait_valid 6/6 (no leg sacrifice) but progress_ratio med only 0.11-0.12 (bar 0.35, ~3x short), slip/m 15-17. `walk_startjitter` is worse: gait_valid 2/6 det, 2/6 sto, chronic 1-3-leg sacrifice, over_current terminations in 3-4/6 episodes per mode.
- `-s1`: even weaker — walk/det gait_valid 0/6 (leg 5 chronically parked every episode), walk/sto 6/6 but prog med 0.04 with 2/6 over_current terms, `walk_startjitter` gait_valid 0/6 det / 3/6 sto with chronic sacrifice + over_current in 4-7/12 episodes. progress_ratio med 0.03-0.06 across all modes.

**Root cause (per-tick `wandb_history.csv`, `env/sched_value` vs `env/reward_walk`/`_prog`, `terminations/over_current`, `env/height_err_mm` — same read on both seeds, not training-average noise): a SCHEDULE COLLISION, not a defect in the action-blend mechanism itself.** The blend anneal (`goal.walk_residual_blend` 0.05->1.0 over the first 1.4M/2M steps) and the log-std anneal (`--log-std-anneal-frac=1.0`, i.e. over the SAME 2M-step clock) race to their floors together: by the time blend reaches 1.0 (~1.4M steps), `train/std` has already fallen from ~0.37 to ~0.09, and keeps shrinking to ~0.05 through the whole 0.6M-step "settling window" that was supposed to let the policy practice unassisted. In lockstep with the blend ramp: `reward_walk` declines monotonically 2.0->0.1-0.2, `reward_walk_prog` goes and STAYS negative once blend nears 1.0, `height_err_mm` climbs 0->~32mm and plateaus there (never recovers), and `over_current` terminations appear once blend crosses ~0.5-0.6 and persist unresolved through the settling window on both seeds. This is exactly the launch's own pre-registered "prediction-if-false" (policy leans on the reference, collapses once blend nears 1.0) — refined with the specific compounding mechanism (std being squeezed shut at the same moment reference authority is withdrawn, leaving no exploration room to adapt). Reward quarters (`-s0`: [101.8,178.7,231.1,147.3], `-s1`: [101.4,170.8,188.2,116.7]) show a real Q3->Q4 decline, not a still-rising-reward case — the 08-21 "continue" reading does not apply.

**Not a mechanism kill**: the residual-blend action mechanism itself remains bank-proven (structural walking regardless of raw policy output at low blend, `test_assistfade_rung3_*`) and both seeds' `walk/det`+`walk/sto` halves show a real six-leg gait mid-training before the collapse. This is a retreat-one-parameter situation (matches the launch's own "if collapse happens... argues t1_steps needs to be later, not the mechanism being wrong" framing, refined to identify std-anneal-frac as the more specific lever).

**Retry launched this cycle (single lever, no new bank owed — same already-banked mechanism, only a schedule hyperparameter change)**: `cw-assistfade-rung3-residualfade-{s0,s1}-stdslow`, `respec --from` the failed pair, `--log-std-anneal-frac=3.0` (denom=6M vs the run's 2M steps, so std only reaches ~1/3 of the way to the -3.0 floor by budget end — ~0.19 instead of ~0.05 — giving meaningfully more exploration room through the blend fade-out and settling window) with every other lever (blend schedule, t1_steps=1.4M, reward stack, random-weight init) byte-identical to the failed parent. VERIFIED RUNNING: `-s0-stdslow` train-0, `-s1-stdslow` train-1. Gate: identical ignition text to the parent canary. FAIL-if: progress still <0.35, leg sacrifice, or over_current terminations reappear in `walk_startjitter` — check the same per-tick `env/sched_value` vs reward/height/termination trend before concluding std-vs-schedule; if this ALSO fails the same way, the compounding is not std-related and the next retreat is a later/slower blend `t1_steps` or a longer total budget instead (do not repeat the log-std-frac lever a second time).

Evidence: `ops.sh entry cw-assistfade-rung3-residualfade-{s0,s1}{,-stdslow}`, `logs/ckpt_eval/cw_assistfade_rung3_residualfade_{s0,s1}_gate/report.json`, `logs/experiments/cw-assistfade-rung3-residualfade-{s0,s1}/wandb_history.csv`, W&B `7sdm0vbk`/`k9tb5713`, RL_LOG 09-06 19:0x-19:1x.

## 09-06 ~19:2x — REFINEMENT to the ~18:1x sway-dominance root cause: does NOT fully generalize to `-s0-ignitewiden` (the cleanest of the 4 grid arms); rung 3's own future hardened-band gate must check speed-covariance explicitly, not infer it from gait cleanliness

**This cycle's own two assigned runs (`-s0-ignitewiden`, `-s1-freshband`) were ALREADY VERDICTED by a concurrent cycle before this one started** (`FAIL - STILL-IGNORES` / `FAIL - COLLAPSE`, matching the ledger, RL_LOG 09-06 17:47/17:49, and this file's own grid tally above) — independently re-confirmed both against fresh `ops.sh review` reads, no duplicate verdict written. Found the ~18:1x sway-dominance root-cause entry (immediately below) already landed by a concurrent cycle, plus rung 3 already designed/banked/**launched** (`cw-assistfade-rung3-residualfade-{s0,s1}`, both already finished their 2M canary budget and synced a checkpoint by the time this cycle checked capacity — own gate eval not yet kicked, left for whichever cycle owns that follow-up, not duplicated here to avoid a race).

Before accepting the ~18:1x conclusion ("the reward is ALIGNED... the same mechanism across all 4 grid cells"), spent this cycle's own no-training-spend budget building an independent per-tick check on the ONE grid arm that entry did not itself trace: `-s0-ignitewiden` (the cleanest-gait, lowest-slip arm of the 4). Used the same `eval_checkpoint.py --course-trace` tool the ~18:1x entry built, matched method (30s det rollout, `--no-video --no-wandb --no-start-jitter-panel`, fixed `goal.walk_speed_min/max_m_s=0.06`, the run's own reward cfg verbatim):

- `walk_sway_rms_mm`: median **2.92mm**, p90 5.80mm, max 9.85mm — only **17%** of valid ticks (489/2825) cross the 5mm allowance (vs freshband's 68%/1157/1706 in the ~18:1x read), charged at -0.53/tick when active.
- `reward_walk_course_income`: **+0.740/tick mean** (valid ticks) vs sway's **-0.093/tick mean over the SAME denominator** — income outweighs sway income **~8:1** on this arm (freshband's own read was the reverse: sway outweighed income ~1.7:1). A quick fixed-`--per-mode 1`/10s single-episode sample earlier in this cycle (before switching to the matched 30s method) even read **zero** sway ticks over allowance at all — the 30s read is the one to trust, but both agree sway is a minor, not dominant, drag on this arm.
- Net: on `-s0-ignitewiden`, the reward channel this track cares about (course_income) clearly, substantially rewards going faster than the policy currently does, with only a small counter-drag from sway — yet the held-out gate (already verdicted) shows the IDENTICAL flat-speed-regardless-of-command fingerprint as every other arm in the grid (`speed_mean_m_s` 0.030-0.037 across the full 0.035-0.066 commanded spread).

**This means the ~18:1x mechanism (sway self-limits the reward-optimal pace regardless of command) is REAL and DOMINANT for the swayiest arms (`freshband`, and explains the `-s1-freshband` collapse direction) but is NOT the complete story for the whole 4-arm grid** — on the cleanest arm, the net per-tick gradient already favors more speed by a wide margin and the policy still doesn't condition its pace on the command. Something else (candidates, not yet isolated: PPO credit assignment across a ~0.75s windowed/delayed course-income kernel vs the periodic-gait-dominated 18-dim action space; the temporary BC-anchor's command-conditioned target providing too weak a differentiating signal across such a narrow 0.035-0.066 m/s band relative to the dominant cyclic waveform; another reward channel not traced here — loadslip/drag_loaded/idle_charge — implicitly capping pace) is also live, independent of sway.

**Does not countermand the rung-3 pivot** (persistent partial reference is a reasonable structural fix for sway/cleanliness on its own merits regardless), but flags a concrete process point for whoever reads rung 3's future HARDENED (varying-band) gate: passing on gait-cleanliness/ignition alone (the current canary-phase gate, fixed 0.06 m/s, does not test covariance at all) must NOT be read as "confirms the sway story and closes the flat-speed pathology" — that pathology has now been shown to survive even where sway is a minor drag, so the hardened-band gate needs its own explicit `speed_mean_m_s` vs `cmd_dist_m` covariance check (reusing the rung-2 arms' own gate language) before anyone declares the original pathology fixed.

No training spend, no code changed (reused the existing `--course-trace` columns built by the ~18:1x entry). No new launch this cycle — rung 3's 2 canaries are already running/finished under a concurrent cycle's ownership; every other track re-checked fresh (joystick/amp/cpg DONE/maintenance, standwalk blocked on design, todaypolicy has one open non-assistfade bug already flagged as not-this-lead); `backlog.json` empty, all 11 reachable GPU pods free with zero live trainers at the time of this check — genuinely idle-with-empty-queue for any NEW launch this track could responsibly make, not idle-next-to-runnable-work (the one live thread, rung3's gate eval, is being left to its own launching cycle to avoid a duplicate/race).

Evidence: `/tmp/dg2/ignitewiden_30s.csv` (regenerable: `uv run python -m rl_move.sim.eval_checkpoint rl_move/sim/policies/ppo_goal_cw_assistfade_rung2_anchorfade_s0_ignitewiden.zip --task joint_walk --course-trace <path> --episode-seconds 30 --no-video --no-wandb --no-start-jitter-panel --modes walk --per-mode 1 --dr-scale 0.0 --seed 0` + this run's own ignitewiden `--cfg-set` stack, `ops.sh entry cw-assistfade-rung2-anchorfade-s0-ignitewiden`), RL_LOG 09-06 19:2x.

## 09-06 ~19:xx — RUNG 3 BUILT + BANKED + LAUNCHED (residual fade), per the ~18:1x recommendation below

**Acted on the ~18:1x recommendation directly below** (retreat to
rung 3 rather than a rung-2 reward patch). Rung 3
(`EASIER_WALKING_CURRICULUM.md` item 3, "actor controls bounded
residuals around the scripted tripod reference; progressively
increase residual authority while reducing reference amplitude") is a
genuinely new ACTION-SPACE mechanism, not a reward term, so it needed
its own build + bank before any launch (RESEARCH_RULES).

**Design (assume-and-go, `OPERATOR_QUESTIONS.md` 2026-09-06 ~19:xx):**
the doc names two quantities (residual authority, reference
amplitude); built ONE tied scalar instead of two independently
scheduled knobs:

    applied_action = ref + blend * (raw_policy_action - ref)

`ref` is the same command-conditioned scripted-TripodGait target the
WALK BC-anchor loss already uses (`self._walk_bc_gait`); `blend` is
the new `goal.walk_residual_blend` in [0, 1] (`goal.walk_residual_
gate` arms the mechanism, default 0 = bit-exact off). blend=0 =>
applied IS the reference (residual authority zero — even an
adversarial/refusing raw policy still walks); blend=1 => applied IS
the raw policy action exactly (reference amplitude zero,
mathematically identical to the gate being off). This is exactly an
additive bounded residual (`ref + blend*(raw-ref)` = reference plus a
residual capped at `blend` times the raw/ref gap), matching the doc's
"bounded residual" language with one knob. Meant to be driven by the
EXISTING generic in-run `sched.*` scheduler (`sched.key=goal.
walk_residual_blend`) — no new trainer callback needed.

**Implementation**: `rl_move/sim/sim_env.py` — `_walk_bc_gait`
construction (both the fresh-reset and mode-switch sites) now also
fires when `goal.walk_residual_gate>0` (previously gated only on
`train.bc_anchor_coef>0`), and a new block at the top of
`_step_begin` (before the safety filter, right after the existing
sched-clock write so an annealed blend value is picked up the same
tick it's written) computes `ref` from that gait object and applies
the blend formula above. Only active on WALK ticks with a live
teacher; never touches rise/hold/lower/getup. Both new cfg keys
default to the legacy no-op (gate off / blend=1.0), so every existing
run/test is bit-exact unaffected — confirmed by re-running
`test_bc_anchor.py` (137/137 green, unchanged) since that suite shares
the touched `_walk_bc_gait` construction code path.

**Bank**: `test_task_semantics.py` `test_assistfade_rung3_*` (5 new
tests, reusing the existing `_walk_rollout`/`ASSISTFADE_RUNG1_
OVERRIDES` harness rather than a new one — this bank checks the
ACTION BLEND itself, not a reward-income ordering). All 5 green.
Measured values (mesh family, rung-1 base stack, 5-seed mean):

| raw policy | gate off | blend=0.05 | blend=0.5 | blend=1.0 |
|---|---|---|---|---|
| "gait" (honest teacher) | 3720.2 | 4417.3 | 4180.9 | 3720.2 |
| "park" (refusal) | -300.7 | 4395.0 | 3400.0 | -300.7 |

blend=1.0 reproduces gate-off EXACTLY on both policies (pure pass-
through confirmed, not just close); at blend=0.05 the refusing "park"
raw policy is fully rescued to walking-level income (actually
slightly ABOVE the bank's own "gait" teacher, since the internal
`_walk_bc_gait` reference uses the corrected knee=100 robot_abs
stance convention vs the bank's older knee=80 `WALK_PLANT`, a
pre-existing convention difference, not a bug in this mechanism); mid
values interpolate monotonically between the two endpoints for the
refusing policy, confirming authority hands over in the right
direction across the whole range.

**Launched** (canary phase, mirrors rung 2's own first-canary recipe:
2M steps, mesh/100Hz, episode-seconds 10, fixed-forward 0.06 m/s,
n-envs 3072, seed 0/1, RANDOM actor-weight init — no `--init-from`):
`cw-assistfade-rung3-residualfade-s0` / `-s1`. Schedule: `sched.key=
goal.walk_residual_blend`, v0=0.05 -> v1=1.0 linearly over the first
1.4M of the 2M-step budget (leaving a 0.6M-step settling window at
full unassisted authority before the run ends, so the final
checkpoint has actually trained under zero assistance, not just been
evaluated under it for the first time). **Gate-reading note for the
next reader (important, do not skip)**: unlike a reward-income read,
this run's OWN saved cfg carries `goal.walk_residual_gate=1` +
`sched.key=goal.walk_residual_blend` baked in — the held-out gate
eval MUST override `goal.walk_residual_gate=0` (or at minimum drop
`sched.key`/`walk_residual_blend` from the eval's `--cfg-set` list
entirely) so the checkpoint is judged on its OWN unassisted policy
output, not with the teacher still steering at eval-time tick~0
(`sim_env.py`'s own scheduler docstring: eval-harness envs sit at
tick~0 and read ~v0 for any scheduled key unless the eval invocation
overrides it). `eval_checkpoint.py` loads `load_config()` defaults +
explicit `--cfg-set`, so simply NOT copying `goal.walk_residual_*`/
`sched.*` into the eval's cfg-set list is sufficient — do not copy
them by habit from the training command.

Gate (ignition, per curriculum doc, det+sto held-out, DR-0): sustained
forward translation for the full episode, repeated alternating
support transitions, all six legs participating (no permanently
planted/unloaded leg), zero falls/safety terminations, progress_ratio
>= 0.35. Slip/current recorded, not held to the joystick band yet.
Prediction-if-true: the mechanism's structural walking-regardless-of-
policy property (proven in the bank above) means ignition should be
easier to clear than rung 2's own random-weight canary (which had to
rely on a strong but ungrounded anchor LOSS coefficient); the settling
window should mean the ignition gate is being judged on a policy that
has genuinely practiced at full authority, not just inherited a good
pose. Prediction-if-false: if the policy learns to "lean on" the
reference during the assisted window and collapses once blend nears
1.0 within the settling window (visible as reward/behavior degrading
in the last ~0.5M steps of training), that argues t1_steps needs to
be later (a longer/gentler handover) rather than the mechanism being
wrong — check `env/reward_walk_*` trend across the anneal in
`wandb_history.csv` before concluding either way.

Evidence: `rl_move/sim/sim_env.py`, `rl_move/tests/
test_task_semantics.py` (`test_assistfade_rung3_*`), `OPERATOR_
QUESTIONS.md` 2026-09-06 ~19:xx, snapshot (this cycle, tag TBD by
`snapshot.sh`), `ops.sh entry cw-assistfade-rung3-residualfade-s{0,1}`
once running.

## 09-06 ~18:1x — DIG-IN RESOLVED: sway-vs-income root-caused with real per-tick evidence; ALL 4 rung-2 habituation-dose arms now closed; RECOMMENDATION = retreat to rung 3, not a stride-amplitude reward patch

**Closes the "course_income/excess_sway near-cancellation" DIG-IN flagged
09-06 ~17:4x/~17:5x** (wandb-scalar-only lead on `s0-freshband`) with a
real per-tick trace, not another training-average proxy. Built the
tool this needed: `eval_checkpoint.py --course-trace` now also logs
`walk_sway_rms_mm`, `reward_walk_excess_sway`,
`walk_course_income_speed_f`, `reward_walk_course_income` per commanded
tick (4 new trailing CSV columns, purely additive — existing readers
indexing the first 10 fields are unaffected; `test_course_disp_
semantics.py` still 16/16 green). Snapshot `55d038f4` (exp/course-
trace-sway-income-columns).

Ran a genuine 30s deterministic straight-line rollout of the final
`s0-freshband` checkpoint on-pod (train-1, `env.model_source=mesh`,
same reward cfg the run trained under) and decomposed every tick:
- `walk_sway_rms_mm` (0.75s windowed RMS lateral deviation): **median
  6.76mm, up to 13.6mm**, valid on 1706/3000 ticks (rest fail the
  60deg course-cap gate, mostly early settling). 68% of those valid
  ticks (1157/1706) EXCEED `walk_sway_allow_mm=5.0` and get charged,
  averaging **-1.30/tick when charged** (max -3.45, cap is -6.0).
- `reward_walk_course_income` averages **+0.317/tick when active**
  (94% of ticks). Mean-over-ALL-3000-ticks: income +0.299 vs sway
  -0.502 — sway OUTWEIGHS income by ~68% on this rollout (not a
  near-perfect cancellation as the wandb-scalar read suggested; that
  read's denominator convention differs, but the qualitative
  conclusion — sway dominates — holds either way).
- **Calibration control, same tool, same tick-by-tick method**: ran
  the IDENTICAL probe against `cw-walkteach-scripted-allhead-acq12m`
  (rung 0's PASSING, teacher-band-slip champion, which keeps its BC
  anchor's `bc_anchor_walk_coef`/`phase_lock` PERMANENTLY — never
  anneals to 0). Its `walk_sway_rms_mm`: **median 1.75mm, max 5.04mm**
  — almost NEVER crosses the 5mm allowance (2/2798 valid ticks
  charged, -0.015 mean, negligible), and its income averages
  **+0.555/tick when active** (75% higher than freshband's).

**Root cause, evidence-backed, not hypothesis**: `walk_sway_allow_mm=
5.0` is correctly calibrated against a genuinely clean six-leg gait
(the always-anchored champion sits comfortably under it) — this is
NOT a miscalibrated/buggy allowance to raise. The rung-2 lineage
(temporary anchor, FULLY zeroed after ignition, per rung 2's own
definition) produces a measurably swayier gait post-anneal (~3.8x the
champion's median RMS) even though the harness's `gait_valid`/
`sacrificed_legs` checks call it clean — six-leg participation and
low sway are different axes, and rung 2 is failing the second one.
Because the sway charge scales with actual lateral wobble and NOT
with the commanded speed, and because pushing achieved speed higher
without a stabilizing ongoing reference would (all else equal)
increase tripod sway further, the reward-optimal policy self-limits
to whatever pace keeps sway near its current (already-elevated)
level — REGARDLESS of the commanded value. This is the same
mechanism across all 4 grid cells: the two `-freshband`/`-ignitewiden`
FAIL-STILL-IGNORES arms hold a stable-but-swayey pace; the collapsed
`-s1-freshband` arm shows what happens when this same instability
compounds past the point of stable stance. **This reframes the whole
4-arm result: the reward is ALIGNED (correctly pricing real
instability), not misaligned — the mechanism gap is rung 2's own
premise (zero ongoing imitation of any kind post-ignition) producing
a gait that cannot match the always-anchored champion's cleanliness,
not a missing stride-amplitude/speed-tracking price.**

**Recommendation (assume-and-go, per this track's own retreat rule
— "retreat one rung on a clear ALIGNED failure"): do NOT build the
previously-proposed stride-amplitude/speed-tracking reward term next.**
Adding a lever that pays MORE for going faster without also fixing
gait cleanliness would likely just trade the current
flat-but-stable-and-clean failure for a faster, swayier, more
fall-prone one (the `-s1-freshband` collapse is a preview of that
direction). Per the doc's own ladder, the licensed next step is
**rung 3 (bounded residuals around the scripted tripod with a fading
reference)** — a persistent-but-shrinking structural anchor is exactly
the mechanism the champion's own PASS depends on (permanent
phase-lock), so rung 3's fading-residual-bounds design is the natural
next rung to test, not a same-rung reward patch. This is a genuinely
new mechanism (bounded residual action space around the teacher, not
a bc_anchor coefficient) — needs its own design + `test_task_
semantics.py` bank before any launch, per RESEARCH_RULES; not started
this cycle (time budget), flagged as the concrete next-session
build item below.

Evidence: `/tmp/sway_income_trace_freshband.csv` /
`/tmp/sway_income_trace_acq12m.csv` (both regenerable via `uv run
python -m rl_move.sim.eval_checkpoint <ckpt> --course-trace <path>
--episode-seconds 30 --no-video --no-wandb --no-start-jitter-panel
--modes walk --per-mode 1 --dr-scale 0.0` + the run's own `ops.sh
evalcmd` cfg-set with `goal.walk_heading_max_rad=0`/
`walk_cmd_resample_s=30`/`walk_park_start_frac=0` for a clean
straight-line read), `logs/experiments/cw-assistfade-rung2-
anchorfade-s0-freshband/wandb_history.csv`, code change
`rl_move/sim/eval_checkpoint.py` (`run_episode`'s `course_trace`
docstring + write call), RL_LOG 09-06 18:1x.

**Updated next-step priority (supersedes the 09-06 ~17:4x
stride-amplitude proposal; the canonical `## Next` list further down
this file is historical rung-1->rung-2 transition record and is not
touched):**
0. **Design + bank rung 3** (bounded residual action space around the
   scripted TripodGait teacher, residual bounds shrinking on a
   schedule, "fading reference" per the curriculum doc) — reuse the
   rung-2 semantics-bank construction pattern
   (`ASSISTFADE_RUNG1_OVERRIDES`/`assistfade_rung1_returns`,
   `test_assistfade_rung2_*`) for the seven named landmarks under
   rung 3's own reward/action-space shape. This is a genuinely new
   mechanism (residual-bounded action space, not an anchor
   coefficient) and needs its own build, not a copy-paste of the
   rung-2 anneal gate.
1. Do NOT fund a 5th same-rung speed-band arm, and do not build the
   stride-amplitude/speed-tracking reward term proposed by the prior
   cycle's less-precise lead — superseded by the root-cause finding
   above (reward is aligned; the gap is gait cleanliness without an
   ongoing reference, which a new price on speed alone would not fix).
2. If rung 3's design proves slower than expected, a cheaper
   diagnostic worth running first: repeat the champion-vs-freshband
   `--course-trace` comparison at a HIGHER commanded speed band to
   confirm the sway-scales-with-speed hypothesis directly (right now
   both probes ran at their own recipe's native/near-native pace, not
   a controlled sweep) — informational, no training spend.

## 09-06 ~17:4x — s0-freshband CLOSES habituation hypothesis; NEW evidence-backed lead (course_income/excess_sway near-cancellation), DIG-IN handoff

`cw-assistfade-rung2-anchorfade-s0-freshband` (TRUE random init, 0
habituation, widened 0.04-0.08 m/s band from step 0 — the structural
test after exploration-magnitude was closed 3/3) landed **FAIL -
HABITUATION-NOT-THE-CAUSE**: `bc_anchor_anneal/gate_pass` latches
clean at 1.52M, coef ramps 3->1.89(@3M)->0(@6M), holds 0 through
12M; post-anneal held-out gate is clean (gait_valid 6/6 every one of
4 modes, 0 falls/terms, sac=[] every episode) — but per-episode
`speed_mean_m_s` clusters 0.047-0.054 m/s across the ENTIRE
0.035-0.066 m/s commanded spread in both walk/det and walk/sto (e.g.
cmd=0.035->speed=0.051, cmd=0.066->speed=0.049 — no visible
covariance). This is the 3rd distinct root-cause hypothesis closed
for the same "ignores the commanded speed band" fingerprint
(exploration-magnitude closed 3/3 at -v2/-lsd2/-explore2; kernel-
width/sigma closed via standalone rollout probe; now init-habituation
closed via freshband). Sibling `-s1-freshband` and the `-ignitewiden`
pair are still computing on their own pods (train-0/4/7) — read them
before generalizing further, but do not fund a 4th same-mechanism
speed-band arm on this recipe.

**New lead found this cycle (no GPU spend, wandb_history.csv
decomposition of the SAME freshband run, not a fresh probe — flag as
a starting point for the next DIG-IN, not a confirmed root cause):**
at the end of training (last ~15 logged points, steps 11.9-12.0M),
`env/reward_walk_course_income` averages **+0.87** while
`env/reward_walk_excess_sway` averages **-0.81 to -0.86** — the sway
charge nearly FULLY CANCELS the course-income term (net ~+0.01 to
+0.06 out of a possible +0.87), even though this recipe is PURE
FIXED-FORWARD (`walk_heading_max_rad=0`, no turning at all) and the
logged mean `env/walk_sway_rms_mm` (~4.0-4.6mm) sits BELOW the
`walk_sway_allow_mm=5.0` allowance — meaning the mean itself should
mostly not trigger the excess charge, so the sustained ~-0.85 average
implies the per-tick/per-window sway distribution frequently exceeds
the 5mm allowance by enough to matter, not evenly, which this
aggregated wandb scalar cannot resolve (needs per-tick/per-episode
trace, not training-averaged means). Also:
`env/walk_course_income_speed_f` (achieved-along/commanded-distance
ratio, clipped [0,1]) averages **~0.55** — exactly consistent with a
policy converging to one roughly-CONSTANT absolute speed (~0.05 m/s)
regardless of command (0.55 ~= mean of clip(0.05/cmd,0,1) over
[0.035,0.066]), i.e. the course-income mechanism's speed_factor is
seeing and could in principle price this exact pathology, but its net
contribution to total reward is almost entirely offset by the sway
term before it can shape behavior. This is the SAME general "sway
charge overwhelms course/forward income" family the todaypolicy
track's 09-06 ~13:0x arc-vs-chord audit found for TIGHT TURNS
(`reward_walk_excess_sway`=-1177 vs `reward_walk_course_income`=+165,
a 7x mismatch) — but manifesting here on a STRAIGHT command where the
arc-vs-chord confound does not apply, so it is likely a DIFFERENT
defect in the same mechanism family (the sway allowance/window
calibration itself, not the chord-vs-arc geometry). **Not yet
root-caused to a specific code defect or fixed — needs a per-tick
trajectory probe (log every tick's `walk_sway_rms_mm`/
`reward_walk_excess_sway` for one held-out rollout, histogram the
firing distribution) before any reward patch, per the standing
root-cause-before-patch rule.**
`DIG-IN: assistfade rung2 harden-speedband / walk_task.py excess-sway
vs course-income pricing — near-total cancellation on straight-line
commands, root cause not yet isolated.`
Evidence: `logs/ckpt_eval/cw_assistfade_rung2_anchorfade_s0_freshband_
gate/report.json`, `logs/experiments/cw-assistfade-rung2-anchorfade-
s0-freshband/wandb_history.csv` (`env/reward_walk_course_income`,
`env/reward_walk_excess_sway`, `env/walk_course_income_speed_f`,
`env/walk_sway_rms_mm` columns), W&B `x8h2ftwk`, RL_LOG 09-06 17:40.

Registered: 2026-09-06 (operator directive 2026-09-03/09-05,
`rl_docs/EASIER_WALKING_CURRICULUM.md`, merged as PR #1 / eb736371).
Scope: real mesh/100 Hz physics. "From scratch" = random network
weights, NOT prior-free. This track exists precisely so that
`walkcurr`'s honest prior-free negative result (retired 08-31) is
never rewritten or weakened — and so nobody launches another raw-joint
reward-dose or architecture sweep to relitigate it.

## Goal
Work the assistance-removal ladder (curriculum doc §"Assistance-removal
ladder"): run only the FIRST UNPROVEN rung; advance on a behavioral
pass, retreat one rung (toward more assistance) on a clear aligned
failure. Ignition gate per rung (both seeds, det held-out video/eval):
sustained forward translation full episode, repeated alternating
support transitions, all six legs participating (no permanently
planted/unloaded leg), zero falls/terminations, progress_ratio >=
0.35. Slip/current recorded, not gated at ignition. After ignition:
harden ONE dimension at a time (speed band, fixed headings, command
changes/stops, yaw, then DR/pushes).

## Ledger audit — what is already proven (2026-09-06, do not duplicate)
- **Rung 0 (proven endpoint, mesh/100 Hz): PROVEN, do not rerun.**
  - Scripted-tripod BC clone
    `ppo_goal_cw_walkteach_scripted_allhead_bc1_std25.zip`
    (bc_init_gait, 180 eps/270k pairs mesh/100 Hz harvest, holdout act
    err 0.0034) passed the pre-RL CLONE DIRECTION GATE: all 8 headings
    0 falls, prog_m>0, completion 0.374-0.393 on the teacher band
    (`logs/ckpt_eval/walkteach_scripted_allhead_bc1_panel/`, RL_LOG
    08-30 16:2x).
  - Persistent-BC-anchor RL on that clone PASSES at scale:
    `cw-walkteach-scripted-allhead-canary{,-s1}-r1` (2/2 CANARY PASS)
    -> `cw-walkteach-scripted-allhead-acq12m{,-s1}` (2/2 PASS, 5/5
    clauses, slip/m <= 2.9 teacher band, zero falls det+sto).
- **Rung 1 on PRIMITIVE/25 Hz (evidence, NOT mesh proof):**
  `cw-amp-m2-bcinit-sec5-noamp` (seed 7) + `-seed1` (08-22, pre-mesh-
  flip): BC init + task-only PPO (zero AMP/BC/imitation), fixed fwd
  0.08 m/s, DR-0, 2M — both PASS (gait_valid 6/6 det+sto, real net
  travel, no crouch collapse). Families do not transfer; this
  motivates but does not prove rung 1 on mesh.
- **Rung 1 on MESH/100 Hz: UNPROVEN as of 2026-09-06.** Ledger swept:
  every mesh-era walk run that inits from a BC clone carries an
  ongoing `train.bc_anchor_*` stack (rung 0); the anchor-free mesh
  init-from runs (joyfullcurr13/15/16 lineage) are a different scope
  (full-DR joystick curriculum, hist/tf obs) and FAILED for reasons
  already verdicted there. No exact rung-1 equivalent exists.
- easy0905 (`walkcurr` current campaign) is teacher-free on EASY
  physics — different question, different track; no overlap.

## Now
- **09-06 ~17:4x this cycle (bookkeeping close-out, verdict already landed by a concurrent cycle):** confirmed and closed out `s0-freshband`'s held-out gate: **FAIL - HABITUATION-NOT-THE-CAUSE**, ledger/W&B/RL_LOG already carried the verdict (`ops.sh verdict` ran before this cycle started) -- independently re-pulled the raw `report.json` off train-1 and hand-checked all 4 modes myself before trusting it: `speed_mean_m_s` clusters 0.035-0.054 m/s in EVERY mode (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto) while `cmd_dist_m` ranges 0.352-0.669 over the 10 s episodes (i.e. the commanded speed swings the full 0.04-0.08 m/s band) -- zero covariance, exact same fingerprint as `-v2`/`-lsd2`/`-explore2`. Gait itself is clean: `gait_valid` True and `sacrificed_legs=[]` in all 24 episodes, zero falls/terminations. This is the TRUE-random-init (0 habituation) arm, so it rules out the last "stuck in the BC clone's fixed-cadence habit" explanation. **Sibling status (do not duplicate):** all 3 remaining habituation-dose arms (`s1-freshband` train-0, `s0-ignitewiden` train-4, `s1-ignitewiden` train-7) finished GPU training too (fleet now shows 11/11 reachable GPU pods free, no trainers) and their held-out gate evals are ALREADY RUNNING on their own pods (`eval_checkpoint` processes live-verified via `kubectl exec ps aux` at ~17:4x) -- not ready this cycle, leave for the next reader per the doc's own sequencing rule (assistfade licenses no 2nd-generation arm until all 4 land). Per the pre-registered gate text, the licensed next step once all 4 confirm is design work, NOT another log-std/init/band tweak: bank an explicit stride-amplitude/speed-tracking reward term (semantics-bank first, per RESEARCH_RULES) since the reward stack currently has no per-step lever pricing achieved speed against the commanded value beyond the saturating course-income kernel. Did not launch anything this cycle (no license yet, and a separate concurrent cycle already owns general capacity-fill for the idle GPU pods) -- not idle-next-to-runnable-work, this track's own next licensed step is gated on 3 in-flight evals.

- **09-06 ~17:2x this cycle (housekeeping: committed the prior cycle's uncommitted verdict/refill state -- s0-explore2 FAIL-COLLAPSE + s1-explore2 FAIL-COLLAPSE verdicts and the freshband/ignitewiden habituation-dose refill were already fully written but sitting uncommitted; snapshotted+pushed, no content changed).** Checkup-confirmed all 4 in-flight habituation-dose arms HEALTHY (`{s0,s1}-freshband`, `{s0,s1}-ignitewiden`). `s0-freshband` (the TRUE-random-init, 0-habituation extreme) finished training mid-cycle: full 12M budget, ignition anneal gate passed at 1.52M (`bc_anchor_anneal/gate_pass`), `bc_anchor_anneal/coef` ramped 3->0 by ~9M, `rollout/ep_rew_mean` climbed every quarter (9.5/226.7/590.3/1056.5) with only a small late dip (941.1 at the very last logged point) -- reward trend looks healthy, no collapse signature. Kicked the held-out ignition+speed-covariance gate on its own pod (train-1, `podeval`), registered via `evalpending`, left unverdicted for the next reader (do not poll/sleep on it). `s1-freshband` (~9M/12M), `s0-ignitewiden` (~5M/8M), `s1-ignitewiden` (~6.7M/8M) all still genuinely training. Re-checked capacity: 7 free GPU slots, empty backlog; walkcurr's own QUEUE AIM frontier is blocked on in-flight composite/kick-dose gate reads and a DIG-IN-owned axis bisection (items 1-2), item(4)'s slip fix (`footslip-c1`) just finished but is explicitly another cycle's to read; assistfade's own hardening ladder is sequential-by-doc (one habituation-dose question in flight, no second arm licensed until these land); joystick/amp/cpg closed/DONE, standwalk/todaypolicy blocked on design-thinking/delivered. Genuinely idle for NEW launches this cycle, not idle-next-to-runnable-work.

- **09-06 ~17:1x this cycle (partial-refill; independently verdicted
  `s0-explore2` before noticing a concurrent cycle had already handled
  `s1-explore2`/`freshband` above): `s0-explore2` also FAIL - COLLAPSE,
  WORSE than its sibling.** Held-out gate: `gait_valid` 0/6 on EVERY
  mode (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto),
  `sac=[0,1]` (two chronically sacrificed legs) in 23/24 episodes,
  slip/m med 11.8-14.5, prog/fwd collapsed to 0.04-0.19 — video
  (`walk_det_0_sheet.png`) confirms a near-static splayed-leg pose
  across all 6 sampled frames. Consistent with this run's own
  mid-training canary auto-stop at 4.37M ("protected skill(s) ['hold']
  failed 3 consecutive probes") being a real, correct signal, not
  noise. Confirms 2/2 `-explore2` seeds collapse at this boost —
  exploration MAGNITUDE closed 3/3 stands. **Also this cycle (before
  spotting the concurrent `-freshband`/`-ignitewiden` coordination
  above), independently designed and launched the SAME structural
  next-step idea**: `cw-assistfade-rung2-anchorfade-{s0,s1}-
  ignitewiden` (respec from each seed's own `-reseed8m-gatefix`,
  keeping its baked `--init-from` pointing at the ORIGINAL 2M canary
  checkpoint — i.e. 2M steps of prior single-speed habituation, not
  0 — same anchor-fade anneal mechanism, `goal.walk_speed_min_m_s`/
  `max_m_s` widened 0.06/0.06 -> 0.04-0.08 from step 0 of the FULL 8M
  ignition anneal instead of a late hardening retrofit, phase=
  acquisition since the canary cap is 2M and the anchor anneal needs
  ~5M to fully ramp). Both VERIFIED RUNNING (train-4, train-7) BEFORE
  either cycle noticed the other's overlapping work; not a pure
  duplicate of `-freshband` per the coordination note above (0M vs 2M
  vs the closed 8-10M habituation doses — read as a 3-point dose
  comparison, `-ignitewiden` first since it isolates ignition-order
  from init-randomness). Evidence: `logs/ckpt_eval/
  cw_assistfade_rung2_harden_speedband_s0_explore2_gate/{report.json,
  walk_det_0_sheet.png}`, W&B `m9vvxa5y`, RL_LOG 09-06 17:04.

- **09-06 ~17:0x this cycle (triaged `-s1-explore2`, the bigger-
  exploration-magnitude escalation the ~16:3x entry below launched):
  **FAIL - COLLAPSE.** Held-out det+sto 4-mode gate regressed hard vs
  its `-lsd2` parent: `gait_valid` fell to 4/6, 5/6, 3/6, 2/6 across
  the 4 modes (was 6/6 clean on every mode for `-lsd2`), 21/24
  episodes now terminate mid-clip via `over_current` with
  `roll_class=fell` (video-consistent real falls; `-lsd2` had 0/24
  terminations), and `slip_per_m` degraded to 3.9-6.5 (vs 2.4-3.6 on
  `-lsd2`) — exactly the pre-registered FAIL-COLLAPSE branch. The
  original target pathology is ALSO unrepaired on top of the
  collapse: `speed_mean_m_s` still clusters 0.033-0.048 m/s regardless
  of `cmd_dist_m` spanning 0.044-0.53m across episodes (a >10x range)
  — doubling the exploration boost (`--warm-log-std-override=-1.3`,
  std~0.27 vs `-lsd2`'s -2.0/std~0.135) bought zero speed-tracking
  gain while destabilizing balance recovery into falls. Sibling
  `s0-explore2` independently corroborates the same direction (its own
  training-time canary auto-stopped at 4.37M citing "protected
  skill(s) ['hold'] failed 3 consecutive probes"); `s0`'s held-out
  gate report was still mid-eval on train-0 at the time of this
  writing (not ready this cycle) — read it before treating this as a
  fully-confirmed 2/2. **This closes exploration MAGNITUDE as a repair
  lever for the speed-band-ignoring pathology, 3/3**: zero-boost
  (`-v2`), std~0.135 (`-lsd2`, confirmed real log_std movement via
  `wandb_history.csv`), and std~0.27 (`-explore2` here) all fail to
  produce speed covariance, and the largest boost actively
  destabilizes gait. **Refill (same cycle): moved to the pre-
  registered structural/capability lever instead of a fourth log-std
  value** — launched `cw-assistfade-rung2-anchorfade-{s0,s1}-
  freshband` (2 arms, 12M budget each, phase=acquisition, evidence =
  the 2-seed-confirmed `-reseed8m-gatefix` ignition mechanism). These
  are a FULL REDO of the rung-2 ignition itself (bc_anchor_coef=3.0,
  anneal_gate=1, assay_reseed=1 fix, byte-identical to the working
  recipe) from TRUE random actor weights (no `--init-from` at all) with
  the widened 0.04-0.08 m/s speed band baked in from step 0, instead of
  warm-starting hardening on top of a checkpoint that already spent
  8-10M steps habituating a single fixed 0.06 m/s cadence before ever
  seeing a varying command. Both VERIFIED RUNNING (train-1, train-0).
  Gate: standard ignition PASS (anneal latches, post-anneal held-out
  gait_valid/0 falls/progress_ratio>=0.35) AND per-episode speed
  covaries with `cmd_dist_m` — FAIL-HABITUATION-NOT-THE-CAUSE if gait
  is clean but speed still ignores the band (closes the ignition-order
  hypothesis, escalates to an explicit stride-amplitude reward term
  next); FAIL-MECHANISM/FAIL-COLLAPSE if the wider band itself breaks
  ignition. Evidence: `logs/ckpt_eval/
  cw_assistfade_rung2_harden_speedband_s1_explore2_gate/report.json`,
  W&B `6ipzl1ia`, RL_LOG 09-06 17:02.
  **NOTE (same cycle, post-launch coordination check):** a CONCURRENT
  cycle independently reached the identical conclusion off its own
  `s0-explore2` read and already launched
  `cw-assistfade-rung2-anchorfade-{s0,s1}-ignitewiden` (train-4/
  train-7) — NOT a pure duplicate of `-freshband`: `-ignitewiden` keeps
  `--init-from` pointing at each seed's original 2M canary checkpoint
  (widens the band starting from 2M steps of prior habituation, an
  8M budget, single-lever change vs `-reseed8m-gatefix`), while
  `-freshband` drops `--init-from` entirely (TRUE random actor, 0
  steps of habituation, 12M budget). Read BOTH as a habituation-DOSE
  comparison (0 vs 2M vs the closed 8-10M cases), not four redundant
  seeds of one question — `-ignitewiden` is the cleaner single-lever
  test and should be read first; `-freshband` is the more expensive
  confirmatory extreme. Future cycles: check `capacity.py`/`ops.sh
  entry` for in-flight sibling arms before backlog-adding a new
  structural test — the near-duplicate name tripwire only catches
  numeric-suffix twins, not differently-worded escalations of the same
  idea.

- **09-06 ~16:3x this cycle (triaged the `-lsd2` pair the ~15:4x entry
  below launched; both FAIL - IGNORES-BAND again, but this time
  root-caused with real probe evidence instead of another guess):**
  Both seeds: gait/falls/progress stay clean (gait_valid 6/6 all 4
  modes, 0 falls, prog med 0.49-0.61(s0)/0.46-0.55(s1) >= 0.35 bar),
  `log_std` genuinely moved this time (confirmed in
  `wandb_history.csv`: -2.0 at step 0 -> ~-2.98 by 7.8M, a real anneal,
  unlike the `-v2` pair's zero-movement bug) — yet achieved
  `speed_mean_m_s` STILL clusters flat (s0 0.037-0.048, s1 0.036-0.043)
  across the same 0.035-0.067 m/s commanded band. This REFUTES the
  `-lsd2` launch hypothesis (zero-exploration schedule bug) cleanly:
  exploration was real, the pathology persisted anyway.
  **Root-caused further instead of guessing again**: built
  `reward.walk_kernel_sigma_v_m_s` (new cfg, default-off, bit-exact,
  2 new bank tests, `test_task_semantics.py`) to test the doc's own
  guessed next step ("an explicit speed-tracking reward term") —
  specifically whether the Gaussian kernel's fixed `SIGMA_V=0.05 m/s`
  width (comparable to the ENTIRE hardened 0.04-0.08 band) was
  flattening the gradient. A standalone rollout probe (command-matched
  gait vs a scripted habitual-fixed-speed twin — the exact pathology
  seen on video/harness) shows the matched-vs-mismatch return gap
  stays FLAT at ~20-24% across every sigma from 0.05 down to 0.01
  (narrower does NOT widen it, slightly narrows it at the tightest
  width) — **this rules out kernel width as the mechanism.** The
  already-active `walk_kernel_prog_gate`/`k_walk_prog` terms already
  supply a real, sizeable (~20-24% return) incentive to track command
  speed; the reward is not silently flat. PPO simply has not converted
  an already-large real gradient into a stride-length change within
  8M steps, starting from a checkpoint entrenched by 10M+ prior steps
  of single-fixed-speed training. Also notes: the `amp` track's
  `walk_phase_speed_scale` clock-only-coupling lever was independently
  CLOSED for a related pathology (RL_LOG 08-23: "CLOCK-ONLY COUPLING
  IS INSUFFICIENT" — faster legs, same body speed, no command
  correlation, slip doubles) — do not relaunch that lever here
  unpaired with a stride-amplitude fix. **Refill**: launched
  `cw-assistfade-rung2-harden-speedband-{s0,s1}-explore2` (respec from
  each seed's SAME entrenched base checkpoint, `--warm-log-std-
  override=-1.3` — std~0.27 at launch, roughly double `-lsd2`'s -2.0/
  std~0.135 — the one remaining untested single-axis lever: bigger
  exploration MAGNITUDE, not a reward-shape change). Both VERIFIED
  RUNNING (train-0/train-1). **Both finished training within this same
  cycle** (fast: n-envs=3072 on an idle GPU, ~5-7 min wall time) —
  `-s1-explore2` ran the full 8M budget clean (`canary/hold_a/b=1` at
  the end); `-s0-explore2` AUTO-STOPPED early at 4.37M via its own
  canary regression guard (`protected skill(s) ['hold'] failed 3
  consecutive probes`) — the bigger std~0.27 noise may be destabilizing
  the `hold` skill even though the target axis is walk speed-tracking,
  a live FAIL-COLLAPSE candidate per this pair's own pre-registered
  gate text, worth a close read once the held-out gate lands (kicked
  `podeval` for both on their own pods this cycle, registered via
  `evalpending`, left unverdicted for the next reader — do not
  poll/sleep on it). If this ALSO reads flat on speed-covariance,
  exploration magnitude is closed too (3/3: zero-boost, -2.0, -1.3)
  and the next cycle should escalate to a structural fix (a fresh
  non-phase-locked init, or a genuinely new explicit stride-amplitude
  reward term) rather than another log-std value. Evidence: `logs/ckpt_eval/
  cw_assistfade_rung2_harden_speedband_s{0,1}_lsd2_gate/report.json`,
  `logs/experiments/cw-assistfade-rung2-harden-speedband-s{0,1}-lsd2/
  wandb_history.csv` (`log_std_anneal/all/value`), `rl_move/tests/
  test_task_semantics.py::test_harden_speedband_sigma_v_*`, snapshot
  `exp/assistfade-speedband-sigma-calibration`, W&B `0yvoegf9`/
  `1rtyf5jc`, RL_LOG 09-06 16:36-16:37.

- **09-06 ~15:4x (prior cycle; verdicted the
  `-speedband-{s0,s1}-v2` pair the ~15:0x entry below flagged as live
  FAIL candidates, root-caused, and relaunched the repair pair):**
  Both **FAIL - IGNORES-BAND**: gait stays clean (gait_valid 6/6 every
  one of 4 modes, 0 falls/terminations, all 24 episodes both seeds)
  but achieved `speed_mean_m_s` does NOT track the per-episode
  commanded speed — s0 clusters 0.037-0.039 m/s, s1 reads a LITERAL
  constant 0.038 m/s in every single `walk/det` episode, regardless of
  `cmd_dist_m`/10s spanning 0.035-0.066 m/s (~2x range) both seeds;
  `walk/sto` also misses `progress_ratio>=0.35` (s0 med 0.29, s1 med
  0.30) because achieved speed can't reach the band's upper half. s1's
  reward is genuinely declining (932.3->862.9->757.4), a real
  regression, not the 08-21 rising-reward pattern; s0's is flat/
  plateaued (1327.3->1354.1), not a continue candidate either.
  **Root cause (not the doc's own guessed "needs a speed-tracking
  reward term"):** the progress reward already normalizes by `s_ref`
  (`r_prog=k_prog*min(along/s_ref,1.25)`, so matching command IS
  priced) but both continuations inherited the gatefix source's
  already-fully-annealed `log_std` (~-3.0, std 0.05) and re-applied
  `--log-std-final -3.0 --log-std-anneal-frac 1.0` on top of that —
  **zero exploration boost for the entire 8M budget**, so the policy
  never searched for a genuinely different cadence per command; it
  just replayed its single habitual gait. This matches the documented
  `--warm-log-std-override` precedent (~200 prior uses fleet-wide)
  for exactly this "warm-started fine-tune whose std barely moves"
  shape. **Relaunched the repair pair** (respec from each `-v2` run,
  unchanged everything else): `cw-assistfade-rung2-harden-speedband-
  {s0,s1}-lsd2` — adds `--warm-log-std-override=-2.0` (std~0.135 at
  launch, annealing back to the same -3.0 target over the same 8M
  steps: real exploration early, converged/deterministic by the end).
  Both VERIFIED RUNNING (train-4/train-7). Gate: same 4-mode held-out
  panel, PASS needs achieved speed to visibly covary with per-episode
  `cmd_dist_m` (not cluster within ~0.005 m/s across a >=0.02 m/s
  commanded spread) with gait/falls unchanged; FAIL-STILL-IGNORES if
  speed stays flat despite the exploration boost -> escalate to an
  explicit speed-tracking reward term (a new mechanism) next, since
  that would rule out the schedule explanation. Evidence: `logs/
  ckpt_eval/cw_assistfade_rung2_harden_speedband_{s0,s1}_v2_gate/
  report.json`, W&B `dydwknke`/`227unt2g`, RL_LOG 09-06 15:45.

- **09-06 ~15:0x this cycle (refill-only, no completions assigned per
  the prompt, but both hardening arms finished mid-cycle anyway):**
  `cw-assistfade-rung2-harden-speedband-{s0,s1}-v2` (the speed-band
  hardening arms launched at ~14:37 below) BOTH finished training with
  no gate eval started. Notable from W&B alone (not yet a verdict —
  gate reads kicked, unread): `-s0-v2` auto-stopped early at 6.74M of
  the planned 8M (reward quarters 301.6/974.1/1327.3/1354.1 —
  flattening, consistent with either a canary auto-stop or a natural
  plateau); `-s1-v2` ran the full 8M but its reward is DECLINING
  (932.3 -> 862.9 -> 757.4 across its last 3 quarters) — the same
  shape the rung-1 `-cont8m` budget-collapse runs showed before their
  gait was found destroyed. Kicked `podeval` for both on their own
  pods (train-4/train-7), registered via `evalpending`, left
  unverdicted — next reader should treat s1's declining-reward
  trend as a live FAIL-COLLAPSE candidate per this arm's own
  pre-registered gate (see `ops.sh entry`), not assume PASS from the
  early launch note alone.

- **09-06 ~14:1x this cycle (`-s1-reseed8m-gatefix` verdicted ACQ
  PASS, completing the pair): RUNG 2 (anchor fade from random
  actor-weight init) IS NOW A 2-SEED-CONFIRMED WORKING MECHANISM.**
  Both `cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m-gatefix`
  (the goal-mix-isolation-fix reruns from the ~13:2x entry below) PASS
  their identical pre-registered gate: `bc_anchor_anneal/gate_pass`
  latches at global_step ~1.03M on BOTH seeds (2nd in-training check),
  `train/bc_coef` ramps 3.0->0.0 by ~5.06M and holds at 0 through the
  rest of the 8M budget on both, and the post-anneal held-out det+sto
  gate eval (anchor at 0) clears gait_valid 24/24, 0 falls/
  terminations, sac=[] (no permanently planted leg) on ALL 4 modes for
  BOTH seeds — progress_ratio med 0.41-0.49 (s0) / 0.31-0.46 (s1)
  against the 0.35 ignition bar. Video (contact sheets + det frame
  strips, both seeds) shows continuous six-leg alternating-support
  cycling and clear forward translation. slip_per_m runs 2.83-3.82
  (s0) / 3.02-5.07 (s1) — above the mature 2.9 joystick band on both,
  expected/accepted at ignition per this doc's own rule, watch item
  for hardening (s1 runs softer). **Next**: graduate rung 2 to
  hardening — harden ONE dimension at a time per this doc's own
  ladder (speed band -> fixed headings -> command changes/stops ->
  yaw -> DR/pushes), starting from either seed's 8M checkpoint
  (`ppo_goal_cw_assistfade_rung2_anchorfade_{s0,s1}_reseed8m_gatefix.zip`).
  SKILLS.md updated (1 row, both seeds). Evidence:
  `logs/ckpt_eval/cw_assistfade_rung2_anchorfade_{s0,s1}_
  reseed8m_gatefix_gate/report.json`, `logs/experiments/
  cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m-gatefix/
  wandb_history.csv` (`bc_anchor_anneal/*`), W&B `m1wc03cy`/
  `11imredg`, RL_LOG 09-06 14:0x/14:12.

  **Refill (same cycle): launched the ladder's first hardening arm,
  speed band, both seeds — `cw-assistfade-rung2-harden-speedband-
  {s0,s1}-v2`** (respec from each seed's own 8M gatefix checkpoint,
  `--init-from-source`, 8M budget, DR-0, BC anchor EXPLICITLY off
  `train.bc_anchor_coef=0.0`/`bc_anchor_anneal_gate=0` — it already
  fully annealed and its demonstrations were recorded at the old
  single 0.06 m/s speed, so leaving it on would re-run the anneal and
  confound the speed-band question; widened `goal.walk_speed_min_m_s`/
  `max_m_s` from the fixed 0.06 point to a uniform 0.04-0.08 m/s
  per-episode band, still inside the previously-validated pinned-speed
  panel range). **Note (self-correction, same cycle):** the first
  `respec --now` attempt for both seeds (no `-v2` suffix) silently
  carried over the source run's un-zeroed `train.bc_anchor_coef=3.0`/
  `anneal_gate=1` — caught within ~2 min via a ledger cfg audit before
  any real training time was lost, killed both trainer PIDs, ledger
  entries marked KILLED with the mistake documented, and relaunched
  clean as `-v2` with the anchor cfg keys explicitly zeroed (verified
  both re-launches' extra_args before moving on). Both `-v2` arms
  VERIFIED RUNNING (train-4 `dydwknke`, train-7 `227unt2g`) with
  growing `global_step` confirmed post-launch. Gate: standard held-out
  det+sto (4 modes) clears gait_valid majority/0 falls/progress_ratio
  >=0.35 at the widened band AND per-episode achieved speed
  (`cmd_dist_m`/10s vs `speed_mean_m_s`) tracks the per-episode
  commanded value rather than clustering near the old 0.06 pace;
  FAIL-COLLAPSE retreats to a narrower band, FAIL-IGNORES-BAND flags
  a missing speed-tracking reward term. Next reader: triage these once
  finished (`ops.sh review cw-assistfade-rung2-harden-speedband-{s0,
  s1}-v2`).

- **09-06 ~13:2x this cycle: ROOT CAUSE FOUND AND FIXED — the anneal
  gate's "one level deeper" NaN mystery (~12:2x entry below) was a
  real code bug in the ignition-gate ASSAY, not a policy or
  distribution problem.** `train_ppo_mjx._BcAnchorAnnealGateCb._build()`
  constructs a dedicated MJX assay env but never isolates its goal
  generator to pure walk — unlike the main training venv (which gets
  a post-construction `set_goal_mix(args.goal_mix)` call) and unlike
  `goal.walk_pure` (construction-time isolation) — so every assay
  episode silently drew from `config.yaml`'s default multi-mode
  mixture (`p_hold`=0.10/`p_lean`=0.15/`p_track`=0.15/`p_unload`=0.20/
  `p_raise`=0.15/`p_rise`=0.35 PLUS this task's own `p_walk`=0.70
  default — walk was only ~39% of draws, not the recipe's intended
  100%). A non-walk draw has no `.vx` trajectory, so `cmd_dist`/
  `cmd_prog_m` never accumulate and `cmd_prog_frac` reads `nan` for
  that episode — `aggregate_walk_probe`'s plain-mean (BY DESIGN,
  matches `eval_task`'s own nan rules, see
  `test_aggregate_nan_rules_match_eval_task`) then poisons the WHOLE
  round to `nan` from a single such draw, regardless of the real fall
  rate — explaining why several rounds read `early_term_rate=0.00`
  with `prog=nan` (a healthy round, structurally unmeasurable).
  Root-caused via a standalone GPU repro (`MjxShardedVecEnv`, the
  exact rung-2 cfg, a trivial zero-action policy): 5-6/8 episodes nan
  with the bug, 0/8 nan after the fix, across 3 reseeded rounds.
  **This is NOT a policy failure**: both `-reseed8m` held-out gate
  reads (verdicted this cycle, FAIL - TOOLING) already show 0 falls,
  24/24 gait_valid, six-leg cycling at-or-near the 0.35 ignition bar
  UNDER THE STILL-STUCK ANCHOR (s1: progress_ratio 0.35-0.40 on all 4
  modes, clean pass on the gate's own clause (b); s0: 0.32-0.44,
  borderline on 2/4 modes) — the anneal never got a chance to fire,
  not because the policy couldn't earn it. Fixed: `_build()` now
  forces a full pure-walk isolation (zero every `p_<mode>`, then
  `p_walk=1.0`, via the VecEnv-safe `set_goal_mix` hook — the same
  isolation `eval_checkpoint.py`'s `ALL_MODES` per-mode forcing loop
  and `goal.walk_pure` already use). 2 new regression tests
  (`test_walkcurr_mjx.py`:
  `test_default_goal_mix_is_not_pure_walk_without_walk_pure_or_isolation`,
  `test_full_pure_walk_isolation_guarantees_a_walk_trajectory_every_reset`),
  137+21 existing tests green, snapshot `exp/bc-anchor-anneal-goalmix-fix`
  (landed via a concurrent cycle's snapshot sweep into commit
  `c4b54263`, confirmed pushed). **Relaunched both seeds from the SAME
  2M parent checkpoints with the fix in place**:
  `cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m-gatefix` (8M,
  `--allow-twin` since the config is byte-identical to the reseed8m
  pair — only the trainer code differs — VERIFIED RUNNING train-4/
  train-7). Expect the gate to latch within the first few 500k-step
  checks now that the assay actually measures pure-walk episodes;
  read those before attempting any further anneal-gate variant.
  Evidence: `/tmp/repro_cmd_dist.py` (standalone GPU repro, not
  committed — recreate from this note if needed), `ops.sh review
  cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m`, W&B `jekexee3`/
  `qsqewbb5`, RL_LOG 09-06 13:2x-13:3x.

- **09-06 ~12:2x this cycle (both `-reseed8m` seeds found ALREADY FINISHED, ahead of
  schedule -- ckpt pulled + gate eval kicked for both, backgrounded; NOT yet verdicted,
  but the training-log evidence alone already answers the reseed fix's own question and
  is worth recording now): the reseed fix (`train.bc_anchor_anneal_assay_reseed=1`)
  WORKS AS DESIGNED but does NOT unblock the anneal -- ROOT CAUSE IS ONE LEVEL DEEPER
  than the ~12:0x entry diagnosed.** Confirmed via `grep '[bc-anchor-anneal]'` on both
  pods' raw training logs (s0: 11 checks to auto-stop at 5.5M; s1: 15 checks, ran the
  full 8M): `early_term_rate` (the "falls" figure) now genuinely VARIES round to round
  (0.00/0.12/0.25/0.38, both seeds) instead of being pinned at 0.125 forever -- the
  reseed IS drawing independent configs, exactly as designed. **But `cmd_prog_frac`
  (the progress clause) reads NaN on EVERY SINGLE round of BOTH seeds, 26/26 combined
  checks, INCLUDING every round where `early_term_rate=0.00` (s0 @3.0M; s1 @3.0M/5.5M/
  7.0M/7.5M) -- i.e. progress is NaN even when literally zero probe episodes fell.**
  This rules out the ~12:0x diagnosis's implicit assumption (that NaN was purely a
  downstream symptom of `failed_probe_row()` on a fallen episode) -- read the actual
  code path: `walk_task.py`'s `cmd_prog_frac` is `nan` whenever `w["cmd_dist"] <= 0.01`
  (episode's own commanded-distance accumulator), a DIFFERENT and independent condition
  from the `early_term`/fall flag; `aggregate_walk_probe` (`walkcurr_cert.py`) then
  plain-means `cmd_prog_frac` across all 8 rows (not in `_NAN_OK`, unlike
  `cross_track_frac`/`wrong_way`/`stop_speed_*` which ARE nanmean'd) -- so a SINGLE
  episode with near-zero commanded distance poisons the whole round's aggregate to NaN
  even though the other 7 episodes walked fine. Rung 2's launch cfg is fixed-forward
  0.06 m/s with no stops/no park-starts, so it is not yet understood WHY any episode
  would end with `cmd_dist<=0.01` absent a fall -- next reader should instrument/log a
  single assay round's raw per-episode `cmd_dist` values (not just the aggregate) to
  find which episode index is empty and why (candidates: the assay's `goal.walk_probe=1.0`
  override interacting with `episode-seconds=10` in a way that truncates the command
  window before any distance accrues, or a race between `env.seed()` and `flush_reset_
  pools()` leaving one sub-env's goal trajectory unset for its first episode). **One
  candidate already RULED OUT this cycle**: a bounded CPU repro
  (`SimHexapodJointWalkEnv`, identical cfg incl. `walk_yaw_cmd=1`/`walk_phase_run_on_yaw=1`/
  `walk_yaw_zero_frac=1.0`, 16 seeds, random small-action policy, full 1000-tick/10s
  episodes) NEVER produced a NaN `cmd_prog_frac` — every trunc episode (full horizon)
  and every early term (random-policy falls, all at tick 261) read a finite value,
  including on falls. So the goal-trajectory construction itself is not the defect in
  isolation; the NaN is specific to either (a) the ACTUAL trained/bc-anchored
  deterministic policy's action pattern (possible occasional NaN/degenerate action under
  strong `bc_anchor_coef=3` + tiny `std=0.05`), or (b) something MJX/`MjxShardedVecEnv`-
  pool-specific that the CPU single-env repro cannot reach (`env.flush_reset_pools()`/
  sharded pool reuse has no CPU-env equivalent tested here). Next step needs either the
  real checkpoint run through the CPU env (feasible, no GPU needed — load the `.zip`
  policy and call `.predict(deterministic=True)` instead of random actions) or an
  instrumented GPU-side print of the MJX assay's raw per-env `cmd_dist`/`term` array
  before aggregation. Reproduction script left at (not committed, recreate if useful):
  a `SimHexapodJointWalkEnv` loop over seeds with the rung-2 cfg dict, printing
  `info["walk_probe"]["cmd_prog_frac"]` and `env._goal_traj.vx` per episode. **Second
  repro attempt (same cycle): loaded the ACTUAL `-s0-reseed8m` checkpoint
  (`PPO.load(..., device="cpu")`) and ran it deterministically in the same CPU env
  across 16 seeds — ALL 16 gave the IDENTICAL result (`cmd_prog_frac=0.2458`, 0 falls,
  full 1000-tick episodes), because with `dr_scale=0`/`randomize=False`/fixed speed+zero
  yaw the CPU episode has no seed-sensitive randomness left to vary at all.** No NaN, no
  variation. This rules out the checkpoint's weights/deterministic-action-pattern being
  inherently degenerate (a healthy, reproducible walk comes out every time in the CPU
  physics) and narrows the remaining candidate space to the MJX/warp GPU path itself —
  most likely `MjxShardedVecEnv`'s pool/shard reset mechanics (the CPU single-env test
  has no equivalent to reproduce), or a genuine MJX-vs-CPU-MuJoCo physics divergence
  under this exact policy that only manifests on the GPU backend. Next reproduction step
  needs either an MJX-backed (not CPU mujoco) single-shard construction with the same
  checkpoint, or GPU-side instrumentation of the live assay's raw per-env row dump. **Do not
  relaunch another anneal-gate arm on unmodified code — this is now proven code-level
  (26/26 checks across 2 independent seeds), not a training/seed variance question**;
  the ignition gate CANNOT latch until either (a) `cmd_prog_frac` moves to `_NAN_OK`
  (nanmean, matching the sibling command-conditional keys) if a legitimately
  unmeasurable-but-not-failed episode is expected, or (b) the root NaN source itself is
  fixed once found. Both `-reseed8m` runs otherwise behaved exactly like healthy rung-2
  training throughout (reward/canary telemetry unremarkable; `canary/hold_a/b=1`
  throughout both) -- this is purely an anneal-gate bookkeeping defect, not a policy
  regression. DIG-IN flagged for whichever cycle reads the held-out gate evals (kicked
  this cycle, backgrounded, ~1.5-2h): `-s0-reseed8m` AUTO-STOPPED again at 5.5M (walk_fwd
  3-consecutive-fail, same canary mechanism as `-cont8m`, but earlier — 5.5M vs the
  parent's ~7.9M); `-s1-reseed8m` ran the full 8M with no auto-stop. Evidence:
  `kubectl exec hexapod-mjx-train-{4,7} -- grep '\[bc-anchor-anneal\]'
  /tmp/train_cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m.log`, `rl_move/sim/
  walk_task.py` cmd_prog_frac definition, `rl_move/sim/walkcurr_cert.py`
  `aggregate_walk_probe`/`_NAN_OK`, W&B `jekexee3`/`qsqewbb5`.

- **09-06 ~12:0x (DIG-IN cycle, `-s0-cont8m` VERDICTED: ACQ FAIL - INFORMATIVE, assay
  deadlock root-caused; fix built + both seeds relaunched):** the held-out mesh gate eval
  landed and does NOT show collapse — gait_valid 24/24, 0 falls/terms, no sacrificed leg,
  six legs cycling on video — so the pre-registered FAIL-MECHANISM text is NOT met. But
  det prog med fell to 0.30 (parent 2M: 0.36–0.52; bar 0.35) while sto stayed 0.39–0.40
  with better slip (2.98 vs det 4.48): the deterministic MEAN is what regressed, matching
  the canary. ROOT CAUSE of the never-latching anneal (both seeds): the in-training assay
  is PINNED — `env.seed(828282)` before EVERY round, desync off, deterministic policy —
  so all rounds replay the SAME 8 configs; the persistent `early_term_rate=0.125`
  (s0: 10/11 rounds; s1: 15/15) is ONE hard init the anchored policy deterministically
  fails, not small-n noise (the 11:2x entry's "assay noise" read was wrong — parent 2M
  failed 2/8, later ckpts 1/8: policy-dependent falls). Double lock: that episode injects
  `failed_probe_row()` → `cmd_prog_frac=NaN` (plain-mean, not `_NAN_OK`) → the progress
  clause ALSO NaN-fails every round (`gate_cmd_prog_frac` absent from history, both
  seeds). Chicken-and-egg: the latch demands zero falls on a frozen probe set whose hard
  init the strong anchor (coef stuck 3.0) prevents the policy from fixing; continued
  anchored training then degrades pinned det behavior (canary walk_fwd 0/2 from ~3M new
  steps in s0, ~5M in s1). Per 08-21: misalignment to repair. FIX (snapshot
  `exp/cw-assistfade-rung2-anchorfade-reseed-fix`): `train.bc_anchor_anneal_assay_reseed`
  (default OFF, bit-exact; fresh pinned seed per assay round → independent draws; 9 tests
  green). RELAUNCHED both seeds from the PARENT 2M checkpoints (not the degraded cont8m
  ends): `cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m`, reseed=1, 8M, pre-registered
  gates incl. a FAIL-ASSAY-DISTRIBUTION clause if reseeded rounds still never latch.
  `-s1-cont8m` left unverdicted for its own triage cycle (evidence identical; cite this
  entry). Note for the "cont8m past its 2M canary is structurally unstable" question: at
  rung 2 the instability now has a concrete mechanism (stuck anchor + std anneal squeezing
  the det mean), distinct from rung-1's gait destruction.
- **09-06 ~11:5x this cycle (triage of `-s0-cont8m`, DIG-IN flagged, no verdict yet — held-out
  gate eval still computing on-pod, video-every=1/24-episode panels run 1.5-2h): both rung-2
  `-cont8m` continuations (`-s0-cont8m` train-8, `-s1-cont8m` train-9, the other a concurrent
  cycle's to verdict) independently AUTO-STOPPED via the fixed-seed canary regression guard —
  NOT a triage kill, the run's own `_make_canary_stop_callback` fired mid-training.** Plain
  English: `walk_fwd` was one of only two "protected" groups (the ones the 2M parent checkpoint
  passed 2/2 at launch — the other is `hold`); by the time each run reached ~5.7M
  (`-s0-cont8m`) / ~7.9M (`-s1-cont8m`) of the planned 8M new steps, `walk_fwd_a`/`walk_fwd_b`
  had failed 3 consecutive periodic probes (every ~1M steps) while `hold` stayed 2/2 throughout
  — training auto-stopped itself per its own regression guard
  (`canary/auto_stop=1`, log line `[canary] AUTO-STOP at 5,667,840: protected skill(s)
  ['walk_fwd'] failed 3 consecutive probes`, W&B `71d7y3v2`/matching for s1). The walk_fwd
  canary case is essentially the SAME distribution as this recipe's own training task (pinned
  hold-then-ramp-then-constant 0.06 m/s forward, mesh/100 Hz) — so a deterministic pinned probe
  regressing on the training task itself, while `ep_rew_mean` kept climbing every quarter
  (`-s0-cont8m` reward quarters 215.7/681.4/1188.6/1251.2, still rising at the point of
  auto-stop) is a real reward<->eval divergence signal, not noise: per-check history shows
  `walk_fwd_{a,b}` pass at the 2M checkpoint, a single early blip fail at 1M-new-steps, ANOTHER
  pass at 2M-new-steps, then a clean 0/0 fail from 3M-new-steps onward through auto-stop — looks
  like settling into a genuine regressed basin after ~3M steps, not one noisy sample. This is
  the THIRD cont8m-budget failure fingerprint in this campaign (rung-1's `-s1-cont8m` gait-
  destroyed-by-budget and `-s2-cont8m` wrong-direction-spin-by-budget were the first two) —
  worth asking, once both held-out reads land, whether "continue the SAME fixed-forward-only
  cont8m recipe past its 2M canary" is itself a structurally unstable move on this track,
  independent of which rung. DIG-IN reason for `-s0-cont8m`: the pre-registered ledger gate's
  own FAIL text ("the held-out gait collapses... at this budget") may already be met, but the
  held-out mesh gate eval (det+sto, per-leg gait metrics, video) was still computing at end of
  this cycle — verdict on that read, not the canary telemetry alone, per the video/gate-outranks-
  reward rule. If the gate eval instead shows a CLEAN six-leg gait despite the canary fail, that
  is a genuine gate-vs-canary disagreement needing its own root-cause (canary's pinned/short
  hold+ramp probe may not match the harness's 10s constant-command episodes). Evidence so far:
  `logs/experiments/cw-assistfade-rung2-anchorfade-{s0,s1}-cont8m/wandb_summary.json`
  (`canary_baseline`/`canary_protected`/`canary/*` keys), `wandb_history.csv` (per-check
  `canary/walk_fwd_{a,b}` timeline), on-pod
  `/tmp/train_cw-assistfade-rung2-anchorfade-s0-cont8m.log` (`grep '\[canary\]'`).
- **09-06 ~11:2x this cycle (refill-only, no completions assigned; found+verdicted the rung-2
  anchorfade canary pair a concurrent cycle had launched and left unread):** **both seeds CANARY
  PASS, and BEAT the ignition bar already at 2M under the still-strong anchor** — held-out gate
  eval 24/24 episodes gait_valid=true, 0 terminations, 0 sacrificed legs, six-leg cycling
  (duty 0.35-0.62, swing_count uniform 12/12), progress_ratio 0.35-0.52 across all 4 modes (bar
  0.35), slip/m 2.4-3.3 (near/at the 2.9 teacher band) — clearly better than rung-1's own BC-init
  canary comparison point (progress med 0.22) despite starting from RANDOM weights. The in-training
  anneal-gate assay (n=8 eps every 500k steps) never latched `ignition_gate_pass` in this 2M window
  (`bc_anchor_anneal/gate_pass`=0 every check, `gate_early_term_rate`=0.25 vs 0/24 in the larger
  held-out eval — small-n assay noise, not a real fall pattern) so `bc_anchor_coef` never annealed
  off 3.0 — exactly the CANARY gate's own "not yet annealed is fine at this budget" criterion.
  SKILLS.md updated (1 new entry, both seeds). **Refill:** launched `-cont8m` for both seeds
  (+8M each, 10M cumulative, `--init-from-source`, ACQ phase) — gives the periodic assay ~16 more
  checks to latch the gate and drive the anchor through its 4M-step anneal, then the real read is
  deterministic held-out behavior WITH the anchor at/near zero (the doc's actual downstream gate,
  not the still-strong-anchor mechanism-health check this cycle closed). VERIFIED RUNNING
  `-s0-cont8m` train-8, `-s1-cont8m` train-9. Housekeeping: an early respec attempt for `-s1-cont8m`
  timed out client-side and was mistakenly retried, producing a duplicate `-s1-cont8m-rr1` on
  train-2 running the identical recipe — caught via a live `kubectl exec ps` cross-check, killed
  immediately (`ops.sh killrun`), ledger marked KILLED with the duplicate explained; no information
  lost, `-s1-cont8m` (train-9) is the surviving run. Evidence: `logs/ckpt_eval/
  cw_assistfade_rung2_anchorfade_{s0,s1}_gate/report.json`, W&B `fd7gmi2z`/`70k66xu7`,
  `logs/experiments/cw-assistfade-rung2-anchorfade-{s0,s1}/wandb_history.csv`, `launch_run.py
  status`, RL_LOG 09-06 11:2x.
- **09-06 ~03:3x rung-1 first read (s1) + refill (keep-GPUs-training
  cycle, fb_20260906T031718_f01aa6):** `-s1` VERDICTED **CANARY PASS
  (mechanism health)** — task-only PPO from BC init did NOT destroy
  the gait at 2M: gait_valid 24/24 (all 4 modes), 0 falls/terms,
  sac=[] everywhere, six-leg cycling + level body on video
  (`logs/ckpt_eval/cw_assistfade_rung1_bcinit_taskonly_s1_gate/`).
  Shortfall is pure speed: det prog med 0.22 vs the 0.35 ignition bar
  (0.12 m/10 s at 0.06 m/s cmd); slip 8-12/m recorded. Per 08-21 +
  the gate's own "don't judge acquisition at 2M" scope this is
  continue-not-retreat. LAUNCHED: `-s1-cont8m` (+8M from own ckpt,
  acquisition phase, ignition bar judged at 10M total) and `-s2`
  (fresh-seed 2M canary — s0's training reward collapsed in Q4
  (96->23) while s1's stayed healthy; s2 disambiguates seed-vs-recipe
  before more acquisition spend). `-s0`'s gate eval was still running
  on train-4 (watcher prestage; a concurrent triage cycle owns its
  pollreap) — the JOINT rung-1 ignition read stays OPEN pending s0.
  No rung-2 launch until the joint read lands (doc: run only the
  first unproven rung); rung-2 anchor-fade still owes the full
  intermediate-state semantics bank before any launch.
- **09-06 ~03:4x JOINT RUNG-1 READ (s0 lands): NOT A PASS.** `-s0`
  VERDICTED **CANARY FAIL - MECHANISM — gait destroyed on this seed**:
  aggregate `gait_valid` 0/24 across all 4 modes, a chronic 2-leg
  (legs 0,1, the front-right/right-middle adjacent pair) sacrifice in
  nearly every episode (occasionally 3-4 legs), 2 safety terminations
  (over_current) under `walk_startjitter`, progress_ratio 0.08-0.20
  (worse than even s1's failing 0.13-0.25 band). Video confirms a
  near-stationary/quivering body, not s1's slower-but-real six-leg
  gait. Training reward Q4 collapsed 95.6->22.9 exactly where the
  gait failure concentrates (vs s1's healthier 167.8->108.6) — the
  reward-collapse flag that motivated launching `-s2` before this
  read landed was justified. **Joint rung-1 ignition gate is NOT MET**
  (requires both seeds; s1 alone read CANARY PASS mechanism-health,
  s0 reads FAIL gait-destroyed) — per the doc's own rule this is a
  RETREAT trigger, not a same-recipe retry. However: since `-s2`
  (fresh-seed 2M canary, seed-vs-recipe discriminator) and `-s1-cont8m`
  (+8M continuation of the healthy seed) were ALREADY launched before
  this read landed specifically to test whether s0's failure is a
  per-seed basin or a recipe-level defect, retreat is deferred one
  more data point: if `-s2` also shows gait destruction, rung 1 is
  recipe-unstable (>=2/3 seeds destroy the gait) and the doc's retreat
  (rung 2 slower anchor fade, or rung 3 tighter residuals) fires next
  cycle; if `-s2` reads healthy like s1, rung 1 is seed-sensitive but
  viable and a 3rd/4th seed or `-s1-cont8m`'s ignition-bar read at 10M
  decides advancement. Evidence: `logs/ckpt_eval/
  cw_assistfade_rung1_bcinit_taskonly_s0_gate/report.json`, W&B
  `vf3f9kbw`; RL_LOG 09-06 03:40.
- **Rung 1 canary pair LAUNCHED 2026-09-06:**
  `cw-assistfade-rung1-bcinit-taskonly-s0` / `-s1` (2M each, canary
  phase). Recipe = `cw-walkteach-scripted-allhead-canary-r1` byte-
  identical EXCEPT: all `train.bc_anchor_*` = 0 and
  `reward.walk_anchor_gate=0` (no ongoing BC/imitation of any kind);
  fixed forward only (`walk_heading_max_rad=0`, `walk_stop_frac=0`,
  `walk_park_start_frac=0`, resample no-op at 30 s > 10 s episodes);
  fixed 0.06 m/s (inside the clone's 0.06-0.10 training envelope, per
  the doc's 0.04-0.06 rung-1 band); 10 s episodes; same init
  (`..._bc1_std25.zip`), same log-std anneal to -3.0 (proven low
  walking-noise range), same bank-proven course-income reward stack
  (no new reward keys => no new mechanism bank owed; ordering check
  for the EXACT rung-1 cfg added to `rl_move/tests/
  test_task_semantics.py` ASSISTFADE_RUNG1 bank this cycle).
- Gate (pre-registered, ignition): see Goal. PASS on both seeds =>
  advance to first hardening dim (speed band) and queue rung 2
  (anchor fade from random weights). FAIL with gait destroyed =>
  rung 2 with SLOWER anchor fade, or rung 3 (tighter residual bounds)
  — explicitly NOT a reward-dose/architecture retry.

## Rung-1 seed panel state (09-06 ~04:4x)
- `s0` CANARY FAIL - MECHANISM (gait destroyed, 0/24 gv) — verdicted 03:40.
- `s1` CANARY PASS mechanism at 2M (24/24 gv, 0 falls, det prog 0.22 <
  0.35 bar) but its `-s1-cont8m` (+8M, 10M total) ignition read is
  **FAIL — gait destroyed by budget**: aggregate gait_valid 0/24 (all
  4 modes), EVERY episode now terminates over_current (24/24, vs 0/24
  at 2M), chronic 2-leg sacrifice (leg 4 airborne duty 0.02-0.08, leg
  5 permanently planted duty 0.98-1.0, every episode), video confirms
  near-static body + one leg dragging rigidly. Reward net-DECLINED
  (quarters 30.9/-234.1/-124.5/2.0, trough -300 around 3-4M) with
  terminations/over_current rising in lockstep (22-60 early ->
  85-147 late) — not the 08-21 rising-reward continuation case.
  Verdicted 04:38, W&B `nvpkarrc`.
- `s2` CANARY PASS mechanism at 2M (23/24 gv, 0 falls, six legs
  cycling on det strip, det prog med 0.23 < 0.35 bar; one
  startjitter/sto over_current term reported-not-gated per the 09-04
  uncalibrated-current ruling) → `s2-cont8m` RUNNING (train-8), the
  deciding data point.
- **Updated joint read: 2/3 seeds now show gait destruction (s0
  immediately at 2M, s1 after +8M budget) — trending toward a
  RECIPE-level ceiling/entrenchment, not seed noise, matching the
  same budget-driven leg-sacrifice attractor CURRENT_TRUTHS already
  logs across unrelated crossgrav/sde lineages this week.** Per the
  doc's own rule, do not launch a 4th same-recipe seed while
  `s2-cont8m` is still deciding; if `s2-cont8m` also destroys its
  gait, rung 1 is CLOSED (recipe-unstable, >=2/3 destroy) and the
  next cycle fires the doc's retreat (rung 2 slower anchor fade, or
  rung 3 tighter residuals) without further same-recipe spend.

## RUNG 1 CLOSED (09-06 ~05:0x) — 3/3 seeds fail at scale, retreat fires
`s2-cont8m` landed: gait_valid 6/6 all 4 modes (no leg sacrifice) but
progress_ratio NEGATIVE in all 24 episodes (-0.10 to -0.16),
direction_err_mean_deg 99-119° (spin/wrong-way, not a tracking miss),
slip_per_m 20-24 (7-8x the 2.9 band), video confirms a body that spins
in place while the heading arrow rotates through multiple directions.
Reward quarters 98.7/44.1/-4.8/-275.2 — clean decline, not the 08-21
rising-reward case. **Final rung-1 tally: 3/3 seeds fail at 8-10M
scale, each via a DIFFERENT fingerprint** (s0: immediate gait
destruction at 2M; s1-cont8m: chronic 2-leg sacrifice + 100%
over_current at 10M; s2-cont8m: clean six-leg gait but wrong-direction
spin + massive slip at 10M). This clears the doc's own >=2/3-destroy
retreat threshold decisively. **Rung 1 (BC init + task-only PPO, no
ongoing BC/AMP/imitation) is CLOSED on mesh/100Hz: do not fund a 4th
same-recipe seed or any same-recipe budget continuation.**

## Next
0. **SEMANTICS BANK GREEN 2026-09-06 ~10:2x (no training spend, code +
   tests only — this closes the last precondition item 1 below still
   listed as owed).** `test_task_semantics.py`'s
   `test_assistfade_rung2_*` (5 tests, `assistfade_rung2_returns`
   fixture) now pin the doc's seven named landmarks (`weight_shift`,
   `one_lift`, `one_placement`, `one_transition`, `two_steps_fall`,
   `static_stand`, `clean_gait`) under the UNCHANGED rung-1 reward
   stack (`ASSISTFADE_RUNG1_OVERRIDES` — rung 2 only changes the
   TRAINING side, `bc_anchor.py`'s own docstring: "the reward stack is
   UNTOUCHED"). All 5 green: no permanent-refusal landmark
   (`static_stand`) rivals any attempt; no fall-after-progress
   landmark (`two_steps_fall`) rivals a safe partial attempt or beats
   holding still; `clean_gait` remains the clear global optimum above
   every partial landmark. Two calibration findings worth reusing if
   this bank is ever revisited: (a) a naive first construction froze
   each partial landmark's pose and held it for the REMAINING ~13s of
   a 15s episode — that measures "stuck", not "progress", and scored
   WORSE than `static_stand` for every partial landmark (independently
   re-discovered twice this cycle, once by this session, once by a
   concurrent session that landed the fix — see file history); (b) the
   four partial landmarks cluster in a narrow band and do NOT form a
   strict internal staircase (`one_lift` can beat `one_placement`) —
   asserted as a band, not a fine ordering, per the bank's own
   evidence-over-assumption convention. **Rung-2 canary launch is now
   precondition-clear** (mechanism below + bank both green) but NOT
   YET LAUNCHED by any session as of this note — the next reader can
   launch it directly: 2 seeds, mesh/100Hz, `goal.walk_speed_*=0.06`
   fixed-forward (rung-1's exact command diet), RANDOM actor-weight
   init (no `--init-from-source`, unlike rung 1's BC-clone init — this
   is rung 2's whole point), `train.bc_anchor_coef` set to a genuinely
   STRONG initial value (rung 1's BC-clone init never needed a
   nonzero anchor; rung 2 has no precedent run to copy a dose from —
   pick something clearly dominant early, e.g. on the order of the
   rise-task anchor doses in `bc_anchor.py`, and say so in the launch
   notes since it is a fresh assume-and-go), `train.bc_anchor_anneal_
   gate=1` (+ `_steps/_check_every/_assay_episodes/_min_progress`, all
   built 09-06 ~09:3x), 2M-step canary budget (this is a genuinely new
   mechanism combination — canary first, never straight to ACQ).
1. **MECHANISM BUILT 2026-09-06 ~09:3x (no training spend, code +
   tests only).** Rung 2's "anneal the anchor smoothly to zero only
   after deterministic walking passes" needed a genuinely new
   mechanism (a gate-triggered anneal, not a fixed coefficient or a
   plain step-count schedule — a step-count-only anneal would repeat
   rung 1's exact failure of dropping the anchor before the RL side
   has anything to fall back on). Built, default-OFF, bit-exact when
   off:
   - `walkcurr_cert.IGNITION_GATE` / `ignition_gate_pass()`: a pure
     function pinning the curriculum doc's own named ignition
     criteria (no falls, six-leg participation via
     `contact_sw_per_s`/`foot_sw_min_per_s`, `cmd_prog_frac>=0.35`) —
     deliberately LOOSER than `WALKCURR_GATE`/`walkcurr_bucket_pass`
     (slip/roll/cross-track/direction are recorded, not gated, at
     ignition per the doc). 4 new unit tests
     (`test_walk_curriculum.py`), including one that explicitly checks
     ignition passes a sloppy-but-walking row `WALKCURR_GATE` would
     reject.
   - `bc_anchor.bc_anchor_anneal_value()`: a pure scheduler — holds
     the coefficient at its initial ("strong") value until a
     `pass_step` is latched (None = never yet, matching "initially"),
     then linearly ramps to 0 over `train.bc_anchor_anneal_steps`,
     then holds at 0. 4 new unit tests (holds pre-pass at any step
     magnitude, linear ramp arithmetic, holds at 0 post-ramp,
     monotonic non-increasing).
   - `attach_bc_anchor()` now reads
     `train.bc_anchor_anneal_gate/_steps/_check_every/
     _assay_episodes/_min_progress` (all inert unless
     `bc_anchor_anneal_gate>0`, which itself requires
     `bc_anchor_coef>0` — fails closed if there is nothing to anneal).
     3 new unit tests (default-off wiring, positive-coef requirement,
     cfg knobs round-trip).
   - `train_ppo_mjx.py`: a new `_BcAnchorAnnealGateCb`
     (gated on `model.bc_anneal_gate`, independent of
     `--walk-curriculum` — rung 2's launch cfg is a single fixed
     forward command, not a bucket ladder) that periodically builds a
     dedicated deterministic MJX assay env (same construction pattern
     as the walk-curriculum cert loop's own `_MjxWalkCurrCert._build`/
     `_assay`, `goal.walk_probe=1.0`, no bucket forcing), runs
     `train.bc_anchor_anneal_assay_episodes` det episodes, aggregates
     via the existing `aggregate_walk_probe`, and on the FIRST round
     that clears `ignition_gate_pass` latches that step and starts
     overwriting live `model.bc_coef` via `bc_anchor_anneal_value`
     every rollout start. Latching is permanent (a later regressed
     assay never re-arms the anchor). Import-checked
     (`python -c "import rl_move.sim.train_ppo_mjx"`), no dry-run
     harness exists to exercise the callback itself without spending
     GPU steps — that first real exercise is the eventual rung-2
     canary launch below, not this cycle.
   - Tests: `uv run pytest rl_move/tests/test_bc_anchor.py
     rl_move/tests/test_walk_curriculum.py rl_move/tests/
     test_walkcurr_mjx.py` — 191+19 = 210 passed, 0 failed (14 new
     tests added by this change).
   - Snapshot: see RL_LOG for the commit/tag.
   **Still owed before ANY rung-2 launch** (per the doc's own process
   requirement, unchanged by the mechanism build above): the full
   intermediate-state semantics bank (weight shift, one useful lift,
   one forward placement, one support transition, two steps then
   fall, static stand, clean gait) — an ordering check (à la
   `ASSISTFADE_RUNG1_OVERRIDES`/`assistfade_rung1_returns`) that the
   rung-2 reward stack scores those seven synthetic
   trajectories/action-sequences in the intended order under
   `attach_bc_anchor`'s strong-then-annealing regime. This is the
   next concrete piece of work (design the 7 synthetic states, reuse
   the rise/hold bank's synthetic-pose-generation helpers where
   possible since weight-shift/lift/placement look like posture-probe
   variants; support-transition/two-steps-then-fall/clean-gait need a
   rollout-based score like `ASSISTFADE_RUNG1`'s `_walk_rollout`) —
   NOT a design question needing an operator answer, a build task for
   whichever cycle picks this up next.
2. Alternative if rung 2's design proves harder to bank than expected:
   rung 3 (bounded residuals around the scripted tripod with a fading
   reference) is the doc's other named retreat target and may have a
   simpler semantics story (residual bounds shrink on a schedule
   rather than an anchor coefficient annealing) — worth a quick
   comparative design pass before committing to one.
3. Do NOT re-attempt rung 1 with a reward-dose or architecture tweak
   (doc-binding) — the failure modes (leg-sacrifice, wrong-direction
   spin) are both budget-driven entrenchment away from a healthy 2M
   canary, not an undertrained or misconfigured start.

## WAITING-ON
- (none) — simulation only; never touch the physical robot.
