# Coordinated steering causal screen — frozen proposal

No new simulation or training was run. The eight independently fitted sign vectors do not yet define one controller: at matched phases, only 10–14 of 18 joint signs agree across starts. This proposal first averages each central secant across the two matched-start members, then takes its sign. The result is four frozen templates indexed only by command sign and observed phase.

`derive_templates.py` reproduces `frozen_templates.json` from the exact compact measurements in `single_joint_inputs.json`. Run `uv run python derive_templates.py`; it performs no simulation. Input, output and reviewed source-bank hashes are retained.

The common vectors’ first-order sums at amplitude 0.05 range from 5.247 to 12.427 mrad across the eight states. These finite-secant estimates are not authority bounds: summed absolute per-axis even residues range from 6.23 to 11.66 mrad, and nonlinear interactions can invalidate superposition. The 18-coordinate vector at 0.05 has L2 norm 0.2121, versus 0.05 for one axis, and 18 times the squared norm. This tests a new coordinated dose class and preserves the original 0/288 single-joint negative.

The proposed screen has 40 branches plus four continuous baseline references: eight original states, each with zero and both vector signs at amplitudes 0.025 and 0.05. Keep the frozen assets, configuration, prefix, safety and five-pulse-tick plus 75-policy-tick timing. Require full zero, prefix and endpoint parity before interpretation. All doses and mapping rules are frozen before execution.

The nearest circular phase selects one of two centers for the commanded yaw sign. Distance ties within 1e-12 rad select the lower phase index. Exact zero yaw command produces a zero vector. Choose the vector at burst start and hold it fixed throughout the five ticks; never select by start label or tick index.

Keep actual 5 mrad commanded-direction gain and corrected retention as primary. Opposite-vector controls separate odd response from even facilitation; report both. Require the expected odd direction to support the gradient-sign template. Report the stronger ±5 mrad reversal result separately. Select one global dose through the prespecified repeatability rule; do not tune by state or joint. Exact predicates appear in `screen_proposal.json`.

Support on these measured states licenses only the frozen quarter-phase tests and straight zero-off retention check. Quarter-phase states lie near template boundaries: the fixed tie rule and possible different selections across nearby starts are part of the mapping being tested. Do not repair them after seeing outcomes.

No PPO follows from in-sample improvement alone. A recurring burst or feedback schedule still needs a precise definition and validation on the original 15-second panel with both continuous yaw signs and straight motion before any conditional 2M canary. This proposal creates no new seed, training arm or simulator job.
