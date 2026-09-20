"""Hardware-only metrics from the 25 pinned hexapod2 RL traces.
Per run: hold-phase loaded droop per joint (q - cmd, signed), walk-phase signed error stats,
rocking spectrum (roll & gyro_x dominant Hz vs stride Hz), timing quality, voltage-free current."""
import csv, json, sys, glob, re
import numpy as np
from pathlib import Path
D = Path('/tmp/hexapod2-replay-matrix/csv')
man = json.load(open('/Users/lukas/hexapod/hexapod_walker/prototype_sts3215/rl_move/sim/hexapod2_replay_matrix.json'))
ent = {e['filename']: e for e in man['entries']}

def load(p):
    with open(p) as fh:
        rd = csv.DictReader(fh); rows = list(rd)
    out = {}
    for k in rd.fieldnames:
        try: out[k] = np.array([float(r[k]) if r[k] not in ('', None) else np.nan for r in rows])
        except ValueError: out[k] = np.array([r[k] for r in rows])
    return out

def dom_hz(t, x, lo=0.3, hi=12.0):
    x = x - np.nanmean(x); x = np.nan_to_num(x)
    if len(x) < 64: return np.nan, np.nan
    dt = float(np.median(np.diff(t))); f = np.fft.rfftfreq(len(x), dt); p = np.abs(np.fft.rfft(x))**2
    m = (f >= lo) & (f <= hi); 
    if not m.any(): return np.nan, np.nan
    k = np.argmax(p * m); return float(f[k]), float(p[k] / p[m].sum())

