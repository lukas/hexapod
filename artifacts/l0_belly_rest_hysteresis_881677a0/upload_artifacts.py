#!/usr/bin/env python3
"""PUT every staged artifact to the Lab, before sealing.

The Authorization header is read from the MCP config and written to a curl
config file that is created 0600 and deleted afterwards, so the credential
never appears in argv, in the process table, or in this script's output.
"""
import json, os, pathlib, subprocess, sys, tempfile

EXP = "881677a009404afda40c6c0d84e8b7d6"
BASE = "https://robot-lab.cwd1f0-new-cluster.coreweave.app"
D = pathlib.Path(__file__).resolve().parent
STAGE = D / "_staged"

cfg = json.load(open(os.path.expanduser("~/.claude/hexapod/mcp.json")))
auth = (cfg.get("mcpServers") or cfg)["robot_lab"]["headers"]["Authorization"]

names = sorted(p.name for p in STAGE.iterdir() if p.is_file())
only = sys.argv[1:] or names
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
