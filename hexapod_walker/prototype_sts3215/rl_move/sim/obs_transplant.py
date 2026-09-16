"""Policy warm-start across obs-layout changes (SB3 policies; torch is
imported lazily) and the privileged-dim index both trainers share."""
from __future__ import annotations

from .cfg_set import _parse_cfg_set


def _privileged_idx(args, n_obs: int) -> tuple[int, ...]:
    """Obs indices of the privileged measured-velocity dims (asym critic).

    Frame layout (walk task): [.., 2 measured-vel, (2 phase if
    goal.walk_phase_obs), (1 wz_ref if goal.walk_yaw_cmd), (6 mode
    one-hot if obs.mode_onehot)]. With obs.history_frames=K the frame
    repeats K times (newest first), so the vel dims recur once per
    frame. The old hardcoded (-2, -1) is the K=1, extras-off special
    case. (walk_yaw_cmd was MISSING here until 08-11 — latent, never
    hit: ledger audit shows only cw-walk-aac-s1b/-s1c ever passed
    --asym-critic, both yaw/phase-off; fixed while adding the mode
    one-hot so the tail accounting is complete.)
    """
    ov = _parse_cfg_set(getattr(args, "cfg_set", None))
    k = max(1, int(ov.get("obs.history_frames", 1)))
    off = 2
    if ov.get("goal.walk_phase_obs", 0.0) == 1.0:
        off += 2
    if ov.get("goal.walk_yaw_cmd", 0.0) == 1.0:
        off += 1
    if ov.get("obs.mode_onehot", 0.0) == 1.0:
        off += 6
    if n_obs % k:
        raise SystemExit(f"obs width {n_obs} not divisible by "
                         f"history_frames {k}")
    w = n_obs // k
    return tuple(i * w + w - off + j for i in range(k) for j in (0, 1))


def pad_obs_transplant(old_model, new_model, n_pad: int,
                       insert_at: int = -1) -> None:
    """Transplant policy weights across an obs WIDENING of ``n_pad`` dims.

    By default (``insert_at=-1``) the new dims must be appended at the
    END of the obs vector (walk phase clock, +2). With ``insert_at>=0``
    the ``n_pad`` new dims are INSERTED at that column index instead —
    needed when the widening dim sits mid-layout (e.g. the wz_ref yaw
    command appends before an existing fault_health tail block, so the
    old tail columns must shift right, not stay in place). Either way
    every tensor whose shape matches copies exactly; the first-layer
    weights of the policy/value MLPs gain ``n_pad`` zero columns, so
    the transplanted policy's outputs are bit-identical to the parent
    for ANY value of the new dims until training moves the zero
    columns. Optimizer state is fresh (architecture changed).
    NOTE: ``insert_at`` is a raw column index into the FLATTENED obs;
    with obs-history stacking (obs.history_frames>1) a mid-layout
    insertion applies per frame and is NOT expressible here — do not
    use ``insert_at`` on stacked-history lineages.
    """
    import torch
    n_new = int(new_model.observation_space.shape[0])
    n_old = int(old_model.observation_space.shape[0])
    if n_new - n_old != n_pad:
        raise SystemExit(
            f"--obs-pad-transplant {n_pad} but obs widened by "
            f"{n_new - n_old} ({n_old} -> {n_new}); check cfg-sets")
    if insert_at >= 0 and insert_at > n_old:
        raise SystemExit(
            f"--obs-pad-insert-at {insert_at} out of range for parent "
            f"obs width {n_old}")
    sd_old = old_model.policy.state_dict()
    sd_new = new_model.policy.state_dict()
    if set(sd_old) != set(sd_new):
        raise SystemExit("state_dict key mismatch; transplant needs the "
                         "same net_arch as the parent")
    widened = []
    with torch.no_grad():
        for k, v_new in sd_new.items():
            v_old = sd_old[k]
            if v_new.shape == v_old.shape:
                v_new.copy_(v_old)
            elif (v_new.dim() == 2 and v_new.shape[0] == v_old.shape[0]
                  and v_new.shape[1] == n_new
                  and v_old.shape[1] == n_old):
                v_new.zero_()
                if insert_at < 0:
                    v_new[:, :n_old].copy_(v_old)
                else:
                    v_new[:, :insert_at].copy_(v_old[:, :insert_at])
                    v_new[:, insert_at + n_pad:].copy_(
                        v_old[:, insert_at:])
                widened.append(k)
            else:
                raise SystemExit(f"unexpected shape change for {k}: "
                                 f"{tuple(v_old.shape)} -> "
                                 f"{tuple(v_new.shape)}")
    new_model.policy.load_state_dict(sd_new, strict=True)
    where = ("appended at tail" if insert_at < 0
             else f"inserted at col {insert_at}")
    print(f"[train] obs-pad transplant: {n_old} -> {n_new} dims "
          f"({where}); zero-padded first-layer columns in {widened}")


