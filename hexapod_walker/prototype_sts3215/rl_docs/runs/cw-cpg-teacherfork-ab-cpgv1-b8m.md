# cw-cpg-teacherfork-ab-cpgv1-b8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-03T13:14:41+00:00

**pod**: hexapod-mjx-train-5

**steps**: 8000000

**parent**: cw-cpg-teacherfork-ab-cpgv1

**hypothesis**: Plain English: cpg/STATUS.md's own Next item 3 flags that ONE 2M-step data point (cw-cpg-teacherfork-ab-cpgv1, VERDICTED INFORMATIVE/WORSE-BUT-WALKING: the CPG-search motion library sustains real AMP-style walking but with det margins ~15-20% softer than the scripted teacher_v2, sto matched/better) is not enough to decide a teacher-library adoption fork -- explicitly 'not funded this cycle, amp M4 composition has GPU priority' on 08-23, now free (11 idle GPU slots, empty backlog, no cpg/amp GPU contention). Single lever vs cpgv1: --steps 2M->8M (matched-larger-budget, same BC-clone init/same reward/same amp-motion-lib=cpg_v1.npz/same seed 7), answering whether the softer-margin gap holds, closes, or widens once the discriminator+policy have a realistic training budget instead of a 2M discovery-scale snapshot.

**gate**: Read eval_amp_m5 (or the DR-0 gate + own-DR walk panel if m5 isn't wired for this lineage) det+sto walk margins (gait_valid, net fwd travel, slip/m) against BOTH style05's own numbers (the teacher_v2-library parity bar) AND cpgv1's own 2M numbers. PASS/CLOSES = margins now clear style05's bars at parity (within noise) -- promote cpg_v1 as a viable AMP style source, no adoption yet (still needs the cpg-clone-init cell before a real fork). PARTIAL = margin gap shrinks (>=30% closer to style05) but doesn't fully clear -- keep WORSE-BUT-WALKING verdict, note budget-dependence. FAIL/WIDENS = gap flat or worse than the 2M read, or any new fall/collapse -- closes the matched-larger-budget cell, leaving CPG-clone init as the only remaining lever before the adoption question is fully closed.

**verdict**: Result: FAILED at launch (infra, not a research result) -- trainer crashed immediately on hexapod-mjx-train-5 with ValueError: rl_move/sim/motion_library/cpg_v1.npz: pre-v2 motion library (None/None); rebuild it in canonical robot coordinates. Evidence: cpg_v1.npz was built 08-23, BEFORE the 09-02/09-03 joint-frame-v2 migration (multiple joint_frame/joint_contract stamping fixes landed across the codebase per RL_LOG 09-02/09-03); amp_discriminator.py's MotionLibrary loader now hard-requires joint_frame=FRAME_ROBOT_ABS + a joint_contract stamp that this npz predates and lacks, so ANY --amp-motion-lib=cpg_v1.npz run on current code will crash the same way until the library is rebuilt. Why this was launched at all: I mis-read cpg/STATUS.md -- grepped only the '## Next' section (which still lists item 3, the teacherfork-ab-cpgv1 second-data-point question, as open/'not funded this cycle, amp M4 has GPU priority' from 08-23) without first reading the file's TOP banner, which is the CURRENT state per the doc's own convention ('newest Update at the TOP'). The top banner already shows this exact question closed THREE TIMES over at matched/larger budget (ab6m pair 08-23, teacherfork-ab-cpgv1-acq1b/style05-budget2 8M pair 08-23, ab8m cpgv1r/teacherr pair 08-24) -- tracks.json cpg gate is already GREEN, adoption decision recorded (cpg_v1 = co-equal AMP style source, no forced swap). This launch was REDUNDANT on top of being broken. No relaunch: (1) the research question is already closed, (2) if a future arm genuinely needs cpg_v1.npz on current code, rebuild it first via 'build_motion_library.py --controller se2cpg --cpg-params-from rl_move/sim/policies/cpg_controller_robust120_yawtrim.json' (regenerates with current joint-frame-v2 stamping) -- filed as a maintenance item, not funded this cycle since nothing needs it. Killed the stuck INTENT launcher process (778116, orphaned after the pod-side crash) and confirmed zero trainer process alive on hexapod-mjx-train-5 -- pod is free.

