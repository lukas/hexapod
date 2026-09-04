# Easier walking curriculum — operator directive (2026-09-03)

## Decision

Reopen the walking-discovery question as a new pragmatic curriculum. Do not
rewrite or weaken the retired `walkcurr` result: raw-joint, prior-free PPO was
an honest negative result. For this line, "from scratch" means random neural
network weights, not absence of locomotion structure.

The goal is to make the task easy enough that a randomly initialized actor
first produces a real six-leg forward walk, then remove assistance one rung at
a time. If a rung fails, move toward more assistance. Do not launch another
raw-joint reward-dose or architecture sweep.

## Evidence already established

- No phase, phase observation alone, and phase plus a small alternating-tripod
  contact reward all failed to leave the static basin at full budget.
- The scripted tripod teacher walks on the mesh/100 Hz contract.
- BC-cloned and BC-anchored policies can walk. Therefore the fully assisted
  endpoint is already proven and must not be duplicated.
- Standing-centered action bias is required; zero action must not map to the
  old belly-sit pose.

## Assistance-removal ladder

Run only the first unproven rung. Advance after a behavioral pass; retreat one
rung after a clear aligned failure.

0. **Proven endpoint (do not rerun):** scripted-tripod BC clone / persistent BC
   anchor.
1. **BC initialization, then task-only PPO:** initialize a compact centralized
   MLP from the proven scripted-tripod clone, remove ongoing BC/AMP/imitation
   loss, and train only fixed forward walking. This tests whether RL can retain
   and stabilize a gait without continuing teacher supervision.
2. **Anchor fade:** random actor weights with a strong BC anchor initially;
   anneal the anchor smoothly to zero only after deterministic walking passes.
3. **Residual fade:** actor controls bounded residuals around the scripted
   tripod reference; progressively increase residual authority while reducing
   reference amplitude. Keep gait phase observable.
4. **Phase/contact only:** already failed under the prior reward stack. Revisit
   only after a successful assisted rung supplies an explicit reverse
   curriculum and matched intermediate-state semantics bank.
5. **Raw-joint prior-free PPO:** retired negative result; not a launch target.

## First unproven canary

Before launching, search the ledger for an exact existing equivalent. If none
exists, create a new registered track/scope and launch two seeds of rung 1:

- mesh model, 100 Hz;
- compact centralized MLP;
- fixed forward command, initially 0.04-0.06 m/s;
- walk-only episodes, 8-12 s, no stops or command resampling;
- DR0, no pushes, no yaw, no terrain variation;
- standing-centered action bias;
- initialize from the proven scripted-tripod BC clone;
- no BC anchor, imitation loss, AMP reward, or scripted action target during
  PPO;
- modest posture/height regularization and forward-course income;
- initially weak slip, action-rate, current, and fall costs so an imperfect
  first step is better than standing still;
- anneal exploration noise toward the already-proven low walking-noise range.

If an exact rung-1 experiment already passed, skip directly to rung 2. If it
failed because the gait was destroyed immediately, start rung 2 with a slower
anchor fade or rung 3 with tighter residual bounds; do not retry it with reward
dose changes alone.

## Behavioral gate

This is an ignition gate, not the final joystick gate. Pass only when both
seeds show, in deterministic held-out video/eval:

- sustained forward translation for the full episode;
- repeated alternating support transitions;
- all six legs participating, with no permanently planted or unloaded leg;
- zero falls and zero safety terminations;
- progress ratio at least 0.35.

Record slip and current, but do not require the mature joystick slip threshold
at ignition. Once walking passes, harden one dimension at a time: speed band,
fixed headings, command changes/stops, yaw, then DR/pushes.

## Process requirements

- Build an intermediate-state semantics bank before any new reward mechanism:
  weight shift, one useful lift, one forward placement, one support transition,
  two steps then fall, static stand, and clean gait.
- Use matched controls and seed replication.
- Judge video and held-out behavior above training return.
- Keep this simulation-only; do not move or command the physical robot.
