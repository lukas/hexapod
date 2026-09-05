import copy

import pytest

from hexapod_lab.guarded_queue import GuardedQueueError, _NoRedirect, http_client, queue_plan


def payload():
    return {"name": "Timing canary", "description": "Operator-supervised only",
            "duration_seconds": 3, "execution_mode": "external_guarded",
            "parameters": {"robot_id": "hexapod-1", "plan_id": "timing-v1"}}


def client(existing=None, supported=True):
    calls = []
    def request(method, path, body=None):
        calls.append((method, path, body))
        if path == "/openapi.json":
            return {"components": {"schemas": {"ExperimentIn": {"properties": {
                "execution_mode": {"enum": ["builtin", "external_guarded"] if supported else ["builtin"]}
            }}}}}
        if method == "GET":
            return existing or []
        return {**body, "id": "exp-1", "status": "waiting_for_operator"}
    return request, calls


def test_old_server_refused_before_any_post():
    request, calls = client(supported=False)
    with pytest.raises(GuardedQueueError, match="does not advertise"):
        queue_plan({"queue_payloads": [payload()]}, request)
    assert all(method == "GET" for method, _, _ in calls)


def test_validated_guarded_job_receipt():
    request, calls = client()
    receipt = queue_plan({"queue_payloads": [payload()]}, request)[0]
    assert receipt["status"] == "waiting_for_operator"
    assert receipt["reused"] is False
    assert [m for m, _, _ in calls] == ["GET", "GET", "POST"]


def test_identical_job_is_reused_even_if_already_completed():
    record = {**payload(), "id": "old", "status": "succeeded"}
    request, calls = client([record])
    receipt = queue_plan({"queue_payloads": [payload()]}, request)[0]
    assert receipt == {"id": "old", "name": "Timing canary", "plan_id": "timing-v1",
                       "status": "succeeded", "reused": True}
    assert all(m == "GET" for m, _, _ in calls)


def test_changed_or_duplicate_identity_refused_before_any_post():
    stale = {**payload(), "id": "old", "status": "waiting_for_operator", "duration_seconds": 20}
    new = copy.deepcopy(payload())
    new["parameters"]["plan_id"] = "new-first"
    request, calls = client([stale])
    with pytest.raises(GuardedQueueError, match="conflicts"):
        queue_plan({"queue_payloads": [new, payload()]}, request)
    assert all(m == "GET" for m, _, _ in calls)


@pytest.mark.parametrize("change", [
    {"execution_mode": "builtin"}, {"duration_seconds": float("nan")},
    {"duration_seconds": True}, {"parameters": {"robot_id": "hexapod-1"}},
])
def test_invalid_plan_refused_without_network(change):
    request, calls = client()
    with pytest.raises(ValueError):
        queue_plan({"queue_payloads": [{**payload(), **change}]}, request)
    assert calls == []


@pytest.mark.parametrize("url", ["http://example.com", "https://user:secret@example.com", "https://example.com/path"])
def test_plaintext_remote_or_credential_url_refused(url):
    with pytest.raises(GuardedQueueError):
        http_client(url, "test-token")


def test_redirect_is_refused_before_credentials_can_be_forwarded():
    from urllib.request import Request
    request = Request("https://lab.example/api/experiments", headers={"Authorization": "Bearer private"})
    assert _NoRedirect().redirect_request(request, None, 302, "Found", {}, "https://elsewhere.example") is None
