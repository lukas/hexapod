"""Verify the controller's signed browser cookie without trusting proxy headers."""

import base64
import hashlib
import hmac
from pathlib import Path
import time
from typing import Optional

from .auth import Principal


COOKIE_NAME = "hexapod_sso"


class SsoAuth:
    def __init__(self, secret_file: Optional[Path], users: str):
        self.secret_file = secret_file
        self.users = {}
        for record in filter(None, (item.strip() for item in users.split(","))):
            role, separator, name = record.partition(":")
            if (not separator or role not in {"viewer", "operator", "admin"}
                    or not name or len(name) > 120
                    or any(ord(char) < 32 or char in ":|" for char in name)
                    or name in self.users):
                raise ValueError("HEXAPOD_SSO_USERS must contain unique viewer/operator/admin:name entries")
            self.users[name] = Principal(name=name, role=role)

    def authenticate(self, token: str) -> Optional[Principal]:
        if not self.secret_file or not self.users or not token or len(token) > 512:
            return None
        # Re-read for rotation; a missing/unreadable secret never enables access.
        try:
            secret = self.secret_file.read_text().strip().encode()
            if not secret:
                return None
            body, signature = token.rsplit(".", 1)
            payload = base64.b64decode(body + "=" * (-len(body) % 4), altchars=b"-_", validate=True)
            expected = hmac.new(secret, payload, hashlib.sha256).hexdigest().encode("ascii")
            if not hmac.compare_digest(expected, signature.encode("ascii")):
                return None
            name, expires = payload.decode("utf-8").rsplit("|", 1)
            if int(expires) <= time.time():
                return None
        except (OSError, ValueError, UnicodeError):
            return None
        return self.users.get(name)
