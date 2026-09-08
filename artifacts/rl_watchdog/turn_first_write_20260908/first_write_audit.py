"""Frozen offline first-write arithmetic. No policy, helper or simulator imports."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CHAIN = ROOT / 'artifacts/rl_watchdog/turn_control_chain_20260908/full'
MAG = ROOT / 'artifacts/rl_watchdog/turn_magnitude_execution_20260908'
MODES = ('candidate_plus', 'candidate_minus', 'comparator_plus', 'comparator_minus')
LO = np.tile(np.array([-35., -80., -20.]) * (np.pi / 180), 6)
HI = np.tile(np.array([35., 40., 150.]) * (np.pi / 180), 6)
ATOL = 2e-15  # Validation arithmetic only; never zero classification/dose parity.

def read(p):
    return json.loads(Path(p).read_text())

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dump(p, x):
    def encode(v):
        if isinstance(v, np.ndarray): return v.tolist()
        if isinstance(v, np.generic): return v.item()
        raise TypeError(type(v).__name__)
    Path(p).write_text(json.dumps(x, indent=2, default=encode, allow_nan=False) + '\n')

def numeric(x, shape=None):
    a = np.asarray(x)
    if a.dtype.hasobject or a.dtype.kind not in 'bifu' or not np.isfinite(a).all():
        raise ValueError('invalid numeric data')
    if shape is not None and a.shape != shape:
        raise ValueError(f'shape {a.shape} != {shape}')
    return a

def vec(x):
    return numeric(x, (18,)).astype(float)

def exact(a, b, label):
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape or a.dtype != b.dtype or a.tobytes() != b.tobytes():
        raise ValueError('exact parity: ' + label)

def arithmetic(a, b, label):
    a, b = numeric(a), numeric(b)
    if a.shape != b.shape or not np.allclose(a, b, rtol=0, atol=ATOL):
        raise ValueError('arithmetic parity: ' + label)
    return float(np.max(np.abs(a - b)))

def decode(action, center, half):
    a = numeric(action)
    if a.shape[-1:] != (18,) or np.any(np.abs(a) > 1):
        raise ValueError('invalid decoder action')
    c, h = vec(center), vec(half)
    if np.any(h <= 0): raise ValueError('invalid half range')
    return c + a.astype(float) * h

def safe_target(q, last, cap, lo=LO, hi=HI):
    q, last, cap = numeric(q), numeric(last), numeric(cap)
    if q.shape != last.shape or q.shape[-1:] != (18,) or np.any(cap <= 0):
        raise ValueError('invalid safety projection inputs')
    lo, hi = vec(lo), vec(hi)
    if np.any(lo >= hi): raise ValueError('invalid joint limits')
    return np.clip(last + np.clip(q - last, -cap, cap), lo, hi)

def logical_to_mj(q):
    q = numeric(q).astype(float).copy()
    if q.shape[-1:] != (18,): raise ValueError('invalid joint frame shape')
    q[..., 2::3] -= q[..., 1::3]
    return q

def inject(action, delta):
    a = numeric(action, (18,))
    d = vec(delta)
    if np.any(np.abs(a) > 1) or np.any(np.abs(d) > .05):
        raise ValueError('outside frozen action/dose bounds')
    # Exact operations in the archived WrappedPredictor.predict.
    raw = np.asarray(a, dtype=np.float32).copy() + d
    clipped = np.clip(raw, -1., 1.)
    changed = clipped.astype(np.float32)
    return dict(raw=raw, clipped=clipped, changed=changed,
                applied=changed - a, clip_hits=int(np.count_nonzero(raw != clipped)))

def classify(decoded_delta, safe_delta):
    d, s = vec(decoded_delta), vec(safe_delta)
    dn, sn = float(np.linalg.norm(d)), float(np.linalg.norm(s))
    return dict(decoded_l2_rad=dn, safe_l2_rad=sn,
                ratio=sn / dn if dn > 0 else None,
                masked=(d != 0) & (s == 0),
                nonzero_decoded_coordinates=int(np.count_nonzero(d)),
                nonzero_safe_coordinates=int(np.count_nonzero(s)),
                all_safe_coordinates_unchanged=bool(np.all(s == 0)))

def validate_cell(z, metadata, ticks):
    """Validate unchanged arithmetic for every archived baseline control row."""
    exact(z['control__tick'], np.arange(ticks), 'control index')
    for key in ('control__policy_action', 'control__env_input_action',
                'control__decoder_action', 'control__decoded_logical_rad',
                'control__safety_input_logical_rad', 'control__safety_previous_logical_rad',
                'control__safety_output_logical_rad', 'control__latched_logical_rad',
                'commands__q_mj_rad'):
        numeric(z[key], (ticks, 18))
        expected_dtype = np.float32 if key in ('control__policy_action', 'control__env_input_action') else np.float64
        if z[key].dtype != np.dtype(expected_dtype):
            raise ValueError('changed original dtype: ' + key)
    for key, wanted in (('control__decoder_ok', True), ('control__safety_ok', True),
                        ('control__safety_held', False), ('control__safety_terminate', False),
                        ('control__terminated', False), ('control__truncated', False)):
        if not np.all(numeric(z[key], (ticks,)) == wanted):
            raise ValueError('unhealthy/missing baseline state: ' + key)
    for key in ('control__decoder_reason', 'control__safety_reason'):
        if np.asarray(z[key]).shape != (ticks,) or np.any(z[key] != ''):
            raise ValueError('nonempty/missing status reason')
    if np.any(numeric(z['control__safety_entry_ramp_s'], (ticks,)) != 0):
        raise ValueError('entry ramp active')
    if not np.all(numeric(z['control__command_count'], (ticks,)) == 1):
        raise ValueError('missing/extra actual command')
    exact(z['control__command_start'], np.arange(ticks), 'command offset')
    exact(z['commands__tick'], np.arange(ticks), 'actual command chronology')
    exact(z['control__policy_action'], z['control__env_input_action'], 'policy/environment action')
    exact(z['control__decoder_action'], z['control__policy_action'].astype(float), 'unmodified decoder input')
    center, half = metadata['affine_center_rad'], metadata['affine_half_range_rad']
    q = decode(z['control__decoder_action'], center, half)
    e1 = arithmetic(q, z['control__decoded_logical_rad'], 'affine decode')
    exact(z['control__decoded_logical_rad'], z['control__safety_input_logical_rad'], 'decoder/safety input')
    cap = numeric(z['control__safety_max_delta_rad'], (ticks,))
    if np.any(cap != np.deg2rad(.375)): raise ValueError('changed slew contract')
    s = safe_target(q, z['control__safety_previous_logical_rad'], cap[:, None])
    e2 = arithmetic(s, z['control__safety_output_logical_rad'], 'rate and joint limits')
    exact(z['control__safety_output_logical_rad'], z['control__latched_logical_rad'], 'safe/latched')
    e3 = arithmetic(logical_to_mj(s), z['commands__q_mj_rad'], 'actual native command')
    return dict(ticks=ticks, actual_writes=ticks, decode_max_error_rad=e1,
                safe_max_error_rad=e2, write_max_error_rad=e3)

def verify(spec):
    if spec['runner_sha256'] != sha(__file__): raise ValueError('runner changed')
    for relative, expected in spec['input_sha256'].items():
        if sha(ROOT / relative) != expected: raise ValueError('input changed: ' + relative)

def run(spec, out):
    out.mkdir(parents=True, exist_ok=False)
    dump(out / 'manifest.json', dict(status='STARTED_OFFLINE_ONLY', preregistration=spec))
    try:
        verify(spec)
        baseline, validation = {}, []
        for cell in spec['baseline_cells']:
            cid, n = cell['id'], cell['ticks']
            meta = read(CHAIN / (cid + '.json'))
            with np.load(CHAIN / (cid + '_chain.npz'), allow_pickle=False) as f:
                z = {k: f[k] for k in f.files}
            validation.append(dict(id=cid, **validate_cell(z, meta['metadata'], n)))
            baseline[cid] = (z, meta)
        if sum(v['ticks'] for v in validation) != 6020:
            raise ValueError('fixed 6020 baseline coverage not met')
        dump(out / 'baseline_validation.json', validation)
        selected = {s['state_id']: s for s in read(MAG / 'full_recovered/selected_states_frozen.json')}
        templates = {t['template_id']: t for t in read(MAG / 'frozen_vectors.json')['templates']}
        if set(selected) != {s['state_id'] for s in spec['states']}:
            raise ValueError('frozen state inventory mismatch')
        rows = []
        for item in spec['states']:
            sid, p, cid = item['state_id'], item['p'], item['baseline_id']
            sel = selected[sid]
            z, meta = baseline[cid]
            if sel['p'] != p or sel['cell'] != item['cell']:
                raise ValueError('frozen state identity changed')
            if meta['full_states'][str(p)] != sel['prefix']:
                raise ValueError('complete baseline prefix mismatch')
            if float(z['control__phase_pre'][p]) != sel['actual_phase']:
                raise ValueError('onset phase identity mismatch')
            action = z['control__policy_action'][p]
            previous = z['control__safety_previous_logical_rad'][p]
            cap = float(z['control__safety_max_delta_rad'][p])
            center, half = meta['metadata']['affine_center_rad'], meta['metadata']['affine_half_range_rad']
            q0 = decode(action.astype(float), center, half)
            safe0 = safe_target(q0, previous, cap)
            zero = inject(action, np.zeros(18))
            exact(zero['changed'], action, 'zero action ' + sid)
            exact(safe_target(decode(zero['changed'], center, half), previous, cap), safe0, 'zero safe ' + sid)
            for mode in MODES:
                archived = read(MAG / 'full_recovered/rows' / (sid + '_' + mode + '.json'))
                if archived['prefix'] != sel['prefix'] or archived['p'] != p or archived['cell'] != item['cell']:
                    raise ValueError('archived branch prefix/identity mismatch')
                d = archived['controller_state']['doses']
                if len(d) != 5 or [x['tick'] for x in d] != list(range(p, p + 5)):
                    raise ValueError('archived pulse coverage mismatch')
                source_vector = archived['controller_state'][
                    'candidate_vector' if mode.startswith('candidate') else 'comparator_vector']
                template = templates[archived['controller_state']['mapping']['template_id']]
                vector_key = 'candidate_vector' if mode.startswith('candidate') else 'comparator_vector'
                exact(vec(source_vector), vec(template[vector_key]), 'canonical frozen vector')
                requested = vec(source_vector) * (1 if mode.endswith('_plus') else -1)
                exact(requested, np.asarray(d[0]['requested'], dtype=float), 'frozen first request')
                result = inject(action, requested)
                exact(result['applied'].astype(float), np.asarray(d[0]['applied'], dtype=float), 'archived first applied dose')
                if result['clip_hits'] != d[0]['clip_hits']: raise ValueError('archived clip count')
                q1 = decode(result['changed'].astype(float), center, half)
                safe1 = safe_target(q1, previous, cap)
                dd, sd = q1 - q0, safe1 - safe0
                row = dict(id=archived['id'], state_id=sid, mode=mode, tick=p,
                    source_complete_state_sha256=sel['prefix']['complete_state_sha256'],
                    baseline_action=action, requested_action_increment=requested,
                    applied_action_increment=result['applied'], action_clip_hits=result['clip_hits'],
                    decoded_delta_logical_rad=dd, safe_delta_logical_rad=sd,
                    write_delta_mj_rad=logical_to_mj(safe1) - logical_to_mj(safe0),
                    **classify(dd, sd))
                rows.append(row)
                dump(out / (archived['id'] + '.json'), row)
        if len(rows) != 32: raise ValueError('fixed32 onset inventory not met')
        dump(out / 'summary.json', dict(status='VALID_ALGEBRAIC_FIRST_WRITE_AUDIT',
            baselines=6, baseline_ticks=6020, onset_states=8, archived_first_writes=32,
            all_zero_safe_first_writes=sum(r['all_safe_coordinates_unchanged'] for r in rows),
            first_write_only=True, simulator_rollouts=0, new_controller=False, no_PPO=True,
            causal_limit='No conclusion about subsequent four pulse ticks, delayed profile transmission or plant/yaw efficacy. Previous STOPs and criteria unchanged.'))
    except Exception as exc:
        dump(out / 'failure.json', dict(status='INVALID_OFFLINE_AUDIT', error=repr(exc)))
        raise

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    run(read(HERE / 'PREREGISTRATION.json'), args.out)

if __name__ == '__main__': main()
