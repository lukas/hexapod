"""Summarize turn-traction probe JSONs into the mechanism-decision table.

Mechanism A (friction-cone saturation): slipping loaded pads sit near
the cone (frac_slip_near_cone high, cone_usage_max_med_on_slip ~1).
Mechanism B (opposing-stance cancellation): net yaw moment is a small
difference of large opposing per-leg terms (net_over_gross low) and/or
slip happens at LOW cone usage.
"""
import json
import sys
import numpy as np


def cellkey(r):
    return f"({r['cell'][0]:.2f},{r['cell'][1]:+.2f})@{r.get('phase_offset', 0):.2f}"


def agg(vals):
    v = [x for x in vals if x is not None]
    return float(np.median(v)) if v else None


def show_audit(path):
    data = json.load(open(path))
    print(f"\n=== {data['label']} (engine={data['engine']}, "
          f"policy={data['policy']}) ===")
    for r in data["results"]:
        a = r["contact_audit"]
        t = a["traction"]
        yb = t["yaw_budget"]
        am = a["angmom_check"]
        pf = t["per_foot"]
        legs = sorted(pf, key=int)
        usage_med = [pf[f]["cone_usage_max_med"] for f in legs]
        fsn = [pf[f]["frac_slip_near_cone"] for f in legs]
        fsl = [pf[f]["frac_slip_low_cone"] for f in legs]
        slipn = [pf[f]["slip_substeps"] for f in legs]
        taus = [pf[f]["tau_z_med_loaded_Nm"] for f in legs]
        fn = [pf[f]["fn_med_N"] for f in legs]
        sat = t["actuator_force_saturation_stance"]
        print(f"\n cell {cellkey(r)} fell={r['fell']} "
              f"wz_med={r['wz_med']:+.4f} vx_med={r['vx_med']:.4f}")
        print(f"  angmom: valid={am['valid']} relRMS={am['relative_rms_residual']:.4f} "
              f"slope={am['slope']:.3f}" if am["slope"] is not None else
              f"  angmom: valid={am['valid']}")
        print(f"  yaw_budget: net={yb['net_tau_z_med_Nm']:+.4f} "
              f"pos={yb['pos_sum_med_Nm']:.4f} neg={yb['neg_sum_med_Nm']:.4f} "
              f"net/gross={yb['net_over_gross_med']:.3f} "
              f"couple_share={yb['couple_imp_share_of_net']:.3f}")
        print(f"  per-leg fn_med(N):        "
              + " ".join(f"{v:7.2f}" if v is not None else "   None" for v in fn))
        print(f"  per-leg tau_z med (Nm):   "
              + " ".join(f"{v:+7.4f}" if v is not None else "   None" for v in taus))
        print(f"  per-leg cone_use max med: "
              + " ".join(f"{v:7.3f}" if v is not None else "   None" for v in usage_med))
        print(f"  per-leg slip substeps:    "
              + " ".join(f"{v:7d}" for v in slipn))
        print(f"  per-leg P(near-cone|slip):"
              + " ".join(f"{v:7.3f}" if v is not None else "   None" for v in fsn))
        print(f"  per-leg P(low-cone |slip):"
              + " ".join(f"{v:7.3f}" if v is not None else "   None" for v in fsl))
        print(f"  act rail frac: yaw={sat['yaw']['frac_at_rail']} "
              f"hip={sat['hip']['frac_at_rail']} knee={sat['knee']['frac_at_rail']} "
              f"(med {sat['yaw']['force_sat_med']:.3f}/"
              f"{sat['hip']['force_sat_med']:.3f}/"
              f"{sat['knee']['force_sat_med']:.3f})")


def show_tick(path):
    data = json.load(open(path))
    print(f"\n=== {data['label']} (engine=tick, static validation) ===")
    for r in data["results"]:
        sc = r["static_check"]
        print(f" cell {cellkey(r)}: sum_normal/weight={sc['sum_normal_over_weight']:.4f} "
              f"sign={sc['sign_convention']:+.0f} "
              f"touch_relerr={sc['touch_vs_contactN_med_relerr']:.4f} "
              f"tang/norm={sc['tangential_over_normal_med']:.4f} "
              f"mu={sc['static_mu_min']:.2f} "
              f"| dyn touch_relerr={r['touch_vs_contactN_med_relerr_dynamic']:.4f} "
              f"| angmom corr={r['angmom_check']['corr_net_tau_vs_dLdt']:.3f} "
              f"| net/gross={r['yaw_budget']['net_over_gross_med']:.3f} "
              f"wz={r['body']['wz_med']:+.4f}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        if "tick" in p:
            show_tick(p)
        else:
            show_audit(p)
