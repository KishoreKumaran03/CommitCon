import base64
import binascii
import hmac
import os

from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


class BasicAuthMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] == "/api/health":
            await self.app(scope, receive, send)
            return

        expected_password = os.getenv("CAMPUSFLOW_PASSWORD")
        if not expected_password:
            await self.app(scope, receive, send)
            return

        authorization = next(
            (value for key, value in scope["headers"] if key.lower() == b"authorization"),
            b"",
        )
        try:
            scheme, encoded = authorization.split(None, 1)
            if scheme.lower() != b"basic":
                raise ValueError("Unsupported authorization scheme.")
            decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
            username, separator, password = decoded.partition(":")
        except (ValueError, UnicodeDecodeError, binascii.Error):
            username, separator, password = "", "", ""

        expected_username = os.getenv("CAMPUSFLOW_USERNAME", "admin")
        valid = (
            bool(separator)
            and hmac.compare_digest(username.encode("utf-8"), expected_username.encode("utf-8"))
            and hmac.compare_digest(password.encode("utf-8"), expected_password.encode("utf-8"))
        )
        if not valid:
            response = Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="CampusFlow"'},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
