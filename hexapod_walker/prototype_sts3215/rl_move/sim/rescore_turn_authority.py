"""rescore_turn_authority.py — re-score probe_turn_authority.py reads
against a MATCHED CONTINUATION control instead of a frozen parent.

WHY (standwalk steering-axis dig-in, 09-04): a ~26-canary "lever
family" (yawarm/yawboost/omegaboost/combdose/selomegaboost geometry
levers on the walk+turn BC-anchor lineage) was scored FAIL/FAIL/FAIL
against a FROZEN parent checkpoint (`cap29-stdwalklo-hi{,-s1}`) that
never took the same 2M extra training steps the lever arms did. The
`cont`/`cont-s1` matched controls (09-04, same 2M continuation, ZERO
lever) found plain continuation alone already erodes pure-turn wz_med
22-35% vs the frozen parent — meaning every lever's "pure-turn
regression" was conflated with a training-time confound it didn't
cause. This tool re-derives each cell's win/lose call against the
correct (matched-continuation) comparator instead.

Two independent pieces, each testable without a live pod/ledger:
  - `ledger_cfg_args(extra_args)`: given a ledger `extra_args` list
    (as returned by `ops.sh entry <run> extra_args`, a Python-literal
    list), return the ordered non-``train.*`` ``--cfg-set`` values —
    the "FULL non-train.* cfg-set list" `probe_turn_authority.py`'s
    own CHECKPOINT-POLICY CFG WARNING requires replaying, extracted
    once instead of hand-copied per run (silent obs-width mismatches
    if a key is missed/copied stale — see that warning).
  - `summarize_probe(result_json)` / `magnitude_pct` / `rescore_cell`:
    pure grouping+arithmetic over a `probe_turn_authority.py` result
    dict, no I/O.

CLI:
  uv run python -m rl_move.sim.rescore_turn_authority cfg <run>
      -> prints ``--cfg-set k=v ...`` ready to paste into a fresh
         ``probe_turn_authority.py`` invocation for that checkpoint's
         own training cfg (minus ``train.*``).
  uv run python -m rl_move.sim.rescore_turn_authority table
      <manifest.json> <control_name> [<control_name_s1>]
      -> manifest.json maps name->probe-result-json-path; prints a
         win/lose table for every non-control entry against the named
         control(s) (entries whose name ends ``_s1``/``-s1`` use the
         second control if given).
"""
from __future__ import annotations

import argparse
import ast
import json
import statistics
import subprocess
import sys
from pathlib import Path

WZ_POS = 0.25
WZ_NEG = -0.25
VX_PURE = 0.0
VX_COMBINED = 0.08
PURE_TURN_CAP_PCT = 10.0


def ledger_cfg_args(extra_args: list[str]) -> list[str]:
    """Non-``train.*`` ``--cfg-set`` values from a ledger ``extra_args``
    list, in original order. Pure function — no ledger/pod access."""
    out: list[str] = []
    i = 0
    while i < len(extra_args):
        if extra_args[i] == "--cfg-set" and i + 1 < len(extra_args):
            key = extra_args[i + 1].split("=", 1)[0]
            if not key.startswith("train."):
                out.append(extra_args[i + 1])
            i += 2
        else:
            i += 1
    return out


def fetch_ledger_cfg_args(run: str, ops_sh: Path) -> list[str]:
    """Shells out to ``ops.sh entry <run> extra_args`` (Python-literal
    list on stdout) and applies :func:`ledger_cfg_args`."""
    raw = subprocess.check_output([str(ops_sh), "entry", run, "extra_args"])
    extra_args = ast.literal_eval(raw.decode().strip())
    return ledger_cfg_args(extra_args)


def summarize_probe(result: dict) -> dict[tuple[float, float], float]:
    """``{(wz_cmd, vx_cmd): median(wz_med across probe seeds)}`` from a
    ``probe_turn_authority.py`` ``--out`` JSON dict."""
    groups: dict[tuple[float, float], list[float]] = {}
    for r in result["results"]:
        key = (round(r["wz_cmd"], 3), round(r["vx_cmd"], 3))
        groups.setdefault(key, []).append(r["wz_med"])
    return {k: statistics.median(v) for k, v in groups.items()}


