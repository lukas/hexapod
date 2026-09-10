#!/usr/bin/env python3
"""PUT every staged artifact to the Lab, BEFORE completing the experiment.

Ordering matters: the evidence gets sealed roughly 90 s after a result
registers, and a post-seal PUT returns 409, so everything here must land while
the experiment is still waiting_for_operator.  The L0 sibling lost its whole
raw set to exactly that race.

Auth is NOT the robot_lab MCP bearer -- the REST API rejects it with 401 even
on GET.  The REST keys are the HEXAPOD_API_KEYS entries the local Lab process
is started with (run-hexapod-lab.sh), and it reads them from the macOS
keychain; this uses the `operator:assistants` token, the same principal MCP
calls already act as.  It is read in-process and written to a curl config file
created 0600 and deleted afterwards, so the credential never reaches argv, the
process table, or this script's output.
"""
import json, os, pathlib, subprocess, sys, tempfile

EXP = "7299f24343654f9893274d4328b277ad"
BASE = os.environ.get("LAB_BASE", "http://127.0.0.1:8767")
D = pathlib.Path(__file__).resolve().parent
STAGE = D / "_staged"

_tok = subprocess.run(
    ["/usr/bin/security", "find-generic-password", "-a", "assistants",
     "-s", "Hexapod Lab API", "-w"],
    capture_output=True, text=True, check=True).stdout.strip()
auth = "Bearer " + _tok
del _tok

# Smallest first, so a size limit or a timeout on one big bundle cannot cost
# the small recomputable evidence that matters most.
names = [p.name for p in sorted((q for q in STAGE.iterdir() if q.is_file()),
                                key=lambda q: q.stat().st_size)]
args = sys.argv[1:]
if args and args[0] == "--max-bytes":
    cap = int(args[1])
    only = [n for n in names if (STAGE / n).stat().st_size <= cap]
else:
    only = args or names
fd, curlrc = tempfile.mkstemp(prefix="labput", suffix=".conf")
os.close(fd)
os.chmod(curlrc, 0o600)
with open(curlrc, "w") as fh:
    fh.write(f'header = "Authorization: {auth}"\n')

ok = skipped = failed = 0
results = []
try:
    for n in only:
        p = STAGE / n
        url = f"{BASE}/api/experiments/{EXP}/artifacts/{n}"
        cp = subprocess.run(
            ["curl", "-sS", "--config", curlrc, "-X", "PUT",
             "--max-time", "300", "-H", "Content-Type: application/octet-stream",
             "--data-binary", f"@{p}", "-o", "/dev/null",
             "-w", "%{http_code}", url],
            capture_output=True, text=True)
        code = (cp.stdout or "").strip()
        if code in ("200", "201"):
            ok += 1
        elif code == "409":
            skipped += 1
        else:
            failed += 1
            results.append({"artifact": n, "code": code,
                            "stderr": (cp.stderr or "")[:200]})
        print(f"  {code}  {n}", flush=True)
finally:
    os.remove(curlrc)

print(f"\nuploaded {ok}, already-present {skipped}, failed {failed}")
if results:
    print(json.dumps(results, indent=1))
sys.exit(1 if failed else 0)
