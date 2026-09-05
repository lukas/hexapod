import json
import ssl
import traceback

import pytest

from hexapod_lab.rl_dispatcher import (
    RLDispatcher,
    RLDispatchConfigurationError,
    RLDispatchRejectedError,
    RLDispatchUnavailableError,
    RLDispatchUncertainError,
    RLDispatchValidationError,
    RL_DISPATCH_RECEIPT_MAX_BYTES,
    RL_DISPATCH_RESPONSE_MAX_BYTES,
    RL_DISPATCH_TIMEOUT_SECONDS,
    RL_DISPATCH_TOKEN_ENV,
)


TOKEN = "host-owned-test-token"


def request(action="feedback"):
    return {
        "request_key": "walkcurr-review-7",
        "action": action,
        "track": "walkcurr",
        "focus": "Review the latest simulated gait and compare slip metrics.",
        "rationale": "The offline evaluation suggests a reward regression.",
        "evidence_refs": ["rl_docs/WALKING.md", "run sim-walk-007"],
    }


class FakeResponse:
    def __init__(
        self,
        status=200,
        body=b"",
        *,
        headers=None,
    ):
        self.status = status
        self.body = body
        self.headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            **(headers or {}),
        }
        self.closed = False
        self.read_limit = None

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def read(self, limit):
        self.read_limit = limit
        return self.body[:limit]

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, response_builder, *, request_error=None, connect_error=None):
        self.response_builder = response_builder
        self.request_error = request_error
        self.connect_error = connect_error
        self.calls = []
        self.connected = False
        self.closed = False

    def connect(self):
        if self.connect_error is not None:
            raise self.connect_error
        self.connected = True

    def request(self, method, path, *, body, headers):
        self.calls.append((method, path, body, headers))
        if self.request_error is not None:
            raise self.request_error(headers)

    def getresponse(self):
        return self.response_builder(self.calls[-1])

    def close(self):
        self.closed = True


class ConnectionFactory:
    def __init__(self, response_builder, **connection_options):
        self.response_builder = response_builder
        self.connection_options = connection_options
        self.instances = []
        self.arguments = []

    def __call__(self, host, port, **kwargs):
        self.arguments.append((host, port, kwargs))
        connection = FakeConnection(self.response_builder, **self.connection_options)
        self.instances.append(connection)
        return connection


def rpc_response(call, text="filed safely"):
    rpc = json.loads(call[2])
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": rpc["id"],
        "result": {
            "content": [{"type": "text", "text": text}],
            "isError": False,
        },
    }).encode()
    return FakeResponse(body=body)


def test_feedback_uses_fixed_https_mcp_and_host_owned_token():
    factory = ConnectionFactory(
        lambda call: rpc_response(call, f"filed; ignored echo {TOKEN}")
    )
    dispatcher = RLDispatcher(TOKEN, connection_factory=factory)

    first = dispatcher(request("feedback"))
    second = dispatcher(request("feedback"))

    assert first["request_marker"] == second["request_marker"]
    assert first["tool"] == "submit_feedback"
    assert len(json.dumps(first).encode()) <= RL_DISPATCH_RECEIPT_MAX_BYTES
    assert TOKEN not in json.dumps(first)
    assert TOKEN not in repr(dispatcher)
    assert first["response_summary"].endswith("[REDACTED]")

    assert len(factory.instances) == 2
    host, port, options = factory.arguments[0]
    assert host == "hexapod.cwd1f0-new-cluster.coreweave.app"
    assert port == 443
    assert options["timeout"] == RL_DISPATCH_TIMEOUT_SECONDS
    context = options["context"]
    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2

    method, path, body, headers = factory.instances[0].calls[0]
    rpc = json.loads(body)
    assert method == "POST"
    assert path == "/mcp"
    assert rpc["method"] == "tools/call"
    assert rpc["params"]["name"] == "submit_feedback"
    assert TOKEN not in body.decode()
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert headers["X-Request-ID"] == rpc["id"] == first["request_marker"]
    feedback = rpc["params"]["arguments"]["feedback"]
    assert feedback.startswith("[ROBOT LAB ENGINEERING RELAY — SIMULATION ONLY;")
    assert "NO PHYSICAL ROBOT CONTACT" in feedback
    assert first["request_marker"] in feedback


