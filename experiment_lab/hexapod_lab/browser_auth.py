"""Browser sign-in without HTTP Basic password dialogs.

API clients keep using their existing Authorization header. Browser sessions
contain only an opaque random identifier and disappear when this process stops.
"""

import base64
from dataclasses import dataclass
import hashlib
from html import escape
import secrets
import time
from typing import Dict, Optional
from urllib.parse import parse_qs, quote, urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from .auth import Principal, TokenAuth


COOKIE_NAME = "hexapod_lab_session"
SESSION_SECONDS = 8 * 60 * 60
MAX_SESSIONS = 2048


@dataclass(frozen=True)
class BrowserSession:
    principal: Principal
    expires_at: float


def safe_next(value: str) -> str:
    """Accept only local browser pages, never an external redirect."""
    if any(ord(char) < 32 for char in value) or "\\" in value:
        return "/"
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "/"
    if parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//"):
        return "/"
    if parsed.path == "/" or parsed.path in {"/tag-scan", "/tag-layout-history"}:
        return value
    if parsed.path.startswith("/experiments/"):
        return value
    return "/"


def login_page(next_path: str, *, error: str = "", username: str = "") -> str:
    message = f"<p class='error' role='alert'>{escape(error)}</p>" if error else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in · Robot Lab</title>
