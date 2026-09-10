"""Publish a finished run in one command, without an LLM turn per artifact.

Run only after motion/recorders have stopped and the robot command lease has
been released. This client does not control the robot or change queue latches.
Artifacts are staged before terminal registration, so an interrupted upload
cannot cause the automatic sealer to publish an incomplete successful result.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


SERVER_FILES = {
    "manifest.json", "experiment.json", "summary.md", "vision-context.json",
    "apriltag-layout.snapshot.json", "apriltag-pose-config.snapshot.json",
    "floor-tag-map.snapshot.json", "hexapod-tag-map.snapshot.json",
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def chunks(handle):
    yield from iter(lambda: handle.read(1024 * 1024), b"")


def digest(handle):
    value = hashlib.sha256()
    for chunk in chunks(handle):
        value.update(chunk)
    return value.hexdigest()


class LabPublisher:
    def __init__(self, base_url, token, timeout=120):
        parsed = urlsplit(base_url)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or (parsed.scheme == "http" and parsed.hostname not in
                    {"localhost", "127.0.0.1", "::1"})):
            raise ValueError("Use a loopback HTTP or HTTPS RobotLab URL without credentials")
        if not token or "\n" in token or "\r" in token:
            raise ValueError("HEXAPOD_LAB_TOKEN is required")
        self.base_url, self.token, self.timeout = base_url.rstrip("/"), token, timeout

    def request(self, method, path, payload=None, file=None):
        headers = {"Authorization": "Bearer " + self.token}
        body = None
        if file is not None:
            headers.update({"Content-Type": "application/octet-stream",
                            "Content-Length": str(os.fstat(file.fileno()).st_size)})
            body = chunks(file)
        elif payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        # A fresh opener per request supports concurrent uploads without shared
        # connection state, proxies, or bearer forwarding through redirects.
        response = build_opener(ProxyHandler({}), NoRedirect()).open(
            Request(self.base_url + path, data=body, headers=headers, method=method),
            timeout=self.timeout,
        )
        return response

    def json(self, method, path, payload=None):
        with self.request(method, path, payload) as response:
            return json.load(response)

    def upload(self, experiment_id, path):
        target = f"/api/experiments/{experiment_id}/artifacts/{quote(path.name, safe='')}"
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Artifact must be a regular file: {path.name}")
        with path.open("rb") as source:
            before = os.fstat(source.fileno())
            try:
                with self.request("PUT", target + "?defer_manifest=true", file=source) as response:
                    response.read()
            except HTTPError as exc:
                if exc.code != 409:
                    raise
                # A retry may encounter files from a previously interrupted
                # publication. Reuse only an exact byte match; never overwrite.
                source.seek(0)
                expected = digest(source)
                with self.request("GET", target) as response:
                    if digest(response) != expected:
                        raise ValueError(f"Existing artifact differs: {path.name}") from exc
            after = os.fstat(source.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError(f"Artifact changed during publication: {path.name}")
        return before.st_size


def finalize(publisher, experiment_id, result, artifacts, workers=4):
    if not re.fullmatch(r"[a-f0-9]{32}", experiment_id):
        raise ValueError("Expected the saved experiment's 32-character ID")
    if result.get("status") not in {"succeeded", "failed", "cancelled"}:
        raise ValueError("Result must explicitly state its terminal status")
    if not result.get("summary_markdown"):
        raise ValueError("A brief factual summary_markdown is required")
    paths = [Path(path) for path in artifacts]
    names = [path.name for path in paths]
    if (len(names) != len(set(names)) or any(name in SERVER_FILES or
            name.startswith(".") or name.endswith(".upload") for name in names)):
        raise ValueError("Artifact names must be unique, visible, and not server-owned")
    if any(path.is_symlink() or not path.is_file() for path in paths):
        raise ValueError("All artifacts must exist as regular files before publication")
    started = time.monotonic()
    prefix = f"/api/experiments/{experiment_id}"
    plan = publisher.json("GET", prefix)
    payload = dict(result)
    # The service requires exact saved-spec identity. Fetch it mechanically;
    # agents should not rediscover import_result or paraphrase its parameters.
    for key in ("name", "description", "duration_seconds", "parameters"):
        value = plan[key]
        if key in payload and payload[key] != value:
            raise ValueError(f"Result {key} differs from the saved plan")
        payload[key] = value
    with ThreadPoolExecutor(max_workers=max(1, min(8, workers))) as pool:
        sizes = list(pool.map(lambda path: publisher.upload(experiment_id, path), paths))
    # No terminal write occurs until every upload succeeds. The existing result
    # endpoint verifies identity on retries, and sealing rebuilds all digests.
    publisher.json("POST", prefix + "/result", payload)
    sealed = publisher.json("POST", prefix + "/evidence-seal", {})
    if not sealed.get("evidence_sealed_at") or not sealed.get("evidence_manifest_sha256"):
        raise RuntimeError("RobotLab did not confirm the evidence seal")
    return {
        "experiment_id": experiment_id,
        "status": sealed["status"],
        "evidence_manifest_sha256": sealed["evidence_manifest_sha256"],
        "evidence_sealed_at": sealed["evidence_sealed_at"],
        "uploaded_artifacts": len(paths), "uploaded_bytes": sum(sizes),
        "publish_seconds": round(time.monotonic() - started, 3),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--result-file", type=Path, required=True,
                        help="JSON with status, summary_markdown and actual recorded_at; saved spec is fetched automatically")
    parser.add_argument("--artifact-list", type=Path, required=True,
                        help="JSON array of file paths, relative to this list's directory")
    parser.add_argument("--url", default="http://127.0.0.1:8767")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    files = json.loads(args.artifact_list.read_text())
    if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
        parser.error("--artifact-list must contain a JSON array of paths")
    paths = [args.artifact_list.parent / item for item in files]
    result = json.loads(args.result_file.read_text())
    try:
        receipt = finalize(LabPublisher(args.url, os.environ.get("HEXAPOD_LAB_TOKEN", "")),
                           args.experiment_id, result, paths, args.workers)
    except HTTPError as exc:
        # Never print headers, credentials, or an arbitrarily large error body.
        raise SystemExit(f"RobotLab publication failed: HTTP {exc.code}; evidence not confirmed sealed")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
