"""Fetch and replay the curated Hexapod 2 Robot Lab validation matrix.

The manifest stores provenance and SHA-256 digests, never credentials or raw
telemetry.  This command obtains the CSVs through the existing authenticated
Robot Lab client, verifies every byte, and replays recorded post-safety servo
commands through one explicit digital-twin configuration.  Four traces are a
fit set; the remaining policy families, directions, repeats, and older runs
stay held out so a PS200-only parameter tweak cannot masquerade as a useful
twin.  Hardware replay defaults to the loaded-actuator fit; select ``air``
explicitly only when comparing against the unloaded bench calibration.

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.replay_hexapod2_matrix --split fit
    uv run python -m rl_move.sim.replay_hexapod2_matrix --split all \
        --joint-series-flex-json candidate.json --out report.json
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import tempfile
from urllib import request
from urllib.parse import urljoin, urlsplit

import numpy as np

from .leg_mount_flex import from_cfg as leg_mount_flex_from_cfg
from .joint_series_flex import from_cfg as joint_series_flex_from_cfg
from .replay_trace import _ReplaySim, analyze, load_trace
from .servo_model import LOADED_MODEL_PATH, SimServoParams


HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "hexapod2_replay_matrix.json"
DEFAULT_DATA_DIR = Path("/tmp/hexapod2-replay-matrix")

REPORT_METRICS = (
    "trace_duration_s", "trace_median_hz",
    "q_rmse_moving_deg", "roll_div_tick",
    "hw_peak_roll_rel_deg", "sim_peak_roll_rel_deg",
    "sim_true_peak_roll_rel_deg",
    "roll_waveform_rmse_deg", "pitch_waveform_rmse_deg",
    "hw_peak_current_a", "sim_peak_current_proxy_a",
    "sim_displacement_mm", "sim_speed_mm_s",
    "sim_max_mount_flex_deg",
    "sim_max_series_flex_deg",
)

_RUN_ID_RE = re.compile(r"[A-Za-z0-9_-]+")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text())
    if not isinstance(manifest, dict):
        raise ValueError(f"replay manifest must be a JSON object: {path}")
    if manifest.get("schema_version") != 1:
        raise ValueError(f"unsupported replay manifest schema: {path}")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"replay manifest has no entries: {path}")
    artifact_hashes: dict[str, str] = {}
    hash_artifacts: dict[str, str] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"manifest entry {index} is not an object")
        for key in (
                "run_id", "filename", "family", "split", "artifact",
                "sha256"):
            if not isinstance(entry.get(key), str) or not entry[key]:
                raise ValueError(f"manifest entry missing {key}: {entry}")
        if _RUN_ID_RE.fullmatch(entry["run_id"]) is None:
            raise ValueError(f"unsafe manifest run_id: {entry['run_id']!r}")
        filename = Path(entry["filename"])
        if filename.name != entry["filename"] or filename.suffix != ".csv":
            raise ValueError(
                f"manifest filename must be one CSV basename: "
                f"{entry['filename']!r}")
        if entry["split"] not in {"fit", "holdout"}:
            raise ValueError(f"unsupported manifest split: {entry['split']!r}")
        rel = Path(entry["artifact"])
        if (rel.is_absolute() or ".." in rel.parts
                or rel.suffix != ".csv"):
            raise ValueError(f"unsafe manifest artifact path: {rel}")
        if _SHA256_RE.fullmatch(entry["sha256"]) is None:
            raise ValueError(
                f"invalid manifest SHA-256 for {entry['run_id']}: "
                f"{entry['sha256']!r}")

        artifact = entry["artifact"]
        digest = entry["sha256"]
        if artifact in artifact_hashes and artifact_hashes[artifact] != digest:
            raise ValueError(
                f"manifest artifact {artifact!r} has conflicting SHA-256")
        if digest in hash_artifacts and hash_artifacts[digest] != artifact:
            raise ValueError(
                f"manifest SHA-256 {digest} maps to multiple artifacts")
        artifact_hashes[artifact] = digest
        hash_artifacts[digest] = artifact
    return manifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _entry_path(data_dir: Path, entry: dict) -> Path:
    return data_dir / entry["artifact"]


def _url_origin(url: str) -> tuple[str, str, int]:
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError(f"unsupported Robot Lab artifact URL: {url!r}")
    try:
        port = parsed.port
    except ValueError as caught:
        raise RuntimeError(f"invalid Robot Lab artifact URL: {url!r}") from caught
    if port is None:
        port = 443 if parsed.scheme.lower() == "https" else 80
    return parsed.scheme.lower(), parsed.hostname.lower(), port


def _same_origin(first: str, second: str) -> bool:
    return _url_origin(first) == _url_origin(second)


def _reject_https_downgrade(first: str, second: str) -> None:
    if _url_origin(first)[0] == "https" and _url_origin(second)[0] != "https":
        raise RuntimeError(
            f"refusing HTTPS-to-HTTP Robot Lab redirect: {second!r}")


class _SafeAuthRedirectHandler(request.HTTPRedirectHandler):
    """Never forward a Robot Lab bearer token across URL origins."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(
            req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        _reject_https_downgrade(req.full_url, redirected.full_url)
        if not _same_origin(req.full_url, redirected.full_url):
            redirected.remove_header("Authorization")
        return redirected


