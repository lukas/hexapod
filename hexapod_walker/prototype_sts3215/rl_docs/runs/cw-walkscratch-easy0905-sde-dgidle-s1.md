# cw-walkscratch-easy0905-sde-dgidle-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-05T16:45:46+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**hypothesis**: Plain English: does pairing the structural per-leg walk_duty_gate (blocks single-leg-park) with the direct along-speed anti-idle price k_walk_idle_charge (blocks whole-body freeze/vibration-in-place) escape the static-quiver absorbing state that bare walk_duty_gate alone (sde-dgfresh-s0/s0b, sdehalfgrav-dgfresh-s0, 3/3 FAIL) could not? CAVEAT this hypothesis must carry: an anti-idle price is NOT untested on this recipe -- sde-idleterm-{s0,s1} already ran k_park_duty=4.0+k_walk_idle_charge=2.0 (same dose here) plus a HARD qvel-based safety.walk_idle_terminate_s=3.0 on this exact sde/easy0905 base and STILL froze (on-screen speed 0.001-0.032 m/s): the qvel-terminate got jitter-dodged by servo micro-vibration (mean|qvel|>=2deg/s with no coherent stepping -- the SAME vibration-not-stride signature the bare-duty-gate freeze shows), and the soft idle-charge alone was simply paid down as an accepted ongoing cost, never escaped, in 2M. This arm swaps the OLD flat k_park_duty for walk_duty_gate (proven to structurally block one-leg-park, unlike k_park_duty) and DROPS the dodgeable qvel-terminate entirely (k_walk_idle_charge's own along-speed EMA prices BODY displacement, not joint motion -- harder to fake via leg jitter alone) -- a genuinely new combination, not a repeat. If-true: real six-leg forward progress (fwd well above the ~0.06m det floor already seen, ideally >0.3m/20s, stride_m_mean clearly above 0.01) emerges or is visibly progressing -- license a 40M acquisition continuation. If-false (freeze/vibration-in-place again): this is the THIRD independently-designed price/termination mechanism (after walk_gait_gate+k_step_event, and k_park_duty+k_walk_idle_charge+qvel-terminate) to fail on this exact recipe -- treat 'reward-shaping alone escapes the sde/easy0905 frozen basin' as CLOSED and escalate to a structural fix (BC/CPG-seeded init, higher entropy/exploration schedule, or a moving-state curriculum start) rather than a 4th price variant.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. 2M canary: det walk forward_dist_m / stride_m_mean clearly nonzero and NOT matching the disqualified freeze fingerprint (fwd med <=0.1m AND stride_m_mean <=0.005m with duty>=0.5 on most legs, per sde-dgfresh-s0's own report.json); env/walk_duty_gate_factor and the along-speed EMA both show real, even partial, engaged forward motion (not just high per-tick duty from vibration); reward not pinned flat/near-zero for the whole run. PASS licenses a 40M acquisition continuation; FAIL (freeze/vibration-in-place matching sde-dgfresh-s0 or sde-idleterm-s0/s1) closes reward-shaping-alone repair for this recipe -- next lever must be structural, not a further price/termination variant.

