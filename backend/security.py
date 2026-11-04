"""Local-browser request boundaries. Not a replacement for authentication."""

from fastapi import HTTPException
from starlette.responses import JSONResponse


class LocalRequestGuard:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        allowed = {
            b"http://127.0.0.1:5173",
            b"http://localhost:5173",
            b"http://127.0.0.1:8000",
            b"http://localhost:8000",
        }
        if scope["method"] not in ("GET", "HEAD", "OPTIONS") and headers.get(
            b"origin"
        ) not in allowed | {None}:
            return await JSONResponse({"detail": "Untrusted browser origin"}, 403)(
                scope, receive, send
            )
        limit = 102 * 1024 * 1024 if scope["path"].endswith("/videos") else 1024 * 1024
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await JSONResponse({"detail": "Invalid Content-Length"}, 400)(
                scope, receive, send
            )
        if length > limit:
            return await JSONResponse({"detail": "Request body too large"}, 413)(
                scope, receive, send
            )
        received = 0

        async def bounded_receive():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > limit:
                raise HTTPException(413, "Request body too large")
            return message

        await self.app(scope, bounded_receive, send)