rows_out = []
for p in sorted(D.glob('*.csv')):
    fn = p.name.split('__', 1)[1]
    e = ent.get(fn, {}); d = load(p)
    # Chassis tilt from the mount-corrected body_* columns ONLY; never the raw
    # uncal_*/roll_deg columns. Uncalibrated run -> NaN arrays so tilt metrics
    # come out NaN instead of silently reporting mount-uncorrected sensor tilt.
    _roll = d.get('body_roll_deg'); _pitch = d.get('body_pitch_deg')
    _tilt_ok = (_roll is not None and _pitch is not None
                and np.isfinite(_roll).any() and np.isfinite(_pitch).any())
    if not _tilt_ok:
        _roll = np.full(len(d['t_s']), np.nan)
        _pitch = np.full(len(d['t_s']), np.nan)
    t = d.get('mono_s', d['t_s']);
    if np.any(np.diff(t) <= 0): t = d['t_s']
    q = np.stack([d[f'q{i}_deg'] for i in range(18)], 1); c = np.stack([d[f'cmd{i}_deg'] for i in range(18)], 1)
    ph = d['phase'] if 'phase' in d else np.array(['walk'] * len(t))
    hold = (ph == 'hold'); walk = np.isin(ph, ['walk', 'run'])
    sgn = q - c
    r = {'run': e.get('run_id', '?'), 'file': fn, 'family': e.get('family', '?'), 'cmd': e.get('command', '?'),
         'hz': round(len(t) / (t[-1] - t[0]), 1), 'n_hold': int(hold.sum()), 'n_walk': int(walk.sum()),
         'imu_uncalibrated': not _tilt_ok}
    if hold.sum() > 10:
        # last 60% of hold rows = settled
        idx = np.where(hold)[0]; idx = idx[len(idx) // 2:]
        m = np.nanmean(sgn[idx], 0)
        r['hold_droop_hip'] = [round(float(m[1 + 3 * l]), 1) for l in range(6)]
        r['hold_droop_knee'] = [round(float(m[2 + 3 * l]), 1) for l in range(6)]
        r['hold_droop_yaw'] = [round(float(m[0 + 3 * l]), 1) for l in range(6)]
        r['hold_pose_hip'] = [round(float(np.nanmean(c[idx, 1 + 3 * l])), 1) for l in range(6)]
        r['hold_pose_knee'] = [round(float(np.nanmean(c[idx, 2 + 3 * l])), 1) for l in range(6)]
        r['hold_roll_pitch'] = [round(float(np.nanmean(_roll[idx])), 1), round(float(np.nanmean(_pitch[idx])), 1)]
    if walk.sum() > 64:
        w = np.where(walk)[0]; tw = t[w]
        err = np.abs(sgn[w])
        r['walk_err_mean'] = round(float(np.nanmean(err)), 2); r['walk_err_p95'] = round(float(np.nanpercentile(err, 95)), 1)
        # signed mean per axis: negative = under command (sag) for knee
        r['walk_signed_knee_mean'] = [round(float(np.nanmean(sgn[w, 2 + 3 * l])), 1) for l in range(6)]
        r['walk_signed_hip_mean'] = [round(float(np.nanmean(sgn[w, 1 + 3 * l])), 1) for l in range(6)]
        stride, _ = dom_hz(tw, c[w, 2]);  # knee cmd of leg 0
        st = [dom_hz(tw, c[w, 2 + 3 * l])[0] for l in range(6)]; stride = float(np.nanmedian(st))
        r['stride_hz'] = round(stride, 2)
        fr, pr = dom_hz(tw, _roll[w]); fg, pg = dom_hz(tw, d['gyro_x_dps'][w]); fp, pp = dom_hz(tw, _pitch[w])
        r['roll_dom_hz'] = round(fr, 2); r['roll_dom_frac'] = round(pr, 2); r['gyro_x_dom_hz'] = round(fg, 2); r['pitch_dom_hz'] = round(fp, 2)
        r['roll_rel_peak'] = round(float(np.nanmax(np.abs(_roll[w] - np.nanmedian(_roll[w[:5]])))), 1)
        r['roll_rms'] = round(float(np.nanstd(_roll[w])), 2); r['pitch_rms'] = round(float(np.nanstd(_pitch[w])), 2)
        r['gyro_x_rms'] = round(float(np.sqrt(np.nanmean(d['gyro_x_dps'][w] ** 2))), 1)
        # roll band power split: stride band vs 2x stride vs sub-stride
        x = np.nan_to_num(_roll[w] - np.nanmean(_roll[w])); dt = float(np.median(np.diff(tw)))
        f = np.fft.rfftfreq(len(x), dt); P = np.abs(np.fft.rfft(x)) ** 2; tot = P[f > 0.2].sum() + 1e-9
        def band(a, b): return round(float(P[(f >= a) & (f < b)].sum() / tot), 2)
        r['roll_band_sub'] = band(0.2, 0.7 * stride) if stride == stride else None
        r['roll_band_stride'] = band(0.7 * stride, 1.4 * stride) if stride == stride else None
        r['roll_band_2x'] = band(1.4 * stride, 2.6 * stride) if stride == stride else None
        r['roll_band_hi'] = band(2.6 * stride, 12) if stride == stride else None
        # timing
        if 'period_ms' in d:
            per = d['period_ms'][w]; nom = 1000.0 / r['hz']
            r['period_ms_p50_p95_max'] = [round(float(np.nanpercentile(per, 50)), 1), round(float(np.nanpercentile(per, 95)), 1), round(float(np.nanmax(per)), 1)]
            r['overrun_frac'] = round(float(np.mean(per > 1.5 * nom)), 3)
        if 'service_ms' in d: r['service_ms_p50'] = round(float(np.nanmedian(d['service_ms'][w])), 1)
        if 'stale_feedback' in d: r['stale_frac'] = round(float(np.nanmean(d['stale_feedback'][w])), 3)
        if 'position_age_ms' in d: r['pos_age_ms_p50_p95'] = [round(float(np.nanpercentile(d['position_age_ms'][w], 50)), 1), round(float(np.nanpercentile(d['position_age_ms'][w], 95)), 1)]
        if 'max_cur_a' in d: r['max_cur_a_p95'] = round(float(np.nanpercentile(d['max_cur_a'][w], 95)), 2)
        cur = np.stack([d[f'cur{i}_a'] for i in range(18)], 1)[w]
        r['cur_mean_hip_knee'] = [round(float(np.nanmean(cur[:, 1::3])), 3), round(float(np.nanmean(cur[:, 2::3])), 3)]
        r['cur_p99_joint_max'] = round(float(np.nanpercentile(cur, 99.5)), 2)
        # per-leg knee swing amplitude commanded
        r['knee_cmd_amp'] = [round(float(np.nanpercentile(c[w, 2 + 3 * l], 95) - np.nanpercentile(c[w, 2 + 3 * l], 5)), 1) for l in range(6)]
    rows_out.append(r)
json.dump(rows_out, open('/tmp/simgap/hw_metrics.json', 'w'), indent=1)
# print compact
for r in rows_out:
    print(f"{r['run']} {r['family'][:18]:<18} {r['cmd'][:22]:<22} hz={r['hz']:<5} hold={r['n_hold']:<4} walk={r['n_walk']:<5}", end=' ')
    if 'hold_droop_knee' in r: print(f"droopK={r['hold_droop_knee']} droopH={r['hold_droop_hip']} tilt={r['hold_roll_pitch']}", end=' ')
    if 'stride_hz' in r: print(f"| stride={r['stride_hz']} rollHz={r['roll_dom_hz']}({r['roll_dom_frac']}) gxHz={r['gyro_x_dom_hz']} bands sub/str/2x/hi={r['roll_band_sub']}/{r['roll_band_stride']}/{r['roll_band_2x']}/{r['roll_band_hi']} rollpk={r['roll_rel_peak']} rms={r['roll_rms']} err={r['walk_err_mean']}/{r['walk_err_p95']} per={r.get('period_ms_p50_p95_max')} ovr={r.get('overrun_frac')} stale={r.get('stale_frac')} posage={r.get('pos_age_ms_p50_p95')} cur={r['cur_mean_hip_knee']} kneeamp={r['knee_cmd_amp']}", end='')
    print()
