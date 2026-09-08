from pathlib import Path
import json
from statistics import median
root = Path(__file__).resolve().parent
base = json.loads((root / "parent_gate_report.json").read_text())
new = json.loads((root / "corrected_probe_report.json").read_text())
expected = {"walk/det", "walk/sto", "walk_startjitter/det", "walk_startjitter/sto"}
assert set(base["episodes"]) == set(new["episodes"]) == expected
improving = 0
for group in base["episodes"]:
    a, b = base["episodes"][group], new["episodes"][group]
    assert len(a) == len(b) == 6
    assert all(x["randomization"] == y["randomization"] for x,y in zip(a,b))
    x,y = median(e["slip_per_m"] for e in a), median(e["slip_per_m"] for e in b)
    improving += y <= 0.9*x
    print(f"{group}: {x:.4f} -> {y:.4f} ({100*(y/x-1):+.2f}%), gait={sum(e['gait_valid'] for e in b)}/6, terms={sum(e['terminated'] for e in b)}")
print(f"Groups improving >=10%: {improving}/4; required >=3. Proceed: {improving >= 3}")
assert improving == 0
