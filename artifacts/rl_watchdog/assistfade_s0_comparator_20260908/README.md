# Assisted s0 exact-comparator correction

This record compares existing reports; no evaluation or training was rerun.

The candidate is `cw-assistfade-rung3-legdutyratio-s0`. Its single-lever
control is `cw-assistfade-rung3-residualfade-s0`, not the
`nostdanneal` descendant. Both matched reports have policy std 0.052,
4.80573 kg `mesh_mjx_twin` (0 mesh assets), and the same 100 Hz motor
contract. Only the four duty-charge settings differ scientifically in
the recorded launch arguments. Both start from random weights with
seed 0; neither uses `--init-from`.

Correct gait-valid count: **16/24 -> 15/24**. Safety terminations:
**7/24 -> 9/24**. Nominal det/sto gait is already 6/6 in the control.
Nominal deterministic progress/slip improve; nominal stochastic
progress/slip do not. Differing jitter termination times limit
interpretation of full-episode means.

`comparison.json` includes exact source paths/checkpoints, model and
motor identity, full launch argv, their hashes, and selected per-episode
values. It was prepared against local base `6d09c28d7`, using native
RL MCP report and ledger reads. The broad baseline run-name lookup
returned the nostdanneal descendant first; the exact `_gate` suffix
resolved the intended report, verified by its header and checkpoint.

The correction withdraws the asserted opposite-seed recovery and its
DIG-IN premise. It neither issues a formal verdict nor establishes
statistical equivalence, mechanism-class failure, or eligibility for
more training. A low-duty penalty does not directly target a fully
planted high-duty leg. Historical RL_LOG text is retained with an
appended correction.