def hist_stride_transplant(old_model, new_model, stride: int,
                           hist_frames: int) -> None:
    """Warm-start across a history-stack DENSIFICATION (rate conversion).

    The obs is a newest-first frame stack ``[f(t), f(t-1), ...]``. When
    the control rate rises by ``stride`` (e.g. 4 for 25 Hz -> 100 Hz)
    and ``obs.history_frames`` rises by the same factor (16 -> 64), the
    parent's frame k (k old ticks = k*stride new ticks ago) lives at the
    child's frame ``k*stride``. First-layer columns of the policy/value
    MLPs are scattered to those slots and every other column is zeroed,
    so the transplanted policy computes the parent's function of the
    rate-matched (old-cadence-spaced) frames (measured max action diff
    7e-6 on the cw_arch_hist16 parent — float32 matmul summation-order
    noise from the wider first layer, not a mapping error) until
    training moves the zero columns. Every same-shape tensor copies exactly; optimizer
    state is fresh (architecture changed). A tail-append zero-pad
    (``pad_obs_transplant``) is WRONG for this conversion: it would map
    the parent onto the newest ``hist_old`` frames — a window ``stride``x
    shorter in wall clock than the parent ever saw.
    """
    import torch
    stride = int(stride)
    hist_frames = int(hist_frames)
    n_new = int(new_model.observation_space.shape[0])
    n_old = int(old_model.observation_space.shape[0])
    if stride < 2:
        raise SystemExit("--hist-stride-transplant needs stride >= 2")
    if hist_frames < stride or hist_frames % stride:
        raise SystemExit(
            f"--hist-stride-transplant {stride} needs obs.history_frames "
            f"divisible by the stride (got {hist_frames})")
    if n_new % hist_frames:
        raise SystemExit(
            f"obs dim {n_new} is not a multiple of obs.history_frames "
            f"{hist_frames}; check cfg-sets")
    width = n_new // hist_frames
    hist_old = hist_frames // stride
    if n_old != hist_old * width:
        raise SystemExit(
            f"parent obs {n_old} != {hist_old} frames x {width} dims — "
            "parent/child per-frame obs contracts differ; align cfg "
            "before transplanting")
    sd_old = old_model.policy.state_dict()
    sd_new = new_model.policy.state_dict()
    if set(sd_old) != set(sd_new):
        raise SystemExit("state_dict key mismatch; transplant needs the "
                         "same net_arch as the parent")
    widened = []
    with torch.no_grad():
        for k, v_new in sd_new.items():
            v_old = sd_old[k]
            if v_new.shape == v_old.shape:
                v_new.copy_(v_old)
            elif (v_new.dim() == 2 and v_new.shape[0] == v_old.shape[0]
                  and v_new.shape[1] == n_new
                  and v_old.shape[1] == n_old):
                v_new.zero_()
                for f in range(hist_old):
                    dst = f * stride * width
                    v_new[:, dst:dst + width].copy_(
                        v_old[:, f * width:(f + 1) * width])
                widened.append(k)
            else:
                raise SystemExit(f"unexpected shape change for {k}: "
                                 f"{tuple(v_old.shape)} -> "
                                 f"{tuple(v_new.shape)}")
    new_model.policy.load_state_dict(sd_new, strict=True)
    print(f"[train] hist-stride transplant: {n_old} -> {n_new} dims "
          f"({hist_old} -> {hist_frames} frames x {width}, stride "
          f"{stride}); scattered first-layer columns in {widened}")
