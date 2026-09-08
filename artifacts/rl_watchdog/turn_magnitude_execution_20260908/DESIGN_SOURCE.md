# Design candidate: capped magnitude allocation at the existing lower L2 budget

**DESIGN ONLY — not preregistered, implementation-reviewed, trial-ready, queued or executed.** Root requested this assessment after the completed support-yaw STOP. No new simulator response, eval, training, robot action, source-model change or publication was performed. An execution owner and separate preregistration would be needed after root review; this is not an automatic continuation of any failed protocol.

## Concrete question and recommendation

One distinct, finite question survives: does allocating the **same requested action L2 norm** according to the original measured central secants outperform the equal-magnitude sign-box allocation on previously untested phases, while clearing the original absolute yaw and retention gates?

The existing four templates discard all response magnitudes, putting equal amplitude on all 18 coordinates. At their lower tested amplitude .025, the requested L2 norm is rho = sqrt(18) × .025 = **.10606601718**. At that same norm, unconstrained magnitude weighting would need peaks **.05814/.04776/.05046/.05484**, exceeding the existing .05 per-coordinate ceiling in three templates. Clipping those vectors would silently unmatch their norms. At the higher .05-equivalent norm, the cap forces all 18 magnitudes to .05: the optimum is exactly the completed sign-box intervention and provides no new experiment.

Use one capped allocation at the lower norm instead. It asks about action allocation, not another global dose, cadence, support mask, plant setting or training seed. It is scientifically defensible as a falsifiable design candidate; the available finite secants do not predict its actual success. The original single-axis, sign-box, analytic-support and time-slicing STOPs remain unchanged.

## Exact offline rule

Use the four **unchanged mean central-secant arrays** in [frozen_templates.json](../turn_coordinated_guidance_20260908/frozen_templates.json), SHA256 **7014cf633de1e9d22996525ff0465a86819c5865dcb3e0e464996846d1027214**. These came from sign(wz) × [yaw(+.05) − yaw(−.05)] / .1, averaged across the original fixed two-start phase pairs. Do not recompute pairings, signs, source responses or weights after any new response is observed.

For each fixed template g, define

- candidate: u_j = sign(g_j) × min(.05, lambda × abs(g_j));
- comparator: b_j = .025 × sign(g_j);
- choose lambda uniquely so sum_j u_j² = 18 × .025².

This is the maximizer of the **frozen mean-secant linear surrogate** g·u subject to L2 ≤ rho and L-infinity ≤ .05. It is not an optimizer of measured new performance. Deterministic numeric recipe: float64; low = 0, high = .05 / min(nonzero abs(g)); 100 bisections using the squared coordinate sum; lambda = (low + high)/2. All current arrays have 18 nonzero entries. Zero/nonfinite input or insufficient nonzero coordinates to reach rho invalidates the design; do not choose a substitute.

[allocation_calculation.json](allocation_calculation.json) contains all four derived vectors, lambda values, source hashes, exact phase targets and source-state predictions. This is offline arithmetic only.

| Template | Capped coordinates | Candidate max coordinate | Mean linear prediction: box → candidate (mrad) |
|---|---:|---:|---:|
| negative yaw, phase 0 | 2 | .050000 | 5.058 → 7.430 |
| negative yaw, phase 1 | 0 | .047759 | 3.063 → 3.732 |
| positive yaw, phase 0 | 1 | .050000 | 4.222 → 5.104 |
| positive yaw, phase 1 | 2 | .050000 | 5.947 → 7.848 |

The source-state surrogate exceeds 5 mrad for both members of negative phase 0 and positive phase 1, but one source member worsens under weighting. **Do not select or drop templates using these predictions.** All four mappings remain fixed. These are discovery calculations, not held-out outcomes or authority bounds. Candidate L1 is .313–.373 versus comparator .45; matching L2 does not match peak dose, mechanical energy, joint work, current, clipping, actual joint motion or contact loads. The changed coordinate allocation is the intended contrast.

## Frozen source and evaluation cells

Use the exact parent yawref-cigate8m checkpoint, SHA256 **61f9c20f0f72d89217a22b47037e33c8dad2f50bfaca0a3d5517f714dd0eeb10**; full XML SHA256 **7efb8e8a0cb014c0b4bac27c41e7a85e683553168b87d85aac0d52d6a8e5a837**; original 64-key cfg SHA256 **aabf4cc25f78ebf3b28ff7b4a46fba85c109f4061becaf4212e8842b5c550e40**. Full source/assets are pinned in [reviewed bank](../turn_actionbank_review_20260908/full/bank.json); reviewed helper SHA256 **436b0eee695094f94d68346548e12efed147f087b1447ea2349b0f4feb67cd54**.

Assert full mesh 34 meshes / 159 geoms / 4.80573 kg, unchanged 400 write speed / 20 acceleration / .375° tick / 350 counts/s resolved velocity / 100 Hz, and all original safety/current settings. 350 is velocity, not current. Copy pinned assets into an isolated execution source; no regeneration or implicit current-source overrides. Keep affine joint action decoding and deterministic policy, seed **0**, DR **0**, original starts **0 and pi**, vx **.08**, wz **±.15**. Preserve one-second zero hold plus one-second linear ramp. Arc episode configuration remains ten seconds; baselines stop after 755 ticks. No new reset draws or training seeds.

## Previously frozen, unexecuted quarter-phase state rule

Reuse the **selection definition**, not an execution license, from the original coordinated proposal's unexecuted conditional holdouts. For each of its four fixed template pairs and each member (eight states total):

