"""Synchronized recovery-curriculum cohort for ``train_ppo_mjx``.

``_RecoverPopulation`` lets N trainer processes (one W&B run each) race
the same recover bucket, elect a winner per bucket through W&B run
summaries, download the winning checkpoint and release the cohort to the
next bucket together. The ``_recover_population_*`` functions are the
pure record/election helpers it is built from; they are kept separate so
tests can drive the election logic without W&B.

Moved verbatim out of train_ppo_mjx.py (which re-exports these names).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .train_ppo_sim import POLICY_DIR


def _recover_population_record(summary: dict, kind: str,
                               bucket: int) -> dict | None:
    """Decode one atomic candidate/winner/ack record from W&B summary."""
    raw = summary.get(
        f"recover_population/{kind}_B{int(bucket):02d}")
    if isinstance(raw, dict) and set(raw) == {"last"}:
        raw = raw["last"]
    if not raw:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    return dict(raw) if isinstance(raw, dict) else None


def _recover_population_choose_candidate(
        peer_rows: list[tuple[int, str, str, dict]], bucket: int,
        parent_fingerprint: str, population_id: str) -> dict | None:
    """Elect the earliest valid candidate, with member as the tie-break."""
    candidates = []
    for member, run_id, run_name, summary in peer_rows:
        row = _recover_population_record(summary, "candidate", bucket)
        if row is None:
            continue
        if (str(row.get("population_id", "")) != str(population_id)
                or int(row.get("bucket", -1)) != int(bucket)
                or int(row.get("member", -1)) != int(member)
                or str(row.get("run_id", "")) != str(run_id)
                or str(row.get("run_name", "")) != str(run_name)
                or str(row.get("parent_fingerprint", ""))
                != str(parent_fingerprint)
                or not row.get("policy_sha256")
                or not row.get("curriculum_sha256")
                or not row.get("policy_file")
                or not row.get("curriculum_file")):
            continue
        candidates.append(row)
    if not candidates:
        return None
    return min(candidates, key=lambda row: (
        int(row.get("time_ns", 0)), int(row["member"])))


def _recover_population_all_acked(
        peer_rows: list[tuple[int, str, str, dict]], winner: dict,
        population_id: str, expected_members: int) -> bool:
    """Require an identity-bound ACK from every cohort member."""
    if len(peer_rows) != int(expected_members):
        return False
    bucket = int(winner["bucket"])
    fingerprint = str(winner["policy_sha256"])
    for member, run_id, run_name, summary in peer_rows:
        ack = _recover_population_record(summary, "ack", bucket)
        if (ack is None
                or str(ack.get("population_id", "")) != str(population_id)
                or int(ack.get("bucket", -1)) != bucket
                or int(ack.get("member", -1)) != int(member)
                or str(ack.get("run_id", "")) != str(run_id)
                or str(ack.get("run_name", "")) != str(run_name)
                or str(ack.get("policy_sha256", "")) != fingerprint):
            return False
    return True


def _recover_population_release(
        leader_summary: dict, winner: dict,
        population_id: str) -> dict | None:
    """Return a valid leader release for one fully adopted winner."""
    bucket = int(winner["bucket"])
    row = _recover_population_record(leader_summary, "release", bucket)
    if (row is None
            or str(row.get("population_id", "")) != str(population_id)
            or int(row.get("bucket", -1)) != bucket
            or str(row.get("policy_sha256", ""))
            != str(winner["policy_sha256"])):
        return None
    return row


def _recover_population_all_ready(
        peer_rows: list[tuple[int, str, str, dict]], bucket: int,
        population_id: str, root_fingerprint: str,
        bootstrap_steps: int, expected_members: int) -> bool:
    """Require every seeded member to reach the same root budget."""
    if len(peer_rows) != int(expected_members):
        return False
    for member, run_id, run_name, summary in peer_rows:
        ready = _recover_population_record(summary, "ready", bucket)
        if (ready is None
                or str(ready.get("population_id", ""))
                != str(population_id)
                or int(ready.get("bucket", -1)) != int(bucket)
                or int(ready.get("member", -1)) != int(member)
                or str(ready.get("run_id", "")) != str(run_id)
                or str(ready.get("run_name", "")) != str(run_name)
                or str(ready.get("root_fingerprint", ""))
                != str(root_fingerprint)
                or int(ready.get("bootstrap_steps", -1))
                != int(bootstrap_steps)):
            return False
    return True


def _recover_population_start(
        leader_summary: dict, bucket: int, population_id: str,
        root_fingerprint: str, bootstrap_steps: int) -> dict | None:
    """Return a valid leader release for the initial seeded race."""
    row = _recover_population_record(leader_summary, "start", bucket)
    if (row is None
            or str(row.get("population_id", "")) != str(population_id)
            or int(row.get("bucket", -1)) != int(bucket)
            or str(row.get("root_fingerprint", ""))
            != str(root_fingerprint)
            or int(row.get("bootstrap_steps", -1))
            != int(bootstrap_steps)):
        return None
    return row


class _RecoverPopulation:
    """W&B-backed best-of-N checkpoint election for recovery training."""

    def __init__(self, args, run, initial_bucket: int):
        self.population_id = str(args.recover_population_id)
        self.member = int(args.recover_population_member)
        self.peer_names = tuple(
            name.strip() for name in args.recover_population_runs.split(",")
            if name.strip())
        self.peer_ids = tuple(
            run_id.strip()
            for run_id in args.recover_population_run_ids.split(",")
            if run_id.strip())
        if len(self.peer_ids) != len(self.peer_names):
            raise RuntimeError("recovery population W&B id roster mismatch")
        self.run = run
        self.entity = str(run.entity)
        self.project = str(run.project)
        self.project_path = f"{self.entity}/{self.project}"
        # Public Api run/list objects retain negative lookups inside the
        # active W&B service process. InternalApi.run_resume_status issues a
        # fresh GraphQL read and is specifically designed to see a run that
        # did not exist on an earlier call.
        self._internal_api = None
        self.api = None
        self.poll_seconds = float(args.recover_population_poll_seconds)
        self.barrier_timeout = float(
            args.recover_population_barrier_timeout_seconds)
        self.initial_bucket = int(initial_bucket)
        self.adopted_bucket = int(initial_bucket)
        self.parent_fingerprint = f"root:{self.population_id}"
        self.bootstrap_steps = int(
            args.n_envs * args.n_steps
            * args.recover_population_bootstrap_rollouts)
        self._start_ready = False
        self._race_started = False
        self._next_poll = 0.0
        self._peer_ids = dict(zip(self.peer_names, self.peer_ids))
        expected_run_id = self.peer_ids[self.member]
        if str(run.id) != expected_run_id:
            raise RuntimeError(
                "recovery population local W&B id mismatch: expected "
                f"{expected_run_id}, got {run.id}")
        self._local_summary: dict = {}
        self._sync_count = 0
        self._api_runs: dict[str, object] = {}
        self._pending_candidates: dict[int, dict] = {}
        self._pending_acks: dict[int, tuple[dict, int, int]] = {}

    def _summary_update(self, values: dict) -> None:
        self.run.summary.update(values)
        self._local_summary.update(values)

    def publish_candidate(self, checkpoint: dict) -> None:
        import hashlib
        path = Path(checkpoint["path"])
        metadata_path = Path(checkpoint["metadata_path"])
        bucket = int(checkpoint["bucket"])
        row = {
            "population_id": self.population_id,
            "bucket": bucket,
            "member": self.member,
            "run_id": str(self.run.id),
            "run_name": self.peer_names[self.member],
            "step": int(checkpoint["step"]),
            "time_ns": time.time_ns(),
            "parent_fingerprint": self.parent_fingerprint,
            "policy_file": path.relative_to(POLICY_DIR).as_posix(),
            "curriculum_file": metadata_path.relative_to(
                POLICY_DIR).as_posix(),
            "policy_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "curriculum_sha256": hashlib.sha256(
                metadata_path.read_bytes()).hexdigest(),
        }
        self._pending_candidates[bucket] = row
        self._flush_candidates()

    def _flush_candidates(self) -> None:
        """Upload files before making an atomic candidate record visible."""
        import wandb
        for bucket, row in list(self._pending_candidates.items()):
            try:
                for key in ("policy_file", "curriculum_file"):
                    rel = self._checked_relative_path(row[key])
                    path = POLICY_DIR / rel
                    if not path.is_file():
                        raise FileNotFoundError(path)
                    self.run.save(
                        str(path), base_path=str(POLICY_DIR), policy="now")
                self._summary_update({
                    f"recover_population/candidate_B{bucket:02d}":
                        json.dumps(row, sort_keys=True),
                    "recover_population/latest_candidate_bucket": bucket,
                    "recover_latest_promotion_checkpoint":
                        str(row["policy_file"]),
                })
            except Exception as exc:
                print("[recover-pop] candidate upload deferred for "
                      f"B{bucket}: {exc}")
                continue
            del self._pending_candidates[bucket]
            try:
                wandb.log({
                    "global_step": int(row["step"]),
                    "RECOVER_POPULATION/candidate_bucket": float(bucket),
                    "RECOVER_POPULATION/candidate_member": float(self.member),
                })
            except Exception as exc:
                print(f"[recover-pop] candidate metric deferred: {exc}")
            print("[recover-pop] published retained candidate "
                  f"B{bucket} from member {self.member}")

    def _peer_rows(self) -> list[tuple[int, str, str, dict]]:
        if self._internal_api is None:
            from wandb.sdk.internal.internal_api import Api as InternalApi
            self._internal_api = InternalApi()
        rows = []
        for member, name in enumerate(self.peer_names):
            run_id = self._peer_ids.get(name)
            if run_id is None:
                continue
            payload = self._internal_api.run_resume_status(
                self.entity, self.project, run_id)
            if payload is None:
                continue
            if str(payload.get("name", "")) != run_id:
                raise RuntimeError(
                    f"recovery population peer id mismatch for {run_id}")
            display_name = str(payload.get("displayName", ""))
            if display_name != name:
                raise RuntimeError(
                    "recovery population peer name mismatch for "
                    f"{run_id}: expected {name}, got {display_name}")
            raw_summary = payload.get("summaryMetrics") or {}
            if isinstance(raw_summary, str):
                raw_summary = json.loads(raw_summary)
            if not isinstance(raw_summary, dict):
                raise RuntimeError(
                    f"invalid W&B summary for recovery peer {run_id}")
            summary = dict(raw_summary)
            if run_id == str(self.run.id):
                summary.update(self._local_summary)
            rows.append((member, run_id, name, summary))
        return rows

    def _winner(self, leader_summary: dict, bucket: int) -> dict | None:
        row = _recover_population_record(leader_summary, "winner", bucket)
        if (row is None
                or row.get("population_id") != self.population_id
                or int(row.get("bucket", -1)) != int(bucket)):
            return None
        return row

    def _all_acked(self, peer_rows, winner: dict) -> bool:
        return _recover_population_all_acked(
            peer_rows, winner, self.population_id, len(self.peer_names))

    def _release(self, leader_summary: dict,
                 winner: dict) -> dict | None:
        return _recover_population_release(
            leader_summary, winner, self.population_id)

    def _start(self, leader_summary: dict) -> dict | None:
        return _recover_population_start(
            leader_summary, self.initial_bucket, self.population_id,
            self.parent_fingerprint, self.bootstrap_steps)

    def _elect(self, peer_rows, leader_summary: dict) -> dict:
        if self.member != 0 or len(peer_rows) != len(self.peer_names):
            return leader_summary
        last_bucket = self.initial_bucket
        last_winner = None
        while True:
            row = self._winner(leader_summary, last_bucket + 1)
            if row is None:
                break
            last_bucket += 1
            last_winner = row
        if last_winner is None and self._start(leader_summary) is None:
            return leader_summary
        # ACKs alone are not enough: every member blocks after ACK until the
        # leader publishes this release. That gives each bucket three fresh
        # branches from the exact same parent instead of letting one member
        # build a multi-bucket head start while slower peers are restoring.
        if last_winner is not None and self._release(
                leader_summary, last_winner) is None:
            return leader_summary
        parent = (f"root:{self.population_id}" if last_winner is None
                  else str(last_winner["policy_sha256"]))
        candidate = _recover_population_choose_candidate(
            peer_rows, last_bucket + 1, parent, self.population_id)
        if candidate is None:
            return leader_summary
        winner = dict(candidate)
        winner["elected_time_ns"] = time.time_ns()
        key = f"recover_population/winner_B{last_bucket + 1:02d}"
        values = {
            key: json.dumps(winner, sort_keys=True),
            "recover_population/latest_winner_bucket": last_bucket + 1,
        }
        self._summary_update(values)
        leader_summary.update(values)
        import wandb
        wandb.log({
            "global_step": int(self.run.summary.get("global_step", 0)),
            "RECOVER_POPULATION/winner_bucket": float(last_bucket + 1),
            "RECOVER_POPULATION/winner_member": float(winner["member"]),
        })
        print("[recover-pop] elected member "
              f"{winner['member']} candidate for B{last_bucket + 1}")
        return leader_summary

    @staticmethod
    def _checked_relative_path(raw: str) -> Path:
        path = Path(str(raw))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe recovery population file {raw!r}")
        return path

    def _download(self, winner: dict) -> dict:
        import hashlib
        run_id = str(winner["run_id"])
        policy_rel = self._checked_relative_path(winner["policy_file"])
        curriculum_rel = self._checked_relative_path(
            winner["curriculum_file"])
        if run_id == str(self.run.id):
            policy_path = POLICY_DIR / policy_rel
            curriculum_path = POLICY_DIR / curriculum_rel
        else:
            import wandb
            if self.api is None:
                self.api = wandb.Api(timeout=15)
            api_run = self._api_runs.get(run_id)
            if api_run is None:
                api_run = self.api.run(
                    f"{self.project_path}/{run_id}")
                self._api_runs[run_id] = api_run
            root = (POLICY_DIR / "recover_population" /
                    self.population_id /
                    f"B{int(winner['bucket']):02d}_m{int(winner['member'])}")
            root.mkdir(parents=True, exist_ok=True)
            for rel in (policy_rel, curriculum_rel):
                remote = api_run.file(rel.as_posix())
                if remote is None:
                    raise FileNotFoundError(
                        f"W&B run {run_id} has no file {rel.as_posix()}")
                remote.download(root=str(root), replace=True)
            policy_path = root / policy_rel
            curriculum_path = root / curriculum_rel
        for path, key in ((policy_path, "policy_sha256"),
                          (curriculum_path, "curriculum_sha256")):
            if not path.is_file():
                raise FileNotFoundError(path)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != str(winner[key]):
                raise RuntimeError(
                    f"recovery population checksum mismatch for {path}")
        metadata = json.loads(curriculum_path.read_text())
        if int(metadata["promotion_bucket"]) != int(winner["bucket"]):
            raise RuntimeError("recovery population curriculum bucket "
                               "does not match the elected winner")
        return {
            "path": policy_path,
            "metadata_path": curriculum_path,
            "bucket": int(winner["bucket"]),
            "step": int(winner["step"]),
            "curriculum": metadata["curriculum"],
            "cert_round": int(metadata.get("cert_round", 0)),
            "population_record": winner,
        }

    def poll(self) -> dict | None:
        now = time.monotonic()
        if now < self._next_poll:
            return None
        self._next_poll = now + self.poll_seconds
        self._flush_candidates()
        self._flush_acks()
        try:
            peer_rows = self._peer_rows()
            if len(peer_rows) != len(self.peer_names):
                print("[recover-pop] waiting for all peer W&B runs: "
                      f"{len(peer_rows)}/{len(self.peer_names)} visible")
                return None
            leader_summary = peer_rows[0][3]
            leader_summary = self._elect(peer_rows, leader_summary)
            winner = self._winner(leader_summary, self.adopted_bucket + 1)
            if winner is None:
                return None
            if str(winner.get("parent_fingerprint", "")) != (
                    self.parent_fingerprint):
                raise RuntimeError(
                    "recovery population winner has the wrong parent "
                    f"fingerprint for B{self.adopted_bucket + 1}")
            return self._download(winner)
        except Exception as exc:
            print(f"[recover-pop] poll deferred: {exc}")
            return None

    def acknowledge(self, checkpoint: dict, global_step: int) -> None:
        winner = checkpoint["population_record"]
        bucket = int(checkpoint["bucket"])
        self.adopted_bucket = bucket
        self.parent_fingerprint = str(winner["policy_sha256"])
        self._sync_count += 1
        ack = {
            "population_id": self.population_id,
            "bucket": bucket,
            "member": self.member,
            "run_id": str(self.run.id),
            "run_name": self.peer_names[self.member],
            "policy_sha256": self.parent_fingerprint,
            "winner_run_id": str(winner["run_id"]),
            "ack_time_ns": time.time_ns(),
        }
        self._pending_acks[bucket] = (
            ack, int(global_step), int(winner["member"]))
        self._flush_acks()

    def wait_for_start(self, global_step: int) -> None:
        """Equalize seeded B0 budgets before the first candidate can win."""
        if self._race_started or int(global_step) < self.bootstrap_steps:
            return
        import wandb
        started = time.monotonic()
        deadline = started + self.barrier_timeout
        next_status = started
        sleep_seconds = min(max(self.poll_seconds, 1.0), 5.0)
        while True:
            if not self._start_ready:
                ready = {
                    "population_id": self.population_id,
                    "bucket": self.initial_bucket,
                    "member": self.member,
                    "run_id": str(self.run.id),
                    "run_name": self.peer_names[self.member],
                    "root_fingerprint": self.parent_fingerprint,
                    "bootstrap_steps": self.bootstrap_steps,
                    "ready_time_ns": time.time_ns(),
                }
                try:
                    self._summary_update({
                        f"recover_population/ready_B{self.initial_bucket:02d}":
                            json.dumps(ready, sort_keys=True),
                        "recover_population/bootstrap_ready_bucket":
                            self.initial_bucket,
                    })
                    self._start_ready = True
                    try:
                        wandb.log({
                            "global_step": int(global_step),
                            "RECOVER_POPULATION/bootstrap_ready": 1.0,
                        })
                    except Exception as exc:
                        print("[recover-pop] bootstrap-ready metric deferred: "
                              f"{exc}")
                except Exception as exc:
                    print("[recover-pop] bootstrap readiness deferred: "
                          f"{exc}")
            try:
                peer_rows = self._peer_rows()
                if len(peer_rows) == len(self.peer_names):
                    leader_summary = peer_rows[0][3]
                    release = self._start(leader_summary)
                    if (release is None and self.member == 0
                            and _recover_population_all_ready(
                                peer_rows, self.initial_bucket,
                                self.population_id,
                                self.parent_fingerprint,
                                self.bootstrap_steps,
                                len(self.peer_names))):
                        release = {
                            "population_id": self.population_id,
                            "bucket": self.initial_bucket,
                            "root_fingerprint": self.parent_fingerprint,
                            "bootstrap_steps": self.bootstrap_steps,
                            "member_count": len(self.peer_names),
                            "start_time_ns": time.time_ns(),
                        }
                        values = {
                            f"recover_population/start_B{self.initial_bucket:02d}":
                                json.dumps(release, sort_keys=True),
                            "recover_population/start_bucket":
                                self.initial_bucket,
                        }
                        self._summary_update(values)
                        leader_summary.update(values)
                        try:
                            wandb.log({
                                "global_step": int(global_step),
                                "RECOVER_POPULATION/start_release": 1.0,
                            })
                        except Exception as exc:
                            print("[recover-pop] start metric deferred: "
                                  f"{exc}")
                        print("[recover-pop] leader RELEASED initial B"
                              f"{self.initial_bucket} race after all "
                              f"{len(self.peer_names)} members reached "
                              f"{self.bootstrap_steps:,} steps")
                    if release is not None:
                        waited = time.monotonic() - started
                        self._race_started = True
                        try:
                            wandb.log({
                                "global_step": int(global_step),
                                "RECOVER_POPULATION/start_observed": 1.0,
                                "RECOVER_POPULATION/start_wait_seconds":
                                    float(waited),
                            })
                        except Exception as exc:
                            print("[recover-pop] start-observed metric "
                                  f"deferred: {exc}")
                        print("[recover-pop] member "
                              f"{self.member} STARTED initial B"
                              f"{self.initial_bucket} race after "
                              f"{waited:.1f}s")
                        return
            except Exception as exc:
                print(f"[recover-pop] start poll deferred: {exc}")
            now = time.monotonic()
            if now >= deadline:
                raise RuntimeError(
                    "recovery population timed out waiting for all members "
                    f"to reach the {self.bootstrap_steps:,}-step initial "
                    f"race barrier after {self.barrier_timeout:.0f}s")
            if now >= next_status:
                print("[recover-pop] member "
                      f"{self.member} WAITING at initial B"
                      f"{self.initial_bucket} bootstrap barrier")
                next_status = now + 60.0
            time.sleep(min(sleep_seconds, deadline - now))

    def wait_for_release(self, checkpoint: dict, global_step: int) -> None:
        """Block rollout collection until every member ACKs this winner."""
        import wandb
        winner = checkpoint["population_record"]
        bucket = int(checkpoint["bucket"])
        started = time.monotonic()
        deadline = started + self.barrier_timeout
        next_status = started
        sleep_seconds = min(max(self.poll_seconds, 1.0), 5.0)
        while True:
            self._flush_acks()
            try:
                peer_rows = self._peer_rows()
                if len(peer_rows) == len(self.peer_names):
                    leader_summary = peer_rows[0][3]
                    release = self._release(leader_summary, winner)
                    if (release is None and self.member == 0
                            and self._all_acked(peer_rows, winner)):
                        release = {
                            "population_id": self.population_id,
                            "bucket": bucket,
                            "policy_sha256": str(winner["policy_sha256"]),
                            "winner_run_id": str(winner["run_id"]),
                            "member_count": len(self.peer_names),
                            "release_time_ns": time.time_ns(),
                        }
                        values = {
                            f"recover_population/release_B{bucket:02d}":
                                json.dumps(release, sort_keys=True),
                            "recover_population/latest_release_bucket":
                                bucket,
                        }
                        self._summary_update(values)
                        leader_summary.update(values)
                        try:
                            wandb.log({
                                "global_step": int(global_step),
                                "RECOVER_POPULATION/release_bucket":
                                    float(bucket),
                            })
                        except Exception as exc:
                            print("[recover-pop] release metric deferred: "
                                  f"{exc}")
                        print("[recover-pop] leader RELEASED B"
                              f"{bucket} after all {len(self.peer_names)} "
                              "members ACKed")
                    if release is not None:
                        waited = time.monotonic() - started
                        try:
                            wandb.log({
                                "global_step": int(global_step),
                                "RECOVER_POPULATION/released_bucket":
                                    float(bucket),
                                "RECOVER_POPULATION/release_wait_seconds":
                                    float(waited),
                            })
                        except Exception as exc:
                            print("[recover-pop] release-observed metric "
                                  f"deferred: {exc}")
                        print("[recover-pop] member "
                              f"{self.member} observed RELEASE B{bucket} "
                              f"after {waited:.1f}s; next race may start")
                        return
            except Exception as exc:
                print(f"[recover-pop] release poll deferred: {exc}")
            now = time.monotonic()
            if now >= deadline:
                raise RuntimeError(
                    "recovery population timed out waiting for all members "
                    f"to ACK/release B{bucket} after "
                    f"{self.barrier_timeout:.0f}s")
            if now >= next_status:
                print("[recover-pop] member "
                      f"{self.member} WAITING at B{bucket} ACK barrier")
                next_status = now + 60.0
            time.sleep(min(sleep_seconds, deadline - now))

    def _flush_acks(self) -> None:
        import wandb
        for bucket, (ack, global_step, winner_member) in list(
                self._pending_acks.items()):
            try:
                self._summary_update({
                    f"recover_population/ack_B{bucket:02d}":
                        json.dumps(ack, sort_keys=True),
                    "recover_population/latest_ack_bucket": bucket,
                })
            except Exception as exc:
                print(f"[recover-pop] ACK deferred for B{bucket}: {exc}")
                continue
            del self._pending_acks[bucket]
            try:
                wandb.log({
                    "global_step": global_step,
                    "RECOVER_POPULATION/adopted_bucket": float(bucket),
                    "RECOVER_POPULATION/ack_bucket": float(bucket),
                    "RECOVER_POPULATION/winner_member": float(winner_member),
                    "RECOVER_POPULATION/sync_count": float(self._sync_count),
                })
            except Exception as exc:
                print(f"[recover-pop] ACK metric deferred: {exc}")