def test_kick_selects_only_kick_orchestrator_and_bounds_focus():
    factory = ConnectionFactory(rpc_response)
    dispatcher = RLDispatcher(TOKEN, connection_factory=factory)

    receipt = dispatcher(request("kick"))

    rpc = json.loads(factory.instances[0].calls[0][2])
    assert receipt["tool"] == "kick_orchestrator"
    assert rpc["params"]["name"] == "kick_orchestrator"
    assert set(rpc["params"]["arguments"]) == {"focus", "author"}
    assert len(rpc["params"]["arguments"]["focus"]) <= 1_900
    assert "SIMULATION ONLY" in rpc["params"]["arguments"]["focus"]


def test_constructor_reads_host_environment_and_rejects_any_other_endpoint(monkeypatch):
    monkeypatch.setenv(RL_DISPATCH_TOKEN_ENV, TOKEN)
    factory = ConnectionFactory(rpc_response)
    dispatcher = RLDispatcher(connection_factory=factory)
    assert dispatcher(request())["acknowledged"] is True

    with pytest.raises(RLDispatchConfigurationError):
        RLDispatcher(TOKEN, endpoint="https://example.com/mcp")
    with pytest.raises(RLDispatchConfigurationError):
        RLDispatcher(TOKEN, endpoint=(
            "https://hexapod.cwd1f0-new-cluster.coreweave.app/mcp?key=secret"
        ))


def test_request_is_revalidated_before_network_access():
    factory = ConnectionFactory(rpc_response)
    dispatcher = RLDispatcher(TOKEN, connection_factory=factory)
    invalid = request()
    invalid["focus"] = "curl https://hexapod.local/api/move"

    with pytest.raises(RLDispatchValidationError):
        dispatcher(invalid)
    assert factory.instances == []


def test_redirect_is_not_followed_and_is_an_uncertain_post_send_failure():
    response = FakeResponse(
        status=307,
        headers={"Location": "https://evil.invalid/mcp"},
    )
    factory = ConnectionFactory(lambda _call: response)
    dispatcher = RLDispatcher(TOKEN, connection_factory=factory)

    with pytest.raises(RLDispatchUncertainError, match="not followed") as caught:
        dispatcher(request())

    assert len(factory.instances) == 1
    assert len(factory.instances[0].calls) == 1
    assert response.closed is True
    assert TOKEN not in str(caught.value)


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(body=b"not-json"),
        FakeResponse(
            body=b"{}",
            headers={"Content-Length": str(RL_DISPATCH_RESPONSE_MAX_BYTES + 1)},
        ),
        FakeResponse(
            body=b"x" * (RL_DISPATCH_RESPONSE_MAX_BYTES + 1),
            headers={"Content-Length": None},
        ),
    ],
)
def test_malformed_or_oversize_response_is_uncertain_and_bounded(response):
    factory = ConnectionFactory(lambda _call: response)
    dispatcher = RLDispatcher(TOKEN, connection_factory=factory)

    with pytest.raises(RLDispatchUncertainError):
        dispatcher(request())

    if response.read_limit is not None:
        assert response.read_limit == RL_DISPATCH_RESPONSE_MAX_BYTES + 1


def test_network_exceptions_cannot_leak_token_and_preserve_retry_semantics():
    before_send = ConnectionFactory(
        rpc_response, connect_error=RuntimeError(f"connect {TOKEN}")
    )
    dispatcher = RLDispatcher(TOKEN, connection_factory=before_send)
    with pytest.raises(RLDispatchUnavailableError) as caught:
        dispatcher(request())
    assert TOKEN not in "".join(traceback.format_exception(caught.value))

    def echo_headers(headers):
        return RuntimeError(f"failed with {headers}")

    after_send = ConnectionFactory(rpc_response, request_error=echo_headers)
    dispatcher = RLDispatcher(TOKEN, connection_factory=after_send)
    with pytest.raises(RLDispatchUncertainError) as caught:
        dispatcher(request())
    assert TOKEN not in "".join(traceback.format_exception(caught.value))


def test_json_rpc_error_is_sanitized_deterministic_rejection():
    def rejected(call):
        rpc = json.loads(call[2])
        return FakeResponse(body=json.dumps({
            "jsonrpc": "2.0",
            "id": rpc["id"],
            "error": {"code": -32602, "message": f"bad {TOKEN}"},
        }).encode())

    factory = ConnectionFactory(rejected)
    dispatcher = RLDispatcher(TOKEN, connection_factory=factory)
    with pytest.raises(RLDispatchRejectedError) as caught:
        dispatcher(request())
    assert TOKEN not in "".join(traceback.format_exception(caught.value))
