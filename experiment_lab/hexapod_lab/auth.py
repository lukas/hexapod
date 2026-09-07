from dataclasses import dataclass
import base64
import hashlib
import hmac
from typing import Dict

from fastapi import Header, HTTPException, Request


ROLE_LEVEL = {"viewer": 1, "automation": 2, "operator": 2, "admin": 3}


@dataclass(frozen=True)
class Principal:
    name: str
    role: str


class TokenAuth:
    def __init__(self, records: str):
        self._tokens: Dict[str, Principal] = {}
        for record in filter(None, (item.strip() for item in records.split(","))):
            try:
                role, name, token = record.split(":", 2)
            except ValueError as exc:
                raise ValueError("HEXAPOD_API_KEYS entries must be role:name:token") from exc
            if role not in ROLE_LEVEL or not token:
                raise ValueError(
                    "API key role must be viewer, automation, operator, or admin"
                )
            digest = hashlib.sha256(token.encode()).hexdigest()
            self._tokens[digest] = Principal(name=name, role=role)

    @property
    def configured(self) -> bool:
        return bool(self._tokens)

    def authenticate(self, authorization: str) -> Principal:
        scheme, _, token = authorization.partition(" ")
        username = ""
        if scheme.lower() == "basic" and token:
            try:
                username, token = base64.b64decode(token).decode().split(":", 1)
            except Exception:
                token = ""
        elif scheme.lower() == "bearer" and token:
            pass
        else:
            raise HTTPException(401, "Authentication required",
                                headers={"WWW-Authenticate": 'Basic realm="Hexapod Lab"'})
        candidate = hashlib.sha256(token.encode()).hexdigest()
        for digest, principal in self._tokens.items():
            if hmac.compare_digest(candidate, digest) and (not username or username == principal.name):
                return principal
        raise HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": 'Basic realm="Hexapod Lab"'})

    def dependency(self, minimum_role: str):
        def verify(request: Request, authorization: str = Header(default="")) -> Principal:
            principal = getattr(request.state, "browser_principal", None) or self.authenticate(authorization)
            if (
                principal.role == "automation"
                and minimum_role not in {"viewer", "automation"}
            ):
                raise HTTPException(403, "Automation credential is not allowed for this operation")
            if ROLE_LEVEL[principal.role] < ROLE_LEVEL[minimum_role]:
                raise HTTPException(403, "Insufficient role")
            return principal
        return verify
