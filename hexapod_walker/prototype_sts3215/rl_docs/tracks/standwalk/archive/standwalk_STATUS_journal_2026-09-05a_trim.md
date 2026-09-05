Update, 2026-09-05 ~02:4x: **Infra recovery — DONE-gate eval RELAUNCHED
on train-9.** train-6 (running the 09-04 ~18:1x DONE-gate flat-only
read) was found OOMKilled (host-level, exit 137, container 96Gi limit
hit ~22:48Z 09-04 — the eval's own `--shards 8`, 8 concurrent
`eval_checkpoint` subprocesses each with `--video` against the mesh/
100Hz model, plus this pod's usual accumulated stale-process load, is
the likely cause; matches the recurring "idle pod accumulates memory"
pattern from train-0/4/10 incidents). `pending_evals.json`'s entry had
already silently expired (8h TTL) with no verdict ever landing — the
read was fully lost, not just delayed. Recovery: deleted+recreated
train-6 from the manifest (now Pending on host CPU, normal, will
schedule when capacity frees — do NOT force it); pushed the
`mlcontprice8` checkpoint + synced code to train-9 (clean pod, no
stale processes, confirmed via `ps`) and relaunched the identical
`donegatecmd` flat=1 command with **`--jobs 4`** added (caps concurrent
shard subprocesses at 4 instead of 8, same `--shards 8` statistical
layout/seed streams) to keep memory headroom — confirmed at ~40GB/96GB
cgroup usage with 4 shard workers running, well clear of the limit.
Re-registered via `evalpending` (train-9). Still the track's first read
of this lineage against the real gate, not the stress diet.

Prior updates (09-04 ~13:2x..~18:1x) archived verbatim in `archive/
standwalk_STATUS_journal_2026-09-04{hh,jj,kk,ll}_trim.md`.