def _artifact_request(publisher, remote: str) -> request.Request:
    """Build an artifact request without disclosing auth cross-origin."""
    url = urljoin(publisher.base_url.rstrip("/") + "/", remote)
    _url_origin(url)
    _reject_https_downgrade(publisher.base_url, url)
    headers = {}
    if _same_origin(publisher.base_url, url):
        headers["Authorization"] = f"Bearer {publisher.token}"
    return request.Request(url, headers=headers)


def _run_detail(publisher, run_id: str) -> dict:
    """Read fixed-origin run metadata with redirect-safe authentication."""
    incoming = _artifact_request(publisher, f"/api/runs/{run_id}")
    opener = request.build_opener(_SafeAuthRedirectHandler())
    with opener.open(
            incoming, timeout=float(getattr(publisher, "timeout_s", 20.0))
    ) as response:
        detail = json.loads(response.read().decode("utf-8"))
    if not isinstance(detail, dict):
        raise RuntimeError("Robot Lab returned unexpected run metadata")
    return detail


def _fetch_one(publisher, data_dir: Path, entry: dict) -> Path:
    target = _entry_path(data_dir, entry)
    expected = entry["sha256"]
    if target.is_file() and _sha256(target) == expected:
        return target

    detail = _run_detail(publisher, entry["run_id"])
    run = detail.get("run", detail)
    files = run.get("files") or detail.get("files") or []
    paths = [item.get("path") if isinstance(item, dict) else str(item)
             for item in files]
    matches = [path for path in paths
               if path and Path(path).name == entry["filename"]]
    if len(matches) != 1:
        raise RuntimeError(
            f"Robot Lab run {entry['run_id']} has {len(matches)} files named "
            f"{entry['filename']!r}")
    remote = matches[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    incoming = _artifact_request(publisher, remote)
    part: Path | None = None
    digest = hashlib.sha256()
    try:
        with tempfile.NamedTemporaryFile(
                mode="wb", dir=target.parent,
                prefix=f".{target.name}.", suffix=".part",
                delete=False) as stream:
            part = Path(stream.name)
            opener = request.build_opener(_SafeAuthRedirectHandler())
            with opener.open(incoming, timeout=60) as response:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    digest.update(block)
                    stream.write(block)
        actual = digest.hexdigest()
        if actual != expected:
            raise RuntimeError(
                f"Robot Lab SHA mismatch for {entry['run_id']}/"
                f"{entry['filename']}: expected {expected}, got {actual}")
        part.replace(target)
    finally:
        if part is not None:
            part.unlink(missing_ok=True)
    return target


def fetch_entries(entries: list[dict], data_dir: Path, *, jobs: int = 6) -> None:
    """Authenticated, checksum-verified fetch. Credentials are never logged."""
    from hexapod_tracker.robot_lab import RobotLabPublisher

    publisher = RobotLabPublisher.from_env()
    if not publisher.configured:
        raise RuntimeError(
            "Robot Lab credential unavailable; configure the existing "
            "Hexapod Lab credential source")
    unique_entries: dict[str, dict] = {}
    for entry in entries:
        artifact = entry["artifact"]
        previous = unique_entries.get(artifact)
        if previous is not None and previous["sha256"] != entry["sha256"]:
            raise ValueError(
                f"artifact {artifact!r} requested with conflicting SHA-256")
        unique_entries.setdefault(artifact, entry)
    with ThreadPoolExecutor(max_workers=max(1, int(jobs))) as pool:
        futures = {
            pool.submit(_fetch_one, publisher, data_dir, entry): entry
            for entry in unique_entries.values()
        }
        for future in as_completed(futures):
            entry = futures[future]
            path = future.result()
            print(f"  fetched/verified {entry['run_id']}  {path.name}")


def verify_entries(entries: list[dict], data_dir: Path) -> None:
    """Require every selected artifact to exist and match its manifest."""
    for entry in entries:
        path = _entry_path(data_dir, entry)
        if not path.is_file():
            raise RuntimeError(f"missing replay artifact: {path}")
        actual = _sha256(path)
        if actual != entry["sha256"]:
            raise RuntimeError(
                f"replay artifact SHA mismatch for {path}: expected "
                f"{entry['sha256']}, got {actual}")


def _load_flex(path: Path | None):
    if path is None:
        return None
    blob = json.loads(path.read_text())
    section = blob.get("leg_mount_flex", blob)
    return leg_mount_flex_from_cfg({
        "leg_mount_flex": {**section, "enabled": 1}})


def _load_series_flex(path: Path | None):
    if path is None:
        return None
    blob = json.loads(path.read_text())
    section = blob.get("joint_series_flex", blob)
    return joint_series_flex_from_cfg({
        "joint_series_flex": {**section, "enabled": 1}})


def _passes_attitude_gate(metrics: dict) -> bool:
    values = np.asarray([
        metrics["hw_peak_roll_rel_deg"],
        metrics["sim_peak_roll_rel_deg"],
        metrics["roll_waveform_rmse_deg"],
    ], dtype=float)
    if not np.all(np.isfinite(values)) or values[0] < 0.0:
        return False
    hw_peak, sim_peak, waveform_rmse = values
    peak_tolerance = max(2.0, 0.30 * hw_peak)
    return bool(abs(sim_peak - hw_peak) <= peak_tolerance
                and waveform_rmse <= 3.0)


def _summaries(records: list[dict]) -> dict:
    out: dict[str, dict] = {}
    keys = sorted({record["split"] for record in records})
    for split in keys:
        rows = [record for record in records if record["split"] == split]
        out[split] = {
            "n": len(rows),
            "attitude_gate_passed": sum(row["attitude_gate_pass"] for row in rows),
            "median_roll_peak_abs_error_deg": round(float(np.median([
                abs(row["sim_peak_roll_rel_deg"]
                    - row["hw_peak_roll_rel_deg"]) for row in rows])), 2),
            "median_roll_waveform_rmse_deg": round(float(np.median([
                row["roll_waveform_rmse_deg"] for row in rows])), 2),
            "median_q_rmse_deg": round(float(np.median([
                row["q_rmse_moving_deg"] for row in rows])), 2),
        }
    return out


def run_matrix(entries: list[dict], data_dir: Path, *, params,
               model_source: str, mount_flex=None, series_flex=None,
               imu_pos_mm: tuple[float, float, float] = (0., 0., 0.)) \
        -> list[dict]:
    records = []
    for index, entry in enumerate(entries, 1):
        path = _entry_path(data_dir, entry)
        if not path.is_file() or _sha256(path) != entry["sha256"]:
            raise RuntimeError(f"missing or unverified replay artifact: {path}")
        trace = load_trace(path)
        sim = _ReplaySim(
            params, leg_mount_flex=mount_flex,
            joint_series_flex=series_flex,
            model_source=model_source, imu_pos_mm=imu_pos_mm).replay(trace)
        analysis = analyze(trace, sim)
        record = {
            "run_id": entry["run_id"],
            "filename": entry["filename"],
            "family": entry.get("family"),
            "split": entry["split"],
            "command": entry.get("command"),
            "quality_flags": entry.get("quality_flags", []),
            **{key: analysis[key] for key in REPORT_METRICS},
        }
        record["attitude_gate_pass"] = _passes_attitude_gate(record)
        records.append(record)
        print(
            f"[{index:02d}/{len(entries):02d}] {record['split']:<7} "
            f"{record['family']:<24} q={record['q_rmse_moving_deg']:>4.1f}deg "
            f"roll={record['sim_peak_roll_rel_deg']:>4.1f}/"
            f"{record['hw_peak_roll_rel_deg']:>4.1f}deg "
            f"wave={record['roll_waveform_rmse_deg']:>4.1f}deg "
            f"speed={record['sim_speed_mm_s']:>5.1f}mm/s "
            f"{'PASS' if record['attitude_gate_pass'] else 'FAIL'}")
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--split", choices=("fit", "holdout", "all"),
                        default="all")
    parser.add_argument("--model-source",
                        choices=("mesh", "mesh_mjx", "primitive"),
                        default="mesh")
    parser.add_argument("--servo-params", choices=("air", "loaded"),
                        default="loaded")
    parser.add_argument("--leg-mount-flex-json", type=Path, default=None)
    parser.add_argument("--joint-series-flex-json", type=Path, default=None)
    parser.add_argument(
        "--imu-pos-mm", default="0,0,0",
        help="chassis-frame IMU x,y,z in mm (default chassis origin)")
    parser.add_argument("--fetch-only", action="store_true")
    parser.add_argument("--no-fetch", action="store_true",
                        help="fail if a verified local CSV is absent")
    parser.add_argument("--fetch-jobs", type=int, default=6)
    parser.add_argument("--limit", type=int, default=0,
                        help="smoke-test only the first N selected entries")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest)
    entries = [entry for entry in manifest["entries"]
               if args.split == "all" or entry["split"] == args.split]
    if args.limit > 0:
        entries = entries[:args.limit]
    if not entries:
        raise SystemExit(f"manifest has no entries for split {args.split!r}")
    if not args.no_fetch:
        fetch_entries(entries, args.data_dir, jobs=args.fetch_jobs)
    if args.fetch_only:
        verify_entries(entries, args.data_dir)
        return 0

    params = (SimServoParams.load() if args.servo_params == "air" else
              SimServoParams.load(LOADED_MODEL_PATH))
    mount_flex = _load_flex(args.leg_mount_flex_json)
    series_flex = _load_series_flex(args.joint_series_flex_json)
    if mount_flex is not None and series_flex is not None:
        parser.error("--leg-mount-flex-json and --joint-series-flex-json "
                     "are mutually exclusive")
    try:
        imu_pos_mm = tuple(float(value) for value in args.imu_pos_mm.split(","))
    except ValueError:
        parser.error("--imu-pos-mm must be x,y,z in millimetres")
    if len(imu_pos_mm) != 3 or not np.all(np.isfinite(imu_pos_mm)):
        parser.error("--imu-pos-mm must be three finite values")
    records = run_matrix(
        entries, args.data_dir, params=params,
        model_source=args.model_source, mount_flex=mount_flex,
        series_flex=series_flex,
        imu_pos_mm=imu_pos_mm)
    report = {
        "schema_version": 1,
        "manifest": str(args.manifest.resolve()),
        "model_source": args.model_source,
        "servo_params": args.servo_params,
        "leg_mount_flex": (None if mount_flex is None
                           else mount_flex.summary()),
        "joint_series_flex": (None if series_flex is None
                              else series_flex.summary()),
        "imu_pos_mm": list(imu_pos_mm),
        "summary": _summaries(records),
        "records": records,
    }
    out = args.out or args.data_dir / (
        f"replay_{args.split}_{args.model_source}_{args.servo_params}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nwrote {out}")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