<style>
:root{{color-scheme:dark;font-family:system-ui,sans-serif;background:#0c1110;color:#e8f1ec}}
*{{box-sizing:border-box}}body{{margin:0;min-height:100svh;display:grid;place-items:center;padding:24px}}
main{{width:100%;max-width:430px;padding:32px;border:1px solid #2a3932;border-radius:20px;background:#141c19}}
.eyebrow{{color:#b7f34a;font-size:13px;font-weight:700;letter-spacing:.12em;text-transform:uppercase}}
h1{{font-size:32px;letter-spacing:-.04em;margin:12px 0}}p{{color:#a8bab1;line-height:1.5}}
label{{display:block;font-size:14px;font-weight:600;margin:22px 0 8px}}
input{{width:100%;min-width:0;border:1px solid #53665b;border-radius:8px;padding:13px;font:inherit;background:#0c1110;color:#e8f1ec}}
input:focus{{outline:2px solid #b7f34a;outline-offset:2px}}
button{{width:100%;margin-top:26px;border:0;border-radius:8px;padding:14px;font:inherit;font-weight:700;background:#b7f34a;color:#142006;cursor:pointer}}
.error{{border:1px solid #a64c48;border-radius:8px;padding:12px;color:#ffb9b3}}
.hint{{font-size:13px;margin-bottom:0}}
</style></head><body><main>
<div class="eyebrow">Robot Lab</div><h1>Sign in</h1>
<p>View experiments, results, and recordings.</p>{message}
<form method="post" action="/login">
<input type="hidden" name="next" value="{escape(next_path, quote=True)}">
<label for="username">Username</label>
<input id="username" name="username" value="{escape(username, quote=True)}" autocomplete="username" autocapitalize="none" spellcheck="false" required maxlength="120">
<label for="password">Password</label>
<input id="password" name="password" type="password" autocomplete="current-password" autocapitalize="none" spellcheck="false" required maxlength="4096">
<button type="submit">Sign in</button>
</form><p class="hint">Use your Robot Lab username and password.</p>
</main></body></html>"""


def install_browser_auth(app: FastAPI, auth: TokenAuth, public_base_url: str) -> None:
    sessions: Dict[str, BrowserSession] = {}

    def session_key(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def get_session(request: Request) -> Optional[BrowserSession]:
        token = request.cookies.get(COOKIE_NAME, "")
        if not token or len(token) > 128:
            return None
        key = session_key(token)
        session = sessions.get(key)
        if session and session.expires_at <= time.monotonic():
            sessions.pop(key, None)
            return None
        return session

    def same_origin(request: Request) -> bool:
        if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
            return False
        base = urlsplit(public_base_url) if public_base_url else request.url
        expected = f"{base.scheme}://{base.netloc}"
        return request.headers.get("origin", "").rstrip("/") == expected

    def private_response(response):
        response.headers["Cache-Control"] = "no-store"
        # Browsers may send Origin: null on a form POST under no-referrer.
        # Preserve same-origin form checks without leaking referrers elsewhere.
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def form_response(next_path: str, *, error: str = "", username: str = "", status: int = 200):
        response = HTMLResponse(login_page(next_path, error=error, username=username), status_code=status)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
        return private_response(response)

    @app.middleware("http")
    async def browser_session(request: Request, call_next):
        session = get_session(request)
        if session and request.url.path not in {"/login", "/logout"}:
            if request.method not in {"GET", "HEAD", "OPTIONS"} and not same_origin(request):
                return private_response(JSONResponse({"detail": "Same-origin browser request required"}, status_code=403))
            request.state.browser_principal = session.principal
        response = await call_next(request)
        path = request.url.path
        browser_page = path in {"/", "/tag-scan", "/tag-layout-history"} or path.startswith("/experiments/")
        if browser_page and response.status_code == 401 and request.method in {"GET", "HEAD"}:
            destination = safe_next(path + ("?" + request.url.query if request.url.query else ""))
            response = RedirectResponse("/login?next=" + quote(destination, safe=""), status_code=303)
        if response.status_code == 401 and COOKIE_NAME in request.cookies:
            # An expired session must not reopen a Basic dialog for a video,
            # download, or fetch still in flight. Reloading a page shows login.
            if "WWW-Authenticate" in response.headers:
                del response.headers["WWW-Authenticate"]
        if COOKIE_NAME in request.cookies or browser_page or path in {"/login", "/logout"}:
            private_response(response)
        return response

    @app.get("/login", response_class=HTMLResponse, include_in_schema=False)
    async def show_login(request: Request):
        return form_response(safe_next(request.query_params.get("next", "/")))

    @app.post("/login", include_in_schema=False)
    async def sign_in(request: Request):
        if not same_origin(request):
            return form_response("/", error="Open the sign-in page on this website and try again.", status=403)
        if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/x-www-form-urlencoded":
            return form_response("/", error="Please use the sign-in form.", status=415)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 8192:
                return form_response("/", error="The sign-in details are too long.", status=413)
        try:
            fields = parse_qs(body.decode("utf-8"), keep_blank_values=True, max_num_fields=3)
            if any(len(values) != 1 for values in fields.values()):
                raise ValueError("Duplicate form field")
        except (ValueError, UnicodeError):
            return form_response("/", error="Please enter your sign-in details again.", status=400)
        username = fields.get("username", [""])[0].strip()
        password = fields.get("password", [""])[0]
        destination = safe_next(fields.get("next", ["/"])[0])
        try:
            if not username or ":" in username or len(username) > 120 or len(password) > 4096:
                raise HTTPException(401)
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            principal = auth.authenticate("Basic " + credentials)
        except HTTPException:
            return form_response(destination, error="Username or password wasn’t accepted. Please check both and try again.", username=username[:120], status=401)
        now = time.monotonic()
        for key, value in list(sessions.items()):
            if value.expires_at <= now:
                sessions.pop(key, None)
        previous = request.cookies.get(COOKIE_NAME, "")
        if previous:
            sessions.pop(session_key(previous), None)
        if len(sessions) >= MAX_SESSIONS:
            sessions.pop(next(iter(sessions)))
        token = secrets.token_urlsafe(32)
        sessions[session_key(token)] = BrowserSession(principal, now + SESSION_SECONDS)
        response = RedirectResponse(destination, status_code=303)
        # Secure also covers TLS terminated by the configured CoreWeave proxy.
        secure = request.url.scheme == "https" or urlsplit(public_base_url).scheme == "https"
        response.set_cookie(COOKIE_NAME, token, httponly=True, secure=secure, samesite="lax", path="/")
        return private_response(response)

    @app.post("/logout", include_in_schema=False)
    async def sign_out(request: Request):
        if not same_origin(request):
            return private_response(JSONResponse({"detail": "Same-origin browser request required"}, status_code=403))
        token = request.cookies.get(COOKIE_NAME, "")
        if token:
            sessions.pop(session_key(token), None)
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(COOKIE_NAME, path="/")
        return private_response(response)
