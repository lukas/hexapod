"""Submit reviewed physical plans only to an operator-waiting Robot Lab lane.

This client never executes robot commands. The server must advertise guarded
jobs before the first POST, and matching plan IDs are reused, not duplicated.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.parse import urlsplit


class GuardedQueueError(ValueError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward a bearer credential to a redirected destination.
        return None


FIELDS = ("name", "description", "duration_seconds", "parameters", "execution_mode")
# The current Lab GET /api/experiments returns at most Store.list()'s newest
# 100 records, without a cursor. A full page cannot establish that an older
# matching plan is absent, so do not silently create a duplicate.
EXPERIMENT_LIST_LIMIT = 100


def validate_payloads(plan: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(plan, dict):
        raise GuardedQueueError("Plan must be a JSON object")
    payloads = plan.get("queue_payloads")
    if not isinstance(payloads, list) or not payloads:
        raise GuardedQueueError("Plan needs a nonempty queue_payloads list")
    ids: set[str] = set()
    for payload in payloads:
        if not isinstance(payload, dict) or payload.get("execution_mode") != "external_guarded":
            raise GuardedQueueError("Every job must explicitly use external_guarded")
        if set(payload) != set(FIELDS):
            raise GuardedQueueError("Unexpected or missing experiment fields")
        duration = payload.get("duration_seconds")
        if isinstance(duration, bool) or not isinstance(duration, (float, int)) or not math.isfinite(duration) or duration <= 0:
            raise GuardedQueueError("Job duration must be finite and positive")
        if not isinstance(payload.get("name"), str) or not 1 <= len(payload["name"]) <= 120:
            raise GuardedQueueError("Job needs a name of at most 120 characters")
        if not isinstance(payload.get("description"), str) or len(payload["description"]) > 4000:
            raise GuardedQueueError("Job description must be text of at most 4000 characters")
        params = payload.get("parameters")
        if not isinstance(params, dict) or not params.get("robot_id"):
            raise GuardedQueueError("Every guarded job needs parameters.robot_id")
        plan_id = params.get("plan_id")
        if not isinstance(plan_id, str) or not plan_id or plan_id in ids:
            raise GuardedQueueError("Every job needs a unique nonempty parameters.plan_id")
        ids.add(plan_id)
    # Reject nonfinite values anywhere before network activity.
    json.dumps(payloads, allow_nan=False)
    return payloads


def _same_spec(record: dict[str, Any], payload: dict[str, Any]) -> bool:
    return all(record.get(key) == payload[key] for key in FIELDS)


def queue_plan(plan: dict[str, Any], request: Callable[..., Any]) -> list[dict[str, Any]]:
    payloads = validate_payloads(plan)
    schema = request("GET", "/openapi.json")
    modes = (schema.get("components", {}).get("schemas", {}).get("ExperimentIn", {})
             .get("properties", {}).get("execution_mode", {}).get("enum", []))
    if "external_guarded" not in modes:
        raise GuardedQueueError("Server does not advertise external_guarded; no jobs submitted")
    existing = request("GET", "/api/experiments")
    if not isinstance(existing, list):
        raise GuardedQueueError("Server experiment listing is invalid; no jobs submitted")
    listing_may_be_truncated = len(existing) >= EXPERIMENT_LIST_LIMIT
    matches = {}
    # Check all existing identities before any mutation, including stale plans.
    for payload in payloads:
        plan_id = payload["parameters"]["plan_id"]
        found = [r for r in existing if isinstance(r, dict)
                 and isinstance(r.get("parameters"), dict)
                 and r["parameters"].get("plan_id") == plan_id]
        if len(found) > 1 or (found and not _same_spec(found[0], payload)):
            raise GuardedQueueError(f"Existing plan {plan_id!r} conflicts; no jobs submitted")
        if found:
            matches[plan_id] = found[0]
        elif listing_may_be_truncated:
            raise GuardedQueueError(
                f"Plan {plan_id!r} was not found in the newest {EXPERIMENT_LIST_LIMIT} "
                "experiments; older identities may be hidden. Inspect full history "
                "or add server-side plan lookup before submitting; no jobs submitted"
            )
    receipts = []
    for payload in payloads:
        plan_id = payload["parameters"]["plan_id"]
        reused = plan_id in matches
        record = matches[plan_id] if reused else request("POST", "/api/experiments", payload)
        if not isinstance(record, dict) or not _same_spec(record, payload) or not record.get("id"):
            raise GuardedQueueError("Server returned an inconsistent receipt; inspect Lab before retrying")
        if not reused and record.get("status") != "waiting_for_operator":
            raise GuardedQueueError("New job did not enter waiting_for_operator; inspect Lab immediately")
        receipts.append({"id": record["id"], "name": record["name"],
                         "plan_id": plan_id, "status": record.get("status"), "reused": reused})
    return receipts


def http_client(base_url: str, token: str) -> Callable[..., Any]:
    parsed = urlsplit(base_url)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (parsed.scheme != "https" and not local_http) or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise GuardedQueueError("Use an HTTPS server origin or a loopback HTTP origin")
    if not token:
        raise GuardedQueueError("Configured token environment variable is empty")
    opener = build_opener(_NoRedirect())

    def request(method: str, path: str, payload: Any = None) -> Any:
        data = None if payload is None else json.dumps(payload, allow_nan=False).encode()
        req = Request(base_url.rstrip("/") + path, data=data, method=method,
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with opener.open(req, timeout=30) as response:
                if urlsplit(response.url).netloc != parsed.netloc:
                    raise GuardedQueueError("Unexpected redirected origin")
                raw = response.read(16 * 1024 * 1024 + 1)
        except HTTPError as exc:
            raise GuardedQueueError(f"Lab returned HTTP {exc.code}; inspect existing jobs before retrying") from None
        if len(raw) > 16 * 1024 * 1024:
            raise GuardedQueueError("Lab response exceeded the evidence client size limit")
        return json.loads(raw)

    return request


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--base-url", default="https://robot-lab.cwd1f0-new-cluster.coreweave.app")
    parser.add_argument("--token-env", default="HEXAPOD_LAB_TOKEN")
    parser.add_argument("--submit", action="store_true", help="Submit to the guarded queue; otherwise validate locally")
    parser.add_argument("--receipts", type=Path)
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text())
        payloads = validate_payloads(plan)
        if not args.submit:
            print(json.dumps({"validated": len(payloads), "submitted": False}))
            return
        result = {"receipts": queue_plan(plan, http_client(args.base_url, os.environ.get(args.token_env, "")))}
        if args.receipts:
            args.receipts.parent.mkdir(parents=True, exist_ok=True)
            args.receipts.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Guarded queue refused: {exc}\n")


if __name__ == "__main__":
    main()