def magnitude(summary: dict[tuple[float, float], float], wz_cmd: float,
              vx_cmd: float) -> float:
    """Turn-authority magnitude in the COMMANDED direction (so a
    negative wz_cmd's more-negative wz_med reads as a BIGGER, better
    number, matching the positive-wz_cmd convention)."""
    v = summary[(round(wz_cmd, 3), round(vx_cmd, 3))]
    return -v if wz_cmd < 0 else v


def magnitude_pct(new: float, base: float) -> float:
    """% change in magnitude vs a matched-control baseline. Positive
    == more turn authority than the control (good); the caller decides
    what "good" means per clause (combined wants positive both signs,
    pure-turn wants >= -PURE_TURN_CAP_PCT)."""
    if base == 0:
        return float("inf") if new > 0 else 0.0
    return (new - base) / base * 100.0


def rescore_cell(arm: dict[tuple[float, float], float],
                  control: dict[tuple[float, float], float]) -> dict:
    """One lever-vs-control verdict cell, per the standwalk steering
    gate shape (combined wins both signs, pure-turn within the cap)."""
    pt_pos_pct = magnitude_pct(magnitude(arm, WZ_POS, VX_PURE),
                                magnitude(control, WZ_POS, VX_PURE))
    pt_neg_pct = magnitude_pct(magnitude(arm, WZ_NEG, VX_PURE),
                                magnitude(control, WZ_NEG, VX_PURE))
    cb_pos_pct = magnitude_pct(magnitude(arm, WZ_POS, VX_COMBINED),
                                magnitude(control, WZ_POS, VX_COMBINED))
    cb_neg_pct = magnitude_pct(magnitude(arm, WZ_NEG, VX_COMBINED),
                                magnitude(control, WZ_NEG, VX_COMBINED))
    pure_turn_ok = min(pt_pos_pct, pt_neg_pct) >= -PURE_TURN_CAP_PCT
    combined_win = cb_pos_pct > 0 and cb_neg_pct > 0
    return {
        "pure_turn_pct": (pt_pos_pct, pt_neg_pct),
        "combined_pct": (cb_pos_pct, cb_neg_pct),
        "pure_turn_cap_ok": pure_turn_ok,
        "combined_both_sign_win": combined_win,
        "pass": pure_turn_ok and combined_win,
    }


def _cmd_cfg(args: argparse.Namespace) -> int:
    ops_sh = Path(__file__).resolve().parents[2] / "rl_move" / "orchestrator" / "ops.sh"
    cfg = fetch_ledger_cfg_args(args.run, ops_sh)
    print(" ".join(f"--cfg-set {c}" for c in cfg))
    return 0


def _cmd_table(args: argparse.Namespace) -> int:
    manifest = json.loads(Path(args.manifest).read_text())
    summaries = {name: summarize_probe(json.loads(Path(path).read_text()))
                 for name, path in manifest.items()}
    ctrl0 = summaries[args.control]
    ctrl1 = summaries.get(args.control_s1 or args.control, ctrl0)
    for name, summary in summaries.items():
        if name in (args.control, args.control_s1):
            continue
        control = ctrl1 if name.replace("-", "_").endswith("_s1") else ctrl0
        cell = rescore_cell(summary, control)
        print(f"{name:24s} pure_turn={cell['pure_turn_pct']!r} "
              f"combined={cell['combined_pct']!r} "
              f"PASS={cell['pass']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    cfg_ap = sub.add_parser("cfg", help="print a checkpoint's replayable "
                             "non-train.* --cfg-set args from the ledger")
    cfg_ap.add_argument("run")
    cfg_ap.set_defaults(fn=_cmd_cfg)

    table_ap = sub.add_parser("table", help="re-score a manifest of "
                               "probe_turn_authority result JSONs vs a "
                               "matched-continuation control")
    table_ap.add_argument("manifest")
    table_ap.add_argument("control")
    table_ap.add_argument("control_s1", nargs="?", default=None)
    table_ap.set_defaults(fn=_cmd_table)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
