#!/usr/bin/env python3
"""Prove the L0 runner's single-transient /api/errors tolerance is narrow.

Runs against the REAL row recorded by the L1 sibling at 05:14:30.087Z
(artifacts/l1_belly_rest_hysteresis_9e65cca8/run2/new_error_rows.json), so
the positive case is a row this rig actually produced, not a mock.
"""
import importlib.util, json, os, pathlib, sys

os.environ.setdefault("OUT_DIR", "/tmp/l0_tolerance_test")
os.environ.setdefault("PROTOCOL", "/dev/null")
HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "l0runner", HERE / "guarded_runner_l0_hysteresis.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

REAL = json.loads((HERE.parent / "l1_belly_rest_hysteresis_9e65cca8"
                   / "run2" / "new_error_rows.json").read_text())[0]
fails = []


def check(label, row, want):
    ok, why = r._tolerable_bus_timing(row)
    tag = "ok " if ok == want else "FAIL"
    if ok != want:
        fails.append(label)
    print(f"  [{tag}] tolerable={ok!s:5} want={want!s:5}  {label}\n"
          f"         -> {why.get('verdict')}")
    return ok


print("classifier loaded from linux_control:",
      r.classify_bare_err_reply is not None)
assert r.classify_bare_err_reply is not None, \
    "reviewed classifier must load; otherwise the runner is strict-only"

print("\npositive -- the one row the plan allows")
if check("real 05:14:30.087Z bare-ERR row (12.9 ms desync band)", REAL, True):
    r.tolerated_rows.append({"row": REAL})
check("a SECOND identical row (allowance already spent)", REAL, False)
r.tolerated_rows.clear()
check("104 ms row (desync guard behind a streaming pass, c1f8067c band)",
      {**REAL, "data": {**REAL["data"], "first_byte_wait_ms": 104.0}}, True)
r.tolerated_rows.clear()
check("5 ms row (inline checksum/bad-n reject, also a torn frame)",
      {**REAL, "data": {**REAL["data"], "first_byte_wait_ms": 5.0}}, True)
r.tolerated_rows.clear()

print("\nnegative -- everything else halts")
for label, row in [
    ("a brownout row", {**REAL, "kind": "brownout"}),
    ("bus_timing from the host path, not the MCU", {**REAL, "src": "host"}),
    ("critical level", {**REAL, "level": "critical"}),
    ("a framed n>0 transaction", {**REAL,
                                  "data": {**REAL["data"], "n": 4}}),
    ("a different reason (no_a5)", {**REAL,
                                    "data": {**REAL["data"],
                                             "reason": "no_a5"}}),
    ("wait outside both firmware bands (unattributed)",
     {**REAL, "data": {**REAL["data"], "first_byte_wait_ms": 400.0}}),
    ("an ASCII 'ERR wake' reply, not a bare-ERR frame reject",
     {**REAL, "data": {**REAL["data"], "pre_a5_lines": ["ERR wake"]}}),
    ("no data block at all", {k: v for k, v in REAL.items() if k != "data"}),
]:
    check(label, row, False)

print("\nFAILURES:", fails or "none")
sys.exit(1 if fails else 0)
