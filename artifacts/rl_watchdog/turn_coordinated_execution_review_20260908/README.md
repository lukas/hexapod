# Coordinated screen execution review

Cloud owner 20260908T071722 executed the frozen proposal from main7b9d114ef. Independent review observed the actual runner and analysis before execution, then verified their hashes matched the full result. The complete40-branch bank took21.19s; no duplicate simulation was run by this reviewer.

The registered result is STOP. All8zero controls and32pulse prefixes pass full-state checks; no action clips. Corrected retention passes30/32, with two positive-yaw .05 pulses losing too much forward progress (.85424 and.89082 ratios). Four of16positive-vector cases meet5mrad+retention, and15/16 have positive odd response. Only the negative-yaw phase0 template at.05 meets the same-start-pair rule (7.066/5.666mrad); neither dose qualifies for BOTH yaw signs. No global dose is selected; conditional holdouts and PPO are not licensed.

This is a finite test of four frozen phase templates at two total perturbation doses. It does not rule out other coordinated/state-dependent/recurring controllers. The original single-joint negative remains intact. The owner retains the full raw bank and source in artifacts/rl_watchdog/turn_coordinated_screen_20260908 on the controller and is publishing its own result.

- Bank SHA256:cacf55dc524d60cf85a3c8ca3bb74074d09ce15e31789b3b63d36d764bf7acdc.
- Runner SHA256:af61c11a55d0cb0361d6d712e348b69e98b0e59c24959ea3bf92d08ad9401ebd.
- Analysis SHA256:cf00013d238521466324799c715bb623785acd3c7aed733e30ad216a94335b77.

Audit and independent_recheck.json retain detailed provenance and predicates. No source correction or additional experiment was required.