1. The original member has source tick P = 600 or 638 and recorded pre-action phase phi_P.
2. Target wrap(phi_P + pi/2). From the unchanged 755-tick continuous baseline, choose the pre-action tick in inclusive [P+10, P+25] with minimum circular phase distance; exact ties choose earliest tick.
3. Group the resulting two-start states by their original template pair. Freeze these eight target identities, selected ticks, actual phases and full states before any nonzero branches. Never regroup by observed gain or by which runtime template was chosen.

This uses four continuous baselines: two command signs × two initial phases. Require replay equality with the recorded original P=600/638 prefix/endpoint states and windows as well as all new zero-control full-state/trace checks. Missing or terminated states remain unavailable/nonqualifying, with no replacement.

The runtime lookup is unchanged for both candidate and comparator: observed wrapped phase chooses the nearest of the two original centers for sign(wz); circular-distance ties within 1e-12 rad choose lower phase index. The held-out targets are near lookup boundaries and paired starts may select different templates. That is part of the tested mapping; no reassignment, phase recentering or smoothing is allowed. Exact wz=0 returns all zeros. These states are held out **from the template derivation and prior pulse execution**, not independent training/reset samples.

## Finite controls and exactness

At each of the eight states, five branches: untouched zero, +u, −u, +b, −b. **40 branch slots + four continuous baselines.** Command sign is unchanged; positive/negative refer to reversing the prescribed action vector, whose source secant already includes command sign. Freeze the vector at pulse onset. Add after SB3 prediction clipping for exactly five ticks, clip to action bounds, then ordinary safety/servo/physics; follow with 75 unchanged-policy ticks.

All eight zero controls must pass full integration/controller prefix and endpoint plus scoring-window trace parity **before** nonzero branches. Every signed branch must match its zero prefix. Record requested/applied coordinate increments, L1/L2/L-infinity, clips, per-leg material slip/loaded time, relative tilt and simulated current where available. Missing current is reported, not inferred from state hashes. If action-bound clipping occurs, that state cannot support the matched-requested-allocation interpretation; record all outcomes and do not rescale or replace it. Ordinary differing servo/contact responses are part of the mechanism, not grounds to adjust the dose.

Separately, each of the two original starts gets a 15-second straight triple: untouched, candidate zero-off, comparator zero-off. **Six straight rollouts**, full trace and endpoint parity required through 1500 ticks. The original straight retention bars also apply: zero termination over the full rollout; on the unchanged post-ramp [2,15] s window, positive baseline body-forward distance, each zero-off arm forward >= .9 baseline, loaded material-contact displacement <= 1.25 baseline, relative roll/pitch maxima <= baseline +3 degrees, and all scored ticks walking. Report these explicitly even when traces match; an unhealthy baseline cannot pass by parity alone. Total finite ceiling: **50 rollouts** including baselines; no adaptive stages, extra dose or seed.

## Fixed decisions for a future preregistration

Primary G = sign(wz) × [branch yaw change − zero yaw change], retaining original last-solve world yaw; report endpoint yaw additionally. For each law, odd = (G+ − G−)/2 and even = (G+ + G−)/2.

A candidate state qualifies only with **G+ ≥ .005 rad**, odd > 0, and corrected retention in **both** +u and −u: complete 80 ticks, all walking, zero termination, positive baseline body-forward distance, forward ≥ .9 baseline, loaded material-contact displacement ≤ 1.25 baseline, relative roll/pitch maxima ≤ baseline +3°. No new chronic-leg criterion. Missing/nonfinite gate metrics invalidate interpretation.

Separate the two questions:

- **Held-out burst authority:** for each yaw sign, at least one of the two fixed quarter-phase groups must qualify at both starts under the above unchanged gate.
- **Allocation advantage:** the same qualifying group must also have G+(u) > G+(b) at both starts, with requested norms matched and no action-bound clipping. The +b comparator must complete the same finite 80-tick scoring window; a shorter endpoint cannot support a paired advantage. Report the exact paired differences; this sign criterion is not a statistical or practical-effect-size claim. The matched comparator's own original-gate status and forward/slip tradeoffs are reported completely.

Call the proposed mechanism supported only if both questions pass for both yaw signs and every exactness/straight check passes. Otherwise stop this exact proposal; report any partial authority separately without selecting another dose, retuning weights, reusing test responses, replacing phases or initiating PPO. A tiny comparative advantage is limited evidence even if absolute authority clears 5 mrad.

Even a pass would establish only this frozen allocation's held-out burst result. It would not isolate physical energy efficiency, demonstrate sustained steering or define a recurring controller. No automatic 15-second intervention, continuation, canary or PPO is included.

## Evidence limits and ownership

The four templates use closed-loop 80-tick finite secants, not infinitesimal Jacobians. Their even-axis residues are comparable to predicted gains; simultaneous mixed odd terms and contact transitions remain unmeasured. Opposite-vector controls distinguish odd response from even facilitation but cannot eliminate mixed odd nonlinearities. Same-state sign-box results, the independent geometric support STOP, and historical time-slicing negatives do not supply those missing coordinated responses. Measuring that exact held-out matched comparison is the proposed finite question; there is no justified claim that magnitude weighting will recover steering.

The active scratch cycle 20260908T093002 is independent. This artifact makes no launch or ownership claim. Root reviews the design and coordinates any later implementation; the completed failures and original continuous-joystick qualifications remain in force.
